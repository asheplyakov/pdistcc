
import pdistcc
import pytest

from pytest_mock import mocker

from ..compiler import (
    find_compiler_wrapper,
    wrap_compiler,
)
from ..compiler.gcc import GCCWrapper
from ..compiler.msvc import MSVCWrapper
from ..compiler.errors import UnsupportedCompiler


def test_find_gcc():
    cmd = 'gcc -c -o foo.o foo.c'.split()
    wrapper = find_compiler_wrapper(cmd)
    assert isinstance(wrapper, GCCWrapper)


def test_find_msvc():
    cmd = 'cl.exe /c /Fofoo.obj foo.c'.split()
    wrapper = find_compiler_wrapper(cmd)
    assert isinstance(wrapper, MSVCWrapper)


def test_unknown_compiler():
    cmd = 'barf foo buzz'.split()
    with pytest.raises(UnsupportedCompiler):
        find_compiler_wrapper(cmd)


def test_wrap_compiler(mocker):
    mocker.patch('pdistcc.compiler.find_compiler_wrapper')
    wrapper_mock = mocker.MagicMock()
    wrapper_mock.wrap_compiler = mocker.MagicMock()
    pdistcc.compiler.find_compiler_wrapper.return_value = wrapper_mock
    mocker.patch('pdistcc.compiler.pick_server')
    pdistcc.compiler.pick_server.return_value = {
        'host': 'localhost',
        'port': 11111,
    }
    distcc_hosts = [
            {'host': 'a', 'port': 1234},
            {'host': 'localhost', 'port': 11111},
    ]
    wrap_compiler(distcc_hosts, 'gcc -c -o foo.o foo.c'.split())
    pdistcc.compiler.find_compiler_wrapper.assert_called_once_with(
        'gcc -c -o foo.o foo.c'.split(),
        {}
    )
    pdistcc.compiler.pick_server.assert_called_once_with(
        distcc_hosts,
        tuple('gcc -c -o foo.o foo.c'.split()),
    )
    wrapper_mock.wrap_compiler.assert_called_once_with('localhost', 11111)
