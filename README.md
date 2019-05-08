# bard
Bard Music Manager - A database to manage your music, find duplicates and fix tags

# Installation

First, some dependencies have to be installed in order to build bard:

```
sudo zypper in libboost_python3-devel "pkgconfig(libavcodec)" "pkgconfig(libavformat)" "pkgconfig(libswresample)" pkgconfig(libavutil)" python3-pyacoustid python3-mutagen python3-Pillow python3-numpy python3-dbus-python python3-SQLAlchemy python3-pydub
```

If you want to use the web interface (which is still in very early stages of development, and thus not ready for real usage):

```
sudo zypper in python3-Werkzeug python3-Flask python3-Flask-Cors python3-Flask-Login python3-Jinja2 python3-bcrypt
```

If you intend to build the internal bard tests (only recommended if you plan to contribute to bard), then you should also install:

```
sudo zypper in libboost_program_options-devel
```

And now we're ready to build and install bard:

```
python3 setup.py build
python3 setup.py install
```

# Configuration

Before using bard, you need to configure it. Configuring it is very easy and mostly implies
telling it the whole list of directories where you have your music files, so bard can scan
them and extract information. Note that bard will never modify or write over your music files
or directories. All it does is read them, extract tags, perform an audio analysis and write
everything into its database.

You can copy the default configuration file from config/bard (which is installed to
/usr/share/doc/packages/bard) to ~/.config/bard and edit it.

# Usage

```bard update```

will update the internal database with new and modified filed from the directories into the configuration file.

```bard ls Dire%Straits```

will list all songs having Dire.*Straits into their path

```bard play Glass```

will play (using mpv) all songs containing "Glass" into their path

Note that for most bard commands, you can use "search expressions", full paths to a file, or the ID given to a song by bard.

```bard info Maximizing%the%audience```

Will show all information about any song containing "Maximizing.*the.*audience" into its path.

```bard find-audio-duplicates```

Will take a while and analyze all songs, comparing the audio signatures and storing which songs are similar into the database.
To see if one song has any duplicate, just use the ```info``` command. ```bard find-audio-duplicates``` should be run
every time new songs are added to a collection.

```bard compare-dirs -s directory1 directory2```

Will compare two directories and report if the songs in the first directory are a subset of the songs in the second directory.
Being a subset means that files are similar and having equal or less quality (for example if directory1 and directory2 contains
the same songs, but the ones in directory1 are encoded in mp3 128kbps while the songs in directory2 are encoded in mp3 320 kbps).

Note that bard will never remove files. If you find duplicated files, you can remove them and then run ```bard update``` to
let bard know that some files no longer exist.


# License

Bard is distributed under the GPL v3.0 license.
The web interface uses [jQuery](https://jquery.org/), which is licensed under a MIT license.
