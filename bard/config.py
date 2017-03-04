import os
import re
import json


def readConfiguration():
    cfgfile = os.path.expanduser('~/.config/bard')
    if not os.path.isfile(cfgfile):
        raise FileNotFoundError('Configuration file not found. Please configure the application at %s' % cfgfile)

    data = ''.join([line for line in open(cfgfile).readlines() if not re.match('\s*(#|//)', line)])

    return json.loads(data)


config = readConfiguration()
