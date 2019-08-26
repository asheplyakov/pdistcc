
import os
import socket
import sys


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


def chunked_read_write(sock, fobj, size, chunk_size=4096):
    remaining = size
    while remaining > 0:
        chunk = sock.recv(chunk_size if remaining > chunk_size else remaining)
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


def dcc_compile(doti, args, host='127.0.0.1', port=3632, ofile='a.out'):

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
            chunked_send(s, f, doti_len)

    def handle_response(s):
        greeting, version, _ = read_field(s, False)
        if greeting != b'DONE' or version != 1:
            raise InvalidToken('expected DONE, got "{}"', to_string(greeting))

        field, status, _ = read_field(s, False)
        if field != b'STAT':
            raise InvalidToken('expected STAT, got "{}"', to_string(field))

        field, flen, _ = read_field(s, False)
        if field != b'SERR':
            raise InvalidToken('expected SERR, got "{}"', to_string(field))
        chunked_read_write(s, sys.stderr.buffer, flen)

        field, flen, _ = read_field(s, False)
        if field != b'SOUT':
            raise InvalidToken('expected SOUT, got "{}"', to_string(field))
        chunked_read_write(s, sys.stdout.buffer, flen)

        if status != 0:
            sys.exit(status)

        field, flen, _ = read_field(s, False)
        if field != b'DOTO':
            raise InvalidToken('expected DOTO, got "{}"' % to_string(field))

        with open(ofile, 'wb') as aout:
            chunked_read_write(s, aout, flen)
            aout.flush()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        request(s)
        handle_response(s)
