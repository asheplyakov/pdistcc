
import io
import pytest


from .fakeops import (
    FakeFileOpsFactory,
    FakeSocket,
)

from ..net import (
    DccClient,
    InvalidToken,
    ProtocolError,
    chunked_read_write,
    dcc_decode,
    dcc_encode,
    read_token,
)


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


def test_read_token_short_xfail():
    sock = FakeSocket(b'DIST0')
    with pytest.raises(ProtocolError):
        read_token(sock, b'DIST')


def test_read_token_unexpected_xfail():
    sock = FakeSocket(b'DIST00000001')
    with pytest.raises(InvalidToken):
        read_token(sock, b'ARGC')


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
    fileFactory = FakeFileOpsFactory({'dot.o': b''}, close=False)
    dcc = DccClient(sock,
                    'hello.ii',
                    'dot.o',
                    stdout=stdout,
                    stderr=stderr,
                    fileops=fileFactory)
    ret = dcc.handle_response()
    assert ret == 0
    assert fileFactory._vfs['dot.o'].getvalue() == fakeobj


def test_dcc_compilation_failed():
    stdout = io.BytesIO(b'')
    stderr = io.BytesIO(b'')
    sock = FakeSocket(b''.join([
        dcc_encode('DONE', 1),
        dcc_encode('STAT', 1),
        dcc_encode('SERR', len(b'error')),
        b'error',
        dcc_encode('SOUT', len(b'text')),
        b'text',
    ]))
    fileFactory = FakeFileOpsFactory({}, close=False)
    dcc = DccClient(sock,
                    'hello.ii',
                    'dot.o',
                    stdout=stdout,
                    stderr=stderr,
                    fileops=fileFactory)
    ret = dcc.handle_response()
    assert ret == 1
    assert 'dot.o' not in fileFactory._vfs
    assert stdout.getvalue() == b'text'
    assert stderr.getvalue() == b'error'


def test_dcc_junk():
    sock = FakeSocket(b''.join([
        dcc_encode('BARF', 123),
        b'XY',
    ]))
    dcc = DccClient(sock,
                    'hello.ii',
                    'hello.o',
                    stdout=io.BytesIO(),
                    stderr=io.BytesIO(),
                    fileops=FakeFileOpsFactory())
    with pytest.raises(InvalidToken):
        dcc.handle_response()


def test_dcc_unsupported_protocol_version_xfail():
    sock = FakeSocket(b'DONE00000002')
    dcc = DccClient(sock,
                    'hello.ii',
                    'dot.o',
                    stdout=io.BytesIO(),
                    stderr=io.BytesIO(),
                    fileops=FakeFileOpsFactory())
    with pytest.raises(ProtocolError):
        dcc.handle_response()


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
    assert sock._write.getvalue() == b''.join([
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
