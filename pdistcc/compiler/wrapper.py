
import subprocess
from ..net import dcc_compile
from .errors import PreprocessorFailed

LANG_C = 'c'
LANG_CXX = 'c++'


class CompilerWrapper(object):
    def __init__(self, args):
        self._args = args[1:]
        self._compiler = args[0]

    def wrap_compiler(self, host, port):
        self.can_handle_command()
        if self.called_for_preprocessing():
            args = [self._compiler]
            args.extend(self._args)
            subprocess.check_call(args)
            return
        preprocessor_cmd = self.preprocessor_cmd()
        try:
            subprocess.check_output(preprocessor_cmd)
        except subprocess.CalledProcessError:
            raise PreprocessorFailed()

        dcc_compile(self.preprocessed_file(),
                    self.compiler_cmd(),
                    host=host,
                    port=port,
                    ofile=self.object_file())
