#!/usr/bin/python3
from bard.analysis_database import conversion_dict, keys_with_stats, \
    keys_with_lists_stats, keys_with_lists, fkeys_with_lists, \
    fkeys_with_lists_of_lists, keys_to_ignore

schema = 'analysis'
sql = f'CREATE SCHEMA {schema}'
print(sql)


def create_table_for_essentia_variable(varname, use_stats_vars=False,
                                       allow_value_list=False,
                                       use_array_of_values=False):
    tablename = varname.replace('.', '__')

    if use_stats_vars:
        tablename += '_stats'
        columns = '''mean REAL,
        minimum REAL,
        maximum REAL,
        stdev REAL,
        var REAL,
        median REAL,
        dmean REAL,
        dmean2 REAL,
        dvar REAL,
        dvar2 REAL'''
    elif use_array_of_values:
        columns = 'values REAL[]'
    else:
        columns = 'value REAL'

    if allow_value_list:
        index = 'song_id INTEGER, pos INTEGER'
        unique = '\n        UNIQUE(song_id, pos),'
    else:
        index = 'song_id INTEGER PRIMARY KEY'
        unique = ''

    sql = (f'''CREATE TABLE {schema}.{tablename} (
        {index},
        {columns},{unique}
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE\n)''')
    print(sql)

    if allow_value_list:
        sql = f'''CREATE INDEX {tablename}_song_id_idx
                  ON {tablename} (song_id)\n'''
        print(sql)


for varname in keys_with_stats:
    if varname in keys_to_ignore:
        continue
    create_table_for_essentia_variable(varname, use_stats_vars=True,
                                       allow_value_list=False)

for varname in keys_with_lists:
    if varname in keys_to_ignore:
        continue
    create_table_for_essentia_variable(varname, use_stats_vars=False,
                                       allow_value_list=False,
                                       use_array_of_values=True)

for varname in keys_with_lists_stats:
    if varname in keys_to_ignore:
        continue
    create_table_for_essentia_variable(varname, use_stats_vars=True,
                                       allow_value_list=True)

for varname in fkeys_with_lists:
    if varname in keys_to_ignore:
        continue
    create_table_for_essentia_variable(varname, use_stats_vars=False,
                                       allow_value_list=True,
                                       use_array_of_values=False)

for varname, col_numbers in fkeys_with_lists_of_lists:
    if varname in keys_to_ignore:
        continue
    create_table_for_essentia_variable(varname, use_stats_vars=False,
                                       allow_value_list=True,
                                       use_array_of_values=True)


string_columns = ['metadata.version.essentia',
                  'tonal.chords_key',
                  'tonal.chords_scale',
                  'tonal.key_edma.key',
                  'tonal.key_edma.scale',
                  'tonal.key_krumhansl.key',
                  'tonal.key_krumhansl.scale',
                  'tonal.key_temperley.key',
                  'tonal.key_temperley.scale',
                  'highlevel.genre_dortmund.value',
                  'highlevel.genre_electronic.value',
                  'highlevel.genre_rosamerica.value',
                  'highlevel.genre_tzanetakis.value',
                  'highlevel.ismir04_rhythm.value',
                  'highlevel.moods_mirex.value']

tables = {}
for key, value in conversion_dict.items():
    table, col = value
    tables.setdefault(table, []).append((col,
                                         'TEXT' if key in string_columns
                                         else 'REAL'))

for tablename, columns in tables.items():
    column_defs = ',\n   '.join(f'{colname} {coltype}'
                                for colname, coltype in columns)
    sql = (f'CREATE TABLE {schema}.{tablename} (\n' +
           '   song_id INTEGER PRIMARY KEY,\n   ' + column_defs +
           ''',\n   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE\n)\n''')
    print(sql)
