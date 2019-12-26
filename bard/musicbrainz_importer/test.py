#!/usr/bin/python3

from mbimporter import MusicBrainzImporter
from bard.musicdatabase import MusicDatabase
from datetime import datetime

db = MusicDatabase()

#MusicBrainzImporter.retrieve_mbdump_file('mbdump.tar.bz2')
importer = MusicBrainzImporter()
#importer.retrieve_musicbrainz_dumps()
#importer.read_mbdump_table('artist')
time1 = datetime.now()

#x=importer.read_mbdump_table('l_artist_release')

#print(x.getallbycolumn('artist',9555))
#importer.import_entity_uuid('artist', '6416a02b-eda2-4c43-bca8-396ee30b5c74')  # David Lanz

#importer.import_entity_uuid('artist', 'f3d8c154-208d-4efa-b52d-7e9f16adcdae')  # Kitaro
#importer.import_entity_uuid('artist', 'e61318db-a4de-4a2b-99b8-b892dba1b03b')  # Eric Tingstad
#importer.import_entity_uuid('artist', '89da72ac-30be-4950-9b59-ecdf2a9e772d')  # Nancy Rumbel
#importer.import_entity_uuid('release_group', '5bbbeefc-4dae-3c77-82bb-35fc2723b262')  # Woodlands
#importer.import_entity_uuid('release_group', '6b47c9a0-b9e1-3df9-a5e8-50a6ce0dbdbd')  # A night at the opera
#importer.import_entity_uuid('recording', '6244adb7-2a77-4e37-a0aa-6a99267bb655')  # A kind of magic
#importer.import_entity_uuid('work', '73c55095-fa3d-3a59-aa33-d75538233c08')  # A kind of magic
#importer.import_entity_uuid('work', '01058179-a28f-4e0d-96be-0678e3d5e053')  # We will rock you

#importer.import_entity_uuid('recording', '76e7d2cf-b659-4c24-9652-38109a57a266') # Santorini


#importer.import_entity_uuid('label', '48e05d59-41a2-435c-9f74-7df9bc1181cc')  # Private Music

importer.import_entity_uuid('release', 'bc687229-7b3f-449b-93bf-9ba002b1fe60')  # A Kind of Magic

time2 = datetime.now()
print(str(time2 - time1))

importer.import_entity_uuid('release', '9ace7c8c-55b4-4c5d-9aa8-e573a5dde9ad')  # The Works

time3 = datetime.now()
print(str(time3 - time2))
