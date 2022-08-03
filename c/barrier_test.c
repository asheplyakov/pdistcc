#include "barrier.h"
#include <pthread.h>
#include <time.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

struct thread_arg {
	struct barrier *barrier;
	unsigned sleep_usecs;
	int id;
	int ret;
};

static int64_t
timespec_delta_usec(const struct timespec *start,
		    const struct timespec *end) {
	int64_t dt = ((int64_t)(end->tv_sec - start->tv_sec))*1000000;
	dt += ((int64_t)(end->tv_nsec - start->tv_nsec))/1000;
	return dt;
}

static void *run(void *arg) {
	int err;
	int64_t elapsed;
	struct timespec start, end;
	struct thread_arg *thearg = arg;
	if (clock_gettime(CLOCK_MONOTONIC, &start) < 0) {
		perror("clock_gettime");
		exit(2);
	}
	if (thearg->sleep_usecs) {
		/* only one thread sleeps explicitly... */
		printf("thread %d: sleeping for %d usec\n",
		       thearg->id, thearg->sleep_usecs);
		usleep(thearg->sleep_usecs);
	}
	/* however others wait for the sleeping thread */
	err = barrier_wait(thearg->barrier);
	if (err) {
		perror("barrier_wait");
		exit(3);
	}
	if (clock_gettime(CLOCK_MONOTONIC, &end) < 0) {
		perror("clock_gettime [2]");
		exit(5);
	}
	elapsed = timespec_delta_usec(&start, &end);
	printf("thread %d, elapsed time: %ld usec\n", thearg->id, elapsed);
	if (elapsed < thearg->sleep_usecs) {
		printf("thread %d: unexpectedly awaken before %u\n",
		       thearg->id, thearg->sleep_usecs);
	       thearg->ret = 1;
	}
	return NULL;
}

int main(int argc, char **argv) {
	int i, err = 0, N = 20;
	struct thread_arg targs[N];
	pthread_t thread_ids[N];
	struct barrier barrier;

	err = barrier_init(&barrier, N, 0);
	if (err) {
		fprintf(stderr, "failed to initialize the barrier\n");
		exit(7);
	}

	for (i = 0; i < N; i++) {
		targs[i].barrier = &barrier;
		targs[i].id = i;
		targs[i].ret = 0;
		targs[i].sleep_usecs = i != N - 1 ? 0U : 1000000U;
		err = pthread_create(&thread_ids[i], NULL, run, &targs[i]);
		if (err) {
			fprintf(stderr, "pthread_create: error %d\n", err);
			exit(23);
		}
	}

	for (i = 0; i < N; i++) {
		err = pthread_join(thread_ids[i], NULL);
		if (err) {
			fprintf(stderr, "pthread_join: error %d\n", err);
			exit(29);
		}
	}
	barrier_close(&barrier);
	for (i = 0; i < N; i++) {
		if (targs[i].ret != 0) {
			fprintf(stderr, "thread %d: expectation failed\n", i);
			err++;
		}
	}
	return err;
}
