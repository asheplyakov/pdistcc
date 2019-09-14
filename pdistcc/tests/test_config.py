
import pytest
import os

from pytest_mock import mocker

from ..config import (
    client_settings,
    server_settings,
)


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
    assert settings['distcc_hosts'] == ['example.com:1234/10']
