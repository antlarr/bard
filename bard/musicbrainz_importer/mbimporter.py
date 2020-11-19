# -*- coding: utf-8 -*-
import sys
import os
import os.path
import json
import urllib.request
import subprocess
import copy
# from datetime import datetime
# import inspect
from functools import partial
from bard.percentage import Percentage
from bard.musicdatabase import MusicDatabase, table
from bard.musicbrainz_database import MusicBrainzDatabase
from mbtableinmemory import MBTableInMemory
from mbtableiter import MBTableIter
from mbtablecached import MBTableCached
from mbtablefromdisk import MBTableFromDisk
from mbenums import musicbrainz_enums
from mboptions import MBOptions
from sqlalchemy import text, and_, select
import concurrent.futures
from multiprocessing import Lock

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


columns_translations = {
    'artist': {'mbid': 'gid',
               'disambiguation': 'comment',
               'artist_type': 'type',
               'area_id': 'area'},
    'area': {'mbid': 'gid',
             'area_type': 'type'},
    'artist_alias': {'artist_id': 'artist',
                     'artist_alias_type': 'type'},
    'event': {'mbid': 'gid',
              'event_type': 'type'},
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
    'link_attribute_credit': {'link_id': 'link',
                              'link_attribute_type_id': 'attribute_type'},
    'recording': {'mbid': 'gid',
                  'disambiguation': 'comment',
                  'artist_credit_id': 'artist_credit'},
    'recording_alias': {'recording_id': 'recording',
                        'recording_alias_type': 'type'},
    'release': {'mbid': 'gid',
                'disambiguation': 'comment',
                'artist_credit_id': 'artist_credit',
                'release_group_id': 'release_group',
                'release_status': 'status'},
    'release_group_secondary_type_join': {'release_group_id': 'release_group'},
    'release_country': {'release_id': 'release',
                        'country_id': 'country'},
    'release_unknown_country': {'release_id': 'release'},
    'release_label': {'release_id': 'release',
                      'label_id': 'label'},
    'label': {'mbid': 'gid',
              'disambiguation': 'comment',
              'label_type': 'type',
              'area_id': 'area'},
    'series': {'mbid': 'gid',
               'disambiguation': 'comment',
               'series_type': 'type'},
    'medium': {'release_id': 'release'},
    'track': {'mbid': 'gid',
              'recording_id': 'recording',
              'medium_id': 'medium',
              'artist_credit_id': 'artist_credit',
              'number_text': 'number'}}

tables = ['area',
          'artist',
          'artist_alias',
          'artist_credit',
          'artist_credit_name',
          'enum_area_type_values',
          'enum_artist_alias_type_values',
          'enum_artist_type_values',
          'enum_event_type_values',
          'enum_gender_values',
          'enum_instrument_type_values',
          'enum_label_type_values',
          'enum_language_values',
          'enum_medium_format_values',
          'enum_place_type_values',
          'enum_release_group_type_values',
          'enum_release_status_values',
          'enum_series_type_values',
          'enum_work_type_values',
          'event',
          'instrument',
          'l_area_area',
          'l_area_artist',
          'l_area_event',
          'l_area_instrument',
          'l_area_label',
          'l_area_place',
          'l_area_recording',
          'l_area_release',
          'l_area_release_group',
          'l_area_series',
          'l_area_work',
          'l_artist_artist',
          'l_artist_event',
          'l_artist_instrument',
          'l_artist_label',
          'l_artist_place',
          'l_artist_recording',
          'l_artist_release',
          'l_artist_release_group',
          'l_artist_series',
          'l_artist_work',
          'l_event_event',
          'l_event_instrument',
          'l_event_label',
          'l_event_place',
          'l_event_recording',
          'l_event_release',
          'l_event_release_group',
          'l_event_series',
          'l_event_work',
          'l_instrument_instrument',
          'l_instrument_label',
          'l_instrument_place',
          'l_instrument_recording',
          'l_instrument_release',
          'l_instrument_release_group',
          'l_instrument_series',
          'l_instrument_work',
          'l_label_label',
          'l_label_place',
          'l_label_recording',
          'l_label_release',
          'l_label_release_group',
          'l_label_series',
          'l_label_work',
          'l_place_place',
          'l_place_recording',
          'l_place_release',
          'l_place_release_group',
          'l_place_series',
          'l_place_work',
          'l_recording_recording',
          'l_recording_release',
          'l_recording_release_group',
          'l_recording_series',
          'l_recording_work',
          'l_release_group_release_group',
          'l_release_group_series',
          'l_release_group_work',
          'l_release_release',
          'l_release_release_group',
          'l_release_series',
          'l_release_work',
          'l_series_series',
          'l_series_work',
          'l_work_work',
          'label',
          'link',
          'link_attribute',
          'link_attribute_credit',
          'link_attribute_type',
          'link_type',
          'medium',
          'place',
          'recording',
          'recording_alias',
          'release',
          'release_country',
          'release_unknown_country',
          'release_group',
          'release_label',
          'series',
          'track',
          'work']


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
    'enum_artist_alias_type_values': 'artist_alias_type',
    'enum_artist_type_values': 'artist_type',
    'enum_event_type_values': 'event_type',
    'enum_release_group_type_values': 'release_group_primary_type',
    'enum_release_status_values': 'release_status',
    'enum_language_values': 'language',
    'enum_gender_values': 'gender',
    'enum_medium_format_values': 'medium_format',
    'enum_recording_alias_type_values': 'recording_alias_type',
    'enum_work_type_values': 'work_type',
    'enum_place_type_values': 'place_type',
    'enum_series_type_values': 'series_type',
    'enum_label_type_values': 'label_type',
    'enum_instrument_type_values': 'instrument_type',
    'enum_release_group_secondary_type_values': 'release_group_secondary_type'
}

# When importing an item of type 'key', also import other tables, specified as
# a list of tuples of 3 strings. The first is the new table to import,
# the second, the column in the table that is the key (in the original mb name)
# that has to be matched to the item property specified by the third parameter.
# extra_imports = {
#    'artist': [('artist_alias', 'artist', 'id'),
#               ('l_artist_artist', 'entity0', 'id'),
#               ('l_artist_artist', 'entity1', 'id')],
#    'artist_credit': [('artist_credit_name', 'artist_credit', 'id')],
#    'work': [('l_artist_work', 'entity1', 'id'),
#             ('l_work_work', 'entity0', 'id'),
#             ('l_work_work', 'entity1', 'id')],
#    'recording': [('l_artist_recording', 'entity1', 'id'),
#                  ('l_recording_recording', 'entity0', 'id'),
#                  ('l_recording_recording', 'entity1', 'id'),
#                  ('l_recording_work', 'entity0', 'id')],
#    'link': [('link_attribute', 'link', 'id')],
#    'release': [('l_artist_release', 'entity1', 'id'),
#                ('release_country', 'release', 'id'),
#                ('release_label', 'release', 'id'),
#                ('medium', 'release', 'id')],
#    'label': [('l_artist_label', 'entity1', 'id'),
#              # We don't want to follow subsidiaries
#              # ('l_label_label', 'entity0', 'id'),
#              # We want to have parent labels
#              ('l_label_label', 'entity1', 'id')],
#    'medium': [('track', 'medium', 'id')]}
#


related_entities_to_import = {
    'event': [('recording', 0, False),
              ('release', 0, False),
              ('release_group', 0, False),
              ('work', 0, False)],
    'artist': [('event', 0, False),
               ('artist', 0, True),
               ('artist', 1, True),
               ('recording', 0, False),
               ('release', 0, False),
               ('release_group', 0, False),
               ('work', 0, False)],
    'work': [('work', 0, True),
             ('work', 1, True),
             ('recording', 1, False)],
    'series': [('artist', 1, False),
               ('event', 1, False),
               ('recording', 1, False),
               ('release', 1, False),
               ('release_group', 1, False),
               ('work', 0, False)]}


indexed_columns = {'artist_alias': ['artist'],
                   'recording_alias': ['recording'],
                   'l_artist_artist': ['entity0', 'entity1'],
                   'artist_credit_name': ['artist_credit'],
                   'l_artist_work': ['entity1'],
                   'l_work_work': ['entity0', 'entity1'],
                   'l_artist_recording': ['entity1'],
                   'l_recording_recording': ['entity0', 'entity1'],
                   'link_attribute': ['link'],
                   'l_artist_release': ['entity1'],
                   'release_country': ['release'],
                   'release_unknown_country': ['release'],
                   'release_label': ['release'],
                   'medium': ['release'],
                   'l_artist_label': ['entity1'],
                   'l_label_label': ['entity1'],
                   'track': ['medium']}


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


class MusicBrainzImporter:
    def __init__(self):
        """Create a MusicBrainzImporter object."""
        self.directory = os.path.expanduser('~/.local/share/bard')
        self.names = None
        self.entities = {}
        self.initialize_l_table_filters()
        self.uuids = {}
        self.uuids_not_found = {}
        self.ids = {}
        self.parent_ids = {}
        self.uuids_not_found_mutex = Lock()

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

        print(latest)
        return url + "/" + latest, latest

    @staticmethod
    def retrieve_mbdump_file(filename):
        url, _ = MusicBrainzImporter.get_fullexport_latest_directory()
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
        tableClasses = {'track': MBTableFromDisk,
                        'recording': MBTableFromDisk,
                        'url': MBTableFromDisk,
                        'l_artist_recording': MBTableCached,
                        'recording_meta': MBTableFromDisk,
                        'release': MBTableCached,
                        'l_recording_work': MBTableCached,
                        'artist': MBTableFromDisk,
                        'release_group': MBTableCached,
                        'l_artist_url': MBTableCached,
                        'release_country': MBTableFromDisk,
                        'release_unknown_country': MBTableFromDisk,
                        'release_label': MBTableFromDisk,
                        'l_artist_release': MBTableFromDisk}

        try:
            MBTableClass = tableClasses[tablename]
        except KeyError:
            MBTableClass = MBTableInMemory
        # if tablename in ['track', 'recording', 'url', 'l_artist_recording',
        #                  'recording_meta', 'release', 'l_recording_work',
        #                  'artist', 'release_group', 'l_artist_url',
        #                  'l_release_url', 'medium', 'annotation',
        #                  'l_artist_work', 'work', 'artist_credit',
        #                  'release_label', 'artist_credit_name',
        #                  'release_country', 'l_artist_release']:
        #     table = MBTableFromDisk(tablename, columns)
        # else:
        if MBTableClass == MBTableFromDisk:
            table = MBTableClass(tablename, columns,
                                 indexed_columns.get(tablename, []))
        else:
            table = MBTableClass(tablename, columns)

        table.loadFromFile(filename)

        print('##########################################################  ' +
              f'Read {type(table).__name__}({tablename}). Size:',
              getsize(table), '. len: ', len(table))

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
        if entity.startswith('enum_'):
            record['id_value'] = item['id']
            record['name'] = item['name']
        else:
            for col in dbtable.columns:
                mbcolname = translations.get(col.name, col.name)

                try:
                    record[col.name] = item[mbcolname]
                except KeyError:
                    print(f'Cannot get {entity} item[{mbcolname}]: {item}')
                    raise

#        for fk in dbtable.foreign_keys:
#            if (fk.column.table.name.startswith('enum_') and
#                    fk.column.table.name.endswith('_values')):
#                col_keys = fk.constraint.column_keys
#                if len(col_keys) != 1:
#                    msg = ('Invalid constraint column_keys: %s for fk: %s'
#                           % (col_keys, fk))
#                    raise ValueError(msg)
#                dbenum = musicbrainz_enums[fk.column.table.name]
#                column = col_keys[0]
#                if type(record[column]) == str:
#                    record[column] = dbenum.id_value(record[column])
#                else:
#                    enumtable = table_translations[fk.column.table.name]
#
#                    self.read_entity_table(enumtable)
#                    try:
#                        value = self.entities[enumtable][record[column]]
#                    except KeyError:
#                        print(f'Error obtaining self.entities[{enumtable}]'
#                              f'[record[{column}] == {record[column]}]')
#                        raise
#                    if value:
#                        record[column] = dbenum.id_value(value['name'])
#                        print(f'record column {column} set to '
#                              f'{record[column]}'
#                              ' as value for %s' % value['name'])
#                    else:
#                        record[column] = None
#                        print(f'record column {column} set to None')
#
#            else:
#                col_keys = fk.constraint.column_keys
#                if len(col_keys) != 1:
#                    msg = ('Invalid constraint column_keys: %s for fk: %s'
#                           % (col_keys, fk))
#                    raise ValueError(msg)
#
#                value = record[col_keys[0]]
#                if value:
#                    dbRecord = fk.column.table.select(fk.column == value)
#                    dbRecord = MusicDatabase.execute(dbRecord).fetchone()
#                    # This should maybe use a stack of objects being modified
#                    if not dbRecord:
#                        print('Adding fk', fk.column.table.name,
#                              fk.column.name, value)
#                        tablename = fk.column.table.name
#                        opts = copy.deepcopy(options)
#                        opts.set_inmediate_flag()
#                        self.import_entity(tablename, fk.column.name, value,
#                                           opts)
#
#        MusicDatabase.commit()
        if entity == 'artist_credit_name':
            MusicDatabase.insert_or_update(dbtable, record,
                    and_(dbtable.c.artist_credit_id == record['artist_credit_id'],  # noqa
                         dbtable.c.position == record['position']))
        elif entity == 'link_attribute':
            MusicDatabase.insert_or_update(dbtable, record,
                and_(dbtable.c.link_id == record['link_id'],  # noqa
                     dbtable.c.link_attribute_type_id == record['link_attribute_type_id']))  # noqa
        elif entity == 'link_attribute_credit':
            MusicDatabase.insert_or_update(dbtable, record,
                and_(dbtable.c.link_id == record['link_id'],  # noqa
                     dbtable.c.link_attribute_type_id == record['link_attribute_type_id']))  # noqa
        elif entity == 'release_country':
            MusicDatabase.insert_or_update(dbtable, record,
                and_(dbtable.c.release_id == record['release_id'],  # noqa
                     dbtable.c.country_id == record['country_id']))
        elif entity == 'release_unknown_country':
            MusicDatabase.insert_or_update(dbtable, record,
                dbtable.c.release_id == record['release_id']) # noqa
        elif entity == 'release_group_secondary_type_join':
            MusicDatabase.insert_or_update(dbtable, record,
                dbtable.c.release_group_id == record['release_group_id'])  # noqa
        else:
            MusicDatabase.insert_or_update(dbtable, record)

        # extra_import = extra_imports.get(entity, [])

        # for extra_table, extra_column, src_prop in extra_import:
        #    if options.should_follow_table(extra_table):
        #        print('')
        #        print(extra_table, 'options:', str(options))
        #        self.import_extra_data(extra_table, extra_column, src_prop,
        #                               entity, item, options)

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

    def get_mbdump_tableiter(self, tablename):
        filename = os.path.join(self.directory, 'mbdump', tablename)
        columns = self.names[tablename]
        table = MBTableIter(tablename, columns)
        table.loadFromFile(filename)
        return table

    def import_enum_table(self, tablename):
        dbenum = musicbrainz_enums[tablename]
        enumtable = table_translations[tablename]
        filename = os.path.join(self.directory, 'mbdump', enumtable)
        columns = self.names[enumtable]
        print(columns)
        table = MBTableIter(tablename, columns)

        table.loadFromFile(filename)

        for item in table.getlines():
            dbenum.import_value(item['id'], item['name'])
        MusicDatabase.commit()

    def import_elements_from_table_old(self, tablename, *, uuids=[], ids=[],
                                       linkids=[], artistids=[]):
        """Import entities from tablename that match uuids or ids.

        (only one can be set).
        """
        self.load_musicbrainz_schema_importer_names()
        if (tablename.startswith('enum_') and
                tablename.endswith('_values')):
            return self.import_enum_table(tablename)

        table = self.get_mbdump_tableiter(tablename)
        print(f'Importing elements from table {tablename}...')

        if ids:
            for item in table.getlines_matching_values('id', ids):
                self.save_entity_item(tablename, item, MBOptions())
        elif uuids:
            for item in table.getlines_matching_values('gid', uuids):
                self.save_entity_item(tablename, item, MBOptions())
        elif linkids:
            for item in table.getlines_matching_values('link', linkids):
                self.save_entity_item(tablename, item, MBOptions())
        elif artistids:
            for item in table.getlines_matching_values('artist', artistids):
                self.save_entity_item(tablename, item, MBOptions())
        else:
            for item in table.getlines():
                self.save_entity_item(tablename, item, MBOptions())
        MusicDatabase.commit()

    def import_elements_from_table(self, tablename, *, column=None, ids=None):
        """Import all entities from tablename or only those that match ids.

        If column is set, then ids is not compared to the 'id' column, but
        to the one specified by column. Note that the column name should be
        a reference to the original musicbrainz table column name.
        """
        if ids == set() or ids == []:
            return
        self.load_musicbrainz_schema_importer_names()
        if (tablename.startswith('enum_') and
                tablename.endswith('_values')):
            return self.import_enum_table(tablename)

        table = self.get_mbdump_tableiter(tablename)
        print(f'Importing elements from table {tablename}...')

        if ids:
            if not column:
                column = 'id'
            for item in table.getlines_matching_values(column, ids):
                self.save_entity_item(tablename, item, MBOptions())
        else:
            for item in table.getlines():
                self.save_entity_item(tablename, item, MBOptions())
        MusicDatabase.commit()

    def convert_uuids_to_ids(self, entity, uuids):
        print(f'Convert {len(uuids)} {entity} uuids to ids...')
        table = self.get_mbdump_tableiter(entity)

        r = set()
        found = set()

        for item in table.getlines_matching_values('gid', uuids):
            found.add(item['gid'])
            r.add(item['id'])

        with self.uuids_not_found_mutex:
            self.uuids_not_found[entity] = uuids.difference(found)
            print(len(self.uuids_not_found[entity]), entity, 'uuids not found')

        print(f'...converted {len(r)} {entity} uuids to ids')
        return (entity, r)

    def get_entity_ids_from_relationship_table(self, entity, r_entity, pos,
                                               both_checked=False):
        if pos == 0:
            relation = f'l_{entity}_{r_entity}'
        elif pos == 1:
            relation = f'l_{r_entity}_{entity}'

        table = self.get_mbdump_tableiter(relation)

        colname = f'entity{pos}'
        r_colname = f'entity{1-pos}'
        result = set()
        link_ids = set()
        ids = set()
        if both_checked:
            for item in table.getlines():
                if (item[colname] in self.ids[entity] and
                        item[r_colname] in self.ids[r_entity]):
                    result.add(item[colname])
                    link_ids.add(item['link'])
                    ids.add(item['id'])
        else:
            for item in table.getlines():
                if item[r_colname] in self.ids[r_entity]:
                    result.add(item[colname])
                    link_ids.add(item['link'])
                    ids.add(item['id'])
                    # if item['link'] == 1099:
                    #    import pdb
                    #    pdb.set_trace()
        return result, link_ids, relation, ids

    def import_relationship_table(self, entity, r_entity, pos):
        if pos == 0:
            tablename = f'l_{entity}_{r_entity}'
        elif pos == 1:
            tablename = f'l_{r_entity}_{entity}'
        print(f'Importing {tablename}')

        self.import_elements_from_table(tablename, ids=self.ids[tablename])

    def get_artist_credit_ids_for_entity(self, entity):
        table = self.get_mbdump_tableiter(entity)

        return (entity, set(x['artist_credit']
                for x in table.getlines_matching_values('id',
                                                        self.ids[entity])))
        # if x['id'] in self.ids[entity]))

    def get_artists_from_artist_credit_ids(self):
        table = self.get_mbdump_tableiter('artist_credit_name')

        return set(x['artist'] for x in table.getlines_matching_values(
                   'artist_credit', self.ids['artist_credit']))
        # if x['artist_credit'] in self.ids['artist_credit'])

    def get_link_attribute_types_from_link_attributes(self):
        table = self.get_mbdump_tableiter('link_attribute')

        return set(x['attribute_type'] for x in table.getlines_matching_values(
                   'link', self.ids['link']))

    def get_parent_link_attribute_types(self, ids):
        table = self.get_mbdump_tableiter('link_attribute_type')

        return set(x['parent'] for x in table.getlines_matching_values(
                   'id', ids))

    def get_mediums_from_release_ids(self):
        table = self.get_mbdump_tableiter('medium')

        return set(x['id'] for x in table.getlines()
                   if x['release'] in self.ids['release'])

    def get_release_groups_from_release_ids(self):
        table = self.get_mbdump_tableiter('release')

        return set(x['release_group']
                   for x in table.getlines_matching_values(
                   'id', self.ids['release']))

    def get_labels_from_release_ids(self):
        table = self.get_mbdump_tableiter('release_label')

        return set(x['label']
                   for x in table.getlines_matching_values(
                   'release', self.ids['release']))

    def get_tracks_and_recordings_from_medium_ids(self):
        table = self.get_mbdump_tableiter('track')

        result = [(x['id'], x['recording'])
                  for x in table.getlines_matching_values(
                  'medium', self.ids['medium'])]
        return zip(*result)

    def get_files_to_check_manually_for_missing_uuids(self):
        tab_cols = {'artist': [('songs_mb_artistids', 'artistid'),
                               ('songs_mb_albumartistids', 'albumartistid')],
                    'recording': [('songs_mb', 'recordingid')],
                    'release': [('songs_mb', 'releaseid')],
                    'release_group': [('songs_mb', 'releasegroupid')],
                    'track': [('songs_mb', 'releasetrackid')],
                    'work': [('songs_mb_workids', 'workid')]}

        c = MusicDatabase.getCursor()
        paths = set()
        for entity, uuids in self.uuids_not_found.items():
            if not uuids:
                continue
            for tablename, column in tab_cols[entity]:
                sql = text(f'SELECT path, {column} FROM songs, {tablename} '
                           f'where id = song_id and {column} in :uuids '
                           'ORDER BY path')
                result = c.execute(sql, {'uuids': tuple(uuids)})
                paths.update((x[0], entity, x[1]) for x in result.fetchall())
        return paths

    def get_files_to_check_manually_for_missing_ids(self):
        table = self.get_mbdump_tableiter('track')

        c = MusicDatabase.getCursor()
        paths = set()
        # Check tracks which reference recordings that
        # haven't been referenced before.
        for x in table.getlines_matching_values('id', self.ids['track']):
            if x['recording'] not in self.ids['recording']:
                sql = text('SELECT path FROM songs, songs_mb '
                           'where id = song_id and releasetrackid = :uuid ')
                result = c.execute(sql, {'uuid': x['gid']})
                paths.update(x[0] for x in result.fetchall())
        return paths

    def get_files_to_check_manually_for_missing_works(self):
        table = self.get_mbdump_tableiter('l_recording_work')
        recordings = self.get_mbdump_tableiter('recording')

        print('Preloading recordings...')
        recordings_uuid = {rec['id']: rec['gid']
                           for rec in recordings.getlines()}
        print('Iterating on l_recording_work ...')

        c = MusicDatabase.getCursor()
        paths = set()
        sql = text('SELECT path FROM songs, songs_mb '
                   'where id = song_id and recordingid = :uuid ')
        # Check recordings which reference works that haven't been
        # referenced before.
        for x in table.getlines_matching_values('entity0',
                                                self.ids['recording']):
            if x['entity1'] not in self.ids['work']:
                result = c.execute(sql, {'uuid':
                                         recordings_uuid[x['entity0']]})
                r = result.fetchone()
                paths.add(r[0])
        return paths

    def load_data_to_import(self, artist_credits=True, mediums=True,
                            linked_entities=True):
        mbdb = MusicBrainzDatabase()
        self.uuids = {}
        self.uuids['artist'] = mbdb.get_all_artists()
        self.uuids['recording'] = mbdb.get_all_recordings()
        self.uuids['release_group'] = mbdb.get_all_releasegroups()
        self.uuids['release'] = mbdb.get_all_releases()
        self.uuids['track'] = mbdb.get_all_tracks()
        self.uuids['work'] = mbdb.get_all_works()

        self.uuids_not_found = {}
        self.ids = {}
        self.ids['event'] = set()
        self.ids['artist_credit'] = set()
        self.ids['series'] = set()
        self.ids['link'] = set()
        self.ids['label'] = set()
        for entity, uuids in self.uuids.items():
            _, self.ids[entity] = self.convert_uuids_to_ids(entity, uuids)
            print(entity, len(self.ids[entity]), 'ids')

        # futures = []
        # with concurrent.futures.ThreadPoolExecutor() as executor:
        #     futures = {executor.submit(
        #                self.convert_uuids_to_ids, ent, uuids)
        #                for ent, uuids in self.uuids.items()}
        #     print('Waiting for threads to finish...')
        #     for future in concurrent.futures.as_completed(futures):
        #         entity, ids = future.result()
        #         self.ids[entity] = ids
        #         print(f'entity {entity} finished: {len(ids)} ids')

        ids = self.get_release_groups_from_release_ids()
        self.ids['release_group'].update(ids)

        ids = self.get_labels_from_release_ids()
        self.ids['label'].update(ids)

        if mediums:
            self.ids['medium'] = self.get_mediums_from_release_ids()
            print('-------')
            print('tracks: ', len(self.ids['track']))
            print('recording: ', len(self.ids['recording']))
            # Add all recordings from all mediums so we can show
            # also missing recordings from releases
            track_ids, recording_ids = \
                self.get_tracks_and_recordings_from_medium_ids()
            self.ids['recording'].update(recording_ids)
            self.ids['track'].update(track_ids)

            print('tracks: ', len(self.ids['track']))
            print('recording: ', len(self.ids['recording']))

        if artist_credits:
            futures = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # for ent in ['recording','release','release_group','track']:
                #    print(f'Running thread for artist_credit_ids for {ent}')
                #    future = executor.submit(
                #        self.get_artist_credit_ids_for_entity, ent)
                #    futures.append((ent, future))

                entities = ['recording', 'release', 'release_group', 'track']
                futures = {executor.submit(
                    self.get_artist_credit_ids_for_entity, ent)
                    for ent in entities}

                print('Waiting for threads to finish...')
                for future in concurrent.futures.as_completed(futures):
                    entity, ids = future.result()
                    self.ids['artist_credit'].update(ids)
                    print(f'entity {entity} finished')
                    print('artist_credit ids', len(self.ids['artist_credit']))

            print('artist ids', len(self.ids['artist']))
            ids = self.get_artists_from_artist_credit_ids()
            self.ids['artist'].update(ids)
            print('artist ids', len(self.ids['artist']))

        if linked_entities:
            for entity, relations in related_entities_to_import.items():
                for rel, event_pos, both_checked in relations:
                    entity_ids, link_ids, tablename, table_ids = (
                        self.get_entity_ids_from_relationship_table(
                            entity, rel, event_pos, both_checked))
                    self.ids[entity].update(entity_ids)
                    self.ids['link'].update(link_ids)
                    try:
                        self.ids[tablename].update(table_ids)
                    except KeyError:
                        self.ids[tablename] = table_ids

                    print(entity, rel, len(self.ids[entity]), ' + ids')

            self.ids['link_attribute_type'] = \
                self.get_link_attribute_types_from_link_attributes()
            parent_link_attribute_types = \
                self.get_parent_link_attribute_types(
                    self.ids['link_attribute_type'])
            self.parent_ids['link_attribute_type'] = \
                parent_link_attribute_types

        print(sorted(self.ids.keys()))

    def import_table(self, tablename):
        if tablename not in self.ids:
            raise ValueError(f'Table {tablename} not found')

        self.import_elements_from_table(tablename, ids=self.ids[tablename])

    def get_song_ids_for_recordings_dict(self):
        c = MusicDatabase.getCursor()
        sql = text('SELECT mr.id recording_id, song_id '
                   '  FROM songs_mb, musicbrainz.recording mr '
                   ' WHERE mr.mbid = songs_mb.recordingid ORDER BY 1')
        pairs = c.execute(sql)
        recording_id, song_id = pairs.fetchone()
        last_recording_id = recording_id
        songs = [song_id]
        result = {}
        for recording_id, song_id in pairs.fetchall():
            if recording_id != last_recording_id:
                result[last_recording_id] = songs
                songs = [song_id]
                last_recording_id = recording_id
            else:
                songs.append(song_id)
        result[last_recording_id] = songs
        return result

    def get_album_ids_for_release_groups_dict(self):
        c = MusicDatabase.getCursor()
        sql = text('SELECT mr.release_group_id , album_id '
                   '  FROM album_release, musicbrainz.release mr'
                   ' WHERE release_id = mr.id '
                   '  ORDER BY 1')
        pairs = c.execute(sql)
        rg_id, album_id = pairs.fetchone()
        last_rg_id = rg_id
        albums = [album_id]
        result = {}
        for rg_id, album_id in pairs.fetchall():
            if rg_id != last_rg_id:
                result[last_rg_id] = albums
                albums = [album_id]
                last_rg_id = rg_id
            else:
                albums.append(album_id)
        result[last_rg_id] = albums
        return result

    def import_ratings_from_table(self, entity, musicbrainzUserID):
        self.load_musicbrainz_schema_importer_names()
        if entity == 'recording':
            tablename = 'recording_meta'
            tgt_tablename = 'songs_ratings'
            tgt_column = 'song_id'
            conversion = self.get_song_ids_for_recordings_dict()
            ids = self.ids['recording']
        elif entity == 'release-group':
            tablename = 'release_group_meta'
            tgt_tablename = 'albums_ratings'
            tgt_column = 'album_id'
            conversion = self.get_album_ids_for_release_groups_dict()
            ids = self.ids['release_group']
        elif entity == 'artist':
            tablename = 'artist_meta'
            tgt_tablename = 'artists_ratings'
            tgt_column = 'artist_id'
            conversion = None
            ids = self.ids['artist']
        table = self.get_mbdump_tableiter(tablename)
        print(f'Importing ratings from table {tablename}...')

        sqlupdate = text(f'UPDATE {tgt_tablename} '
                         f'   SET rating=:rating '
                         f' WHERE user_id={musicbrainzUserID} '
                         f'   AND {tgt_column}=:tgt_entity')

        sqlinsert = text(f'INSERT INTO {tgt_tablename} '
                         f'(user_id, {tgt_column}, rating) '
                         f'VALUES ({musicbrainzUserID}, :tgt_entity, :rating)')
        c = MusicDatabase.getCursor()
        for item in table.getlines_matching_values('id', ids):
            if item['rating'] is None:
                continue
            if conversion:
                try:
                    tgt_entity_ids = conversion[item['id']]
                except KeyError:
                    print(f'{entity} id {item["id"]} cannot be converted '
                          f'to {tgt_column}')
                    continue
            else:
                tgt_entity_ids = [item['id']]

            for tgt_entity_id in tgt_entity_ids:
                r = c.execute(sqlupdate.bindparams(tgt_entity=tgt_entity_id,
                                                   rating=item['rating'] / 10))

                if r.rowcount == 0:
                    c.execute(sqlinsert.bindparams(tgt_entity=tgt_entity_id,
                                                   rating=item['rating'] / 10))
        c.commit()

    def import_ratings(self):
        musicbrainzUserID = MusicDatabase.getUserID('_musicbrainz',
                                                    create=True)
        MusicDatabase.setUserActive(musicbrainzUserID, False)

        self.import_ratings_from_table('recording',
                                       musicbrainzUserID=musicbrainzUserID)
        self.import_ratings_from_table('release-group',
                                       musicbrainzUserID=musicbrainzUserID)
        self.import_ratings_from_table('artist',
                                       musicbrainzUserID=musicbrainzUserID)

    def import_everything(self):
        self.import_enum_table('enum_area_type_values')
        self.import_enum_table('enum_artist_alias_type_values')
        self.import_enum_table('enum_artist_type_values')
        self.import_enum_table('enum_event_type_values')
        self.import_enum_table('enum_release_group_type_values')
        self.import_enum_table('enum_release_status_values')
        self.import_enum_table('enum_language_values')
        self.import_enum_table('enum_gender_values')
        self.import_enum_table('enum_medium_format_values')
        self.import_enum_table('enum_recording_alias_type_values')
        self.import_enum_table('enum_work_type_values')
        self.import_enum_table('enum_place_type_values')
        self.import_enum_table('enum_series_type_values')
        self.import_enum_table('enum_label_type_values')
        self.import_enum_table('enum_instrument_type_values')
        self.import_enum_table('enum_release_group_secondary_type_values')

        self.import_elements_from_table('area')
        self.import_table('artist')
        self.import_table('artist_credit')
        self.import_elements_from_table('artist_credit_name',
                                        column='artist_credit',
                                        ids=self.ids['artist_credit'])
        self.import_elements_from_table('artist_alias',
                                        column='artist',
                                        ids=self.ids['artist'])
        self.import_table('release_group')
        self.import_elements_from_table('release_group_secondary_type_join',
                                        column='release_group',
                                        ids=self.ids['release_group'])

        self.import_table('release')
        self.import_elements_from_table('release_country',
                                        column='release',
                                        ids=self.ids['release'])
        self.import_elements_from_table('release_unknown_country',
                                        column='release',
                                        ids=self.ids['release'])
        self.import_table('label')
        self.import_elements_from_table('release_label',
                                        column='release',
                                        ids=self.ids['release'])
        self.import_table('medium')
        self.import_table('recording')
        self.import_elements_from_table('recording_alias',
                                        column='recording',
                                        ids=self.ids['recording'])
        self.import_table('track')
        self.import_table('work')
        self.import_table('event')
        self.import_table('series')
        self.import_elements_from_table('link_type')
        if 'link_attribute_type' in self.parent_ids:
            (self.import_elements_from_table('link_attribute_type',
             column='id', ids=self.parent_ids['link_attribute_type']))

        self.import_table('link_attribute_type')
        self.import_table('link')
        self.import_elements_from_table('link_attribute_credit',
                                        column='link', ids=self.ids['link'])
        self.import_elements_from_table('link_attribute',
                                        column='link', ids=self.ids['link'])
        for entity, relations in related_entities_to_import.items():
            for rel, event_pos, both_checked in relations:
                self.import_relationship_table(entity, rel, event_pos)

        self.import_ratings()
