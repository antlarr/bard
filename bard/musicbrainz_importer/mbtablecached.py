# -*- coding: utf-8 -*-

import mbtable


def tobytes(value):
    if type(value) == bool:
        return b't' if value else b'f'

    return str(value).encode('utf-8')


class MBTableCached:
    def __init__(self, name, columns):
        """Create a MBTable object."""
        self.name = name
        self.columns = columns
        self.column_types = {x[0]: x[1] for x in columns}
        self.column_position = {x[0]: i for i, x in enumerate(columns)}
        try:
            self.id_position = self.column_position['id']
        except KeyError:
            self.id_position = None

        self.serial = 0

    def loadFromFile(self, filename):
        with open(filename, 'rb') as f:
            self.lines = [x.rstrip(b'\n') for x in f.readlines()]

    def __getitem__(self, _id):
        if _id is None:
            return None
        if self.id_position == 0:
            strid = tobytes(_id) + b'\t'
            for line in self.lines:
                if line.startswith(strid):
                    return mbtable.processLine(line.decode('utf-8'),
                                               self.columns)
            raise KeyError('Error getting MBTableCached(%s)[%s]' %
                           (self.name, str(_id)))

        strid = tobytes(_id)
        for line in self.lines:
            values = line.split(b'\t')
            if values[self.id_position] == strid:
                return mbtable.processLine(line.decode('utf-8'), self.columns)

        raise KeyError('Error getting MBTableCached(%s)[%s]' %
                       (self.name, str(_id)))

    def getbygid(self, gid):
        return self.getbycolumn('gid', gid)

    def getbycolumn(self, column, value):
        if column == 'id':
            return self[value]

        position = self.column_position[column]
        value = str(value).encode('utf-8')
        for line in self.lines:
            cols = line.split(b'\t')
            if cols[position] == value:
                return mbtable.processLine(line.decode('utf-8'), self.columns)

        raise KeyError('Error getting MBTableCached(%s)[%s][%s]' %
                       (self.name, column, value))

    def getbycolumns(self, column_values):
        raise RuntimeError('Undefined MBTableCached.getbycolumns')

    def contains(self, column, value):
        position = self.column_position[column]
        value = tobytes(value)
        for line in self.lines:
            cols = line.split(b'\t')
            if cols[position] == value:
                return True

        return False

    def getallbycolumn(self, column, value):
        position = self.column_position[column]
        value = tobytes(value)
        r = []
        for line in self.lines:
            cols = line.split(b'\t')
            if cols[position] == value:
                r.append(mbtable.processLine(line.decode('utf-8'), self.columns))

        return r
