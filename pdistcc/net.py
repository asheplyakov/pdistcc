
import os
import socket
import sys

from contextlib import contextmanager


DCC_TOKEN_HEADER_LEN = 12
DCC_VERSION = 1


class ProtocolError(Exception):
    pass


class InvalidToken(ProtocolError):
    def __init__(self, fmt, *args, **kwargs):
        super().__init__()
        self.message = fmt.format(*args, **kwargs)

    def __str__(self):
        return 'InvalidToken: ' + self.message


def dcc_encode(name, val):
    return '{0}{1:08x}'.format(name, val).encode('utf-8')


def dcc_decode(token):
    if len(token) != DCC_TOKEN_HEADER_LEN:
        raise InvalidToken("expected {0} bytes, got {1}",
                           DCC_TOKEN_HEADER_LEN,
                           len(token))
    name = token[:4]
    size = int(token[4:], 16)
    return name, size


def recv_exactly(s, count):
    data = b''
    remaining = count
    while remaining > 0:
        chunk = s.recv(remaining)
        if len(chunk) == 0:
            raise ProtocolError('peer disconnected')
        data += chunk
        remaining -= len(chunk)
    return data


def read_field(s, with_data=True):
    data = recv_exactly(s, DCC_TOKEN_HEADER_LEN)
    name, tlen = dcc_decode(data)
    val = b''
    if with_data and tlen > 0:
        val = recv_exactly(s, tlen)
    return name, tlen, val


def read_token(sock, expected=None):
    data = recv_exactly(sock, DCC_TOKEN_HEADER_LEN)
    name, size = dcc_decode(data)
    if expected is not None and name != expected:
        raise InvalidToken('expected "{}", got "{}"',
                           to_string(name), to_string(expected))
    return name, size


def chunked_read_write(sock, fobj, size, chunk_size=4096):
    remaining = size
    while remaining > 0:
        chunk = sock.recv(chunk_size if remaining > chunk_size else remaining)
        if len(chunk) == 0:
            raise ProtocolError('peer disconnected')
        fobj.write(chunk)
        remaining -= len(chunk)


def chunked_send(sock, fobj, size, chunk_size=4096):
    remaining = size
    while remaining > 0:
        chunk = fobj.read(chunk_size)
        sock.sendall(chunk)
        remaining -= len(chunk)


def to_string(b):
    return b.decode('utf-8')


class FileOpsFactory(object):
    @contextmanager
    def open(self, name, flags):
        f = open(name, flags)
        try:
            yield f
        finally:
            f.close()

    def size(self, f):
        return os.stat(f.fileno()).st_size

    def isfile(self, path):
        return os.path.isfile(path)

    def flush(self, f):
        f.flush()

    def close(self, f):
        f.close()

    def remove(self, path):
        os.remove(path)


class DccClient(object):
    def __init__(self, conn,
                 doti,
                 ofile,
                 stdout=sys.stdout.buffer,
                 stderr=sys.stderr.buffer,
                 fileops=FileOpsFactory()):
        self._conn = conn
        self._doti = doti
        self._ofile = ofile
        self._stdout = stdout
        self._stderr = stderr
        self._fileops = fileops
        self._protocol_version = DCC_VERSION

    def request(self, args):
        buf = dcc_encode('DIST', DCC_VERSION)
        buf += dcc_encode('ARGC', len(args))
        for n, arg in enumerate(args):
            argbytes = arg.encode('utf-8')
            buf += dcc_encode('ARGV', len(argbytes))
            buf += argbytes
        with self._fileops.open(self._doti, 'rb') as doti:
            doti_len = self._fileops.size(doti)
            buf += dcc_encode('DOTI', doti_len)
            self._conn.sendall(buf)
            chunked_send(self._conn, doti, doti_len)

    def handle_response(self):
        _, version = read_token(self._conn, b'DONE')
        if version != self._protocol_version:
            raise ProtocolError('unsupported protocol version {}, supported: {}'
                                .format(version, self._protocol_version))
        _, status = read_token(self._conn, b'STAT')

        _, serr_len = read_token(self._conn, b'SERR')
        chunked_read_write(self._conn, self._stderr, serr_len)

        _, sout_len = read_token(self._conn, b'SOUT')
        chunked_read_write(self._conn, self._stdout, sout_len)

        if status != 0:
            return status

        _, doto_len = read_token(self._conn, b'DOTO')
        with self._fileops.open(self._ofile, 'wb') as doto:
            chunked_read_write(self._conn, doto, doto_len)
            self._fileops.flush(doto)
        return status


def dcc_compile(doti, args, host='127.0.0.1', port=3632, ofile='a.out'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        dcc = DccClient(s, doti, ofile)
        dcc.request(args)
        dcc.handle_response()
