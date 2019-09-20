
import os
import pdistcc
import pytest
import sys

from pytest_mock import mocker

from ..cli import (
    main,
    server_main,
)


def test_pdistcc_main(mocker):
    args = 'pdistcc.py gcc -c -o foo.o foo.c'.split()
    mocker.patch('sys.argv', args)
    mocker.patch('pdistcc.cli.wrap_compiler')
    pdistcc.cli.wrap_compiler.return_value = 0
    mocker.patch('pdistcc.cli.client_settings')
    settings = {
        'distcc_hosts': [{'host': '127.0.0.1', 'port': 1234, 'weight': 123}],
    }
    pdistcc.cli.client_settings.return_value = settings
    assert main() == 0
    pdistcc.cli.wrap_compiler.assert_called_once_with(
        [{'host': '127.0.0.1', 'port': 1234, 'weight': 123}],
        args[1:], settings,
    )
    pdistcc.cli.client_settings.assert_called_once()


def test_pdistcc_main_explicit_host(mocker):
    args = 'pdistcc.py --host example.com:3210/20 --host localhost:1234/10 '\
        'gcc -c -o foo.o foo.c'.split()
    distcc_hosts = [
        {'host': 'example.com', 'port': 3210, 'weight': 20},
        {'host': 'localhost', 'port': 1234, 'weight': 10},
    ]

    mocker.patch('sys.argv', args)
    mocker.patch('pdistcc.cli.client_settings')
    pdistcc.cli.client_settings.return_value = {}
    mocker.patch('pdistcc.cli.wrap_compiler')
    pdistcc.cli.wrap_compiler.return_value = 0
    assert main() == 0
    pdistcc.cli.client_settings.assert_called_once()
    pdistcc.cli.wrap_compiler.assert_called_once_with(
        distcc_hosts,
        'gcc -c -o foo.o foo.c'.split(),
        {'distcc_hosts': distcc_hosts},
    )


def test_pdistcc_daemon(mocker):
    args = ['pdistccd.py']
    mocker.patch('sys.argv', args)
    mocker.patch('pdistcc.cli.server_settings')
    pdistcc.cli.server_settings.return_value = {
        'host': 'localhost',
        'port': 11111,
    }
    mocker.patch('pdistcc.cli.daemon')
    assert server_main() is None
    pdistcc.cli.daemon.assert_called_once_with(
        {'host': 'localhost', 'port': 11111},
        host='localhost',
        port=11111
    )
