#!/usr/bin/env python3

import argparse
import logging

from .config import (
     DISTCCD_PORT,
     client_settings,
     merge_settings_with_cli,
     parse_distcc_host,
     server_settings,
)
from .compiler import wrap_compiler
from .server import daemon


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='distcc_hosts',
                        nargs='*', help='where to compile')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Verbose execution mode')
    parser.add_argument("compiler", nargs='*', help="compiler and arguments")
    args, unknown = parser.parse_known_args()
    args.compiler.extend(unknown)

    settings = merge_settings_with_cli(client_settings(), args)
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
    settings = merge_settings_with_cli(server_settings(), args)
    daemon(settings,
           host=settings['host'],
           port=settings['port'])
