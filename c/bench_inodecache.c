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
#include <ctype.h>
#include "inodecache.h"
#include "bench_stats.h"
#include "compiler_properties.h"
#include "mkdir_p.h"

struct bench_result {
	sem_t lock;
	struct bench_stats stats;
	struct bench_stats nocache_stats;
	int lock_initialized;
};

void bench_result_unmap(struct bench_result **ptrptr) {
	struct bench_result *obj = NULL;
	if (!ptrptr || !*ptrptr) {
		return;
	}
	obj = *ptrptr;
	if (MAP_FAILED == (void *)obj) {
		*ptrptr = NULL;
		return;
	}
	if (obj->lock_initialized) {
		if (sem_destroy(&obj->lock)) {
			perror("bench_result_unmap: sem_destroy");
		}
		obj->lock_initialized = 0;
	}
	if (munmap((void *)obj, sizeof(*obj)) != 0) {
		perror("bench_result_unmap: munmap");
	}
	*ptrptr = NULL;
}

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

	memset(result, 0, sizeof(*result));
	bench_stats_reset(&result->stats);
	bench_stats_reset(&result->nocache_stats);

	if (sem_init(&result->lock, 1, 1) != 0) {
		err = -errno;
		perror("sem_init");
		goto out_err;
	}
	result->lock_initialized = 1;

	*resultptr = result;
	return 0;

out_err:
	bench_result_unmap(&result);
	return err;
}

int64_t timespec_delta_usec(const struct timespec *start, const struct timespec *end) {
	int64_t delta;
	delta = ((int64_t)(end->tv_sec - start->tv_sec))*1000000;
	delta += (end->tv_nsec - start->tv_nsec)/1000;
	return delta;
}

static void bench_stats_print(FILE *f, const struct bench_stats *bstat) {
	fprintf(f, "count: %" PRId64 ", avg: %.1lf, max: %" PRId64 ", min: %" PRId64 ", var: %.1lf usec",
		bstat->count,
		bstat->avg,
		bstat->max,
		bstat->min,
		bstat->var);
}

int bench_inode_cache(int cachedirfd, const char *compiler, const char *triplet, int repetitions, struct bench_result *result) {
	int i;
	int err = 0;
	char *value = NULL;
	struct bench_stats bstat, nocache_stats;
	struct timespec start, end;
	struct inode_cache ic = { .dir = "none", .dirfd = cachedirfd };

	bench_stats_reset(&bstat);
	bench_stats_reset(&nocache_stats);
	err = inode_cache_open(&ic);
	if (err) {
		printf("failed to open inode cache, error %d\n", err);
		goto out;
	}

	for (i = 0; i < repetitions; i++) {
		if (clock_gettime(CLOCK_MONOTONIC, &start) < 0) {
			err = -errno;
			perror("clock_gettime");
			goto out;
		}
		err = inode_cache_get(&ic, compiler, (uint16_t)GCC_TRIPLET, &value);
		if (err) {
			printf("failed to read %s/%d from cache: %d (%s)\n",
				compiler, GCC_TRIPLET, err, strerror(-err));
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
	bench_stats_finalize(&bstat);

	for (i = 0; i < repetitions; i++) {
		if (clock_gettime(CLOCK_MONOTONIC, &start) < 0) {
			err = -errno;
			perror("clock_gettime [3]");
			goto out;
		}
		err = get_gcc_triplet(compiler, &value);
		if (err) {
			printf("failed to figure out %s triplet: %d (%s)\n",
				compiler, err, strerror(err > 0 ? err : -err));
			goto out;
		}

		if (clock_gettime(CLOCK_MONOTONIC, &end) < 0) {
			err = -errno;
			perror("clock_gettime [4]");
			goto out;
		}
		bench_stats_update(&nocache_stats, timespec_delta_usec(&start, &end));

		if (strcmp(triplet, value) != 0) {
			printf("%s: wrong triplet '%s', expected '%s'\n",
				__func__, value, triplet);
			err = -EINVAL;
			goto out;
		}
		free(value);
		value = NULL;
	}
	bench_stats_finalize(&nocache_stats);

	printf("pid %d: ", (int)getpid());
	bench_stats_print(stdout, &bstat);
	printf("\n");
	printf("pid %d: NO CACHE ", (int)getpid());
	bench_stats_print(stdout, &nocache_stats);
	printf("\n");
	fflush(stdout);

	if (sem_wait(&result->lock) < 0) {
		err = errno;
		perror("sem_wait");
		goto out;
	}
	bench_stats_merge(&result->stats, &bstat);
	bench_stats_merge(&result->nocache_stats, &nocache_stats);
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


int run_bench(int cachedirfd, const char *compiler, const char *triplet, unsigned nproc, int repetitions) {
	int ret = 0, err = 0;
	unsigned i = 0;
	int wstatus = 0;
	pid_t *children = NULL;
	struct bench_result *result = NULL;
	struct inode_cache ic = { .dir = NULL, .dirfd = cachedirfd };

	children = calloc(nproc, sizeof(pid_t));
	if (!children) {
		ret = ENOMEM;
		goto out;
	}
	err = bench_result_map(&result);
	if (err) {
		goto out;
	}

	err = inode_cache_open(&ic);
	if (err) {
		printf("%s: failed to open inode cache, error %d\n", __func__, err);
		goto out;
	}
	err = inode_cache_put(&ic, compiler, (uint16_t)GCC_TRIPLET, triplet);
	if (err) {
		printf("%s: failed to store %s for %s: error %d (%s)\n",
			__func__, triplet, compiler, err, strerror(-err));
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
			err = bench_inode_cache(cachedirfd, compiler, triplet, repetitions, result);
			free(children);
			free((void *)triplet);
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

	printf("total: ");
	bench_stats_print(stdout, &result->stats);
	printf("\n");
	printf("NO CACHE: total: ");
	bench_stats_print(stdout, &result->nocache_stats);
	printf("\n");
	fflush(stdout);
out:
	bench_result_unmap(&result);
	free(children);
	inode_cache_close(&ic);
	return ret;
}

static void print_help() {
	printf("Usage: bench_inode_cache [-j concurrency] [-n repetitions] [-c cachedir] /path/to/gcc\n");
}

#define DEFAULT_NPROC 10
#define DEFAULT_REPETITIONS 500

int main(int argc, char **argv) {
	int err = 0, opt, cachedirfd = -1;
	int nproc = 0, repetitions = 0;
	const char* compiler = NULL;
	char* triplet = NULL;

	const char *cachedir = NULL;

	while ((opt = getopt(argc, argv, "hj:n:c:")) != -1) {
		switch (opt) {
			case 'n':
				repetitions = (unsigned)atoi(optarg);
				break;
			case 'j':
				nproc = atoi(optarg);
				break;
			case 'c':
				cachedir = strdup(optarg);
				if (!cachedir) {
					printf("*** main: failed to allocate cachedir\n");
					exit(EXIT_FAILURE);
				}
				break;
			case 'h':
				print_help();
				exit(EXIT_SUCCESS);
				break;
			default:
				print_help();
				exit(EXIT_FAILURE);
		}
	}
	if (optind >= argc) {
		print_help();
		exit(EXIT_FAILURE);
	}
	compiler = argv[optind];

	repetitions = repetitions > 0 ? repetitions : DEFAULT_REPETITIONS;
	if (!nproc) {
		nproc = sysconf(_SC_NPROCESSORS_ONLN);
	}
	if (nproc <= 0) {
		nproc = DEFAULT_NPROC;
	}
	printf("repetitions: %u, nproc: %d\n", repetitions, nproc);

	if (!cachedir) {
		const char *home = getenv("HOME");
		if (!home) {
			printf("*** Neither cachedir no HOME are defined\n");
			exit(EXIT_FAILURE);
		}
		if (asprintf((char **)&cachedir, "%s/.cache", home) < 0) {
			printf("*** main: cachedir: asprintf failed\n");
			exit(EXIT_FAILURE);
		}
	}
	if ((cachedirfd = mkdir_p((char *)cachedir, 0755)) < 0) {
		err = - cachedirfd;
		printf("failed to open cachedir \"%s\": %d (%s)\n", cachedir, err, strerror(err));
		goto out;
	}

	if ((err = get_gcc_triplet(compiler, &triplet)) != 0) {
		printf("*** Failed to figure out GCC triplet: %d (%s)\n", err, strerror(-err));
		goto out;
	}
	/* make valgrind happy */
	free((void *)cachedir);
	cachedir = NULL;

	if (run_bench(cachedirfd, compiler, triplet, (unsigned)nproc, repetitions)) {
		err = EXIT_FAILURE;
	}
out:
	if (cachedirfd >= 0) {
		close(cachedirfd);
	}
	free((void *)cachedir);
	free(triplet);
	return err < 0 ? -err : err;
}
