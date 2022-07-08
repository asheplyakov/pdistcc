
import os
import re
import subprocess

from .errors import (
        UnsupportedCompiler,
        UnsupportedCompilationMode,
)
from .gcc import GCCWrapper
from .msvc import MSVCWrapper
from ..sched import pick_server


def find_compiler_wrapper(compiler_cmd, settings={}):
    compiler_name = os.path.basename(compiler_cmd[0])
    if compiler_name in ('gcc', 'g++', 'c++'):
        wrapper = GCCWrapper(compiler_cmd, settings)
    elif re.match('^.*-gcc(-[0-9.]+)*$', compiler_name):
        wrapper = GCCWrapper(compiler_cmd, settings)
    elif re.match('^.*-g[+][+](-[0-9.]+)*$', compiler_name):
        wrapper = GCCWrapper(compiler_cmd, settings)
    elif compiler_name in ('cl', 'clang-cl', 'cl.exe', 'clang-cl.exe'):
        wrapper = MSVCWrapper(compiler_cmd, settings)
    else:
        raise UnsupportedCompiler(compiler_name)
    return wrapper


def wrap_compiler(distcc_hosts, compiler_cmd, settings={}):
    host = pick_server(distcc_hosts, tuple(compiler_cmd))
    if host['host'] == 'localhost':
        subprocess.check_call(compiler_cmd)
    else:
        wrapper = find_compiler_wrapper(compiler_cmd, settings)
        try:
            wrapper.wrap_compiler(host['host'], host['port'])
        except UnsupportedCompilationMode:
            # called for linking, etc
            subprocess.check_call(compiler_cmd)
