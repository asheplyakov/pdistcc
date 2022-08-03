#ifndef SA_BARRIER_H
#define SA_BARRIER_H
#include <semaphore.h>

struct barrier {
	int N;
	int count;
	sem_t mutex;
	sem_t barrier;
	unsigned barrier_init : 1;
	unsigned mutex_init : 1;
};

int barrier_wait(struct barrier *b);
int barrier_init(struct barrier *b, int N, int interprocess);
void barrier_close(struct barrier *b);


#endif /* SA_BARRIER_H */
