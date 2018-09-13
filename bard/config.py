# -*- coding: utf-8 -*-
import os
import re
import json
import pwd


def readConfiguration():
    cfgfile = os.path.expanduser('~/.config/bard')
    if not os.path.isfile(cfgfile):
        raise FileNotFoundError('Configuration file not found.'
                                'Please configure the application at %s'
                                % cfgfile)

    data = ''.join([line for line in open(cfgfile).readlines()
                    if not re.match('\s*(#|//)', line)])

    return json.loads(data)


config = readConfiguration()

if 'username' not in config:
    config['username'] = pwd.getpwuid(os.getuid()).pw_name

if 'immutableDatabase' not in config:
    config['immutableDatabase'] = False
