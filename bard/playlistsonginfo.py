from bard.playlist import Playlist, PlaylistTypes
from bard.bard import bard
from bard.musicdatabase import MusicDatabase


class PlaylistSongInfo:
    def __init__(self, **kwargs):
        """Create a playlistSongInfo object from a flask request."""
        self.vars = kwargs

    def __getattr__(self, attr):
        return self.vars[attr]

    @staticmethod
    def from_request(request):
        # playlistSongInfo= {'playlist_type': 'album',
        #                    'album_id': 1,
        #                    'medium_number': 2,
        #                    'track_position': 3}
        # playlistSongInfo= {'playlist_type': 'user',
        #                    'playlist_id': 1,
        #                    'index': 2}
        # playlistSongInfo= {'playlist_type': 'search',
        #                    'search_playlist_id': 1,
        #                    'index': 2}
        r = {}
        r['playlist_type'] = PlaylistTypes(request.form['playlist_type'])

        try:
            r['song_id'] = request.form['song_id']
        except KeyError:
            r['song_id'] = None

        if r['playlist_type'] == PlaylistTypes.User:
            r['playlist_id'] = int(request.form['playlist_id'])
            r['index'] = int(request.form['index'])

        elif r['playlist_type'] == PlaylistTypes.Album:
            r['album_id'] = int(request.form['album_id'])
            r['medium_number'] = int(request.form['medium_number'])
            r['track_position'] = int(request.form['track_position'])

        elif r['playlist_type'] == PlaylistTypes.Search:
            r['search_playlist_id'] = int(request.form['search_playlist_id'])
            r['index'] = int(request.form['index'])

        return PlaylistSongInfo(**r)

    def set_current_user(self, user_id):
        self.user_id = user_id

    def next_song(self):
        if self.playlist_type == PlaylistTypes.User:
            plman = bard.playlist_manager
            playlist = plman.load_id_from_db(self.playlist_id, self.user_id)
            print('NEXT', playlist, self.playlist_id)
            r = playlist.get_next_song(self.index)
            if not r:
                return None
            song_id, idx = r
            result = {'song_id': song_id,
                      'playlist_type': self.playlist_type,
                      'playlist_id': self.playlist_id,
                      'index': idx}
        elif self.playlist_type == PlaylistTypes.Album:
            r = MusicDatabase.get_next_album_song(self.album_id,
                                                  self.medium_number,
                                                  self.track_position)
            if not r:
                return None
            result = {'song_id': r['song_id'],
                      'playlist_type': self.playlist_type,
                      'album_id': self.album_id,
                      'medium_number': r['medium_number'],
                      'track_position': r['track_position']}
        elif self.playlist_type == PlaylistTypes.Search:
            plman = bard.playlist_manager
            pl = plman.get_search_playlist(self.search_playlist_id,
                                           self.user_id)
            if not pl:
                return None

            r = pl.get_next_song(self.index)
            if not r:
                return None

            song_id, idx = r
            result = {'song_id': song_id,
                      'playlist_type': self.playlist_type,
                      'search_playlist_id': self.search_playlist_id,
                      'index': idx}
        return PlaylistSongInfo(**result)

    def as_dict(self):
        return {k: v if not isinstance(v, PlaylistTypes) else v.value
                for k, v in self.vars.items()}
