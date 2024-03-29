
import io

from contextlib import contextmanager


class FakeSocket(object):
    def __init__(self, initial=b''):
        self._read = io.BytesIO(initial)
        self._write = io.BytesIO()

    def send(self, data):
        return self._write.write(data)

    def recv(self, size):
        return self._read.read(size)

    def recv_into(self, buf, size=0):
        if size == 0:
            return self._read.readinto(buf)
        else:
            with memoryview(buf) as mv:
                with mv[:size] as submv:
                    return self._read.readinto(submv)

    def sendall(self, data):
        sent = 0
        while sent < len(data):
            sent += self.send(data[sent:])


class FakeFileOpsFactory(object):
    def __init__(self, vfs={}):
        self._vfs = vfs

    @contextmanager
    def open(self, name, flags):
        content = self._vfs.get(name, b'')
        if isinstance(content, bytes):
            f = io.BytesIO(content)
            self._vfs[name] = f
        else:
            f = content
        try:
            yield f
        finally:
            f.close()

    def isfile(self, path):
        return path in self._vfs

    def size(self, f):
        return len(f.getvalue())

    def flush(self, f):
        pass

    def close(self, f):
        pass


class FakeTempFileFactory(object):
    def __init__(self, names):
        self._names = names
        self._counter = -1
        self._content = []

    def name(self, index):
        return self._content[index].name

    def file(self, index):
        return self._content[index].file

    @property
    def call_count(self):
        return self._counter

    @contextmanager
    def __call__(self, prefix='', suffix='', delete=True):
        class _dummy(object):
            def __init__(self, name, file):
                self.name = name
                self.file = file

            def flush(self):
                self.file.flush()

        self._counter += 1
        obj = _dummy(self._names[self._counter], io.BytesIO())
        self._content.append(obj)
        try:
            yield obj
        finally:
            pass



