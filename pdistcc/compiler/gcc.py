
from .wrapper import CompilerWrapper
from .errors import UnsupportedCompilationMode

LANG_C = 'c'
LANG_CXX = 'c++'


class GCCWrapper(CompilerWrapper):
    source_file_extensions = ('cpp', 'cxx', 'cc', 'c')
    extension2lang = {
        'c': LANG_C,
    }

    def __init__(self, args):
        super().__init__(args)
        self._srcfile = None
        self._objfile = None
        self._preprocessed_file = None

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
        for arg in self._args:
            if skip_next_arg:
                skip_next_arg = False
                continue
            if arg == '-c':
                is_object_compilation = True
            elif self._is_source_file(arg):
                source_count += 1
                self._srcfile = arg
            elif arg == '-o':
                has_object_file = True
                skip_next_arg = True

        if source_count != 1:
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

    def object_file(self):
        return self._objfile

    def preprocessed_file(self):
        return self._preprocessed_file

    def source_file(self):
        return self._srcfile

    def compiler_cmd(self):
        cmd = [self._compiler]
        for arg in self._args:
            if arg != self._srcfile:
                cmd.append(arg)
            else:
                cmd.append(self._preprocessed_file)
        return cmd
