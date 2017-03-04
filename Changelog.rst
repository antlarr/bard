Release history
###############

Next release
============

-

0.1.0 (2017-03-01)
==================

* First release
* import command: Import files to the Bard's sqlite database
* check-checksum command: Check that the files haven't changed calculating
  their checksum and comparing it with the checksum when they were imported.
* find-audio-duplicates command : Find duplicated imported files comparing
  files checksums, the checksum of the audio track (to check files whose
  audio is exactly the same but have different tags), and an acoustic
  fingerprint calculated with pyacoustid.
* info command: Searches the database for a song and prints its location
  and metadata.
* compare-songs command: Compares two songs (not necessarily imported)
  calculating their acoustic fingerprints.
