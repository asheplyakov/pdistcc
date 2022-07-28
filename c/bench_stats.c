#include <math.h>
#include "bench_stats.h"

void bench_stats_reset(struct bench_stats *st) {
	st->avg = 0.0;
	st->count = 0;
	st->min = INT64_MAX;
	st->max = INT64_MIN;
	st->m2 = 0.0;
	st->var = NAN;
}

void bench_stats_update(struct bench_stats *st, int64_t x) {
	double old_avg = st->avg;
	st->count++;
	st->avg += (((double)x) - st->avg)/st->count;
	st->m2 += (((double)x) - st->avg)*(((double)x) - old_avg);
	if (x > st->max) {
		st->max = x;
	}
	if (x < st->min) {
		st->min = x;
	}
}

static inline double square(double x) {
	return x*x;
}

static inline double prod_over_sum(int64_t x, int64_t y) {
	return ((double)(x*y))/(x + y);
}

void bench_stats_merge(struct bench_stats *self, const struct bench_stats *other) {
	int64_t new_count = self->count + other->count;
	/* n = |x|
	 * m = |y|
	 * N = n + m
	 * M_2 = M_2(x) + M_2(y) + (<x> - <y>)**2 * (n*m)/(n + m)
	 */
	double delta = self->avg - other->avg;
	self->m2 += other->m2 + square(delta)*prod_over_sum(self->count, other->count);
	self->avg = (self->avg*self->count + other->avg*other->count)/new_count;
	self->count = new_count;
	if (other->max > self->max) {
		self->max = other->max;
	}
	if (other->min < self->min) {
		self->min = other->min;
	}
	bench_stats_finalize(self);

}

void bench_stats_finalize(struct bench_stats *self) {
	self->var = sqrt(self->m2/self->count);
}
