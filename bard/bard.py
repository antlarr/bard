#!/usr/bin/python3
from bard.utils import fixTags, calculateFileSHA256, \
    calculateAudioTrackSHA256, printDictsDiff
from bard.song import Song
from bard.musicdatabase import MusicDatabase
from bard.terminalcolors import TerminalColors
import chromaprint
import sys
import os
import re
import ctypes
import numpy
from gmpy import popcount
import mutagen
import argparse
import subprocess
from argparse import ArgumentParser
from bard.config import config


def bitsoncount(i):
    # assert 0 <= i < 0x100000000
    i = i - ((i >> 1) & 0x55555555)
    i = (i & 0x33333333) + ((i >> 2) & 0x33333333)
    return (((i + (i >> 4) & 0xF0F0F0F) * 0x1010101) & 0xffffffff) >> 24


def compareBits(x, y):
    i = 1
    same_bits = 0
    for c in range(32):
        if x & i == y & i:
            same_bits += 1
        i <<= 1
    return same_bits


def compareChromaprintFingerprints(a, b, threshold=0.9, cancelThreshold=0.55, offset=None):
    equal_bits = 0
    total_idx = min(len(a[0]), len(b[0]))
    total_bits = 32.0 * total_idx
    remaining = total_bits
    thresholdBits = int(total_bits * cancelThreshold)
    for i, (x, y) in enumerate(zip(a[0], b[0])):
        #print('old', offset, i, x, y)
        equal_bits += 32 - popcount(x.value ^ y.value)
        #print(equal_bits)
        remaining -= 32
        if equal_bits + remaining < thresholdBits:
            return -1
    return equal_bits / total_bits


def compareChromaprintFingerprintsAndOffset(a, b, maxoffset=50, debug=False):
    if not a[0] or not b[0]:
        return (None, None)

    cancelThreshold = 0.55
    equal_bits = [0] * (2 * maxoffset)
    result = equal_bits[:]
    total_idx = ([min(len(a[0]) - maxoffset + idx,
                      len(b[0]) - maxoffset) for idx in range(maxoffset)] +
                 list(reversed([min(len(a[0]) - maxoffset,
                                    len(b[0]) - maxoffset + idx)
                                for idx in range(1, maxoffset)])))
    total_bits = [32.0 * x for x in total_idx]
    remaining = total_bits[:]
    thresholdBits = [int(x * cancelThreshold) for x in total_bits]
    for offset in range(0, maxoffset):
        remaining = total_bits[offset]
        for i in range(total_idx[offset]):
#            x = a[0][i - offset]
#            y = b[0][i]
            equal_bits[offset] += 32 - popcount(a[0][i-offset].value ^ b[0][i].value)
            remaining -= 32
            if equal_bits[offset] + remaining < thresholdBits[offset]:
                result[offset] = -1
                break
        else:
            result[offset] = equal_bits[offset] / total_bits[offset]
#        print('new',offset, result[offset])

    for offset in reversed(range(-maxoffset + 1, 0)):
        remaining = total_bits[offset]
        for i in range(total_idx[offset]):
#            x = a[0][i]
#            y = b[0][i + offset]
            # print('new', offset, i, x, y)
            equal_bits[offset] += 32 - popcount(a[0][i].value ^ b[0][i+offset].value)
            remaining -= 32
            if equal_bits[offset] + remaining < thresholdBits[offset]:
                result[offset] = -1
                break
        else:
            result[offset] = equal_bits[offset] / total_bits[offset]
#        print('new',offset, result[offset])

    max_idx = numpy.argmax(result)
    max_val = result[max_idx]
    if max_idx > maxoffset:
        max_idx = -(maxoffset * 2 - max_idx)
    return (max_idx, max_val)


def compareChromaprintFingerprintsAndOffset2(a, b, maxoffset=50, debug=False):
    if not a[0] or not b[0]:
        return (None, None)
    tmp = (a[0][:], a[1])
    result_offset = 0
    result = compareChromaprintFingerprints(a, b)
    if debug:
        print(0, result)
    for i in range(1, maxoffset):
        tmp[0].insert(0, ctypes.c_uint32(0))
        r = compareChromaprintFingerprints(tmp, b)
        if debug:
            print(i, r)
        if r > result:
            result = r
            result_offset = i
    tmp = (b[0][:], b[1])
    for i in range(1, maxoffset):
        tmp[0].insert(0, ctypes.c_uint32(0))
        r = compareChromaprintFingerprints(a, tmp)
        if debug:
            print(-i, r)
        if r > result:
            result = r
            result_offset = -i
    if result < 0:
        result = None
    return (result_offset, result)


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


class Bard:

    def __init__(self, ro=False):
        self.db = MusicDatabase(ro)

        self.ignoreExtensions = ['.jpg', '.jpeg', '.bmp', '.tif', '.png',
                                 '.gif',
                                 '.m3u', '.pls', '.cue', '.m3u8', '.au',
                                 '.mid', '.kar', '.lyrics',
                                 '.url', '.lnk', '.ini', '.rar', '.zip',
                                 '.war', '.swp',
                                 '.txt', '.nfo', '.doc', '.rtf', '.pdf',
                                 '.html', '.log', '.htm',
                                 '.sfv', '.sfw', '.directory', '.sh',
                                 '.contents', '.torrent', '.cue_', '.nzb',
                                 '.md5', '.gz',
                                 '.fpl', '.wpl', '.accurip', '.db', '.ffp',
                                 '.flv', '.mkv', '.m4v', '.mov', '.mpg',
                                 '.mpeg', '.avi']

        self.excludeDirectories = ['covers', 'info']

    def getMusic(self, where_clause='', where_values=None):
        # print(where_clause)
        c = MusicDatabase.conn.cursor()
        statement = ('SELECT id, root, path, mtime, title, artist, album, '
                     'albumArtist, track, date, genre, discNumber, '
                     'coverWidth, coverHeight, coverMD5 FROM songs %s' %
                     where_clause)
        # print(statement, where_values)
        if where_values:
            result = c.execute(statement, where_values)
        else:
            result = c.execute(statement)
        r = []
        for x in result.fetchall():
            r.append(Song(x))
        return r

    def getSongs(self, path=None, songID=None):
        values = None
        if songID:
            where = 'WHERE id = %d' % songID
        elif not path.startswith('/'):
            # where = "WHERE path like '%%%s%%'" % (path)
            where = "WHERE path like ?"
            values = ('%' + path + '%',)
        else:
            # where = "WHERE path = '%s'" % (path)
            where = "WHERE path = ?"
            values = (path, )
        return self.getMusic(where_clause=where, where_values=values)

    def addSong(self, path):
        if config['immutableDatabase']:
            print("Error: Can't add song %s : "
                  "The database is configured as immutable" % path)
            return
        song = Song(path)
        if not song.isValid:
            print('Song %s is not valid' % path)
            sys.exit(1)
        MusicDatabase.addSong(song)
        MusicDatabase.commit()

    def addDirectoryRecursively(self, directory):
        if config['immutableDatabase']:
            print("Error: Can't add directory %s : "
                  "The database is configured as immutable" % directory)
            return
        for dirpath, dirnames, filenames in os.walk(directory, topdown=True):
            print('New dir: %s' % dirpath)
            filenames.sort()
            dirnames.sort()
            for filename in filenames:
                if True in [filename.lower().endswith(ext)
                            for ext in self.ignoreExtensions]:
                    continue

                path = os.path.join(dirpath, filename)
                if MusicDatabase.isSongInDatabase(path):
                    print('Already in db: %s' % filename)
                    continue
                song = Song(path, rootDir=directory)
                if not song.isValid:
                    print('Skipping: %s' % filename)
                    continue
                MusicDatabase.addSong(song)
            MusicDatabase.commit()

            for excludeDir in self.excludeDirectories:
                try:
                    dirnames.remove(excludeDir)
                except ValueError:
                    pass

    def add(self, args):
        for arg in args:
            if os.path.isfile(arg):
                self.addSong(os.path.normpath(arg))

            elif os.path.isdir(arg):
                self.addDirectoryRecursively(os.path.normpath(arg))

    def info(self, path):
        try:
            songID = int(path)
        except ValueError:
            songID = None
        if songID:
            songs = self.getSongs(songID=songID)
        else:
            songs = self.getSongs(path=path)

        for song in songs:
            song.loadMetadataInfo()
            print("----------")
            try:
                filesize = "%d bytes" % os.path.getsize(song.path())
            except FileNotFoundError:
                filesize = "File not found"
            print("%s (%s)" % (song.path(), filesize))
            print("song id:", song.id)
            for k, v in song.metadata.items():
                print(TerminalColors.WARNING + str(k) + TerminalColors.ENDC +
                      ' : ' + str(v)[:100])
            print("file sha256sum: ", song.fileSha256sum())
            print("audio track sha256sum: ", song.audioSha256sum())

            print('duration:', song.duration())
            print('bitrate :', song.bitrate())
            print('bits_per_sample:', song.bits_per_sample())
            print('sample_rate    :', song.sample_rate())
            print('channels:', song.channels())
            if song.coverWidth():
                print('cover:  %dx%d' %
                      (song.coverWidth(), song.coverHeight()))

    def list(self, path, long_ls=False, show_id=False):
        try:
            songID = int(path)
        except ValueError:
            songID = None
        if songID:
            songs = self.getSongs(songID=songID)
        else:
            songs = self.getSongs(path=path)
        for song in songs:
            if show_id:
                print('%d) ' % song.id, end='', flush=True)
            if long_ls:
                command = ['ls', '-l', song.path()]
                subprocess.run(command)
            else:
                print("%s" % song.path())

    def listSimilars(self, condition=None, long_ls=False):
        if isinstance(condition, list):
            condition = ' '.join(condition)
        similar_pairs = MusicDatabase.getSimilarSongs(condition)
        for songID1, songID2, offset, similarity in similar_pairs:
            song1 = self.getSongs(songID=songID1)[0]
            song2 = self.getSongs(songID=songID2)[0]
            print('------  (%d ~=~ %d) offset: %d   similarity %f' %
                  (songID1, songID2, offset, similarity))
            for song in (song1, song2):
                if long_ls:
                    command = ['ls', '-l', song.path()]
                    subprocess.run(command)
                else:
                    print("%s" % song.path())

    def play(self, ids_or_paths):
        paths = []
        for id_or_path in ids_or_paths:
            songs = self.getSongsFromIDorPath(id_or_path)
            for song in songs:
                paths.append(song.path())

        command = ['mpv'] + paths
        process = subprocess.run(command)

    def findDuplicates(self):
        collection = self.getMusic()
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
        collection = self.getMusic()
        count = 0
        for song in collection:
            if not song.mtime():
                try:
                    mtime = os.path.getmtime(song.path())
                except os.FileNotFoundError:
                    print('File %s not found: removing from db' % song.path())
                    MusicDatabase.removeSong(song)
                    continue

                if not config['immutableDatabase']:
                    c = MusicDatabase.conn.cursor()
                    values = [mtime, song.id]
                    c.execute('''UPDATE songs set mtime = ? WHERE id = ?''',
                              values)
                    count += 1
                    if count % 10:
                        MusicDatabase.commit()
                print('Fixed %s' % song.path())
            else:
                print('%s already fixed' % song.path())
        MusicDatabase.commit()

    def checkSongsExistence(self):
        collection = self.getMusic()
        count = 0
        for song in collection:
            if not os.path.exists(song.path()):
                if os.path.lexists(song.path()):
                    print('Broken symlink at %s' % song.path())
                else:
                    print('Removing song %s from DB: File not found' %
                          song.path())
                    self.db.removeSong(song)
                continue

            if song.mtime() == os.path.getmtime(song.path()):
                print('Correct in db: %s' % song.path())
                continue
            song = Song(song.path(), rootDir=song.root())
            if not song.isValid:
                print('Skipping: %s' % song.path())
                continue
            MusicDatabase.addSong(song)

            count += 1
            if count % 10:
                MusicDatabase.commit()
        MusicDatabase.commit()

    def fixChecksums(self, from_song_id=None):
        if from_song_id:
            collection = self.getMusic("WHERE id >= ?", (int(from_song_id),))
        else:
            collection = self.getMusic()
        count = 0
        forceRecalculate = True
        for song in collection:
            if not os.path.exists(song.path()):
                if os.path.lexists(song.path()):
                    print('Broken symlink at %s' % song.path())
                else:
                    print('Removing song %s from DB: File not found' %
                          song.path())
                    self.db.removeSong(song)
                continue
            # sha256InDB = song.fileSha256sum()
            # if not sha256InDB:
            #     print('Calculating SHA256sum for %s' % song.path())
            #     sha256InDisk = calculateFileSHA256(song.path())
            #     MusicDatabase.addFileSha256sum(song.id, sha256InDisk)
            #     count += 1
            #     if count % 10:
            #         MusicDatabase.commit()
            # else:
            #    print('Skipping %s' % song.path())
            audioSha256sumInDB = song.audioSha256sum()
            if not audioSha256sumInDB or forceRecalculate:
                print('Calculating SHA256sum for %s' % song.path())
                calc = calculateAudioTrackSHA256  # Just to prevent an E501
                audioSha256sumInDisk = calc(song.path(),
                                            tmpdir=config['tmpdir'])
                # print('Setting audio track sha256 %s to %s' %
                #       (audioSha256sum, song.path()))
                if audioSha256sumInDB != audioSha256sumInDisk:
                    if audioSha256sumInDB:
                        print('Audio SHA256sum differ in disk and DB: '
                              '(%s != %s)' %
                              (audioSha256sumInDisk, audioSha256sumInDB))
                    MusicDatabase.addAudioTrackSha256sum(song.id,
                                                         audioSha256sumInDisk)
                    count += 1
                    if count % 10:
                        MusicDatabase.commit()
            else:
                print('Skipping %s' % song.path())

        MusicDatabase.commit()
        print('done')

    def checkChecksums(self, from_song_id=None):
        if from_song_id:
            collection = self.getMusic("WHERE id >= ?", (int(from_song_id),))
        else:
            collection = self.getMusic()
        failedSongs = []
        for song in collection:
            if not os.path.exists(song.path()):
                if os.path.lexists(song.path()):
                    print('Broken symlink at %s' % song.path())
                else:
                    print('Removing song %s from DB: File not found' %
                          song.path())
                    self.db.removeSong(song)
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
                    print(TerminalColors.OKGREEN + 'OK' + TerminalColors.ENDC)
                else:
                    print(TerminalColors.FAIL + 'FAIL' + TerminalColors.ENDC +
                          ' (db contains %s, disk is %s)' %
                          (sha256InDB, sha256InDisk))
                    failedSongs.append(song)

        if failedSongs:
            print('Failed songs:')
            for song in failedSongs:
                print('%d %s' % (song.id, song.path()))
        else:
            print('All packages successfully checked: ' +
                  TerminalColors.OKGREEN + 'OK' + TerminalColors.ENDC)

    def fixTags(self, args):
        for path in args:
            if not os.path.isfile(path):
                print('"%s" is not a file. Skipping.' % path)
                continue

            mutagenFile = mutagen.File(path)
            fixTags(mutagenFile)

            if (MusicDatabase.isSongInDatabase(path) and
               not path.startswith('/tmp/')):
                self.addSong(path)

    def findAudioDuplicates(self, from_song_id=0):
        c = MusicDatabase.conn.cursor()
        fingerprints = {}
        info = {}
        decodedFPs = {}
        matchThreshold = 0.8
        storeThreshold = 0.55
        maxoffset = 50
        sql = ('SELECT id, fingerprint, sha256sum, audio_sha256sum, path, '
               'completeness FROM fingerprints, songs, checksums, '
               'properties where songs.id=fingerprints.song_id and '
               'songs.id = checksums.song_id and '
               'songs.id = properties.song_id order by id')
        for (songID, fingerprint, sha256sum, audioSha256sum, path,
                completeness) in c.execute(sql):
            # print('.', songID,  end='', flush=True)
            dfp = chromaprint.decode_fingerprint(fingerprint)
#            dfp = ([ctypes.c_uint32(x) for x in dfp[0]], dfp[1])
            dfp = ([ctypes.c_uint32(x) for x in dfp[0]] + [ctypes.c_uint32(0)] * maxoffset, dfp[1])
            if not dfp[0]:
                print("Error calculating fingerprint of song %s (%s)" %
                      (songID, path))
                continue
            if songID < from_song_id:
                fingerprints[fingerprint] = songID
                decodedFPs[fingerprint] = dfp
                info[songID] = (sha256sum, audioSha256sum, path, completeness)
                continue
            if songID > from_song_id:
                return

            for fp, otherSongID in fingerprints.items():
                offset, similarity = \
                    compareChromaprintFingerprintsAndOffset(
                        decodedFPs[fp], dfp)
                if similarity and similarity >= storeThreshold:
                    print('******** %d %d %d %f' % (otherSongID, songID,
                                                    offset, similarity))
                    MusicDatabase.addSongsSimilarity(otherSongID, songID,
                                                     offset, similarity)
                    MusicDatabase.commit()
                else:
                    if similarity:
                        print('%d %d %d %f' % (otherSongID, songID,
                                               offset, similarity))
                    else:
                        print('%d %d different' % (otherSongID, songID))

                if similarity and similarity >= matchThreshold:
                    # print('''Duplicates found!\n''',
                    #       songID, fingerprint, path)
                    # print('''Duplicates found!\n''', fp)
                    # print('''Duplicates found!\n''', fingerprints[fp])
                    (otherSha256sum, otherAudioSha256sum, otherPath,
                        otherCompleteness) = info[fingerprints[fp]]
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
                    else:
                        msg = 'Similarity %f' % similarity
                        # print('Duplicate songs found: %s\n     %s\n'
                        #       'and %s' % (msg, otherPath, path))
                    break

            fingerprints[fingerprint] = songID
            decodedFPs[fingerprint] = dfp
            info[songID] = (sha256sum, audioSha256sum, path, completeness)

    def findAudioDuplicates2(self, from_song_id=None):
        c = MusicDatabase.conn.cursor()
        info = {}
        matchThreshold = 0.8
        storeThreshold = 0.56
        if not from_song_id:
            from_song_id = 0
        from bard.bard_ext import FingerprintManager
        fpm = FingerprintManager()
        fpm.setMaxOffset(100)

        sql = ('SELECT id, fingerprint, sha256sum, audio_sha256sum, path, '
               'completeness FROM fingerprints, songs, checksums, '
               'properties where songs.id=fingerprints.song_id and '
               'songs.id = checksums.song_id and '
               'songs.id = properties.song_id order by id')

        for (songID, fingerprint, sha256sum, audioSha256sum, path,
                completeness) in c.execute(sql):
            # print('.', songID,  end='', flush=True)
            dfp = chromaprint.decode_fingerprint(fingerprint)
            if not dfp[0]:
                print("Error calculating fingerprint of song %s (%s)" %
                      (songID, path))
                continue
            if songID < from_song_id:
                fpm.addSong(songID, dfp[0])
                result = []
            else:
#                if songID > from_song_id:
#                    return
                result = fpm.addSongAndCompare(songID, dfp[0], storeThreshold)

            for (songID2, offset, similarity) in result:
                print('******** %d %d %d %f' % (songID2, songID,
                                                offset, similarity))
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
                    else:
                        msg = 'Similarity %f' % similarity
                        # print('Duplicate songs found: %s\n     %s\n'
                        #       'and %s' % (msg, otherPath, path))
            if result:
                MusicDatabase.commit()

            info[songID] = (sha256sum, audioSha256sum, path, completeness)

    def getSongsFromIDorPath(self, id_or_path):
        try:
            songID = int(id_or_path)
        except ValueError:
            songID = None

        if songID:
            return self.getSongs(songID=songID)

        return self.getSongs(path=id_or_path)

    def compareSongs(self, song1, song2):
        matchThreshold = 0.8
        storeThreshold = 0.55
        maxoffset = 50
        dfp1 = chromaprint.decode_fingerprint(song1.getAcoustidFingerprint())
        dfp1 = ([ctypes.c_uint32(x) for x in dfp1[0]] + [ctypes.c_uint32(0)] * maxoffset,
                dfp1[1])
        dfp2 = chromaprint.decode_fingerprint(song2.getAcoustidFingerprint())
        dfp2 = ([ctypes.c_uint32(x) for x in dfp2[0]] + [ctypes.c_uint32(0)] * maxoffset,
                dfp2[1])
        (offset, similarity) = compareChromaprintFingerprintsAndOffset(dfp1,
                                                                       dfp2,
                                                                       maxoffset,
                                                                       True)
        if similarity and similarity >= storeThreshold \
                and song1.id and song2.id:
            print('******** %d %d %d %f' % (song1.id, song2.id,
                                            offset, similarity))
            # MusicDatabase.addSongsSimilarity(song1.id, song2.id,
            #                                  offset, similarity)
            # MusicDatabase.commit()

        dfp1 = chromaprint.decode_fingerprint(song1.getAcoustidFingerprint())
        dfp1 = ([ctypes.c_uint32(x) for x in dfp1[0]], dfp1[1])
        dfp2 = chromaprint.decode_fingerprint(song2.getAcoustidFingerprint())
        dfp2 = ([ctypes.c_uint32(x) for x in dfp2[0]], dfp2[1])
        (offset, similarity) = compareChromaprintFingerprintsAndOffset2(dfp1,
                                                                        dfp2,
                                                                        maxoffset,
                                                                        True)

        if similarity and similarity >= storeThreshold \
                and song1.id and song2.id:
            print('******** %d %d %d %f' % (song1.id, song2.id,
                                            offset, similarity))
        return

        if similarity and similarity >= matchThreshold:
            if song1.fileSha256sum() == song2.fileSha256sum():
                msg = ('Exactly the same files (sha256 = %s)' %
                       song1.fileSha256sum())
                print('Duplicate songs : %s\n'
                      '%s\n and %s' % (msg, song1.path(), song2.path()))
            elif song1.audioSha256sum() == song2.audioSha256sum():
                msg = ('Same audio track with different tags '
                       '(completeness: %d <-> %d)' % (song1.completeness,
                                                      song2.completeness))
                print('Duplicate songs : %s\n'
                      '%s\n and %s' % (msg, song1.path(), song2.path()))
            else:
                msg = 'Similarity %f' % similarity
                print('Similar songs found: %s\n'
                      '%s\n and %s' % (msg, song1.path(), song2.path()))
        else:
            print('''Songs not similar (similarity: %f)''' % similarity)

        song1.loadMetadataInfo()
        song2.loadMetadataInfo()
        printDictsDiff(song1.metadata, song2.metadata, forcePrint=True)

        if song1.metadata == song2.metadata:
            print('Songs have identical metadata!')

    def compareSongIDsOrPaths(self, songid1, songid2):
        songs1 = self.getSongsFromIDorPath(songid1)
        if len(songs1) != 1:
            print('No match or more than one match for ', songid1)
            return
        song1 = songs1[0]
        songs2 = self.getSongsFromIDorPath(songid2)
        if len(songs2) != 1:
            print('No match or more than one match for ', songid2)
            return
        song2 = songs2[0]
        self.compareSongs(song1, song2)

    def compareFiles(self, path1, path2):
        song1 = Song(path1)
        song2 = Song(path2)
        self.compareSongs(song1, song2)

    def parseCommandLine(self):
        main_parser = ArgumentParser(
            description='Manage your music collection',
                        formatter_class=argparse.RawTextHelpFormatter)
        sps = main_parser.add_subparsers(
            dest='command', metavar='command',
            help='''The following commands are available:
find-duplicates     find duplicate files comparing the checksums
find-audio-duplicates
                    find duplicate files comparing the audio fingerprint
compare-songs [id_or_path] [id_or_path]
                    compares two songs given their paths or song id
compare-files [path] [path]
                    compares two files not neccesarily in the database
fix-mtime           fixes the mtime of imported files (you should never
                    need to use this)
fix-checksums       fixes the checksums of imported files (you should
                    never need to use this)
check-songs-existence
                    check for removed files to remove them from the
                    database
check-checksums     check that the imported files haven't been modified
                    since they were imported
import [file_or_directory [file_or_directory ...]]
                    import new (or update) music. You can specify the
                    files/directories to import as arguments. If no
                    arguments are given in the command line, the
                    musicPaths entries in the configuration file are used
info <file | song id>
                    shows information about a song from the database
list|ls [-l] [-i|--id] <file | song id> [file | song_id ...]
                    lists paths to a song from the database
list-similars [-l] [condition]
                    lists files marked as similar in the database
                    (with find-audio-duplicates)
play <file | song id> [file | song_id ...]
                    play the specified songs using mpv
fix-tags <file_or_directory [file_or_directory ...]>
                    apply several normalization algorithms to fix tags of
                    files passed as arguments
update
                    Update database with new/modified/deleted files''')
        # find-duplicates command
        sps.add_parser('find-duplicates',
                       description='Find duplicate files comparing '
                                   'the checksums')
        # find-audio-duplicates command
        parser = sps.add_parser('find-audio-duplicates',
                                description='Find duplicate files comparing '
                                            'the audio fingerprint')
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            help='Starts fixing checksums from a specific '
                                 'song_id')
        # compare-songs command
        parser = sps.add_parser('compare-songs',
                                description='Compares two songs')
        parser.add_argument('song1', metavar='id_or_path')
        parser.add_argument('song2', metavar='id_or_path')
        parser = sps.add_parser('compare-files',
                                description='Compares two files not'
                                ' neccesarily in the database')
        parser.add_argument('song1', metavar='path')
        parser.add_argument('song2', metavar='path')
        # fix-mtime command
        sps.add_parser('fix-mtime',
                       description='Fixes the mtime of imported files '
                                   '(you should never need to use this)')
        # fix-checksums command
        parser = sps.add_parser('fix-checksums',
                                description='Fixes the checksums of imported '
                                'files (you should never need to use this)')
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            help='Starts fixing checksums from a specific '
                                 'song_id')
        # check-songs-existence command
        sps.add_parser('check-songs-existence',
                       description='Check for removed files to remove them '
                                   'from the database')
        # check-checksums command
        parser = sps.add_parser('check-checksums',
                                description='Check that the imported files '
                                "haven't been modified since they were "
                                "imported")
        parser.add_argument('--from-song-id', type=int, metavar='from_song_id',
                            help='Starts fixing checksums '
                                 'from a specific song_id')
        # import command
        parser = sps.add_parser('import',
                                description='Import new (or update) music. '
                                'You can specify the files/directories to '
                                'import as arguments. If no arguments are '
                                'given in the command line, the musicPaths '
                                'entries in the configuration file are used')
        parser.add_argument('paths', nargs='*', metavar='file_or_directory')
        # info command
        parser = sps.add_parser('info',
                                description='Shows information about a song '
                                            'from the database')
        parser.add_argument('path', nargs=1)
        # list command
        parser = sps.add_parser('list',
                                description='Lists paths to songs '
                                            'from the database')
        parser.add_argument('-l', dest='long_ls', action='store_true',
                            help='Actually run ls -l')
        parser.add_argument('-i', '--id', dest='show_id', action='store_true',
                            help='Show the id of each song listed')
        parser.add_argument('paths', nargs='+')
        parser = sps.add_parser('ls',
                                description='Lists paths to songs '
                                            'from the database')
        parser.add_argument('-l', dest='long_ls', action='store_true',
                            help='Actually run ls -l')
        parser.add_argument('-i', '--id', dest='show_id', action='store_true',
                            help='Show the id of each song listed')
        parser.add_argument('paths', nargs='+')
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
        parser.add_argument('paths', nargs='+')
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
        options = main_parser.parse_args()

        if options.command == 'find-duplicates':
            self.findDuplicates()
        elif options.command == 'find-duplicates':
            self.fixMtime()
        elif options.command == 'fix-checksums':
            self.fixChecksums(options.from_song_id)
        elif options.command == 'check-songs-existence':
            self.checkSongsExistence()
        elif options.command == 'check-checksums':
            self.checkChecksums(options.from_song_id)
        elif options.command == 'find-audio-duplicates':
            self.findAudioDuplicates2(options.from_song_id)
        elif options.command == 'compare-songs':
            self.compareSongIDsOrPaths(options.song1, options.song2)
        elif options.command == 'compare-files':
            self.compareFiles(options.song1, options.song2)
        elif options.command == 'fix-tags':
            self.fixTags(options.paths)
        elif options.command == 'info':
            self.info(options.path[0])
        elif options.command == 'list' or options.command == 'ls':
            for path in options.paths:
                self.list(path, long_ls=options.long_ls,
                          show_id=options.show_id)
        elif options.command == 'list-similars':
            self.listSimilars(condition=options.condition,
                              long_ls=options.long_ls)
        elif options.command == 'play':
            self.play(options.paths)
        elif options.command == 'import':
            paths = options.paths
            if not paths:
                paths = config['musicPaths']

            self.add(paths)
        elif options.command == 'update':
            paths = config['musicPaths']
            self.add(paths)
            self.checkSongsExistence()


def main():
    app = Bard()
    return app.parseCommandLine()


if __name__ == "__main__":
    main()
