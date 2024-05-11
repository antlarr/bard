from sqlalchemy import MetaData, Table, Column, Index, \
    ForeignKey, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy import Integer, Text, Numeric, Boolean, \
    LargeBinary, DateTime, REAL, TIMESTAMP
from sqlalchemy import select, func
from sqlalchemy.sql import expression
from sqlalchemy_utils import create_view, UUIDType

metadata = MetaData()

Songs = \
    Table('songs', metadata,
          Column('id', Integer, primary_key=True, autoincrement=True),
          Column('root', Text, nullable=False),
          Column('path', Text, unique=True, nullable=False),
          Column('filename', Text, nullable=False),
          Column('mtime', Numeric(20, 8)),
          Column('title', Text),
          Column('artist', Text),
          Column('album', Text),
          Column('albumartist', Text),
          Column('track', Integer),
          Column('date', Text),
          Column('genre', Text),
          Column('discnumber', Integer),
          Column('coverwidth', Integer),
          Column('coverheight', Integer),
          Column('covermd5', Text),
          Column('completeness', REAL),
          Column('update_time', TIMESTAMP,
                 server_default=func.current_timestamp()),
          Column('insert_time', TIMESTAMP,
                 server_default=func.current_timestamp()),
          Index('songs_path_idx', 'path'))

Properties = \
    Table('properties', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id),
                 primary_key=True, autoincrement=False),
          Column('format', Text),
          Column('duration', REAL),
          Column('bitrate', Integer),
          Column('bits_per_sample', Integer),
          Column('sample_rate', Integer),
          Column('channels', Integer),
          Column('audio_sha256sum', Text),
          Column('silence_at_start', REAL),
          Column('silence_at_end', REAL))

EnumSampleFormatValues = \
    Table('enum_sample_format_values', metadata,
          Column('id_value', Integer,
                 primary_key=True, autoincrement=True),
          Column('name', Text),
          Column('bits_per_sample', Integer),
          Column('is_planar', Boolean))


(EnumSampleFormatValues.insert()
 .values(name='u8', bits_per_sample=8, is_planar=False))
(EnumSampleFormatValues.insert()
 .values(name='s16', bits_per_sample=16, is_planar=False))
(EnumSampleFormatValues.insert()
 .values(name='s32', bits_per_sample=32, is_planar=False))
(EnumSampleFormatValues.insert()
 .values(name='flt', bits_per_sample=32, is_planar=False))
(EnumSampleFormatValues.insert()
 .values(name='dbl', bits_per_sample=64, is_planar=False))
(EnumSampleFormatValues.insert()
 .values(name='u8p', bits_per_sample=8, is_planar=True))
(EnumSampleFormatValues.insert()
 .values(name='s16p', bits_per_sample=16, is_planar=True))
(EnumSampleFormatValues.insert()
 .values(name='s32p', bits_per_sample=32, is_planar=True))
(EnumSampleFormatValues.insert()
 .values(name='fltp', bits_per_sample=32, is_planar=True))
(EnumSampleFormatValues.insert()
 .values(name='dblp', bits_per_sample=64, is_planar=True))
(EnumSampleFormatValues.insert()
 .values(name='s64', bits_per_sample=64, is_planar=False))
(EnumSampleFormatValues.insert()
 .values(name='s64p', bits_per_sample=64, is_planar=True))

EnumLibraryVersionsValues = \
    Table('enum_library_versions_values', metadata,
          Column('id_value', Integer, primary_key=True,
                 autoincrement=True),
          Column('bard_audiofile', Text),
          Column('libavcodec', Text),
          Column('libavformat', Text),
          Column('libavutil', Text),
          Column('libswresample', Text))

EnumFormatValues = \
    Table('enum_format_values', metadata,
          Column('id_value', Integer, primary_key=True,
                 autoincrement=True),
          Column('name', Text))

EnumCodecValues = \
    Table('enum_codec_values', metadata,
          Column('id_value', Integer, primary_key=True,
                 autoincrement=True),
          Column('name', Text))

DecodeProperties = \
    Table('decode_properties', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 primary_key=True, autoincrement=False),
          Column('codec', Integer, ForeignKey(EnumCodecValues.c.id_value),
                 nullable=False),
          Column('format', Integer, ForeignKey(EnumFormatValues.c.id_value),
                 nullable=False),
          Column('container_duration', REAL),
          Column('decoded_duration', REAL),
          Column('container_bitrate', Integer),
          Column('stream_bitrate', Integer),
          Column('stream_sample_format', Integer,
                 ForeignKey(EnumSampleFormatValues.c.id_value)),
          Column('stream_bits_per_raw_sample', Integer),
          Column('decoded_sample_format', Integer,
                 ForeignKey(EnumSampleFormatValues.c.id_value)),
          Column('samples', Integer),
          Column('library_versions', Integer,
                 ForeignKey(EnumLibraryVersionsValues.c.id_value),
                 nullable=False))


DecodeMessages = \
    Table('decode_messages', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('time_position', REAL),
          Column('level', Integer),
          Column('message', Text),
          Column('pos', Integer),
          Index('decode_messages_song_id_idx', 'song_id'))

Tags = \
    Table('tags', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('name', Text, nullable=False),
          Column('value', Text),
          Column('pos', Integer),
          Index('tags_song_id_idx', 'song_id'))

Covers = \
    Table('covers', metadata,
          Column('path', Text, nullable=False),
          Column('cover', LargeBinary, nullable=False))

Checksums = \
    Table('checksums', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 primary_key=True, autoincrement=False),
          Column('sha256sum', Text, nullable=False),
          Column('last_check_time', TIMESTAMP,
                 server_default=func.current_timestamp()),
          Column('insert_time', TIMESTAMP,
                 server_default=func.current_timestamp()))

Fingerprints = \
    Table('fingerprints', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 primary_key=True, autoincrement=False),
          Column('fingerprint', LargeBinary, nullable=False),
          Column('insert_time', TIMESTAMP,
                 server_default=func.current_timestamp()))

Similarities = \
    Table('similarities', metadata,
          Column('song_id1', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('song_id2', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('match_offset', Integer, nullable=False),
          Column('similarity', REAL, nullable=False),
          PrimaryKeyConstraint('song_id1', 'song_id2',
                               name='similarities_song_id1_song_id2_key'),
          Index('similarities_song_id1_idx', 'song_id1'),
          Index('similarities_song_id2_idx', 'song_id2'))

Users = \
    Table('users', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('name', Text, nullable=False),
          Column('password', LargeBinary),
          Column('active', Boolean, server_default=expression.true()))

SongsRatings = \
    Table('songs_ratings', metadata,
          Column('user_id', Integer,
                 ForeignKey(Users.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('rating', Integer),
          UniqueConstraint('user_id', 'song_id',
                           name='songs_ratings_user_id_song_id_key'))


avg_songs_ratings_s = (select(SongsRatings.c.song_id,
                              Users.c.id.label('user_id'),
                              func.round(func.avg(SongsRatings.c.rating))
                              .label('avg_rating'))
                       .where(SongsRatings.c.user_id != Users.c.id)
                       .group_by(SongsRatings.c.song_id, Users.c.id))
AvgSongsRatings = create_view('avg_songs_ratings',
                              avg_songs_ratings_s, metadata)

Albums = \
    Table('albums', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('path', Text, unique=True, nullable=False))

AlbumsRatings = \
    Table('albums_ratings', metadata,
          Column('user_id', Integer,
                 ForeignKey(Users.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('album_id', Integer,
                 ForeignKey(Albums.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('rating', Integer),
          UniqueConstraint('user_id', 'album_id',
                           name='albums_ratings_user_id_album_id_key'))

avg_albums_ratings_s = (select(AlbumsRatings.c.album_id,
                                Users.c.id.label('user_id'),
                                func.round(func.avg(AlbumsRatings.c.rating))
                                .label('avg_rating'))
                        .where(AlbumsRatings.c.user_id != Users.c.id)
                        .group_by(AlbumsRatings.c.album_id, Users.c.id))
AvgAlbumsRatings = create_view('avg_albums_ratings',
                               avg_albums_ratings_s, metadata)


SongsHistory = \
    Table('songs_history', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('song_id', Integer, nullable=False),
          Column('path', Text, nullable=False),
          Column('mtime', Numeric(20, 8)),
          Column('song_insert_time', DateTime),
          Column('removed', Boolean, server_default=expression.false()),
          Column('sha256sum', Text, nullable=False),
          Column('last_check_time', DateTime),
          Column('duration', REAL),
          Column('bitrate', Integer),
          Column('audio_sha256sum', Text, nullable=False),
          Column('description', Text),
          Column('insert_time', TIMESTAMP,
                 server_default=func.current_timestamp()),
          Index('songs_history_song_id_idx', 'song_id'),
          Index('songs_history_path_idx', 'path'))


SongsMBArtistIDs = \
    Table('songs_mb_artistids', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('artistid', UUIDType(binary=False), nullable=False),
          Index('songs_mb_artistids_song_id_idx', 'song_id'),
          Index('songs_mb_artistids_artistid_idx', 'artistid'))

SongsMBAlbumArtistIDs = \
    Table('songs_mb_albumartistids', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('albumartistid', UUIDType(binary=False), nullable=False),
          Index('songs_mb_albumartistids_song_id_idx', 'song_id'),
          Index('songs_mb_albumartistids_albumartistid_idx', 'albumartistid'))


SongsMBWorkIDs = \
    Table('songs_mb_workids', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Column('workid', UUIDType(binary=False), nullable=False),
          Index('songs_mb_workids_song_id_idx', 'song_id'),
          Index('songs_mb_workids_workid_idx', 'workid'))


SongsMB = \
    Table('songs_mb', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 primary_key=True, autoincrement=False, nullable=False),
          Column('releasegroupid', UUIDType(binary=False)),
          Column('releaseid', UUIDType(binary=False)),
          Column('releasetrackid', UUIDType(binary=False)),
          Column('recordingid', UUIDType(binary=False)),
          Column('confirmed', Boolean),
          Index('songs_mb_releasegroupid_idx', 'releasegroupid'),
          Index('songs_mb_recordingid_idx', 'recordingid'))


AlbumSongs = \
    Table('album_songs', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 primary_key=True, autoincrement=False, nullable=False),
          Column('album_id', Integer,
                 ForeignKey(Albums.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False),
          Index('album_songs_song_id_idx', 'song_id', unique=True),
          Index('album_songs_album_id_idx', 'album_id'))


album_properties_s = (select(
    AlbumSongs.c.album_id,
     Properties.c.format,
     func.min(Properties.c.bitrate).label('min_bitrate'),
     func.max(Properties.c.bitrate).label('max_bitrate'),
     func.min(Properties.c.bits_per_sample).label('min_bits_per_sample'),
     func.max(Properties.c.bits_per_sample).label('max_bits_per_sample'),
     func.min(Properties.c.sample_rate).label('min_sample_rate'),
     func.max(Properties.c.sample_rate).label('max_sample_rate'),
     func.min(Properties.c.channels).label('min_channels'),
     func.max(Properties.c.channels).label('max_channels'))
    .where(AlbumSongs.c.song_id == Properties.c.song_id)
    .group_by(AlbumSongs.c.album_id, Properties.c.format))

AlbumProperties = \
    Table('album_properties', metadata,
          Column('album_id', Integer,
                 ForeignKey(Albums.c.id, ondelete='CASCADE'),
                 autoincrement=False, nullable=False, index=True),
          Column('format', Text),
          Column('min_bitrate', Integer),
          Column('max_bitrate', Integer),
          Column('min_bits_per_sample', Integer),
          Column('max_bits_per_sample', Integer),
          Column('min_sample_rate', Integer),
          Column('max_sample_rate', Integer),
          Column('min_channels', Integer),
          Column('max_channels', Integer))

AlbumRelease = \
    Table('album_release', metadata,
          Column('album_id', Integer,
                 ForeignKey(Albums.c.id, ondelete='CASCADE'),
                 primary_key=True, autoincrement=False),
          Column('release_id', Integer,
                 ForeignKey('musicbrainz.release.id', ondelete='CASCADE'),
                 autoincrement=False, nullable=False, index=True))

# album_release_s = (select(
#     [AlbumSongs.c.album_id,
#      column("musicbrainz.release.id").label('release_id')])
#     .select_from(text('musicbrainz.release'))
#     .select_from(SongsMB)
#     .where(and_(SongsMB.c.releaseid == column("musicbrainz.release.mbid"),
#                 SongsMB.c.song_id == AlbumSongs.c.song_id))
#     .group_by(AlbumSongs.c.album_id, column("musicbrainz.release.id")))
#
#
# def create_meta_views(dialect):
#     if dialect == 'sqlite':
#         create_view('album_properties', album_properties_s, metadata)
#     else:
#         indexes = [Index('album_properties_album_id_idx', 'album_id')]
#         create_materialized_view('album_properties', album_properties_s,
#                                  metadata=metadata, indexes=indexes)
#
#     if dialect == 'sqlite':
#         create_view('album_release', album_release_s, metadata)
#     else:
#         indexes = [Index('album_release_album_id_idx', 'album_id',
#                          unique=True),
#                    Index('album_release_release_id_idx', 'release_id')]
#         create_materialized_view('album_release', album_release_s,
#                                  metadata=metadata, indexes=indexes)


EnumPlaylistTypeValues = \
    Table('enum_playlist_type_values', metadata,
          Column('id_value', Integer, primary_key=True,
                 autoincrement=True),
          Column('name', Text))

EnumPlaylistTypeValues.insert().values(name='user')
EnumPlaylistTypeValues.insert().values(name='album')
EnumPlaylistTypeValues.insert().values(name='search')
EnumPlaylistTypeValues.insert().values(name='generated')

Playlists = \
    Table('playlists', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('name', Text, nullable=False),
          Column('owner_id', Integer,
                 ForeignKey(Users.c.id, ondelete='CASCADE'),
                 nullable=False),
          Column('playlist_type', Integer,
                 ForeignKey(EnumPlaylistTypeValues.c.id_value),
                 nullable=False))

PlaylistSongs = \
    Table('playlist_songs', metadata,
          Column('playlist_id', Integer,
                 ForeignKey(Playlists.c.id, ondelete='CASCADE'),
                 nullable=False),
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 nullable=False),
          Column('recording_mbid', UUIDType(binary=False)),
          Column('pos', Integer),
          UniqueConstraint('playlist_id', 'pos',
                           name='playlist_songs_playlist_id_pos_key'),
          Index('playlist_songs_playlist_id_song_id_idx',
                'playlist_id', 'song_id'))


PlaylistGenerators = \
    Table('playlist_generators', metadata,
          Column('playlist_id', Integer,
                 ForeignKey(Playlists.c.id, ondelete='CASCADE'),
                 nullable=False),
          Column('generator', Text))


ArtistPaths = \
    Table('artist_paths', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('path', Text, nullable=False, unique=True),
          Column('image_filename', Text))


ArtistsMB = \
    Table('artists_mb', metadata,
          Column('id', Integer,
                 ForeignKey("musicbrainz.artist.id", ondelete='CASCADE',
                            name='artists_mb_id_fkey'),
                 primary_key=True,
                 autoincrement=False),  # The Foreign Key will be created after
                                        # the musicbrainz.artist table is
                                        # created.
          Column('locale_name', Text),
          Column('locale_sort_name', Text),
          Column('locale', Text),
          Column('artist_alias_type', Integer),
          Column('artist_path_id', Integer,
                 ForeignKey(ArtistPaths.c.id, ondelete='CASCADE')))


ArtistCreditsMB = \
    Table('artist_credits_mb', metadata,
          Column('artist_credit_id', Integer,
                 ForeignKey("musicbrainz.artist_credit.id", ondelete='CASCADE',
                            name='artist_credits_mb_artist_credit_id_fkey'),
                 primary_key=True),
          # The Foreign Key will be created after the
          # musicbrainz.artist_credit table is created.
          Column('artist_path_id', Integer,
                 ForeignKey(ArtistPaths.c.id, ondelete='CASCADE')))


ArtistsRatings = \
    Table('artists_ratings', metadata,
          Column('user_id', Integer,
                 ForeignKey(Users.c.id, ondelete='CASCADE'),
                 nullable=False, autoincrement=False),
          Column('artist_id', Integer,
                 ForeignKey(ArtistsMB.c.id, ondelete='CASCADE',
                            name='artists_ratings_artist_id_fkey'),
                 nullable=False),
          Column('rating', Integer),
          UniqueConstraint('user_id', 'artist_id',
                           name='artists_ratings_user_id_artist_id_key'))

avg_artists_ratings_s = (select(ArtistsRatings.c.artist_id,
                                Users.c.id.label('user_id'),
                                func.round(func.avg(ArtistsRatings.c.rating))
                                .label('avg_rating'))
                         .where(ArtistsRatings.c.user_id != Users.c.id)
                         .group_by(ArtistsRatings.c.artist_id, Users.c.id))
AvgArtistsRatings = create_view('avg_artists_ratings',
                                avg_artists_ratings_s, metadata)


Cuesheets = \
    Table('cuesheets', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 nullable=False),
          Column('idx', Integer, nullable=False),
          Column('sample_position', Integer, nullable=False),
          Column('time_position', REAL, nullable=False),
          Column('title', Text),
          Index('cuesheets_song_id_idx', 'song_id'))

DynamicRangeData = \
    Table('dynamic_range_data', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id, ondelete='CASCADE'),
                 nullable=False),
          Column('dr14', Integer, nullable=False),
          Column('db_peak', REAL, nullable=False),
          Column('db_rms', REAL, nullable=False),
          Column('insert_time', TIMESTAMP,
                 server_default=func.current_timestamp()),
          Index('dynamic_range_data_song_id_idx', 'song_id'))
