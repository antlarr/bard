# bard
Bard Music Manager - A database to manage your music, find duplicates and fix tags

# Installation

Right now there are only prebuilt packages for openSUSE Leap and Tumbleweed. In those cases, you can add my build repository:

`sudo zypper ar obs://home:alarrosa:bard bard-repository`

Once the repository is added, you can install bard with:

`sudo zypper in bard`

# Build from sources

## Install build dependencies

First, some dependencies have to be installed in order to build bard:

```
sudo zypper in libboost_python3-devel "pkgconfig(libavcodec)" "pkgconfig(libavformat)" "pkgconfig(libswresample)" "pkgconfig(libavutil)" python3-pyacoustid python3-mutagen python3-Pillow python3-numpy python3-dbus-python python3-SQLAlchemy python3-pydub python3-SQLAlchemy-Utils python3-alembic python3-paramiko
```

```
sudo apt-get install build-essential python3-dev libavcodec-dev libavformat-dev libswresample-dev libavutil-dev python3-acoustid python3-mutagen python3-numpy python3-sqlalchemy python3-setuptools libboost-python3-dev
```

If you want to use the web interface (which is still in early stages of development, and thus not ready for real usage):

```
sudo zypper in python3-Werkzeug python3-Flask python3-Flask-Cors python3-Flask-Login python3-Jinja2 python3-bcrypt
```

If you want bard to do high level analysis of songs (extracting tonal, rhythm, genre and other features from an audio analysis) you need to install the latest essentia version and its highlevel models. I've prepared openSUSE packages in the bard repository. They can be installed with:

```
sudo zypper in essentia-python essentia-models
```

If you intend to build the internal bard tests (only recommended if you plan to contribute to bard), then you should also install:

```
sudo zypper in libboost_program_options-devel
```

```
sudo apt-get install libboost-program-options-dev
```

## Building bard

And now we're ready to build and install bard:

```
python3 setup.py build
python3 setup.py install
```

# Configuration

Before using bard, you need to configure it. Configuring it is very easy and mostly implies
telling it a list of directories where you have your music files, so bard can scan
them and extract information. Note that bard will never modify or write over your music files
or directories. All it does is read them, extract tags, perform an audio analysis and write
everything into its database.

You can run ```bard init``` to create a basic example config file with a basic structure that
you can edit to configure bard instead of having to do it from scratch.

The example file will be written to the default config file location at `~/.config/bard`.
Edit it and set at least the correct values for the `music_paths` config option. It should
be set to one or more directories where you have music collection. Bard will search for
music recursively on directories under the ones you specify. Note that Bard tries to help
you to organize your music collection and keep it clean, so it will complain if it finds
files it cannot recognize. In those cases you might want to move the files out of your music
collection directory or in some cases, even remove the files. If you want to keep them,
you can add glob patterns to the `ignore_files` config option. Files matching those
globs will be ignored by Bard.

Another important aspect you might want to decide is what database Bard should use.
By default a sqlite database will be used and you don't have to worry about configuring
anything, but if you have the possibility of using a postgresql database, that's preferred.
Refer to the [configuring postgresql](docs/configuring_postgresql.md) documentation for
information on how to do that.

Note that there's currently no migration process from one database to another that means you
might want to choose the database in an early stage so you don't have to process all your
collection again if you change to use another database.

# Usage

```bard update```

will update the internal database with new and modified filed from the directories into the configuration file.
The music files will be read and information like format, embeeded tags, audio quality, file hash, decoded
audio hash, audio fingerprint, etc. will be extracted and stored in the database.

Bard will assign each song found an ID that identifies the song in the database.


```bard ls Dire%Straits```

will list all songs having Dire.*Straits into their path (note that SQL's LIKE wildcards are used here).

```bard play Glass```

will play (using mpv) all songs containing "Glass" into their path

Note that for most bard commands, you can use "search expressions", full paths to a file, or the ID given to a song by bard.

```bard process-songs```

While `bard update` searches for new/removed songs and extracts basic metadata about them, the `process-songs` command
is a lenghtier process that performs music analysis. It's composed on two kinds of analysis that are performed in two steps
and can be run independently with the `find-audio-duplicates` and `analyze-songs` commands.

The first step, equivalent to `find-audio-duplicates`, compares the audio fingerprint of a song to all other
existing fingerprints in the database thus finding similar songs even if they have different format, audio quality or
(in some cases) even if they are different versions of the same song. The similarity between songs is stored in the
database and can be seen with the `info` command when showing information about a song (which shows which songs are similar)
and is also used by the `compare-dirs` and `compare-songs` commands (which compares directories or individual songs).

The second step, equivalent to `analyze-songs`, uses the [essentia](http://essentia.upf.edu/) library to analyze the songs and extract audio features
such as tonality or rhythm information and also uses highlevel classifiers to extract a probability of a song to be
instrumental or having voices (in that case, also, if there's a male or female voice), the probability of a song
to be acoustic, electronic, bright, dark, aggresive, relaxed and even several automatic genre classifiers.

Note that this second step requires a working installation of the [essentia](http://essentia.upf.edu/) library, python bindings
and compatible [classifier models](https://essentia.upf.edu/svm_models/). If you installed Bard using the openSUSE packages,
 this should have been installed automatically.

As a shortcut, you can also use `bard update --process` which runs the `update` command and after it finishes,
it runs the `process-songs` command.

```bard info Maximizing%the%audience```

Will show all information about any song containing "Maximizing.*the.*audience" into its path.

```bard find-audio-duplicates```

Will take a while and analyze all songs, comparing the audio signatures and storing which songs are similar into the database.
To see if one song has any duplicate, just use the ```info``` command. ```bard find-audio-duplicates``` should be run
every time new songs are added to a collection. Note that using `bard process-songs` is recommended instead as it does all
audio processing at once.

```bard compare-dirs -s directory1 directory2```

Will compare two directories and report if the songs in the first directory are a subset of the songs in the second directory.
Being a subset means that files are similar and having equal or less quality (for example if directory1 and directory2 contains
the same songs, but the ones in directory1 are encoded in mp3 128kbps while the songs in directory2 are encoded in mp3 320 kbps).

Note that bard will never remove files. If you find duplicated files, you can remove them and then run ```bard update``` to
let bard know that some files no longer exist.

```bard compare-files file1 file2```

This command compares two songs, extracting the audio fingerprint and comparing them. Since the command extracts the
audio fingerprint instead of using what's stored in the database, it works with files that haven't been added to the
database yet, even for files that are outside the `music_paths` directories. Alternatively, there's a `compare-songs` command
that uses the fingerprint stored in the database and thus it's much faster but can only be used for songs already
added to the database.

# Recommended workflow to organize your music collection

The recommended workflow to organize your music is this:
1) Put all your unorganized music in one or more directories and add those directories to the music_paths config option in Bard.
2) Choose one empty directory where you'll have "correctly organized music", add that directory to the music_paths config option in Bard
   and also put it in the `musicbrainz_tagged_music_paths` config option. Finally open Picard and in the Options dialog, in the File Naming section, set
   the `Destination directory` to that directory too.
3) You can now start using Bard adding songs to its collection, analyzing and playing them and comparing different directories and song files.
4) Install the [Bard plugin and file naming script](picard_plugin/) in Picard.
4) Go over the albums in the unorganized music directories adding MusicBrainz tags with Picard and saving them. Picard will move them
   to the organized folder. I cannot stress enough the importance of correct songs having correct MusicBrainz tags. Note that this
   for example disambiguates Artists who are called the same and even different versions of songs, not only live or studio versions
   but also really different versions of songs that some artists sometime record.
5) After organizing files, you have to run `bard update` so bard notices the files were moved around. Note that Bard will usually
   detect that files were moved and just update their location keeping their ID and extracted analysis information. Bard will detect
   moved files even if their tags or cover art are modified since it checks the audio hash for this.

You can use `bard stats` to get statistics on your collection, including the percentage of songs correctly organized (having MusicBrainz tags)

# MusicBrainz integration

Bard can import information from the MusicBrainz database into your local database. To do this there are two command that have to be run periodically.

```bard mb-update```

This will download the latest MusicBrainz database dumps from the MusicBrainz servers and extract them. Note that the MusicBrainz database is huge so at the time
of writing this, the `mb-update` command requires ~17GB in your home directory (~3.7GB to download and ~13.3GB after uncompression). You can run this command
as many times as you want (it'll just update the downloaded and extracted files) but note that the database dumps are only updated in MusicBrainz servers every
3 or 4 days, so you don't need to execute it every day.

```bard mb-import```

Since the database is so big, we don't want to import all of it as Bard only will use information related to the music you have in the collection. Using
the `mb-import` command, Bard will first gather which information is useful to it and then import only that. Note that only the information about songs with
correct MusicBrainz tags will be imported (which makes it important to use Picard and organize your music correctly). As an example, note that
Bard will not only import information about the main artist a song is credited to, but also information about other artists related to the song (guest performers,
for example) and information about the release/release group (such as release country, date, etc.).

Note that the web interface currently only shows songs from your collection having MusicBrainz imported data. Songs in the "unorganized music directories"
can be seen from the command line, but the web interface is currently restricted to organized music.

# Doing Backups of your music collection

Currently backups are only done to a different computer which can be accessed using ssh. Check the [backup documentation](docs/backups.md) for more information.

# About music sources

Please, always use music from legal sources and support the artists.

# License

Bard is distributed under the GPL v3.0 license.
The web interface uses [jQuery](https://jquery.org/), which is licensed under a MIT license.
