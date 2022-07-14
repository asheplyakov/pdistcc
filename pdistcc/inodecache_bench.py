
import itertools
import multiprocessing
import os
import os.path
import shutil
import subprocess
import time

from .inodecache import InodeCache


class Stat:
    def __init__(self):
        self._avg = 0.0
        self._n = 0
        self._min = float("+inf")
        self._max = float("-inf")

    def update(self, x):
        self._n += 1
        self._avg += (x - self._avg)/self._n
        if x > self._max:
            self._max = x
        if x < self._min:
            self._min = x

    def merge(self, other):
        new_count = self.count + other.count
        self._avg  = (self.count*self.avg + other.count*other.avg)/new_count
        self._count = new_count
        self._min = min(self.min, other.min)
        self._max = max(self.max, other.max)

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def avg(self):
        return self._avg

    @property
    def count(self):
        return self._n


def bench(repetitions):
    cdir = os.path.expanduser('~/.cache/pdistcc/icache')
    ic = InodeCache(cdir)
    gcc = '/usr/bin/gcc'
    value = b'test'
    ic.put(gcc, 1, value)
    st = Stat()
    start, end = None, None
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        ret = ic.get(gcc, 1)
        end = time.perf_counter_ns()
        assert ret == value
        elapsed = (end - start)//1000
        st.update(elapsed)
    return st


def bench_nocache(repetitions):
    gcc = '/usr/bin/gcc'
    st = Stat()
    start, end = None, None
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        out = subprocess.check_output([gcc, '-dumpmachine']).strip()
        end = time.perf_counter_ns()
        elapsed = (end - start)//1000
        st.update(elapsed)
    return st


def bench_multiprocess(concurrency, repetitions):
    def reap(ares):
        st = ares[0].get()
        for handle in ares[1:]:
            st.merge(handle.get())
        return st

    with multiprocessing.Pool(processes=concurrency) as pool:
        ares = [pool.apply_async(bench, (repetitions,))
                for _ in range(concurrency)]
        st_cache = reap(ares)
        ares = [pool.apply_async(bench_nocache, (repetitions,))
                for _ in range(concurrency)]
        st_nocache = reap(ares)

    def report(st):
        print("average\tmax\tmin")
        print("{0:0.1f}\t{1:0.1f}\t{2:0.1f}".format(st.avg, st.max, st.min))

    print('--- cached ---')
    report(st_cache)
    print('--- NO CACHE ---')
    report(st_nocache)


def main():
    cdir = os.path.expanduser('~/.cache/pdistcc/icache')
    ic = InodeCache(cdir)
    gcc = '/usr/bin/gcc'
    ic.purge(gcc, 1)
    assert ic.get(gcc, 1) is None
    ic.put(gcc, 1, b'test')
    assert ic.get(gcc, 1) == b'test'
    bench_multiprocess(20, 500)


if __name__ == '__main__':
    main()
