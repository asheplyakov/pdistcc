
import os
import pytest
import sys

thisfile = os.path.realpath(__file__)
thisdir = os.path.dirname(thisfile)
parent_dir = os.path.dirname(thisdir)
new_path = [parent_dir]
new_path.extend([d for d in sys.path if d != thisdir])
sys.path = new_path


from pdistcc.compiler.msvc import MSVCWrapper
from pdistcc.compiler.errors import UnsupportedCompilationMode


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
        preprocessor = wrapper.preprocessor_cmd()
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
