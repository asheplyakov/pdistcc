
import copy
import logging
import multiprocessing
import os
import tempfile
import time
import socketserver
import subprocess

from .net import (
    FileOpsFactory,
    InvalidToken,
    chunked_read_write,
    chunked_send,
    dcc_encode,
    read_field,
    to_string,
)

from .compiler import find_compiler_wrapper

DCC_PROTOCOL = 1
logger = logging.getLogger(__name__)


class Distccd(socketserver.BaseRequestHandler):
    def __init__(self, settings, *args, **kwargs):
        # XXX: super().__init__ calls handle(), which uses _settings
        self._settings = settings
        self._fileops = kwargs.get('fileops', FileOpsFactory())
        self._tempfile = kwargs.get('tempfile', tempfile.NamedTemporaryFile)
        self._Popen = kwargs.get('popen', subprocess.Popen)
        self._perf = Perf()
        for arg in ('fileops', 'tempfile', 'popen'):
            if arg in kwargs:
                del kwargs[arg]
        super().__init__(*args, **kwargs)

    def _read_compiler_cmd(self, argc):
        compiler_cmd = []
        for n in range(argc):
            argv, tlen, arg = read_field(self.request)
            if argv != b'ARGV':
                raise InvalidToken("expected ARGV, got {}", to_string(argv))
            compiler_cmd.append(to_string(arg))
        logger.debug('%s: orig compiler cmd: %s', self.client_address, ' '.join(compiler_cmd))
        return compiler_cmd

    def _read_request(self):
        hello, tlen, _ = read_field(self.request, False)
        if hello != b'DIST':
            raise InvalidToken("client hasn't sent a valid greeting")
        argc_name, argc, _ = read_field(self.request, False)
        if argc_name != b'ARGC':
            raise InvalidToken("expected ARGC, got {}", to_string(argc_name))
        compiler_cmd = self._read_compiler_cmd(argc)
        return compiler_cmd

    def _read_doti(self):
        start_time = time.perf_counter()
        name, doti_bytes, _ = read_field(self.request, False)
        if name != b'DOTI':
            raise InvalidToken("expected DOTI, got {}", to_string(name))
        logger.debug('%s: reading doti file', self.client_address)
        with self._tempfile(suffix='.ii', delete=False) as doti:
            path = doti.name
            chunked_read_write(self.request, doti.file, doti_bytes)
            doti.flush()
        self._perf.recv_time = (time.perf_counter() - start_time)*1000
        self._perf.recv_size = doti_bytes
        logger.debug('%s: successfully read %s bytes', self.client_address, doti_bytes)
        return path

    def _compile(self, wrapper, cleanup_files):
        objext = '.' + wrapper.object_file().split('.')[-1]
        objname = os.path.basename(wrapper.object_file())

        # XXX: perhaps this is racy
        with self._tempfile(prefix=objname, suffix=objext) as f:
            objfile = f.name
        wrapper.set_object_file(objfile)
        cleanup_files.append(objfile)

        compiler_cmd = wrapper.compiler_cmd()
        logger.debug('%s: running compiler: %s', self.client_address, str(compiler_cmd))
        start_time = time.perf_counter()
        compiler = self._Popen(compiler_cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = compiler.communicate()
        self._perf.compile_time = (time.perf_counter() - start_time)*1000
        ret = compiler.returncode
        logger.debug('%s: compiler returned: %s', self.client_address, ret)
        return ret, stdout, stderr, objfile

    def _reply(self, ret, stdout, stderr, objfile):
        logging.debug('%s: sending reply', self.client_address)
        start_time = time.perf_counter()
        buf = dcc_encode('DONE', DCC_PROTOCOL)
        buf += dcc_encode('STAT', ret)
        buf += dcc_encode('SERR', len(stderr))
        self.request.sendall(buf)
        self.request.sendall(stderr)
        self.request.sendall(dcc_encode('SOUT', len(stdout)))
        self.request.sendall(stdout)

        try:
            with self._fileops.open(objfile, 'rb') as doto:
                doto_len = self._fileops.size(doto)
                self.request.sendall(dcc_encode('DOTO', doto_len))
                logger.debug('%s: sending object file %s', self.client_address, objfile)
                chunked_send(self.request, doto, doto_len)
                self._perf.send_time = (time.perf_counter() - start_time)*1000
                self._perf.send_size = doto_len
                logger.debug('%s: successfully sent %s bytes', self.client_address, doto_len)
        except FileNotFoundError:
            if ret != 0:
                self.request.sendall(dcc_encode('DOTO', 0))
            else:
                raise RuntimeError("compiler failed to produce '%s' file" % objfile)

    def handle(self):
        if 'delayed_handle' in self._settings:
            pass
        start_time = time.perf_counter()
        logger.info("connection from %s", self.client_address)
        cleanup_files = []
        try:
            compiler_cmd = self._read_request()
            wrapper = find_compiler_wrapper(compiler_cmd, self._settings)
            wrapper.can_handle_command()
            doti_file = self._read_doti()
            cleanup_files.append(doti_file)
            wrapper.set_preprocessed_file(doti_file)
            ret, stdout, stderr, objfile = self._compile(wrapper, cleanup_files)
            self._reply(ret, stdout, stderr, objfile)
            self._perf.total_time = (time.perf_counter() - start_time)*1000
            logger.info("%s: request handled: %s", self.client_address, self._perf)
        except BrokenPipeError:
            # client has disconnected, ignore
            pass
        finally:
            for p in cleanup_files:
                if os.path.isfile(p):
                    os.remove(p)


class Perf:
    def __init__(self):
        self._total_time = 0.0
        self._compile_time = 0.0
        self._recv_time = 0.0
        self._send_time = 0.0
        self._recv_size = 0
        self._send_size = 0

    @property
    def total_time(self):
        return self._total_time

    @property
    def recv_time(self):
        return self._recv_time

    @property
    def compile_time(self):
        return self._compile_time

    @property
    def send_time(self):
        return self._send_time

    @property
    def recv_size(self):
        return self._recv_size

    @property
    def send_size(self):
        return self._send_size

    @total_time.setter
    def total_time(self, value):
        self._total_time = value

    @compile_time.setter
    def compile_time(self, value):
        self._compile_time = value

    @recv_time.setter
    def recv_time(self, value):
        self._recv_time = value

    @send_time.setter
    def send_time(self, value):
        self._send_time = value

    @recv_size.setter
    def recv_size(self, value):
        self._recv_size = value

    @send_size.setter
    def send_size(self, value):
        self._send_size = value

    def __str__(self):
        return f'total: {self._total_time:.2f}, compile: {self._compile_time:.2f}, recv: {self._recv_time:.2f}, send: {self._send_time:.2f}, recv size: {self._recv_size}, send size: {self._send_size}'


def daemon(settings, host='127.0.0.1', port=3632):
    logging.basicConfig(level=settings['loglevel'],
                        format='%(asctime)-15s %(message)s')

    def distccd_factory(*args, **kwargs):
        return Distccd(copy.deepcopy(settings), *args, **kwargs)

    socketserver.TCPServer.allow_reuse_address = True
    socketserver.TCPServer.request_queue_size = multiprocessing.cpu_count() + 1
    logger.info("listening at %s:%s", host, port)
    if hasattr(socketserver, 'ForkingTCPServer'):
        Server = socketserver.ForkingTCPServer
    else:
        Server = socketserver.ThreadingTCPServer
    with Server((host, port), distccd_factory) as server:
        server.serve_forever()
