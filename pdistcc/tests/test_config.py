
import pytest
import os

from pytest_mock import mocker

from ..config import (
    client_settings,
    parse_distcc_host,
    server_settings,
)


def test_parse_distcc_host():
    host = parse_distcc_host('127.0.0.1:3632/123')
    assert host['host'] == '127.0.0.1'
    assert host['port'] == 3632
    assert host['weight'] == 123


def test_parse_distcc_host_xfail():
    with pytest.raises(ValueError):
        parse_distcc_host('abracadabra;')


def test_server_settings(mocker):
    # TODO: replace any reads from files (use dependency injection)
    here = os.path.dirname(os.path.abspath(__file__))
    confpath = os.path.join(here, 'server.json')
    mocker.patch('os.path.isfile')
    mocker.patch('os.path.expanduser')
    os.path.expanduser.return_value = here
    os.path.isfile.return_value = True
    settings = server_settings()
    os.path.expanduser.assert_called_once_with('~/.config/pdistcc')
    os.path.isfile.assert_called_once_with(confpath)
    assert settings['listen'] == '127.0.0.1:1234'


def test_client_settings(mocker):
    # TODO: replace any reads from files (use dependency injection)
    here = os.path.dirname(os.path.abspath(__file__))
    confpath = os.path.join(here, 'client.json')
    mocker.patch('os.path.isfile')
    mocker.patch('os.path.expanduser')
    os.path.expanduser.return_value = here
    os.path.isfile.return_value = True
    settings = client_settings()
    os.path.expanduser.assert_called_once_with('~/.config/pdistcc')
    os.path.isfile.assert_called_once_with(confpath)
    assert settings['distcc_hosts'] == [
        {'host': 'example.com', 'port': 1234, 'weight': 10},
    ]
