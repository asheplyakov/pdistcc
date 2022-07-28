#ifndef BENCH_STATS_H
#define BENCH_STATS_H
#include <stdint.h>

struct bench_stats {
	double avg;
	int64_t count;
	int64_t min;
	int64_t max;
	double m2;
	double var;
};

extern void bench_stats_reset(struct bench_stats *st);
extern void bench_stats_update(struct bench_stats *st, int64_t value);
extern void bench_stats_merge(struct bench_stats *self, const struct bench_stats *other);
extern void bench_stats_finalize(struct bench_stats *self);

#endif /* BENCH_STATS_H */


