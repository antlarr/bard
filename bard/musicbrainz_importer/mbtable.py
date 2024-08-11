import re
from datetime import datetime
from uuid import UUID


def to_int(x):
    if x == b'\\N':
        return None
    return int(x)


def to_str(x):
    if x == b'\\N':
        return None
    return x.decode('utf-8')


def to_uuid(x):
    if x == b'\\N':
        return None
    return UUID(x.decode('ascii'))


def to_bool(x):
    if x == b'\\N':
        return None
    return {b't': True, b'f': False}[x]


def to_datetime(x):
    if x == b'\\N':
        return None
    x = re.sub(r'\+[0-9][0-9]$', '', x)
    try:
        return datetime.strptime(x,
                                 '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        return datetime.strptime(x,
                                 '%Y-%m-%d %H:%M:%S')


def decoder_for_type(x, col_name):
    if x == 'int':
        return to_int
    elif x == 'bool':
        return to_bool
    elif x == 'datetime':
        return to_datetime
    elif x == 'uuid':
        return to_uuid
    else:
        return to_str


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
        elif type == 'uuid':
            r[name] = UUID(value)
        else:
            r[name] = value
    return r


class LazyTableRecord:
    def __init__(self, values, col_pos_and_decoders):
        """Create a LazyTableRecord object."""
        # self.values = line.strip('\n').split('\t')
        # self.values = line.split('\t')
        self.values = values
        self.positions_and_decoders = col_pos_and_decoders

    def keys(self):
        return self.positions_and_decoders.keys()

    def __len__(self):
        return len(self.values)

    def __getitem__(self, item):
        pos, decoder = self.positions_and_decoders[item]
        value = self.values[pos]

        return decoder(value)

# def processLineLazy(line, columns):
#    r = {}
#    for (name, type), value in zip(columns, values):
#        # print(name, type, value)
#        if value == '\\N':
#            r[name] = None
#        elif type == 'int':
#            r[name] = int(value)
#        elif type == 'bool':
#            r[name] = {'t': True, 'f': False}[value]
#        elif type == 'datetime':
#            value = re.sub(r'\+[0-9][0-9]$', '', value)
#            try:
#                r[name] = datetime.strptime(value,
#                                            '%Y-%m-%d %H:%M:%S.%f')
#            except ValueError:
#                r[name] = datetime.strptime(value,
#                                            '%Y-%m-%d %H:%M:%S')
#        else:
#            r[name] = value
#    return r
