
from uhashring import HashRing


def pick_server(servers, key):
    if len(servers) == 1:
        return servers[0]
    # HashRing does not accept list of distcs
    _servers = dict((n, s) for n, s in enumerate(servers))
    return _servers[HashRing(_servers).get_node(key)]
