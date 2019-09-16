
import pytest

from ..compiler.gcc import GCCWrapper
from ..compiler.errors import UnsupportedCompilationMode


class TestGCCWrapper(object):

    def test_accepts_single_compile(self):
        cmdline = 'g++ -c -o foo.o foo.cpp'.split()
        wrapper = GCCWrapper(cmdline)
        wrapper.can_handle_command()
        wrapper.preprocessor_cmd()
        remote_cmd = wrapper.compiler_cmd()
        assert remote_cmd == 'g++ -c -o foo.o -x c++ foo.ii'.split()

    def test_handles_c(self):
        cmdline = 'gcc -c -o foo.o foo.c'.split()
        wrapper = GCCWrapper(cmdline)
        wrapper.can_handle_command()
        wrapper.preprocessor_cmd()
        remote_cmd = wrapper.compiler_cmd()
        assert remote_cmd == 'gcc -c -o foo.o -x c foo.i'.split()

    def test_handles_x_cxx(self):
        cmdline = 'g++ -c -o foo.o -x c++ foo.cpp'.split()
        wrapper = GCCWrapper(cmdline)
        wrapper.can_handle_command()
        wrapper.preprocessor_cmd()
        remote_cmd = wrapper.compiler_cmd()
        assert remote_cmd == 'g++ -c -o foo.o -x c++ foo.ii'.split()

    @pytest.mark.parametrize("arg", ['-DFOO', '-Ibar', '-M', '-MD'])
    def test_omits_preprocessor_args(self, arg):
        cmdline = 'g++ -O2 -c {} -o foo.o foo.cpp'.format(arg).split()
        wrapper = GCCWrapper(cmdline)
        wrapper.can_handle_command()
        wrapper.preprocessor_cmd()
        remote_cmd = wrapper.compiler_cmd()
        assert arg not in remote_cmd

    def test_rejects_linking(self):
        cmdline = '/usr/bin/g++ -O2 -o foo foo.cpp'.split()
        wrapper = GCCWrapper(cmdline)
        with pytest.raises(UnsupportedCompilationMode):
            wrapper.can_handle_command()

    def test_rejects_multiple_sources(self):
        cmdline = '/usr/bin/g++ -O2 -c bar.cpp foo.cpp'.split()
        wrapper = GCCWrapper(cmdline)
        with pytest.raises(UnsupportedCompilationMode):
            wrapper.can_handle_command()

    def test_skips_includes_remote(self):
        cmdline = 'g++ -c -DFOO -o foo.o foo.cpp'.split()
        wrapper = GCCWrapper(cmdline)
        wrapper.can_handle_command()
        wrapper.set_preprocessed_file('foo.ii')
        assert wrapper.preprocessed_file() == 'foo.ii'
        assert wrapper.compiler_cmd() == 'g++ -c -o foo.o -x c++ foo.ii'.split()

    def test_skips_MT_remote(self):
        cmdline = 'g++ -c -MT foo.o -o foo.o foo.cpp'.split()
        wrapper = GCCWrapper(cmdline)
        wrapper.can_handle_command()
        wrapper.set_preprocessed_file('foo.ii')
        assert wrapper.preprocessed_file() == 'foo.ii'
        assert wrapper.compiler_cmd() == 'g++ -c -o foo.o -x c++ foo.ii'.split()


def test_linking_xfail():
    wrapper = GCCWrapper('gcc foo.c'.split())
    with pytest.raises(UnsupportedCompilationMode):
        wrapper.can_handle_command()


def test_no_object_files_xfail():
    wrapper = GCCWrapper('gcc -c foo.c'.split())
    with pytest.raises(UnsupportedCompilationMode):
        wrapper.can_handle_command()


def test_no_sources_xfail():
    wrapper = GCCWrapper('gcc -c -o foo.o'.split())
    with pytest.raises(UnsupportedCompilationMode):
        wrapper.can_handle_command()


def test_compiler_dir():
    settings = {
        'gcc': {
            'compiler_dir': '/opt/rh/bin',
        },
    }
    wrapper = GCCWrapper('gcc -c -o foo.o foo.c'.split(), settings=settings)
    wrapper.can_handle_command()
    assert wrapper.preprocessor_cmd() == '/opt/rh/bin/gcc -E -o foo.i foo.c'.split()
    assert wrapper.compiler_cmd() == '/opt/rh/bin/gcc -c -o foo.o -x c foo.i'.split()
