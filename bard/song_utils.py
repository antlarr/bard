from bard.utils import printProperties, simple_find_matching_square_bracket, \
    formatLength, alignColumns, getPropertiesAsString
from bard.song import DifferentLengthException, CantCompareSongsException
from bard.terminalcolors import TerminalColors
from bard.musicdatabase import MusicDatabase
from bard.musicdatabase_songs import getSongs
from bard.analysis_database import AnalysisDatabase
import os
import re


def get_probability_color(prob, prob_from_0_5=False):
    if prob_from_0_5:
        prob = (prob - 0.5) * 2
    if prob >= 0.98:
        return TerminalColors.White
    return TerminalColors.Gradient[int(prob * 10)]


def print_song_info(song, userID=None, print_analysis=True):
    song.loadMetadataInfo()
    print("----------")
    try:
        filesize = "%d bytes" % os.path.getsize(song.path())
    except FileNotFoundError:
        filesize = "File not found"
    print("%s (%s)" % (song.path(), filesize))
    print("song id:", song.id)

    rating = song.userRating(userID)
    if rating:
        print("my rating:", '*' * rating, '(%d/10)' % rating)
    avgrating = song.avgRating(userID)
    if avgrating:
        print("avg rating:", '*' * avgrating, '(%d/10)' % avgrating)

    if not rating and not avgrating:
        rating = song.rating(userID)
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

    if print_analysis:
        print_song_info_analysis(song)

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


def print_song_info_analysis(song):
    analysis = AnalysisDatabase.songAnalysis(song.id)
    if not analysis:
        return
    # print(dir(analysis))
    # print(analysis.keys())
    # print(analysis)
    options = {'danceable': ('danceable', 'not danceable'),
               'gender_female': ('female', 'male'),
               'acoustic': ('acoustic', 'not acoustic'),
               'aggressive': ('aggresive', 'not aggresive'),
               'electronic': ('electronic', 'not electronic'),
               'happy': ('happy', 'not happy'),
               'party': ('party', 'not party'),
               'relaxed': ('relaxed', 'not relaxed'),
               'sad': ('sad', 'not sad'),
               'bright': ('bright', 'dark'),
               'atonal': ('atonal', 'tonal'),
               'instrumental': ('instrumental', 'voice')}
    for opt, values in options.items():
        if (opt == 'gender_female' and
                analysis['highlevel']['instrumental'] > 0.95):
            continue

        first = analysis['highlevel'][opt] >= 0.5
        v = values[0] if first else values[1]
        prob = (analysis["highlevel"][opt] if first else
                1 - analysis["highlevel"][opt])
        color = get_probability_color(prob, prob_from_0_5=True)
        print(f'{opt}: {color}{v}{TerminalColors.ENDC} ({prob:.3f})')

    options = ['genre_dortmund', 'genre_electronic', 'genre_rosamerica',
               'genre_tzanetakis', 'ismir04_rhythm', 'moods_mirex']
    for opt in options:
        prob = analysis['highlevel'][opt]['probability']
        value = analysis['highlevel'][opt]['value']
        color = get_probability_color(prob)
        indent = ' ' * (len(opt) + 2)
        first = True
        for k, p in analysis['highlevel'][opt]['all'].items():
            sel = '* ' if k == value else '  '
            color = get_probability_color(p)
            head = f'{opt}: ' if first else indent
            print(f'{head}{color}{sel}{k}{TerminalColors.ENDC} ({p:.3f})')
            first = False

    options = [('lowlevel', 'average_loudness'),
               ('lowlevel', 'dynamic_complexity'),
               ('rhythm', 'beats_count'),
               ('rhythm', 'bpm'),
               ('rhythm', 'danceability'),
               ('rhythm', 'onset_rate'),
               ('tonal', 'chords_changes_rate'),
               ('tonal', 'chords_number_rate'),
               ('tonal', 'tuning_frequency')]
    for k1, k2 in options:
        print(f'{k2}: {analysis[k1][k2]}')

    tonal = analysis['tonal']
    print(f'chords_key/scale: {tonal["chords_key"]} {tonal["chords_scale"]}')
    indent_len = len('chords_key/scale: ')
    for k in ['key_edma', 'key_krumhansl', 'key_temperley']:
        key = tonal[k]
        indent = ' ' * (indent_len - len(k) - 1)
        print(f"{k}:{indent}{key['key']} {key['scale']} ({key['strength']})")
