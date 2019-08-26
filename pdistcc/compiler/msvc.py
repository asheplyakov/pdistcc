
import sys
from .wrapper import CompilerWrapper
from .errors import UnsupportedCompilationMode as UCM


LANG_C = 'c'
LANG_CXX = 'c++'


class MSVCWrapper(CompilerWrapper):
    # FIXME: for now this supports only clang-cl on the remote side.
    # A real msvc needs tons of environment variables to work properly.

    def __init__(self, args, settings={}):
        super().__init__(args)
        self._srcfile = None
        self._objfile = None
        self._preprocessed_file = None
        cfg = settings.get('msvc', {})
        self._distcc_compat = cfg.get('distcc_compat', False)
        self._use_clang = cfg.get('use_clang', sys.platform != 'win32')
        self._clang_path = cfg.get('clang_path',
                                   'clang-cl' if self._use_clang else None)

    @property
    def clang_path(self):
        return self._clang_path

    @property
    def use_clang(self):
        return self._use_clang

    @clang_path.setter
    def clang_path(self, value):
        self._clang_path = value
        if value:
            self._use_clang = True

    @property
    def distcc_compat(self):
        return self._distcc_compat

    @distcc_compat.setter
    def distcc_compat(self, val):
        self._distcc_compat = val

    def _is_source_file(self, path):
        ext = path.split('.')[-1].lower()
        return ext in ('c', 'cpp', 'cc', 'cxx', 'i', 'ii')

    def _is_preprocessed_source_file(self, path):
        ext = path.split('.')[-1].lower()
        return ext in ('i', 'ii')

    def can_handle_command(self):
        source_count = 0
        is_object_compilation = False
        has_object_file = False

        skip_next_arg = False
        for arg in self._args:
            if skip_next_arg:
                skip_next_arg = False
                continue
            if arg in ('/c', '-c'):
                is_object_compilation = True
            elif arg[0] == '@':
                raise UCM('Response files are not supported')
            elif arg in ('/Zi', '/ZI'):
                raise UCM('PDB generation is not supported')
            elif arg.startswith("/Fo"):
                has_object_file = True
                self._objfile = arg[3:]
            elif arg.startswith('/MP'):
                raise UCM('Multiprocessing mode is unsupported')
            elif self._is_source_file(arg):
                self._srcfile = arg
                source_count += 1

        if source_count > 1:
            raise UCM('Multiple source files')
        elif source_count == 0:
            raise UCM('No source files')
        if not (is_object_compilation and has_object_file):
            raise UCM('Only compilation of a single source file is supported')

    def _preprocessed_filename(self):
        objname_woext = self._objfile.split('.')[:-1]
        objname_woext.append('i')
        self._preprocessed_file = objname_woext.join('.')
        return self._preprocessed_file

    def preprocessor_cmd(self):
        cmd = [self._compiler]
        for arg in self._args:
            skip_arg = False
            if arg in ('/c', '/E', '-c'):
                skip_arg = True
                skip_arg = True
            elif arg.startswith('/Fo'):
                skip_arg = True
                self._objfile = arg[3:]
                cmd.extend(['/P', '/Fi{}'.format(self.preprocessed_file())])
            if not skip_arg:
                cmd.append(arg)
        return cmd

    def _lang(self):
        srcext = self._srcfile.split('.')[-1].lower()
        return LANG_C if srcext == 'c' else LANG_CXX

    def compiler_cmd(self):
        cmd = [self._compiler if not self._use_clang else self._clang_path]
        for arg in self._args:
            if arg == '/c':
                # XXX: distcc
                cmd.append('-c' if self._distcc_compat else '/c')
            elif arg == self._srcfile:
                cmd.append('/TP' if self._lang() == LANG_CXX else '/TC')
                cmd.append(self._preprocessed_file)
            else:
                cmd.append(arg)
        return cmd

    def object_file(self):
        return self._objfile

    def set_object_file(self, objfile):
        if objfile == self._objfile:
            return
        args = [a if not a.startswith('/Fo') else '/Fo{}'.format(objfile)
                for a in self._args]
        self._args = args
        self._objfile = objfile

    def preprocessed_file(self):
        if self._preprocessed_file is None:
            objname_woext = self._objfile.split('.')[:-1]
            objname_woext.append('i')
            self._preprocessed_file = '.'.join(objname_woext)
        return self._preprocessed_file

    def set_preprocessed_file(self, path):
        self._preprocessed_file = path

    def source_file(self):
        return self._srcfile

    def set_source_file(self, srcfile):
        if srcfile == self._srcfile:
            return
        new_args = [a if a != self._srcfile else srcfile for a in self._args]
        self._args = new_args
        self._srcfile = srcfile
