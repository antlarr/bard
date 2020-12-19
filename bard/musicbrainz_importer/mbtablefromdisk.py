# -*- coding: utf-8 -*-

import mbtable
from mbtablecached import tobytes
from largedictintint import LargeDictOfIntToInt


class MBTableFromDisk:
    def __init__(self, name, columns, index_columns=[]):
        """Create a MBTableFromDisk object."""
        self.name = name
        self.columns = columns
        self.column_types = {x[0]: x[1] for x in columns}
        self.column_position = {x[0]: i for i, x in enumerate(columns)}

        self.index_columns = set(index_columns)

        print(self.columns)
        print(self.column_position)
        try:
            self.id_position = self.column_position['id']
            self.index_columns.add('id')
        except KeyError:
            self.id_position = None

        self.indexed_positions = {c: LargeDictOfIntToInt()
                                  for c in self.index_columns
                                  if c in self.column_position.keys()}

        self.fh = None

        self.serial = 0

    def __len__(self):
        if not self.indexed_positions:
            raise None
        return len(next(iter(self.indexed_positions.values())))

    def indexFile(self):
        temp = {col: {} for col in self.indexed_positions.keys()}
        line = self.fh.readline()
        pos = 0
        while line:
            values = line.split(b'\t')
            for col in self.indexed_positions.keys():
                k = int(values[self.column_position[col]])
                temp[col].setdefault(k, []).append(pos)
                # self.indexed_positions[col][k] = pos

            pos += len(line)

            line = self.fh.readline()

        for col in self.indexed_positions.keys():
            print(col)
            self.indexed_positions[col].fromdict(temp[col])
            # self.indexed_positions[col].dumpvalues()

    def loadFromFile(self, filename):
        self.fh = open(filename, 'rb')

        self.indexFile()

    def __getitem__(self, _id):
        if _id is None:
            return None

        if self.id_position is None:
            raise KeyError('Error getting MBTableFromDisk(%s)[%s]: No id col' %
                           (self.name, str(_id)))

        try:
            pos = self.indexed_positions['id'][_id]
        except KeyError:
            raise KeyError('Error getting MBTableFromDisk(%s)[%s]: '
                           'No id avail' % (self.name, str(_id)))
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

        if column in self.indexed_positions:
            try:
                pos = self.indexed_positions[column][_id]
            except KeyError:
                raise KeyError('Error getting MBTableFromDisk(%s)[%s:%s] ' %
                               (self.name, column, str(value)))
            self.fh.seek(pos)
        else:
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
        raise RuntimeError('MBTableFromDisk.getbycolumns not implemented')

    def contains(self, column, value):
        if column in self.index_columns:
            return value in self.indexed_positions[column]

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
        r = []

        if column in self.index_columns:
            positions = self.indexed_positions[column].getallvalues(value)
            value = tobytes(value)
            for position in positions:
                self.fh.seek(position)
                line = self.fh.readline()
                cols = line.rstrip(b'\n').split(b'\t')
                if cols[col_position] == value:
                    r.append(mbtable.processLine(line.decode('utf-8'),
                                                 self.columns))
            return r

        value = tobytes(value)

        self.fh.seek(0)
        for line in self.fh.readlines():
            cols = line.rstrip(b'\n').split(b'\t')
            if cols[col_position] == value:
                r.append(mbtable.processLine(line.decode('utf-8'),
                                             self.columns))

        return r
