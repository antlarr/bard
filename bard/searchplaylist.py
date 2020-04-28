from bard.playlist import Playlist
import itertools


class SearchPlaylist(Playlist):
    id_sequence = itertools.count()

    def __init__(self, query):
        """Create a SearchPlaylist object."""
        super(SearchPlaylist, self).__init__(None,
                                             owner_id=query.owner_id)
        self.query = query
        self.searchPlaylistID = next(SearchPlaylist.id_sequence)
        print(f'searchPlaylistID: {self.searchPlaylistID}')

    def append_song(self, song_id):
        self.songs.append((song_id, None))

    def get_next_song(self, index):
        if index >= len(self.songs) - 1:
            return None

        index += 1
        return (self.songs[index][0], index)
