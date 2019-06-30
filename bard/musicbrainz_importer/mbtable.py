import re
from datetime import datetime

def processLine(line, columns):
    values = line.strip('\n').split('\t')
    r = {}
    for (name, type), value in zip(columns, values):
        # print(name, type, value)
        if value == '\\N':
            r[name] = None
        elif type == 'int':
            r[name] = int(value)
        elif type == 'bool':
            r[name] = {'t': True, 'f': False}[value]
        elif type == 'datetime':
            value = re.sub(r'\+[0-9][0-9]$', '', value)
            try:
                r[name] = datetime.strptime(value,
                                            '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                r[name] = datetime.strptime(value,
                                            '%Y-%m-%d %H:%M:%S')
        else:
            r[name] = value
    return r
