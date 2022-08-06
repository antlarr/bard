from bard.musicdatabase import MusicDatabase, DatabaseEnum, table
from collections import namedtuple
from sqlalchemy import text, insert, select, and_, desc, union, distinct
import bard.config as config
from bard.utils import alignColumns
from bard.db.core import Songs, Tags, AlbumSongs, AlbumRelease, SongsMB, \
    Properties, PlaylistSongs
from bard.db.musicbrainz import Medium, Release, Track, ArtistCredit
import os.path
from bard.percentage import Percentage

MBDataTuple = namedtuple('MBDataTuple',
                         ['artistids', 'albumartistids', 'workids',
                          'releasegroupid', 'releaseid', 'releasetrackid',
                          'recordingid', 'confirmed'])

FullSongsWebQuery = namedtuple('FullSongsWebQuery',
                               ['columns', 'conditions', 'order_by',
                                'limit', 'offset'])
FullSongsWebQuery.__new__.__defaults__ = ([], [], [], None, None)

MediumFormatEnum = DatabaseEnum('medium_format', schema='musicbrainz')
ReleaseStatusEnum = DatabaseEnum('release_status', schema='musicbrainz')
LanguageEnum = DatabaseEnum('language', schema='musicbrainz')
ReleaseGroupTypeEnum = DatabaseEnum('release_group_type', schema='musicbrainz')

# https://picard.musicbrainz.org/docs/mappings/
convert_tag = {
    'releasestatus':
        ['TXXX:MusicBrainz Album Status',
         'RELEASESTATUS',
         'MUSICBRAINZ_ALBUMSTATUS',
         '----:com.apple.iTunes:MusicBrainz Album Status',
         'MusicBrainz/Album Status'],
    'releasecountry':
        ['TXXX:MusicBrainz Album Release Country',
         'RELEASECOUNTRY',
         '----:com.apple.iTunes:MusicBrainz Album Release Country',
         'MusicBrainz/Album Release Country'],
    'releasetype':
        ['TXXX:MusicBrainz Album Type',
         'RELEASETYPE',
         'musicbrainz_albumtype',
         '----:com.apple.iTunes:MusicBrainz Album Type',
         'MusicBrainz/Album Type'],
    'musicbrainz_artistid':
        ['TXXX:MusicBrainz Artist Id',
         'musicbrainz_artistid',
         '----:com.apple.iTunes:MusicBrainz Artist Id',
         'MusicBrainz/Artist Id'],
    'musicbrainz_albumartistid':
        ['TXXX:MusicBrainz Album Artist Id',
         'musicbrainz_albumartistid',
         '----:com.apple.iTunes:MusicBrainz Album Artist Id',
         'MusicBrainz/Album Artist Id'],
    'musicbrainz_releasegroupid':
        ['TXXX:MusicBrainz Release Group Id',
         'musicbrainz_releasegroupid',
         '----:com.apple.iTunes:MusicBrainz Release Group Id',
         'MusicBrainz/Release Group Id'],
    'musicbrainz_releasetrackid':
        ['TXXX:MusicBrainz Release Track Id',
         'musicbrainz_releasetrackid',
         '----:com.apple.iTunes:MusicBrainz Release Track Id',
         'MusicBrainz/Release Track Id'],
    'musicbrainz_releaseid':
        ['TXXX:MusicBrainz Album Id',
         'musicbrainz_albumid',
         '----:com.apple.iTunes:MusicBrainz Album Id',
         'MusicBrainz/Album Id'],
    'musicbrainz_recordingid':
        ['UFID:http://musicbrainz.org',
         'TXXX:musicbrainz_trackid',
         'musicbrainz_trackid',
         '----:com.apple.iTunes:MusicBrainz Track Id',
         'MusicBrainz/Track Id'],
    'musicbrainz_workid':
        ['TXXX:MusicBrainz Work Id',
         'TXXX:musicbrainz_workid',
         'musicbrainz_workid',
         '----:com.apple.iTunes:MusicBrainz Work Id',
         'MusicBrainz/Work Id']
}


def lowercase_dict_keys(dictionary):
    return {x.lower(): y for x, y in dictionary.items()}


def decode_bytes(func):
    def wrapper(*args, **kwargs):
        r = func(*args, **kwargs)

        if isinstance(r, bytes):
            return r.decode('utf-8')

        if isinstance(r, list):
            return [x.decode('utf-8')
                    if isinstance(x, bytes) else x for x in r]

        return r
    return wrapper


@decode_bytes
def getList(tags, metadata_tags):
    for tag_name in metadata_tags:
        try:
            value = tags[tag_name]
        except KeyError:
            continue
        return value
    # No perfect match. Let's try ignoring case
    lc_tags = lowercase_dict_keys(tags)
    for tag_name in metadata_tags:
        try:
            value = lc_tags[tag_name.lower()]
        except KeyError:
            continue
        return value

    return None


def getValue(tags, metadata_tags):
    value = getList(tags, metadata_tags)
    if not value:
        return None
    if len(value) > 1:
        raise ValueError
    return value[0]


def getSongMusicBrainzIDs(songid, tags=None):
    if not tags:
        tags = MusicDatabase.getSongTags(songid)

    artistids = getList(tags, convert_tag['musicbrainz_artistid'])
    albumartistids = getList(tags, convert_tag['musicbrainz_albumartistid'])
    workids = getList(tags, convert_tag['musicbrainz_workid'])

    releasegroupid = getValue(tags, convert_tag['musicbrainz_releasegroupid'])
    releaseid = getValue(tags, convert_tag['musicbrainz_releaseid'])
    releasetrackid = getValue(tags, convert_tag['musicbrainz_releasetrackid'])
    recordingid = getValue(tags, convert_tag['musicbrainz_recordingid'])

    try:
        confirmed = (tags.get('musicbrainzverified', [None])[0] == '1' or
                     tags.get('uselabel', [None])[0] == '2' or
                     tags.get('usebarcode', [None])[0] == '1')
    except KeyError:
        confirmed = False

    r = MBDataTuple(artistids, albumartistids, workids, releasegroupid,
                    releaseid, releasetrackid, recordingid, confirmed)
    return r


class MusicBrainzDatabase:
    @staticmethod
    def songTags(songIDs=None, *, connection):
        if songIDs:
            sel = (select([Tags.c.song_id, Tags.c.name, Tags.c.value])
                   .where(Tags.c.song_id.in_(songIDs))
                   .order_by(Tags.c.song_id, Tags.c.pos))
        else:
            sel = (select([Tags.c.song_id, Tags.c.name, Tags.c.value])
                   .order_by(Tags.c.song_id, Tags.c.pos))
        result = connection.execute(sel)
        tags = {}
        rows = result.fetchall()
        current_song_id = None
        for row in rows:
            if row.song_id != current_song_id:
                if current_song_id:
                    yield current_song_id, tags
                    tags = {}
                current_song_id = row.song_id
            if row.name not in tags:
                tags[row.name] = [row.value]
            else:
                tags[row.name] += [row.value]

        if current_song_id:
            yield current_song_id, tags

    @staticmethod
    def insertMBArtistIDs(song_id, artistIDs, *, connection):
        if not artistIDs:
            return
        songs_mb_artistids = table('songs_mb_artistids')

        s = select([songs_mb_artistids.c.artistid]) \
            .where(songs_mb_artistids.c.song_id == song_id)

        result = connection.execute(s).fetchall()

        if set(artistIDs) == set(x['artistid'] for x in result):
            return

        d = songs_mb_artistids.delete() \
                              .where(songs_mb_artistids.c.song_id == song_id)
        connection.execute(d)
        for artistID in artistIDs:
            i = insert(songs_mb_artistids).values(song_id=song_id,
                                                  artistid=artistID)
            connection.execute(i)

    @staticmethod
    def insertMBAlbumArtistIDs(song_id, albumArtistIDs, *, connection):
        if not albumArtistIDs:
            return
        songs_mb_albumartistids = table('songs_mb_albumartistids')

        s = select([songs_mb_albumartistids.c.albumartistid]) \
            .where(songs_mb_albumartistids.c.song_id == song_id)

        result = connection.execute(s).fetchall()

        if set(albumArtistIDs) == set(x['albumartistid'] for x in result):
            return

        d = songs_mb_albumartistids.delete() \
            .where(songs_mb_albumartistids.c.song_id == song_id)
        connection.execute(d)
        for artistID in albumArtistIDs:
            i = insert(songs_mb_albumartistids).values(song_id=song_id,
                                                       albumartistid=artistID)
            connection.execute(i)

    @staticmethod
    def insertMBWorkIDs(song_id, workIDs, *, connection):
        if not workIDs:
            return
        songs_mb_workids = table('songs_mb_workids')

        s = select([songs_mb_workids.c.workid]) \
            .where(songs_mb_workids.c.song_id == song_id)

        result = connection.execute(s).fetchall()

        if set(workIDs) == set(x['workid'] for x in result):
            return

        d = songs_mb_workids.delete() \
                            .where(songs_mb_workids.c.song_id == song_id)
        connection.execute(d)
        for workID in workIDs:
            i = insert(songs_mb_workids).values(song_id=song_id,
                                                workid=workID)
            connection.execute(i)

    @staticmethod
    def insertMusicBrainzTags(song_id, mbIDs, *, connection):
        MusicBrainzDatabase.insertMBArtistIDs(song_id, mbIDs.artistids,
                                              connection=connection)
        MusicBrainzDatabase.insertMBAlbumArtistIDs(song_id,
                                                   mbIDs.albumartistids,
                                                   connection=connection)
        MusicBrainzDatabase.insertMBWorkIDs(song_id, mbIDs.workids,
                                            connection=connection)
        songs_mb = table('songs_mb')
        mbTagRecord = songs_mb.select(songs_mb.c.song_id == song_id)
        mbTagRecord = connection.execute(mbTagRecord).fetchone()
        if mbTagRecord:
            if (mbTagRecord['releasegroupid'] != mbIDs.releasegroupid or
                mbTagRecord['releaseid'] != mbIDs.releaseid or
                mbTagRecord['releasetrackid'] != mbIDs.releasetrackid or
                mbTagRecord['recordingid'] != mbIDs.recordingid or
                    mbTagRecord['confirmed'] != mbIDs.confirmed):
                print(f'update mb data for {song_id}')
                u = songs_mb.update() \
                            .where(songs_mb.c.song_id == song_id) \
                            .values(song_id=song_id,
                                    releasegroupid=mbIDs.releasegroupid,
                                    releaseid=mbIDs.releaseid,
                                    releasetrackid=mbIDs.releasetrackid,
                                    recordingid=mbIDs.recordingid,
                                    confirmed=mbIDs.confirmed)
                connection.execute(u)
        else:
            print(f'insert mb data for {song_id}')
            i = songs_mb.insert().values(song_id=song_id,
                                         releasegroupid=mbIDs.releasegroupid,
                                         releaseid=mbIDs.releaseid,
                                         releasetrackid=mbIDs.releasetrackid,
                                         recordingid=mbIDs.recordingid,
                                         confirmed=mbIDs.confirmed)
            connection.execute(i)

    @staticmethod
    def songsWithoutMBData():
        c = MusicDatabase.getCursor()
        sql = text('SELECT id FROM songs '
                   'WHERE NOT EXISTS (SELECT song_id '
                   '                    FROM songs_mb '
                   '                   WHERE song_id = id) '
                   'ORDER BY id')
        result = c.execute(sql)
        return [x[0] for x in result.fetchall()]

    @staticmethod
    def updateMusicBrainzIDs(songIDs=None):
        if not songIDs:
            return
        c = MusicDatabase.getConnection()
        for song_id, tags in MusicBrainzDatabase.songTags(songIDs,
                                                          connection=c):
            mbIDs = getSongMusicBrainzIDs(song_id, tags)
            if any(mbIDs):
                MusicBrainzDatabase.insertMusicBrainzTags(song_id, mbIDs,
                                                          connection=c)
                c.commit()

    @staticmethod
    def checkMusicBrainzTags():
        c = MusicDatabase.getCursor()
        sql = text('SELECT id, path FROM songs '
                   'WHERE root = :root '
                   '  AND NOT EXISTS (SELECT song_id '
                   '                   FROM songs_mb '
                   '                  WHERE recordingid is not NULL '
                   '                    AND song_id = id)'
                   '     ORDER BY id')
        table = []
        for root in config.config['musicbrainz_tagged_music_paths']:
            result = c.execute(sql, {'root': root})
            table.extend((str(song_id), path)
                         for song_id, path in result.fetchall())
        if table:
            table.insert(0, ('SONGID', 'PATH'))
            aligned = alignColumns(table, (False, True))
            print('Songs which should have musicbrainz tags but don\'t:')
            for line in aligned:
                print(line)
        return bool(table)

    @staticmethod
    def checkAlbumsWithDifferentReleases():
        c = MusicDatabase.getCursor()
        sql = text('SELECT album_id, path, '
                   '       COUNT(DISTINCT musicbrainz.release.id) '
                   '  FROM songs_mb, albums, album_songs, musicbrainz.release '
                   ' WHERE albums.id = album_songs.album_id '
                   '   AND releaseid = mbid '
                   '   AND songs_mb.song_id = album_songs.song_id '
                   ' GROUP BY album_songs.album_id, albums.path '
                   ' HAVING COUNT(DISTINCT musicbrainz.release.id) > 1')

        result = c.execute(sql)
        table = [(str(album_id), path, str(count))
                 for album_id, path, count in result.fetchall()]
        if table:
            table.insert(0, ('ALBUMID', 'PATH', 'NUMBER OF RELEASES'))
            aligned = alignColumns(table, (False, True, False))
            print('Albums that contain songs from different releases:')
            for line in aligned:
                print(line)
        return bool(table)

    @staticmethod
    def checkAlbumsWithDifferentFormats():
        c = MusicDatabase.getCursor()
        sql = text('select id, path, format '
                   '  from albums, album_properties '
                   ' where id in (select album_id '
                   '                from (select  album_id, count(*) '
                   '                        from album_properties '
                   '                    group by album_id '
                   '                      having count(*)>1) '
                   '                  as foo) '
                   '   and id = album_id')

        result = c.execute(sql)
        table = [(str(album_id), path, audioFormat)
                 for album_id, path, audioFormat in result.fetchall()]
        if table:
            table.insert(0, ('ALBUMID', 'PATH', 'FORMAT'))
            aligned = alignColumns(table, (False, True, True))
            print('Albums that contain songs with different formats:')
            for line in aligned:
                print(line)
        return bool(table)

    @staticmethod
    def get_all_artists():
        """Return all artists (used by the mb importer)."""
        songs_mb_artistids = table('songs_mb_artistids')

        s = select([songs_mb_artistids.c.artistid]).distinct()

        result_artists = MusicDatabase.execute(s).fetchall()
        s1 = set(x['artistid'] for x in result_artists)

        songs_mb_albumartistids = table('songs_mb_albumartistids')

        s = select([songs_mb_albumartistids.c.albumartistid]).distinct()

        result_albumartists = MusicDatabase.execute(s).fetchall()
        r = s1.union(x['albumartistid'] for x in result_albumartists)
        return r

    @staticmethod
    def get_all_elements_from_songs_mb(column=None):
        if not column:
            return []

        songs_mb = table('songs_mb')

        s = select([getattr(songs_mb.c, column)]).distinct()

        result = MusicDatabase.execute(s).fetchall()
        r = set(x[column] for x in result)
        r.difference_update({None})

        return r

    @staticmethod
    def get_all_recordings():
        return MusicBrainzDatabase.get_all_elements_from_songs_mb(
            'recordingid')

    @staticmethod
    def get_all_releasegroups():
        return MusicBrainzDatabase.get_all_elements_from_songs_mb(
            'releasegroupid')

    @staticmethod
    def get_all_releases():
        return MusicBrainzDatabase.get_all_elements_from_songs_mb(
            'releaseid')

    @staticmethod
    def get_all_tracks():
        return MusicBrainzDatabase.get_all_elements_from_songs_mb(
            'releasetrackid')

    @staticmethod
    def get_all_works():
        songs_mb_workids = table('songs_mb_workids')

        s = select([songs_mb_workids.c.workid]).distinct()

        result = MusicDatabase.execute(s).fetchall()
        return set(x['workid'] for x in result)

    @staticmethod
    def get_range_artists(offset=0, page_size=500, metadata=False,
                          artist_filter='all'):
        artist = table('musicbrainz.artist')
        artists_mb = table('artists_mb')
        artist_paths = table('artist_paths')
        j = (artists_mb.join(artist_paths,
             artists_mb.c.artist_path_id == artist_paths.c.id, isouter=True))
        if artist_filter in ['main', 'main+']:
            acn = table('musicbrainz.artist_credit_name')
            rg = table('musicbrainz.release_group')
            rel = table('musicbrainz.release')
            songs_mb = table('songs_mb')
            tables_to_get_artists_from = [
                select([rg.c.artist_credit_id]).where(rg.c.mbid.in_(
                    select([songs_mb.c.releasegroupid]))),
                select([rel.c.artist_credit_id]).where(rel.c.mbid.in_(
                    select([songs_mb.c.releaseid])))]
            if artist_filter == 'main+':
                rec = table('musicbrainz.recording')
                tables_to_get_artists_from.append(
                    select([rec.c.artist_credit_id]).where(rec.c.mbid.in_(
                        select([songs_mb.c.recordingid]))))

            main_artist_ids = \
                (select([distinct(acn.c.artist_id)])
                 .where(acn.c.artist_credit_id.in_(
                        union(*tables_to_get_artists_from))))
            qfilter = and_(artist.c.id.in_(main_artist_ids),
                           artist.c.id == artists_mb.c.id)
        else:
            qfilter = (artist.c.id == artists_mb.c.id)

        s = (select([artist.c.id, artist.c.mbid, artist.c.name,
                    artist.c.artist_type, artist.c.area_id, artist.c.gender,
                    artist.c.disambiguation,
                    artists_mb.c.locale_name, artists_mb.c.locale_sort_name,
                    artist_paths.c.path, artist_paths.c.image_filename])
             .select_from(j)
             .where(qfilter)
             .order_by(artists_mb.c.locale_name)
             .limit(page_size)
             .offset(offset))
        return MusicDatabase.execute(s).fetchall()

    @staticmethod
    def is_better_alias(a, b):
        """Return True if a is a better alias than b."""
        if a and not b:
            return True

        try:
            order_a = config.config['preferred_locales'].index(a['locale'])
        except ValueError:
            if (a['locale'] == b['locale'] and
                a['primary_for_locale'] and
                    not b['primary_for_locale']):
                return True
            return False

        try:
            order_b = config.config['preferred_locales'].index(b['locale'])
        except ValueError:
            # a is in the preferred_locales and b is not
            return True

        if order_a == order_b:
            return (a['primary_for_locale'] and not b['primary_for_locale'])

        return order_a < order_b

    @staticmethod
    def cacheMusicBrainzDB():
        artist = table('musicbrainz.artist')
        aa = table('musicbrainz.artist_alias')
        s = select([artist.c.id, artist.c.mbid, artist.c.name,
                    artist.c.sort_name, artist.c.artist_type, artist.c.area_id,
                    artist.c.gender, artist.c.disambiguation])
        locales = config.config['preferred_locales']
        c = MusicDatabase.getCursor()
        artists = {a['id']: a for a in c.execute(s).fetchall()}

        s = (select([aa.c.artist_id, aa.c.name, aa.c.sort_name, aa.c.locale,
                     aa.c.artist_alias_type, aa.c.primary_for_locale])
             .where(and_(aa.c.artist_id.in_(artists.keys()),
                         aa.c.locale.in_(locales))))
        current = {}
        aliases = {}
        for x in c.execute(s).fetchall():
            aliases.setdefault(x['artist_id'], []).append(x)

        percentage = Percentage()
        percentage.max_value = len(artists)
        for i, a in enumerate(artists.values()):
            current = {}
            try:
                current_artist_aliases = aliases[a['id']]
            except KeyError:
                current = {'locale_name': a['name'],
                           'locale_sort_name': a['sort_name'],
                           'locale': None,
                           'artist_alias_type': None}
            else:
                for x in current_artist_aliases:
                    if MusicBrainzDatabase.is_better_alias(x, current):
                        current = {'locale_name': x['name'],
                                   'locale_sort_name': x['sort_name'],
                                   'locale': x['locale'],
                                   'artist_alias_type': x['artist_alias_type'],
                                   'primary_for_locale':
                                       x['primary_for_locale']}
                del current['primary_for_locale']

            current['id'] = a['id']
            MusicDatabase.insert_or_update('artists_mb', current, connection=c)
            percentage.set_value(i)

        c.commit()
        percentage.set_value(percentage.max_value)
        print('')

    @staticmethod
    def get_letter_offset_for_artist(letter, artist_filter='all'):
        if letter == '0':
            return 0

        if artist_filter in ['main', 'main+']:
            if artist_filter == 'main+':
                rec_table_union = '''union select rec.artist_credit_id
        from musicbrainz.recording rec
       where rec.mbid in (select recordingid from songs_mb)'''
            else:
                rec_table_union = ''
            qfilter = '''
where id in (select distinct acn.artist_id
               from musicbrainz.artist_credit_name acn
               where acn.artist_credit_id in
     (select rg.artist_credit_id
        from musicbrainz.release_group rg
       where rg.mbid in (select releasegroupid from songs_mb)
union select rel.artist_credit_id
        from musicbrainz.release rel
       where rel.mbid in (select releaseid from songs_mb)
        %s))''' % rec_table_union
        else:
            qfilter = ''
        c = MusicDatabase.getCursor()
        sql = ('select min(subq.offset) from ('
               '       select row_number() over(order by locale_name)'
               '                           as offset,'
               '              locale_name, id'
               f'         from artists_mb {qfilter}) as subq'
               '  where subq.locale_name ilike :search')
        result = c.execute(sql, {'search': letter + '%'})
        return result.fetchone()[0] - 1

    @staticmethod
    def get_artist_image_path(artistID):
        c = MusicDatabase.getCursor()
        sql = ('select ap.path, ap.image_filename '
               'from artists_mb amb, artist_paths ap '
               'where amb.id = :artistid and amb.artist_path_id = ap.id')
        result = c.execute(sql, {'artistid': artistID})
        r = result.fetchone()
        if not r:
            return None
        return os.path.join(r[0], r[1])

    @staticmethod
    def get_artist_info(*, artistID=None, artistMBID=None):
        artist = table('musicbrainz.artist')
        artists_mb = table('artists_mb')
        artist_paths = table('artist_paths')
        j = (artists_mb.join(artist_paths,
             artists_mb.c.artist_path_id == artist_paths.c.id, isouter=True))
        s = (select([artist.c.id, artist.c.mbid, artist.c.name,
                    artist.c.artist_type, artist.c.area_id, artist.c.gender,
                    artist.c.disambiguation,
                    artists_mb.c.locale_name, artists_mb.c.locale_sort_name,
                    artist_paths.c.path, artist_paths.c.image_filename])
             .select_from(j))
        if artistMBID:
            s = s.where(and_(artist.c.id == artists_mb.c.id,
                             artist.c.mbid == artistMBID))
        else:
            s = s.where(and_(artist.c.id == artists_mb.c.id,
                             artist.c.id == artistID))

        return MusicDatabase.execute(s).fetchone()

    @staticmethod
    def get_artist_id(mbid):
        artist = table('musicbrainz.artist')
        s = select([artist.c.id]).where(artist.c.mbid == mbid)

        r = MusicDatabase.execute(s).fetchone()
        return r[0] if r else None

    @staticmethod
    def get_artists_info(artistIDs):
        artist = table('musicbrainz.artist')
        artists_mb = table('artists_mb')
        artist_paths = table('artist_paths')
        j = (artists_mb.join(artist_paths,
             artists_mb.c.artist_path_id == artist_paths.c.id, isouter=True))
        s = (select([artist.c.id, artist.c.mbid, artist.c.name,
                    artist.c.artist_type, artist.c.area_id, artist.c.gender,
                    artist.c.disambiguation,
                    artists_mb.c.locale_name, artists_mb.c.locale_sort_name,
                    artist_paths.c.path, artist_paths.c.image_filename])
             .select_from(j)
             .where(and_(artist.c.id == artists_mb.c.id,
                         artist.c.id.in_(artistIDs))))
        return MusicDatabase.execute(s).fetchall()

    @staticmethod
    def get_artist_aliases(artistID, locales=None, only_primary=False):
        alias = table('musicbrainz.artist_alias')
        s = (select([alias.c.name, alias.c.sort_name, alias.c.locale,
                     alias.c.artist_alias_type, alias.c.primary_for_locale])
             .where(alias.c.artist_id == artistID)
             .order_by(alias.c.locale)
             .order_by(desc(alias.c.primary_for_locale)))
        # query is ordered by locale and inside each locale, the primary
        # is returned first
        if locales:
            s = s.where(alias.c.locale.in_(locales))
        if only_primary:
            s = s.where(alias.c.primary_for_locale.is_(True))
        return MusicDatabase.execute(s).fetchall()

    @staticmethod
    def get_artist_release_groups(artistID):
        c = MusicDatabase.getCursor()
        sql = ('select rg.id, mbid, rg.name, disambiguation, '
               'rgt.name as release_group_type, rg.artist_credit_id, '
               'ac.name as artist_credit_name'
               ' from musicbrainz.release_group as rg, '
               '      musicbrainz.artist_credit as ac, '
               '      musicbrainz.artist_credit_name as acn, '
               '      musicbrainz.enum_release_group_type_values as rgt '
               'where rg.artist_credit_id = ac.id '
               '  and rg.artist_credit_id = acn.artist_credit_id '
               '  and rg.release_group_type = rgt.id_value '
               '  and acn.artist_id = :artistID '
               '  and exists(select ar.album_id '
               '               from album_release ar, musicbrainz.release rel '
               '              where ar.release_id = rel.id '
               '                and rel.release_group_id = rg.id)')
        result = c.execute(sql, {'artistID': artistID})
        return result.fetchall()

    @staticmethod
    def get_release_group_directories(rgMBID):
        c = MusicDatabase.getCursor()
        sql = ('select path '
               '  from songs '
               ' where id in (select song_id '
               '               from songs_mb '
               '              where releasegroupid=:rgMBID) '
               ' order by id')
        result = c.execute(sql, {'rgMBID': rgMBID})
        return set(os.path.dirname(path) for (path,) in result.fetchall())

    @staticmethod
    def get_link_type_id(name, entity_type0, entity_type1):
        if not getattr(MusicBrainzDatabase, 'link_types', None):
            c = MusicDatabase.getCursor()
            sql = ('select id, name, entity_type0, entity_type1 '
                   'from musicbrainz.link_type')
            r = c.execute(sql)
            MusicBrainzDatabase.link_types = \
                {(lt_name, lt_entity_t0, lt_entity_t1): lt_id
                 for lt_id, lt_name, lt_entity_t0, lt_entity_t1
                 in r.fetchall()}

        try:
            return MusicBrainzDatabase.link_types[(name,
                                                   entity_type0, entity_type1)]
        except KeyError:
            print(f'Link type {name} from {entity_type0} to {entity_type1} '
                  'does not exist. Available link types of that kind are:')
            for name, et0, et1 in MusicBrainzDatabase.link_types:
                if et0 == entity_type0 and et1 == entity_type1:
                    print(name, et0, et1)
            print('Fix the application!')
            raise RuntimeError('Link type does not exist.')

    @staticmethod
    def get_links(entity_type0, entity_type1, lt_id, entity_positions, entity):
        c = MusicDatabase.getCursor()
        if 0 in entity_positions:
            if 1 in entity_positions:
                clause = '(l.entity0=:entity or l.entity1=:entity)'
            else:
                clause = 'l_entity0=:entity'
        else:
            clause = 'l_entity1=:entity'

        rel_table = f'l_{entity_type0}_{entity_type1}'

        sql = ('select link.id link_id, entity0, entity1, link_order, '
               '        entity0_credit, entity1_credit, '
               '        begin_date_year, begin_date_month, begin_date_day,'
               '        end_date_year, end_date_month, end_date_day'
               f'   from musicbrainz.{rel_table} l, '
               '        musicbrainz.link link '
               '  where link.id = l.link_id '
               '    and link.link_type_id=:lt_id '
               f'    and {clause}')
        r = c.execute(sql, {'lt_id': lt_id, 'entity': entity})
        return r.fetchall()

    @staticmethod
    def get_related_entities(relation, entity, entity_type):
        lt_id = MusicBrainzDatabase.get_link_type_id(*relation)
        entity_positions = [i for i in (0, 1)
                            if relation[i + 1] == entity_type]

        r = MusicBrainzDatabase.get_links(relation[1], relation[2], lt_id,
                                          entity_positions, entity)
        return r

    @staticmethod
    def get_link_attributes(link_id):
        c = MusicDatabase.getCursor()
        sql = ('select id, name '
               '   from musicbrainz.link_attribute la, '
               '        musicbrainz.link_attribute_type lat '
               '  where la.link_id = :link_id '
               '    and la.link_attribute_type_id = lat.id ')
        r = c.execute(sql, {'link_id': link_id})
        return r.fetchall()

    @staticmethod
    def get_artist_artist_relationship(relationship, artistID):
        relation = (relationship, 'artist', 'artist')
        r = MusicBrainzDatabase.get_related_entities(relation, artistID,
                                                     'artist')
        result1 = []
        result2 = []
        ids = []
        for x in r:
            if x['entity0'] != artistID:
                ids.append(x['entity0'])
            if x['entity1'] != artistID:
                ids.append(x['entity1'])

        artists = {x['id']: dict(x)
                   for x in MusicBrainzDatabase.get_artists_info(ids)}
        # print(artists)

        for x in r:
            begin_date = (x['begin_date_year'],
                          x['begin_date_month'],
                          x['begin_date_day'])
            end_date = (x['end_date_year'],
                        x['end_date_month'],
                        x['end_date_day'])
            attrs = MusicBrainzDatabase.get_link_attributes(x['link_id'])
            if x['entity0'] != artistID:
                result1.append((artists[x['entity0']], begin_date, end_date,
                                [x['name'] for x in attrs] if attrs else None))
                # print('###', x)
            if x['entity1'] != artistID:
                result2.append((artists[x['entity1']], begin_date, end_date,
                                [x['name'] for x in attrs] if attrs else None))
                # print('   ', x)

        # print('->', result1)
        # print('<-', result2)
        return (result1, result2)

    @staticmethod
    def get_artist_members_of_band_relations(artistID):
        MBD = MusicBrainzDatabase
        return MBD.get_artist_artist_relationship('member of band', artistID)

    @staticmethod
    def get_artist_collaboration_relations(artistID):
        MBD = MusicBrainzDatabase
        return MBD.get_artist_artist_relationship('collaboration', artistID)

    @staticmethod
    def get_release_group_info(rgID):
        rg = table('musicbrainz.release_group')
        ac = table('musicbrainz.artist_credit')
        s = (select([rg.c.id, rg.c.mbid, rg.c.name,
                    rg.c.disambiguation,
                    rg.c.release_group_type, rg.c.artist_credit_id,
                    ac.c.name.label('artist_name')])
             .where(and_(rg.c.artist_credit_id == ac.c.id,
                         rg.c.id == rgID)))
        return MusicDatabase.execute(s).fetchone()

    @staticmethod
    def get_release_group_secondary_types(rgID):
        c = MusicDatabase.getCursor()
        sql = ('select name '
               '  from musicbrainz.release_group_secondary_type_join, '
               '       musicbrainz.enum_release_group_secondary_type_values '
               ' where release_group_id = :rgID '
               '   and secondary_type = id_value')
        r = c.execute(text(sql), {'rgID': rgID})
        return [x[0] for x in r.fetchall()]

    @staticmethod
    def get_release_group_releases(rgID):
        c = MusicDatabase.getCursor()
        sql = text('select album_id, r.id, mbid, r.name, disambiguation, '
                   '       release_status, language, barcode, '
                   '       artist_credit_id, ac.name artist_name, '
                   '       r.release_group_id '
                   '  from musicbrainz.release r, '
                   '       musicbrainz.artist_credit ac, '
                   '       album_release ar'
                   ' where ar.release_id = r.id '
                   '   and r.artist_credit_id = ac.id '
                   '   and r.release_group_id = :rgID ')
        r = c.execute(sql, {'rgID': rgID})
        return r.fetchall()

    @staticmethod
    def get_release_group_album_count(rgID):
        c = MusicDatabase.getCursor()
        sql = text('select count(*) '
                   '  from album_release ar, musicbrainz.release r '
                   ' where ar.release_id = r.id '
                   '   and r.release_group_id = :rgID')
        r = c.execute(sql, {'rgID': rgID}).fetchone()
        if not r or not r[0]:
            return 0
        return r[0]

    @staticmethod
    def get_release_tracks_count(releaseID):
        c = MusicDatabase.getCursor()
        sql = text('select m.position, count(*) '
                   '  from musicbrainz.medium m, '
                   '       musicbrainz.track t '
                   ' where m.release_id=:releaseID '
                   '   and t.medium_id=m.id group by 1 order by 1')
        r = c.execute(sql, {'releaseID': releaseID})
        return [count for pos, count in r.fetchall()]

    @staticmethod
    def get_release_group_albums(rgID):
        c = MusicDatabase.getCursor()
        sql = text('select ar.album_id'
                   '  from album_release ar, musicbrainz.release r '
                   ' where ar.release_id = r.id '
                   '   and r.release_group_id = :rgID')
        r = c.execute(sql, {'rgID': rgID}).fetchall()
        return [x[0] for x in r]

    @staticmethod
    def get_release_mediums(releaseID):
        m = table('musicbrainz.medium')
        emfv = table('musicbrainz.enum_medium_format_values')
        s = (select([m.c.id, m.c.release_id, m.c.position,
                     emfv.c.name.label('format_name'),
                     m.c.name])
             .where(and_(m.c.format == emfv.c.id_value,
                         m.c.release_id == releaseID))
             .order_by(m.c.position))
        return MusicDatabase.execute(s).fetchall()

    @staticmethod
    def mediumlist_to_string(mediumlist):
        r = []
        format_name = None
        num = 0
        for medium in mediumlist:
            if medium['format_name'] != format_name:
                if num > 1:
                    r.append(f'{num}x{format_name}')
                elif num == 1:
                    r.append(format_name)
                num = 0
                format_name = medium['format_name']
            num += 1

        if num > 1:
            r.append(f'{num}x{format_name}')
        elif num == 1:
            r.append(format_name)

        return '+'.join(r)

    @staticmethod
    def get_release_directories(releaseMBID):
        c = MusicDatabase.getCursor()
        sql = ('select path '
               '  from songs '
               ' where id in (select song_id '
               '               from songs_mb '
               '              where releaseid=:releaseMBID)')
        result = c.execute(text(sql), {'releaseMBID': releaseMBID})
        return set(os.path.dirname(path) for (path,) in result.fetchall())

    @staticmethod
    def get_release_label(releaseID):
        rl = table('musicbrainz.release_label')
        label = table('musicbrainz.label')
        s = (select([label.c.name.label('label_name'), rl.c.catalog_number])
             .where(and_(rl.c.label_id == label.c.id,
                         rl.c.release_id == releaseID)))
        return MusicDatabase.execute(s).fetchall()

    @staticmethod
    def getAlbumDisambiguation(release, use_uselabel=False):
        c = MusicDatabase.getCursor()
        sql = text('select name, value '
                   '  from tags, album_songs '
                   ' where tags.song_id = album_songs.song_id '
                   '   and album_songs.album_id = :albumID '
                   '   and name IN (\'comment\',\'usereleasecomment\','
                   '                \'uselabel\') '
                   ' group by name, value')
        r = c.execute(sql, {'albumID': release['album_id']})
        album = {x['name']: x['value'] for x in r.fetchall()}
        # print(release, album)
        try:
            usereleasecomment = int(album['usereleasecomment'])
        except KeyError:
            usereleasecomment = 1

        result = []
        if usereleasecomment == 2:
            result.append(album['comment'])
        elif usereleasecomment == 1:
            if release['disambiguation']:
                result.append(release['disambiguation'])
        elif usereleasecomment == 3:
            rg = MusicBrainzDatabase.get_release_group_info(
                release['release_group_id'])
            if rg['disambiguation']:
                result.append(rg['disambiguation'])

        if use_uselabel:
            try:
                uselabel = int(album['uselabel'])
            except KeyError:
                uselabel = 0

            if uselabel > 0:
                release_label = \
                    MusicBrainzDatabase.get_release_label(release['id'])[0]
                if uselabel == 1:
                    result.append(release_label['label_name'])
                else:
                    result.append(release_label['label_name'] + ':' +
                                  release_label['catalog_number'])

        return ','.join(result)

    @staticmethod
    def get_album_info(albumID):
        c = MusicDatabase.getCursor()
        sql = text('select album_id, r.id release_id, mbid release_mbid, '
                   '       r.name, disambiguation, '
                   '       release_status, language, barcode, '
                   '       artist_credit_id, ac.name artist_credit_name, '
                   '       r.release_group_id '
                   '  from musicbrainz.release r, '
                   '       musicbrainz.artist_credit ac, '
                   '       album_release ar'
                   ' where ar.release_id = r.id '
                   '   and r.artist_credit_id = ac.id '
                   '   and ar.album_id = :albumID ')
        result = c.execute(sql, {'albumID': albumID})
        return result.fetchone()

    @staticmethod
    def get_release_events(releaseID):
        c = MusicDatabase.getCursor()
        sql = text('select a.name country, date_year, date_month, date_day '
                   '  from musicbrainz.release_country rc, '
                   '       musicbrainz.area a '
                   ' where rc.release_id = :releaseID '
                   '   and rc.country_id = a.id')
        result = c.execute(sql, {'releaseID': releaseID})
        r = result.fetchall()
        sql = text('select NULL country, date_year, date_month, date_day '
                   '  from musicbrainz.release_unknown_country rc '
                   ' where rc.release_id = :releaseID')
        result = c.execute(sql, {'releaseID': releaseID})
        r.extend(result.fetchall())
        return r

    @staticmethod
    def get_album_tracks(albumID):
        c = MusicDatabase.getCursor()
        columns = [AlbumRelease.c.album_id,
                   Medium.c.position.label('medium_number'),
                   Medium.c.format.label('medium_format_id'),
                   #   emfv.name as medium_format,
                   Medium.c.name.label('medium_name'),
                   Track.c.position.label('track_position'),
                   Track.c.mbid.label('track_mbid'),
                   Track.c.recording_id,
                   Track.c.number_text,
                   Track.c.name,
                   ArtistCredit.c.name.label('artist_name'),
                   Track.c.artist_credit_id,
                   Track.c.is_data_track,
                   (Track.c.length / 1000).label('duration')]

        sel = (select(columns)
               .where(and_(AlbumRelease.c.release_id == Medium.c.release_id,
                           Medium.c.id == Track.c.medium_id,
                           AlbumRelease.c.album_id == albumID,
                           Track.c.artist_credit_id == ArtistCredit.c.id))
               .order_by(Medium.c.position, Track.c.position))
        result = c.execute(sel)

        return result.fetchall()

    @staticmethod
    def get_album_songs(albumID):
        c = MusicDatabase.getCursor()
        sql = ('select songs_mb.song_id, '
               '       songs_mb.releasetrackid '
               '  from album_songs, songs_mb '
               ' where album_songs.song_id = songs_mb.song_id '
               '   and album_songs.album_id = :albumID ')
        result = c.execute(text(sql), {'albumID': albumID})
        return result.fetchall()

    @staticmethod
    def get_songs_information_for_webui(*, songIDs=None,
                                        query=FullSongsWebQuery()):
        if songIDs:
            query = FullSongsWebQuery(
                conditions=[AlbumSongs.c.song_id.in_(songIDs)],
                order_by=[AlbumSongs.c.song_id])

        c = MusicDatabase.getCursor()

        columns = [AlbumSongs.c.album_id.label('album_id'),
                   AlbumSongs.c.song_id.label('song_id'),
                   Medium.c.position.label('medium_number'),
                   Medium.c.format.label('medium_format_id'),
                   #   emfv.name as medium_format,
                   Release.c.name.label('release_name'),
                   Medium.c.name.label('medium_name'),
                   Track.c.position.label('track_position'),
                   Track.c.mbid.label('track_mbid'),
                   Track.c.recording_id,
                   Track.c.number_text,
                   Track.c.name,
                   ArtistCredit.c.name.label('artist_name'),
                   Track.c.artist_credit_id,
                   Track.c.is_data_track,
                   Properties.c.duration,
                   Properties.c.format,
                   Properties.c.bitrate,
                   Properties.c.bits_per_sample,
                   Properties.c.sample_rate,
                   Properties.c.channels,
                   *query.columns]

        sel = (select(columns)
               .where(and_(AlbumRelease.c.release_id == Medium.c.release_id,
                           AlbumRelease.c.release_id == Release.c.id,
                           Medium.c.id == Track.c.medium_id,
                           AlbumRelease.c.album_id == AlbumSongs.c.album_id,
                           Track.c.artist_credit_id == ArtistCredit.c.id,
                           SongsMB.c.song_id == AlbumSongs.c.song_id,
                           Properties.c.song_id == AlbumSongs.c.song_id,
                           SongsMB.c.releasetrackid == Track.c.mbid,
                           *query.conditions)))

        if query.order_by:
            sel = sel.order_by(*query.order_by)
        if query.limit:
            sel = sel.limit(query.limit)
        if query.offset:
            sel = sel.offset(query.offset)
        # print(sel)
        result = c.execute(sel)
        return result.fetchall()

    @staticmethod
    def get_playlist_songs_information_for_webui(playlistID):
        query = FullSongsWebQuery(
            columns=[PlaylistSongs.c.pos.label('position')],
            conditions=[PlaylistSongs.c.playlist_id == playlistID,
                        AlbumSongs.c.song_id == PlaylistSongs.c.song_id],
            order_by=[PlaylistSongs.c.pos])
        return MusicBrainzDatabase.get_songs_information_for_webui(query=query)

    @staticmethod
    def get_album_songs_information_for_webui(albumID):
        query = FullSongsWebQuery(
            conditions=[AlbumRelease.c.album_id == albumID],
            order_by=[Medium.c.position, Track.c.position])
        return MusicBrainzDatabase.get_songs_information_for_webui(query=query)

    @staticmethod
    def get_artist_credit_info(artistCreditID):
        c = MusicDatabase.getCursor()
        sql = ('select artist_id, position, name, join_phrase'
               '  from musicbrainz.artist_credit_name '
               ' where artist_credit_id = :artistCreditID '
               '  order by position')
        result = c.execute(text(sql), {'artistCreditID': artistCreditID})
        return result.fetchall()

    @staticmethod
    def get_artist_credit_ids(mbids):
        """Return a list of artist_credit_ids associated to a list of mbids.

        In theory, this should return just one artist_credit_ids, but some
        times there are more than one artist_credit_ids, for example, when the
        same artists are credited like "Eric Woolfson and Alan Parsons"
        and also like "Eric Woolfson & Alan Parsons".
        """
        acn = table('musicbrainz.artist_credit_name')
        s = select([acn.c.artist_credit_id])
        for pos, mbid in enumerate(mbids):
            artist_id = MusicBrainzDatabase.get_artist_id(mbid)
            s = s.where(acn.c.artist_credit_id.in_(
                (select([acn.c.artist_credit_id])
                 .where(and_(acn.c.artist_id == artist_id,
                             acn.c.position == pos)))))
        s = (s.where(acn.c.artist_credit_id.notin_(
             (select([acn.c.artist_credit_id])
              .where(acn.c.position == len(mbids)))))
             .group_by(acn.c.artist_credit_id))

        r = MusicDatabase.execute(s).fetchall()
        return sorted([x[0] for x in r]) if r else None

    @staticmethod
    def search_songs_for_webui(query, offset=None, page_size=200):
        query = FullSongsWebQuery(
            conditions=[Songs.c.path.ilike(f'%{query}%'),
                        AlbumSongs.c.song_id == Songs.c.id],
            order_by=[AlbumSongs.c.album_id,
                      Medium.c.position,
                      Track.c.position],
            limit=page_size,
            offset=offset)
        return MusicBrainzDatabase.get_songs_information_for_webui(query=query)

    @staticmethod
    def get_release_group_date(releaseGroupID):
        c = MusicDatabase.getCursor()
        sql = ('select min(date_year)'
               '  from musicbrainz.release_country rc,'
               '       musicbrainz.release r'
               ' WHERE r.id = rc.release_id '
               '   AND r.release_group_id = :releaseGroupID ')
        r = c.execute(text(sql), {'releaseGroupID': releaseGroupID}).fetchone()
        if r and r[0]:
            return r[0]

        sql = ('select min(s.date)'
               '  from songs s, album_songs aso, album_release ar, '
               '       musicbrainz.release r'
               ' WHERE r.release_group_id = :releaseGroupID '
               '   AND ar.release_id = r.id '
               '   AND aso.album_id = ar.album_id '
               '   AND s.id = aso.song_id ')
        r = c.execute(text(sql), {'releaseGroupID': releaseGroupID}).fetchone()
        if not r or not r[0]:
            return None
        return r[0]

    @staticmethod
    def get_release_group_ratings(release_group_id, user_id):
        album_ids = MusicBrainzDatabase.get_release_group_albums(
            release_group_id)
        ratings = MusicDatabase.get_albums_ratings(album_ids, user_id)
        if any(x[1] == 'user' for x in ratings.values()):
            return (max(x[0] for x in ratings.values() if x[1] == 'user'),
                    'user')
        kind = 'avg' if any(x[1] == 'avg' for x in ratings.values()) else None
        if ratings:
            return (sum(x[0] for x in ratings.values()) / len(ratings), kind)
        return (5, None)

    @staticmethod
    def add_artist_path(artist_path, image_filename, *, connection=None):
        artist_paths = table('artist_paths')
        i = artist_paths.insert().values(path=artist_path,
                                         image_filename=image_filename)
        if not connection:
            connection = MusicDatabase.getCursor()
        r = connection.execute(i)
        return r.inserted_primary_key[0] if r else None

    @staticmethod
    def set_artist_path_image_filename(artist_path_id, image_filename):
        artist_paths = table('artist_paths')
        u = (artist_paths.update()
             .where(artist_paths.c.id == artist_path_id)
             .values(image_filename=image_filename))
        c = MusicDatabase.getConnection()
        c.execute(u)

    @staticmethod
    def get_artist_path(artist_path_id):
        artist_paths = table('artist_paths')
        s = (select([artist_paths.c.path])
             .where(artist_paths.c.id == artist_path_id))
        c = MusicDatabase.getConnection()
        r = c.execute(s).fetchone()
        return r[0] if r else None

    @staticmethod
    def get_artist_path_id(artist_path):
        artist_paths = table('artist_paths')
        s = (select([artist_paths.c.id])
             .where(artist_paths.c.path == artist_path))
        c = MusicDatabase.getConnection()
        r = c.execute(s).fetchone()
        return r[0] if r else None

    @staticmethod
    def set_artist_path(artist_id, path_id, *, connection=None):
        if not connection:
            connection = MusicDatabase.getCursor()
        artists_mb = table('artists_mb')
        s = select([artists_mb.c.artist_path_id]).where(artists_mb.c.id ==
                                                        artist_id)
        r = connection.execute(s).fetchone()
        if r and r[0] == path_id:
            # print(f'artist {artist_id} already has path {path_id}')
            return
        print(f'Adding path {path_id} to artist {artist_id}')

        u = (artists_mb.update()
             .where(artists_mb.c.id == artist_id)
             .values(artist_path_id=path_id))

        connection.execute(u)

    @staticmethod
    def set_artist_credit_path(artist_credit_ids, path_id,
                               *, connection=None):
        artist_credits_mb = table('artist_credits_mb')
        if not connection:
            connection = MusicDatabase.getCursor()
        for artist_credit_id in artist_credit_ids:
            s = (select([artist_credits_mb.c.artist_path_id])
                 .where(artist_credits_mb.c.artist_credit_id ==
                        artist_credit_id))
            r = connection.execute(s).fetchone()
            if r and r[0] == path_id:
                # print(f'artist credit id {artist_credit_id} '
                #       f'already has path {path_id}')
                continue
            print(f'Adding path {path_id} to artist credit {artist_credit_id}')
            u = (artist_credits_mb.update()
                 .where(artist_credits_mb.c.artist_credit_id ==
                        artist_credit_id)
                 .values(artist_path_id=path_id))
            r = connection.execute(u)
            if r.rowcount == 0:
                i = (artist_credits_mb.insert()
                     .values(artist_credit_id=artist_credit_id,
                             artist_path_id=path_id))
                connection.execute(i)
