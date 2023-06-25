from bard.musicdatabase import MusicDatabase
from sqlalchemy import text
from bard.playlist import Playlist, PlaylistTypes
from bard.searchplaylist import SearchPlaylist
from bard.generatedplaylist import GeneratedPlaylist
from bard.searchquery import SearchQuery
import itertools


class PlaylistManager:
    search_id_seq = itertools.count()

    def __init__(self):
        """Create a PlaylistManager object."""
        self.searchPlaylists = {}
        self.searchQueriesMap = {}

    @staticmethod
    def load_playlist_from_db(where_clause='', where_values=None, tables=[],
                              order_by=None, limit=None):
        c = MusicDatabase.getCursor()

        if 'playlists' not in tables:
            tables.insert(0, 'playlists')

        statement = ('SELECT id, name, owner_id, playlist_type FROM %s %s' %
                     (','.join(tables), where_clause))

        if order_by:
            statement += ' ORDER BY %s' % order_by

        if limit:
            statement += ' LIMIT %d' % limit

        if where_values:
            result = c.execute(text(statement).bindparams(**where_values))
        else:
            result = c.execute(text(statement))

        pltype = {1: Playlist, 4: GeneratedPlaylist}
        return [pltype[x.playlist_type](db_row=x)
                for x in result.fetchall()]

    @staticmethod
    def load_id_from_db(playlistID, ownerID=None):
        where = ['id = :id']
        values = {'id': playlistID}

        if ownerID:
            where.append('owner_id = :owner_id')
            values['owner_id'] = ownerID

        where = 'WHERE ' + ' AND '.join(where)
        r = PlaylistManager.load_playlist_from_db(where, values)
        return r[0] if r else None

    def get_playlist(self, playlistGID, userID):
        if playlistGID['type'] == PlaylistTypes.User.value:
            return PlaylistManager.load_id_from_db(playlistGID['playlistID'],
                                                   userID)

        # if playlistGID['type'] == PlaylistTypes.Album.value:
        #     return Album.load_id_from_db(playlistGID['albumID'], userID)

        if playlistGID['type'] == PlaylistTypes.Search.value:
            try:
                return self.searchPlaylists[playlistGID['id']]
            except KeyError:
                return None

        return None

    def get_user_playlist(self, playlistID, userID):
        return PlaylistManager.load_id_from_db(playlistID, userID)

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
