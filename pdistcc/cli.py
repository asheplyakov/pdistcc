#!/usr/bin/env python3

import argparse
import logging
import os
import re

from .config import (
     DISTCCD_PORT,
     server_settings,
     client_settings,
)
from .compiler import wrap_compiler
from .server import daemon


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


def _merge_settings_with_cli(settings, args):
    merged_settings = {}
    for k in settings.keys():
        cli_val = getattr(args, k) if hasattr(args, k) else None
        merged_settings[k] = cli_val or settings[k]
    if hasattr(args, 'verbose'):
        loglevel = 'WARN'
        if args.verbose == 1:
            loglevel = 'INFO'
        elif args.verbose >= 2:
            loglevel = 'DEBUG'
        merged_settings['loglevel'] = loglevel
    return merged_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='distcc_hosts',
                        nargs='*', help='where to compile')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Verbose execution mode')
    parser.add_argument("compiler", nargs='*', help="compiler and arguments")
    args, unknown = parser.parse_known_args()
    args.compiler.extend(unknown)

    settings = _merge_settings_with_cli(client_settings(), args)
    logging.basicConfig(level=settings['loglevel'],
                        format='%(asctime)-15s %(message)s')
    distcc_hosts = [parse_distcc_host(h) for h in settings['distcc_hosts']]
    wrap_compiler(distcc_hosts, args.compiler, settings)


def server_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='IP to bind to')
    parser.add_argument('--port', type=int, help='port to listen at')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Verbose execution mode')
    args = parser.parse_args()
    settings = _merge_settings_with_cli(server_settings(), args)
    daemon(settings,
           host=settings['host'],
           port=settings['port'])
