import pytest
import sys

from pytest_mock import mocker
from unittest.mock import MagicMock

from ..cli import main as client_main

import pdistcc


def test_distcc_host_cmdline(mocker):
    cmdline = 'pdistcc --host a:1111/1 b:2222/2 -- gcc -c foo.c'
    dcc_hosts = [
        {'host': 'a', 'port': 1111, 'weight': 1},
        {'host': 'b', 'port': 2222, 'weight': 2},
    ]
    mocker.patch('sys.argv', new=cmdline.split())
    mocker.patch('pdistcc.cli.wrap_compiler')
    mocker.patch('pdistcc.cli.client_settings', return_value={'distcc_hosts': None})
    client_main()
    pdistcc.cli.wrap_compiler.assert_called_once_with(dcc_hosts,
        'gcc -c foo.c'.split(),
        {'distcc_hosts': 'a:1111/1 b:2222/2'.split()}
    )
