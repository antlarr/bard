# -*- coding: utf-8 -*-

import mbtable
from mbtablecached import tobytes
from largedictintint import LargeDictOfIntToInt


class MBTableFromDisk:
    def __init__(self, name, columns):
        """Create a MBTableFromDisk object."""
        self.name = name
        self.columns = columns
        self.column_types = {x[0]: x[1] for x in columns}
        self.column_position = {x[0]: i for i, x in enumerate(columns)}
        print(self.columns)
        print(self.column_position)
        try:
            self.id_position = self.column_position['id']
            self.entry_positions = LargeDictOfIntToInt()
        except KeyError:
            self.id_position = None
            self.entry_positions = None
        self.fh = None

        self.serial = 0

    def indexFile(self):
        line = self.fh.readline()
        pos = 0
        while line:
            values = line.split(b'\t')
            if self.id_position is not None:
                self.entry_positions[int(values[self.id_position])] = pos
            pos += len(line)

            line = self.fh.readline()

    def loadFromFile(self, filename):
        self.fh = open(filename, 'rb')

        self.indexFile()

    def __getitem__(self, _id):
        if _id is None:
            return None

        if self.id_position is None:
            raise KeyError('Error getting MBTableFromDisk(%s)[%s]: No id col' %
                           (self.name, str(_id)))

        print(self.entry_positions)
        try:
            pos = self.entry_positions[_id]
        except KeyError:
            raise KeyError('Error getting MBTableFromDisk(%s)[%s]: No id avail' %
                       (self.name, str(_id)))
        self.fh.seek(pos)
        line = self.fh.readline()

        if self.id_position == 0:
            strid = tobytes(_id) + b'\t'
            if line.startswith(strid):
                return mbtable.processLine(line.decode('utf-8'), self.columns)
        else:
            strid = tobytes(_id)
            values = line.rstrip(b'\n').split(b'\t')
            if values[self.id_position] == strid:
                return mbtable.processLine(line.decode('utf-8'), self.columns)

        raise KeyError('Error getting MBTableFromDisk(%s)[%s]' %
                       (self.name, str(_id)))

    def getbygid(self, gid):
        return self.getbycolumn('gid', gid)

    def getbycolumn(self, column, value):
        if column == 'id':
            return self[value]

        self.fh.seek(0)

        col_position = self.column_position[column]
        value = str(value).encode('utf-8')
        for line in self.fh.readlines():
            cols = line.rstrip(b'\n').split(b'\t')
            if cols[col_position] == value:
                return mbtable.processLine(line.decode('utf-8'), self.columns)

        raise KeyError('Error getting MBTableFromDisk(%s)[%s][%s]' %
                       (self.name, column, value))

    def getbycolumns(self, column_values):
        raise RuntimeError('Undefined MBTableFromDisk.getbycolumns')

    def contains(self, column, value):
        if column == 'id' and self.id_position is not None:
            return value in self.line_positions
        elif column == 'id':
            raise ValueError('No id column in table?')

        self.fh.seek(0)

        col_position = self.column_position[column]
        value = tobytes(value)
        for line in self.fh.readlines():
            cols = line.rstrip(b'\n').split(b'\t')
            if cols[col_position] == value:
                return True

        return False

    def getallbycolumn(self, column, value):
        col_position = self.column_position[column]
        value = tobytes(value)
        r = []
        self.fh.seek(0)
        for line in self.fh.readlines():
            cols = line.rstrip(b'\n').split(b'\t')
            print(cols[col_position], value)
            if cols[col_position] == value:
                r.append(mbtable.processLine(line.decode('utf-8'), self.columns))

        return r
