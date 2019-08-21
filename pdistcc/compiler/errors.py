

class UnsupportedCompiler(BaseException):
    def __init__(self, msg):
        self.msg = msg


class UnsupportedCompilationMode(BaseException):
    def __init__(self, msg):
        self.msg = msg


class PreprocessorFailed(BaseException):
    pass
