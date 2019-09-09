
import io
import os
import pytest
import sys

from contextlib import contextmanager


thisfile = os.path.realpath(__file__)
thisdir = os.path.dirname(thisfile)
parent_dir = os.path.dirname(thisdir)
new_path = [parent_dir]
new_path.extend([d for d in sys.path if d != thisdir])
sys.path = new_path


from pdistcc.net import (
    DccClient,
    InvalidToken,
    chunked_read_write,
    dcc_decode,
    dcc_encode,
)


class FakeFileOpsFactory(object):
    def __init__(self, vfs={}):
        self._vfs = vfs

    @contextmanager
    def open(self, name, flags):
        f = io.BytesIO(self._vfs.get(name, b''))
        self._vfs[name] = f
        try:
            yield f
        finally:
            pass

    def size(self, f):
        return len(f.getvalue())

    def flush(self, f):
        pass

    def close(self, f):
        f.close()


class FakeSocket(io.BytesIO):
    def __init__(self, initial=b''):
        super().__init__(initial)

    def send(self, what):
        return self.write(what)

    def sendall(self, what):
        size = len(what)
        sent = 0
        while sent < size:
            sent += self.write(what[sent:])

    def recv(self, size):
        return self.read(size)


def test_dcc_encode():
    size = 31
    b = dcc_encode('SERR', size)
    assert b == b'SERR' + b'0000001f'


def test_dcc_decode():
    raw = b'SERR' + b'000000aa'
    name, val = dcc_decode(raw)
    assert name == b'SERR'
    assert val == 170


def test_decode_rejects_short():
    with pytest.raises(InvalidToken):
        name, size = dcc_decode(b'DIST0')


def test_decode_rejects_long():
    with pytest.raises(InvalidToken):
        name, size = dcc_decode(b'DIST' + b'0'*12)


def test_chunked_read_write_small():
    size = 1024
    fobj = io.BytesIO()
    sock = FakeSocket(b'a' * size)
    chunked_read_write(sock, fobj, size)
    assert fobj.getvalue() == b'a' * size


def test_chunked_read_write_large():
    size = 10000
    fobj = io.BytesIO()
    sock = FakeSocket(b'a' * size)
    chunked_read_write(sock, fobj, size)
    assert fobj.getvalue() == b'a' * size


def test_dcc_reply_success():
    stdout = io.BytesIO(b'')
    stderr = io.BytesIO(b'')
    fakeobj = b'FAKEELF'
    sock = FakeSocket(b''.join([
        dcc_encode('DONE', 1),
        dcc_encode('STAT', 0),
        dcc_encode('SERR', len(b'test')),
        b'test',
        dcc_encode('SOUT', len(b'test')),
        b'test',
        dcc_encode('DOTO', len(fakeobj)),
        fakeobj,
    ]))
    fileFactory = FakeFileOpsFactory({
        'dot.o': b'',
    })
    dcc = DccClient(sock,
                    'hello.ii',
                    'dot.o',
                    stdout=stdout,
                    stderr=stderr,
                    fileops=fileFactory)
    ret = dcc.handle_response()
    assert ret == 0
    assert fileFactory._vfs['dot.o'].getvalue() == fakeobj


def test_dcc_request1():
    stdout = io.StringIO('')
    stderr = io.StringIO('')
    sock = FakeSocket()
    source = b'int f(int x, int y) { return x + y; }'
    doti = 'hello.ii'
    doto = 'hello.o'
    fileFactory = FakeFileOpsFactory({
        doti: source,
        doto: b'',
    })
    dcc = DccClient(sock,
                    'hello.ii',
                    'a.o',
                    stdout=stdout,
                    stderr=stderr,
                    fileops=fileFactory)
    cmd = 'g++ -c -o {} -x c++ {}'.format(doto, doti).split()
    dcc.request(cmd)
    assert sock.getvalue() == b''.join([
        b'DIST00000001',
        b'ARGC00000007',
        b'ARGV00000003' + b'g++',
        b'ARGV00000002' + b'-c',
        b'ARGV00000002' + b'-o',
        b'ARGV00000007' + b'hello.o',
        b'ARGV00000002' + b'-x',
        b'ARGV00000003' + b'c++',
        b'ARGV00000008' + b'hello.ii',
        dcc_encode('DOTI', len(source)),
        source,
    ])
