#include <errno.h>
#include <semaphore.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

struct barrier {
	int N;
	int count;
	sem_t mutex;
	sem_t barrier;
	unsigned barrier_init : 1;
	unsigned mutex_init : 1;
};

int barrier_wait(struct barrier *b) {
	int err = 0;
	err = sem_wait(&b->mutex);
	if (err) {
		err = errno;
		perror("barrier_wait: sem_wait mutex");
		goto out;
	}
	b->count++;
	if (b->count == b->N) {
		err = sem_post(&b->barrier);
		if (err) {
			err = errno;
			perror("barrier_wait: sem_post barrier");
			sem_post(&b->mutex);
			goto out;
		}
	}
	err = sem_post(&b->mutex);
	if (err) {
		err = errno;
		perror("barrier_wait: sem_post mutex");
	}

	err = sem_wait(&b->barrier);
	if (err) {
		err = errno;
		perror("barrier_wait: sem_wait barrier");
		goto out;
	}
	err = sem_post(&b->barrier);
	if (err) {
		err = errno;
		perror("barrier_wait: sem_post barrier [2]");
	}
out:
	return err;
}

void barrier_close(struct barrier *b) {
	if (b->mutex_init) {
		sem_destroy(&b->mutex);
		b->mutex_init = 0;
	}
	if (b->barrier_init) {
		sem_destroy(&b->barrier);
		b->barrier_init = 0;
	}
}

int barrier_init(struct barrier *b, int N, int interprocess) {
	int err = 0;

	memset(b, 0, sizeof(*b));
	b->N = N;

	err = sem_init(&b->mutex, !!interprocess, 1);
	if (err) {
		err = errno;
		perror("barrier_init: sem_init mutex");
		goto err_out;
	} 
	b->mutex_init = 1;
	err = sem_init(&b->barrier, !!interprocess, 0);
	if (err) {
		err = errno;
		perror("barrier_init: sem_init barrier");
		goto err_out;
	}
	b->barrier_init = 1;
	return 0;
err_out:
	barrier_close(b);
	return err;
}
