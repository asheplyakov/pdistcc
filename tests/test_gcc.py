
import os
import pytest
import sys


thisfile = os.path.realpath(__file__)
thisdir = os.path.dirname(thisfile)
parent_dir = os.path.dirname(thisdir)
new_path = [parent_dir]
new_path.extend([d for d in sys.path if d != thisdir])
sys.path = new_path


from pdistcc.compiler.gcc import GCCWrapper
from pdistcc.compiler.errors import UnsupportedCompilationMode


class TestGCCWrapper(object):

    def test_omits_preprocessor_args(self):
        cmdline = '/usr/bin/g++ -O2 -c -DFOO -o foo.o foo.cpp'.split()
        wrapper = GCCWrapper(cmdline)
        wrapper.can_handle_command()
        preprocessor_cmd = wrapper.preprocessor_cmd()
        remote_cmd = wrapper.compiler_cmd()
        assert wrapper.object_file() == 'foo.o'
        assert wrapper.preprocessed_file() == 'foo.ii'
        assert remote_cmd == '/usr/bin/g++ -O2 -c -o foo.o -x c++ foo.ii'.split()

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


