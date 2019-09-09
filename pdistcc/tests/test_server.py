
import subprocess

from unittest.mock import MagicMock

from .fakeops import (
    FakeFileOpsFactory,
    FakeSocket,
    FakeTempFileFactory,
)

from ..server import (
    Distccd
)


def test_distccd_normal():
    source = b'int f(int x,int y){return x+y;}'
    job = b''.join([
        b'DIST', b'00000001',
        b'ARGC', b'00000005',
        b'ARGV', b'00000003', b'gcc',
        b'ARGV', b'00000002', b'-c',
        b'ARGV', b'00000002', b'-o',
        b'ARGV', b'00000005', b'foo.o',
        b'ARGV', b'00000005', b'foo.c'
        b'DOTI', b'0000001f', source,
    ])
    # network communication
    sock = FakeSocket(job)

    # running the compiler
    mock_popen = MagicMock()
    mock_popen.return_value.communicate.return_value = (b'SOUT', b'SERR')
    mock_popen.return_value.returncode = 0

    # simulate the compiler output
    fileops = FakeFileOpsFactory({'foo_1.o': b'FAKE'})

    # temporary files
    faketempfile = FakeTempFileFactory(['foo_0.ii', 'foo_1.o'])

    handler = Distccd({}, sock, ('127.0.0.1', '3632'), {},
                      fileops=fileops,
                      tempfile=faketempfile,
                      popen=mock_popen)
    compiler_cmd = 'gcc -c -o foo_1.o -x c foo_0.ii'.split()

    mock_popen.assert_called_once_with(compiler_cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
    faketempfile.file(0).seek(0)
    assert faketempfile.file(0).getvalue() == source
    assert sock._write.getvalue() == b''.join([
        b'DONE', b'00000001',
        b'STAT', b'00000000',
        b'SERR', b'00000004', b'SERR',
        b'SOUT', b'00000004', b'SOUT',
        b'DOTO', b'00000004', b'FAKE',
    ])
