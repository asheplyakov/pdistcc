
import copy
import json
import os


DISTCCD_PORT = 3632


def _find_config(name):
    possible_dirs = []
    if 'PDISTCC_DIR' in os.environ:
        possible_dirs.append(os.environ['PDISTCC_DIR'])
    possible_dirs.append(os.path.expanduser('~/.config/pdistcc'))
    for confdir in possible_dirs:
        conffile = os.path.join(confdir, name)
        if os.path.isfile(conffile):
            return conffile


def _server_settings():
    return {
        'listen': '127.0.0.1:{}'.format(DISTCCD_PORT),
    }


def _client_settings():
    return {
        'distcc_hosts': ['127.0.0.1:{}/10'.format(DISTCCD_PORT)],
    }


def _merge_settings(settings, default):
    for var, default_value in default.items():
        if var not in settings:
            settings[var] = default_value


def _settings(name, default):
    conffile = _find_config(name)
    settings = copy.deepcopy(default)
    if conffile is not None:
        try:
            with open(conffile, 'r') as f:
                settings = json.load(f)
        except:
            print("couldn't load configuration from {}, using defaults")

    _merge_settings(settings, default)
    return settings


def server_settings():
    settings = _settings('server.json', _server_settings())
    host, port = settings['listen'].split(':')
    settings['host'] = host
    settings['port'] = int(port)
    return settings


def client_settings():
    settings = _settings('client.json', _client_settings())
    if 'DISTCC_HOSTS' in os.environ:
        settings['distcc_hosts'] = os.environ['DISTCC_HOSTS'].split()
    return settings
