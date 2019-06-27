# https://picard.musicbrainz.org/docs/mappings/
from bard.musicdatabase import MusicDatabase, table
from collections import namedtuple
from sqlalchemy import text, insert, select

MBDataTuple = namedtuple('MBDataTuple',
                         ['artistids', 'albumartistids', 'workids',
                          'releasegroupid', 'releaseid', 'releasetrackid',
                          'recordingid', 'confirmed'])


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
    def songTags(songIDs=None):
        c = MusicDatabase.getCursor()
        if songIDs:
            sql = text('SELECT song_id, name, value FROM tags '
                       'WHERE song_id IN :id_list '
                       'ORDER BY song_id, pos')
            result = c.execute(sql, {'id_list': tuple(songIDs)})
        else:
            sql = text('SELECT song_id, name, value FROM tags '
                       'ORDER BY song_id, pos')
            result = c.execute(sql)
        tags = {}
        row = result.fetchone()
        current_song_id = None
        while row:
            if row.song_id != current_song_id:
                if current_song_id:
                    yield current_song_id, tags
                    tags = {}
                current_song_id = row.song_id
            if row.name not in tags:
                tags[row.name] = [row.value]
            else:
                tags[row.name] += [row.value]

            row = result.fetchone()
        if current_song_id:
            yield current_song_id, tags

    @staticmethod
    def insertMBArtistIDs(song_id, artistIDs):
        if not artistIDs:
            return
        songs_mb_artistids = table('songs_mb_artistids')

        s = select([songs_mb_artistids.c.artistid]) \
            .where(songs_mb_artistids.c.song_id == song_id)

        result = MusicDatabase.execute(s).fetchall()

        if set(artistIDs) == set(x['artistid'] for x in result):
            return

        d = songs_mb_artistids.delete() \
                              .where(songs_mb_artistids.c.song_id == song_id)
        MusicDatabase.execute(d)
        for artistID in artistIDs:
            i = insert(songs_mb_artistids).values(song_id=song_id,
                                                  artistid=artistID)
            MusicDatabase.execute(i)

    @staticmethod
    def insertMBAlbumArtistIDs(song_id, albumArtistIDs):
        if not albumArtistIDs:
            return
        songs_mb_albumartistids = table('songs_mb_albumartistids')

        s = select([songs_mb_albumartistids.c.albumartistid]) \
            .where(songs_mb_albumartistids.c.song_id == song_id)

        result = MusicDatabase.execute(s).fetchall()

        if set(albumArtistIDs) == set(x['albumartistid'] for x in result):
            return

        d = songs_mb_albumartistids.delete() \
            .where(songs_mb_albumartistids.c.song_id == song_id)
        MusicDatabase.execute(d)
        for artistID in albumArtistIDs:
            i = insert(songs_mb_albumartistids).values(song_id=song_id,
                                                       albumartistid=artistID)
            MusicDatabase.execute(i)

    @staticmethod
    def insertMBWorkIDs(song_id, workIDs):
        if not workIDs:
            return
        songs_mb_workids = table('songs_mb_workids')

        s = select([songs_mb_workids.c.workid]) \
            .where(songs_mb_workids.c.song_id == song_id)

        result = MusicDatabase.execute(s).fetchall()

        if set(workIDs) == set(x['workid'] for x in result):
            return

        d = songs_mb_workids.delete() \
                            .where(songs_mb_workids.c.song_id == song_id)
        MusicDatabase.execute(d)
        for workID in workIDs:
            i = insert(songs_mb_workids).values(song_id=song_id,
                                                workid=workID)
            MusicDatabase.execute(i)

    @staticmethod
    def insertMusicBrainzTags(song_id, mbIDs):
        MusicBrainzDatabase.insertMBArtistIDs(song_id, mbIDs.artistids)
        MusicBrainzDatabase.insertMBAlbumArtistIDs(song_id,
                                                   mbIDs.albumartistids)
        MusicBrainzDatabase.insertMBWorkIDs(song_id, mbIDs.workids)
        songs_mb = table('songs_mb')
        mbTagRecord = songs_mb.select(songs_mb.c.song_id == song_id)
        mbTagRecord = MusicDatabase.execute(mbTagRecord).fetchone()
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
                MusicDatabase.execute(u)
        else:
            print(f'insert mb data for {song_id}')
            i = songs_mb.insert().values(song_id=song_id,
                                         releasegroupid=mbIDs.releasegroupid,
                                         releaseid=mbIDs.releaseid,
                                         releasetrackid=mbIDs.releasetrackid,
                                         recordingid=mbIDs.recordingid,
                                         confirmed=mbIDs.confirmed)
            MusicDatabase.execute(i)

    @staticmethod
    def songsWithoutMBData():
        c = MusicDatabase.getCursor()
        sql = text('SELECT id FROM songs '
                   'WHERE id NOT IN (select song_id FROM songs_mb) '
                   'ORDER BY id')
        result = c.execute(sql)
        return [x[0] for x in result.fetchall()]

    @staticmethod
    def updateMusicBrainzIDs(songIDs=None):
        if not songIDs:
            return
        for song_id, tags in MusicBrainzDatabase.songTags(songIDs):
            mbIDs = getSongMusicBrainzIDs(song_id, tags)
            if any(mbIDs):
                MusicBrainzDatabase.insertMusicBrainzTags(song_id, mbIDs)
                MusicDatabase.commit()
