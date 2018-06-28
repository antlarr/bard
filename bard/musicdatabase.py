# -*- coding: utf-8 -*-

from bard.config import config
from bard.normalizetags import normalizeTagValues
import sqlite3
import os
import re
import mutagen


def toString(v):
    if isinstance(v, list):
        return ', '.join(v)

    return v


class MusicDatabase:
    conn = None

    def __init__(self, ro=False):
        """Create a MusicDatabase object."""
        _databasepath = config['databasePath']
        databasepath = os.path.expanduser(os.path.expandvars(_databasepath))
        if not os.path.isdir(os.path.dirname(databasepath)):
            os.makedirs(os.path.dirname(databasepath))
        if not os.path.isfile(databasepath):
            if ro:
                raise Exception("Database doesn't exist and read-only was "
                                "requested")
            MusicDatabase.conn = sqlite3.connect(databasepath)
            self.createDatabase()
        else:
            uri = 'file:' + databasepath
            if ro:
                uri += '?mode=ro'
            MusicDatabase.conn = sqlite3.connect(uri, uri=True)
        MusicDatabase.conn.execute('pragma foreign_keys=ON')
        MusicDatabase.conn.row_factory = sqlite3.Row

    def createDatabase(self):
        if config['immutableDatabase']:
            print("Error: Can't create database: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.conn.cursor()
        c.execute('''
CREATE TABLE songs (
                    id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                    root TEXT,
                    path TEXT,
                    filename TEXT,
                    mtime TIMESTAMP,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    albumArtist TEXT,
                    track INTEGER,
                    date TEXT,
                    genre TEXT,
                    discNumber INTEGER,
                    coverWidth INTEGER,
                    coverHeight INTEGER,
                    coverMD5 TEXT,
                    completeness REAL
                   )''')
        c.execute('''
CREATE TABLE properties(
                    song_id INTEGER,
                    format TEXT,
                    duration REAL,
                    bitrate REAL,
                    bits_per_sample INTEGER,
                    sample_rate INTEGER,
                    channels INTEGER,
                    audio_sha256sum TEXT,
                    silence_at_start REAL,
                    silence_at_end REAL,
                    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                 )''')
        c.execute('''
CREATE TABLE tags(
                    song_id INTEGER,
                    name TEXT,
                    value TEXT,
                    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                 )''')
        c.execute('''
CREATE TABLE covers(
                  path TEXT,
                  cover TEXT
                  )''')
        c.execute('''
CREATE TABLE checksums(
                  song_id INTEGER,
                  sha256sum TEXT,
                  FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                  )''')
        c.execute('''
CREATE TABLE fingerprints(
                  song_id INTEGER,
                  fingerprint TEXT,
                  FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                  )''')
        c.execute('''
CREATE TABLE similarities(
                  song_id1 INTEGER,
                  song_id2 INTEGER,
                  offset INTEGER,
                  similarity REAL,
                  UNIQUE(song_id1, song_id2),
                  FOREIGN KEY(song_id1) REFERENCES songs(id) ON DELETE CASCADE,
                  FOREIGN KEY(song_id2) REFERENCES songs(id) ON DELETE CASCADE
                  )''')
        c.execute('''
 CREATE TABLE users (
                  id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                  name TEXT
                  )''')
        c.execute('''
 CREATE TABLE ratings (
                  user_id INTEGER,
                  song_id INTEGER,
                  rating INTEGER,
                  UNIQUE(user_id, song_id),
                  FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE,
                  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                  )''')

    @staticmethod
    def addSong(song):
        if config['immutableDatabase']:
            print("Error: Can't add song to DB: "
                  "The database is configured as immutable")
            return
        song.calculateCompleteness()

        c = MusicDatabase.conn.cursor()
        result = c.execute('''SELECT id FROM songs where path = ? ''',
                           (song.path(),))
        songID = result.fetchone()

        values = [(song.root(), song.path(), song.filename(), song.mtime(),
                   song['title'], toString(song['artist']), song['album'],
                   song['albumartist'], song['tracknumber'], song['date'],
                   toString(song['genre']), song['discnumber'],
                   song.coverWidth(), song.coverHeight(), song.coverMD5(),
                   song.completeness), ]

        if songID:  # song is already in db, we have to update it
            song.id = songID[0]
            print('Updating song %s' % song.path())
            values = [values[0][3:] + (song.path(), )]
            sql = ('UPDATE songs SET mtime=?, title=?, artist=?, album=?, '
                   'albumArtist=?, track=?, date=?, genre=?, discNumber=?, '
                   'coverWidth=?, coverHeight=?, coverMD5=?, completeness=? '
                   'WHERE path = ?')
            c.executemany(sql, values)

            values = [(song.fileSha256sum(), song.id), ]
            c.executemany('UPDATE checksums SET sha256sum=? WHERE song_id=?',
                          values)

            values = [(song.fingerprint, song.id), ]
            c.executemany('UPDATE fingerprints SET fingerprint=? '
                          'WHERE song_id=?', values)

            values = [(song.format(), song.duration(), song.bitrate(),
                       song.bits_per_sample(), song.sample_rate(),
                       song.channels(), song.audioSha256sum(),
                       song.silenceAtStart(), song.silenceAtEnd(), song.id), ]
            c.executemany('UPDATE properties SET format=?, duration=?, '
                          'bitrate=?, bits_per_sample=?, sample_rate=?, '
                          'channels=?, audio_sha256sum=?, silence_at_start=?, '
                          'silence_at_end=? WHERE song_id=?''',
                          values)

            values = [(song.id), ]
            c.execute('''DELETE from tags where song_id = ?''', (song.id,))

            tags = []
            for key, values in song.metadata.items():
                values = normalizeTagValues(values, song.metadata, key)

                if isinstance(values, list):
                    for value in values:
                        tags.append((song.id, key, value))
                else:
                    if isinstance(values, mutagen.apev2.APEBinaryValue):
                        continue
                    tags.append((song.id, key, str(values)))
            # print(tags)
            c.executemany('INSERT INTO tags(song_id, name, value) '
                          'VALUES (?,?,?)', tags)
        else:
            print('Adding new song %s' % song.path())
            print(values[0][3:])
            c.executemany('INSERT INTO songs(root, path, filename, mtime, '
                          'title, artist, album, albumArtist, track, date, '
                          'genre, discNumber, coverWidth, coverHeight, '
                          'coverMD5, completeness) '
                          'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values)

            result = c.execute('''SELECT last_insert_rowid()''')
            song.id = result.fetchone()[0]

            values = [(song.id, song.fileSha256sum()), ]
            c.executemany('INSERT INTO checksums(song_id, sha256sum) '
                          'VALUES (?,?)', values)

            values = [(song.id, song.fingerprint), ]
            c.executemany('INSERT INTO fingerprints(song_id, fingerprint) '
                          'VALUES (?,?)', values)

            values = [(song.id, song.format(), song.duration(), song.bitrate(),
                       song.bits_per_sample(), song.sample_rate(),
                       song.channels(), song.audioSha256sum(),
                       song.silenceAtStart(), song.silenceAtEnd()), ]
            c.executemany('INSERT INTO properties(song_id, format, duration, '
                          'bitrate, bits_per_sample, sample_rate, channels, '
                          'audio_sha256sum, silence_at_start, silence_at_end) '
                          'VALUES (?,?,?,?,?,?,?,?,?,?)', values)

            tags = []
            for key, values in song.metadata.items():
                values = normalizeTagValues(values, song.metadata, key)

                if isinstance(values, list):
                    for value in values:
                        tags.append((song.id, key, value))
                else:
                    if isinstance(values, mutagen.apev2.APEBinaryValue):
                        continue
                    tags.append((song.id, key, str(values)))
            # print(tags)
            c.executemany('INSERT INTO tags(song_id, name, value) '
                          'VALUES (?,?,?)', tags)

    @staticmethod
    def removeSong(song):
        if config['immutableDatabase']:
            print("Error: Can't remove song %d from DB: "
                  "The database is configured as immutable" % song.id)
            return
        c = MusicDatabase.conn.cursor()
        c.execute('DELETE FROM covers where path = ? ', (song.path(),))
        c.execute('DELETE FROM checksums where song_id = ? ', (song.id,))
        c.execute('DELETE FROM fingerprints where song_id = ? ', (song.id,))
        c.execute('DELETE FROM tags where song_id = ? ', (song.id,))
        c.execute('DELETE FROM properties where song_id = ? ', (song.id,))
        c.execute('DELETE FROM ratings where song_id = ? ', (song.id,))
        c.execute('DELETE FROM songs where id = ? ', (song.id,))
        MusicDatabase.commit()

    @staticmethod
    def getSongsCount():
        c = MusicDatabase.conn.cursor()

        result = c.execute('SELECT COUNT(*) FROM songs')
        count = result.fetchone()
        return count[0]

    @staticmethod
    def addCover(pathToSong, pathToCover):
        if config['immutableDatabase']:
            print("Error: Can't add cover to song: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.conn.cursor()

        result = c.execute('''SELECT path FROM covers where path = ? ''',
                           (os.path.normpath(pathToSong),))
        path = result.fetchone()
        if path:  # cover is already in db, we have to update it
            values = [(pathToCover, os.path.normpath(pathToSong)), ]
            c.executemany('UPDATE covers set cover=?  WHERE path = ?',
                          values)
        else:
            values = [(os.path.normpath(pathToSong), pathToCover), ]
            c.executemany('INSERT INTO covers(path, cover) VALUES (?,?)',
                          values)

    @staticmethod
    def isSongInDatabase(path=None, songID=None):
        c = MusicDatabase.conn.cursor()
        if songID:
            result = c.execute('SELECT mtime, path FROM songs where id = ? ',
                               (songID,))
            mtime, path = result.fetchone()
        else:
            result = c.execute('SELECT mtime FROM songs where path = ? ',
                               (os.path.normpath(path),))
            mtime = result.fetchone()
            if not mtime:
                return False
            mtime = mtime[0]
        if mtime == os.path.getmtime(path):
            return True
        return False

    @staticmethod
    def getSongTags(songID):
        c = MusicDatabase.conn.cursor()
        result = c.execute('SELECT name, value FROM tags where song_id = ? ',
                           (songID,))
        tags = {}
        for name, value in result.fetchall():
            if name not in tags:
                tags[name] = [value]
            else:
                tags[name] += [value]
        return tags

    @staticmethod
    def getSongProperties(songID):
        c = MusicDatabase.conn.cursor()
        result = c.execute('''SELECT format, duration, bitrate,
                     bits_per_sample, sample_rate, channels, audio_sha256sum,
                     silence_at_start, silence_at_end
                     FROM properties where song_id = ? ''', (songID,))
        row = result.fetchone()
        info = type('info', (), {})()

        try:
            info.length = row['duration']
            info.bitrate = row['bitrate']
            info.bits_per_sample = row['bits_per_sample']
            info.sample_rate = row['sample_rate']
            info.channels = row['channels']
        except KeyError:
            print('Error getting song properties for song ID %d' % songID)
            raise

        return row['format'], info, row['audio_sha256sum'], \
            (row['silence_at_start'], row['silence_at_end'])

    @staticmethod
    def getSimilarSongsToSongID(songID, similarityThreshold=0.85):
        c = MusicDatabase.conn.cursor()
        result = c.execute('select song_id1, offset, similarity '
                           '  from similarities '
                           ' where song_id2=? and similarity>=? '
                           '   union '
                           'select song_id2, offset, similarity '
                           '  from similarities '
                           ' where song_id1=? and similarity>=?''',
                           (songID, similarityThreshold,
                            songID, similarityThreshold))
        similarSongs = [(x[0], x[1], x[2]) for x in result.fetchall()]

        return similarSongs

    @staticmethod
    def areSongsSimilar(songID1, songID2, similarityThreshold=0.85):
        if songID1 > songID2:
            songID1, songID2 = songID2, songID1
        c = MusicDatabase.conn.cursor()
        sql = '''select 1 from similarities where song_id1=?
                              and song_id2=? and similarity>=?'''
        result = c.execute(sql, (songID1, songID2, similarityThreshold))
        return result.fetchone() is not None

    @staticmethod
    def songsSimilarity(songID1, songID2):
        if songID1 > songID2:
            songID1, songID2 = songID2, songID1
        c = MusicDatabase.conn.cursor()
        sql = '''select similarity from similarities where song_id1=?
                              and song_id2=?'''
        result = c.execute(sql, (songID1, songID2))
        x = result.fetchone()
        if not x:
            return 0
        return x[0]

    @staticmethod
    def commit():
        if config['immutableDatabase']:
            MusicDatabase.conn.rollback()
            return
        MusicDatabase.conn.commit()

    @staticmethod
    def addFileSha256sum(songid, sha256sum):
        if config['immutableDatabase']:
            print("Error: Can't add file SHA256: The database is configured "
                  "as immutable")
            return
        c = MusicDatabase.conn.cursor()
        c.execute('INSERT INTO checksums (song_id, sha256sum) VALUES (?, ?) ',
                  (songid, sha256sum))

    @staticmethod
    def addAudioTrackSha256sum(songid, audioSha256sum):
        if config['immutableDatabase']:
            print("Error: Can't add file SHA256: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.conn.cursor()
        c.execute('UPDATE properties set audio_sha256sum=? where song_id=?',
                  (audioSha256sum, songid))

    @staticmethod
    def addAudioSilences(songid, silence_at_start, silence_at_end):
        if config['immutableDatabase']:
            print("Error: Can't set song silences: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.conn.cursor()
        c.execute('UPDATE properties set silence_at_start=?, silence_at_end=? '
                  'where song_id=?',
                  (silence_at_start, silence_at_end, songid))

    @staticmethod
    def addSongsSimilarity(songid1, songid2, offset, similarity):
        if config['immutableDatabase']:
            print("Error: Can't add song similarity: "
                  "The database is configured as immutable")
            return
        if songid1 > songid2:
            songid1, songid2 = songid2, songid1
        elif songid1 == songid2 and (similarity != 1.0 or offset != 0):
            print("Error: A song should be exactly similar to itself")
            print(songid1, songid2, similarity, offset)
            return
        elif songid1 == songid2:
            print("Error: A song shouldn't be compared with itself")
            print(songid1, songid2, similarity, offset)
            return
        c = MusicDatabase.conn.cursor()
        c.execute('UPDATE similarities set offset=?, similarity=? '
                  'where song_id1=? and song_id2=?',
                  (offset, similarity, songid1, songid2))
        if c.rowcount == 0:
            c.execute('INSERT INTO similarities '
                      '(song_id1, song_id2, offset, similarity) '
                      'VALUES (?,?,?,?)',
                      (songid1, songid2, offset, similarity))

    @staticmethod
    def getSimilarSongs(condition=None):
        if not condition:
            condition = '> 0.85'
        else:
            condition = re.match(r'[0-9<>= .]*', condition).group()
        c = MusicDatabase.conn.cursor()
        result = c.execute('SELECT song_id1, song_id2, offset, similarity '
                           'FROM similarities WHERE similarity %s' % condition)
        pairs = []
        for songid1, songid2, offset, similarity in result.fetchall():
            pairs.append((songid1, songid2, offset, similarity))
        return pairs

    @staticmethod
    def getGenres(ids=[], paths=[], root=None):
        tables = 'tags'
        if root:
            condition = 'AND song_id IN (select id from songs where root = ?)'
            variables = (root,)
        else:
            condition = ''
            variables = ()
        if ids:
            condition += (' AND song_id in (%s)' %
                          (','.join([str(x) for x in ids])))
        if paths:
            part = ''
            for path in paths:
                if part:
                    part += ' OR path like ?'
                else:
                    part = 'path like ?'
                variables += ('%' + paths[0] + '%',)
            condition += ' AND id = song_id AND (%s)' % part
            tables += ',songs'

        sql = '''select value, count(*) 'c'
                   from %s
                  where (name like 'genre' OR name='TCON')
                        %s
                  group by value
                  order by c''' % (tables, condition)
        print(sql, variables)
        c = MusicDatabase.conn.cursor()
        result = c.execute(sql, variables)
        pairs = []
        for genre, count in result.fetchall():
            pairs.append((genre.split('\0'), count))
        return pairs

    @staticmethod
    def getUserID(username, create=True):
        sql = 'select id from users where name = ?'
        c = MusicDatabase.conn.cursor()
        result = c.execute(sql, (username,))
        userID = result.fetchone()
        if userID:
            return userID[0]

        if create:
            sql = 'INSERT INTO users(name) VALUES (?)'
            c.execute(sql, (username,))

            result = c.execute('''SELECT last_insert_rowid()''')
            userID = result.fetchone()[0]
            MusicDatabase.commit()
            return userID

        return None
