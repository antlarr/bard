from bard.playlist import Playlist
from bard.musicdatabase_songs import getMusic
from bard.musicdatabase import MusicDatabase, DatabaseEnum, table
import numpy


def normalized(v):
    s = sum(v)
    return map(lambda x: x / s, v)


class GeneratedPlaylist(Playlist):
    def __init__(self, generator=None, db_row=None, owner_id=None):
        """Create a GeneratedPlaylist object."""
        super(GeneratedPlaylist, self).__init__(db_row=db_row,
                                                owner_id=owner_id)
        self.playlist_type = DatabaseEnum('playlist_type').id_value(
            'generated')
        # self.store_songs_in_db = False
        if not generator:
            generator = "shuffle"
        self.generator = generator
        print(f'generatedPlaylist generator: {generator}')
        if not db_row:
            self.generate_new_songs(30)

    def create_in_db(self):
        super(GeneratedPlaylist, self).create_in_db()

        c = MusicDatabase.getCursor()
        t = table('playlist_generators')
        data = {'playlist_id': self.id,
                'generator': self.generator}

        MusicDatabase.insert_or_update(t, data,
                                       t.c.playlist_id == self.id,
                                       connection=c)
        c.commit()

    def generate_new_songs(self, count):
        songs = getMusic('WHERE songs_mb.song_id = id', tables=['songs_mb'])
        ids = []
        probabilities = []
        for song in songs:
            ids.append(song.id)
            probabilities.append(song.userRating(self.owner_id) * 1000)

        ids = numpy.random.choice(ids, count, replace=False,
                                  p=list(normalized(probabilities)))
        for song_id in ids:
            self.append_song(int(song_id))

    def get_next_song(self, index):
        print(f'requested next song: {index} {len(self.songs)}')
        if index >= len(self.songs) - 2:
            self.generate_new_songs(30)

        index += 1
        return (self.songs[index][0], index)
