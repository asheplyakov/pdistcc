#!/usr/bin/env python3

import argparse
import os
import socket
import subprocess
import sys

DCC_TOKEN_HEADER_LEN = 12
DCC_VERSION = 1
LANG_C = 'c'
LANG_CXX = 'c++'


def dcc_compile(doti, args, host='127.0.0.1', port=3632, ofile='a.out'):

    def dcc_encode(name, val):
        return '{0}{1:08x}'.format(name, val).encode('utf-8')

    def dcc_decode(token):
        if len(token) != DCC_TOKEN_HEADER_LEN:
            raise RuntimeError("expected %d bytes, got %d" % (DCC_TOKEN_HEADER_LEN, len(token)))
        name = token[:4]
        size = int(token[4:], 16)
        return name, size

    def request(s):
        buf = dcc_encode('DIST', DCC_VERSION)
        buf += dcc_encode('ARGC', len(args))
        for n, arg in enumerate(args):
            argbytes = arg.encode('utf-8')
            buf += dcc_encode('ARGV', len(argbytes))
            buf += argbytes

        st = os.stat(doti)
        doti_len = st.st_size
        buf += dcc_encode('DOTI', doti_len)

        s.sendall(buf)

        with open(doti, 'rb') as f:
            remaining = doti_len
            while remaining > 0:
                chunk = f.read(4096)
                s.sendall(chunk)
                remaining -= len(chunk)

    def recv_exactly(s, count):
        data = b''
        remaining = count
        while remaining > 0:
            data += s.recv(remaining)
            remaining = count - len(data)
        return data

    def read_field(s, with_data=True):
        data = recv_exactly(s, DCC_TOKEN_HEADER_LEN)
        name, tlen = dcc_decode(data)
        val = b''
        if with_data and tlen > 0:
            val = recv_exactly(s, tlen)
        return name, tlen, val

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        request(s)

        greeting = recv_exactly(s, DCC_TOKEN_HEADER_LEN)
        expected_greeting = dcc_encode('DONE', 1)
        if greeting != expected_greeting:
            raise RuntimeError('expected DONE, got "%s"' % greeting.decode('utf-8'))

        status_str = recv_exactly(s, DCC_TOKEN_HEADER_LEN)
        if status_str[:4] != b'STAT':
            raise RuntimeError('expected STAT, got "%s"' % status_str.decode('utf-8'))
        status = int(status_str[4:], 16)

        field, flen, val = read_field(s)
        if field != b'SERR':
            raise RuntimeError('expected SERR, got "%s"' % val.decode('utf-8'))

        if flen > 0:
            sys.stderr.write(val.decode('utf-8'))

        field, flen, val = read_field(s)
        if field != b'SOUT':
            raise RuntimeError('expected SOUT, got "%s"' % val.decode('utf-8'))

        if flen > 0:
            sys.stdout.write(val.decode('utf-8'))

        if status != 0:
            sys.exit(status)

        field, flen, _ = read_field(s, False)
        if field != b'DOTO':
            raise RuntimeError('expected DOTO, got "%s"' % val.decode('utf-8'))

        left = flen
        with open(ofile, 'wb') as aout:
            while left > 0:
                val = s.recv(4096)
                aout.write(val)
                left -= len(val)
            aout.flush()


class UnsupportedCompiler(BaseException):
    def __init__(self, msg):
        self.msg = msg


class UnsupportedCompilationMode(BaseException):
    def __init__(self, msg):
        self.msg = msg


class PreprocessorFailed(BaseException):
    pass


class CompilerWrapper(object):
    def __init__(self, args):
        self._args = args[1:]
        self._compiler = args[0]

    def wrap_compiler(self, host, port):
        self.can_handle_command()
        preprocessor_cmd = self.preprocessor_cmd()
        try:
            subprocess.check_output(preprocessor_cmd)
        except subprocess.CalledProcessError:
            raise PreprocessorFailed()

        dcc_compile(self.preprocessed_file(),
                    self.compiler_cmd(),
                    host=host,
                    port=port,
                    ofile=self.object_file())

    def can_handle_command(self):
        return False

    def preprocessor_cmd(self):
        return []

    def compiler_cmd(self):
        return []

    def source_file(self):
        pass

    def object_file(self):
        pass

    def preprocessed_file(self):
        pass


class GCCWrapper(CompilerWrapper):
    source_file_extensions = ('cpp', 'cxx', 'cc', 'c')
    extension2lang = {
        'c': LANG_C,
    }

    def __init__(self, args):
        super().__init__(args)
        self._srcfile = None
        self._objfile = None
        self._preprocessed_file = None

    def _is_source_file(self, arg):
        fileext = arg.split('.')[-1].lower()
        return fileext in self.source_file_extensions

    def _lang(self):
        srcext = self._srcfile.split('.')[-1].lower()
        return self.extension2lang.get(srcext, LANG_CXX)

    def _preprocessed_filename(self, obj):
        doti_suffix = 'ii' if self._lang() == LANG_CXX else 'i'
        doti = obj.split('.')[:-1] + [doti_suffix]
        return '.'.join(doti)

    def can_handle_command(self):
        source_count = 0
        is_object_compilation = False
        has_object_file = False

        skip_next_arg = False
        for arg in self._args:
            if skip_next_arg:
                skip_next_arg = False
                continue
            if arg == '-c':
                is_object_compilation = True
            elif self._is_source_file(arg):
                source_count += 1
                self._srcfile = arg
            elif arg == '-o':
                has_object_file = True
                skip_next_arg = True

        if source_count != 1:
            raise UnsupportedCompilationMode('multiple sources')
        if not is_object_compilation:
            raise UnsupportedCompilationMode('linking')
        if not has_object_file:
            raise UnsupportedCompilationMode('output object not specified')

    def preprocessor_cmd(self):
        cmd = [self._compiler]
        next_arg_is_object = False

        for arg in self._args:
            skip_arg = False
            if '-c' == arg:
                cmd.extend(['-E'])
                skip_arg = True
            elif next_arg_is_object:
                self._objfile = arg
                self._preprocessed_file = self._preprocessed_filename(arg)
                cmd.append(self._preprocessed_file)
                next_arg_is_object = False
                skip_arg = True
            elif '-o' == arg:
                next_arg_is_object = True
            else:
                pass
            if not skip_arg:
                cmd.append(arg)
        return cmd

    def object_file(self):
        return self._objfile

    def preprocessed_file(self):
        return self._preprocessed_file

    def source_file(self):
        return self._srcfile

    def compiler_cmd(self):
        cmd = [self._compiler]
        for arg in self._args:
            if arg != self._srcfile:
                cmd.append(arg)
            else:
                cmd.append(self._preprocessed_file)
        return cmd


def wrap_compiler(host, port, compiler_cmd):
    compiler_name = os.path.basename(compiler_cmd[0])
    if compiler_name in ('gcc', 'g++'):
        wrapper = GCCWrapper(compiler_cmd)
    else:
        raise UnsupportedCompiler(compiler_name)
    wrapper.wrap_compiler(host, port)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='where to compile', default='127.0.0.1')
    parser.add_argument('--port', type=int,
                        help='port distccd listens at', default=3632)
    parser.add_argument("compiler", nargs='*', help="compiler and arguments")
    args = parser.parse_args()

    wrap_compiler(args.host, args.port, args.compiler)


if __name__ == '__main__':
    main()
