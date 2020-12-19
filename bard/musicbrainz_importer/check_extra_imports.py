#!/usr/bin/python3

from mbimporter import MusicBrainzImporter
from bard.musicdatabase import MusicDatabase
from bard.musicbrainz_database import MusicBrainzDatabase
import os.path
import re


medium_pattern = re.compile(r'(CD|LP)[0-9]+($| - )')


def albumdirectory(path):
    dirname = os.path.dirname(path)
    (dirname2, basename) = os.path.split(dirname)
    return dirname2 if medium_pattern.match(basename) else dirname


def get_ids_in_songs_mb(column):
    c = MusicDatabase.getCursor()
    sql = f'select distinct {column} from songs_mb'
    result = c.execute(sql)
    return set(x for (x,) in result.fetchall())


def get_song_paths_from_songs_mb(column, uuids):
    c = MusicDatabase.getCursor()
    sql = f'''select path
             from songs
            where id in (select song_id
                           from songs_mb
                          where {column} in :uuid_list)
         order by path'''
    result = c.execute(sql, {'uuid_list': tuple(uuids)})
    return [x for (x,) in result.fetchall()]


db = MusicDatabase()
mbdb = MusicBrainzDatabase()
#artists = mbdb.get_all_artists()
#recordings = mbdb.get_all_recordings()
#releasegroups = mbdb.get_all_releasegroups()
#releases = mbdb.get_all_releases()
#tracks = mbdb.get_all_tracks()
#works = mbdb.get_all_works()

# MusicBrainzImporter.retrieve_mbdump_file('mbdump.tar.bz2')
importer = MusicBrainzImporter()

# importer.retrieve_musicbrainz_dumps()

importer.load_data_to_import(artist_credits=False, mediums=False,
                             linked_entities=False)

release_group = importer.get_mbdump_tableiter('release_group')

print('Preloading recordings...')
release_group_ids = {x['gid']: x['id']
                     for x in release_group.getlines()
                     if x['id'] in importer.ids['release_group']}

r_g_to_import_uuids = release_group_ids.keys()

release_group_ids_from_files = get_ids_in_songs_mb('releasegroupid')

extra_release_group_uuids = set(x for x in r_g_to_import_uuids
                                if x not in release_group_ids_from_files)

print('Extra Release Group:')
print(extra_release_group_uuids)
print(len(importer.ids['release']))

release = importer.get_mbdump_tableiter('release')
ids = set(release_group_ids[uuid] for uuid in extra_release_group_uuids)
release_uuids = []
print('Those releases groups come from the following releases:')
for item in release.getlines_matching_values('release_group', ids):
    if item['id'] not in importer.ids['release']:
        continue
    print(item['id'], item['gid'], item['name'])
    release_uuids.append(item['gid'])

print('Which come from the following files:')
paths = get_song_paths_from_songs_mb('releaseid', release_uuids)
for path in paths:
    print(path)
