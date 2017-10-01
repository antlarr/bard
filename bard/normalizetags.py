# -*- coding: utf-8 -*-

import mutagen
import mutagen.mp3
import mutagen.mp4
import mutagen.easymp4
import mutagen.monkeysaudio
import mutagen.asf
import mutagen.flac
import mutagen.wavpack


def extractFirstElementOfTuple(x):
    if isinstance(x, tuple):
        return x[0]
    return x


tagFilter = {
    mutagen.mp3.MP3: {
        'genre': lambda x: x and x.genres or None},
    mutagen.mp4.MP4: {
        'tracknumber': extractFirstElementOfTuple,
        'trkn': extractFirstElementOfTuple,
        'discnumber': extractFirstElementOfTuple,
        'disk': extractFirstElementOfTuple, }}

tagMaps = {
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
        'date': 'WM/Year', }}


def normalizeTagValue(obj, mutagenFile, tag):
    if isinstance(obj, mutagen.apev2.APETextValue):
        splitted = [x for x in str(obj).split('\x00') if x]
        if len(splitted) == 1:
            return splitted[0]
        return splitted

    if isinstance(obj, mutagen.apev2.APEBinaryValue) or \
       isinstance(obj, mutagen.asf._attrs.ASFByteArrayAttribute) or \
       isinstance(obj, mutagen.mp4.MP4Cover) or \
       isinstance(obj, mutagen.id3.APIC):
        return None

    if hasattr(obj, 'value'):
        return obj.value

    if isinstance(obj, mutagen.mp4.MP4FreeForm):
        return str(obj)

    if isinstance(obj, mutagen.id3.Frame):
        return str(obj)

    try:
        func = tagFilter[type(mutagenFile)][tag]
    except KeyError:
        def func(x):
            return x

    return func(obj)


def normalizeTagValues(values, mutagenFile=None, tag=None):
    if isinstance(values, list):
        return [normalizeTagValue(x, mutagenFile, tag) for x in values if x]
    return normalizeTagValue(values, mutagenFile, tag)


def getTag(mutagenFile, tag):
    if type(mutagenFile) in tagMaps:
        tagMap = tagMaps[type(mutagenFile)]
        result = mutagenFile.get(tagMap.get(tag, tag), None)
    else:
        result = mutagenFile.get(tag, None)

    # print(tag, result, type(result))
    if isinstance(result, list) and len(result) == 1:
        result = result[0]
    # print(tag, result, type(result))

    result = normalizeTagValues(result, mutagenFile, tag)
    return result
