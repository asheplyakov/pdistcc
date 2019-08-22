
import bisect


def pick_server(servers, key):
    if len(servers) == 1:
        return servers[0]
    buckets = [0]
    total_weight = 0
    for s in servers:
        total_weight += s['weight']
        buckets.append(total_weight - 1)
    bucket_idx = hash(key) % total_weight
    server_idx = bisect.bisect_left(buckets, bucket_idx) - 1
    return servers[server_idx]
