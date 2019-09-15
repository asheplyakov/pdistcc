#!/usr/bin/env python3

import argparse

from .config import (
    client_settings,
    parse_distcc_host,
    server_settings,
)
from .compiler import wrap_compiler
from .server import daemon


def merge_settings_with_cli(settings, args):
    merged_settings = {}
    for k in settings.keys():
        cli_val = getattr(args, k) if hasattr(args, k) else None
        merged_settings[k] = cli_val or settings[k]
    for k in dir(args):
        if k.startswith('_'):
            continue
        elif k == 'compiler':
            continue
        cli_val = getattr(args, k)
        merged_settings[k] = cli_val or settings.get(k)
    return merged_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='distcc_hosts', action='append',
                        nargs=1, help='where to compile')
    parser.add_argument("compiler", nargs='*', help="compiler and arguments")
    args, unknown = parser.parse_known_args()
    args.compiler.extend(unknown)
    if args.distcc_hosts:
        # [['localhost'], ['anotherhost']]
        distcc_hosts = [parse_distcc_host(h[0]) for h in args.distcc_hosts]
        args.distcc_hosts = distcc_hosts

    settings = merge_settings_with_cli(client_settings(), args)
    return wrap_compiler(settings['distcc_hosts'], args.compiler, settings)


def server_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='IP to bind to')
    parser.add_argument('--port', type=int, help='port to listen at')
    args = parser.parse_args()
    settings = merge_settings_with_cli(server_settings(), args)
    daemon(settings,
           host=settings['host'],
           port=settings['port'])
