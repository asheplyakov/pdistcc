
import copy
import json
import logging
import os
import re


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
        'loglevel': 'WARN',
    }


def _client_settings():
    return {
        'distcc_hosts': ['127.0.0.1:{}/10'.format(DISTCCD_PORT)],
        'loglevel': 'WARN',
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


def parse_loglevel(strr):
    levels = {
        'DEBUG': logging.DEBUG,
        'WARN': logging.WARNING,
        'INFO': logging.INFO,
    }
    return levels.get(strr.upper(), logging.DEBUG)


def server_settings():
    settings = _settings('server.json', _server_settings())
    host, port = settings['listen'].split(':')
    settings['host'] = host
    settings['port'] = int(port)
    loglevel = parse_loglevel(settings['loglevel'])
    settings['loglevel'] = loglevel
    return settings


def client_settings():
    settings = _settings('client.json', _client_settings())
    if 'DISTCC_HOSTS' in os.environ:
        settings['distcc_hosts'] = os.environ['DISTCC_HOSTS'].split()
    return settings


def merge_settings_with_cli(settings, args):
    merged_settings = {}
    for k in settings.keys():
        cli_val = getattr(args, k) if hasattr(args, k) else None
        merged_settings[k] = cli_val or settings[k]
    if hasattr(args, 'verbose'):
        loglevel = 'WARN'
        if args.verbose == 1:
            loglevel = 'INFO'
        elif args.verbose >= 2:
            loglevel = 'DEBUG'
        merged_settings['loglevel'] = loglevel
    return merged_settings


def parse_distcc_host(h):
    rx = re.compile('^([^:/]+):([0-9]+)/([0-9]+)')
    m = rx.match(h)
    if m is None:
        raise ValueError('invalid host spec: %s' % h)
    host, port, weight = m.groups()
    return {
        'host': host,
        'port': int(port),
        'weight': int(weight),
    }
