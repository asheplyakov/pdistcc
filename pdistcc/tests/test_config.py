
import pytest
import os

from pytest_mock import mocker
from unittest.mock import mock_open

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


def test_config_PDISTCC_DIR(mocker):
    here = os.path.dirname(os.path.abspath(__file__))
    confpath = os.path.join(here, 'client.json')
    environ = {
        'PDISTCC_DIR': here,
        'USER': 'none',
        'LOGNAME': 'none',
        'HOME': '/',
    }
    mocker.patch('os.environ', environ)
    mocker.patch('os.path.expanduser')
    mocker.patch('os.path.isfile')
    os.path.isfile.return_value = True
    settings = client_settings()
    assert settings['distcc_hosts'] == [
        {'host': 'example.com', 'port': 1234, 'weight': 10},
    ]
    os.path.isfile.assert_called_once_with(confpath)
    os.path.expanduser.assert_called_once_with('~/.config/pdistcc')


def test_config_client_DISTCC_HOSTS(mocker):
    here = os.path.dirname(os.path.abspath(__file__))
    confpath = os.path.join(here, 'client.json')
    environ = {
        'DISTCC_HOSTS': 'localhost:1111/50'
    }
    mocker.patch('os.environ', environ)
    mocker.patch('os.path.expanduser')
    os.path.expanduser.return_value = here
    mocker.patch('os.path.isfile')
    os.path.isfile.return_value = True
    settings = client_settings()
    assert settings['distcc_hosts'] == [
        {'host': 'localhost', 'port': 1111, 'weight': 50},
    ]
    os.path.isfile.assert_called_once_with(confpath)
    os.path.expanduser.assert_called_once_with('~/.config/pdistcc')


def test_broken_config(mocker):
    m_open = mock_open(read_data='{ "BROKEN": ')
    mocker.patch('pdistcc.config.open', m_open)
    mocker.patch('os.path.expanduser')
    os.path.expanduser.return_value = '/'
    mocker.patch('os.path.isfile')
    os.path.isfile.return_value = True
    settings = client_settings()
    os.path.isfile.assert_called_once_with('/client.json')
    os.path.expanduser.assert_called_once_with('~/.config/pdistcc')
    m_open.assert_called_once_with('/client.json', 'r')
