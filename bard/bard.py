from bard.utils import fixTags, calculateFileSHA256, printSongsInfo, \
    fingerprint_AudioSegment, alignColumns, decodeAudio, \
    calculateSHA256_data, formatLength, colorizeTime, colorizeAll
from bard.song import Song, Ratings, DifferentLengthException, \
    CantCompareSongsException
from bard.song_utils import print_song_info
from bard.musicdatabase import MusicDatabase
from bard.musicdatabase_songs import getMusic, getSongs, getSongsAtPath, \
    getSongsFromIDorPath
from bard.terminalcolors import TerminalColors
from bard.terminalkeyboard import ask_user_to_choose_one_option
from bard.comparesongs import compareSongSets
from bard.backup import backupMusic
from bard import __version__
import chromaprint
from collections import namedtuple
from collections.abc import MutableSet
from sqlalchemy import text
import urllib.parse
import dbus
import sys
import os
import datetime
import re
import numpy
import time
import random
import mutagen
import argparse
import subprocess
import fnmatch
from dataclasses import dataclass
from argparse import ArgumentParser
import bard.config as config
from bard.user import requestNewPassword
from bard.musicbrainz_database import MusicBrainzDatabase
from bard.album import albumPath
from bard.playlistmanager import PlaylistManager
from bard.analysis_database import AnalysisDatabase, SongAnalysis, \
    AnalysisImporter
from bard.musicbrainz_importer.mbimporter import MusicBrainzImporter
try:
    import importlib.resources as importlib_resources
except ImportError:
    # In PY<3.7 fall-back to backported `importlib_resources`.
    import importlib_resources

ComparisonResult = namedtuple('ComparisonResult', ['offset', 'similarity'])

bard = None


@dataclass
class Query:
    root: str = None
    genre: str = None
    my_rating: str = None
    others_rating: str = None
    rating: str = None
    user_id: int = None

    def __post_init__(self):
        if ((self.rating or self.my_rating or self.others_rating) and
                not self.user_id):
            self.user_id = MusicDatabase.getUserID(config.config['username'])

    def __bool__(self):
        return bool(self.root or self.genre or self.my_rating or
                    self.others_rating or self.rating)


def normalized(v):
    s = sum(v)
    return map(lambda x: x / s, v)


class SongSet(MutableSet):
    def __init__(self, iterable=[]):
        """Construct a SongSet object."""
        super().__init__()
        self.set = set()
        self.audioHashes = set()
        for song in iterable:
            if isinstance(song, Song):
                if song.id:
                    self.set.add(song.id)
                self.audioHashes.add(song.audioSha256sum())
            elif isinstance(song, int):
                self.set.add(song)
                audio_sha256sum = MusicDatabase.getSongProperties(song)[2]
                self.audioHashes.add(audio_sha256sum)

    def copy(self):
        x = super().copy()
        return x

    def __contains__(self, song):
        if isinstance(song, Song):
            songID = song.id
            songSha256 = song.audioSha256sum()
        else:
            songID = song
            songSha256 = MusicDatabase.getSongProperties(song)[2]
        if songID in self.set:
            return True
        if songSha256 in self.audioHashes:
            return True

        if songID:
            similarSongs = MusicDatabase.getSimilarSongsToSongID(songID, 0.85)
            similarSongs = [x[0] for x in similarSongs]
            print('songs similar to', song, ' : ', similarSongs)
            for itsong in similarSongs:
                if itsong in self.set:
                    return True
        return False

    def add(self, item):
        return self.set.add(item.id)

    def __len__(self):
        return len(self.audioHashes)

    def __iter__(self):
        return self.set.__iter__()

    def discard(self, item):
        return self.set.discard(item)

    def __repr__(self):
        return repr(self.set)


def summation(m, n):
    """Return the sum of numbers from m to n."""
    if m >= n:
        return 0
    return (n + 1 - m) * (n + m) / 2


def compare_AudioSegments(audio1, audio2, showAudioOffsets=True):
    fpa1 = fingerprint_AudioSegment(audio1)
    fpa2 = fingerprint_AudioSegment(audio2)
    dfpa1 = chromaprint.decode_fingerprint(fpa1)
    dfpa2 = chromaprint.decode_fingerprint(fpa2)

    store_threshold = config.config['store_threshold']
    short_song_store_threshold = config.config['short_song_store_threshold']
    short_song_length = config.config['short_song_length']
    from bard.bard_ext import FingerprintManager
    fpm = FingerprintManager()
    fpm.setMaxOffset(100)
    fpm.setCancelThreshold(store_threshold)
    fpm.setShortSongCancelThreshold(short_song_store_threshold)
    fpm.setShortSongLength(short_song_length)
    fpm.addSong(1, dfpa1[0], len(audio1) / 1000)
    fpm.addSong(2, dfpa2[0], len(audio2) / 1000)

    values = fpm.compareSongsVerbose(1, 2)
    if showAudioOffsets:
        for offset, similarity in values:
            if similarity > 0.59:
                print(offset, similarity)

    (offset, similarity) = max(values, key=lambda x: x[1])
    return (offset, similarity)


def normalizeDate(date):
    if type(date) == int:
        return date
    if type(date) == str and date == '':
        return 0

    x = re.match('.*([0-9]{4}).*', date)
    if not x:
        print('Wrong date: %s' % date)
        return 0
    return int(x.group(1))


def normalizeTrack(track):
    if type(track) == int:
        return track
    pos = track.find('/')
    if pos != -1:
        return int(track[:pos])
    return int(track)


def walktree(path):
    files = []
    dirs = []
    for entry in os.scandir(path):
        if entry.is_file():
            #t = entry.stat().st_mtime
            # print(entry.path)
            files.append(entry)
        elif entry.is_dir(follow_symlinks=True):
            dirs.append(entry)

    yield path, dirs, files

    for directory in dirs:
        yield from walktree(directory.path)


class Bard:

    def __init__(self):
        """Construct a Bard object."""
        self.db = None
        self.ignore_files = []
        self.excludeDirectories = []
        self.playlist_manager = None
        self.songMTimeCache = {}

        config.load_configuration()
        if config.config is None:
            return None

        self.db = MusicDatabase()
        self.ignore_files = ['*.jpg', '*.jpeg', '*.bmp', '*.tif', '*.png',
                             '*.gif', '*.xcf', '*.webp', '*.avif',
                             '*.m3u', '*.pls', '*.cue', '*.m3u8', '*.au',
                             '*.mid', '*.kar', '*.lyrics', '*.lrc',
                             '*.url', '*.lnk', '*.ini', '*.rar', '*.zip',
                             '*.war', '*.swp',
                             '*.txt', '*.nfo', '*.doc', '*.rtf', '*.pdf',
                             '*.html', '*.log', '*.htm',
                             '*.sfv', '*.sfw', '.directory', '*.sh',
                             '*.contents', '*.torrent', '*.cue_', '*.nzb',
                             '*.md5', '*.gz',
                             '*.fpl', '*.wpl', '*.accurip', '*.db', '*.ffp',
                             '*.flv', '*.mkv', '*.m4v', '*.mov', '*.mpg',
                             '*.mpeg', '*.avi', '*.webm',
                             '.artist_mbid', '.releasegroup_mbid']
        self.ignore_files += config.config['ignore_files']

        self.excludeDirectories = ['covers', 'info']
        self.playlist_manager = PlaylistManager()

    def getCurrentlyPlayingSongs(self):
        bus = dbus.SessionBus()
        names = [x for x in bus.list_names()
                 if x.startswith('org.mpris.MediaPlayer2.mpv')]
        if len(names) == 0:
            return []
        songs = []
        pausedSongs = []
        path = None
        playingSongPath = None
        for name in names:
            mpv = bus.get_object(name, '/org/mpris/MediaPlayer2')
            properties = dbus.Interface(mpv, 'org.freedesktop.DBus.Properties')
            playbackStatus = properties.Get('org.mpris.MediaPlayer2.Player',
                                            'PlaybackStatus')
            if playbackStatus != 'Playing' and playbackStatus != 'Paused':
                continue
            metadata = properties.Get('org.mpris.MediaPlayer2.Player',
                                      'Metadata')
            url = urllib.parse.urlparse(metadata['xesam:url'])
            path = urllib.parse.unquote(url.path)
            newSongs = getSongsAtPath(path, exact=True)
            if playbackStatus == 'Playing':
                playingSongPath = path
                songs.extend([x for x in newSongs
                              if x.id not in [y.id for y in songs]])
            else:
                pausedSongs.extend([x for x in newSongs if x.id not in
                                    [y.id for y in pausedSongs]])

        if songs:
            return songs
        if len(pausedSongs) == 1:
            return pausedSongs

        if playingSongPath:
            print("Couldn't find song in database:", playingSongPath)
        return []

    def addSong(self, path, rootDir=None, removedSongsAudioSHA256={},
                mtime=None, commit=True, verbose=False):
        if config.config['immutable_database']:
            print("Error: Can't add song %s : "
                  "The database is configured as immutable" % path)
            return None, None
        isSongInDatabase = MusicDatabase.isSongInDatabase(path, file_mtime=mtime)
        if isSongInDatabase == 1:
            #if verbose:
            #    print('Already in db: %s' % path)
            return None, None
        elif isSongInDatabase == -1:
            print(f'Updating song {path}')
            songStatus = 'updated'
        else:
            print(f'Adding song {path}')
            songStatus = 'new'

        song = Song(path, rootDir=rootDir)
        if not song.isValid:
            msg = f'Song {path} is not valid'
            raise Exception(msg)

        try:
            removedSongs = removedSongsAudioSHA256[song.audioSha256sum()]
        except KeyError:
            pass
        else:
            if not MusicDatabase.songExistsInDatabase(path=song.path()):
                if len(removedSongs) > 1:
                    msg = f'Choose the removed song that was moved to {path}:'
                    options = [song.path() for song in removedSongs]
                    selected = ask_user_to_choose_one_option(options, msg)
                    removedSong = removedSongs[selected]
                else:
                    removedSong = removedSongs[0]

                song.moveFrom(removedSong)
                songStatus = 'renamed'
            else:
                removedPaths = '\n'.join([x.path() for x in removedSongs])
                print(f'{removedPaths} was/were removed and {song.path()} is '
                      'being updated but was already in database, so the '
                      'removed song(s) won\'t be moved to it.')
                removedSong = None
        MusicDatabase.addSong(song)

        if commit:
            MusicDatabase.commit()

        return song.id, songStatus


    def addDirectoryRecursively(self, directory, verbose=False,
                                removedSongsSHA256={}):
        if config.config['immutable_database']:
            print("Error: Can't add directory %s : "
                  "The database is configured as immutable" % directory)
            return None
        songsIDs = {'new': [], 'updated': [], 'renamed': []}
        if not directory.endswith('/'):
            directory += '/'
        for dirpath in sorted(self.songMTimeCache.keys()):
            if not dirpath.startswith(directory):
                continue

            filenames_mtimes = self.songMTimeCache[dirpath]
            #if verbose:
            #    print('New dir: %s' % dirpath)
            #filenames.sort()
            for filename in sorted(filenames_mtimes.keys()):
                mtime = filenames_mtimes[filename]
                path = os.path.join(dirpath, filename)
                id_, songStatus = self.addSong(path, rootDir=directory,
                                   removedSongsAudioSHA256=removedSongsSHA256,
                                   mtime=mtime, commit=True, verbose=verbose)
                if id_:
                    songsIDs[songStatus].append(id_)
            MusicDatabase.commit()

        return songsIDs


    def add(self, args, verbose=False, removedSongsAudioSHA256={}):
        songsIDs = {'new': [], 'updated': [], 'renamed': []}
        for arg in args:
            if os.path.isfile(arg):
                id_, songStatus = (self.addSong(os.path.normpath(arg),
                                   removedSongsAudioSHA256=removedSongsAudioSHA256))  # noqa
                if id_:
                    songsIDs[songStatus].append(id_)

            elif os.path.isdir(arg):
                if verbose:
                    print('Adding directory recursively:', arg)
                r = self.addDirectoryRecursively(os.path.normpath(arg),
                                                 verbose,
                                                 removedSongsAudioSHA256)
                if r:
                    songsIDs['new'].extend(r['new'])
                    songsIDs['updated'].extend(r['updated'])
                    songsIDs['renamed'].extend(r['renamed'])
        return songsIDs

    def cacheFiles(self, paths, verbose=False):
        cache_by_dir = {}
        mtime_cache = {}

        for directory in paths:
            for dirpath, direntries, fileentries in walktree(directory):
                for entry in direntries[:]:
                    if entry.name in self.excludeDirectories:
                        direntries.remove(entry)

                files_mtime = {}
                for entry in fileentries:
                    if any(fnmatch.fnmatch(entry.name.lower(), pattern)
                           for pattern in self.ignore_files):
                        continue

                    files_mtime[entry.name] = entry.stat().st_mtime

                mtime_cache[dirpath] = files_mtime

        return mtime_cache


    def update(self, paths, verbose=False):
        if verbose:
            t_init = time.time()
            print("pre cacheFiles...")

        self.songMTimeCache = self.cacheFiles(paths, verbose)

        removedSongIDs = set()
        removedSongs = []

        if verbose:
            t_1 = time.time()
            print("post cacheFiles", t_1 - t_init)
            print("checkSongsExistenceInPaths...")

        def storeRemovedSongs(song):
            #print('removed song:', song.path())
            if song.id not in removedSongIDs:
                removedSongIDs.add(song.id)
                removedSongs.append(song)

        self.checkSongsExistenceInPaths(paths, verbose=verbose,
                                        callback=storeRemovedSongs)
        if verbose:
            t_2 = time.time()
            print("post checkSongsExistenceInPaths", t_2 - t_1)
            print("removedSongsAudioSHA256 initializing...")
        removedSongsAudioSHA256 = {}
        for song in removedSongs:
            removedSongsAudioSHA256.setdefault(song.audioSha256sum(),
                                               []).append(song)
        if verbose:
            t_3 = time.time()
            print("removedSongsAudioSHA256 initialized", t_3 - t_2, t_3 - t_init)
            print(removedSongsAudioSHA256)
            print("adding...", paths)

        songIDs = self.add(paths, verbose=verbose,
                       removedSongsAudioSHA256=removedSongsAudioSHA256)
        if verbose:
            t_4 = time.time()
            print("added", t_4 - t_3, t_4 - t_init)

        for song in removedSongs:
            if not song.fileExists():
                print('Removing song', song.path())
                self.db.removeSong(song)

        MusicDatabase.removeOrphanAlbums()
        if verbose:
            t_5 = time.time()
            print("removed things", t_5 - t_4, t_5 - t_init)

        ids = songIDs['new'] + songIDs['updated'] + songIDs['renamed']

        # do things for new songs
        MusicBrainzDatabase.updateMusicBrainzIDs(ids)
        MusicDatabase.refresh_album_tables()

        if verbose:
            t_6 = time.time()
            print("updated db", t_6 - t_5, t_6 - t_init)
        print('----')
        print(f'Total songs added: {len(songIDs["new"])}')
        print(f'Total songs updated: {len(songIDs["updated"])}')
        print(f'Total songs renamed: {len(songIDs["renamed"])}')
        print(f'Total songs removed: {len(removedSongs) - len(songIDs["renamed"])}')

    def info(self, ids_or_paths, currentlyPlaying=False, show_analysis=False,
             show_decode_messages=False):
        songs = []
        for id_or_path in ids_or_paths:
            songs.extend(getSongsFromIDorPath(id_or_path))

        if currentlyPlaying:
            playingSongs = self.getCurrentlyPlayingSongs()
            songs.extend(playingSongs)

        userID = MusicDatabase.getUserID(config.config['username'])

        for song in songs:
            print_song_info(song, userID, show_analysis, show_decode_messages)

    def list(self, path, long_ls=False, show_id=False, query=None,
             group_by_directory=False, show_duration=False):
        try:
            songID = int(path)
        except ValueError:
            songID = None
        if songID:
            songs = getSongs(songID=songID, query=query)
        else:
            songs = getSongs(path=path, query=query)
        if group_by_directory:
            dirs = {os.path.dirname(song.path()) for song in songs}
            for directory in sorted(dirs):
                if long_ls:
                    try:
                        size = int(subprocess.check_output(['du', '-s',
                                                            directory]
                                                           ).split()[0])
                    except subprocess.CalledProcessError:
                        size = -1
                    print('%d - ' % size, end='', flush=True)
                print("%s" % directory)
        else:
            for song in songs:
                if show_duration:
                    duration = colorizeTime(TerminalColors.Yellow,
                                            formatLength(song.duration()))
                    duration = f'({duration})'
                else:
                    duration = ''
                if show_id:
                    print('%s) ' % colorizeAll(TerminalColors.White,
                                               str(song.id)),
                          end='', flush=True)
                if long_ls:
                    if duration:
                        print(duration + ' ', end='', flush=True)
                    command = ['ls', '-l', song.path()]
                    subprocess.run(command)
                else:
                    print(f'{song.path()} {duration}')

    def listSimilars(self, condition=None, long_ls=False):
        if isinstance(condition, list):
            condition = ' '.join(condition)
        similar_pairs = MusicDatabase.getSimilarSongs(condition)
        for songID1, songID2, offset, similarity in similar_pairs:
            song1 = getSongs(songID=songID1)[0]
            song2 = getSongs(songID=songID2)[0]
            print('------  (%d %d) offset: %d   similarity %f' %
                  (songID1, songID2, offset, similarity))
            for song in (song1, song2):
                if long_ls:
                    command = ['ls', '-l', song.path()]
                    subprocess.run(command)
                else:
                    print("%s" % song.path())

    def play(self, ids_or_paths, shuffle, query=None):
        paths = []
        if not ids_or_paths and query:
            ids_or_paths = ['']
        for id_or_path in ids_or_paths:
            songs = getSongsFromIDorPath(id_or_path, query=query)
            for song in songs:
                paths.append(song.path())

        if shuffle and paths:
            random.shuffle(paths)
        elif shuffle:
            total_songs = 30
            songs = getMusic('')
            probabilities = []
            userID = MusicDatabase.getUserID(config.config['username'])
            Ratings.cache_all_ratings()
            for song in songs:
                paths.append(song.path())
                probabilities.append(song.rating(userID) * 1000)

#            print(list(normalized(probabilities)))
            paths = numpy.random.choice(paths, total_songs, replace=False,
                                        p=list(normalized(probabilities)))
            paths = list(paths)

        if not paths:
            print('No song was selected to play!')
            return
#        for path in paths:
#            print(path)
        if len(paths) > 2048:
            paths = paths[:2048]

        MusicDatabase.closeConnections()

        command = ['mpv'] + paths
        subprocess.run(command)

    def findDuplicates(self):
        collection = getMusic()
        hashes = {}
        for song in collection:
            if song.audioSha256sum() not in hashes:
                hashes[song.audioSha256sum()] = [song]
            else:
                # print('Duplicate hash found:',
                #       hashes[song.audioSha256sum()], song)
                hashes[song.audioSha256sum()].append(song)
        for h, songs in hashes.items():
            if len(songs) > 1:
                # sortSongsList (first song with most tags,symlinks at the end)
                for song in songs:
                    print(song)
                    print(song._path)

    def fixMtime(self):
        collection = getMusic()
        count = 0
        for song in collection:
            if not song.mtime():
                try:
                    mtime = os.path.getmtime(song.path())
                except os.FileNotFoundError:
                    print('File %s not found: removing from db' % song.path())
                    MusicDatabase.removeSong(song)
                    continue

                if not config.config['immutable_database']:
                    c = MusicDatabase.getCursor()
                    sql = text('UPDATE songs set mtime = :mtime '
                               'WHERE id = :id')
                    c.execute(sql.bindparams(mtime=mtime, id=song.id))
                    count += 1
                    if count % 10:
                        MusicDatabase.commit()
                print('Fixed %s' % song.path())
            else:
                print('%s already fixed' % song.path())
        MusicDatabase.commit()

    def addSilences(self, ids_or_paths=None, threshold=None, min_length=None,
                    silence_at_start=None, silence_at_end=None, dry_run=False):
        collection = []
        if ids_or_paths:
            for id_or_path in ids_or_paths:
                collection.extend(getSongsFromIDorPath(id_or_path))
        else:
            # collection = getMusic()
            collection = getMusic(', properties WHERE id == song_id'
                                  ' AND silence_at_start==-1')

        count = 0

        for song in collection:
            if (silence_at_start is not None and silence_at_end is not None) or \
                ((silence_at_start is not None or silence_at_end is not None) and \
                    not threshold and not min_length):
                silence1 = silence_at_start if silence_at_start is not None else song.silenceAtStart()
                silence2 = silence_at_end if silence_at_end is not None else song.silenceAtEnd()
                if not dry_run:
                    MusicDatabase.addAudioSilences(song.id, silence1, silence2)
                print('Add silences (%s, %s) for %s' % (silence1, silence2,
                                                        song.path()))
                continue

            sha256sum = song.audioSha256sum()
            song.calculateSilences(threshold, min_length)

            sha256sum_pydub = song.audioSha256sum()
            if ((song.path().endswith('flac') or
                 song.path().endswith('ape') or
                 song.path().endswith('.wv')) and
                    sha256sum != sha256sum_pydub):
                print('Error: sha256 does not match: %s != %s' %
                      (sha256sum, sha256sum_pydub))

            silence1 = silence_at_start if silence_at_start is not None else song.silenceAtStart()
            silence2 = silence_at_end if silence_at_end is not None else song.silenceAtEnd()

            if not dry_run:
                MusicDatabase.addAudioSilences(song.id, silence1, silence2)
                MusicDatabase.addAudioTrackSha256sum(song.id, sha256sum_pydub)

            count += 1
            if count % 10:
                MusicDatabase.commit()

            print('Add silences (%s, %s) for %s' % (silence1, silence2,
                                                    song.path()))
#            else:
#                print('%s already fixed' % song.path())
        MusicDatabase.commit()

    def checkSongsExistenceInPath(self, song, callback=None):
        if not os.path.exists(song.path()):
            if os.path.lexists(song.path()):
                print('Broken symlink at %s' % song.path())
            else:
                print('File not found: %s' % song.path())

                if callback:
                    callback(song)

    def checkSongsExistenceInPaths(self, paths, verbose=False, callback=None):
        for path in paths:
            songs = getSongsAtPath(path)
            for song in songs:
                filepath = song.path()
                try:
                    if os.path.basename(filepath) in self.songMTimeCache[os.path.dirname(filepath)]:
                        continue
                except:
                    pass

                if verbose:
                    print('File not found: %s' % filepath)
                callback(song)

    def fixChecksums(self, from_song_id=None, removeMissingFiles=False):
        if from_song_id:
            collection = getMusic("WHERE id >= :id",
                                  {'id': int(from_song_id)},
                                  order_by='id')
        else:
            collection = getMusic(order_by='id')
        count = 0
        for song in collection:
            if not song.fileExists():
                if removeMissingFiles:
                    print('Removing file: %s' % song.path())
                    self.db.removeSong(song)
                else:
                    print('Missing file at %s' % song.path())

                continue

            print('Calculating checksums for %s...' % song.path(), end='',
                  flush=True)
            # check the audio checksum
            audioSha256sumInDB = song.audioSha256sum()

            audiodata, properties = decodeAudio(song.path())
            audioSha256sumInDisk = calculateSHA256_data(audiodata)

            if audioSha256sumInDB != audioSha256sumInDisk:
                MusicDatabase.addAudioTrackSha256sum(song.id,
                                                     audioSha256sumInDisk)
                changed_audiosha256 = True
            else:
                changed_audiosha256 = False

            # check the file checksum
            # print('. File sha from db', end='', flush=True)
            sha256InDB = song.fileSha256sum()
            # print('/disk', end='', flush=True)
            sha256InDisk = calculateFileSHA256(song.path())
            if sha256InDB != sha256InDisk:
                MusicDatabase.addFileSha256sum(song.id, sha256InDisk)
                changed_filesha256 = True
            else:
                MusicDatabase.updateFileSha256sumLastCheckTime(song.id)
                changed_filesha256 = False

            # This should probably have its own command, but it shouldn't be
            # common to use it, so for now we'll just keep it here:
            MusicDatabase.addSongDecodeProperties(song.id, properties)

            if changed_audiosha256 or changed_filesha256:
                print(TerminalColors.Error + 'FAIL' + TerminalColors.ENDC)
                descl = []
                if changed_audiosha256:
                    descl.append('audio')
                    print('  Audio SHA256sum differ in disk and DB: '
                          '(%s != %s)' %
                          (audioSha256sumInDisk, audioSha256sumInDB))
                if changed_filesha256:
                    descl.append('file')
                    print('  File SHA256sum differ in disk and DB: '
                          '(%s != %s)' %
                          (sha256InDisk, sha256InDB))

                desc = 'Update %s checksum%s' % ('/'.join(descl),
                                                 's' if len(descl) > 1 else '')
                (MusicDatabase.createSongHistoryEntry(song.id,
                 audio_sha256sum=audioSha256sumInDisk,
                 sha256sum=sha256InDisk, description=desc))
                count += 1
                if count % 10 == 0:
                    MusicDatabase.commit()
            else:
                print(TerminalColors.Ok + 'OK' + TerminalColors.ENDC)
                count += 1
                if count % 10 == 0:
                    MusicDatabase.commit()

        MusicDatabase.commit()
        print('done')

    def checkChecksums(self, from_song_id=None, removeMissingFiles=False):
        if from_song_id:
            collection = getMusic("WHERE id >= :id",
                                  {'id': int(from_song_id)})
        else:
            collection = getMusic()
        failedSongs = []
        for song in collection:
            if not song.fileExists():
                if removeMissingFiles:
                    print('Removing file: %s' % song.path())
                    self.db.removeSong(song)
                else:
                    print('Missing file at %s' % song.path())

                continue
            sha256InDB = song.fileSha256sum()
            if not sha256InDB:
                print('Calculating SHA256sum for %s' % song.path())
                sha256InDisk = calculateFileSHA256(song.path())
                MusicDatabase.addFileSha256sum(song.id, sha256InDisk)
                MusicDatabase.commit()
            else:
                print('Checking %s ... ' % song.path(), end=' ', flush=True)
                sha256InDisk = calculateFileSHA256(song.path())
                if sha256InDB == sha256InDisk:
                    print(TerminalColors.Ok + 'OK' + TerminalColors.ENDC)
                else:
                    print(TerminalColors.Error + 'FAIL' + TerminalColors.ENDC +
                          ' (db contains %s, disk is %s)' %
                          (sha256InDB, sha256InDisk))
                    failedSongs.append((song, sha256InDB, sha256InDisk))

        if failedSongs:
            print('Failed songs:')
            for song, sha256InDB, sha256InDisk in failedSongs:
                print('%d %s (db contains %s, disk is %s)' %
                      (song.id, song.path(), sha256InDB, sha256InDisk))
        else:
            print('All packages successfully checked: ' +
                  TerminalColors.Ok + 'OK' + TerminalColors.ENDC)

    def fixTags(self, args):
        for path in args:
            if not os.path.isfile(path):
                print('"%s" is not a file. Skipping.' % path)
                continue

            mutagenFile = mutagen.File(path)
            fixTags(mutagenFile)

            if (MusicDatabase.isSongInDatabase(path) == 1 and
               not path.startswith('/tmp/')):
                self.addSong(path)

    def findAudioDuplicates(self, from_song_id=None, songs=[],
                            verbose=False):  # noqa: C901
        c = MusicDatabase.getCursor()
        info = {}
        print_stats = True
        matchThreshold = config.config['match_threshold']
        storeThreshold = config.config['store_threshold']
        shortSongStoreThreshold = config.config['short_song_store_threshold']
        shortSongLength = config.config['short_song_length']

        song_ids_without_fingerprints = \
            MusicDatabase.songIDsWithoutFingerprints()
        if song_ids_without_fingerprints:
            for idx, song_id in enumerate(song_ids_without_fingerprints):
                song = getSongs(songID=song_id)[0]
                print(f'Calculating missing fingerprint for song {song_id} at '
                      f'{song.path()}')
                fingerprint = song.getAcoustidFingerprint()
                MusicDatabase.updateFingerprint(song.id, fingerprint)
                if idx % 10 == 0:
                    MusicDatabase.commit()
            MusicDatabase.commit()

        if songs:
            from_song_id = MusicDatabase.lastSongID() + 1
            # print_stats = False
            collection = set()
            for id_or_path in songs:
                collection.update([x.id for x in
                                   getSongsFromIDorPath(id_or_path)])
            songs = collection
        if not from_song_id:
            from_song_id = MusicDatabase \
                .lastSongIDWithCalculatedSimilarities()
            from_song_id = from_song_id + 1 if from_song_id else 1
        elif from_song_id < 0:
            last = MusicDatabase.lastSongIDWithCalculatedSimilarities() + 1
            from_song_id = last + from_song_id

        if from_song_id > MusicDatabase.lastSongID() and not songs:
            print('All songs are already processed in DB')
            return
        if songs:
            print('Calculating song similarities for song(s):',
                  ' '.join([str(x) for x in sorted(songs)]))
        else:
            print('Start calculating song similarities from song id %d'
                  % from_song_id)
            print('Preparing data structures... ', end='')
        percentage = ''
        from bard.bard_ext import FingerprintManager
        fpm = FingerprintManager()
        fpm.setMaxOffset(100)
        fpm.setCancelThreshold(storeThreshold)
        fpm.setShortSongCancelThreshold(shortSongStoreThreshold)
        fpm.setShortSongLength(shortSongLength)
        speeds = []
        songs_processed = 0
        totalSongsCount = MusicDatabase.getSongsCount()
        fpm.setExpectedSize(totalSongsCount + 5)
        sql = ('SELECT id, fingerprint, sha256sum, audio_sha256sum, path, '
               'completeness, duration-silence_at_start-silence_at_end '
               'FROM fingerprints, songs, checksums, properties '
               'WHERE songs.id=fingerprints.song_id and '
               'songs.id = checksums.song_id and '
               'songs.id = properties.song_id order by id')

        result = c.execute(text(sql))
        incremental_song_ids_to_compare = []
        delete_not_found_similarities = bool(songs)
        start_time = None

        # We iterate over all songs
        # The normal workflow is:
        # Until we get to "from_song_id", songs are just added to fpm to build
        # the data structures.
        # After from_song_id, songs are added and compared to all previous
        # songs. The list of resulting similarities (result) is then added
        # to the database
        #
        # If we want to compare individual songs, then we iterate over all
        # songs (from_song_id is the last song) adding them to fpm to build the
        # data structures. Once we reach any of the songs in the songs list,
        # it's compared to all previous songs and added to
        # incremental_song_ids_to_compare. Now instead of just adding songs to
        # fpm, we compare the song being added just to songs in
        # incremental_song_ids_to_compare and add/remove them to/from the
        # database.
        for (songID, fingerprint, sha256sum, audioSha256sum, path,
                completeness, duration) in result.fetchall():
            # print('.', songID, end='', flush=True)
            if not isinstance(fingerprint, bytes):
                fingerprint = fingerprint.tobytes()
            dfp = chromaprint.decode_fingerprint(fingerprint)
            if not dfp[0]:
                print("Error calculating fingerprint of song %s (%s)" %
                      (songID, path))
                songs_processed += 1
                continue

            if songID < from_song_id and songID not in songs:
                if incremental_song_ids_to_compare:
                    start_time = time.time()
                    result = (fpm.addSongAndCompareToSongList(songID, dfp[0],
                              duration, incremental_song_ids_to_compare))
                else:
                    fpm.addSong(songID, dfp[0], duration)
                    result = []
                tmp = '%d%% ' % (songID * 100.0 / from_song_id)
                if tmp != percentage:
                    backspaces = '\b' * len(percentage)
                    percentage = tmp
                    print(backspaces + percentage, end='', flush=True)
            else:
                if songID == from_song_id:
                    print(('\b' * len(percentage)) + '100%')
                    print('Calculating song similarities...')
                start_time = time.time()
                result = fpm.addSongAndCompare(songID, dfp[0], duration)
                if songID in songs:
                    incremental_song_ids_to_compare.append(songID)
            result.sort(key=lambda x: x[0])

            if delete_not_found_similarities:
                similar_ids = {x[0] for x in result}
                if songID not in songs:
                    ids_not_found = [x
                                     for x in incremental_song_ids_to_compare
                                     if x not in similar_ids]
                else:
                    allSimilarSongs = MusicDatabase.getSimilarSongsToSongID(
                        songID, similarityThreshold=0)
                    allSimilarSongs = [x[0] for x in allSimilarSongs]
                    ids_not_found = [x for x in allSimilarSongs
                                     if x < songID and x not in similar_ids]

                for x in ids_not_found:
                    MusicDatabase.removeSongsSimilarity(x, songID)

            for (songID2, offset, similarity) in result:
                match = '*******' if similarity > matchThreshold else ''
                if delete_not_found_similarities:
                    print('\b' * len(percentage), end='')
                if verbose or similarity > matchThreshold:
                    print('%d %d %d %f %s' % (songID2, songID,
                                              offset, similarity, match))
                if delete_not_found_similarities:
                    print(percentage, end='', flush=True)
                MusicDatabase.addSongsSimilarity(songID2, songID,
                                                 offset, similarity)

                if similarity >= matchThreshold:
                    # print('''Duplicates found!\n''',
                    #       songID, fingerprint, path)
                    # print('''Duplicates found!\n''', fp)
                    # print('''Duplicates found!\n''', fingerprints[fp])
                    (otherSha256sum, otherAudioSha256sum, otherPath,
                        otherCompleteness) = info[songID2]
                    if sha256sum == otherSha256sum:
                        msg = ('Exactly the same files (sha256 = %s)' %
                               sha256sum)
                        print('Duplicate songs found: %s\n'
                              '%s\n and %s' % (msg, otherPath, path))
                    elif audioSha256sum == otherAudioSha256sum:
                        msg = ('Same audio track with different tags '
                               '(completeness: %d <-> %d)' %
                               (otherCompleteness, completeness))
                        print('Duplicate songs found: %s\n'
                              '%s\n and %s''' % (msg, otherPath, path))
                    # else:
                        # msg = 'Similarity %f' % similarity
                        # print('Duplicate songs found: %s\n     %s\n'
                        #       'and %s' % (msg, otherPath, path))
            songs_processed += 1
            info[songID] = (sha256sum, audioSha256sum, path, completeness)
            if result:
                MusicDatabase.commit()
            elif start_time and not incremental_song_ids_to_compare:
                print(f'No match found for song {songID}: {path}')

            if print_stats and start_time:
                delta_time = time.time() - start_time
                speeds = (speeds[{True: 1, False: 0}[len(speeds) >= 20]:] +
                          [len(info) / delta_time])
                avg = numpy.mean(speeds)

                s = summation(songs_processed, totalSongsCount - 1) / avg
                d = datetime.timedelta(seconds=s)
                now = datetime.datetime.now()

                if delete_not_found_similarities:
                    print('\b' * len(percentage), end='')
                if (not incremental_song_ids_to_compare or
                        songID in incremental_song_ids_to_compare):
                    print('Stats: %0.3f seconds in evaluating %d/%d songs '
                          '%0.3f songs/s (avg: %0.3f, songs left: %d, '
                          'estimated end at: %s)' %
                          (delta_time, len(info), totalSongsCount, speeds[-1],
                           avg, totalSongsCount - songs_processed, now + d))

        fpm.writeToFile(os.path.expanduser('~/.cache/bard-fpm.cache'))

        if delete_not_found_similarities:
            print(('\b' * len(percentage)) + '100% . Done')
            MusicDatabase.commit()

    def compareSongs(self, song1, song2, verbose=False,  # noqa: C901
                     showAudioOffsets=False, storeInDB=False,
                     interactive=False):
        try:
            id1 = song1.id
        except AttributeError:
            id1 = -1
            storeInDB = False
        try:
            id2 = song2.id
        except AttributeError:
            id2 = -2
            storeInDB = False

        duration1 = song1.durationWithoutSilences()
        duration2 = song2.durationWithoutSilences()

        print('Comparing ' +
              TerminalColors.First + str(id1) + TerminalColors.ENDC +
              ' and ' +
              TerminalColors.Second + str(id2) + TerminalColors.ENDC)
        matchThreshold = config.config['match_threshold']
        storeThreshold = config.config['store_threshold']
        shortSongStoreThreshold = config.config['short_song_store_threshold']
        shortSongLength = config.config['short_song_length']
        from bard.bard_ext import FingerprintManager
        fpm = FingerprintManager()
        fpm.setMaxOffset(100)
        fpm.setCancelThreshold(storeThreshold)
        fpm.setShortSongCancelThreshold(shortSongStoreThreshold)
        fpm.setShortSongLength(shortSongLength)

        dfp1 = chromaprint.decode_fingerprint(song1.getAcoustidFingerprint())
        dfp2 = chromaprint.decode_fingerprint(song2.getAcoustidFingerprint())
        if id1 < id2:
            fpm.addSong(id1, dfp1[0], duration1)
            fpm.addSong(id2, dfp2[0], duration2)
        else:
            fpm.addSong(id2, dfp2[0], duration2)
            fpm.addSong(id1, dfp1[0], duration1)

        values = fpm.compareSongsVerbose(id1, id2)
        if showAudioOffsets:
            for offset, similarity in values:
                if similarity > storeThreshold:
                    print(offset, similarity)

        (offset, similarity) = max(values, key=lambda x: x[1])

        if storeInDB and similarity and similarity >= storeThreshold \
                and song1.id and song2.id:
            MusicDatabase.addSongsSimilarity(song1.id, song2.id,
                                             offset, similarity)
            MusicDatabase.commit()

        sameSong = False
        if (song1.fileSha256sum() == song2.fileSha256sum() or
            song1.audioSha256sum() == song2.audioSha256sum() or
                (similarity and similarity >= matchThreshold)):
            sameSong = True

        colors = (TerminalColors.First, TerminalColors.Second)
        printSongsInfo(song1, song2, useColors=colors)

        try:
            cmpResult = song1.audioCmp(song2, forceSimilar=sameSong,
                                       useColors=colors,
                                       interactive=interactive)
        except (DifferentLengthException, CantCompareSongsException) as e:
            print(e)
            if similarity and similarity >= matchThreshold:
                msg = 'Similarity %f, offset %d' % (similarity, offset)
                print('Similar songs found: %s' % msg)
            else:
                print('''Songs not similar (similarity: %f, offset: %d)''' %
                      (similarity, offset))
        else:
            if song1.fileSha256sum() == song2.fileSha256sum():
                msg = ('Exactly the same files (sha256 = %s)' %
                       song1.fileSha256sum())
                print('Duplicate songs :', msg)
            elif song1.audioSha256sum() == song2.audioSha256sum():
                msg = 'Exactly same audio track with different tags'
                print('Duplicate songs :', msg)
            elif similarity and similarity >= matchThreshold:
                msg = 'Similarity %f, offset %d' % (similarity, offset)
                print('Similar songs found: %s' % msg)
            else:
                print('''Songs not similar (similarity: %f, offset: %d)''' %
                      (similarity, offset))
            if cmpResult < 0:
                print('%d has better audio than %d' % (id1, id2))
            elif cmpResult > 0:
                print('%d has better audio than %d' % (id2, id1))
            elif cmpResult == 0:
                print('%d and %d have equivalent audio' % (id1, id2))
    #        except DifferentSongsException as e:
    #            print(e)

    def compareDirectories(self, path1, paths, subset=False,
                           maxLengthDifference=5, verbose=False):
        songs1 = getSongsAtPath(path1)
        songs2 = set()
        for path in paths:
            songs2.update(getSongsAtPath(path))
        if len(paths) == 1:
            path2 = paths[0]
        else:
            path2 = '(' + ' + '.join(paths) + ')'
        songs2 = list(songs2)
        try:
            compareSongSets(songs1, songs2, useSubsetSemantics=subset,
                            verbose=verbose,
                            maxLengthDifference=maxLengthDifference)
        except ValueError as e:
            print(e)

        return None

        songs1 = SongSet(songs1)
        songs2 = SongSet(songs2)
        print(songs1)
        print(songs2)

        firstInSecond = songs1 <= songs2
        if subset:
            if firstInSecond:
                print('%s is contained in %s' % (path1, path2))
            else:
                print('%s is NOT contained in %s' % (path1, path2))

        secondInFirst = songs1 <= songs1

        if firstInSecond and secondInFirst:
            print('The following directories contain the same set of songs:')
            print(path1)
            print(path2)
        elif firstInSecond:
            print('The directory %s is contained in %s' % (path1, path2))
        elif secondInFirst:
            print('The directory %s is contained in %s' % (path2, path1))
        else:
            print('None of the following directories is '
                  'a subset of the other:')
            print(path1)
            print(path2)

    def compareSongIDsOrPaths(self, songid1, songid2, interactive=False):
        songs1 = getSongsFromIDorPath(songid1)
        if len(songs1) != 1:
            print('No match or more than one match for ', songid1)
            return
        song1 = songs1[0]
        songs2 = getSongsFromIDorPath(songid2)
        if len(songs2) != 1:
            print('No match or more than one match for ', songid2)
            return
        song2 = songs2[0]
        self.compareSongs(song1, song2, interactive=interactive)

    def compareFiles(self, path1, path2, interactive=False):
        song1 = Song(path1)
        song2 = Song(path2)
        self.compareSongs(song1, song2, storeInDB=False,
                          interactive=interactive)

    def scanFile(self, path, printMatchInfo=False):
        song = Song(path)
        song_duration = song.durationWithoutSilences()
        song_fingerprint = song.getAcoustidFingerprint()
        song_dfp = chromaprint.decode_fingerprint(song_fingerprint)

        from_song_id = MusicDatabase \
            .lastSongIDWithCalculatedSimilarities()
        from_song_id = from_song_id + 1 if from_song_id else 1

        info = {}
        matchThreshold = config.config['match_threshold']
        shortSongStoreThreshold = config.config['short_song_store_threshold']
        shortSongLength = config.config['short_song_length']
        from bard.bard_ext import FingerprintManager
        fpm = FingerprintManager()
        fpm.setMaxOffset(100)
        fpm.setCancelThreshold(matchThreshold)
        fpm.setShortSongCancelThreshold(shortSongStoreThreshold)
        fpm.setShortSongLength(shortSongLength)

        percentage = ''
        songs_processed = 0
        totalSongsCount = MusicDatabase.getSongsCount()
        fpm.setExpectedSize(totalSongsCount + 5)
        c = MusicDatabase.getCursor()

        def getInfo(songID):
            sql = ('SELECT sha256sum, audio_sha256sum, path, '
                   'completeness, duration-silence_at_start-silence_at_end '
                   'FROM fingerprints, songs, checksums, properties '
                   'WHERE songs.id = :song_id and '
                   'songs.id=fingerprints.song_id and '
                   'songs.id = checksums.song_id and '
                   'songs.id = properties.song_id order by id')
            result = c.execute(text(sql).bindparams(song_id=songID))
            return result.fetchone()

        useCache = True
        if useCache:
            fpm.readFromFile(os.path.expanduser('~/.cache/bard-fpm.cache'))
            maxSongID = max(fpm.songIDs())
            completeness = song.getCompleteness()
        else:
            sql = ('SELECT id, fingerprint, sha256sum, audio_sha256sum, path, '
                   'completeness, duration-silence_at_start-silence_at_end '
                   'FROM fingerprints, songs, checksums, properties '
                   'WHERE songs.id=fingerprints.song_id and '
                   'songs.id = checksums.song_id and '
                   'songs.id = properties.song_id order by id')

            result = c.execute(text(sql))
            maxSongID = 0
            for (songID, fingerprint, sha256sum, audioSha256sum, path,
                    completeness, duration) in result.fetchall():
                maxSongID = max(maxSongID, songID)
                info[songID] = (sha256sum, audioSha256sum, path, completeness,
                                duration)
                # print('.', songID, end='', flush=True)
                if not isinstance(fingerprint, bytes):
                    fingerprint = fingerprint.tobytes()
                dfp = chromaprint.decode_fingerprint(fingerprint)
                if not dfp[0]:
                    print("Error calculating fingerprint of song %s (%s)" %
                          (songID, path))
                    songs_processed += 1
                    continue

                fpm.addSong(songID, dfp[0], duration)
                result = []
                tmp = '%d%% ' % (songID * 100.0 / from_song_id)
                if tmp != percentage:
                    backspaces = '\b' * len(percentage)
                    percentage = tmp
                    print(backspaces + percentage, end='', flush=True)

        result = fpm.addSongAndCompare(maxSongID + 1, song_dfp[0],
                                       song_duration)
        sha256sum = song.fileSha256sum()
        audioSha256sum = song.audioSha256sum()

        first = True
        if result:
            print('Matching songs in database:')
            show_all = all(x[2] < matchThreshold for x in result)
        for (songID2, offset, similarity) in \
                sorted(result, key=lambda x: -x[2]):
            if show_all or similarity >= matchThreshold:
                try:
                    (otherSha256sum, otherAudioSha256sum, otherPath,
                        otherCompleteness, otherDuration) = info[songID2]
                except KeyError:
                    (otherSha256sum, otherAudioSha256sum, otherPath,
                        otherCompleteness, otherDuration) = getInfo(songID2)

                print('%d (similarity: %f) %s' % (songID2, similarity,
                                                  otherPath))
                if sha256sum == otherSha256sum:
                    msg = ('Exactly the same files (sha256 = %s)' %
                           sha256sum)
                    print('Duplicate songs found: %s\n'
                          '%s\n and %s' % (msg, otherPath, path))
                elif audioSha256sum == otherAudioSha256sum:
                    msg = ('Same audio track with different tags '
                           '(completeness: %d <-> %d)' %
                           (otherCompleteness, completeness or '0'))
                    print('Duplicate songs found: %s\n'
                          '%s\n and %s''' % (msg, otherPath, path))
                # else:
                    # msg = 'Similarity %f' % similarity
                    # print('Duplicate songs found: %s\n     %s\n'
                    #       'and %s' % (msg, otherPath, path))
                if first and printMatchInfo:
                    self.info([songID2])
                    first = False

    def calculateDR(self, ids_or_paths, force_recalculate=True):
        collection = []
        if force_recalculate:
            for path in ids_or_paths:
                song = Song(path)
                print(f'DR: {song.dr14}')
                print(f'Peak dB: {song.db_peak:0.3f}')
                print(f'RMS dB: {song.db_rms:0.3f}')
            return

        for id_or_path in ids_or_paths:
            collection.extend(getSongsFromIDorPath(id_or_path))

        for song in collection:
            print(song.id, song.path())
            try:
                song.loadDRData()
            except:
                try:
                    song.calculateDR()
                except NameError:
                    return
            print(f'DR: {song.dr14}')
            print(f'Peak dB: {song.db_peak:0.3f}')
            print(f'RMS dB: {song.db_rms:0.3f}')


    def listGenres(self, id_or_paths=None, root=None, quoted_output=False):
        ids = []
        paths = []
        for id_or_path in id_or_paths:
            try:
                ids.append(int(id_or_path))
            except ValueError:
                paths.append(id_or_path)
        genres = MusicDatabase.getGenres(ids=ids, paths=paths, root=root)
        import shlex
        for genre, count in genres:
            if quoted_output:
                if len(genre) == 1:
                    print(shlex.quote(genre[0]))
                else:
                    print(shlex.quote('@@@'.join(genre)))
            else:
                print('%s :\t%s' % (genre, count))

    def listRoots(self, quoted_output=False):
        roots = MusicDatabase.getRoots()
        import shlex
        for root, count in roots:
            if quoted_output:
                print(shlex.quote(root))
            else:
                print('%s :\t%s' % (root, count))

    def fixGenres(self, ids_or_paths=None):
        songs = []
        for id_or_path in ids_or_paths:
            songs.extend(getSongsFromIDorPath(id_or_path))
        for song in songs:
            song.loadMetadata()
            new_genres = []
            a = song.metadata['genre']
            print(a, type(a))

            for genre in song.metadata['genre']:
                print(genre, len(genre))
                genre = genre.strip('\r')
                genre = genre.strip('"')
                genre = genre.strip("'")
                print(genre, len(genre))
                new_genres.append(genre)
            print(new_genres)

    def setRating(self, ids_or_paths, rating, currentlyPlaying):
        if (ids_or_paths in ([], [''], ['%'], ['%%']) and
                not currentlyPlaying):
            print('No song selected to set rating to')
            return

        rating = round(float(rating))
        if rating < 0 or rating > 10:
            print('Rating must be an integer value between 0 and 10')
            return

        songs = []

        for id_or_path in ids_or_paths:
            songs.extend(getSongsFromIDorPath(id_or_path))

        if currentlyPlaying:
            playingSongs = self.getCurrentlyPlayingSongs()
            songs.extend(playingSongs)

        if not songs:
            print('No song selected to set rating to')
            return

        userID = MusicDatabase.getUserID(config.config['username'])
        for song in songs:
            print('Setting rating of %s to %d' % (song.path(), rating))
            song.setUserRating(rating, userID)

    def updateMusicBrainzIDs(self, verbose=False):
        songIDs = MusicBrainzDatabase.songsWithoutMBData()
        MusicBrainzDatabase.updateMusicBrainzIDs(songIDs)

    def updateAlbums(self, regenerate=False, verbose=False):
        songIDsAndPaths = MusicDatabase.songsWithReleaseID(
            onlyWithoutAlbums=not regenerate)

        lastAlbumPath = None
        albumID = None
        for songID, songPath in songIDsAndPaths:
            aPath = albumPath(songPath)
            if aPath != lastAlbumPath:
                albumID = MusicDatabase.getAlbumID(aPath)
                lastAlbumPath = aPath

            MusicDatabase.setSongInAlbum(songID, albumID)
        MusicDatabase.removeOrphanAlbums()
        MusicDatabase.refresh_album_tables()

    def checkMusicBrainzTags(self, verbose=False):
        r1 = MusicBrainzDatabase.checkMusicBrainzTags()
        r2 = MusicBrainzDatabase.checkAlbumsWithDifferentReleases()
        r3 = MusicBrainzDatabase.checkAlbumsWithDifferentFormats()
        if not any([r1, r2, r3]):
            print('Musicbrainz tags are ok!')
            print('This means that every song in the '
                  'musicbrainz_tagged_music_paths directories\n'
                  'is tagged correctly and every directory only '
                  'contains one release.')

    def cacheMusicBrainzDB(self, verbose=False):
        MusicBrainzDatabase.cacheMusicBrainzDB()

    def printStats(self, verbose=False):
        totalSongsCount = MusicDatabase.getSongsCount()
        totalSongsWithMusicBrainzTags = \
            MusicDatabase.getSongsWithMusicBrainzTagsCount()
        print('Total songs: %d' % (totalSongsCount))
        print('Songs with Musicbrainz tags: %d (%.05g%%)' %
              (totalSongsWithMusicBrainzTags,
               totalSongsWithMusicBrainzTags * 100.0 / totalSongsCount))
        print('Songs without Musicbrainz tags: %d (%.05g%%)' %
              (totalSongsCount - totalSongsWithMusicBrainzTags,
               (totalSongsCount -
                totalSongsWithMusicBrainzTags) * 100.0 / totalSongsCount))
        if verbose:
            roots = MusicDatabase.getRoots()
            table = []
            for root, count in roots:
                root = config.translatePath(root)
                try:
                    size = int(subprocess.check_output(['du', '-sm', root]
                                                       ).split()[0])
                except subprocess.CalledProcessError:
                    size = -1
                table.append((str(size) + 'M', root, count))
            aligned = alignColumns(table, (False, True, False))
            for line in aligned:
                print(line)

    def startWebServer(self):
        from bard.web import init_flask_app, app

        MusicDatabase.table('users')
        context = None
        use_ssl = config.config['use_ssl']
        if use_ssl:
            import ssl
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            certpemfile = config.config['ssl_certificate_chain_file']
            serverkeyfile = config.config['ssl_certificate_key_file']

            print(certpemfile)
            print(serverkeyfile)
            if os.path.exists(certpemfile) and os.path.exists(serverkeyfile):
                context.load_cert_chain(certpemfile, serverkeyfile)
            else:
                print(f'{certpemfile} and/or {serverkeyfile} not found')

        app.bard = self
        self.available_devices = ['Web browser', 'Sonos', 'Chromecast', 'local']
        self.current_device = 'Web browser'

        init_flask_app()
        hostname = config.config['hostname']
        port = config.config['port']
        app.run(hostname, port,
                use_reloader=True, use_debugger=False,
                use_evalex=True, ssl_context=context,
                threaded=True)

    def setPassword(self, username):
        requestNewPassword(username)

    def backupMusic(self, target, priorityPatterns):
        backupMusic(target, priorityPatterns)

    def analyzeSongs(self, from_song_id=0, verbose=False):
        if not from_song_id:
            from_song_id = AnalysisDatabase.lastSongIDWithAnalysis()
            from_song_id = from_song_id + 1 if from_song_id else 1

        print(f'Analyzing songs from song {from_song_id}...')
        songsData = AnalysisDatabase.songsWithoutAnalysis(from_song_id)

        c = MusicDatabase.getCursor()
        number_of_tries = 1
        for songID, songPath, songDuration in songsData:
            print(songID, songPath)
            analysis = None
            force_predecode = False
            skip_song = False
            while not analysis:
                try:
                    analysis = (SongAnalysis.analyze(songPath,
                                force_predecode=force_predecode))
                    number_of_tries = 1
                except RuntimeError as e:
                    msg = ('In MusicExtractor.compute: File looks like a '
                           'completely silent file... Aborting...')
                    msg2 = ('In MusicExtractor.compute: AudioLoader: '
                            'Incomplete format conversion (some samples '
                            'missing) from fltp to flt')
                    msg3 = ('In MusicExtractor.compute: AudioLoader: '
                            'could not load audio. Audio file has more '
                            'than 2 channels.')
                    msg4 = ('In MusicExtractor.compute: '
                            'SVMPredict: could not load model')
                    if e.args and e.args[0] == msg:
                        print("Silent file. Skipping...")
                        skip_song = True
                        break
                    elif e.args and (e.args[0] == msg2 or e.args[0] == msg3):
                        force_predecode = True
                        continue
                    elif e.args and e.args[0] == msg4:
                        if number_of_tries < 3:
                            print(msg4 + '. Trying again...')
                            number_of_tries += 1
                        else:
                            raise
                    else:
                        raise
                if abs(analysis.frames['metadata.audio_properties.length'] -
                       songDuration) > 2:
                    dur = analysis.frames['metadata.audio_properties.length']
                    print(f"ERROR: song duration from analysis is {dur}"
                          f" but should be {songDuration}. ", end='')
                    if force_predecode:
                        print("Skipping...")
                        skip_song = True
                        break

                    print("Forcing pre-decoding of song...")
                    analysis = None
                    force_predecode = True
                    continue

            if skip_song:
                continue

            i = AnalysisImporter(songID, analysis)
            i.import_analysis(connection=c)
            c.commit()

    def fixRatings(self, user_id, from_song_id=0, verbose=False):
        if not user_id:
            user_id = MusicDatabase.getUserID(config.config['username'])

        print(f'Fixing ratings for user {user_id}...')
        MusicDatabase.add_null_ratings(user_id, from_song_id, verbose)

    def addArtistPath(self, path, image_filename=None, verbose=False):
        mbidfile = os.path.join(path, '.artist_mbid')
        mbids = [x.strip('\n') for x in open(mbidfile).readlines()]
        dirname = os.path.normpath(path)
        path_id = MusicBrainzDatabase.get_artist_path_id(dirname)
        connection = MusicDatabase.getCursor()
        if path_id:
            MusicBrainzDatabase.set_artist_path_image_filename(path_id,
                                                               image_filename)
        else:
            path_id = (MusicBrainzDatabase.add_artist_path(dirname,
                       image_filename, connection=connection))
            if not path_id:
                return
        if verbose:
            print(f'Adding artist path {dirname} ({path_id}) for {mbids}...')
        if len(mbids) == 1:
            artist_id = MusicBrainzDatabase.get_artist_id(mbids[0],
                connection=connection)
            if artist_id:
                MusicBrainzDatabase.set_artist_path(artist_id, path_id,
                                                    connection=connection)

        artist_credit_ids = MusicBrainzDatabase.get_artist_credit_ids(mbids,
            connection=connection)

        if artist_credit_ids:
            (MusicBrainzDatabase.set_artist_credit_path(artist_credit_ids,
             path_id, connection=connection))

    def updateMusicBrainzArtists(self, verbose=False):
        paths = config.config['music_paths']
        for path in paths:
            if not os.path.isdir(path):
                continue
            for dirpath, dirnames, filenames in os.walk(path, topdown=True):
                dirnames.sort()
                if '.artist_mbid' in filenames:
                    if verbose:
                        print(f'Found artist dir at {dirpath}')
                    image_filenames = [f for f in ('artist.jpg', 'artist.png',
                                                   'artist.webp')
                                       if f in filenames]
                    image_filename = (image_filenames[0]
                                      if image_filenames else None)

                    self.addArtistPath(dirpath, image_filename,
                                       verbose=verbose)
                    MusicDatabase.commit()

                for excludeDir in self.excludeDirectories:
                    try:
                        dirnames.remove(excludeDir)
                    except ValueError:
                        pass

    def initBard(self):
        # Just creating a Bard object is enough to initialize the database
        # so there's no need to do anything respect to the database

        config_path = config.get_configuration_file_path()
        if os.path.exists(config_path):
            print(f'Config file already exists at {config_path}')
            return
        try:
            with importlib_resources.path('bard', 'config.example') \
                    as config_example:
                import shutil
                shutil.copy(config_example, config_path)
                print(f'Wrote an example configuration file to {config_path}')
                print('Please now edit that file and set (at least) the '
                      'directories where you have music files so bard can '
                      'find them.')
        except FileNotFoundError:
            print('Example config file not found, please copy it manually from'
                  ' https://raw.githubusercontent.com/antlarr/bard/master/'
                  f'bard/config.example to {config_path}')

    def processSongs(self, from_song_id=None, verbose=False):
        self.findAudioDuplicates(from_song_id, verbose=verbose)
        self.analyzeSongs(from_song_id=from_song_id, verbose=verbose)

    def updateMusicBrainzDBDump(self, verbose):
        importer = MusicBrainzImporter()
        print('Downloading Musicbrainz database dumps...')
        importer.retrieve_musicbrainz_dumps()

    def importMusicBrainzData(self, verbose):
        importer = MusicBrainzImporter()

        print('Loading data to import...')
        importer.load_data_to_import()
        print('\n\nImporting data from musicbrainz...')
        importer.import_everything()
        print('Data from musicbrainz imported')

    def checkRedirectedMusicBrainzUUIDs(self, list_songs=False, group_size=30, verbose=False):
        importer = MusicBrainzImporter()

        print('Checking redirected uuids...')
        if list_songs:
            importer.check_redirected_uuids_songs(group_size, verbose)
        else:
            importer.check_redirected_uuids(group_size, verbose)

    def parseCommandLine(self):  # noqa: C901
        main_parser = ArgumentParser(
            description='Manage your music collection',
                        formatter_class=argparse.RawTextHelpFormatter)
        main_parser.add_argument('--version', action='version',
                                 version='Bard ' + __version__)
        sps = main_parser.add_subparsers(
            dest='command', metavar='command',
            help='''The following commands are available:
init                initializes the database
find-duplicates     find duplicate files comparing the checksums
find-audio-duplicates [-v] [--from-song-id <song_id>] [song_id ...]
                    find duplicate files comparing the audio fingerprint
compare-songs [-i] [id_or_path] [id_or_path]
                    compares two songs given their paths or song id
compare-files [-i] [path] [path]
                    compares two files not neccesarily in the database
compare-dirs [-s] [dir1] [dir2]
                    compares two directories neccesarily in the database
scan-file [--print-match-info] [path]
                    Parse a file and find out if there are similar songs
                    in the database
fix-mtime           fixes the mtime of imported files (you should never
                    need to use this)
fix-checksums       fixes the checksums of imported files (you should
                    never need to use this)
fix-ratings [--from-song-id id]
                    fixes the missing ratings of songs (you should never need
                    to use this)
add-silences [-t threshold] [-l length] [-s start] [-e end] [file|song_id ...]
                    adds silence information to the db for files missing it
                    (you should never need to use this)
check-songs-existence [-v] [path]
                    check for removed files to remove them from the
                    database
check-checksums     check that the imported files haven't been modified
                    since they were imported
import [file_or_directory [file_or_directory ...]]
                    import new (or update) music. You can specify the
                    files/directories to import as arguments. If no
                    arguments are given in the command line, the
                    music_paths entries in the configuration file are used
info [-p] [-a|--show-analysis] <file | song id>
                    shows information about a song from the database
list|ls [-l] [-d] [-i|--id] [--duration] [-r root] [-g genre] [--rating rating]
        [--my-rating rating] [--others-rating rating] [file | song_id ...]
                    lists paths to a song from the database
list-similars [-l] [condition]
                    lists files marked as similar in the database
                    (with find-audio-duplicates)
list-genres [-r root] [-q] [file | song id]
                    lists genres of songs selected by its name or song id
list-roots [-q]
                    lists roots for songs
fix-genres [file | song id]
                    fix genres of songs selected by its name or song id
play [--sh|--shuffle] [-r root] [-g genre] [--rating rating]
     [--my-rating rating] [--others-rating rating] [file | song_id ...]
                    play the specified songs using mpv
fix-tags <file_or_directory [file_or_directory ...]>
                    apply several normalization algorithms to fix tags of
                    files passed as arguments
update [-v]
                    Update database with new/modified/deleted files
set-rating [-p] <rating> [file | song_id ...]
                    Set rating for a song or songs
stats [-v]
                    Print database statistics
web
                    Start a web server
passwd [username]
                    Sets a user password
backup <target>
                    Backup music to target destination
update-musicbrainz-ids [-v]
                    Update the database musicbrainz IDs from songs
check-musicbrainz-tags [-v]
                    Check if there are songs which should have correct
                    musicbrainz tags but don't
cache-musicbrainz-db [-v]
                    Cache musicbrainz tables by copying data into
                    new tables for fastest access
analyze-songs [-v] [--from-song-id id]
                    Perform a high-level audio analysis of songs
calculate-dr [file | song_id ...]
                    Calculate the Audio Dynamic Range of a song using the
                    DR14-T.meter library.
update-musicbrainz-artists [-v]
                    Find .artist_mbid files to recognize artist paths
                    and images
update-albums [-v] [--regenerate]
                    Update the albums to which songs belong to (this
                    should be never needed)
process-songs [-v] [--from-song-id <song_id>]
                    Process songs finding duplicates and doing a high-level
                    audio analysis (actually, a shortcut for
                    find-audio-duplicates and analyze-songs
mb-update [-v]
                    Download the latest MusicBrainz database
mb-import [-v] [--update]
                    Import downloaded MusicBrainz data into the bard database
mb-check-redirected-uuids [-v] [--list-songs] [--group-size N]
                    Check if there are songs which have old musicbrainz uuids
                    that should be retagged
''')
        # init command
        sps.add_parser('init', description='Initialize the database')
        # find-duplicates command
        sps.add_parser('find-duplicates',
                       description='Find duplicate files comparing '
                                   'the checksums')
        # find-audio-duplicates command
        parser = sps.add_parser('find-audio-duplicates',
                                description='Find duplicate files comparing '
                                            'the audio fingerprint')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            help='Starts fixing checksums from a specific '
                                 'song_id')
        parser.add_argument('songs', nargs='*')
        # compare-songs command
        parser = sps.add_parser('compare-songs',
                                description='Compares two songs')
        parser.add_argument('song1', metavar='id_or_path')
        parser.add_argument('song2', metavar='id_or_path')
        parser.add_argument('-i', dest='interactive', action='store_true',
                            default=False,
                            help='Do an interactive audio comparison')
        # compare-files command
        parser = sps.add_parser('compare-files',
                                description='Compares two files not'
                                ' neccesarily in the database')
        parser.add_argument('song1', metavar='path')
        parser.add_argument('song2', metavar='path')
        parser.add_argument('-i', dest='interactive', action='store_true',
                            default=False,
                            help='Do an interactive audio comparison')
        # compare-dirs command
        parser = sps.add_parser('compare-dirs',
                                description='Compares two directories'
                                ' neccesarily in the database')
        parser.add_argument('-s', dest='subset', action='store_true',
                            default=False,
                            help='Only test if dir1 is a subset of dir2')
        parser.add_argument('-v', dest='verbose', action='store_true',
                            default=False,
                            help='Be verbose')
        parser.add_argument('--length-threshold', type=float,
                            dest='max_length_diff', default=5.0,
                            help='Max length differences allowed between'
                            ' similar songs')
        parser.add_argument('dir1', metavar='path')
        parser.add_argument('dirs', metavar='path', nargs=argparse.REMAINDER)
        # scan-file command
        parser = sps.add_parser('scan-file',
                                description='Parse a file and find out if '
                                'there are similar songs in the database')
        parser.add_argument('--print-match-info', dest='printMatchInfo',
                            action='store_true', default=False,
                            help='Print the information of the most similar '
                            'song found')
        parser.add_argument('path', metavar='path')
        # fix-mtime command
        sps.add_parser('fix-mtime',
                       description='Fixes the mtime of imported files '
                                   '(you should never need to use this)')
        # add-silences command
        parser = sps.add_parser('add-silences',
                                description='Add silence information to the '
                                            'db for files missing it (you '
                                            'should never need to use this)')
        parser.add_argument('-t', '--threshold', type=float,
                            metavar='threshold',
                            default=-65, help='Silence threshold (in dB)')
        parser.add_argument('-l', '--min-length', type=int,
                            metavar='min_length',
                            default=10, help='Minimum silence length (in ms)')
        parser.add_argument('-s', '--silence-at-start', type=float,
                            metavar='length', default=None,
                            help='Don\'t calculate silences, just use this '
                                 'value for silence length at start of song')
        parser.add_argument('-e', '--silence-at-end', type=float,
                            metavar='length', default=None,
                            help='Don\'t calculate silences, just use this '
                                 'value for silence length at end of song')
        parser.add_argument('-d', '--dry-run', action='store_true',
                            help='Don\'t modify the database')
        parser.add_argument('paths', nargs='*')
        # fix-checksums command
        parser = sps.add_parser('fix-checksums',
                                description='Fixes the checksums of imported '
                                'files (you should never need to use this)')
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            help='Starts fixing checksums from a specific '
                                 'song_id')
        parser.add_argument('--remove-missing-files',
                            dest='remove_missing_files', action='store_true',
                            help='Remove missing files')
        # fix-ratings command
        parser = sps.add_parser('fix-ratings',
                                description='Fixes the missing ratings of '
                                'songs (you should never need to use this)')
        parser.add_argument('--user-id', type=int, default=None,
                            help='User id for which to fix missing songs '
                            'ratings')
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            default=0, help='Starts fixing ratings from a '
                            'specific song_id')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        # check-songs-existence command
        parser = sps.add_parser('check-songs-existence',
                                description='Check for removed files to '
                                            'remove them from the database')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        parser.add_argument('paths', nargs='*', metavar='paths')
        # check-checksums command
        parser = sps.add_parser('check-checksums',
                                description='Check that the imported files '
                                "haven't been modified since they were "
                                "imported")
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            help='Starts fixing checksums '
                                 'from a specific song_id')
        parser.add_argument('--remove-missing-files',
                            dest='remove_missing_files', action='store_true',
                            help='Remove missing files')
        # import command
        parser = sps.add_parser('import',
                                description='Import new (or update) music. '
                                'You can specify the files/directories to '
                                'import as arguments. If no arguments are '
                                'given in the command line, the music_paths '
                                'entries in the configuration file are used')
        parser.add_argument('paths', nargs='*', metavar='file_or_directory')
        # info command
        parser = sps.add_parser('info',
                                description='Shows information about a song '
                                            'from the database')
        parser.add_argument('-p', dest='playing', action='store_true',
                            help='Show information of currently playing song')
        parser.add_argument('-a', '--show-analysis', dest='show_analysis',
                            action='store_true', help='Show also the '
                            'highlevel analysis information')
        parser.add_argument('--show-decode-messages',
                            dest='show_decode_messages',
                            action='store_true', help='Show also the '
                            'decode messages')
        parser.add_argument('paths', nargs='*')
        # list command
        parser = sps.add_parser('list',
                                description='Lists paths to songs '
                                            'from the database')
        parser.add_argument('-l', dest='long_ls', action='store_true',
                            help='Actually run ls -l')
        parser.add_argument('-d', dest='group_by_directory',
                            action='store_true',
                            help='Group results by directory')
        parser.add_argument('-i', '--id', dest='show_id', action='store_true',
                            help='Show the id of each song listed')
        parser.add_argument('--duration', dest='show_duration',
                            action='store_true',
                            help='Show the duration of each song listed')
        parser.add_argument('-r', '--root', dest='root',
                            help='List only songs in the given root')
        parser.add_argument('-g', '--genre', dest='genre',
                            help='List only songs with the given genre')
        parser.add_argument('--rating', dest='rating',
                            help='List only songs with the given rating')
        parser.add_argument('--my-rating', dest='my_rating',
                            help='List only songs with the given rating'
                            ' set by the current user')
        parser.add_argument('--others-rating', dest='others_rating',
                            help='List only songs with the given average'
                            'rating set by other users')
        parser.add_argument('paths', nargs='*')
        parser = sps.add_parser('ls',
                                description='Lists paths to songs '
                                            'from the database')
        parser.add_argument('-l', dest='long_ls', action='store_true',
                            help='Actually run ls -l')
        parser.add_argument('-d', dest='group_by_directory',
                            action='store_true',
                            help='Group results by directory')
        parser.add_argument('-i', '--id', dest='show_id', action='store_true',
                            help='Show the id of each song listed')
        parser.add_argument('--duration', dest='show_duration',
                            action='store_true',
                            help='Show the duration of each song listed')
        parser.add_argument('-r', '--root', dest='root',
                            help='List only songs in the given root')
        parser.add_argument('-g', '--genre', dest='genre',
                            help='List only songs with the given genre')
        parser.add_argument('--rating', dest='rating',
                            help='List only songs with the given rating')
        parser.add_argument('--my-rating', dest='my_rating',
                            help='List only songs with the given rating'
                            ' set by the current user')
        parser.add_argument('--others-rating', dest='others_rating',
                            help='List only songs with the given average'
                            'rating set by other users')
        parser.add_argument('paths', nargs='*')
        # list-genres command
        parser = sps.add_parser('list-genres',
                                description='Lists genres of songs '
                                            'in the database')
        parser.add_argument('-r', dest='root',
                            help='Only list genres of songs in a given root')
        parser.add_argument('-q', '--quoted', dest='quoted_output',
                            action='store_true',
                            help='Shows simplified, quoted output')
        parser.add_argument('id_or_paths', nargs='*')
        # list-genres command
        parser = sps.add_parser('list-roots',
                                description='Lists roots for songs')
        parser.add_argument('-q', '--quoted', dest='quoted_output',
                            action='store_true',
                            help='Shows simplified, quoted output')
        # fix-genres command
        parser = sps.add_parser('fix-genres',
                                description='Fix genres of songs '
                                            'in the database')
        parser.add_argument('id_or_paths', nargs='*')
        # list-similars command
        parser = sps.add_parser('list-similars',
                                description='List files marked as similar in '
                                            'the database')
        parser.add_argument('-l', dest='long_ls', action='store_true',
                            help='Run ls -l on the files')
        parser.add_argument('condition', nargs='*', help='An optional '
                            'condition on similarity (i.e. "> 0.8"). '
                            'By default: ">0.85"')
        # play command
        parser = sps.add_parser('play',
                                description='Play the specified songs')
        parser.add_argument('--shuffle', dest='shuffle', action='store_true',
                            help='Shuffle the songs before playing')
        parser.add_argument('-r', '--root', dest='root',
                            help='Play only songs in the given root')
        parser.add_argument('-g', '--genre', dest='genre',
                            help='Play only songs with the given genre')
        parser.add_argument('--rating', dest='rating',
                            help='Play only songs with the given rating')
        parser.add_argument('--my-rating', dest='my_rating',
                            help='List only songs with the given rating'
                            ' set by the current user')
        parser.add_argument('--others-rating', dest='others_rating',
                            help='List only songs with the given average'
                            'rating set by other users')
        parser.add_argument('paths', nargs='*')
        # fix-tags command
        parser = sps.add_parser('fix-tags',
                                description='Apply several normalization '
                                'algorithms to fix tags of files passed as '
                                'arguments')
        parser.add_argument('paths', nargs='*', metavar='file_or_directory')
        # update command
        parser = sps.add_parser('update',
                                description='Update database with new/modified'
                                '/deleted files')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        parser.add_argument('--process', dest='process',
                            action='store_true', help='Shortcut to '
                            'process-audio after the update finishes')
        # set-rating command
        parser = sps.add_parser('set-rating',
                                description='Set rating for a song or songs')
        parser.add_argument('-p', dest='playing', action='store_true',
                            help='Set rating for the currently playing song')
        parser.add_argument('rating', nargs='?')
        parser.add_argument('paths', nargs='*')

        # stats command
        parser = sps.add_parser('stats',
                                description='Print database statistics')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        # update-musicbrainz-ids command
        parser = sps.add_parser('update-musicbrainz-ids', description='Update '
                                'the database musicbrainz IDs from songs')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        # update-albums command
        parser = sps.add_parser('update-albums', description='Update '
                                'the albums to which songs belong to (this '
                                'should be never needed)')
        parser.add_argument('-r', '--regenerate', dest='regenerate',
                            action='store_true', help='Reassign the album '
                            'of all songs')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        # check-musicbrainz-tags command
        parser = sps.add_parser('check-musicbrainz-tags', description='Check '
                                'if there are songs which should have correct '
                                'musicbrainz tags but don\'t')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        # cache-musicbrainz-db command
        parser = sps.add_parser('cache-musicbrainz-db', description='Cache '
                                'musicbrainz tables by copying data into '
                                'new tables for fastest access')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        # web command
        parser = sps.add_parser('web',
                                description='Start a web server')
        # passwd command
        parser = sps.add_parser('passwd',
                                description='Sets a user password')
        parser.add_argument('username', nargs='?', help='Username whose '
                            'password will be set (current user if none)')

        parser = sps.add_parser('backup',
                                description='Backup music to target')
        parser.add_argument('target', nargs='?', help='Target destination')
        parser.add_argument('--priority', dest='priorityPatterns',
                            action='append', help='Pattern to backup first '
                            'when found in a directory')

        # analyze-songs command
        parser = sps.add_parser('analyze-songs', description='Perform a '
                                'high-level audio analysis of songs')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            default=0, help='Starts analyzing songs '
                            'from a specific song_id')
        # calculate-dr14 command
        parser = sps.add_parser('calculate-dr',
                                description='Parse a file and calculate '
                                'its Dynamic Range')
        parser.add_argument('-f', '--force', dest='force',
                            action='store_true', help='Force the recalculation'
                            ' of the dynamic range instead of reading it from '
                            'the database')
        parser.add_argument('ids_or_paths', nargs='*')
        # update-musicbrainz-artists command
        parser = sps.add_parser('update-musicbrainz-artists', description=''
                                'Recognize artists paths on the collection')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        # process-songs command
        parser = sps.add_parser('process-songs', description='Process songs '
                                'finding duplicates and doing a high-level '
                                'audio analysis (actually, a shortcut for '
                                'find-audio-duplicates and analyze-songs)')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            default=0, help='Starts processing songs '
                            'from a specific song_id')
        # mb-update command
        parser = sps.add_parser('mb-update', description='Download the latest '
                                'MusicBrainz database')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        # mb-import command
        parser = sps.add_parser('mb-import', description='Import downloaded '
                                'MusicBrainz data into the bard database')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        parser.add_argument('--update', dest='update',
                            action='store_true', help='Before importing the '
                            'MusicBrainz data, update the local copy from '
                            'which the data is imported')
        # mb-check-redirected-uuids command
        parser = sps.add_parser('mb-check-redirected-uuids', description='Check'
                                ' if there are songs with old MB uuids that '
                                'should be retagged')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true', help='Be verbose')
        parser.add_argument('--list-songs', dest='list_songs',
                            action='store_true', help='List the specific songs'
                            ' with old MB uuids instead of the albums '
                            'containing them')
        parser.add_argument('--group-size', type=int, metavar='group_size',
                            default=30, help='Group results in line of this '
                            'size elements')

        options = main_parser.parse_args()

        if not config.config and options.command != 'init':
            config_path = config.get_configuration_file_path()
            print('Configuration file not found. '
                  f'Please configure the application at {config_path}')
            sys.exit(1)

        if options.command == 'init':
            self.initBard()
        elif options.command == 'find-duplicates':
            self.findDuplicates()
        elif options.command == 'find-duplicates':
            self.fixMtime()
        elif options.command == 'fix-checksums':
            self.fixChecksums(options.from_song_id,
                              removeMissingFiles=options.remove_missing_files)
        elif options.command == 'add-silences':
            self.addSilences(options.paths, options.threshold,
                             options.min_length, options.silence_at_start,
                             options.silence_at_end, options.dry_run)
        elif options.command == 'check-songs-existence':
            paths = options.paths
            if not paths:
                paths = config.config['music_paths']
            self.checkSongsExistenceInPaths(paths, verbose=True,
                                            callback=self.db.removeSong)
        elif options.command == 'check-checksums':
            self.checkChecksums(options.from_song_id,
                                removeMissingFiles=options.remove_missing_files
                                )
        elif options.command == 'find-audio-duplicates':
            self.findAudioDuplicates(options.from_song_id, options.songs, verbose=options.verbose)
        elif options.command == 'compare-songs':
            self.compareSongIDsOrPaths(options.song1, options.song2,
                                       options.interactive)
        elif options.command == 'compare-files':
            self.compareFiles(options.song1, options.song2,
                              interactive=options.interactive)
        elif options.command == 'compare-dirs':
            self.compareDirectories(options.dir1, options.dirs,
                                    subset=options.subset,
                                    maxLengthDifference=options.max_length_diff,
                                    verbose=options.verbose)
        elif options.command == 'fix-tags':
            self.fixTags(options.paths)
        elif options.command == 'info':
            self.info(options.paths, options.playing, options.show_analysis, options.show_decode_messages)
        elif options.command == 'list' or options.command == 'ls':
            if not (options.paths or options.root or options.genre or
                    options.rating or options.my_rating or
                    options.others_rating):
                print('The list command needs either a '
                      'path/id/root/genre or rating parameter to list')
                sys.exit(1)
            query = Query(options.root, options.genre, options.my_rating,
                          options.others_rating, options.rating)
            if not options.paths:
                options.paths = ['']

            for path in options.paths:
                self.list(path, long_ls=options.long_ls,
                          show_id=options.show_id, query=query,
                          group_by_directory=options.group_by_directory,
                          show_duration=options.show_duration)
        elif options.command == 'list-genres':
            self.listGenres(id_or_paths=options.id_or_paths, root=options.root,
                            quoted_output=options.quoted_output)
        elif options.command == 'list-roots':
            self.listRoots(quoted_output=options.quoted_output)
        elif options.command == 'fix-genres':
            self.fixGenres(ids_or_paths=options.id_or_paths)
        elif options.command == 'list-similars':
            self.listSimilars(condition=options.condition,
                              long_ls=options.long_ls)
        elif options.command == 'play':
            query = Query(options.root, options.genre, options.my_rating,
                          options.others_rating, options.rating)
            self.play(options.paths, options.shuffle, query)
        elif options.command == 'import':
            paths = options.paths
            if not paths:
                paths = config.config['music_paths']

            self.add(paths)
        elif options.command == 'update':
            paths = config.config['music_paths']
            self.update(paths, verbose=options.verbose)
            if options.process:
                self.processSongs(verbose=options.verbose)
        elif options.command == 'set-rating':
            self.setRating(options.paths, options.rating, options.playing)
        elif options.command == 'stats':
            self.printStats(options.verbose)
        elif options.command == 'web':
            self.startWebServer()
        elif options.command == 'passwd':
            self.setPassword(options.username)
        elif options.command == 'backup':
            self.backupMusic(options.target, options.priorityPatterns)
        elif options.command == 'update-musicbrainz-ids':
            self.updateMusicBrainzIDs(verbose=options.verbose)
        elif options.command == 'update-albums':
            self.updateAlbums(regenerate=options.regenerate,
                              verbose=options.verbose)
        elif options.command == 'check-musicbrainz-tags':
            self.checkMusicBrainzTags(verbose=options.verbose)
        elif options.command == 'cache-musicbrainz-db':
            self.cacheMusicBrainzDB(verbose=options.verbose)
        elif options.command == 'analyze-songs':
            self.analyzeSongs(from_song_id=options.from_song_id,
                              verbose=options.verbose)
        elif options.command == 'fix-ratings':
            self.fixRatings(options.user_id, from_song_id=options.from_song_id,
                            verbose=options.verbose)
        elif options.command == 'update-musicbrainz-artists':
            self.updateMusicBrainzArtists(verbose=options.verbose)
        elif options.command == 'process-songs':
            self.processSongs(from_song_id=options.from_song_id,
                              verbose=options.verbose)
        elif options.command == 'mb-update':
            self.updateMusicBrainzDBDump(verbose=options.verbose)
        elif options.command == 'mb-import':
            if options.update:
                self.updateMusicBrainzDBDump(verbose=options.verbose)
            self.importMusicBrainzData(verbose=options.verbose)
        elif options.command == 'mb-check-redirected-uuids':
            self.checkRedirectedMusicBrainzUUIDs(list_songs=options.list_songs,
                                                 group_size=options.group_size,
                                                 verbose=options.verbose)
        elif options.command == 'scan-file':
            self.scanFile(options.path, printMatchInfo=options.printMatchInfo)
        elif options.command == 'calculate-dr':
            self.calculateDR(options.ids_or_paths, options.force)


def main():
    global bard
    bard = Bard()
    return bard.parseCommandLine()


if __name__ == "__main__":
    main()
