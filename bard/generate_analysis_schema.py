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

highlevel_probability_sets = ['highlevel.genre_dortmund',
                              'highlevel.genre_electronic',
                              'highlevel.genre_rosamerica',
                              'highlevel.genre_tzanetakis',
                              'highlevel.ismir04_rhythm',
                              'highlevel.moods_mirex']

highlevel_prob_keys = ['highlevel.genre_dortmund.all.alternative',
                       'highlevel.genre_dortmund.all.blues',
                       'highlevel.genre_dortmund.all.electronic',
                       'highlevel.genre_dortmund.all.folkcountry',
                       'highlevel.genre_dortmund.all.funksoulrnb',
                       'highlevel.genre_dortmund.all.jazz',
                       'highlevel.genre_dortmund.all.pop',
                       'highlevel.genre_dortmund.all.raphiphop',
                       'highlevel.genre_dortmund.all.rock',
                       'highlevel.genre_electronic.all.ambient',
                       'highlevel.genre_electronic.all.dnb',
                       'highlevel.genre_electronic.all.house',
                       'highlevel.genre_electronic.all.techno',
                       'highlevel.genre_electronic.all.trance',
                       'highlevel.genre_rosamerica.all.cla',
                       'highlevel.genre_rosamerica.all.dan',
                       'highlevel.genre_rosamerica.all.hip',
                       'highlevel.genre_rosamerica.all.jaz',
                       'highlevel.genre_rosamerica.all.pop',
                       'highlevel.genre_rosamerica.all.rhy',
                       'highlevel.genre_rosamerica.all.roc',
                       'highlevel.genre_rosamerica.all.spe',
                       'highlevel.genre_tzanetakis.all.blu',
                       'highlevel.genre_tzanetakis.all.cla',
                       'highlevel.genre_tzanetakis.all.cou',
                       'highlevel.genre_tzanetakis.all.dis',
                       'highlevel.genre_tzanetakis.all.hip',
                       'highlevel.genre_tzanetakis.all.jaz',
                       'highlevel.genre_tzanetakis.all.met',
                       'highlevel.genre_tzanetakis.all.pop',
                       'highlevel.genre_tzanetakis.all.reg',
                       'highlevel.genre_tzanetakis.all.roc',
                       'highlevel.ismir04_rhythm.all.ChaChaCha',
                       'highlevel.ismir04_rhythm.all.Jive',
                       'highlevel.ismir04_rhythm.all.Quickstep',
                       'highlevel.ismir04_rhythm.all.Rumba-American',
                       'highlevel.ismir04_rhythm.all.Rumba-International',
                       'highlevel.ismir04_rhythm.all.Rumba-Misc',
                       'highlevel.ismir04_rhythm.all.Samba',
                       'highlevel.ismir04_rhythm.all.Tango',
                       'highlevel.ismir04_rhythm.all.VienneseWaltz',
                       'highlevel.ismir04_rhythm.all.Waltz',
                       'highlevel.moods_mirex.all.Cluster1',
                       'highlevel.moods_mirex.all.Cluster2',
                       'highlevel.moods_mirex.all.Cluster3',
                       'highlevel.moods_mirex.all.Cluster4',
                       'highlevel.moods_mirex.all.Cluster5']


highlevel_probability_sets = list(set(x[:x.find('.all.')]
                                      for x in highlevel_prob_keys))

for highlevel_set in highlevel_probability_sets:
    cols = [('song_id', 'INTEGER PRIMARY KEY'),
            ('value', 'TEXT'), ('probability', 'REAL')]
    cols += [(x[len(highlevel_set) + len('.all.'):].replace('-', '_'), 'REAL')
             for x in highlevel_prob_keys if x.startswith(highlevel_set + '.')]
    table_name = highlevel_set.replace('.', '__')
    sql = (f'CREATE TABLE {schema}.{table_name} (\n   ' +
           ',\n   '.join(f'{colname} {coltype}' for colname, coltype in cols) +
           ''',\n   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE\n)\n''')
    print(sql)


string_columns = ['metadata.version.essentia',
                  'tonal.chords_key',
                  'tonal.chords_scale',
                  'tonal.key_edma.key',
                  'tonal.key_edma.scale',
                  'tonal.key_krumhansl.key',
                  'tonal.key_krumhansl.scale',
                  'tonal.key_temperley.key',
                  'tonal.key_temperley.scale']

tables = {}
for key, value in conversion_dict.items():
    table, col = value
#    print(key, table, col)
    tables.setdefault(table, []).append((col,
                                         'TEXT' if key in string_columns
                                         else 'REAL'))

for tablename, columns in tables.items():
    column_defs = ',\n   '.join(f'{colname} {coltype}'
                                for colname, coltype in columns)
    sql = (f'CREATE TABLE {schema}.{tablename} (\n' +
           '   song_id INTEGER PRIMARY KEY,\n   ' + column_defs +
           ''', FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE\n)\n''')
    print(sql)
