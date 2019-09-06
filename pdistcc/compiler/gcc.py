
import os

from .wrapper import CompilerWrapper
from .errors import UnsupportedCompilationMode

LANG_C = 'c'
LANG_CXX = 'c++'

COMPILER_DIR = 'compiler_dir'


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

    def _is_preprocessed_source_file(self, arg):
        fileext = arg.split('.')[-1].lower()
        return fileext in ('i', 'ii')

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
                cmd.append(self._preprocessed_file)
            else:
                cmd.append(arg)
        return cmd

    def is_preprocessor_flag(self, arg):
        if any(arg.startswith(f) for f in ('-I', '-D')):
            return True, False
        elif arg in ('-MD', '-M'):
            return True, False
        elif arg in ('-MT', '-MF'):
            return True, True
        else:
            return False, False

