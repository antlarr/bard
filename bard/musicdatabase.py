# -*- coding: utf-8 -*-

from bard.config import config
from bard.normalizetags import normalizeTagValues
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import sqlite3
import os
import re
import threading
import mutagen


def toString(v):
    if isinstance(v, list):
        return ', '.join(v)

    return v


class MusicDatabase:
    conn = {}
    mtime_cache_by_path = {}
    mtime_cache_by_id = {}
    uri = None
    like = 'like'

    def __init__(self, ro=False):
        """Create a MusicDatabase object."""
        try:
            database = config['database']
        except KeyError:
            database = 'sqlite'

        if database == 'postgresql':
            name = config['database_name']
            user = config['database_user']
            password = config['database_password']
            MusicDatabase.uri = f'postgresql://{user}:{password}@/{name}'
            MusicDatabase.like = 'ilike'
        else:
            _dbpath = config['databasePath']
            databasepath = os.path.expanduser(os.path.expandvars(_dbpath))
            if not os.path.isdir(os.path.dirname(databasepath)):
                os.makedirs(os.path.dirname(databasepath))
            if not os.path.isfile(databasepath):
                if ro:
                    raise Exception("Database doesn't exist and read-only was "
                                    "requested")
                MusicDatabase.conn[threading.get_ident()] = \
                    sqlite3.connect(databasepath)
                self.createDatabase()
            else:
                MusicDatabase.uri = 'sqlite:///' + databasepath
                if ro:
                    MusicDatabase.uri += '?mode=ro'
        MusicDatabase.engine = create_engine(MusicDatabase.uri)
        MusicDatabase.getConnection()

    @staticmethod
    def getConnection():
        currentThread = threading.get_ident()
        try:
            return MusicDatabase.conn[currentThread]
        except KeyError:
            s = Session(bind=MusicDatabase.engine)
            MusicDatabase.conn[currentThread] = s
            return s

    @staticmethod
    def getCursor():
        return MusicDatabase.getConnection()

    def createDatabase(self):
        if config['immutableDatabase']:
            print("Error: Can't create database: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.getCursor()
        c.execute('''
CREATE TABLE songs (
                    id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                    root TEXT,
                    path TEXT,
                    filename TEXT,
                    mtime NUMERIC(20,8),
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
                    song_id INTEGER PRIMARY KEY,
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
                    name TEXT NOT NULL,
                    value TEXT,
                    pos INTEGER,
                    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                 )''')
        c.execute('CREATE INDEX ON tags (song_id)')
        c.execute('''
CREATE TABLE covers(
                  path TEXT,
                  cover BYTEA NOT NULL
                  )''')
        c.execute('''
CREATE TABLE checksums(
                  song_id INTEGER PRIMARY KEY,
                  sha256sum TEXT NOT NULL,
                  FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                  )''')
        c.execute('''
CREATE TABLE fingerprints(
                  song_id INTEGER PRIMARY KEY,
                  fingerprint BYTEA NOT NULL,
                  FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                  )''')
        c.execute('''
CREATE TABLE similarities(
                  song_id1 INTEGER,
                  song_id2 INTEGER,
                  match_offset INTEGER NOT NULL,
                  similarity REAL NOT NULL,
                  UNIQUE(song_id1, song_id2),
                  FOREIGN KEY(song_id1) REFERENCES songs(id) ON DELETE CASCADE,
                  FOREIGN KEY(song_id2) REFERENCES songs(id) ON DELETE CASCADE
                  )''')
        c.execute('CREATE INDEX similarities_song_id1_idx ON similarities (song_id1)')
        c.execute('CREATE INDEX similarities_song_id2_idx ON similarities (song_id2)')

        c.execute('''
 CREATE TABLE users (
                  id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                  name TEXT,
                  password TEXT
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

        c = MusicDatabase.getCursor()
        sql = text('SELECT id FROM songs where path = :path')

        result = c.execute(sql.bindparams(path=song.path()))
        songID = result.fetchone()

        values = {'path': song.path(),
                  'mtime': song.mtime(),
                  'title': song['title'],
                  'artist': toString(song['artist']),
                  'album': song['album'],
                  'albumartist': song['albumartist'],
                  'track': song['tracknumber'],
                  'date': song['date'],
                  'genre': toString(song['genre']),
                  'discnumber': song['discnumber'],
                  'coverwidth': song.coverWidth(),
                  'coverheight': song.coverHeight(),
                  'covermd5': song.coverMD5(),
                  'completeness': song.completeness
                  }

        if songID:  # song is already in db, we have to update it
            song.id = songID[0]
            print('Updating song %s' % song.path())
            sql = ('UPDATE songs SET mtime=:mtime, title=:title, '
                   'artist=:artist, album=:album, albumArtist=:albumartist, '
                   'track=:track, date=:date, genre=:genre, '
                   'discNumber=:discnumber, coverWidth=:coverwidth, '
                   'coverHeight=:coverheight, coverMD5=:covermd5, '
                   'completeness=:completeness WHERE path = :path')

            c.execute(text(sql).bindparams(**values))

            values = {'sha256sum': song.fileSha256sum(),
                      'id': song.id}
            sql = 'UPDATE checksums SET sha256sum=:sha256sum WHERE song_id=:id'
            c.execute(text(sql).bindparams(**values))

            values = {'fingerprint': song.fingerprint,
                      'id': song.id}
            sql = ('UPDATE fingerprints SET fingerprint=:fingerprint '
                   'WHERE song_id=:id')
            c.execute(text(sql).bindparams(**values))

            values = {'format': song.format(),
                      'duration': song.duration(),
                      'bitrate': song.bitrate(),
                      'bits_per_sample': song.bits_per_sample(),
                      'sample_rate': song.sample_rate(),
                      'channels': song.channels(),
                      'audio_sha256sum': song.audioSha256sum(),
                      'silence_at_start': song.silenceAtStart(),
                      'silence_at_end': song.silenceAtEnd(),
                      'id': song.id}
            sql = ('UPDATE properties SET format=:format, duration=:duration, '
                   'bitrate=:bitrate, bits_per_sample=:bits_per_sample, '
                   'sample_rate=:sample_rate, channels=:channels, '
                   'audio_sha256sum=:audio_sha256sum, '
                   'silence_at_start=:silence_at_start, '
                   'silence_at_end=:silence_at_end WHERE song_id=:id')
            c.execute(text(sql).bindparams(**values))

            values = {'id': song.id}
            sql = 'DELETE from tags where song_id = :id'
            c.execute(text(sql).bindparams(**values))

            tags = []
            for key, values in song.metadata.items():
                key, values = normalizeTagValues(values, song.metadata, key, removeBinaryData=True)

                if isinstance(values, list):
                    for pos, value in enumerate(values):
                        tags.append({'id': song.id,
                                     'name': key,
                                     'value': value,
                                     'pos': pos if len(values) > 1 else None
                                     })
                else:
                    if isinstance(values, mutagen.apev2.APEBinaryValue):
                        continue
                    tags.append({'id': song.id,
                                 'name': key,
                                 'value': values,
                                 'pos': None
                                 })
            if tags:
                # print('1', tags)
                sql = ('INSERT INTO tags(song_id, name, value, pos) '
                       'VALUES (:id,:name,:value,:pos)')
                try:
                    c.execute(text(sql), tags)
                except ValueError:
                    c.rollback()
                    print(sql, tags)
                    raise
        else:
            print('Adding new song %s' % song.path())
            values.update({'root': song.root(),
                           'filename': song.filename()})
            print(values)
            sql = ('INSERT INTO songs(root, path, filename, mtime, '
                   'title, artist, album, albumArtist, track, date, '
                   'genre, discNumber, coverWidth, coverHeight, '
                   'coverMD5, completeness) '
                   'VALUES (:root,:path,:filename,:mtime,:title,:artist,'
                   ':album,:albumartist,:track,:date,:genre,:discnumber,'
                   ':coverwidth,:coverheight,:covermd5,:completeness)')
            c.execute(text(sql).bindparams(**values))

#            result = c.execute('SELECT last_insert_rowid()')
            sql = "SELECT currval(pg_get_serial_sequence('songs','id'))"
            result = c.execute(sql)
            song.id = result.fetchone()[0]

            values = {'sha256sum': song.fileSha256sum(),
                      'id': song.id}
            sql = ('INSERT INTO checksums(song_id, sha256sum) '
                   'VALUES (:id,:sha256sum)')
            c.execute(text(sql).bindparams(**values))

            values = {'fingerprint': song.fingerprint,
                      'id': song.id}
            sql = ('INSERT INTO fingerprints(song_id, fingerprint) '
                   'VALUES (:id,:fingerprint)')
            c.execute(text(sql).bindparams(**values))

            values = {'format': song.format(),
                      'duration': song.duration(),
                      'bitrate': song.bitrate(),
                      'bits_per_sample': song.bits_per_sample(),
                      'sample_rate': song.sample_rate(),
                      'channels': song.channels(),
                      'audio_sha256sum': song.audioSha256sum(),
                      'silence_at_start': song.silenceAtStart(),
                      'silence_at_end': song.silenceAtEnd(),
                      'id': song.id}
            sql = ('INSERT INTO properties(song_id, format, duration, '
                   'bitrate, bits_per_sample, sample_rate, channels, '
                   'audio_sha256sum, silence_at_start, silence_at_end) '
                   'VALUES (:id,:format,:duration,:bitrate,:bits_per_sample,'
                   ':sample_rate,:channels,:audio_sha256sum,'
                   ':silence_at_start,:silence_at_end)')
            c.execute(text(sql).bindparams(**values))

            tags = []
            for key, values in song.metadata.items():
                key, values = normalizeTagValues(values, song.metadata, key, removeBinaryData=True)

                if isinstance(values, list):
                    for pos, value in enumerate(values):
                        tags.append({'id': song.id,
                                     'name': key,
                                     'value': value,
                                     'pos': pos if len(values) > 1 else None
                                     })
                else:
                    if isinstance(values, mutagen.apev2.APEBinaryValue):
                        continue
                    tags.append({'id': song.id,
                                 'name': key,
                                 'value': values,
                                 'pos': None
                                 })
            if tags:
                # print('2', tags)
                sql = ('INSERT INTO tags(song_id, name, value, pos) '
                       'VALUES (:id,:name,:value,:pos)')
                try:
                    c.execute(text(sql), tags)
                except ValueError:
                    c.rollback()
                    print(sql, tags)
                    raise

    @staticmethod
    def removeSong(song=None, byID=None):
        if config['immutableDatabase']:
            print("Error: Can't remove song %d from DB: "
                  "The database is configured as immutable" % song.id)
            return
        c = MusicDatabase.getCursor()
        if song:
            sql = text('DELETE FROM covers where path = :path')
            c.execute(sql.bindparams(path=song.path()))
        if song and not byID:
            byID = song.id
        params = {'id': byID}
        c.execute('DELETE FROM checksums where song_id=:id', params)
        c.execute('DELETE FROM fingerprints where song_id=:id', params)
        c.execute('DELETE FROM tags where song_id=:id', params)
        c.execute('DELETE FROM properties where song_id=:id', params)
        c.execute('DELETE FROM ratings where song_id=:id', params)
        c.execute('DELETE FROM songs where id=:id', params)
        MusicDatabase.commit()

    @staticmethod
    def getSongsCount():
        c = MusicDatabase.getCursor()

        result = c.execute('SELECT COUNT(*) FROM songs')
        count = result.fetchone()
        return count[0]

    @staticmethod
    def getSongsWithMusicBrainzTagsCount():
        c = MusicDatabase.getCursor()

        like = MusicDatabase.like
        result = c.execute(f"""SELECT COUNT(*) FROM tags where
   name {like} '%%musicbrainz_trackid'
or name {like} 'UFID:http://musicbrainz.org'
or name {like} '%%MusicBrainz Track Id'
or name {like} '%%MusicBrainz/Track Id'""")
        count = result.fetchone()
        return count[0]

    @staticmethod
    def addCover(pathToSong, pathToCover):
        if config['immutableDatabase']:
            print("Error: Can't add cover to song: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.getCursor()

        result = c.execute(text('SELECT path FROM covers where path=:path'),
                           {'path': os.path.normpath(pathToSong)})
        path = result.fetchone()
        if path:  # cover is already in db, we have to update it
            values = {'cover': pathToCover,
                      'path': os.path.normpath(pathToSong)}
            c.execute(text('UPDATE covers set cover=:cover WHERE path=:path'),
                      values)
        else:
            values = {'cover': pathToCover,
                      'path': os.path.normpath(pathToSong)}
            sql = 'INSERT INTO covers(path, cover) VALUES (:path,:cover)'
            c.execute(text(sql), values)

    @classmethod
    def prepareCache(cls):
        c = MusicDatabase.getCursor()
        if not cls.mtime_cache_by_path:
            result = c.execute('SELECT mtime, path, id FROM songs')
            for x in result.fetchall():
                mtime, path, id = x
                mtime = float(mtime)
                cls.mtime_cache_by_path[path] = mtime
                cls.mtime_cache_by_id[id] = (mtime, path)

    @classmethod
    def isSongInDatabase(cls, path=None, songID=None):
        path = os.path.normpath(path)

        cls.prepareCache()
        try:
            if songID:
                mtime, path = cls.mtime_cache_by_id[songID]
            else:
                mtime = cls.mtime_cache_by_path[path]
        except KeyError:
            return False

        if mtime == os.path.getmtime(path):
            return True
        return False

    @staticmethod
    def getSongTags(songID):
        c = MusicDatabase.getCursor()
        sql = text('SELECT name, value FROM tags where song_id = :id ORDER BY pos')
        result = c.execute(sql, {'id': songID})
        tags = {}
        for name, value in result.fetchall():
            if name not in tags:
                tags[name] = [value]
            else:
                tags[name] += [value]
        return tags

    @staticmethod
    def updateSongsTags(songList, readProperties=True):
        ids = tuple([song.id for song in songList])
        # print('aa', ids)
        if readProperties:
            properties = MusicDatabase.getSongsProperties(ids)
        c = MusicDatabase.getCursor()
        sql = ('SELECT song_id, name, value FROM tags '
               'where song_id in :ids order by song_id, pos')
        result = c.execute(text(sql), {'ids': ids})
        tags = {}
        currentSongID = None
        metadata = None
        for song_id, name, value in result.fetchall():
            if song_id != currentSongID:
                if currentSongID:
                    tags[currentSongID] = metadata
                metadata = type('metadata', (dict,), {})()
                currentSongID = song_id
            try:
                metadata[name] += [value]
            except KeyError:
                metadata[name] = [value]
        else:
            if metadata:
                tags[currentSongID] = metadata

        for song in songList:
            try:
                song.metadata = tags[song.id]
                if readProperties:
                    props = properties[song.id]
                    (song._format, song.metadata.info, song._audioSha256sum,
                     song._silenceAtStart, song._silenceAtEnd) = props
            except KeyError:
                pass

#        if getattr(self, 'id', None) is not None:
#            self.metadata = type('info', (dict,), {})()
#            self.metadata.update(MusicDatabase.getSongTags(self.id))
#            return

    @staticmethod
    def getSongsProperties(songIDs):
        if isinstance(songIDs, str):
            ids = [int(songID) for songID in songIDs.split(',')]
        elif isinstance(songIDs, int):
            ids = (songIDs,)
        elif isinstance(songIDs, (list, tuple)):
            ids = [int(songID) for songID in songIDs]
        ids = tuple(ids)
        c = MusicDatabase.getCursor()
        sql = ('SELECT song_id, format, duration, bitrate, '
               'bits_per_sample, sample_rate, channels, audio_sha256sum, '
               'silence_at_start, silence_at_end '
               'FROM properties where song_id in :ids')
        result = c.execute(text(sql), {'ids': ids})

        r = {}
        for row in result.fetchall():
            try:
                info = type('info', (), {})()
                songID = row['song_id']
                info.length = row['duration']
                info.bitrate = row['bitrate']
                info.bits_per_sample = row['bits_per_sample']
                info.sample_rate = row['sample_rate']
                info.channels = row['channels']

                r[songID] = (row['format'], info, row['audio_sha256sum'],
                             row['silence_at_start'], row['silence_at_end'])
            except KeyError:
                print('Error getting song properties for song ID %d' % songID)
                raise

        return r

    @staticmethod
    def getSongProperties(songID):
        return MusicDatabase.getSongsProperties([songID])[songID]

    @staticmethod
    def getSimilarSongsToSongID(songID, similarityThreshold=0.85):
        c = MusicDatabase.getCursor()
        sql = text('select song_id1, match_offset, similarity '
                   '  from similarities '
                   ' where song_id2=:id and similarity>=:similarity '
                   '   union '
                   'select song_id2, match_offset, similarity '
                   '  from similarities '
                   ' where song_id1=:id and similarity>=:similarity')
        result = c.execute(sql.bindparams(id=songID,
                                          similarity=similarityThreshold))
        similarSongs = [(x[0], x[1], x[2]) for x in result.fetchall()]

        return similarSongs

    @staticmethod
    def areSongsSimilar(songID1, songID2, similarityThreshold=0.85):
        if songID1 > songID2:
            songID1, songID2 = songID2, songID1
        c = MusicDatabase.getCursor()
        sql = '''select 1 from similarities where song_id1=:id1
                              and song_id2=:id2 and similarity>=:similarity'''
        result = c.execute(text(sql).bindparams(id1=songID1, id2=songID2,
                           similarity=similarityThreshold))
        return result.fetchone() is not None

    @staticmethod
    def songsSimilarity(songID1, songID2):
        if songID1 > songID2:
            songID1, songID2 = songID2, songID1
        c = MusicDatabase.getCursor()
        sql = '''select similarity from similarities where song_id1=:id1
                              and song_id2=:id2'''
        result = c.execute(text(sql).bindparams(id1=songID1, id2=songID2))
        x = result.fetchone()
        if not x:
            return 0
        return x[0]

    @staticmethod
    def commit():
        if config['immutableDatabase']:
            MusicDatabase.getConnection().rollback()
            return
        MusicDatabase.getConnection().commit()

    @staticmethod
    def addFileSha256sum(songid, sha256sum):
        if config['immutableDatabase']:
            print("Error: Can't add file SHA256: The database is configured "
                  "as immutable")
            return
        c = MusicDatabase.getCursor()
        sql = ('INSERT INTO checksums (song_id, sha256sum) '
               'VALUES (:id, :sha256sum)')
        c.execute(text(sql).bindparams(id=songid, sha256sum=sha256sum))

    @staticmethod
    def addAudioTrackSha256sum(songid, audioSha256sum):
        if config['immutableDatabase']:
            print("Error: Can't add file SHA256: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.getCursor()
        sql = ('UPDATE properties set audio_sha256sum=:audio_sha256sum '
               'where song_id=:id')
        c.execute(text(sql).bindparams(audio_sha256sum=audioSha256sum,
                                       id=songid))

    @staticmethod
    def addAudioSilences(songid, silence_at_start, silence_at_end):
        if config['immutableDatabase']:
            print("Error: Can't set song silences: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.getCursor()
        sql = ('UPDATE properties set silence_at_start=:silence_at_start,'
               'silence_at_end=:silence_at_end where song_id=:id')
        c.execute(text(sql).bindparams(silence_at_start=silence_at_start,
                  silence_at_end=silence_at_end, id=songid))

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
        c = MusicDatabase.getCursor()
        sql = ('UPDATE similarities set match_offset=:match_offset, '
               'similarity=:similarity where song_id1=:id1 and song_id2=:id2')
        result = c.execute(text(sql).bindparams(match_offset=offset,
                           similarity=similarity, id1=songid1, id2=songid2))
        if result.rowcount == 0:
            sql = ('INSERT INTO similarities '
                   '(song_id1, song_id2, match_offset, similarity) '
                   'VALUES (:id1,:id2,:match_offset,:similarity)')
            result = c.execute(text(sql).bindparams(match_offset=offset,
                               similarity=similarity,
                               id1=songid1, id2=songid2))

    @staticmethod
    def getSimilarSongs(condition=None):
        if not condition:
            condition = '> 0.85'
        else:
            condition = re.match(r'[0-9<>= .]*', condition).group()
        c = MusicDatabase.getCursor()
        sql = ('SELECT song_id1, song_id2, match_offset, similarity '
               'FROM similarities WHERE similarity %s' % condition)
        result = c.execute(sql)
        pairs = []
        for songid1, songid2, offset, similarity in result.fetchall():
            pairs.append((songid1, songid2, offset, similarity))
        return pairs

    @staticmethod
    def getGenres(ids=[], paths=[], root=None):
        like = MusicDatabase.like
        tables = 'tags'
        if root:
            condition = ('AND song_id IN '
                         '(select id from songs where root = :root)')
            variables = {'root': root}
        else:
            condition = ''
            variables = {}
        if ids:
            condition += ' AND song_id in :ids'
            variables['ids'] = tuple(ids)
        if paths:
            part = ''
            for idx, path in enumerate(paths):
                if part:
                    part += f' OR path {like} :path%d' % idx
                else:
                    part = f'path {like} :path%d' % idx
                variables['path%d' % idx] = ('%' + path + '%')
            condition += ' AND id = song_id AND (%s)' % part
            tables += ',songs'

        sql = '''select value, count(*)
                   from %s
                  where (lower(name) = 'genre' OR name='TCON')
                        %s
                  group by value
                  order by 2''' % (tables, condition)
        print(sql, variables)
        c = MusicDatabase.getCursor()
        result = c.execute(text(sql).bindparams(**variables))
        pairs = []
        for genre, count in result.fetchall():
            pairs.append((genre.split('\0'), count))
        return pairs

    @staticmethod
    def getUserID(username, create=True):
        sql = text('select id from users where name = :name')
        c = MusicDatabase.getCursor()
        params = {'name': username}
        result = c.execute(sql.bindparams(**params))
        userID = result.fetchone()
        if userID:
            return userID[0]

        if create:
            sql = 'INSERT INTO users(name) VALUES (:name)'
            c.execute(text(sql).bindparams(name=username))

            # sql = 'SELECT last_insert_rowid()'
            sql = "SELECT currval(pg_get_serial_sequence('users','id'))"
            result = c.execute(sql)
            userID = result.fetchone()[0]
            MusicDatabase.commit()
            return userID

        return None

    @staticmethod
    def lastSongID():
        sql = 'select max(id) from songs'
        c = MusicDatabase.getCursor()
        result = c.execute(sql)
        x = result.fetchone()
        if x:
            return x[0]
        return 0

    @staticmethod
    def lastSongIDWithCalculatedSimilarities():
        sql = 'select max(song_id2) from similarities'
        c = MusicDatabase.getCursor()
        result = c.execute(sql)
        x = result.fetchone()
        if x:
            return x[0]
        return 0

    @staticmethod
    def getRoots():
        sql = 'select distinct(root) from songs'
        c = MusicDatabase.getCursor()
        result = c.execute(sql)
        return [x[0] for x in result.fetchall()]
