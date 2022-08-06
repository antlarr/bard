# -*- coding: utf-8 -*-

import mutagen
import mutagen.mp3
import mutagen.mp4
import mutagen.easymp4
import mutagen.monkeysaudio
import mutagen.asf
import mutagen.flac
import mutagen.wavpack
import mutagen.oggvorbis
import mutagen.oggopus
import mutagen.musepack
import mutagen.wave
import mutagen.dsf


def extractFirstElementOfTuple(x):
    if isinstance(x, tuple):
        return x[0]
    if isinstance(x, str):
        return x.split('/')[0]
    return x


tag_filter = {
    mutagen.mp3.MP3: {
        'genre': lambda x: x and x.genres or None},
    mutagen.mp4.MP4: {
        'tracknumber': extractFirstElementOfTuple,
        'trkn': extractFirstElementOfTuple,
        'discnumber': extractFirstElementOfTuple,
        'disk': extractFirstElementOfTuple, },
    mutagen.flac.FLAC: {
        'tracknumber': extractFirstElementOfTuple,
        'discnumber': extractFirstElementOfTuple, }}

tag_maps = {
    mutagen.mp3.MP3: {
        'album': 'TALB',
        'bpm': 'TBPM',
        'compilation': 'TCMP',  # iTunes extension
        'composer': 'TCOM',
        'copyright': 'TCOP',
        'encodedby': 'TENC',
        'genre': 'TCON',
        'lyricist': 'TEXT',
        'length': 'TLEN',
        'media': 'TMED',
        'mood': 'TMOO',
        'title': 'TIT2',
        'version': 'TIT3',
        'artist': 'TPE1',
        'albumartist': 'TPE2',
        'conductor': 'TPE3',
        'arranger': 'TPE4',
        'discnumber': 'TPOS',
        'organization': 'TPUB',
        'tracknumber': 'TRCK',
        'author': 'TOLY',
        'albumartistsort': 'TSO2',  # iTunes extension
        'albumsort': 'TSOA',
        'composersort': 'TSOC',  # iTunes extension
        'artistsort': 'TSOP',
        'titlesort': 'TSOT',
        'isrc': 'TSRC',
        'discsubtitle': 'TSST',
        'language': 'TLAN', },
    # mutagen.mp3.EasyMP3: {
    #     },
    # mutagen.easymp4.EasyMP4: {
    #     },
    mutagen.mp4.MP4: {
        'title': '\xa9nam',
        'album': '\xa9alb',
        'artist': '\xa9ART',
        'albumartist': 'aART',
        'date': '\xa9day',
        'comment': '\xa9cmt',
        'description': 'desc',
        'grouping': '\xa9grp',
        'genre': '\xa9gen',
        'copyright': 'cprt',
        'albumsort': 'soal',
        'albumartistsort': 'soaa',
        'artistsort': 'soar',
        'titlesort': 'sonm',
        'composersort': 'soco',
        'musicbrainz_artistid': 'MusicBrainz Artist Id',
        'musicbrainz_trackid': 'MusicBrainz Track Id',
        'musicbrainz_albumid': 'MusicBrainz Album Id',
        'musicbrainz_albumartistid': 'MusicBrainz Album Artist Id',
        'musicip_puid': 'MusicIP PUID',
        'musicbrainz_albumstatus': 'MusicBrainz Album Status',
        'musicbrainz_albumtype': 'MusicBrainz Album Type',
        'releasecountry': 'MusicBrainz Release Country',
        'bpm': 'tmpo',
        'tracknumber': 'trkn',
        'discnumber': 'disk', },
    mutagen.flac.FLAC: {
        'album': 'album',
        'albumartist': 'albumartist',
        'albumgenre': 'album genre',
        'artist': 'artist',
        'composer': 'composer',
        'discnumber': 'discnumber',
        'genre': 'genre',
        'label': 'label',
        'language': 'language',
        'musicbrainz_artistid': 'musicbrainz_artistid',
        'musicbrainz_albumid': 'musicbrainz_albumid',
        'musicbrainz_albumartistid': 'musicbrainz_albumartistid',
        'musicbrainz_releasetrackid': 'musicbrainz_releasetrackid',
        'musicbrainz_trackid': 'musicbrainz_trackid',
        'date': 'originaldate',
        'title': 'title',
        'tracknumber': 'tracknumber', },
    mutagen.oggvorbis.OggVorbis: {
        'album': 'album',
        'albumartist': 'albumartist',
        'albumgenre': 'album genre',
        'artist': 'artist',
        'composer': 'composer',
        'discnumber': 'discnumber',
        'genre': 'genre',
        'label': 'label',
        'language': 'language',
        'musicbrainz_artistid': 'musicbrainz_artistid',
        'musicbrainz_albumid': 'musicbrainz_albumid',
        'musicbrainz_albumartistid': 'musicbrainz_albumartistid',
        'musicbrainz_releasetrackid': 'musicbrainz_releasetrackid',
        'musicbrainz_trackid': 'musicbrainz_trackid',
        # 'date': 'originaldate',
        'title': 'title',
        'tracknumber': 'tracknumber', },
    mutagen.oggopus.OggOpus: {
        'album': 'album',
        'albumartist': 'albumartist',
        # 'albumgenre': 'album genre',
        'artist': 'artist',
        'composer': 'composer',
        'discnumber': 'discnumber',
        'genre': 'genre',
        'label': 'label',
        'language': 'language',
        'musicbrainz_artistid': 'musicbrainz_artistid',
        'musicbrainz_albumid': 'musicbrainz_albumid',
        'musicbrainz_albumartistid': 'musicbrainz_albumartistid',
        'musicbrainz_releasetrackid': 'musicbrainz_releasetrackid',
        'musicbrainz_trackid': 'musicbrainz_trackid',
        'title': 'title',
        'tracknumber': 'tracknumber', },
    mutagen.monkeysaudio.MonkeysAudio: {
        'album': 'Album',
        'albumartist': 'Album Artist',
        'albumgenre': 'Album genre',
        'artist': 'Artist',
        'composer': 'Composer',
        'discnumber': 'Disc',
        'genre': 'Genre',
        'label': 'Label',
        'language': 'Language',
        'musicbrainz_artistid': 'Musicbrainz_Artistid',
        'musicbrainz_albumid': 'Musicbrainz_Albumid',
        'musicbrainz_albumartistid': 'Musicbrainz_Albumartistid',
        'musicbrainz_releasetrackid': 'musicbrainz_releasetrackid',
        'musicbrainz_trackid': 'musicbrainz_trackid',
        'date': 'Originaldate',
        'title': 'Title',
        'tracknumber': 'Track', },
    mutagen.wavpack.WavPack: {
        'album': 'Album',
        'albumartist': 'Album Artist',
        'albumgenre': 'Album genre',
        'artist': 'Artist',
        'composer': 'Composer',
        'discnumber': 'Disc',
        'genre': 'Genre',
        'label': 'Label',
        'language': 'Language',
        'musicbrainz_artistid': 'Musicbrainz_Artistid',
        'musicbrainz_albumid': 'Musicbrainz_Albumid',
        'musicbrainz_albumartistid': 'Musicbrainz_Albumartistid',
        'musicbrainz_releasetrackid': 'musicbrainz_releasetrackid',
        'musicbrainz_trackid': 'musicbrainz_trackid',
        'date': 'Originaldate',
        'title': 'Title',
        'tracknumber': 'Track', },
    mutagen.asf.ASF: {
        'artist': 'Author',
        'copyright': 'Copyright',
        'description': 'Description',
        'rating': 'Rating',
        'title': 'Title',
        'albumartist': 'WM/AlbumArtist',
        'album': 'WM/AlbumTitle',
        'composer': 'WM/Composer',
        'genre': 'WM/Genre',
        'label': 'WM/Provider',
        'publisher': 'WM/Publisher',
        'tracknumber': 'WM/TrackNumber',
        'date': 'WM/Year', },
    mutagen.musepack.Musepack: {
        'album': 'Album',
        'albumartist': 'Album Artist',
        'albumgenre': 'Album genre',
        'artist': 'Artist',
        'composer': 'Composer',
        'discnumber': 'Disc',
        'genre': 'Genre',
        'label': 'Label',
        'language': 'Language',
        'musicbrainz_artistid': 'Musicbrainz_Artistid',
        'musicbrainz_albumid': 'Musicbrainz_Albumid',
        'musicbrainz_albumartistid': 'Musicbrainz_Albumartistid',
        'musicbrainz_releasetrackid': 'musicbrainz_releasetrackid',
        'musicbrainz_trackid': 'musicbrainz_trackid',
        'date': 'Originaldate',
        'title': 'Title',
        'tracknumber': 'Track', }}
tag_maps[mutagen.wave.WAVE] = tag_maps[mutagen.mp3.MP3]
tag_maps[mutagen.dsf.DSF] = tag_maps[mutagen.mp3.MP3]


format_to_type = {
    'mp3': mutagen.mp3.MP3,
    'mp4': mutagen.mp4.MP4,
    'asf': mutagen.asf.ASF,
    'flac': mutagen.flac.FLAC,
    'ogg': mutagen.oggvorbis.OggVorbis,
    'opus': mutagen.oggopus.OggOpus,
    'wv': mutagen.wavpack.WavPack,
    'ape': mutagen.monkeysaudio.MonkeysAudio,
    'mpc': mutagen.musepack.Musepack,
    'wav': mutagen.wave.WAVE,
    'dsf': mutagen.dsf.DSF}


def removeFromNullChar(s):
    pos = s.find('\x00')
    if pos >= 0:
        return s[:pos]
    return s


def normalizeTagName(obj, mutagenFile, tag):
    if isinstance(obj, mutagen.id3.PRIV):
        return 'PRIV:' + obj.owner
    if isinstance(obj, mutagen.id3.APIC):
        return 'APIC'
    if isinstance(obj, mutagen.id3.COMM):
        return 'COMM:%s:%s' % (removeFromNullChar(obj.desc),
                               removeFromNullChar(obj.lang))
    return tag


def normalizeTagValue(obj, mutagenFile, tag,  # noqa: C901
                      removeBinaryData=False):
    if isinstance(obj, mutagen.apev2.APETextValue):
        splitted = [x for x in str(obj).split('\x00') if x]
        if len(splitted) == 1:
            if tag in ('tracknumber', 'discnumber'):
                return splitted[0].split('/')[0]
            return splitted[0]
        return splitted

    if (removeBinaryData and
        (isinstance(obj, mutagen.apev2.APEBinaryValue) or
         isinstance(obj, mutagen.asf._attrs.ASFByteArrayAttribute) or
         isinstance(obj, mutagen.mp4.MP4Cover) or
         isinstance(obj, mutagen.id3.APIC) or
         isinstance(obj, mutagen.id3.PRIV) or
         isinstance(obj, mutagen.id3.MCDI) or
         isinstance(obj, mutagen.id3.SYTC) or
         isinstance(obj, mutagen.id3.GEOB) or
         isinstance(obj, mutagen.id3.AENC) or
         isinstance(obj, mutagen.id3.ENCR) or
         (isinstance(mutagenFile, mutagen.flac.FLAC) and tag == 'coverart'))):
        return None

    if isinstance(obj, mutagen.id3.UFID):
        if isinstance(obj.data, bytes):
            try:
                return obj.data.decode('utf-8').strip('\x00')
            except UnicodeDecodeError:
                print('Binary data found in UFID tag', obj.data)
                return 'Binary data'
        return obj.data

    if hasattr(obj, 'value'):
        return obj.value

    if isinstance(obj, mutagen.mp4.MP4FreeForm):
        try:
            if obj.FORMAT_TEXT == mutagen.mp4.AtomDataType.UTF8:
                return obj.decode('utf-8').replace('\x00', '')
            elif obj.FORMAT_TEXT == mutagen.mp4.AtomDataType.UTF16:
                return obj.decode('utf-16').replace('\x00', '')
        except UnicodeDecodeError:
            print(f'Wrong unicode data found in tag {tag}: {obj}')
            return None
        return str(obj)

    # Allow multiple values (lists) on these id3 tags:
    if isinstance(obj, (mutagen.id3.TCON, mutagen.id3.TPUB, mutagen.id3.TSRC,
                        mutagen.id3.TSOC, mutagen.id3.TCOM, mutagen.id3.TEXT,
                        mutagen.id3.TPE3, mutagen.id3.TPE4, mutagen.id3.TLAN,
                        mutagen.id3.TMOO, mutagen.id3.TIT1)):
        return obj.text

    if isinstance(obj, (mutagen.id3.TMCL, mutagen.id3.TIPL)):
        return [role + ':' + name for role, name in obj.people]

    if isinstance(obj, mutagen.id3.COMM):
        text = obj.text
        if isinstance(text, list):
            text = ','.join(text)
        return text

    # Allow multiple values (lists) on these id3 text tags:
    if (isinstance(obj, mutagen.id3.TXXX) and
        obj.desc.lower() in ['musicbrainz album type',
                             'musicbrainz artist id',
                             'musicbrainz album artist id',
                             'musicbrainz work id',
                             'author',
                             'artists',
                             'genre',
                             'writer',
                             'work',
                             'performer',
                             'license',
                             'catalognumber',
                             'style',
                             'comment']):
        return obj.text

    if isinstance(obj, (mutagen.id3.TRCK, mutagen.id3.TPOS)):
        text = obj.text
        if isinstance(text, list):
            text = text[0]
        return text.split('/')[0]

    if isinstance(obj, mutagen.id3.Frame):
        return str(obj)

    if isinstance(obj, str):
        obj = obj.strip('\x00')

    try:
        func = tag_filter[type(mutagenFile)][tag]
    except KeyError:
        def func(x):
            return x

    return func(obj)


def normalizeTagValues(values, mutagenFile=None, tag=None,
                       removeBinaryData=False):
    if isinstance(values, list):
        return (normalizeTagName(values, mutagenFile, tag),
                [normalizeTagValue(x, mutagenFile, tag,
                 removeBinaryData=removeBinaryData) for x in values if x])
    return (normalizeTagName(values, mutagenFile, tag),
            normalizeTagValue(values, mutagenFile, tag,
                              removeBinaryData=removeBinaryData))


def normalizeMetadataDictionary(metadata, mutagenFile=None,
                                removeBinaryData=False):
    r = {}
    for k, v in metadata.items():
        key, values = normalizeTagValues(v, mutagenFile, k, removeBinaryData)
        r[key] = values

    return r


def getTag(mutagenFile, tag, fileformat=None):
    if not mutagenFile:
        return None

    if fileformat:
        typeOfFile = format_to_type[fileformat]
    else:
        typeOfFile = type(mutagenFile)

    if typeOfFile in tag_maps:
        tagMap = tag_maps[typeOfFile]
        result = mutagenFile.get(tagMap.get(tag, tag), None)
    else:
        result = mutagenFile.get(tag, None)

    # print(tag, result, type(result))
    if isinstance(result, list) and len(result) == 1:
        result = result[0]
    # print(tag, result, type(result))

    tag, result = normalizeTagValues(result, mutagenFile, tag,
                                     removeBinaryData=False)
    return result
