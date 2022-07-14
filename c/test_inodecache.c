#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <time.h>
#include <semaphore.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include "inodecache.h"
#include "bench_stats.h"

int get_gcc_triplet(const char *compiler, char **tripletptr) {
	int err = 0;
	char *cmd = NULL;
	FILE *gccpipe = NULL;
	size_t bufsz = 0;
	ssize_t len = -1;
	char *newlineptr = NULL;

	if (!tripletptr) {
		err = -EINVAL;
		goto out;
	}

	if (asprintf(&cmd, "%s -dumpmachine", compiler) < 0) {
		cmd = NULL;
		err = -ENOMEM;
		goto out;
	}

	gccpipe = popen(cmd, "r");
	if (!gccpipe) {
		err = errno ? -errno : -ENOMEM;
		printf("%s: popen failed: %d (%s)\n", __func__, errno, strerror(errno));
		goto out;
	}

	if ((len = getline(tripletptr, &bufsz, gccpipe)) < 0) {
		err = -errno;
		free(*tripletptr);
		goto out;
	}

	newlineptr = strchr(*tripletptr, '\n');
	if (newlineptr) {
		*newlineptr = '\0';
	}
out:
	if (gccpipe) {
		pclose(gccpipe);
	}
	free(cmd);
	return err;
}

int64_t timespec_delta_usec(const struct timespec *start, const struct timespec *end) {
	int64_t delta;
	delta = ((int64_t)(end->tv_sec - start->tv_sec))*1000000;
	delta += (end->tv_nsec - start->tv_nsec)/1000;
	return delta;
}

struct bench_result {
	sem_t lock;
	struct bench_stats stats;
};

int bench_result_map(struct bench_result **resultptr) {
	int err = 0;
	struct bench_result *result = MAP_FAILED;

	if (!resultptr || *resultptr != NULL) {
		err = -EINVAL;
		goto out_err;
	}

	result = mmap(NULL,
			sizeof(*result),
			PROT_READ|PROT_WRITE,
			MAP_SHARED|MAP_ANON,
			-1, 0);
	if (MAP_FAILED == result) {
		err = -errno;
		perror("mmap");
		goto out_err;
	}

	bench_stats_reset(&result->stats);

	if (sem_init(&result->lock, 1, 1) != 0) {
		err = -errno;
		perror("sem_init");
		goto out_err;
	}
	*resultptr = result;
	return 0;

out_err:
	if (result != MAP_FAILED) {
		munmap(result, sizeof(*result));
	}
	return err;
}

int bench_result_unmap(struct bench_result **ptrptr) {
	int err = 0;
	struct bench_result *obj = NULL;
	if (!ptrptr || !*ptrptr) {
		return 0;
	}
	obj = *ptrptr;
	if (MAP_FAILED == (void *)obj) {
		*ptrptr = NULL;
		return 0;
	}
	if (munmap((void *)obj, sizeof(*obj)) != 0) {
		err = - errno;
		perror("munmap");
		return err;
	}
	*ptrptr = NULL;
	return 0;
}

int bench_inode_cache(const char *compiler, const char *triplet, int repetitions, struct bench_result *result) {
	int i;
	int err = 0;
	uint16_t entry_type = 1;
	char *value = NULL;
	struct bench_stats bstat;
	struct timespec start, end;
	struct inode_cache ic = { .dir = "/home/asheplyakov/.cache/pdistcc/icache", .dirfd = -1 };

	bench_stats_reset(&bstat);
	err = inode_cache_open(&ic);
	if (err) {
		goto out;
	}

	err = inode_cache_put(&ic, compiler, entry_type, triplet);
	if (err) {
		printf("failed to store %s for %s: error %d (%s)\n",
			triplet, compiler, err, strerror(-err));
		goto out;
	}

	for (i = 0; i < repetitions; i++) {
		if (clock_gettime(CLOCK_MONOTONIC, &start) < 0) {
			err = -errno;
			perror("clock_gettime");
			goto out;
		}
		err = inode_cache_get(&ic, compiler, entry_type, &value);
		if (err) {
			printf("failed to read %s/%d from cache: %d (%s)\n",
				compiler, (int)entry_type, err, strerror(-err));
			goto out;
		}
		if (clock_gettime(CLOCK_MONOTONIC, &end) < 0) {
			err = -errno;
			perror("clock_gettime");
			goto out;
		}
		bench_stats_update(&bstat, timespec_delta_usec(&start, &end));

		if (strcmp(value, triplet) != 0) {
			printf("wrong value %s, expected %s\n", value, triplet);
			err = -EINVAL;
			goto out;
		}
		free(value);
		value = NULL;
	}

	printf("pid %d, count: %" PRId64 ", avg: %.1lf, max: %" PRId64 ", min: %" PRId64 " usec\n",
		(int)getpid(),
		bstat.count,
		bstat.avg,
		bstat.max,
		bstat.min);
	fflush(stdout);

	if (sem_wait(&result->lock) < 0) {
		err = errno;
		perror("sem_wait");
		goto out;
	}
	bench_stats_merge(&result->stats, &bstat);
	if (sem_post(&result->lock) < 0) {
		err = errno;
		perror("sem_post");
		goto out;
	}
out:
	free(value);
	inode_cache_close(&ic);
	return err;
}

int run_bench(const char *compiler, const char *triplet, unsigned nproc, int repetitions) {
	int ret = 0, err = 0;
	unsigned i = 0;
	int wstatus = 0;
	pid_t *children = NULL;
	struct bench_result *result = NULL;

	children = calloc(nproc, sizeof(pid_t));
	if (!children) {
		ret = ENOMEM;
		goto out;
	}
	err = bench_result_map(&result);
	if (err) {
		goto out;
	}

	for (i = 0; i < nproc; i++) {
		pid_t pid = fork();
		if (pid < 0) {
			/* failed to start process */
			perror("fork");
			children[i] = pid;
		} else if (pid == 0) {
			/* child */
			int err;
			err = bench_inode_cache(compiler, triplet, repetitions, result);
			exit(err < 0 ? -err : err);
		} else {
			children[i] = pid;
		}
	}
	for (i = 0; i < nproc; i++) {
		if (children[i] < 0) {
			ret++;
			continue;
		}
		if (waitpid(children[i], &wstatus, 0) < 0) {
			perror("waitpid");
			ret++;
			continue;
		}
		if (!WIFEXITED(wstatus)) {
			printf("child %d terminated abnormally\n", children[i]);
			ret++;
			continue;
		}
		err = WEXITSTATUS(wstatus);
		if (err) {
			ret++;
			printf("child %d returned error code %d\n",
				children[i], err);
		}
	}

	printf("total: count: %" PRId64 ", avg: %.1lf, max: %" PRId64 ", min: %" PRId64 " usec\n",
		result->stats.count,
		result->stats.avg,
		result->stats.max,
		result->stats.min);
	fflush(stdout);
out:
	bench_result_unmap(&result);
	free(children);
	return ret;
}

int main(int argc, char **argv) {
	int err = 0;
	uint16_t entry_type = 1;
	char *value = NULL;
	const char* test_value = NULL;
	const char* compiler = NULL;
	struct inode_cache ic = { .dir = "/home/asheplyakov/.cache/pdistcc/icache", .dirfd = -1 };
	char *triplet = NULL;

	if (argc != 3) {
		printf("usage: test_inodecache /path/to/binary value\n");
		return 2;
	}
	compiler = argv[1];
	test_value = argv[2];

	if ((err = inode_cache_open(&ic)) != 0) {
		printf("*** Failed to open inode cache, error %d (%s)\n", err, strerror(-err));
		goto out;
	}
	if ((err = inode_cache_del(&ic, compiler, entry_type)) != 0) {
		printf("*** Failed to purge %s from cache: %d (%s)\n", compiler, err, strerror(err));
		goto out;
	}
	if ((err = inode_cache_put(&ic, compiler, entry_type, test_value)) != 0) {
		printf("*** Failed to put %s => %s to cache: %d (%s)\n",
			compiler, test_value, err, strerror(err));
		goto out;
	}
	if ((err = inode_cache_get(&ic, compiler, entry_type, &value)) != 0) {
		printf("*** Failed to retrive value from cache: %d (%s)\n", err, strerror(-err));
		goto out;
	}
	printf("inode_cache(%s) = %s\n", compiler, value);
	if (strcmp(value, test_value) != 0) {
		printf("*** Wrong value from inode cache for %s: expected %s, actual %s\n",
			compiler, test_value, value);
		err = 7;
		goto out;
	}

	free(value);
	value = NULL;

	if ((err = get_gcc_triplet(compiler, &triplet)) != 0) {
		printf("*** Failed to figure out GCC triplet: %d (%s)\n", err, strerror(-err));
		goto out;
	}
	printf("triplet of %s: %s\n", compiler, triplet);

	if ((err = inode_cache_put(&ic, compiler, entry_type, triplet)) != 0) {
		printf("*** Failed to put %s => %s to cache: %d (%s)\n",
			compiler, triplet, err, strerror(err));
		goto out;
	}


	if ((err = inode_cache_get(&ic, compiler, entry_type, &value)) != 0) {
		printf("*** Failed to get value from cache for %s: %d (%s)\n",
			compiler, err, strerror(-err));
		goto out;
	}

	if (strcmp(value, triplet) != 0) {
		printf("*** Wrong value from inode cache for %s: expected %s, actual %s\n",
			compiler, test_value, value);
		err = 11;
		goto out;
	}

	printf("triplet of %s from inode cache: %s\n", compiler, value);
	if (run_bench(compiler, triplet, 20, 500)) {
		err = EXIT_FAILURE;
	}
out:
	free(value);
	inode_cache_close(&ic);
	return err < 0 ? -err : err;
}

