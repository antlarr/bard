from bard.config import config
from bard.normalizetags import normalizeTagValues
import sqlite3
import os
import mutagen


def toString(v):
    if isinstance(v, list):
        return ', '.join(v)

    return v


class MusicDatabase:
    conn = None

    def __init__(self, ro=False):
        databasepath = os.path.expanduser(os.path.expandvars(config['databasePath']))
        if not os.path.isdir(os.path.dirname(databasepath)):
            os.makedirs(os.path.dirname(databasepath))
        if not os.path.isfile(databasepath):
            if ro:
                raise Exception("Database doesn't exist and read-only was requested")
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
            print("Error: Can't create database: The database is configured as immutable")
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

    @staticmethod
    def addSong(song):
        if config['immutableDatabase']:
            print("Error: Can't add song to DB: The database is configured as immutable")
            return
        song.calculateCompleteness()

        c = MusicDatabase.conn.cursor()
        result = c.execute('''SELECT id FROM songs where path = ? ''', (song.path(),))
        songID = result.fetchone()

        values = [(song.root(), song.path(), song.filename(), song.mtime(), song['title'], toString(song['artist']), song['album'], song['albumartist'], song['tracknumber'], song['date'], toString(song['genre']), song['discnumber'], song.coverWidth(), song.coverHeight(), song.coverMD5(), song.completeness), ]

        if songID:  # song is already in db, we have to update it
            song.id = songID[0]
            print('Updating song %s' % song.path())
            values = [values[0][3:] + (song.path(), )]
            c.executemany('''UPDATE songs SET mtime=?, title=?, artist=?, album=?, albumArtist=?, track=?, date=?, genre=?, discNumber=?, coverWidth=?, coverHeight=?, coverMD5=?, completeness=?
                             WHERE path = ?''', values)

            values = [(song.fileSha256sum(), song.id), ]
            c.executemany('''UPDATE checksums SET sha256sum=? WHERE song_id=?''', values)

            values = [(song.fingerprint, song.id), ]
            c.executemany('''UPDATE fingerprints SET fingerprint=? WHERE song_id=?''', values)

            values = [(song.format(), song.duration(), song.bitrate(), song.bits_per_sample(), song.sample_rate(), song.channels(), song.audioSha256sum(), song.id), ]
            c.executemany('''UPDATE properties SET format=?, duration=?, bitrate=?, bits_per_sample=?, sample_rate=?, channels=?, audio_sha256sum=? WHERE song_id=?''', values)

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
            c.executemany('''INSERT INTO tags(song_id, name, value) VALUES (?,?,?)''', tags)
            # for tag in tags:
            #     print(tag)
            #     c.executemany('''INSERT INTO tags(song_id, name, value) VALUES (?,?,?)''', (tag,))
        else:
            print('Adding new song %s' % song.path())
            print(values[0][3:])
            c.executemany('''INSERT INTO songs(root, path, filename, mtime, title, artist, album, albumArtist, track, date, genre, discNumber, coverWidth, coverHeight, coverMD5, completeness)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', values)

            result = c.execute('''SELECT last_insert_rowid()''')
            song.id = result.fetchone()[0]

            values = [(song.id, song.fileSha256sum()), ]
            c.executemany('''INSERT INTO checksums(song_id, sha256sum) VALUES (?,?)''', values)

            values = [(song.id, song.fingerprint), ]
            c.executemany('''INSERT INTO fingerprints(song_id, fingerprint) VALUES (?,?)''', values)

            values = [(song.id, song.format(), song.duration(), song.bitrate(), song.bits_per_sample(), song.sample_rate(), song.channels(), song.audioSha256sum()), ]
            c.executemany('''INSERT INTO properties(song_id, format, duration, bitrate, bits_per_sample, sample_rate, channels, audio_sha256sum) VALUES (?,?,?,?,?,?,?,?)''', values)

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
            c.executemany('''INSERT INTO tags(song_id, name, value) VALUES (?,?,?)''', tags)
            # for tag in tags:
            #     print(tag)
            #     c.executemany('''INSERT INTO tags(song_id, name, value) VALUES (?,?,?)''', (tag,))

    @staticmethod
    def removeSong(song):
        if config['immutableDatabase']:
            print("Error: Can't remove song %d from DB: The database is configured as immutable" % song.id)
            return
        c = MusicDatabase.conn.cursor()
        c.execute('''DELETE FROM covers where path = ? ''', (song.path(),))
        c.execute('''DELETE FROM checksums where song_id = ? ''', (song.id,))
        c.execute('''DELETE FROM fingerprints where song_id = ? ''', (song.id,))
        c.execute('''DELETE FROM tags where song_id = ? ''', (song.id,))
        c.execute('''DELETE FROM properties where song_id = ? ''', (song.id,))
        c.execute('''DELETE FROM songs where id = ? ''', (song.id,))
        MusicDatabase.commit()

    @staticmethod
    def addCover(pathToSong, pathToCover):
        if config['immutableDatabase']:
            print("Error: Can't add cover to song: The database is configured as immutable")
            return
        c = MusicDatabase.conn.cursor()

        result = c.execute('''SELECT path FROM covers where path = ? ''', (os.path.normpath(pathToSong),))
        path = result.fetchone()
        if path:  # cover is already in db, we have to update it
            values = [(pathToCover, os.path.normpath(pathToSong)), ]
            c.executemany('''UPDATE covers set cover=?  WHERE path = ?''', values)
        else:
            values = [(os.path.normpath(pathToSong), pathToCover), ]
            c.executemany('''INSERT INTO covers(path, cover) VALUES (?,?)''', values)

    @staticmethod
    def isSongInDatabase(path=None, songID=None):
        c = MusicDatabase.conn.cursor()
        if songID:
            result = c.execute('''SELECT mtime, path FROM songs where id = ? ''', (songID,))
            mtime, path = result.fetchone()
        else:
            result = c.execute('''SELECT mtime FROM songs where path = ? ''', (os.path.normpath(path),))
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
        result = c.execute('''SELECT name, value FROM tags where song_id = ? ''', (songID,))
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
        result = c.execute('''SELECT format, duration, bitrate, bits_per_sample, sample_rate, channels, audio_sha256sum FROM properties where song_id = ? ''', (songID,))
        row = result.fetchone()
        info = type('info', (), {})()

        try:
            info.length = row['duration']
            info.bitrate = row['bitrate']
            info.bits_per_sample = row['bits_per_sample']
            info.sample_rate = row['sample_rate']
            info.channels = row['channels']
        except:
            print('Error getting song properties for song ID %d' % songID)
            raise

        return row['format'], info, row['audio_sha256sum']

    @staticmethod
    def commit():
        if config['immutableDatabase']:
            MusicDatabase.conn.rollback()
            return
        MusicDatabase.conn.commit()

    @staticmethod
    def addFileSha256sum(songid, sha256sum):
        if config['immutableDatabase']:
            print("Error: Can't add file SHA256: The database is configured as immutable")
            return
        c = MusicDatabase.conn.cursor()
        c.execute('''INSERT INTO checksums (song_id, sha256sum) VALUES (?, ?) ''', (songid, sha256sum))

    @staticmethod
    def addAudioTrackSha256sum(songid, audioSha256sum):
        if config['immutableDatabase']:
            print("Error: Can't add file SHA256: The database is configured as immutable")
            return
        c = MusicDatabase.conn.cursor()
        c.execute('''UPDATE properties set audio_sha256sum=? where song_id=?''', (audioSha256sum, songid))
