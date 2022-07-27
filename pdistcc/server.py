
import aiofiles
import aiofiles.os
import asyncio
import inspect
import logging
import time

from .net import (
    DCC_TOKEN_HEADER_LEN,
    AsyncFileOpsFactory,
    InvalidToken,
    dcc_decode,
    dcc_encode,
    to_string,
)

from .compiler import find_compiler_wrapper

DCC_PROTOCOL = 1
logger = logging.getLogger(__name__)


async def read_field(reader, with_data=True):
    data = await reader.readexactly(DCC_TOKEN_HEADER_LEN)
    name, tlen = dcc_decode(data)
    val = b''
    if with_data and tlen > 0:
        val = await reader.readexactly(tlen)
    return name, tlen, val


async def _popen(cmd):
    prog = cmd.pop(0)
    proc = await asyncio.create_subprocess_exec(prog, *cmd,
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE)
    return proc


class Distccd:
    def __init__(self, reader, writer, settings):
        self._reader = reader
        self._writer = writer
        self._settings = settings
        self._tempfile = aiofiles.tempfile.NamedTemporaryFile
        self._fileops = AsyncFileOpsFactory()
        self._Popen = _popen
        self._client_address = None
        self._perf = Perf()

    async def _read_compiler_cmd(self, argc):
        compiler_cmd = []
        for n in range(argc):
            argv, tlen, arg = await read_field(self._reader)
            if argv != b'ARGV':
                raise InvalidToken("expected ARGV, got {}", to_string(argv))
            compiler_cmd.append(to_string(arg))
        logger.info('orig compiler cmd: %s', ' '.join(compiler_cmd))
        return compiler_cmd

    async def _read_request(self):
        hello, tlen, _ = await read_field(self._reader, False)
        if hello != b'DIST':
            raise InvalidToken("client hasn't sent a valid greeting")
        argc_name, argc, _ = await read_field(self._reader, False)
        if argc_name != b'ARGC':
            raise InvalidToken("expected ARGC, got {}", to_string(argc_name))
        compiler_cmd = await self._read_compiler_cmd(argc)
        return compiler_cmd

    async def _read_doti(self):
        name, doti_bytes, _ = await read_field(self._reader, False)
        ti = time.perf_counter()
        if name != b'DOTI':
            raise InvalidToken("expected DOTI, got {}", to_string(name))
        logger.debug(f'reading doti file from {self._client_address}')
        async with self._tempfile(suffix='.ii', delete=False) as doti:
            path = doti.name
            chunk_size = 64*1024
            size = doti_bytes
            while size > 0:
                if size < chunk_size:
                    chunk_size = size
                chunk = await self._reader.read(chunk_size)
                await doti.write(chunk)
                size = size - len(chunk)
            await doti.flush()
        self._perf.recv_time = (time.perf_counter() - ti)*1000
        self._perf.recv_size = doti_bytes
        logger.debug('successfully read %s bytes', doti_bytes)
        return path

    async def _compile(self, wrapper, cleanup_files):
        objext = '.' + wrapper.object_file().split('.')[-1]
        objfile = wrapper.preprocessed_file() + objext
        wrapper.set_object_file(objfile)
        cleanup_files.append(objfile)

        compiler_cmd = wrapper.compiler_cmd()
        logger.debug('running compiler: %s', str(compiler_cmd))
        ti = time.perf_counter()
        compiler = await self._Popen(compiler_cmd)
        stdout, stderr = await compiler.communicate()
        self._perf.compile_time = (time.perf_counter() - ti)*1000
        ret = compiler.returncode
        logger.debug('compiler returned: %s', ret)
        return ret, stdout, stderr, objfile

    async def _reply(self, ret, stdout, stderr, objfile):
        ti = time.perf_counter()
        logging.debug(f'sending reply to {self._client_address}')
        self._writer.write(dcc_encode('DONE', DCC_PROTOCOL))
        self._writer.write(dcc_encode('STAT', ret))
        self._writer.write(dcc_encode('SERR', len(stderr)))
        self._writer.write(stderr)
        self._writer.write(dcc_encode('SOUT', len(stdout)))
        self._writer.write(stdout)

        try:
            async with self._fileops.open(objfile, 'rb') as doto:
                doto_len = await self._fileops.size(doto)
                self._writer.write(dcc_encode('DOTO', doto_len))
                logger.debug('sending object file %s (%d bytes)', objfile, doto_len)
                chunk_size = 256*1024
                size = doto_len
                while size > 0:
                    if size < chunk_size:
                        chunk_size = size
                    chunk = await doto.read(size)
                    self._writer.write(chunk)
                    size = size - len(chunk)
                await self._writer.drain()
                self._perf.send_time = (time.perf_counter() - ti)*1000
                self._perf.send_size = doto_len
                logger.debug('successfully sent %s bytes', doto_len)
        except FileNotFoundError:
            if ret != 0:
                self._writer.write(dcc_encode('DOTO', 0))
                await self._writer.drain()
            else:
                raise RuntimeError("compiler failed to produce '%s' file" % objfile)

    async def run(self):
        self._client_address = self._writer.get_extra_info('peername')
        logger.info(f'connection from {self._client_address!r}')
        start_time = time.perf_counter()
        cleanup_files = []
        try:
            compiler_cmd = await self._read_request()
            wrapper = find_compiler_wrapper(compiler_cmd, self._settings)
            wrapper.can_handle_command()
            doti_file = await self._read_doti()
            cleanup_files.append(doti_file)
            wrapper.set_preprocessed_file(doti_file)
            ret, stdout, stderr, objfile = await self._compile(wrapper, cleanup_files)
            await self._reply(ret, stdout, stderr, objfile)
            await self._writer.drain()
            self._writer.close()
            await self._writer.wait_closed()
            self._perf.total_time = (time.perf_counter() - start_time)*1000
            logger.info(f'{self._client_address!r} request handled: {self._perf}')
        except BrokenPipeError:
            # client has disconnected, ignore
            logger.info('client "%s": premature disconnect', self._client_address)
        except asyncio.exceptions.IncompleteReadError:
            # client has disconnected, ignore
            logger.info('client "%s": premature disconnect', self._client_address)
        finally:
            for p in cleanup_files:
                try:
                    await self._fileops.remove(p)
                except FileNotFoundError:
                    pass
                except IsADirectoryError:
                    # XXX: should I log this?
                    pass


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


async def _daemon(settings, host='127.0.0.1', port=3632):
    async def dcc_handler(reader, writer):
        handler = Distccd(reader, writer, settings)
        await handler.run()

    server = await asyncio.start_server(dcc_handler,
                                        host,
                                        port,
                                        limit=256*1024,
                                        reuse_address=True)
    logger.info("listening at %s:%s", host, port)
    async with server:
        await server.serve_forever()


def daemon(settings, host='127.0.0.1', port=3632):
    logging.basicConfig(level=settings['loglevel'],
                        format='%(asctime)-15s %(message)s')

    try:
        asyncio.run(_daemon(settings, host, port))
    except KeyboardInterrupt:
        logger.info('Got ^C, exiting...')
        pass
