
import os
from .gcc import GCCWrapper
from .errors import UnsupportedCompiler


def wrap_compiler(host, port, compiler_cmd):
    compiler_name = os.path.basename(compiler_cmd[0])
    if compiler_name in ('gcc', 'g++'):
        wrapper = GCCWrapper(compiler_cmd)
    else:
        raise UnsupportedCompiler(compiler_name)
    wrapper.wrap_compiler(host, port)
