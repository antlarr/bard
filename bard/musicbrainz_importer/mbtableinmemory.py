# -*- coding: utf-8 -*-

import re
from datetime import datetime


class MBTable:
    def __init__(self, name, columns):
        """Create a MBTable object."""
        self.name = name
        self.data = {}
        self.converters = {}
        self.columns = columns
        self.serial = 0

    @staticmethod
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

    def loadFromFile(self, filename):
        with open(filename, 'r') as f:
            for line in f.readlines():
                self.add(MBTable.processLine(line, self.columns))

    def add(self, v):
        fast_access_keys = v.keys()
        try:
            _id = v['id']
            if 'gid' in v:
                fast_access_keys = ['gid']
        except KeyError:
            self.serial += 1
            _id = self.serial

        self.data[_id] = v

        for key in fast_access_keys:
            try:
                self.converters[key][v[key]] = _id
            except KeyError:
                self.converters[key] = {}
                self.converters[key][v[key]] = _id

    def __getitem__(self, _id):
        if _id is None:
            return None
        try:
            return self.data[_id]
        except KeyError:
            print('Error getting MBTable(%s)[%s]' % (self.name, str(_id)))
            raise

    def getbygid(self, gid):
        _id = self.converters['gid'][gid]
        return self.data[_id]

    def getbycolumn(self, column, value):
        if column == 'id':
            return self.data[value]
        try:
            _id = self.converters[column][value]
        except KeyError:
            print('Error getting MBTable(%s)[%s][%s]' % (self.name, column,
                                                         value))
            raise
        return self.data[_id]

    def getbycolumns(self, column_values):
        for x in self.data.values():
            if all(x[col] == val for col, val in column_values.items()):
                return x
        return None

    def contains(self, column, value):
        if column == 'id':
            return value in self.data

        return (column in self.converters and
                value in self.converters[column] and
                self.converters[column][value] in self.data)

    def getallbycolumn(self, column, value):
        return [x for x in self.data.values() if x[column] == value]
