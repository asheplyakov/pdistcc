
import os
import socket
import sys


DCC_TOKEN_HEADER_LEN = 12
DCC_VERSION = 1


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
