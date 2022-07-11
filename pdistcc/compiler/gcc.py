
import os
import subprocess

from .wrapper import CompilerWrapper
from .errors import UnsupportedCompilationMode

LANG_C = 'c'
LANG_CXX = 'c++'

COMPILER_DIR = 'compiler_dir'


def gcc_resolve_triplet(gccpath):
    cmd = [gccpath, '-dumpmachine']
    return subprocess.check_output(cmd).strip()


class GCCWrapper(CompilerWrapper):
    source_file_extensions = ('cpp', 'cxx', 'cc', 'c', 'i', 'ii')
    extension2lang = {
        'c': LANG_C,
    }

    def __init__(self, args, settings={}):
        super().__init__(args)
        self._srcfile = None
        self._objfile = None
        self._preprocessed_file = None
        cfg = settings.get('gcc', {})
        if COMPILER_DIR in cfg:
            compiler = os.path.basename(self._compiler)
            self._compiler = os.path.join(cfg[COMPILER_DIR], compiler)

    def _is_source_file(self, arg):
        fileext = arg.split('.')[-1].lower()
        return fileext in self.source_file_extensions

    def _lang(self):
        srcext = self._srcfile.split('.')[-1].lower()
        return self.extension2lang.get(srcext, LANG_CXX)

    def _preprocessed_filename(self, obj):
        doti_suffix = 'ii' if self._lang() == LANG_CXX else 'i'
        doti = obj.split('.')[:-1] + [doti_suffix]
        return '.'.join(doti)

    def can_handle_command(self):
        source_count = 0
        is_object_compilation = False
        has_object_file = False

        skip_next_arg = False
        for n, arg in enumerate(self._args):
            if skip_next_arg:
                skip_next_arg = False
                continue
            if arg == '-c':
                is_object_compilation = True
            elif arg == '-x':
                skip_next_arg = True
                continue
            elif self._is_source_file(arg):
                source_count += 1
                self._srcfile = arg
            elif arg == '-o':
                skip_next_arg = True
                if n + 1 < len(self._args):
                    self._objfile = self._args[n + 1]
                    has_object_file = True

        if source_count == 0:
            raise UnsupportedCompilationMode('no source files')
        if source_count > 1:
            raise UnsupportedCompilationMode('multiple sources')
        if not is_object_compilation:
            raise UnsupportedCompilationMode('linking')
        if not has_object_file:
            raise UnsupportedCompilationMode('output object not specified')

    def preprocessor_cmd(self):
        cmd = [self._compiler]
        next_arg_is_object = False

        for arg in self._args:
            skip_arg = False
            if '-c' == arg:
                cmd.extend(['-E'])
                skip_arg = True
            elif next_arg_is_object:
                self._objfile = arg
                self._preprocessed_file = self._preprocessed_filename(arg)
                cmd.append(self._preprocessed_file)
                next_arg_is_object = False
                skip_arg = True
            elif '-o' == arg:
                next_arg_is_object = True
            else:
                pass
            if not skip_arg:
                cmd.append(arg)
        return cmd

    def set_source_file(self, srcfile):
        if srcfile == self._srcfile:
            return
        args = [a if a != self._srcfile else srcfile for a in self._args]
        self._args = args
        self._srcfile = srcfile

    def set_object_file(self, objfile):
        if objfile == self._objfile:
            return
        args = [a if a != self._objfile else objfile for a in self._args]
        self._args = args
        self._objfile = objfile

    def object_file(self):
        if self._objfile is None:
            for n, arg in enumerate(self._args):
                if arg == '-o' and n + 1 < len(self._args):
                    self._objfile = self._args[n + 1]
                    break
        return self._objfile

    def preprocessed_file(self):
        return self._preprocessed_file

    def set_preprocessed_file(self, path):
        self._preprocessed_file = path

    def source_file(self):
        return self._srcfile

    def compiler_cmd(self):
        cmd = [self._compiler]
        skip, skip_next = False, False
        for arg in self._args:
            if skip_next:
               skip_next = False
               continue
            skip, skip_next = self.is_preprocessor_flag(arg)
            if skip:
                continue
            elif arg == self._srcfile:
                if '-x' not in self._args:
                    # explicitly specify source language
                    cmd.extend(['-x', self._lang()])
                cmd.append(self._preprocessed_file)
            else:
                cmd.append(arg)
        return cmd

    def called_for_preprocessing(self):
        return '-E' in self._args

    def is_preprocessor_flag(self, arg):
        if arg.startswith('-D'):
            return True, False
        elif arg == '-I':
            return True, True
        elif arg.startswith('-I'):
            return True, False
        elif arg.startswith('-Wp,'):
            return True, False
        elif arg == '-Xpreprocessor':
            return True, True
        elif arg in ('-MD', '-M', '-nostdinc'):
            return True, False
        elif arg in ('-MT', '-MF'):
            return True, True
        elif arg in ('-include', '-imacro', '-iquote', '-isystem'):
            return True, True
        else:
            return False, False

    def _resolve_march_native(self, flag='-march'):
        cmd = [self._compiler, f'{flag}=native', '-Q', '--help=target']
        out = subprocess.check_output(cmd, encoding='utf-8').strip()
        for line in out.split('\n'):
            if line.strip().startswith(f"{flag}="):
                return ''.join(line.split())
        raise RuntimeError(f"Failed to resolve {flag}=native")

    def rewrite_local_args(self):
        new_args = []
        for arg in self._args:
            if arg == "-march=native" or arg == "-mcpu=native":
                new_arg = self._resolve_march_native(flag="-march")
                print(f"rewritten {arg} as {new_arg}")
            elif arg == "-mtune":
                new_arg = self._resolve_march_native(flag="-mtune")
                print(f"rewritten {arg} as {new_arg}")
            else:
                new_arg = arg
            new_args.append(new_arg)
        self._args = new_args
