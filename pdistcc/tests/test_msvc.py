
import pytest

from ..compiler.msvc import MSVCWrapper
from ..compiler.errors import UnsupportedCompilationMode


class TestMSVCWrapper(object):
    def test_rejects_pdb(self):
        cmdline = 'cl.exe /Zi /c /Fofoo.obj foo.cpp'.split()
        wrapper = MSVCWrapper(cmdline)
        with pytest.raises(UnsupportedCompilationMode):
            wrapper.can_handle_command()

    def test_reject_multiple_sources(self):
        cmdline = 'cl.exe /c /Foproj\ foo.cpp bar.cpp'.split()
        wrapper = MSVCWrapper(cmdline)
        with pytest.raises(UnsupportedCompilationMode):
            wrapper.can_handle_command()

    def test_positive(self):
        cmdline = 'cl.exe /c /Fofoo.obj /Z7 /O2 foo.cpp'.split()
        wrapper = MSVCWrapper(cmdline)
        wrapper.can_handle_command()

    def test_accepts_debug(self):
        cmdline = 'cl.exe /c /Fofoo.obj /Z7 /O2 foo.cpp'.split()
        wrapper = MSVCWrapper(cmdline)
        wrapper.can_handle_command()

    def test_object_file(self):
        cmdline = 'cl.exe /c /Fofoo.obj foo.cpp'.split()
        wrapper = MSVCWrapper(cmdline)
        wrapper.can_handle_command()
        assert wrapper.object_file() == 'foo.obj'

    def test_source_file(self):
        cmdline = 'cl.exe /c /Fofoo.obj foo.cpp'.split()
        wrapper = MSVCWrapper(cmdline)
        wrapper.can_handle_command()
        assert wrapper.source_file() == 'foo.cpp'

    def test_preprocessor_cmd(self):
        cmdline = 'cl.exe /c /Fofoo.obj foo.cpp'.split()
        wrapper = MSVCWrapper(cmdline)
        wrapper.can_handle_command()
        preprocessor = wrapper.preprocessor_cmd()
        assert preprocessor == 'cl.exe /P /Fifoo.i foo.cpp'.split()

    def _compiler_cmd(self, native):
        cmdline = 'cl.exe /c /Fofoo.obj foo.cpp'.split()
        settings = {'msvc': {'use_clang': not native}}
        wrapper = MSVCWrapper(cmdline, settings)
        wrapper.can_handle_command()
        wrapper.preprocessor_cmd()
        return wrapper

    def test_compiler_cmd_native(self):
        wrapper = self._compiler_cmd(True)
        compiler_cmd = wrapper.compiler_cmd()
        assert compiler_cmd == 'cl.exe /c /Fofoo.obj /TP foo.i'.split()

    def test_compiler_cmd_clang_cl(self):
        wrapper = self._compiler_cmd(False)
        compiler_cmd = wrapper.compiler_cmd()
        assert compiler_cmd == 'clang-cl /c /Fofoo.obj /TP foo.i'.split()

    def test_set_preprocessed_file(self):
        cmdline = 'cl.exe /c /Fofoo.obj /TP foo.i'.split()
        settings = {'msvc': {'use_clang': True}}
        wrapper = MSVCWrapper(cmdline, settings)
        wrapper.can_handle_command()
        wrapper.set_preprocessed_file('/tmp/fooXYZ.i')
        assert wrapper.preprocessed_file() == '/tmp/fooXYZ.i'
        compiler_cmd = wrapper.compiler_cmd()
        assert compiler_cmd == 'clang-cl /c /Fofoo.obj /TP /tmp/fooXYZ.i'.split()

    def test_set_object_file(self):
        cmdline = 'cl.exe /c /Fofoo.obj foo.cpp'.split()
        settings = {'msvc': {'use_clang': False}}
        wrapper = MSVCWrapper(cmdline, settings)
        wrapper.can_handle_command()
        wrapper.set_preprocessed_file('foo.ii')
        wrapper.set_object_file('C:\\tmp\\fooXYZ.obj')
        assert wrapper.object_file() == 'C:\\tmp\\fooXYZ.obj'
        compiler_cmd = wrapper.compiler_cmd()
        assert compiler_cmd == 'cl.exe /c /FoC:\\tmp\\fooXYZ.obj /TP foo.ii'.split()

    def test_skips_defines(self):
        cmdline = 'cl.exe /c /DFOO=BAR /Fofoo.obj /D_X=Y foo.cpp'.split()
        settings = {'msvc': {'use_clang': False}}
        wrapper = MSVCWrapper(cmdline, settings)
        wrapper.can_handle_command()
        wrapper.set_preprocessed_file('foo.ii')
        assert wrapper.compiler_cmd() == 'cl.exe /c /Fofoo.obj /TP foo.ii'.split()


def test_no_sources_xfail():
    wrapper = MSVCWrapper('cl.exe /c /Fofoo.obj'.split())
    with pytest.raises(UnsupportedCompilationMode):
        wrapper.can_handle_command()


def test_linking_xfail():
    wrapper = MSVCWrapper('cl.exe foo.c'.split())
    with pytest.raises(UnsupportedCompilationMode):
        wrapper.can_handle_command()


def test_response_file_xfail():
    wrapper = MSVCWrapper('cl.exe /c /Fofoo.o foo.c @options.txt'.split())
    with pytest.raises(UnsupportedCompilationMode):
        wrapper.can_handle_command()


def test_fd_without_debuginfo():
    settings = {'msvc': {'use_clang': False}}
    wrapper = MSVCWrapper('cl.exe /c /Fofoo.o foo.c /Fdfoo.pdb'.split(),
                          settings=settings)
    wrapper.can_handle_command()
    preprocessor_cmd = wrapper.preprocessor_cmd()
    assert preprocessor_cmd == 'cl.exe /P /Fifoo.i foo.c'.split()
    assert wrapper.compiler_cmd() == 'cl.exe /c /Fofoo.o /TC foo.i'.split()


def test_mp_xfail():
    wrapper = MSVCWrapper('cl.exe /c /Fofoo.o foo.c /MP4'.split(),
                          settings={'msvc': {'use_clang': False}})
    with pytest.raises(UnsupportedCompilationMode):
        wrapper.can_handle_command()


def test_use_clang():
    cmdline = 'cl.exe /c /Fofoo.obj foo.cpp'.split()
    settings = {
        'msvc': {
            'clang_path': 'D:/bin/clang-cl.exe',
            'use_clang': True,
        }
    }
    wrapper = MSVCWrapper(cmdline, settings=settings)
    wrapper.can_handle_command()
    assert wrapper.preprocessor_cmd() == 'cl.exe /P /Fifoo.i foo.cpp'.split()
    assert wrapper.compiler_cmd() == 'D:/bin/clang-cl.exe /c /Fofoo.obj /TP foo.i'.split()
