# -*- coding: utf-8 -*-

from bard.config import config
from bard.normalizetags import normalizeTagValues
from bard.utils import DecodedAudioPropertiesTuple, DecodeMessageRecord
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import sqlite3
import os
import re
import threading
import mutagen


class DatabaseEnum:
    def __init__(self, enum_name, auto_insert=True, name_is_dict=False):
        self.enum_name = enum_name
        self.table_name = f'enum_{enum_name}_values'
        self.auto_insert = auto_insert
        self.name_is_dict = name_is_dict

    def add_value_dict(self, names):
        columns = ','.join(names.keys())
        values = ','.join(f':{k}' for k in names.keys())

        sql = f'INSERT INTO {self.table_name}({columns}) VALUES ({values})'
        c = MusicDatabase.getCursor()
        c.execute(text(sql).bindparams(**names))

        try:
            sql = (f"SELECT currval(pg_get_serial_sequence("
                   f"'{self.table_name}','id_value'))")
            result = c.execute(sql)
        except sqlalchemy.exc.OperationalError:
            # Try the sqlite way
            sql = 'SELECT last_insert_rowid()'
            result = c.execute(sql)
        return result.fetchone()[0]

    def add_value(self, name):
        sql = (f'INSERT INTO {self.table_name}(name) '
               'VALUES (:name)')
        c = MusicDatabase.getCursor()
        c.execute(text(sql).bindparams(name=name))

        try:
            sql = (f"SELECT currval(pg_get_serial_sequence("
                   f"'{self.table_name}','id_value'))")
            result = c.execute(sql)
        except sqlalchemy.exc.OperationalError:
            # Try the sqlite way
            sql = 'SELECT last_insert_rowid()'
            result = c.execute(sql)
        return result.fetchone()[0]

    def id_value_dict(self, names):
        where = ' AND '.join([f'{k}=:{k}' for k in names.keys()])
        sql = f'SELECT id_value FROM {self.table_name} WHERE {where}'
        c = MusicDatabase.getCursor()
        result = c.execute(text(sql).bindparams(**names))
        r = result.fetchone()
        if not r:
            if self.auto_insert:
                return self.add_value_dict(names)
            return None
        return r[0]

    def id_value(self, name):
        if self.name_is_dict:
            return self.id_value_dict(name)
        sql = f'SELECT id_value FROM {self.table_name} WHERE name=:name'
        c = MusicDatabase.getCursor()
        result = c.execute(text(sql).bindparams(name=name))
        r = result.fetchone()
        if not r:
            if self.auto_insert:
                return self.add_value(name)
            return None
        return r[0]

    def name(self, id_value):
        if self.name_is_dict:
            return self.name_dict(id_value)
        sql = f'SELECT name FROM {self.table_name} WHERE id_value=:id_value'
        c = MusicDatabase.getCursor()
        result = c.execute(text(sql).bindparams(id_value=id_value))
        r = result.fetchone()
        if not r:
            return None
        return r[0]

    def name_dict(self, id_value):
        sql = f'SELECT * FROM {self.table_name} WHERE id_value=:id_value'
        c = MusicDatabase.getCursor()
        result = c.execute(text(sql).bindparams(id_value=id_value))
        r = result.fetchone()
        if not r:
            return None
        print(r)
        print(r.keys())
        raise 'a'
        return r


SampleFormatEnum = DatabaseEnum('sample_format', auto_insert=False)
LibraryVersionsEnum = DatabaseEnum('library_versions', name_is_dict=True)
FormatEnum = DatabaseEnum('format')
CodecEnum = DatabaseEnum('codec')


def toString(v):
    if isinstance(v, list):
        return ', '.join(v)

    return v


def extractDecodeMessagesList(songID, messages):
    tags = []
    for idx, msg in enumerate(messages):
        tags.append({'id': songID,
                     'time_position': msg[0],
                     'level': msg[1],
                     'message': msg[2],
                     'pos': idx})
    return tags


def extractTagsList(song):
    tags = []
    for key, values in song.metadata.items():
        key, values = normalizeTagValues(values, song.metadata, key,
                                         removeBinaryData=True)

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
    return tags


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
        self.database = database

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
        if self.database == 'postgresql':
            serial_primary_key = 'SERIAL PRIMARY KEY'
        else:
            serial_primary_key = 'INTEGER PRIMARY KEY AUTOINCREMENT'
        c = MusicDatabase.getCursor()
        c.execute(f'''
CREATE TABLE songs (
                    id {serial_primary_key},
                    root TEXT,
                    path TEXT UNIQUE,
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
                    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   )''')
        c.execute('CREATE INDEX songs_path_idx ON songs (path)')
        c.execute('''
CREATE TABLE properties(
                    song_id INTEGER PRIMARY KEY,
                    format TEXT,
                    duration REAL,
                    bitrate INTEGER,
                    bits_per_sample INTEGER,
                    sample_rate INTEGER,
                    channels INTEGER,
                    audio_sha256sum TEXT,
                    silence_at_start REAL,
                    silence_at_end REAL,
                    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                 )''')
        c.execute(f'''
CREATE TABLE enum_sample_format_values(
                    id_value {serial_primary_key},
                    name TEXT,
                    bits_per_sample INTEGER,
                    is_planar BOOLEAN
                 )''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('u8', 8, FALSE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('s16', 16, FALSE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('s32', 32, FALSE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('flt', 32, FALSE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('dbl', 64, FALSE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('u8p', 8, TRUE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('s16p', 16, TRUE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('s32p', 32, TRUE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('fltp', 32, TRUE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('dblp', 64, TRUE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('s64', 64, FALSE)''')
        c.execute('INSERT INTO enum_sample_format_values '
                  '(name, bits_per_sample, is_planar) '
                  '''VALUES ('s64p', 64, TRUE)''')
        c.execute(f'''
CREATE TABLE enum_library_versions_values(
                    id_value {serial_primary_key},
                    bard_audiofile TEXT,
                    libavcodec TEXT,
                    libavformat TEXT,
                    libavutil TEXT,
                    libswresample TEXT
                 )''')
        c.execute(f'''
CREATE TABLE enum_format_values(
                    id_value {serial_primary_key},
                    name TEXT,
                 )''')
        c.execute(f'''
CREATE TABLE enum_codec_values(
                    id_value {serial_primary_key},
                    name TEXT,
                 )''')
        c.execute('''
CREATE TABLE decode_properties(
                    song_id INTEGER PRIMARY KEY,

                    codec INTEGER,
                    format INTEGER,
                    container_duration REAL,
                    decoded_duration REAL,

                    container_bitrate INTEGER,
                    stream_bitrate INTEGER,

                    stream_sample_format INTEGER,
                     stream_bits_per_raw_sample INTEGER,

                    decoded_sample_format INTEGER,
                    samples INTEGER,

                    library_versions INTEGER,

                    FOREIGN KEY(song_id)
                      REFERENCES songs(id) ON DELETE CASCADE,
                    FOREIGN KEY(codec)
                      REFERENCES enum_codec_values(id_value),
                    FOREIGN KEY(format)
                      REFERENCES enum_format_values(id_value),
                    FOREIGN KEY(stream_sample_format)
                      REFERENCES enum_sample_format_values(id_value),
                    FOREIGN KEY(decoded_sample_format)
                      REFERENCES enum_sample_format_values(id_value),
                    FOREIGN KEY(library_versions)
                      REFERENCES enum_library_versions_values(id_value)
                 )''')
        c.execute('''
CREATE TABLE decode_messages(
                    song_id INTEGER,
                    time_position REAL,
                    level INTEGER,
                    message TEXT,
                    pos INTEGER,
                    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                 )''')
        c.execute('CREATE INDEX ON decode_messages (song_id)')
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
                  last_check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                  )''')
        c.execute('''
CREATE TABLE fingerprints(
                  song_id INTEGER PRIMARY KEY,
                  fingerprint BYTEA NOT NULL,
                  insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        c.execute('CREATE INDEX similarities_song_id1_idx '
                  ' ON similarities (song_id1)')
        c.execute('CREATE INDEX similarities_song_id2_idx '
                  ' ON similarities (song_id2)')

        c.execute('''
 CREATE TABLE users (
                  id INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                  name TEXT,
                  password BYTEA
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
        c.execute(f'''
 CREATE TABLE songs_history (
                  id {serial_primary_key},
                  song_id INTEGER,
                  path TEXT,
                  mtime NUMERIC(20,8),
                  song_insert_time TIMESTAMP,
                  removed BOOLEAN DEFAULT FALSE,
                  sha256sum TEXT NOT NULL,
                  last_check_time TIMESTAMP,
                  duration REAL,
                  bitrate INTEGER,
                  audio_sha256sum TEXT NOT NULL,
                  description TEXT,
                  insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )''')
        c.execute('CREATE INDEX songs_history_song_id_idx '
                  ' ON songs_history (song_id)')
        c.execute('CREATE INDEX songs_history_path_idx '
                  ' ON songs_history (path)')

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

        values = {'root': song.root(),
                  'filename': song.filename(),
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
            if MusicDatabase.checkChangesForSongHistoryEntry(song):
                MusicDatabase.createSongHistoryEntry(song.id)

            values['id'] = song.id
            # print('Updating song in database')
            sql = ('UPDATE songs SET root=:root, filename=:filename, '
                   'mtime=:mtime, title=:title, '
                   'artist=:artist, album=:album, albumArtist=:albumartist, '
                   'track=:track, date=:date, genre=:genre, '
                   'discNumber=:discnumber, coverWidth=:coverwidth, '
                   'coverHeight=:coverheight, coverMD5=:covermd5, '
                   'completeness=:completeness, update_time=CURRENT_TIMESTAMP '
                   'WHERE id = :id')

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

            prop = song.decode_properties()
            values = {'codec': CodecEnum.id_value(prop.codec),
                      'format': FormatEnum.id_value(prop.format),
                      'container_duration': prop.container_duration,
                      'decoded_duration': prop.decoded_duration,
                      'container_bitrate': prop.container_bitrate,
                      'stream_bitrate': prop.stream_bitrate,
                      'stream_sample_format':
                      SampleFormatEnum.id_value(prop.stream_sample_format),
                      'stream_bits_per_raw_sample':
                      prop.stream_bits_per_raw_sample,
                      'decoded_sample_format':
                      SampleFormatEnum.id_value(prop.decoded_sample_format),
                      'samples': prop.samples,
                      'library_versions':
                      LibraryVersionsEnum.id_value(prop.library_versions),
                      'id': song.id}
            sql = ('UPDATE decode_properties SET codec=:codec, '
                   'format=:format, container_duration=:container_duration, '
                   'decoded_duration=:decoded_duration, '
                   'container_bitrate=:container_bitrate, '
                   'stream_bitrate=:stream_bitrate, '
                   'stream_sample_format=:stream_sample_format, '
                   'stream_bits_per_raw_sample=:stream_bits_per_raw_sample, '
                   'decoded_sample_format=:decoded_sample_format, '
                   'samples=:samples, '
                   'library_versions=:library_versions '
                   'WHERE song_id=:id')
            c.execute(text(sql).bindparams(**values))

            values = {'id': song.id}
            sql = 'DELETE from decode_messages where song_id = :id'
            c.execute(text(sql).bindparams(**values))

            tags = extractDecodeMessagesList(song.id, prop.messages)

            if tags:
                sql = ('INSERT INTO decode_messages(song_id, time_position, '
                       'level, message, pos) VALUES (:id,:time_position,'
                       ':level,:message,:pos)')
                try:
                    c.execute(text(sql), tags)
                except ValueError:
                    c.rollback()
                    print(sql, tags)
                    raise

            values = {'id': song.id}
            sql = 'DELETE from tags where song_id = :id'
            c.execute(text(sql).bindparams(**values))

            tags = extractTagsList(song)

            if tags:
                sql = ('INSERT INTO tags(song_id, name, value, pos) '
                       'VALUES (:id,:name,:value,:pos)')
                try:
                    c.execute(text(sql), tags)
                except ValueError:
                    c.rollback()
                    print(sql, tags)
                    raise
        else:
            # print('Adding song to database')
            values['path'] = song.path()
            # print(values)
            sql = ('INSERT INTO songs(root, path, filename, mtime, '
                   'title, artist, album, albumArtist, track, date, '
                   'genre, discNumber, coverWidth, coverHeight, '
                   'coverMD5, completeness) '
                   'VALUES (:root,:path,:filename,:mtime,:title,:artist,'
                   ':album,:albumartist,:track,:date,:genre,:discnumber,'
                   ':coverwidth,:coverheight,:covermd5,:completeness)')
            c.execute(text(sql).bindparams(**values))

            try:
                sql = "SELECT currval(pg_get_serial_sequence('songs','id'))"
                result = c.execute(sql)
            except sqlalchemy.exc.OperationalError:
                # Try the sqlite way
                sql = 'SELECT last_insert_rowid()'
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

            prop = song.decode_properties()
            values = {'codec': CodecEnum.id_value(prop.codec),
                      'format': FormatEnum.id_value(prop.format),
                      'container_duration': prop.container_duration,
                      'decoded_duration': prop.decoded_duration,
                      'container_bitrate': prop.container_bitrate,
                      'stream_bitrate': prop.stream_bitrate,
                      'stream_sample_format':
                      SampleFormatEnum.id_value(prop.stream_sample_format),
                      'stream_bits_per_raw_sample':
                      prop.stream_bits_per_raw_sample,
                      'decoded_sample_format':
                      SampleFormatEnum.id_value(prop.decoded_sample_format),
                      'samples': prop.samples,
                      'library_versions':
                      LibraryVersionsEnum.id_value(prop.library_versions),
                      'id': song.id}
            sql = ('INSERT INTO decode_properties(song_id, codec, '
                   'format, container_duration, decoded_duration, '
                   'container_bitrate, stream_bitrate, stream_sample_format, '
                   'stream_bits_per_raw_sample, decoded_sample_format, '
                   'samples, library_versions) VALUES (:id,:codec,'
                   ':format, :container_duration, :decoded_duration, '
                   ':container_bitrate, :stream_bitrate, '
                   ':stream_sample_format, :stream_bits_per_raw_sample, '
                   ':decoded_sample_format, :samples, :library_versions)')
            c.execute(text(sql).bindparams(**values))

            tags = extractDecodeMessagesList(song.id, prop.messages)
            if tags:
                sql = ('INSERT INTO decode_messages(song_id, time_position, '
                       'level, message, pos) VALUES (:id,:time_position,'
                       ':level,:message,:pos)')
                try:
                    c.execute(text(sql), tags)
                except ValueError:
                    c.rollback()
                    print(sql, tags)
                    raise

            tags = extractTagsList(song)
            if tags:
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
        if song and not byID:
            byID = song.id
        MusicDatabase.createSongHistoryEntry(byID, removed=True)

        c = MusicDatabase.getCursor()
        if song:
            sql = text('DELETE FROM covers where path = :path')
            c.execute(sql.bindparams(path=song.path()))
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
    def updateFingerprint(cls, songID, fingerprint):
        if config['immutableDatabase']:
            print("Error: Can't update song fingerprint: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.getCursor()

        values = {'fingerprint': fingerprint,
                  'id': songID}
        sql = ('UPDATE fingerprints SET fingerprint=:fingerprint '
               'WHERE song_id=:id')
        c.execute(text(sql).bindparams(**values))

    @classmethod
    def songIDsWithoutFingerprints(cls):
        c = MusicDatabase.getCursor()
        sql = 'SELECT song_id FROM fingerprints WHERE fingerprint IS NULL'
        result = c.execute(sql)
        return [x[0] for x in result.fetchall()]

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
        sql = text('SELECT name, value FROM tags WHERE song_id = :id '
                   'ORDER BY pos')
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
    def getDecodeProperties(songIDs):
        if isinstance(songIDs, str):
            ids = [int(songID) for songID in songIDs.split(',')]
        elif isinstance(songIDs, int):
            ids = (songIDs,)
        elif isinstance(songIDs, (list, tuple)):
            ids = [int(songID) for songID in songIDs]
        ids = tuple(ids)
        c = MusicDatabase.getCursor()

        sql = ('SELECT song_id, time_position, level, message '
               'FROM decode_messages where song_id in :ids '
               'ORDER BY song_id, pos')
        result = c.execute(text(sql), {'ids': ids})
        messages = {}
        for row in result.fetchall():
            dm = DecodeMessageRecord(time_position=row['time_position'],
                                     level=row['level'],
                                     message=row['message'])
            try:
                messages[row['song_id']].append(dm)
            except KeyError:
                messages[row['song_id']] = [dm]

        sql = ('SELECT song_id, codec, format, container_duration, '
               'decoded_duration, container_bitrate, stream_bitrate, '
               'stream_sample_format, stream_bits_per_raw_sample, '
               'decoded_sample_format, samples, library_versions '
               'FROM decode_properties where song_id in :ids')
        result = c.execute(text(sql), {'ids': ids})

        r = {}
        for row in result.fetchall():
            try:
                songID = row['song_id']
                sSmplFmt = SampleFormatEnum.name(row['stream_sample_format'])
                sBitsPerRawSample = row['stream_bits_per_raw_sample']
                dSmplFmt = SampleFormatEnum.name(row['decoded_sample_format'])
                libraryVer = LibraryVersionsEnum.name(row['library_versions'])
                prop = (DecodedAudioPropertiesTuple(
                        codec=CodecEnum.name(row['codec']),
                        format_name=FormatEnum.name(row['format']),
                        container_duration=row['container_duration'],
                        decoded_duration=row['decoded_duration'],
                        container_bitrate=row['container_bitrate'],
                        stream_bitrate=row['stream_bitrate'],
                        stream_sample_format=sSmplFmt,
                        stream_bits_per_raw_sample=sBitsPerRawSample,
                        decoded_sample_format=dSmplFmt,
                        samples=row['samples'],
                        library_versions=libraryVer,
                        messages=messages[songID]))

                r[songID] = prop
            except KeyError:
                print('Error getting decode properties for song ID %d' %
                      songID)
                raise

        return r

    @staticmethod
    def getSongDecodeProperties(songID):
        return MusicDatabase.getDecodeProperties([songID])[songID]

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
    def updateFileSha256sumLastCheckTime(songid):
        if config['immutableDatabase']:
            print("Error: Can't update checksum's last check time: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.getCursor()
        sql = text('UPDATE checksums set last_check_time=CURRENT_TIMESTAMP '
                   'WHERE song_id=:id')
        result = c.execute(sql.bindparams(id=songid))
        return result.rowcount == 1

    @staticmethod
    def addFileSha256sum(songid, sha256sum):
        if config['immutableDatabase']:
            print("Error: Can't add file SHA256: The database is configured "
                  "as immutable")
            return
        c = MusicDatabase.getCursor()
        sql = text('UPDATE checksums set sha256sum=:sha256sum, '
                   'last_check_time=CURRENT_TIMESTAMP WHERE song_id=:id')
        result = c.execute(sql.bindparams(id=songid, sha256sum=sha256sum))
        if result.rowcount == 0:
            sql = text('INSERT INTO checksums (song_id, sha256sum) '
                       'VALUES (:id, :sha256sum)')
            c.execute(sql.bindparams(id=songid, sha256sum=sha256sum))

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
    def addSongDecodeProperties(songid, properties):
        if config['immutableDatabase']:
            print("Error: Can't add decode properties: "
                  "The database is configured as immutable")
            return
        c = MusicDatabase.getCursor()

        values = {'codec': CodecEnum.id_value(properties.codec),
                  'format': FormatEnum.id_value(properties.format),
                  'container_duration': properties.container_duration,
                  'decoded_duration': properties.decoded_duration,
                  'container_bitrate': properties.container_bitrate,
                  'stream_bitrate': properties.stream_bitrate,
                  'stream_sample_format':
                  SampleFormatEnum.id_value(properties.stream_sample_format),
                  'stream_bits_per_raw_sample':
                  properties.stream_bits_per_raw_sample,
                  'decoded_sample_format':
                  SampleFormatEnum.id_value(properties.decoded_sample_format),
                  'samples': properties.samples,
                  'library_versions':
                  LibraryVersionsEnum.id_value(properties.library_versions),
                  'id': songid}
        sql = ('UPDATE decode_properties SET codec=:codec, '
               'format=:format, container_duration=:container_duration, '
               'decoded_duration=:decoded_duration, '
               'container_bitrate=:container_bitrate, '
               'stream_bitrate=:stream_bitrate, '
               'stream_sample_format=:stream_sample_format, '
               'stream_bits_per_raw_sample=:stream_bits_per_raw_sample, '
               'decoded_sample_format=:decoded_sample_format, '
               'samples=:samples, '
               'library_versions=:library_versions '
               'WHERE song_id=:id')
        result = c.execute(text(sql).bindparams(**values))
        if result.rowcount == 0:
            sql = ('INSERT INTO decode_properties(song_id, codec, '
                   'format, container_duration, decoded_duration, '
                   'container_bitrate, stream_bitrate, stream_sample_format, '
                   'stream_bits_per_raw_sample, decoded_sample_format, '
                   'samples, library_versions) VALUES (:id,:codec,'
                   ':format, :container_duration, :decoded_duration, '
                   ':container_bitrate, :stream_bitrate, '
                   ':stream_sample_format, :stream_bits_per_raw_sample, '
                   ':decoded_sample_format, :samples, :library_versions)')
            c.execute(text(sql).bindparams(**values))

        values = {'id': songid}
        sql = 'DELETE from decode_messages where song_id = :id'
        c.execute(text(sql).bindparams(**values))

        tags = extractDecodeMessagesList(songid, properties.messages)

        if tags:
            sql = ('INSERT INTO decode_messages(song_id, time_position, '
                   'level, message, pos) VALUES (:id,:time_position,'
                   ':level,:message,:pos)')
            try:
                c.execute(text(sql), tags)
            except ValueError:
                c.rollback()
                print(sql, tags)
                raise

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
    def removeSongsSimilarity(songid1, songid2):
        if config['immutableDatabase']:
            print("Error: Can't add song similarity: "
                  "The database is configured as immutable")
            return
        if songid1 > songid2:
            songid1, songid2 = songid2, songid1

        c = MusicDatabase.getCursor()
        sql = ('DELETE FROM similarities WHERE '
               'song_id1=:id1 AND song_id2=:id2')
        c.execute(text(sql).bindparams(id1=songid1, id2=songid2))

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

            try:
                sql = "SELECT currval(pg_get_serial_sequence('users','id'))"
                result = c.execute(sql)
            except sqlalchemy.exc.OperationalError:
                # Try the sqlite way
                sql = 'SELECT last_insert_rowid()'
                result = c.execute(sql)

            userID = result.fetchone()[0]
            MusicDatabase.commit()
            return userID

        return None

    @staticmethod
    def setUserPassword(userID, hashed_password):
        c = MusicDatabase.getCursor()
        sql = 'UPDATE users SET password=:password WHERE id = :id'
        result = c.execute(text(sql).bindparams(password=hashed_password,
                                                id=userID))
        if result.rowcount == 0:
            return False
        MusicDatabase.commit()

        return True

    @staticmethod
    def userPassword(username):
        c = MusicDatabase.getCursor()
        sql = 'SELECT password FROM users WHERE name = :name'
        result = c.execute(text(sql).bindparams(name=username))
        hashed_password = result.fetchone()
        if hashed_password:
            return bytes(hashed_password[0])

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

    @staticmethod
    def createSongHistoryEntry(songID, removed=False, description=None,
                               sha256sum=None, audio_sha256sum=None):
        values = {'id': songID,
                  'removed': removed,
                  'description': description}
        if sha256sum:
            sha256sum_ref = ':sha256sum'
            values['sha256sum'] = sha256sum
        else:
            sha256sum_ref = 'checksums.sha256sum'

        if audio_sha256sum:
            audio_sha256sum_ref = ':audio_sha256sum'
            values['audio_sha256sum'] = audio_sha256sum
        else:
            audio_sha256sum_ref = 'properties.audio_sha256sum'
        sql = ('INSERT INTO songs_history (song_id, path, mtime, '
               'song_insert_time, removed, sha256sum, '
               'last_check_time, duration, '
               'bitrate, audio_sha256sum, description) '
               '(SELECT songs.id, songs.path, songs.mtime, '
               f'songs.insert_time, :removed, {sha256sum_ref}, '
               'checksums.last_check_time, properties.duration, '
               f'properties.bitrate, {audio_sha256sum_ref}, :description '
               'FROM songs, checksums, properties '
               'WHERE songs.id = :id AND '
               'songs.id=checksums.song_id AND songs.id=properties.song_id)')
        c = MusicDatabase.getCursor()
        result = c.execute(text(sql).bindparams(**values))
        return result.rowcount == 1

    @staticmethod
    def checkChangesForSongHistoryEntry(song):
        sql = ('SELECT songs.id, songs.path, songs.mtime, '
               'checksums.sha256sum, '
               'properties.duration, '
               'properties.bitrate, properties.audio_sha256sum '
               'FROM songs, checksums, properties '
               'WHERE songs.id = :id AND '
               'songs.id=checksums.song_id AND songs.id=properties.song_id')
        c = MusicDatabase.getCursor()
        result = c.execute(text(sql).bindparams(id=song.id))
        x = result.fetchone()
        return (x.path != song.path() or
                float(x.mtime) != song.mtime() or
                x.sha256sum != song.fileSha256sum() or
                x.duration != song.duration() or
                x.bitrate != song.bitrate() or
                x.audio_sha256sum != song.audioSha256sum())
