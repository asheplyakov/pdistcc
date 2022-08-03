#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include "barrier.h"

static int64_t
timespec_delta_usec(const struct timespec *start,
		    const struct timespec *end) {
	int64_t dt = ((int64_t)(end->tv_sec - start->tv_sec))*1000000;
	dt += ((int64_t)(end->tv_nsec - start->tv_nsec))/1000;
	return dt;
}


int child(int id, unsigned sleep_usecs, struct barrier *barrier) {
	int err = 0;
	int64_t elapsed;
	struct timespec start, end;
	if (clock_gettime(CLOCK_MONOTONIC, &start) < 0) {
		perror("clock_gettime");
		return 2;
	}
	if (sleep_usecs) {
		/* only one process sleeps explicitly... */
		printf("process #%d: sleeping for %d usec\n",
		       id, sleep_usecs);
		usleep(sleep_usecs);
	}
	/* however others wait for the sleeping process */
	err = barrier_wait(barrier);
	if (err) {
		perror("barrier_wait");
		return 3;
	}
	if (clock_gettime(CLOCK_MONOTONIC, &end) < 0) {
		perror("clock_gettime [2]");
		return 1;
	}
	elapsed = timespec_delta_usec(&start, &end);
	printf("process #%d, elapsed time: %ld usec\n", id, elapsed);
	if (elapsed < sleep_usecs) {
		printf("process #%d: unexpectedly awaken before %u\n",
		       id, sleep_usecs);
		return 1;
	}
	return 0;
}

int main(int argc, char **argv) {
	int i, err = 0, wstatus, ret = 0, N = 20;
	pid_t children[N];
	struct barrier *barrier = MAP_FAILED;

	barrier = mmap(NULL,
		       sizeof(*barrier),
		       PROT_READ | PROT_WRITE,
		       MAP_SHARED | MAP_ANON,
		       -1, 0);
	if (MAP_FAILED == barrier) {
		perror("mmap");
		exit(43);
	}

	err = barrier_init(barrier, N, 1);
	if (err) {
		fprintf(stderr, "failed to initialize the barrier\n");
		exit(7);
	}

	for (i = 0; i < N; i++) {
		pid_t pid;
		pid = fork();
		children[i] = pid;
		if (pid < 0) {
			perror("fork");
		} else if (pid == 0) {
			int err;
			unsigned sleep_usec = 0;
			if (i == N - 1) {
				sleep_usec = 1000000U;
			}
			err = child(i, sleep_usec, barrier);
			exit(err);
		}
	}
	for (i = 0; i < N; i++) {
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
			printf("child #%d terminated abnormally\n", i);
			ret++;
			continue;
		}
		err = WEXITSTATUS(wstatus);
		if (err) {
			ret++;
			printf("child #%d returned error code %d\n", i, err);
		}
	}
	barrier_close(barrier);
	munmap(barrier, sizeof(*barrier));
	return ret;
}
