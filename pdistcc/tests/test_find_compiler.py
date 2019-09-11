
import pytest

from ..compiler import find_compiler_wrapper
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
