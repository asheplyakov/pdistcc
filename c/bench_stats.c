#include "bench_stats.h"

void bench_stats_reset(struct bench_stats *st) {
	st->avg = 0.0;
	st->count = 0;
	st->min = INT64_MAX;
	st->max = INT64_MIN;
}

void bench_stats_update(struct bench_stats *st, int64_t x) {
	st->count++;
	st->avg += (((double)x) - st->avg)/st->count;
	if (x > st->max) {
		st->max = x;
	}
	if (x < st->min) {
		st->min = x;
	}
}

void bench_stats_merge(struct bench_stats *self, const struct bench_stats *other) {
	int64_t new_count = self->count + other->count;
	self->avg = (self->avg*self->count + other->avg*other->count)/new_count;
	self->count = new_count;
	if (other->max > self->max) {
		self->max = other->max;
	}
	if (other->min < self->min) {
		self->min = other->min;
	}
}
