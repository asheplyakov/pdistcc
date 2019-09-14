
import os

from contextlib import contextmanager


class FileOpsFactory(object):
    @contextmanager
    def open(self, name, flags):
        f = open(name, flags)
        try:
            yield f
        finally:
            f.close()

    def size(self, f):
        return os.stat(f.fileno()).st_size

    def isfile(self, path):
        return os.path.isfile(path)

    def flush(self, f):
        f.flush()

    def close(self, f):
        f.close()

    def remove(self, path):
        os.remove(path)
