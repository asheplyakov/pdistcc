
from collections import defaultdict
from math import sqrt

from ..sched import pick_server


def test_pick_server_same_weight():
    N = 10000
    server_count = 50
    servers = tuple({'host': '%s' % n, 'weight': 10} for n in range(server_count))
    counts = defaultdict(int)
    commands = ('gcc -c -o foo{0}.o foo{0}.c'.format(n).split() for n in range(N))
    for cmd in commands:
        server = pick_server(servers, tuple(cmd))
        counts[server['host']] += 1

    total = sum(count for _, count in counts.items())
    assert total == N
    avg = N / server_count

    sigma = sum((count - avg)**2 for _, count in counts.items())
    stddev = sqrt(sigma/(server_count - 1))
    assert stddev < 20.0


def test_pick_server_single():
    servers = [ {'host': 'localhost', 'weight': 100} ]
    server = pick_server(servers, 'whatever')
    assert server == servers[0]
