
import os
from .gcc import GCCWrapper
from .msvc import MSVCWrapper
from .errors import UnsupportedCompiler


def find_compiler_wrapper(compiler_cmd):
    compiler_name = os.path.basename(compiler_cmd[0])
    if compiler_name in ('gcc', 'g++'):
        wrapper = GCCWrapper(compiler_cmd)
    elif compiler_name in ('cl', 'clang-cl', 'cl.exe', 'clang-cl.exe'):
        wrapper = MSVCWrapper(compiler_cmd)
    else:
        raise UnsupportedCompiler(compiler_name)
    return wrapper


def wrap_compiler(host, port, compiler_cmd):
    wrapper = find_compiler_wrapper(compiler_cmd)
    wrapper.wrap_compiler(host, port)
