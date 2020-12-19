# -*- coding: utf-8 -*-
import os
import re
import json
import pwd


def readConfiguration():
    cfgfile = os.path.expanduser(os.getenv('BARDCONFIGFILE', '~/.config/bard'))
    if not os.path.isfile(cfgfile):
        raise FileNotFoundError('Configuration file not found.'
                                'Please configure the application at %s'
                                % cfgfile)

    data = ''.join([line for line in open(cfgfile).readlines()
                    if not re.match(r'\s*(#|//)', line)])

    return json.loads(data)


def addDefaultValues(config):
    if 'username' not in config:
        config['username'] = pwd.getpwuid(os.getuid()).pw_name

    if 'host' not in config:
        import socket
        config['host'] = socket.gethostname()

    if 'preferred_locales' not in config:
        import locale
        lang, _ = locale.getlocale()
        lang = lang.split('_')[0]
        config['preferred_locales'] = [lang]

    defaults = {
        'immutable_database': False,
        'match_threshold': 0.8,
        'store_threshold': 0.60,
        'short_song_store_threshold': 0.68,
        'short_song_length': 53,
        'port': 5000,
        'use_ssl': False,
        'ssl_certificate_key_file': '~/.config/bard/certs/server.key',
        'ssl_certificate_chain_file': '~/.config/bard/certs/cert.pem',
        'enable_internal_checks': False,
        'ignore_extensions': [],
    }

    for key, value in defaults.items():
        if key not in config:
            config[key] = value

    path_keys = ['database_path',
                 'ssl_certificate_key_file',
                 'ssl_certificate_chain_file']

    for key in path_keys:
        try:
            config[key] = os.path.expanduser(config[key])
        except KeyError:
            config[key] = None


config = readConfiguration()
addDefaultValues(config)


def translatePath(path):
    if config['translate_paths']:
        for (src, tgt) in config['path_translation_map']:
            src = src.rstrip('/')
            tgt = tgt.rstrip('/')
            if path.startswith(src):
                return tgt + path[len(src):]
    return path
