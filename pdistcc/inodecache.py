
import fasteners
import hashlib
import os
import os.path

CACHE_VERSION = 1


def hash_inode(path, kind):
    hsh = hashlib.new('md5')
    st = os.stat(path)
    key = (
        CACHE_VERSION.to_bytes(2, 'little'),
        kind.to_bytes(2, 'little'),
        st.st_dev.to_bytes(4, 'little'),
        st.st_ino.to_bytes(8, 'little'),
        st.st_size.to_bytes(8, 'little'),
        (st.st_mtime_ns//1000).to_bytes(8, 'little')
    )
    hsh.update(b''.join(k for k in key))
    return hsh.hexdigest()


class InodeCache:
    def __init__(self, cachedir, rwlock=None):
        self._basedir = cachedir
        self._rwlock = rwlock or fasteners.InterProcessReaderWriterLock
        os.makedirs(cachedir, exist_ok=True)

    def _path_by_hash(self, digest):
        return os.path.join(self._basedir, digest)

    def put(self, path, kind, value):
        digest = hash_inode(path, kind)
        entry_path = self._path_by_hash(digest)
        os.makedirs(os.path.dirname(entry_path), exist_ok=True)
        lock = self._rwlock(f"{entry_path}.lock")
        with lock.write_lock():
            with open(entry_path, 'wb') as f:
                f.write(value)

    def get(self, path, kind):
        digest = hash_inode(path, kind)
        entry_path = self._path_by_hash(digest)
        lock = self._rwlock(f"{entry_path}.lock")
        try:
            with lock.read_lock():
                with open(entry_path, 'rb') as f:
                    return f.read()
        except FileNotFoundError:
            return None
