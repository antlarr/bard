# -*- coding: utf-8 -*-

from bard.config import config
from bard.normalizetags import normalizeTagValues
from bard.utils import DecodedAudioPropertiesTuple, DecodeMessageRecord
from bard.album import albumPath
from bard.db import metadata
from bard.db.core import AlbumProperties, AlbumSongs, AlbumRelease, SongsMB, \
    Properties, AlbumsRatings, SongsRatings, AvgSongsRatings, Tags, Songs, \
    DecodeMessages, DecodeProperties, Users, Albums
from bard.db.musicbrainz import Release
import sqlalchemy
from sqlalchemy import create_engine, text, select, and_, or_, exists, func
from sqlalchemy.schema import CreateSchema
from sqlalchemy.orm import Session
from sqlalchemy.event import listen
from alembic.runtime import migration
from alembic.script import ScriptDirectory
from alembic.config import Config
from alembic import command
from functools import lru_cache, partial
import os
import re
import threading
import mutagen

try:
    import importlib.resources as importlib_resources
except ImportError:
    # In PY<3.7 fall-back to backported `importlib_resources`.
    import importlib_resources


def check_current_head(alembic_cfg, connectable):
    # type: (Config, sqlalchemy.engine.Engine) -> bool
    directory = ScriptDirectory.from_config(alembic_cfg)
    with connectable.begin() as connection:
        context = migration.MigrationContext.configure(connection)
        return set(context.get_current_heads()) == set(directory.get_heads())


def attach_sqlite_databases(dbapi_con, connection_record,
                            mb_dbpath, analysis_dbpath):
    cmd = f'ATTACH DATABASE \'{mb_dbpath}\' AS \'musicbrainz\''
    dbapi_con.execute(cmd)
    cmd = f'ATTACH DATABASE \'{analysis_dbpath}\' AS \'analysis\''
    dbapi_con.execute(cmd)


class DatabaseEnum:
    def __init__(self, enum_name, auto_insert=True, name_is_dict=False,
                 schema=None):
        """Create a DatabaseEnum object."""
        self.enum_name = enum_name
        self.schema = schema
        if schema:
            self.table_name = f'{schema}.enum_{enum_name}_values'
        else:
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

    def import_value(self, _id, name):
        c = MusicDatabase.getCursor()
        sql = (f'UPDATE {self.table_name} SET name=:name '
               'WHERE id_value=:id')
        result = c.execute(text(sql).bindparams(id=_id, name=name))
        if result.rowcount == 0:
            sql = (f'INSERT INTO {self.table_name}(id_value, name) '
                   'VALUES (:id, :name)')
            c.execute(text(sql).bindparams(id=_id, name=name))

    def add_value(self, name):
        sql = (f'INSERT INTO {self.table_name}(name) '
               'VALUES (:name)')
        c = MusicDatabase.getConnection()
        tr = c.begin_nested()
        c.execute(text(sql).bindparams(name=name))
        tr.commit()

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

    @lru_cache(maxsize=64)
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
    try:
        songID = song.id
    except AttributeError:
        songID = None
    for key, values in song.metadata.items():
        key, values = normalizeTagValues(values, song.metadata, key,
                                         removeBinaryData=True)

        if isinstance(values, list):
            for pos, value in enumerate(values):
                tags.append({'id': songID,
                             'name': key,
                             'value': value,
                             'pos': pos if len(values) > 1 else None
                             })
        else:
            if isinstance(values, mutagen.apev2.APEBinaryValue):
                continue
            tags.append({'id': songID,
                         'name': key,
                         'value': values,
                         'pos': None
                         })
    return tags


def extractCueSheetTracks(song):
    tracks = []
    for track in song.cuesheet:
        tracks.append({'id': song.id,
                       'idx': track.idx,
                       'sample_position': track.sample_position,
                       'time_position': track.time_position,
                       'title': track.title})
    return tracks


class MusicDatabase:
    conn = {}
    mtime_cache_by_path = {}
    mtime_cache_by_id = {}
    uri = None
    like = 'like'

    def __init__(self):
        """Create a MusicDatabase object."""
        try:
            database = config['database']
        except KeyError:
            database = 'sqlite'
        self.database = database
        ro = config['immutable_database']

        if database == 'sqlite':
            _dbpath = config['database_path']
            databasepath = os.path.expanduser(os.path.expandvars(_dbpath))
            if not os.path.isdir(os.path.dirname(databasepath)):
                os.makedirs(os.path.dirname(databasepath))

            root, ext = os.path.splitext(databasepath)
            MusicDatabase.dbpath = databasepath + '' if ext else '.db'
            mb_dbpath = f'file:{root}-mb{ext if ext else ".db"}'
            analysis_dbpath = (f'file:{root}-analysis'
                               f'{ext if ext else ".db"}')

            MusicDatabase.uri = f'sqlite:///file:{databasepath}?uri=true'
            if ro:
                MusicDatabase.uri += '&mode=ro'
                mb_dbpath += '?mode=ro'
                analysis_dbpath += '?mode=ro'
        else:
            name = config['database_name']
            user = config['database_user']
            password = config['database_password']
            MusicDatabase.uri = f'{database}://{user}:{password}@/{name}'
            MusicDatabase.like = 'ilike'

        MusicDatabase.engine = create_engine(MusicDatabase.uri)
        metadata.bind = MusicDatabase.engine
        if database == 'sqlite':
            # root, ext = os.path.splitext(MusicDatabase.dbpath)
            # mb_dbpath = f'{root}-mb{ext}'
            # analysis_dbpath = f'{root}-analysis{ext}'
            listen(MusicDatabase.engine, "connect", partial(
                   attach_sqlite_databases, mb_dbpath=mb_dbpath,
                   analysis_dbpath=analysis_dbpath))

        alembic_cfg = Config()
        alembic_cfg.set_main_option('sqlalchemy.url', MusicDatabase.uri)

        with importlib_resources.path('bard', 'alembic') as path:
            alembic_path = str(path)
        alembic_cfg.set_main_option('script_location', alembic_path)

        if not MusicDatabase.engine.has_table('cuesheets'):
            print('Tables missing. Creating database schema and tables.')
            self.createDatabase(alembic_cfg)

        self.migrate_database_schema(alembic_cfg)

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

    @staticmethod
    def closeConnections():
        for conn in MusicDatabase.conn.values():
            conn.close()
        MusicDatabase.conn = {}
        MusicDatabase.engine.dispose()

    @staticmethod
    def table(tablename):
        return metadata.tables[tablename]

    @staticmethod
    def view(viewname):
        return metadata.tables[viewname]

    def migrate_database_schema(self, alembic_cfg):
        if check_current_head(alembic_cfg, MusicDatabase.engine):
            return

        print('Database schema needs to be updated')
        with MusicDatabase.engine.begin() as connection:
            alembic_cfg.attributes['connection'] = connection
            command.upgrade(alembic_cfg, "head")
            alembic_cfg.attributes['connection'] = None

    def createDatabase(self, alembic_cfg):
        if config[immutable_database']:
            print("Error: Can't create database: "
                  "The database is configured as immutable")
            return
        print('Creating database...')
        if self.database != 'sqlite':
            MusicDatabase.engine.execute(CreateSchema('musicbrainz'))
            MusicDatabase.engine.execute(CreateSchema('analysis'))

        metadata.create_all(MusicDatabase.engine)

        command.stamp(alembic_cfg, "head")
        print('Database created')

    @staticmethod
    def addSong(song):  # noqa
        if config['immutable_database']:
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
                   'discnumber=:discnumber, coverwidth=:coverwidth, '
                   'coverheight=:coverheight, covermd5=:covermd5, '
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

            sql = 'DELETE from cuesheets where song_id = :id'
            c.execute(text(sql).bindparams(**values))

            cuesheettracks = extractCueSheetTracks(song)

            if cuesheettracks:
                sql = ('INSERT INTO cuesheets(song_id, idx, sample_position, '
                       'time_position, title) '
                       'VALUES (:id,:idx,:sample_position,:time_position, '
                       '        :title)')
                try:
                    c.execute(text(sql), cuesheettracks)
                except ValueError:
                    c.rollback()
                    print(sql, cuesheettracks)
                    raise
        else:
            # print('Adding song to database')
            values['path'] = song.path()
            # print(values)
            ins = Songs.insert().values(**values)
            result = c.execute(ins)
            song.id = result.inserted_primary_key[0]

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
            albumID = MusicDatabase.getAlbumID(albumPath(song.path()),
                                               connection=c)
            MusicDatabase.setSongInAlbum(song.id, albumID, connection=c)

            cuesheettracks = extractCueSheetTracks(song)

            if cuesheettracks:
                sql = ('INSERT INTO cuesheets(song_id, idx, sample_position, '
                       'time_position, title) '
                       'VALUES (:id,:idx,:sample_position,:time_position,'
                       '        :title)')
                try:
                    c.execute(text(sql), cuesheettracks)
                except ValueError:
                    c.rollback()
                    print(sql, cuesheettracks)
                    raise

            sql = text('select id from users')
            result = c.execute(sql)
            user_ids = [x[0] for x in result.fetchall()]

            values = {'song_id': song.id, 'rating': None}
            sql = text('INSERT INTO songs_ratings(song_id, user_id, rating) '
                       'VALUES (:song_id,:user_id, :rating)')
            for user_id in user_ids:
                values['user_id'] = user_id
                c.execute(sql.bindparams(**values))

    @staticmethod
    def removeSong(song=None, byID=None):
        if config['immutable_database']:
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
        c.execute('DELETE FROM songs_ratings where song_id=:id', params)
        c.execute('DELETE FROM album_songs where song_id=:id', params)
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
        if config['immutable_database']:
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
        if config['immutable_database']:
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

    @classmethod
    def songExistsInDatabase(cls, path=None, songID=None):
        c = MusicDatabase.getCursor()
        if path:
            sql = text('SELECT id FROM songs WHERE path = :arg ')
            arg = path
        else:
            sql = text('SELECT id FROM songs WHERE id = :arg ')
            arg = songID
        result = c.execute(sql, {'arg': arg})

        return bool(result.rowcount)

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
        if readProperties:
            properties = MusicDatabase.getSongsProperties(ids)
        c = MusicDatabase.getCursor()
        sel = (select([Tags.c.song_id, Tags.c.name, Tags.c.value])
               .where(Tags.c.song_id.in_(ids))
               .order_by(Tags.c.song_id, Tags.c.pos))
        result = c.execute(sel)
        tags = {}
        currentSongID = None
        song_metadata = None
        for song_id, name, value in result.fetchall():
            if song_id != currentSongID:
                if currentSongID:
                    tags[currentSongID] = song_metadata
                song_metadata = type('metadata', (dict,), {})()
                currentSongID = song_id
            try:
                song_metadata[name] += [value]
            except KeyError:
                song_metadata[name] = [value]
        else:
            if song_metadata:
                tags[currentSongID] = song_metadata

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
        sel = (select([Properties.c.song_id, Properties.c.format,
                       Properties.c.duration, Properties.c.bitrate,
                       Properties.c.bits_per_sample, Properties.c.sample_rate,
                       Properties.c.channels, Properties.c.audio_sha256sum,
                       Properties.c.silence_at_start,
                       Properties.c.silence_at_end])
               .where(Properties.c.song_id.in_(ids)))
        result = c.execute(sel)

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

        sel = (select([DecodeMessages.c.song_id,
                       DecodeMessages.c.time_position,
                       DecodeMessages.c.level,
                       DecodeMessages.c.message])
               .where(DecodeMessages.c.song_id.in_(ids))
               .order_by(DecodeMessages.c.song_id, DecodeMessages.c.pos))
        result = c.execute(sel)
        messages = {}
        for row in result.fetchall():
            dm = DecodeMessageRecord(time_position=row['time_position'],
                                     level=row['level'],
                                     message=row['message'])
            try:
                messages[row['song_id']].append(dm)
            except KeyError:
                messages[row['song_id']] = [dm]

        sel = (select([DecodeProperties.c.song_id,
                       DecodeProperties.c.codec,
                       DecodeProperties.c.format,
                       DecodeProperties.c.container_duration,
                       DecodeProperties.c.decoded_duration,
                       DecodeProperties.c.container_bitrate,
                       DecodeProperties.c.stream_bitrate,
                       DecodeProperties.c.stream_sample_format,
                       DecodeProperties.c.stream_bits_per_raw_sample,
                       DecodeProperties.c.decoded_sample_format,
                       DecodeProperties.c.samples,
                       DecodeProperties.c.library_versions])
               .where(DecodeProperties.c.song_id.in_(ids)))
        result = c.execute(sel)

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
        if config['immutable_database']:
            MusicDatabase.getConnection().rollback()
            return
        MusicDatabase.getConnection().commit()

    @staticmethod
    def updateFileSha256sumLastCheckTime(songid):
        if config['immutable_database']:
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
        if config['immutable_database']:
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
        if config['immutable_database']:
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
        if config['immutable_database']:
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
    def songsByAudioTrackSha256sum(audioSha256sum):
        c = MusicDatabase.getCursor()
        sql = ('SELECT song_id FROM properties '
               'WHERE audio_sha256sum=:audio_sha256sum')
        result = c.execute(text(sql).bindparams(
                           audio_sha256sum=audioSha256sum))
        return [x[0] for x in result.fetchall()]

    @staticmethod
    def addAudioSilences(songid, silence_at_start, silence_at_end):
        if config['immutable_database']:
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
        if config['immutable_database']:
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
        if config['immutable_database']:
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
        conditions = []
        if root:
            conditions.append(Tags.c.song_id.in_(
                              select(Songs.c.id).where(Songs.c.root == root)))
        if ids:
            conditions.append(Tags.c.song_id.in_(ids))
        if paths:
            subcond = [Songs.c.path.ilike(f'%{path}%') for path in paths]
            conditions.append(or_(*subcond))
            conditions.append(Tags.c.song_id == Songs.c.id)

        sel = (select([Tags.c.value, func.count().label('c')])
               .where(and_(or_(func.lower(Tags.c.name) == 'genre',
                               Tags.c.name == 'TCON'),
                           *conditions))
               .group_by(Tags.c.value)
               .order_by('c'))
        c = MusicDatabase.getCursor()
        result = c.execute(sel)
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
            ins = Users.insert().values(name=username)
            result = c.execute(ins)
            userID = result.inserted_primary_key[0]

            MusicDatabase.add_null_ratings(userID, 0)
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
        if hashed_password and hashed_password[0]:
            return bytes(hashed_password[0])

        return None

    @staticmethod
    def setUserActive(userID, active):
        c = MusicDatabase.getCursor()
        sql = 'UPDATE users SET active=:active WHERE id = :id'
        result = c.execute(text(sql).bindparams(active=active,
                                                id=userID))
        if result.rowcount == 0:
            return False
        MusicDatabase.commit()

        return True

    @staticmethod
    def lastSongID():
        sql = 'select max(id) from songs'
        c = MusicDatabase.getCursor()
        result = c.execute(sql)
        x = result.fetchone()
        if x != (None,):
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
        sql = 'select root, count(*) from songs group by root order by root'
        c = MusicDatabase.getCursor()
        result = c.execute(sql)
        return [(x[0], x[1]) for x in result.fetchall()]

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
    def moveSong(songID, newPath, newRoot):
        MusicDatabase.createSongHistoryEntry(songID)
        sql = 'update songs set path=:newPath, root=:newRoot where id=:id'
        c = MusicDatabase.getCursor()
        try:
            result = c.execute(text(sql).bindparams(id=songID,
                               newPath=newPath, newRoot=newRoot))
        except sqlalchemy.exc.IntegrityError as e:
            import psycopg2.errors
            if (isinstance(e.orig, psycopg2.errors.UniqueViolation) or
                    MusicDatabase.database != 'postgresql'):
                print('ERROR: duplicate path')
            print(e)
            raise

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

    @staticmethod
    def execute(executable):
        return MusicDatabase.engine.execute(executable)

    @staticmethod
    def insert_or_update(table, recorddict, wherestatement=None,
                         *, connection=None):
        if type(table) == str:
            table = MusicDatabase.table(table)

        if wherestatement is None:
            wherestatement = (table.c.id == recorddict['id'])

        dbRecord = table.select(wherestatement)
        if not connection:
            connection = MusicDatabase.getCursor()
        dbRecord = connection.execute(dbRecord).fetchone()
        if dbRecord:
            if any(dbRecord[k] != recorddict[k]
                   for k in [c.name for c in table.columns]
                   if k in recorddict):
                # print(f'update {table.name} db data for {recorddict}')
                u = table.update() \
                         .where(wherestatement) \
                         .values(**recorddict)
                connection.execute(u)
#            else:
#                print(f'no changes in {table.name} db data for {recorddict}')
        else:
            # print(f'insert {table.name} db data for {recorddict}')
            i = table.insert().values(**recorddict)
            connection.execute(i)

    @staticmethod
    def songsWithReleaseID(onlyWithoutAlbums=True):
        c = MusicDatabase.getCursor()
        if onlyWithoutAlbums:
            extra = ('   AND NOT EXISTS (SELECT song_id '
                     '                     FROM album_songs '
                     '                    WHERE song_id = songs.id)')
        else:
            extra = ''
        sql = text('SELECT id, path '
                   '  FROM songs, songs_mb '
                   ' WHERE id = songs_mb.song_id '
                   '   AND releaseid IS NOT NULL '
                   f'   {extra}'
                   'ORDER BY id')
        result = c.execute(sql)
        return [(x[0], x[1]) for x in result.fetchall()]

    @staticmethod
    def getRecordingMBID(song_id):
        mb = MusicDatabase.table('songs_mb')
        try:
            return (select([mb.c.recordingid])
                    .where(mb.c.song_id == song_id)
                    .execute().fetchone()[0])
        except (ValueError, KeyError):
            return None

    @staticmethod
    def getAlbumID(albumPath, *, connection=None):
        if not connection:
            connection = MusicDatabase.getCursor()
        sql = text('SELECT id FROM albums where path = :path')

        result = connection.execute(sql, {'path': albumPath}).fetchone()
        if result:
            return result[0]
        else:
            ins = Albums.insert().values(path=albumPath)
            result = connection.execute(ins)
            albumID = result.inserted_primary_key[0]
            return albumID

    @staticmethod
    def setSongInAlbum(songID, albumID, *, connection=None):
        record = {'song_id': songID, 'album_id': albumID}
        album_songs = MusicDatabase.table('album_songs')
        MusicDatabase.insert_or_update(album_songs, record,
                                       album_songs.c.song_id == songID,
                                       connection=connection)

    @staticmethod
    def removeOrphanAlbums():
        c = MusicDatabase.getCursor()
        sql = text('DELETE FROM albums '
                   ' WHERE NOT EXISTS (SELECT album_id '
                   '                     FROM album_songs '
                   '                    WHERE album_id = id)')
        result = c.execute(sql)
        MusicDatabase.commit()

        if result.rowcount:
            print(f'{result.rowcount} orphan albums removed')

    @staticmethod
    def getAlbumProperties(albumID):
        c = MusicDatabase.getCursor()
        sql = text('select * from album_properties '
                   ' where album_id = :albumID')
        r = c.execute(sql, {'albumID': albumID})
        return r.fetchall()

    @staticmethod
    def getAlbumCoversCount(albumID):
        c = MusicDatabase.getCursor()
        sql = text('select count(distinct covermd5) '
                   '  from songs, album_songs '
                   ' where id = song_id '
                   '   and album_id = :albumID')
        r = c.execute(sql, {'albumID': albumID})
        return r.fetchone()[0]

    @staticmethod
    def getAlbumPath(albumID, mediumNumber=None, any_medium=False):
        """Return the path of an album."""
        """mediumNumber can be a medium number or None. If None, then"""
        """any existing medium path is returned if any is True, or"""
        """the root album path is returned if any is False"""
        c = MusicDatabase.getCursor()
        if not mediumNumber and not any_medium:
            sql = text('select path from albums '
                       ' where id = :albumID')
            r = c.execute(sql, {'albumID': albumID}).fetchone()
            if r:
                return r[0]
        if not mediumNumber:
            sql = text('select path from songs, album_songs '
                       ' where id = song_id '
                       '   and album_id = :albumID '
                       '   order by discnumber '
                       ' LIMIT 1')
            r = c.execute(sql, {'albumID': albumID}).fetchone()
            return os.path.dirname(r[0]) if r else None
        sql = text('select path from songs, album_songs '
                   ' where id = song_id '
                   '   and album_id = :albumID '
                   '   and discnumber = :mediumNumber '
                   ' LIMIT 1')
        r = c.execute(sql, {'albumID': albumID,
                            'mediumNumber': mediumNumber}).fetchone()
        if not r:
            return None
        return os.path.dirname(r[0])

    @staticmethod
    def getPlaylistsForUser(userID, playlistID=None):
        c = MusicDatabase.getCursor()

        if playlistID:
            where = 'AND id=:playlist_id'
            vars = {'playlist_id': playlistID}
        else:
            where = ''
            vars = {}

        sql = ('SELECT id, name, playlist_type FROM playlists '
               f'WHERE owner_id = :owner_id {where} ORDER BY id')

        result = c.execute(text(sql).bindparams(owner_id=userID, **vars))

        return result.fetchall()

    @staticmethod
    def get_next_playlist_song(userID, playlistID, index):
        c = MusicDatabase.getCursor()
        sql = text('SELECT song_id, recording_mbid, pos '
                   '  FROM playlist_songs, playlists '
                   ' WHERE playlist_id = :playlistID '
                   '   AND id = playlist_id '
                   '   AND owner_id = :owner_id '
                   ' ORDER BY pos '
                   '   LIMIT 1 OFFSET :index ')
        result = c.execute(sql.bindparams(owner_id=userID,
                                          playlistID=playlistID,
                                          index=index + 1))
        return result.fetchone()

    @staticmethod
    def get_next_album_song(albumID, mediumNumber, track_position):
        c = MusicDatabase.getCursor()
        sql = text('SELECT mb.song_id, mb.recordingid, '
                   '       m.position medium_number, t.position track_position'
                   '  FROM musicbrainz.track t, musicbrainz.medium m, '
                   '       album_release ar, album_songs asongs, songs_mb mb '
                   ' WHERE m.id = t.medium_id '
                   '   AND m.release_id = ar.release_id '
                   '   AND ar.album_id = asongs.album_id '
                   '   AND asongs.album_id = :albumID '
                   '   AND mb.song_id = asongs.song_id '
                   '   AND mb.releasetrackid = t.mbid '
                   '   AND ((m.position = :mediumNumber '
                   '         AND t.position > :track_position) '
                   '        OR m.position > :mediumNumber) '
                   ' ORDER BY m.position, t.position'
                   '  LIMIT 1')

        result = c.execute(sql.bindparams(albumID=albumID,
                                          mediumNumber=mediumNumber,
                                          track_position=track_position))
        return result.fetchone()

    @staticmethod
    def refresh_album_tables():
        MusicDatabase.refresh_album_properties()
        MusicDatabase.refresh_album_release()

    @staticmethod
    def refresh_album_properties():
        delete = AlbumProperties.delete()
        columns = ['album_id', 'format',
                   'min_bitrate', 'max_bitrate',
                   'min_bits_per_sample', 'max_bits_per_sample',
                   'min_sample_rate', 'max_sample_rate',
                   'min_channels', 'max_channels']
        album_properties_s = (select(
            [AlbumSongs.c.album_id,
             Properties.c.format,
             func.min(Properties.c.bitrate).label('min_bitrate'),
             func.max(Properties.c.bitrate).label('max_bitrate'),
             func.min(Properties.c.bits_per_sample).label(
                 'min_bits_per_sample'),
             func.max(Properties.c.bits_per_sample).label(
                 'max_bits_per_sample'),
             func.min(Properties.c.sample_rate).label('min_sample_rate'),
             func.max(Properties.c.sample_rate).label('max_sample_rate'),
             func.min(Properties.c.channels).label('min_channels'),
             func.max(Properties.c.channels).label('max_channels')])
            .where(AlbumSongs.c.song_id == Properties.c.song_id)
            .group_by(AlbumSongs.c.album_id, Properties.c.format))
        insert = AlbumProperties.insert().from_select(columns,
                                                      album_properties_s)
        c = MusicDatabase.getConnection()
        c.execute(delete)
        c.execute(insert)
        c.commit()

    @staticmethod
    def refresh_album_release():
        delete = AlbumRelease.delete()
        album_release_s = (select(
            [AlbumSongs.c.album_id,
             Release.c.id.label('release_id')])
            .select_from(SongsMB)
            .where(and_(
                ~exists(select([AlbumRelease.c.album_id]).where(
                    AlbumRelease.c.album_id == AlbumSongs.c.album_id)),
                SongsMB.c.releaseid == Release.c.mbid,
                SongsMB.c.song_id == AlbumSongs.c.song_id))
            .group_by(AlbumSongs.c.album_id, Release.c.id))
        insert = AlbumRelease.insert().from_select(['album_id', 'release_id'],
                                                   album_release_s)
        c = MusicDatabase.getConnection()
        c.execute(delete)
        c.execute(insert)
        c.commit()

    @staticmethod
    def get_songs_ratings(song_ids, user_id):
        if not song_ids:
            return {}
        c = MusicDatabase.getCursor()
        sel = (select([SongsRatings.c.song_id, SongsRatings.c.rating])
               .where(and_(SongsRatings.c.user_id == user_id,
                           SongsRatings.c.song_id.in_(song_ids),
                           SongsRatings.c.rating.isnot(None))))
        r = c.execute(sel)

        result = {row['song_id']: (row['rating'], 'user')
                  for row in r.fetchall()}

        rem_song_ids = tuple(x for x in song_ids if x not in result.keys())

        if rem_song_ids:
            sel = (select([AvgSongsRatings.c.song_id,
                           AvgSongsRatings.c.avg_rating])
                   .where(and_(AvgSongsRatings.c.user_id == user_id,
                               AvgSongsRatings.c.song_id.in_(rem_song_ids),
                               AvgSongsRatings.c.avg_rating.isnot(None))))
            r = c.execute(sel)

            result.update({row['song_id']: (float(row['avg_rating']), 'avg')
                           for row in r.fetchall()})

            rem_song_ids = tuple(x for x in rem_song_ids
                                 if x not in result.keys())

            result.update({song_id: (5, None) for song_id in rem_song_ids})

        return result

    @staticmethod
    def get_albums_ratings(album_ids, user_id):
        if not album_ids:
            return {}
        c = MusicDatabase.getCursor()
        sel = (select([AlbumsRatings.c.album_id, AlbumsRatings.c.rating])
               .where(and_(AlbumsRatings.c.user_id == user_id,
                           AlbumsRatings.c.album_id.in_(album_ids))))

        r = c.execute(sel)

        result = {row['album_id']: (row['rating'], 'user')
                  for row in r.fetchall()}

        rem_album_ids = tuple(x for x in album_ids if x not in result.keys())
        if not rem_album_ids:
            return result

        sel = (select([AlbumsRatings.c.album_id,
                       func.avg(AlbumsRatings.c.rating).label('avgrating')])
               .where(and_(AlbumsRatings.c.user_id != user_id,
                           AlbumsRatings.c.album_id.in_(rem_album_ids)))
               .group_by(AlbumsRatings.c.album_id))
        r = c.execute(sel)

        result.update({row['album_id']: (float(row['avgrating']), 'avg')
                       for row in r.fetchall()})

        rem_album_ids = tuple(x for x in rem_album_ids
                              if x not in result.keys())

        result.update({album_id: (5, None) for album_id in rem_album_ids})

        return result

    @staticmethod
    def set_album_rating(album_id, rating, user_id):
        c = MusicDatabase.getCursor()
        sql = ('UPDATE albums_ratings set rating = :rating '
               'WHERE user_id = :user_id AND album_id = :album_id')
        sql = text(sql).bindparams(rating=rating, user_id=user_id,
                                   album_id=album_id)
        result = c.execute(sql)
        if result.rowcount == 0:
            sql = ('INSERT INTO albums_ratings '
                   '(user_id, album_id, rating) '
                   'VALUES (:user_id,:album_id,:rating)')
            sql = text(sql).bindparams(rating=rating, user_id=user_id,
                                       album_id=album_id)
            c.execute(sql)
        MusicDatabase.commit()

    @staticmethod
    def set_artist_rating(artist_id, rating, user_id):
        c = MusicDatabase.getCursor()
        sql = ('UPDATE artists_ratings set rating = :rating '
               'WHERE user_id = :user_id AND artist_id = :artist_id')
        sql = text(sql).bindparams(rating=rating, user_id=user_id,
                                   artist_id=artist_id)
        result = c.execute(sql)
        if result.rowcount == 0:
            sql = ('INSERT INTO artists_ratings '
                   '(user_id, artist_id, rating) '
                   'VALUES (:user_id,:artist_id,:rating)')
            sql = text(sql).bindparams(rating=rating, user_id=user_id,
                                       artist_id=artist_id)
            c.execute(sql)
        MusicDatabase.commit()

    @staticmethod
    def add_null_ratings(user_id, from_song_id, verbose=False):
        c = MusicDatabase.getCursor()

        sql = text('INSERT INTO songs_ratings '
                   '     (song_id, user_id, rating) '
                   '     VALUES (:song_id, :user_id, NULL) '
                   ' ON CONFLICT DO NOTHING')
        result = c.execute('SELECT id FROM songs order by id')
        song_ids = [x[0] for x in result.fetchall()]
        for song_id in song_ids:
            if song_id < from_song_id:
                continue
            if verbose:
                print(song_id)
            stm = sql.bindparams(song_id=song_id, user_id=user_id)
            c.execute(stm)
        MusicDatabase.commit()


table = MusicDatabase.table
view = MusicDatabase.view
