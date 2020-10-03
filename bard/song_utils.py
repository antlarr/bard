from bard.utils import printProperties, simple_find_matching_square_bracket, \
    formatLength, alignColumns, getPropertiesAsString
from bard.song import DifferentLengthException, CantCompareSongsException
from bard.terminalcolors import TerminalColors
from bard.musicdatabase import MusicDatabase
from bard.musicdatabase_songs import getSongs
import os
import re


def print_song_info(song, userID=None):
    song.loadMetadataInfo()
    print("----------")
    try:
        filesize = "%d bytes" % os.path.getsize(song.path())
    except FileNotFoundError:
        filesize = "File not found"
    print("%s (%s)" % (song.path(), filesize))
    print("song id:", song.id)
    rating = song.userRating(userID)
    print("rating:", '*' * rating, '(%d/10)' % rating)
    for k in sorted(song.metadata):
        v = song.metadata[k]
        print(TerminalColors.Header + str(k) + TerminalColors.ENDC +
              ' : ' + str(v)[:100])
        if k in ('TMCL', 'TIPL'):
            if len(v) > 1:
                print('*** More than one %s tag in file: ' +
                      'The following list might be incomplete ***')
            txt_repr = v[0]
            m = re.search(r'people=', txt_repr)
            if m:
                pos_bracket = simple_find_matching_square_bracket(
                    txt_repr, m.end())
                txt = txt_repr[m.end():pos_bracket + 1]
                list_artists = eval(txt)
                for instrument, artist in list_artists:
                    print('    %s : %s' % (instrument, artist))

    print("file sha256sum: ", song.fileSha256sum())
    print("audio track sha256sum: ", song.audioSha256sum())

    print('duration: %s s' % formatLength(song.duration()))
    print(('duration without silences: %s s' %
           formatLength(song.durationWithoutSilences())),
          ' (silences: %s + %s)' %
          (formatLength(song.silenceAtStart()),
           formatLength(song.silenceAtEnd())))
    printProperties(song)
    if song.coverWidth():
        print('cover:  %dx%d' %
              (song.coverWidth(), song.coverHeight()))

    similar_pairs = MusicDatabase.getSimilarSongsToSongID(song.id)
    if similar_pairs:
        print('Similar songs:')

    similarSongs = []
    for otherID, offset, similarity in similar_pairs:
        otherSong = getSongs(songID=otherID)[0]
        try:
            audioComparison = song.audioCmp(otherSong,
                                            interactive=False)
        except (DifferentLengthException):
            audioComparison = 2
            colors = {'length': TerminalColors.Magenta}
        except (CantCompareSongsException):
            audioComparison = 3
            colors = {}
        else:
            colors = {}
        colors['bitrate'] = TerminalColors.Blue
        propertiesString = getPropertiesAsString(otherSong, colors)
        color = {-1: TerminalColors.Worse,
                 0: TerminalColors.ENDC,
                 1: TerminalColors.Better,
                 2: TerminalColors.DifferentLength,
                 3: TerminalColors.CantCompareSongs}[audioComparison]
        songpath = (color + ' %d ' % otherID + otherSong.path() +
                    TerminalColors.ENDC)
        songprop = '(%d %f %s)' % (offset, similarity,
                                   propertiesString)
        similarSongs.append([songpath] + songprop.split())
    aligned = alignColumns(similarSongs)
    for line in aligned:
        print(line)
