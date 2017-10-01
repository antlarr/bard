# -*- coding: utf-8 -*-

from bard.config import config
from bard.utils import md5, calculateAudioTrackSHA256_audioread, extractFrontCover, \
    md5FromData, calculateFileSHA256, manualAudioCmp
from bard.musicdatabase import MusicDatabase
from bard.normalizetags import getTag
from bard.ffprobemetadata import FFProbeMetadata
import sqlite3
import os
import shutil
import random
import subprocess
from PIL import Image
import acoustid
import mutagen


class DifferentLengthException(Exception):
    pass


class SlightlyDifferentLengthException(Exception):
    pass


class DifferentSongsException(Exception):
    pass


class CantCompareSongsException(Exception):
    pass


class Ratings:
    def __init__(self):
        c = MusicDatabase.conn.cursor()
        sql = 'SELECT user_id, song_id, rating FROM ratings'
        result = c.execute(sql)
        self.ratings = {}
        for user_id, song_id, rating in result.fetchall():
            try:
                self.ratings[user_id][song_id] = rating
            except KeyError:
                self.ratings[user_id] = {}
                self.ratings[user_id][song_id] = rating

    def getSongRatings(self, user_id, song_id):
        try:
            return self.ratings[user_id][song_id]
        except KeyError:
            return 5


class Song:

    def __init__(self, x, rootDir=None):
        self.tags = {}
        Song.ratings = None
        if type(x) == sqlite3.Row:
            self.id = x['id']
            self._root = x['root']
            self._path = x['path']
            self._mtime = x['mtime']
            self._coverWidth = x['coverWidth']
            self._coverHeight = x['coverHeight']
            self._coverMD5 = x['coverMD5']
            # metadata will be loaded on demand
            self.isValid = True
            return
        self.isValid = False
        self._root = rootDir or ''
        self._path = os.path.normpath(x)
        self.loadFile(x)

    def hasID(self):
        try:
            return self.id is not None
        except AttributeError:
            return False

    def loadMetadata(self):
        if getattr(self, 'metadata', None) is not None:
            return

        if getattr(self, 'id', None) is not None:
            self.metadata = type('info', (dict,), {})()
            self.metadata.update(MusicDatabase.getSongTags(self.id))
            return

        self.loadFile(self._path)
        if self.metadata is None:
            raise Exception("Couldn't load metadata!")

    def loadMetadataInfo(self):
        if getattr(self, 'metadata', None) is None:
            self.loadMetadata()
        elif getattr(self.metadata, 'info', None) is not None:
            return

        (self._format, self.metadata.info, self._audioSha256sum) = \
            MusicDatabase.getSongProperties(self.id)

    def loadCoverImageData(self, path):
        self._coverWidth, self._coverHeight = 0, 0
        self._coverMD5 = ''
        random_number = random.randint(0, 100000)
        coverfilename = os.path.join(config['tmpdir'],
                                     '/cover-%d.jpg' % random_number)

        MusicDatabase.addCover(path, coverfilename)
        # c = self.conn.cursor()

        # values = [ ( path, coverfilename), ]
        # c.executemany('''INSERT INTO covers(path, cover) VALUES (?,?)''',
        #               values)
        command = ['ffmpeg', '-i', path, '-map', '0:m:comment:Cover (front)',
                   '-c', 'copy', coverfilename]

        process = subprocess.run(command, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        if process.returncode != 0:
            # try with any image in the file
            process = subprocess.run(['ffmpeg', '-i', path, '-c', 'copy',
                                      coverfilename],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
            if process.returncode != 0:
                return

        try:
            image = Image.open(coverfilename)
            self._coverWidth, self._coverHeight = image.size
            self._coverMD5 = md5(coverfilename)
        except IOError:
            print('Error reading cover file from %s' % path)
            return

        os.unlink(coverfilename)

    def getAcoustidFingerprint(self):
        fp = acoustid.fingerprint_file(self._path)
        return fp[1]

    def loadFile(self, path):
        try:
            # if path.lower().endswith('.ape') or
            #    path.lower().endswith('.wma') or
            #    path.lower().endswith('.m4a') or
            #    path.lower().endswith('.mp3'):
            self.metadata = mutagen.File(path)
            # else:
            #     self.metadata = mutagen.File(path, easy=True)
        except mutagen.mp3.HeaderNotFoundError as e:
            print("Error reading %s:" % path, e)
            raise

        if not self.metadata:
            print("No metadata found for %s : "
                  "This will probably cause problems" % path)

        formattext = {
            mutagen.mp3.EasyMP3: 'mp3',
            mutagen.mp3.MP3: 'mp3',
            mutagen.easymp4.EasyMP4: 'mp4',
            mutagen.mp4.MP4: 'mp4',
            mutagen.asf.ASF: 'asf',
            mutagen.flac.FLAC: 'flac',
            mutagen.oggvorbis.OggVorbis: 'ogg',
            mutagen.wavpack.WavPack: 'wv',
            mutagen.monkeysaudio.MonkeysAudio: 'ape',
            mutagen.musepack.Musepack: 'mpc', }
        self._format = formattext[type(self.metadata)]

        tmpdir = config['tmpdir']
        self._audioSha256sum = calculateAudioTrackSHA256_audioread(path)


#        self.loadCoverImageData(path)
        try:
            image = extractFrontCover(self.metadata)
        except OSError:
            print('Error extracting image from %s' % path)
            raise

        if image:
            (image, data) = image
            self._coverWidth = image.width
            self._coverHeight = image.height
            self._coverMD5 = md5FromData(data)

        self._mtime = os.path.getmtime(path)
        self._fileSha256sum = calculateFileSHA256(path)

        self.fingerprint = self.getAcoustidFingerprint()

        self.isValid = True

    def root(self):
        return self._root

    def path(self):
        if config['translatePaths']:
            for (src, tgt) in config['pathTranslationMap']:
                src = src.rstrip('/')
                tgt = tgt.rstrip('/')
                if self._path.startswith(src):
                    return tgt + self._path[len(src):]
        return self._path

    def filename(self):
        return os.path.basename(self._path)

    def mtime(self):
        return self._mtime

    def format(self):
        self.loadMetadataInfo()
        return self._format

    def isLossless(self):
        self.loadMetadataInfo()
        return self._format in ['flac', 'wv', 'ape', 'mpc']

    def audioCmp(self, other, forceSimilar=False, interactive=True,
                 useColors=None):
        """Compare the audio of this object with the audio of other.

        Returns -1 if self has better audio than other,
        1 if other has better audio than self and 0 if they have
        audio of the same characteristics. Also, it can raise
        a SongsNotComparableException exception if audio has
        different length or it's not similar according to
        chromaprint fingerprints
        """
        self.loadMetadataInfo()
        other.loadMetadataInfo()
        if self._audioSha256sum == other._audioSha256sum:
            return 0

        if not forceSimilar and not MusicDatabase.areSongsSimilar(self.id,
                                                                  other.id):
            raise DifferentSongsException(
                'Trying to compare different songs (%d and %d)'
                % (self.id, other.id))

        len_diff = abs(self.metadata.info.length - other.metadata.info.length)
        if len_diff > 30:
            raise DifferentLengthException(
                'Songs duration is too different (%d and %d seconds)'
                % (self.metadata.info.length, other.metadata.info.length))

        if len_diff > 3:
            raise SlightlyDifferentLengthException(
                'Songs duration is slightly different (%d and %d seconds)'
                % (self.metadata.info.length, other.metadata.info.length))

        if not interactive:
            if self.isLossless() and not other.isLossless():
                return -1
            if other.isLossless() and not self.isLossless():
                return 1

        si = self.metadata.info
        oi = other.metadata.info
        try:
            sbps = si.bits_per_sample
        except AttributeError:
            sbps = None
        try:
            obps = oi.bits_per_sample
        except AttributeError:
            obps = None

        if not interactive:
            if si.bitrate > oi.bitrate \
               and ((sbps and obps and sbps >= obps) or
                    (not sbps and not obps)) \
               and si.channels >= oi.channels \
               and si.sample_rate >= oi.sample_rate:
                return -1

            if oi.bitrate > si.bitrate \
               and ((sbps and obps and obps >= sbps) or
                    (not sbps and not obps)) \
               and oi.channels >= si.channels \
               and oi.sample_rate >= si.sample_rate:
                return 1

            if oi.bitrate == si.bitrate \
               and ((sbps and obps and obps == sbps) or
                    (not sbps and not obps)) \
               and oi.channels == si.channels \
               and oi.sample_rate == si.sample_rate:
                return 0

        if interactive:
            filename1 = '/tmp/1'
            filename2 = '/tmp/2'
            shutil.copyfile(self.path(), filename1)
            shutil.copyfile(other.path(), filename2)
            result = manualAudioCmp(filename1, filename2, useColors=useColors)
            os.unlink(filename1)
            os.unlink(filename2)
            if result:
                return result

        raise CantCompareSongsException('Not sure how to compare songs')

    def __getitem__(self, key):
        if not getattr(self, 'metadata', None):
            self.loadMetadata()
        return getTag(self.metadata, key)

#     def title(self):
#         tag_names = ['title', 'Title']
#         for tag in tag_names:
#             try:
#                 value = self.metadata[tag]
#             except KeyError:
#                 continue
#
#             if isinstance(value, list):
#                 if len(self.metadata[tag]) > 1:
#                     raise ValueError('List with multiple values: %s' % value)
#                 value = value[0]
#
#             if isinstance(value, mutagen.asf.ASFUnicodeAttribute):
#                 return value.value
#             if isinstance(value, mutagen.apev2.APETextValue):
#                 return str(value)
#             return value
#
#         return None
#
#     def artist(self):
#         if len(self.metadata['artist']) > 1:
#             raise ValueError('List with multiple values: %s' %
#                              self.metadata['artist'])
#         try:
#             return self.metadata['artist'][0]
#         except KeyError:
#             return None
#
#     def album(self):
#         if 'album' in self.metadata and len(self.metadata['album']) > 1:
#             raise ValueError('List with multiple values: %s' %
#                              self.metadata['album'])
#         try:
#             return self.metadata['album'][0]
#         except KeyError:
#             return None
#
#     def albumArtist(self):
#         if 'albumartist' in self.metadata and \
#            isinstance(self.metadata['albumartist'], list) and \
#            len(self.metadata['albumartist']) > 1:
#             raise ValueError('List with multiple values: %s' %
#                              self.metadata['albumartist'])
#         try:
#             return self.metadata['album artist'][0]
#         except KeyError:
#             try:
#                 return self.metadata['albumartist'][0]
#             except KeyError:
#                 return None
#
#     def tracknumber(self):
#         try:
#             return self.metadata['tracknumber'][0]
#         except KeyError:
#             try:
#                 return str(self.metadata['track'])
#             except KeyError:
#                 return None
#
#     def date(self):
#         try:
#             return self.metadata['date'][0]
#         except KeyError:
#             try:
#                 return str(self.metadata['year'])
#             except KeyError:
#                 return None
#
#     def genre(self):
#         try:
#             return ', '.join(self.metadata['genre'])
#         except KeyError:
#             return None
#
#     def discNumber(self):
#         try:
#             return self.metadata['discnumber'][0]
#         except KeyError:
#             try:
#                 return self.metadata['disc'][0]
#             except KeyError:
#                 return None
#
#     def musicbrainz_trackid(self):
#         try:
#             return self.metadata['musicbrainz_trackid'][0]
#         except KeyError:
#             return None

    def duration(self):
        self.loadMetadataInfo()
        return self.metadata.info.length

    def bitrate(self):
        self.loadMetadataInfo()
        try:
            return self.metadata.info.bitrate
        except AttributeError:
            ffprobe_metadata = FFProbeMetadata(self.path())
            print(ffprobe_metadata)
            return ffprobe_metadata['format.bit_rate']

    def bits_per_sample(self):
        self.loadMetadataInfo()
        try:
            return self.metadata.info.bits_per_sample
        except AttributeError:
            return None

    def sample_rate(self):
        self.loadMetadataInfo()
        return self.metadata.info.sample_rate

    def channels(self):
        self.loadMetadataInfo()
        return self.metadata.info.channels

    def audioSha256sum(self):
        try:
            return self._audioSha256sum
        except AttributeError:
            c = MusicDatabase.conn.cursor()
            sql = 'SELECT audio_sha256sum FROM properties where song_id = ?'
            result = c.execute(sql, (self.id,))
            sha = result.fetchone()
            if sha:
                self._audioSha256sum = sha[0]
                return self._audioSha256sum
            return ''

    def hasCover(self):
        return self.coverWidth() > 0

    def coverWidth(self):
        try:
            return self._coverWidth
        except AttributeError:
            return 0

    def coverHeight(self):
        try:
            return self._coverHeight
        except AttributeError:
            return 0

    def coverMD5(self):
        try:
            return self._coverMD5
        except AttributeError:
            return ''

    def fileSha256sum(self):
        try:
            return self._fileSha256sum
        except AttributeError:
            c = MusicDatabase.conn.cursor()
            sql = 'SELECT sha256sum FROM checksums where song_id = ?'
            result = c.execute(sql, (self.id,))
            sha = result.fetchone()
            if sha:
                self._fileSha256sum = sha[0]
                return self._fileSha256sum
            return ''

    def imageSize(self):
        try:
            if not self._coverWidth:
                return 'nocover'
            return '%dx%d' % (self._coverWidth, self._coverHeight)
        except AttributeError:
            return 'nocover'

    def userRating(self, user_id=0):
        if not Song.ratings:
            Song.ratings = Ratings()
        return Song.ratings.getSongRatings(user_id, self.id)

    def calculateCompleteness(self):
        value = 100
        data = [self['title'], self['artist'], self['album'],
                self['albumartist'], self['date'], self['genre'],
                self['tracknumber'], self.coverWidth(),
                self['musicbrainz_trackid']]
        value = 100 - sum(10 for x in data if not x)

        if self.coverWidth() and self.coverWidth() < 400:
            value -= 3

        self.completeness = value

    def __repr__(self):
        return ('%s %s %s %s %s %s %s %s %s %s %s %s' % (self.audioSha256sum(),
                self._path, str(self.metadata.info.length), str(self['title']),
                str(self['artist']), str(self['album']),
                str(self['albumartist']), str(self['tracknumber']),
                str(self['date']), str(self['genre']), str(self['discnumber']),
                self.imageSize()))
