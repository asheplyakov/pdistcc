
import os
import tempfile
import socketserver
import subprocess

from .net import (
    InvalidToken,
    dcc_encode,
    read_field,
    to_string,
)

from .compiler import find_compiler_wrapper

DCC_PROTOCOL = 1


def writeall(fd, chunk):
    remaining = len(chunk)
    while remaining > 0:
        written = os.write(fd, chunk[-remaining:])
        remaining -= written


class Distccd(socketserver.BaseRequestHandler):

    def _read_compiler_cmd(self, argc):
        compiler_cmd = []
        for n in range(argc):
            argv, tlen, arg = read_field(self.request)
            if argv != b'ARGV':
                raise InvalidToken("expected ARGV, got {}", to_string(argv))
            print('{0}th arg: {1}'.format(n, arg))
            compiler_cmd.append(to_string(arg))
        return compiler_cmd

    def _read_request(self):
        hello, tlen, _ = read_field(self.request, False)
        if hello != b'DIST':
            raise InvalidToken("client hasn't sent a valid greeting")
        argc_name, argc, _ = read_field(self.request, False)
        if argc_name != b'ARGC':
            raise InvalidToken("expected ARGC, got {}", to_string(argc_name))
        compiler_cmd = self._read_compiler_cmd(argc)
        print("compiler command: {}".
              format(' '.join([arg for arg in compiler_cmd])))
        return compiler_cmd

    def _read_doti(self):
        name, doti_bytes, _ = read_field(self.request, False)
        if name != b'DOTI':
            raise InvalidToken("expected DOTI, got {}", to_string(name))
        fd, path = tempfile.mkstemp(prefix='pdistcc', suffix='.ii')
        remaining = doti_bytes
        while remaining > 0:
            chunk = self.request.recv(4096)
            writeall(fd, chunk)
            remaining -= len(chunk)
        os.fsync(fd)
        os.close(fd)
        return path

    def _compile(self, wrapper, cleanup_files):
        objext = '.' + wrapper.object_file().split('.')[-1]
        objname = os.path.basename(wrapper.object_file())

        # XXX: perhaps this is racy
        fd, objfile = tempfile.mkstemp(prefix=objname, suffix=objext)
        os.close(fd)
        os.remove(objfile)
        wrapper.set_object_file(objfile)
        cleanup_files.append(objfile)

        compiler_cmd = wrapper.compiler_cmd()
        print("about to run compiler: %s" % str(compiler_cmd))
        compiler = subprocess.Popen(compiler_cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout, stderr = compiler.communicate()
        ret = compiler.returncode
        return ret, stdout, stderr, objfile

    def _reply(self, ret, stdout, stderr, objfile):
        doto_len = os.stat(objfile).st_size
        buf = dcc_encode('DONE', DCC_PROTOCOL)
        buf += dcc_encode('STAT', ret)
        buf += dcc_encode('SERR', len(stderr))
        self.request.sendall(buf)
        self.request.sendall(stderr)
        self.request.sendall(dcc_encode('SOUT', len(stdout)))
        self.request.sendall(stdout)
        self.request.sendall(dcc_encode('DOTO', doto_len))
        remaining = doto_len
        with open(objfile, 'rb') as doto:
            while remaining > 0:
                chunk = doto.read(4096)
                self.request.sendall(chunk)
                remaining -= len(chunk)

    def handle(self):
        cleanup_files = []
        try:
            compiler_cmd = self._read_request()
            wrapper = find_compiler_wrapper(compiler_cmd)
            wrapper.can_handle_command()
            doti_file = self._read_doti()
            cleanup_files.append(doti_file)
            wrapper.set_source_file(doti_file)
            wrapper.set_preprocessed_file(doti_file)
            ret, stdout, stderr, objfile = self._compile(wrapper, cleanup_files)
            self._reply(ret, stdout, stderr, objfile)
        finally:
            for p in cleanup_files:
                if os.path.isfile(p):
                    os.remove(p)


def daemon(host='127.0.0.1', port=3632):
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((host, port), Distccd) as server:
        server.serve_forever()
