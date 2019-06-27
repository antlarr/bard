# -*- coding: utf-8 -*-

import sys
import os
import os.path
import json
import urllib.request
import subprocess
import copy
# import inspect
from functools import partial
from bard.percentage import Percentage
from bard.musicdatabase import MusicDatabase, table
from mbtable import MBTable
from mbtableindisk import MBTableInDisk
from mbenums import musicbrainz_enums
from mboptions import MBOptions
from sqlalchemy import and_, select


columns_translations = {
    'artist': {'mbid': 'gid',
               'disambiguation': 'comment',
               'artist_type': 'type',
               'area_id': 'area'},
    'area': {'mbid': 'gid',
             'area_type': 'type'},
    'artist_alias': {'artist_id': 'artist',
                     'artist_alias_type': 'type'},
    'release_group': {'mbid': 'gid',
                      'artist_credit_id': 'artist_credit',
                      'disambiguation': 'comment',
                      'release_group_type': 'type'},
    'artist_credit': {},
    'artist_credit_name': {'artist_id': 'artist',
                           'artist_credit_id': 'artist_credit'},
    'work': {'mbid': 'gid',
             'disambiguation': 'comment',
             'work_type': 'type'},
    'link': {'link_type_id': 'link_type'},
    'link_type': {'mbid': 'gid'},
    'link_attribute_type': {'mbid': 'gid'},
    'link_attribute': {'link_id': 'link',
                       'link_attribute_type_id': 'attribute_type'},
    'recording': {'mbid': 'gid',
                  'disambiguation': 'comment',
                  'artist_credit_id': 'artist_credit'},
    'release': {'mbid': 'gid',
                'disambiguation': 'comment',
                'artist_credit_id': 'artist_credit',
                'release_group_id': 'release_group',
                'release_status': 'status'},
    'release_country': {'release_id': 'release',
                        'country_id': 'country'},
    'release_label': {'release_id': 'release',
                      'label_id': 'label'},
    'label': {'mbid': 'gid',
              'disambiguation': 'comment',
              'label_type': 'type',
              'area_id': 'area'},
    'medium': {'release_id': 'release'},
    'track': {'mbid': 'gid',
              'recording_id': 'recording',
              'medium_id': 'medium',
              'artist_credit_id': 'artist_credit',
              'number_text': 'number'}}


def add_link_id_column_transform(tablename, entity0, entity1):
    if tablename not in columns_translations:
        columns_translations[tablename] = {}
    columns_translations[tablename]['link_id'] = 'link'


def iterate_over_l_tables(func):
    entities = ['area', 'artist', 'event', 'instrument', 'label', 'place',
                'recording', 'release', 'release_group', 'series', 'work']
    remaining_entities = entities[:]
    for entity0 in entities:
        for entity1 in remaining_entities:
            func(f'l_{entity0}_{entity1}', entity0, entity1)
        remaining_entities.remove(entity0)


iterate_over_l_tables(add_link_id_column_transform)

table_translations = {
    'enum_area_type_values': 'area_type',
    'enum_artist_type_values': 'artist_type',
    'enum_artist_alias_type_values': 'artist_alias_type',
    'enum_release_group_type_values': 'release_group_primary_type',
    'enum_release_status_values': 'release_status',
    'enum_language_values': 'language',
    'enum_gender_values': 'gender',
    'enum_medium_format_values': 'medium_format',
    'enum_work_type_values': 'work_type',
    'enum_place_type_values': 'place_type',
    'enum_series_type_values': 'series_type',
    'enum_label_type_values': 'label_type'}

# When importing an item of type 'key', also import other tables, specified as
# a list of tuples of 3 strings. The first is the new table to import,
# the second, the column in the table that is the key (in the original mb name)
# that has to be matched to the item property specified by the third parameter.
extra_imports = {
    'artist': [('artist_alias', 'artist', 'id'),
               ('l_artist_artist', 'entity0', 'id'),
               ('l_artist_artist', 'entity1', 'id')],
    'artist_credit': [('artist_credit_name', 'artist_credit', 'id')],
    'work': [('l_artist_work', 'entity1', 'id'),
             ('l_work_work', 'entity0', 'id'),
             ('l_work_work', 'entity1', 'id')],
    'recording': [('l_artist_recording', 'entity1', 'id'),
                  ('l_recording_recording', 'entity0', 'id'),
                  ('l_recording_recording', 'entity1', 'id')],
    'link': [('link_attribute', 'link', 'id')],
    'release': [('l_artist_release', 'entity1', 'id'),
                ('release_country', 'release', 'id'),
                ('release_label', 'release', 'id'),
                ('medium', 'release', 'id')],
    'label': [('l_artist_label', 'entity1', 'id'),
              # We don't want to follow subsidiaries
              # ('l_label_label', 'entity0', 'id'),
              # We want to have parent labels
              ('l_label_label', 'entity1', 'id')],
    'medium': [('track', 'medium', 'id')]}

l_tables = {}


def add_l_table(tablename, x, y):
    l_tables[tablename] = (x, y)


iterate_over_l_tables(add_l_table)

extra_filters = {}

follow_links_to_import = {
    ('artist', 'artist'): ['member of band', 'married', 'sibling', 'parent', 'subgroup', 'founder'],  # noqa
    ('label', 'label'): ['label ownership'],
    ('artist', 'label'): ['label founder']}
#    ('artist', 'artist'): ['member of band', 'tribute', 'supporting musician', 'instrumental supporting musician', 'married', 'sibling', 'parent', 'is person', 'conductor position', 'vocal supporting musician', 'subgroup', 'founder', 'named after', 'involved with']}  # noqa


def filter_missing_entities(extra_entity, items, extra_column, entity, item):
    try:
        entities = l_tables[extra_entity]
    except KeyError:
        return items

    test_column = 1 if extra_column == 'entity0' else 0
    test_entity_num = f'entity{test_column}'
    test_entity = entities[test_column]
    dbtable = table('musicbrainz.' + test_entity)
    if dbtable.primary_key.columns.keys() != ['id']:
        raise ValueError(f'Invalid table: {entities}, {test_column},'
                         f'{extra_column}, {entity}, {item}')

    available_ids = {x[0] for x in MusicDatabase.execute(
                     select([dbtable.c.id])).fetchall()}
    r = [x for x in items if x[test_entity_num] in available_ids]
    return r


def filter_in_by_link_type(extra_entity, items, extra_column, entity, item,
                           link_types, importer):
    linktable = importer.read_entity_table('link')
    return [x for x in items
            if linktable[x['link']]['link_type'] in link_types]


def add_filter_missing_entities(tablename, entity0, entity1):
    extra_filters[tablename] = filter_missing_entities


from types import ModuleType, FunctionType
from gc import get_referents

# Custom objects know their class.
# Function objects seem to know way too much, including modules.
# Exclude modules as well.
BLACKLIST = type, ModuleType, FunctionType


def getsize(obj):
    """Sum size of object & members."""
    if isinstance(obj, BLACKLIST):
        raise TypeError('getsize() does not take argument of type: ' +
                        str(type(obj)))
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size


class MusicBrainzImporter:
    def __init__(self):
        """Create a MusicBrainzImporter object."""
        self.directory = os.path.expanduser('~/.local/share/bard')
        self.names = None
        self.entities = {}
        self.initialize_l_table_filters()

    def initialize_l_table_filters(self):
        # By default, only add links to existing entities
        # (filter our links to missing entities)
        iterate_over_l_tables(add_filter_missing_entities)
        # Except for artist <-> work / recording / release / release_group
        del extra_filters['l_artist_work']
        del extra_filters['l_artist_recording']
        del extra_filters['l_artist_release']
        del extra_filters['l_artist_release_group']
        mbtable = self.read_entity_table('link_type')

        for entities, link_names in follow_links_to_import.items():
            link_type_ids = set()
            l_table = f'l_{entities[0]}_{entities[1]}'

            for link_name in link_names:
                sel = {'entity_type0': entities[0],
                       'entity_type1': entities[1],
                       'name': link_name}
                link_type = mbtable.getbycolumns(sel)
                if not link_type:
                    raise ValueError(f'Link type not found: {entities}: '
                                     f'{link_names}')
                link_type_ids.add(link_type['id'])
            extra_filters[l_table] = partial(filter_in_by_link_type,
                                             link_types=link_type_ids,
                                             importer=self)

    @staticmethod
    def get_fullexport_latest_directory():
        url = "http://ftp.musicbrainz.org/pub/musicbrainz/data/fullexport"

        latest = urllib.request.urlopen(url + "/LATEST")
        latest = latest.read().decode('utf-8').strip('\n')

        return url + "/" + latest

    @staticmethod
    def retrieve_mbdump_file(filename):
        url = MusicBrainzImporter.get_fullexport_latest_directory()
        url += '/' + filename

        directory = os.path.expanduser('~/.local/share/bard')
        filename = os.path.join(directory, filename)

        percentage = Percentage(2)

        def proc(blocksTransferred, blockSize, fileSize):
            percentage.max_value = fileSize
            percentage.set_value(blocksTransferred * blockSize)

        print('Retrieving MusicBrainz dump file: ', filename)
        (filename, headers) = urllib.request.urlretrieve(url, filename, proc)
        urllib.request.urlcleanup()
        print('Done')

    def extract_mbdump_file(self, filename):
        filename = os.path.join(self.directory, filename)
        command = ['/usr/bin/tar', '-C', self.directory, '-xvf', filename,
                   'mbdump']
        subprocess.run(command)

    def retrieve_musicbrainz_dumps(self):
        MusicBrainzImporter.retrieve_mbdump_file('mbdump.tar.bz2')
        self.extract_mbdump_file('mbdump.tar.bz2')
        MusicBrainzImporter.retrieve_mbdump_file('mbdump-derived.tar.bz2')
        self.extract_mbdump_file('mbdump-derived.tar.bz2')

    def load_musicbrainz_schema_importer_names(self):
        if self.names:
            return
        filename = os.path.join(self.directory,
                                'musicbrainz_schema_importer_names')
        with open(filename) as f:
            self.names = json.load(f)

    def read_mbdump_table(self, tablename):
        self.load_musicbrainz_schema_importer_names()
        filename = os.path.join(self.directory, 'mbdump', tablename)
        columns = self.names[tablename]
        print(columns)
        if tablename in ['track', 'recording', 'url', 'l_artist_recording',
                         'recording_meta', 'release', 'l_recording_work',
                         'artist', 'release_group', 'l_artist_url',
                         'l_release_url', 'medium', 'annotation',
                         'l_artist_work', 'work', 'artist_credit',
                         'release_label', 'artist_credit_name',
                         'release_country', 'l_artist_release']:
            table = MBTableInDisk(tablename, columns)
        else:
            table = MBTable(tablename, columns)

        table.loadFromFile(filename)

        print('##########################################################  ' +
              f'Read {type(table).__name__}({tablename}). Size:',
              getsize(table))

        return table

    def read_entity_table(self, entity):
        try:
            return self.entities[entity]
        except KeyError:
            pass

        self.entities[entity] = self.read_mbdump_table(entity)
        return self.entities[entity]

    def to_mbcolname(self, table, dbcolumn):
        print(f'translating {table}.{dbcolumn}')
        try:
            translations = columns_translations[table]
        except KeyError:
            translations = {}
        try:
            return translations[dbcolumn]
        except KeyError:
            pass
        return dbcolumn

    def import_extra_data(self, extra_table, extra_column, src_property,
                          entity, item, options):
        print('Importing extra data', extra_table, extra_column, src_property,
              entity, item)

        mbtable = self.read_entity_table(extra_table)
#        mbcolumn = self.to_mbcolname(extra_table, src_property)
#        print(mbcolumn)
#        print(item[mbcolumn])
        items = mbtable.getallbycolumn(extra_column, item[src_property])

        extra_filter = extra_filters.get(extra_table, None)
        if extra_filter:
            print(f'Filtering {extra_table}')
            items = extra_filter(extra_table, items, extra_column,
                                 entity, item)

        if extra_table in ['l_artist_artist']:
            opts = copy.deepcopy(options)
            opts.forbid_table(extra_table)
        else:
            opts = options

        for mbrecord in items:
            print('Importing extra record', extra_table, mbrecord)
            self.import_entity_item(extra_table, mbrecord, opts)

    def save_entity_item(self, entity, item, options):
        dbtable = table('musicbrainz.%s' % entity)

        try:
            translations = columns_translations[entity]
        except KeyError:
            translations = {}
        record = {}
        for col in dbtable.columns:
            mbcolname = translations.get(col.name, col.name)

            try:
                record[col.name] = item[mbcolname]
            except KeyError:
                print(f'Cannot get {entity} item[{mbcolname}]: {item}')
                raise

        for fk in dbtable.foreign_keys:
            if (fk.column.table.name.startswith('enum_') and
                    fk.column.table.name.endswith('_values')):
                col_keys = fk.constraint.column_keys
                if len(col_keys) != 1:
                    msg = ('Invalid constraint column_keys: %s for fk: %s'
                           % (col_keys, fk))
                    raise ValueError(msg)
                dbenum = musicbrainz_enums[fk.column.table.name]
                column = col_keys[0]
                if type(record[column]) == str:
                    record[column] = dbenum.id_value(record[column])
                else:
                    enumtable = table_translations[fk.column.table.name]

                    self.read_entity_table(enumtable)
                    try:
                        value = self.entities[enumtable][record[column]]
                    except KeyError:
                        print(f'Error obtaining self.entities[{enumtable}]'
                              f'[record[{column}] == {record[column]}]')
                        raise
                    if value:
                        record[column] = dbenum.id_value(value['name'])
                        print(f'record column {column} set to {record[column]}'
                              ' as value for %s' % value['name'])
                    else:
                        record[column] = None
                        print(f'record column {column} set to None')

            else:
                col_keys = fk.constraint.column_keys
                if len(col_keys) != 1:
                    msg = ('Invalid constraint column_keys: %s for fk: %s'
                           % (col_keys, fk))
                    raise ValueError(msg)

                value = record[col_keys[0]]
                if value:
                    dbRecord = fk.column.table.select(fk.column == value)
                    dbRecord = MusicDatabase.execute(dbRecord).fetchone()
                    # This should maybe use a stack of objects being modified
                    if not dbRecord:
                        print('Adding fk', fk.column.table.name,
                              fk.column.name, value)
                        tablename = fk.column.table.name
                        opts = copy.deepcopy(options)
                        opts.set_inmediate_flag()
                        self.import_entity(tablename, fk.column.name, value,
                                           opts)

        MusicDatabase.commit()
        if entity == 'artist_credit_name':
            MusicDatabase.insert_or_update(dbtable, record,
                    and_(dbtable.c.artist_credit_id == record['artist_credit_id'],  # noqa
                         dbtable.c.position == record['position']))
        elif entity == 'link_attribute':
            MusicDatabase.insert_or_update(dbtable, record,
                and_(dbtable.c.link_id == record['link_id'],  # noqa
                     dbtable.c.link_attribute_type_id == record['link_attribute_type_id']))  # noqa
        elif entity == 'release_country':
            MusicDatabase.insert_or_update(dbtable, record,
                and_(dbtable.c.release_id == record['release_id'],  # noqa
                     dbtable.c.country_id == record['country_id']))
        else:
            MusicDatabase.insert_or_update(dbtable, record)

        extra_import = extra_imports.get(entity, [])

        for extra_table, extra_column, src_prop in extra_import:
            if options.should_follow_table(extra_table):
                print('')
                print(extra_table, 'options:', str(options))
                self.import_extra_data(extra_table, extra_column, src_prop,
                                       entity, item, options)

    def import_entity_item(self, entity, item, options):
        # if len(inspect.stack()) > 25:
        #     import pdb
        #     pdb.set_trace()

        opts = copy.deepcopy(options)
        opts.set_inmediate_flag(False)
        key = (entity, str(item), str(opts))
        if key in self.items_imported:
            return

        if options.has_inmediate_flag():
            self.items_imported.add(key)
            self.save_entity_item(entity, item, opts)
            return

        print(f'Queue import of {entity} {item} {options}')
        self.items_to_import.append((entity, item, options))

        if self.importing:
            return

        self.importing = True

        for entity, item, opts in self.items_to_import:
            key = (entity, str(item), str(opts))
            self.items_imported.add(key)
            self.save_entity_item(entity, item, opts)

    def cleanup_import(self):
        self.items_imported = set()
        self.items_to_import = []
        self.importing = False

    def import_entity(self, table, column, value, options):
        print("Reading table %s" % table)
        self.read_entity_table(table)
        if (table in self.entities and
                self.entities[table].contains(column, value)):
            print("Saving %s : %s" % (table, value))
            item = self.entities[table].getbycolumn(column, value)
            self.import_entity_item(table, item, options)
        else:
            print("Cannot read %s : %s" % (table, value))

    def import_entity_uuid(self, entity, uuid, options=MBOptions()):
        self.cleanup_import()
        return self.import_entity(entity, 'gid', uuid, options)
