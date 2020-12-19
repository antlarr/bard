#!/usr/bin/python3

from bard.musicdatabase import MusicDatabase
from bard.musicbrainz_database import MusicBrainzDatabase
from mbimporter import MusicBrainzImporter
from datetime import datetime
import argparse


def updateMusicBrainzDBDump(verbose):
    print(f'updateMusicBrainzDBDump {verbose}')
    importer = MusicBrainzImporter()
    importer.retrieve_musicbrainz_dumps()


def importData(verbose):
    print(f'importData {verbose}')
    importer = MusicBrainzImporter()
    _ = MusicDatabase()
    _ = MusicBrainzDatabase()

    print('Load data to import')
    time1 = datetime.now()
    importer.load_data_to_import()
    time2 = datetime.now()

    print('Time to load data to import:', str(time2 - time1))

    importer.import_everything()
    time2 = datetime.now()

    print(str(time2 - time1))
    # db = MusicDatabase()
    # mbdb = MusicBrainzDatabase()
    # artists = mbdb.get_all_artists()
    # recordings = mbdb.get_all_recordings()
    # releasegroups = mbdb.get_all_releasegroups()
    # releases = mbdb.get_all_releases()
    # tracks = mbdb.get_all_tracks()
    # works = mbdb.get_all_works()

    # MusicBrainzImporter.retrieve_mbdump_file('mbdump.tar.bz2')
    # importer.read_mbdump_table('artist')

    # x=importer.read_mbdump_table('l_artist_release')

    # print(x.getallbycolumn('artist',9555))
    # importer.import_entity_uuid('artist',  # David Lanz
    #                             '6416a02b-eda2-4c43-bca8-396ee30b5c74')

    # importer.import_entity_uuid('artist',  # Kitaro
    #                             'f3d8c154-208d-4efa-b52d-7e9f16adcdae')
    # importer.import_entity_uuid('artist',  # Eric Tingstad
    #                             'e61318db-a4de-4a2b-99b8-b892dba1b03b')
    # importer.import_entity_uuid('artist',  # Nancy Rumbel
    #                             '89da72ac-30be-4950-9b59-ecdf2a9e772d')
    # importer.import_entity_uuid('release_group',  # Woodlands
    #                             '5bbbeefc-4dae-3c77-82bb-35fc2723b262')
    # importer.import_entity_uuid('release_group',  # A night at the opera
    #                             '6b47c9a0-b9e1-3df9-a5e8-50a6ce0dbdbd')
    # importer.import_entity_uuid('recording',  # A kind of magic
    #                             '6244adb7-2a77-4e37-a0aa-6a99267bb655')
    # importer.import_entity_uuid('work',  # A kind of magic
    #                             '73c55095-fa3d-3a59-aa33-d75538233c08')
    # importer.import_entity_uuid('work',  # We will rock you
    #                             '01058179-a28f-4e0d-96be-0678e3d5e053')

    # importer.import_entity_uuid('recording',  # Santorini
    #                             '76e7d2cf-b659-4c24-9652-38109a57a266')

    # importer.import_entity_uuid('label',  # Private Music
    #                             '48e05d59-41a2-435c-9f74-7df9bc1181cc')

    # importer.import_entity_uuid('release',  # A Kind of Magic
    #                             'bc687229-7b3f-449b-93bf-9ba002b1fe60')
    #
    # time2 = datetime.now()
    # print(str(time2 - time1))
    #
    # importer.import_entity_uuid('release',  # The Works
    #                             '9ace7c8c-55b4-4c5d-9aa8-e573a5dde9ad')
    #
    # time3 = datetime.now()
    # print(str(time3 - time2))

    # importer.import_table('enum_area_type_values')
    # importer.import_table('area')
    # importer.import_table('enum_artist_alias_type_values')
    # importer.import_table('enum_artist_type_values')
    # importer.import_table('enum_release_group_type_values')
    # importer.import_table('enum_release_status_values')
    # importer.import_table('enum_language_values')
    # importer.import_table('enum_gender_values')
    # importer.import_table('enum_medium_format_values')
    # importer.import_table('enum_work_type_values')
    # importer.import_table('enum_place_type_values')
    # importer.import_table('enum_series_type_values')
    # importer.import_table('enum_label_type_values')
    # importer.import_table('artist', artists)
    # importer.import_table('artist')
    # importer.import_table('artist_credit')
    # importer.import_table('release_group')
    # importer.import_table('release')
    # importer.import_table('medium')
    # importer.import_table('recording')
    # importer.import_table('track')
    # importer.import_table('work')


def main():
    main_parser = argparse.ArgumentParser(
        description='Import data from MusicBrainz DB dumps',
        formatter_class=argparse.RawTextHelpFormatter)
    sps = main_parser.add_subparsers(
        dest='command', metavar='command',
        help='''The following commands are available: update-dump, import''')
    parser = sps.add_parser('update-dump',
                            description='Download the latest '
                            'MusicBrainz DB dump')
    parser.add_argument('--verbose', dest='verbose', action='store_true',
                        help='Be verbose')
    parser = sps.add_parser('import',
                            description='Import data from the MB DB dump')
    parser.add_argument('--verbose', dest='verbose',
                        action='store_true', help='Be verbose')
    options = main_parser.parse_args()
    if options.command == 'update-dump':
        updateMusicBrainzDBDump(options.verbose)
    elif options.command == 'import':
        importData(options.verbose)


if __name__ == "__main__":
    main()
