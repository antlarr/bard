# -*- coding: utf-8 -*-

from bard.musicbrainz_importer import mbtable


class MBTableIter:
    def __init__(self, name, columns):
        """Create a MBTableIter object."""
        self.name = name
        self.columns = columns
        self.column_types = {x[0]: x[1] for x in columns}
        self.col_pos_and_decoders = {x[0]: (i, mbtable.decoder_for_type(x[1],
                                                                        x[0]))
                                     for i, x in enumerate(columns)}
        self.column_positions = {x[0]: i for i, x in enumerate(columns)}
        try:
            self.id_position = self.column_positions['id']
        except KeyError:
            self.id_position = None

        self.serial = 0
        self.fh = None

    def __len__(self):
        return len(self.lines)

    def loadFromFile(self, filename):
        self.fh = open(filename, 'rb')

    def getlines(self):
        for line in self.fh.readlines():
            values = line.rstrip(b'\n').split(b'\t')
            # yield mbtable.processLine(line.decode('utf-8'),
            #                          self.column_types,
            #                          self.column_position)
            yield mbtable.LazyTableRecord(values,
                                          self.col_pos_and_decoders)

    def getlines_matching_values(self, column_name, column_values):
        pos, decoder = self.col_pos_and_decoders[column_name]

        for line in self.fh.readlines():
            values = line.rstrip(b'\n').split(b'\t')
            if decoder(values[pos]) not in column_values:
                continue
            # yield mbtable.processLine(line.decode('utf-8'),
            #                          self.column_types,
            #                          self.column_position)
            yield mbtable.LazyTableRecord(values,
                                          self.col_pos_and_decoders)
