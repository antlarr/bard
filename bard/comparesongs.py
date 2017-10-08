# -*- coding: utf-8 -*-

from bard.musicdatabase import MusicDatabase
from contextlib import suppress


def findPairs(songs1, songs2):
    pairs = {}
    songsRemainingFrom1 = songs1.copy()
    songsRemainingFrom2 = songs2.copy()
    for song1 in songs1:
        similarSongsIn2 = []
        for song2 in songs2:
            similarity = MusicDatabase.songsSimilarity(song1.id, song2.id)
            if similarity >= 0.85:
                similarSongsIn2.append((song2, similarity))
                with suppress(ValueError):
                    songsRemainingFrom1.remove(song1)
                with suppress(ValueError):
                    songsRemainingFrom2.remove(song2)
        if similarSongsIn2:
            pairs[song1] = similarSongsIn2

    return pairs, songsRemainingFrom1, songsRemainingFrom2


def getUniquePairs(data):
    pairs = []
    for song1 in data:
        song2, similarity = max(data[song1], key=lambda x: x[1])
        pairs.append((song1, song2, similarity))

    return pairs


def compareSongSets(songs1, songs2, path1, path2):
    pairs, newSongs1, newSongs2 = findPairs(songs1, songs2)
    print(pairs)
    print(newSongs1)
    print(newSongs2)

    pairs = getUniquePairs(pairs)
    print('---')
    for song1, song2, similarity in pairs:
        print(song1.id, song2.id, similarity)
    print('---')
