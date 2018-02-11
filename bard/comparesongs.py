# -*- coding: utf-8 -*-

from bard.musicdatabase import MusicDatabase
from bard.utils import printSongsInfo
from bard.terminalcolors import TerminalColors
from functools import partial
from contextlib import suppress
from collections import Counter


def most_common(lst):
    if not lst:
        return None
    data = Counter(lst)
    return data.most_common(1)[0][0]


def findPairs(songs1, songs2):
    pairs = {}
    songsRemainingFrom1 = songs1.copy()
    songsRemainingFrom2 = songs2.copy()
    print('Getting pairs from', songs1)
    print(' and              ', songs2)
    for song1 in songs1:
        similarSongsIn2 = []
        for song2 in songs2:
            similarity = MusicDatabase.songsSimilarity(song1.id, song2.id)
            # print(song1.id, song2.id, similarity)
            if similarity >= 0.85:
                similarSongsIn2.append((song2, similarity))
                with suppress(ValueError):
                    songsRemainingFrom1.remove(song1)
                with suppress(ValueError):
                    songsRemainingFrom2.remove(song2)
        if similarSongsIn2:
            pairs[song1] = similarSongsIn2
            if len([x for x in similarSongsIn2 if x[1] == 1.0]) > 1:
                colors = (TerminalColors.WARNING, TerminalColors.ENDC)
                print('%sWARNING: Repeated songs in the same directory!%s' %
                      colors)
                for x in similarSongsIn2:
                    print(x)

    return pairs, songsRemainingFrom1, songsRemainingFrom2


def getUniquePairs(data):
    pairs = []
    print('data', data)
    used = []
    for song1 in data:
        # print('---')
        # print(song1)
        # for s in data[song1]:
        #     print(s)

        candidates = [x for x in data[song1] if x[0] not in used]
        if not candidates:
            colors = (TerminalColors.WARNING, TerminalColors.ENDC)
            print('%sError: Song repeated on first set?%s%s' %
                  (colors[0], colors[1], song1.path()))
            candidates = [x for x in data[song1]]
        song2, similarity = max(candidates, key=lambda x: x[1])
        used.append(song2)
        pairs.append((song1, song2, similarity))

    a = {x[0] for x in pairs}
    b = {x[1] for x in pairs}
#    print(len(a))
#    print(len(b))
#    print(a)
#    print(b)
    for i, x in enumerate(pairs):
        print(i, ')')
        print(x[0].path())
        print(x[1].path())
    if len(a) != len(pairs) or len(b) != len(pairs):
        print('Number of pairs:', len(pairs), '  (%d,%d)' % (len(a), len(b)))
        raise NotImplementedError('getUniquePairs cannot currently handle '
                                  'the case of ' + str(pairs))

    return pairs


def compareSongSets(songs1, songs2, path1, path2):
    interactive = True
    for x in songs1:
        x.loadMetadata()
        x.calculateCompleteness()
    for x in songs2:
        x.loadMetadata()
        x.calculateCompleteness()
    print('songs1', songs1)
    print('songs2', songs2)
    pairs, newSongs1, newSongs2 = findPairs(songs1, songs2)
    print(pairs)
    print(newSongs1)
    print(newSongs2)

    pairs = getUniquePairs(pairs)
    print('-------')
    sourceOfResult = []
    result = []
    source_is_important = False
    colors = (TerminalColors.FAIL, TerminalColors.OKGREEN)
    undecided = []
    for song1, song2, similarity in pairs:
        print(song1.id, song1.path(), ' (completeness: %d)' %
              song1.completeness)
        print(song2.id, song2.path(), ' (completeness: %d)' %
              song2.completeness)
        print('Similarity: ', similarity)
        song1.calculateCompleteness()
        song2.calculateCompleteness()
        take_audio_from = \
            song1.audioCmp(song2, interactive=interactive,
                           printSongsInfoCallback=partial(printSongsInfo,
                                                          useColors=colors))
        if song1.completeness > song2.completeness:
            take_metadata_from = -1
        elif song2.completeness > song1.completeness:
            take_metadata_from = 1
        else:
            take_metadata_from = 0
        print('Better audio:', take_audio_from)

#        if take_audio_from == 0:
#            take_audio_from = most_common(sourceOfResult)
#            if not take_audio_from:
#                take_audio_from = 0
#        else:
        if take_audio_from:
            if undecided:
                idx = {-1: 0, 1: 1}[take_audio_from]
                result = [x[idx] for x in undecided]
                sourceOfResult = [take_audio_from for x in undecided]
                undecided = []
                print('undecided set', sourceOfResult)
            source_is_important = True
            print('source_is_important', take_audio_from)

        if take_audio_from == -1:
            result.append(song1)
            sourceOfResult.append(-1)
            if take_metadata_from == 1:
                colors = (TerminalColors.WARNING, TerminalColors.ENDC)
                print('%sWARNING: Audio is better on first set, but '
                      'metadata is better on second set.%s' % colors)
        elif take_audio_from == 1:
            print(song2.path())
            result.append(song2)
            sourceOfResult.append(1)
            if take_metadata_from == -1:
                colors = (TerminalColors.WARNING, TerminalColors.ENDC)
                print('%sWARNING: Audio is better on second set, but '
                      'metadata is better on first set.%s' % colors)
        else:
            if take_metadata_from != 0:
                colors = (TerminalColors.WARNING, TerminalColors.ENDC)
                which_set = {-1: 'first', 1: 'second'}[take_metadata_from]
                print('%sWARNING: Audio is the same on both sets, but '
                      'metadata is better on the %s set.%s' %
                      (colors[0], which_set, colors[1]))

            if sourceOfResult:
                print('Undecided but there was a previous decision, so reuse that', sourceOfResult[-1])
                print(song1.path(), song2.path())
                result.append({-1: song1, 1: song2}[sourceOfResult[-1]])
                sourceOfResult.append(sourceOfResult[-1])
            else:
                undecided.append((song1, song2))

    if undecided and not result:
        print('undecided', undecided, result)
        result = [x[0] for x in undecided]
        sourceOfResult = [-1 for x in undecided]
    print('---')
    print('undecided:', undecided)
    print('source of result:', sourceOfResult)
    print('pairs:')
    for i, x in enumerate(pairs):
        print(i, x[0].path())
        print(i, x[1].path())

    if not source_is_important:
        colors = (TerminalColors.OKGREEN, TerminalColors.ENDC)
        if not newSongs1 and not newSongs2:
            print('%sBoth sets are interchangeable%s' % colors)
        else:
            print('%sThere are %d interchangeable songs in both sets%s' %
                  (colors[0], len(sourceOfResult), colors[1]))
    elif set(sourceOfResult) == {-1}:
        colors = (TerminalColors.WARNING, TerminalColors.FAIL,
                  TerminalColors.WARNING, TerminalColors.ENDC)
        if not newSongs1 and not newSongs2:
            print('%sBetter source: %sfirst%s set%s' % colors)
        else:
            print('%sBetter source: %sfirst%s set for %d songs%s' %
                  (colors[0], colors[1], colors[2], len(sourceOfResult),
                   colors[3]))
    elif set(sourceOfResult) == {1}:
        colors = (TerminalColors.WARNING, TerminalColors.OKGREEN,
                  TerminalColors.WARNING, TerminalColors.ENDC)
        if not newSongs1 and not newSongs2:
            print('%sBetter source: %ssecond%s set%s' % colors)
        else:
            print('%sBetter source: %ssecond%s set for %d songs%s' %
                  (colors[0], colors[1], colors[2], len(sourceOfResult),
                   colors[3]))
    else:
        colors = (TerminalColors.WARNING, TerminalColors.ENDC)
        print('%sSome songs from the first set and '
              'some songs from the second%s' % colors)

    for song in result:
        print(song.path())
    if newSongs1:
        args = (TerminalColors.WARNING, len(newSongs1),
                TerminalColors.FAIL + 'first' + TerminalColors.WARNING,
                TerminalColors.ENDC)
        print('%sThere are %d original songs in %s set%s' % args)
        for song in newSongs1:
            print(song.path())

    if newSongs2:
        args = (TerminalColors.WARNING, len(newSongs2),
                TerminalColors.OKGREEN + 'second' + TerminalColors.WARNING,
                TerminalColors.ENDC)
        print('%sThere are %d original songs in %s set%s' % args)
        for song in newSongs2:
            print(song.path())

    return result
