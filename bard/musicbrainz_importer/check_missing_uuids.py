#!/usr/bin/python3

from mbimporter import MusicBrainzImporter
from bard.musicdatabase import MusicDatabase
from bard.musicbrainz_database import MusicBrainzDatabase
import sys
import os.path
import re


medium_pattern = re.compile(r'(CD|LP)[0-9]+($| - )')


def albumdirectory(path):
    dirname = os.path.dirname(path)
    (dirname2, basename) = os.path.split(dirname)
    return dirname2 if medium_pattern.match(basename) else dirname


db = MusicDatabase()
mbdb = MusicBrainzDatabase()

importer = MusicBrainzImporter()

importer.load_data_to_import(artist_credits=False, mediums=False,
                             linked_entities=False)
missing_files = []
missing_files2 = []
missing_files = importer.get_files_to_check_manually_for_missing_uuids()
missing_files2 = importer.get_files_to_check_manually_for_missing_ids()
files_with_missing_works = \
    importer.get_files_to_check_manually_for_missing_works()

print('--------------------')
use_directories = True
if use_directories:
    print('Directories to check manually:')
    dirs = set(albumdirectory(path) for path, _, _ in missing_files)

    for dirname in sorted(dirs):
        print(dirname)

    print('----------------- Files with wrong recording uuids:')
    dirs = set(albumdirectory(path) for path in missing_files2)

    for dirname in sorted(dirs):
        print(dirname)

    print('----------------- Files with wrong recording uuids:')
    dirs = set(albumdirectory(path) for path in files_with_missing_works)

    for dirname in sorted(dirs):
        print(dirname)

    sys.exit(0)


print('Files to check manually:')
for path, entity, uuid in missing_files:
    print(path, entity, uuid)

print('----------------- Files with wrong recording uuids:')
for path in missing_files2:
    print(path)

print('----------------- Files with missing works:')
for path in files_with_missing_works:
    print(path)
