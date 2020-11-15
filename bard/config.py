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

    defaults = {
        'immutableDatabase': False,
        'matchThreshold': 0.8,
        'storeThreshold': 0.60,
        'shortSongStoreThreshold': 0.68,
        'shortSongLength': 53,
        'port': 5000,
        'use_ssl': False,
        'sslCertificateKeyFile': '~/.config/bard/certs/server.key',
        'sslCertificateChainFile': '~/.config/bard/certs/cert.pem',
        'enable_internal_checks': False,
    }

    for key, value in defaults.items():
        if key not in config:
            config[key] = value

    path_keys = ['databasePath',
                 'sslCertificateKeyFile',
                 'sslCertificateChainFile']

    for key in path_keys:
        config[key] = os.path.expanduser(config[key])


config = readConfiguration()
addDefaultValues(config)


def translatePath(path):
    if config['translatePaths']:
        for (src, tgt) in config['pathTranslationMap']:
            src = src.rstrip('/')
            tgt = tgt.rstrip('/')
            if path.startswith(src):
                return tgt + path[len(src):]
    return path
