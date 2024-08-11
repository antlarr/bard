# Release history

## Next release

#### New features and improvements:
* Very much improved initial bard usage experience. A number of issues have been fixed when using bard for the first time.
  * Fix creating schemas in the initial database creation with postgresql
  * Fix initial case when there's no rating in the db
* Refactor update process which is now much faster
* Use SQLAlchemy >= 2.0
* Add compatibility with latest MusicBrainz database schema and other improvements to MusicBrainz data importer
* Re-decode audio with lower sample rate to use less resources when a file is using too much memory (usually DSD128 and such files).
* Commit each song to database as they're processed
* Add a verbose parameter to getSongUserRatings and getSongAvgRatings
* Do not use `av_init_packet` which is deprecated in ffmpeg
* Ignore lrc and webm files
* Fix format and decode property and decode message names
* Add alembic support which should allow automatic database migration in the future to new versions.
* Allow to specify a database host and port in the configuration
* Add a --length-threshold parameter to compare-dirs
* Print timing output to test scanning speed
* Reduce the buffer size as much as needed to fix DSD file support
* Normalize more tags correctly, including ab:genre and ab:mood tags
* Allow to work without essentia installed
* Add webp support for cover images
* Draw percentage bars when doing a backup
* Improve documentation

#### New commands:
* New command `calculate-dr` to calculate the Dynamic Range of songs
* New command `scan-file` that reads a file and checks if there are similar songs in the database without importing it.
* New command `mb-check-redirected-uuids` that checks if there are songs in the database that have old obsolete MusicBrainz UUIDs that should be retagged with new ones.
* New parameter `--show-decode-messages` to the `info` command that shows warning/error decode messages.
* Update the bash completion script

#### web-ui:
* Update JQuery-UI to 1.13.2
* Update jquery to 3.7.0
* Start adding support for playing music on different devices
* Remove context menu support
* Add test code to create a context menu

#### picard script:
* Merge joinphrase " con " with " y " when saving files
* Fix use of artists and support useonlyfirstartist
* When processing files already organized, keep genres and images

## 0.5.0 (2021-01-10)

This release improves many areas making it easier to install, configure and use Bard for a new user as well as adding tons of new features and fixes.

#### New features and improvements:
* Big refactor of database engine which now uses sqlalchemy models to create all schemas and to perform many of the queries. Also alembic is now used to handle database schema migrations.
* Integration of essentia so Bard can now perform high level analysis of music and use classifier models to automatically extract more information from songs.
* Generated playlists (aka Dynamic playlists). Playlists that add songs automatically when the current song approaches the last song on the playlist.
* Use the BARDCONFIGFILE environment variable to specify the config file to use (the default is ~/.config/bard)
* Refactor how artist images are stored in the database.
* Add mediaSession / metadata support in bard web so the KDE Plasma media player applet shows information about the bard player and can also control it.
* Add feature to select which artists to show when browsing artists on the web ui. This way the user can select if browsing all artists,
  only "main artists" (artists who are credited in a release group or release) or "main+ artists" (artists who are credited in a release group, release or recording).
* Import also the collaborators relationship and use it in the web ui (This is used for example to relate Jon Anderson and Vangelis with
  the "Jon and Vangelis" artist).
* Installing bard now installs web static files and jinja templates to the package directory so `bard web` can no longer needs to be run from the source directory.
* Add more config defaults and improve the handling of config values
* Add support to process wav and dsf files (with id3 tags)
* Add the Bard plugin for Picard and a recommended file naming script to the `picard_plugin` directory.
* Add LOTS of documentation
* Make the generate-keys.sh script more user friendly

#### New commands:
* New command `analyze-songs` to perform a highlevel analysis of the collection.
* The `ls`/`list` command now has a `--duration` flag to show the duration of each song listed.
* The `ls`/`list` command now has new `--rating`, `--my-rating` and `--others-rating` flags to filter
the listing using each type of rating (i.e. `bard ls --rating "> 8"`)
* Add `update-musicbrainz-artists` command to search for artist images in directories containing an `.artist_mbid` file.
* Add `-a`/`--show-analysis` parameter to the `info` command to show the analysis information of a song.
* Add new `init` command to initialize the database and create an example config file.
* New command `process-songs`, a shortcut for `find-audio-duplicates` + `analyze-songs`.
* New commands `mb-update` and `mb-import` to update and import the data from musicbrainz. Also `mb-import --update` does both at the same time.
* The `update` command has a new `--process` flag which performs all audio processing (like `process-songs`) after the database collection has been updated.

#### New config options:
* Add an 'ignore_extensions' config parameter
* Add a preferred_locales config option instead of having it hardcoded. For example with preferred_locales = ["es", "en"], if an artist has aliases in different locales, a "es" locale is preferred (primary aliases before non primary ones), then "en" locales, and if none of those are avialable, any primary alias followed by non primary ones.
* Rename some config options so now all config options use `snake_case`:
    * `musicPaths` has been renamed to `music_paths`.
    * `storeThreshold` has been renamed to `store_threshold`.
    * `shortSongStoreThreshold` has been renamed to `short_song_store_threshold`.
    * `shortSongLength` has been renamed to `short_song_length`.
    * `immutableDatabase` has been renamed to `immutable_database`.
    * `matchThreshold` has been renamed to `match_threshold`.
    * `musicbrainzTaggedMusicPaths` has been renamed to `musicbrainz_tagged_music_paths`.
    * `sslCertificateChainFile` has been renamed to `ssl_certificate_chain_file`.
    * `sslCertificateKeyFile` has been renamed to `ssl_certificate_key_file`.
    * `databasePath` has been renamed to `database_path`.
    * `translatePaths` has been renamed to `translate_paths`.
    * `pathTranslationMap` has been renamed to `path_translation_map`.
* Rename the `ignore_extensions` config option to `ignore_files` and use globs so it's more flexible.

#### Fixes and other changes:
* Fix length of some files for which mutagen returned a length of 0 seconds
* Normalize also the style TXXX id3 tags
* Improve the song ratings storage in database and small refactor to speed it up
* Fix queries which should be outer joins
* Fix find-audio-duplicates when it's the first time it's run
* Fix importing from musicbrainz when we don't need any item from a table
* Fix importing ratings on newly imported artists
* Add all commands and options to the bash autocompletion scripts
* Keep artist images aspect ratio in the web ui
* Don't print null when a release event has no date assigned
* Also compare the file checksums when comparing files in a backup to recognize files modified since a backup was done.
* Fix sending a non-existing file to the web ui.
* Fix 'hostname' config option which was wrongly referred as 'host'
* Don't fail if ssl_certificate_chain_file or ssl_certificate_key_file don't exist
* Don't fail to create a MBImporter object when mbdump files haven't been downloaded yet
* Create the web private_key file correctly
* Remove the logo rotation animation in the web ui
* Create the musicbrainz_schema_importer_names file on demand

## 0.4.0 (2020-07-12)

This release mainly improves the web ui. The main changes are:

* Much better ratings support for songs, albums, release groups and artists.
* Fix compatibility with python 3.6 (by @cristobalcl )
* Add url support and refactor history management. Now navigating through Bard changes the url shown in the browser and allows
  to link a page so links to artists, release-groups, albums, searches, etc. can be shared or bookmarked.
* Import the release_unknown_country table from musicbrainz
* Much improved album view, showing medium covers if they're different from the main album cover, also release events, and more information.
* Much improved artist view, member-of relationships and release group lists (with release groups separated by types and secondary types).
* Much improved release group view, with album format and disambiguation text information.
* Added flags for release events and the script used to download them from wikipedia.
* Increase storeThreshold to 0.60 so less data is stored in the database when finding duplicates.
* Add the initial work for a configuration dialog (useless for now)
* Import song/album/artist ratings from musicbrainz
* Changes in the database tables, mainly related to the ratings.

## 0.3.2 (2020-04-27)

* Fixes for mpris support reporting the same song twice
* Fix building on archs other than x86_64
* Big speed ups to some database operations
* Improve tag normalization when scanning audio files
* Read embedded cuesheets in flac audio files and store the information in the database. This will allow to distinguish songs within the same file
* Import recording_alias from musicbrainz, which will be used at some point
* web ui changes:
* Custom controls for the media player
* Support for seeking
* Add playlists support
* Play the next song automatically when the current song finishes, continuing the current playlist, album or search result
* Lots of improvements to the search view which now is more congruent with the rest of the interface
* Add caching in the web ui so many operations are much faster now
* Change default font of the application
* Add ratings support (stars representing a rating from 0 to 10 for each song) which allows to be set easily from the playlist/search or album view.

## 0.3.1 (2020-02-02)

* Fix build/installation
* Add --version argument

## 0.3.0 (2020-01-26)

* This release can be used from a terminal and has the following working features:

* Add music files to the collection, parsing metadata tags, audio features and audio fingerprints.
* Store all the parsed and calculated data in a postgresql database.
* Set song ratings.
* Play music (using mpv) selecting what to play or in shuffle mode
* List/Play (select) music by genre. List music genres in the collection.
* Compare songs or full directories to find out if two directories include the same songs, which one has better quality or to find duplicated songs in general, based on the audio, and not on tags.
* Import metadata from musicbrainz for songs in the collection (to the database).

## 0.1.0 (2017-03-01)

* First public release
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
