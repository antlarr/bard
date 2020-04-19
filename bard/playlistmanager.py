# from bard.musicdatabase import MusicDatabase, DatabaseEnum, table
# from bard.config import config
# from sqlalchemy import text, exc, select, and_
# from sqlalchemy.engine.result import RowProxy
from bard.playlist import Playlist, PlaylistTypes
from bard.searchplaylist import SearchPlaylist
from bard.searchquery import SearchQuery
import itertools


class PlaylistManager:
    search_id_seq = itertools.count()

    def __init__(self):
        """Create a PlaylistManager object."""
        self.searchPlaylists = {}
        self.searchQueriesMap = {}

    def get_playlist(self, playlistGID, userID):
        if playlistGID['type'] == PlaylistTypes.User.value:
            return Playlist.load_id_from_db(playlistGID['playlistID'], userID)

        # if playlistGID['type'] == PlaylistTypes.Album.value:
        #     return Album.load_id_from_db(playlistGID['albumID'], userID)

        if playlistGID['type'] == PlaylistTypes.Search.value:
            try:
                return self.searchPlaylists[playlistGID['id']]
            except KeyError:
                return None

        return None

    def get_user_playlist(self, playlistID, userID):
        return Playlist.load_id_from_db(playlistID, userID)

    def get_search_playlist(self, spid, userID):
        try:
            pl = self.searchPlaylists[spid]
        except KeyError:
            print(f'SearchPlaylist {spid} not found')
            return None

        if pl.owner_id == userID:
            return pl
        print(f'User does not have access to searchPlaylist {spid}')
        return None

    def get_search_result_playlist(self, sq: SearchQuery):
        if sq.search_playlist_id:
            return self.get_search_playlist(sq.search_playlist_id,
                                            sq.owner_id)
        try:
            spid = self.searchQueriesMap[sq.key()]
            return self.searchPlaylists[spid]
        except KeyError:
            return None

    def add_search_playlist(self, playlist: SearchPlaylist):
        spid = playlist.searchPlaylistID
        self.searchQueriesMap[playlist.query.key()] = spid
        self.searchPlaylists[spid] = playlist
        return playlist
