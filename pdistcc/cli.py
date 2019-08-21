#!/usr/bin/env python3

import argparse
from .compiler import wrap_compiler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='where to compile', default='127.0.0.1')
    parser.add_argument('--port', type=int,
                        help='port distccd listens at', default=3632)
    parser.add_argument("compiler", nargs='*', help="compiler and arguments")
    args = parser.parse_args()

    wrap_compiler(args.host, args.port, args.compiler)
