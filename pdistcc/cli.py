#!/usr/bin/env python3

import argparse
from .compiler import wrap_compiler
from .server import daemon

DISTCCD_PORT = 3632


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='where to compile', default='127.0.0.1')
    parser.add_argument('--port', type=int,
                        help='port distccd listens at', default=DISTCCD_PORT)
    parser.add_argument("compiler", nargs='*', help="compiler and arguments")
    args = parser.parse_args()

    wrap_compiler(args.host, args.port, args.compiler)


def server_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='IP to bind to', default='127.0.0.1')
    parser.add_argument('--port', type=int,
                        help='port to listen at', default=DISTCCD_PORT)
    args = parser.parse_args()
    daemon(host=args.host, port=args.port)
