#!/usr/bin/env python3

import argparse
import os
import re

from .compiler import wrap_compiler
from .server import daemon
from .sched import pick_server

DISTCCD_PORT = 3632


def parse_distcc_host(h):
    rx = re.compile('^([^:/]+):([0-9]+)/([0-9]+)')
    m = rx.match(h)
    if m is None:
        raise ValueError('invalid host spec: %s' % h)
    host, port, weight = m.groups()
    return {
        'host': host,
        'port': int(port),
        'weight': int(weight),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='hosts', action='append', nargs='*',
                        help='where to compile')
    parser.add_argument("compiler", nargs='*', help="compiler and arguments")
    args, unknown = parser.parse_known_args()
    args.compiler.extend(unknown)

    if args.hosts is None:
        try:
            args.hosts = os.environ['DISTCC_HOSTS'].split()
        except KeyError:
            pass
    if args.hosts is None:
        args.hosts = ['127.0.0.1:{}/10'.format(DISTCCD_PORT)]

    distcc_hosts = [parse_distcc_host(h) for h in args.hosts]
    host = pick_server(distcc_hosts, tuple(args.compiler))

    wrap_compiler(host['host'], host['port'], args.compiler)


def server_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='IP to bind to', default='127.0.0.1')
    parser.add_argument('--port', type=int,
                        help='port to listen at', default=DISTCCD_PORT)
    args = parser.parse_args()
    daemon(host=args.host, port=args.port)
