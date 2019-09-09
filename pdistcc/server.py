
import copy
import logging
import multiprocessing
import os
import tempfile
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
        logger.debug('orig compiler cmd: %s', ' '.join(compiler_cmd))
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
        name, doti_bytes, _ = read_field(self.request, False)
        if name != b'DOTI':
            raise InvalidToken("expected DOTI, got {}", to_string(name))
        logger.debug('reading doti file')
        with self._tempfile(suffix='.ii', delete=False) as doti:
            path = doti.name
            chunked_read_write(self.request, doti.file, doti_bytes)
            doti.flush()
        logger.debug('successfully read %s bytes', doti_bytes)
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
        logger.debug('running compiler: %s', str(compiler_cmd))
        compiler = self._Popen(compiler_cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = compiler.communicate()
        ret = compiler.returncode
        logger.debug('compiler returned: %s', ret)
        return ret, stdout, stderr, objfile

    def _reply(self, ret, stdout, stderr, objfile):
        logging.debug('sending reply')
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
                logger.debug('sending object file %s', objfile)
                chunked_send(self.request, doto, doto_len)
                logger.debug('successfully sent %s bytes', doto_len)
        except FileNotFoundError:
            if ret != 0:
                self.request.sendall(dcc_encode('DOTO', 0))
            else:
                raise RuntimeError("compiler failed to produce '%s' file" % objfile)


    def handle(self):
        if 'delayed_handle' in self._settings:
            pass
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
        except BrokenPipeError:
            # client has disconnected, ignore
            pass
        finally:
            for p in cleanup_files:
                if os.path.isfile(p):
                    os.remove(p)


def daemon(settings, host='127.0.0.1', port=3632):
    logging.basicConfig(level=settings['loglevel'],
                        format='%(asctime)-15s %(message)s')

    def distccd_factory(*args, **kwargs):
        return Distccd(copy.deepcopy(settings), *args, **kwargs)

    socketserver.TCPServer.allow_reuse_address = True
    socketserver.TCPServer.request_queue_size = multiprocessing.cpu_count() + 1
    logger.info("listening at %s:%s", host, port)
    with socketserver.ThreadingTCPServer((host, port), distccd_factory) as server:
        server.serve_forever()
