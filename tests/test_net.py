
import os
import pytest
import sys

thisfile = os.path.realpath(__file__)
thisdir = os.path.dirname(thisfile)
parent_dir = os.path.dirname(thisdir)
new_path = [parent_dir]
new_path.extend([d for d in sys.path if d != thisdir])
sys.path = new_path

from pdistcc.net import (
    InvalidToken,
    dcc_encode,
    dcc_decode,
)


def test_decode_encode():
    b = dcc_encode('DIST', 1)
    name, ver = dcc_decode(b)
    assert ver == 1
    assert name == b'DIST'


def test_decode_rejects_short():
    with pytest.raises(InvalidToken):
        name, size = dcc_decode(b'DIST0')


def test_decode_rejects_long():
    with pytest.raises(InvalidToken):
        name, size = dcc_decode(b'DIST' + b'0'*12)
