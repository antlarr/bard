from bard.musicdatabase import MusicDatabase, DatabaseEnum, table
from bard.config import config
from sqlalchemy import text, exc, select, and_
import sqlite3
from sqlalchemy.engine.result import RowProxy


class Playlist:
    def __init__(self, x, owner_id=None):
        """Create a Playlist object."""
        self.id = None
        self.name = None
        if not owner_id:
            username = config['username']
            self.owner_id = MusicDatabase.getUserID(username)
        else:
            self.owner_id = owner_id
        self.playlist_type = DatabaseEnum('playlist_type').id_value('user')
        self.songs = []

        if isinstance(x, (sqlite3.Row, RowProxy, dict)):
            self.id = x['id']
            self.name = x['name']
            self.owner_id = x['owner_id']

            self.load_playlist_songs()

    @staticmethod
    def load_from_db(where_clause='', where_values=None, tables=[],
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
            print(statement)
            print(where_values)
            result = c.execute(text(statement).bindparams(**where_values))
        else:
            result = c.execute(text(statement))

        r = [Playlist(x) for x in result.fetchall()]
        return r

    @staticmethod
    def load_id_from_db(playlistID, ownerID=None):
        where = ['id = :id']
        values = {'id': playlistID}

        if ownerID:
            where.append('owner_id = :owner_id')
            values['owner_id'] = ownerID

        where = 'WHERE ' + ' AND '.join(where)
        r = Playlist.load_from_db(where, values)
        return r[0] if r else None

    def load_playlist_songs(self):
        c = MusicDatabase.getCursor()
        sql = ('SELECT song_id, recording_mbid, pos '
               'FROM playlist_songs '
               'WHERE playlist_id = :id '
               'ORDER BY pos')
        result = c.execute(text(sql).bindparams(id=self.id))
        self.songs = []
        for idx, x in enumerate(result.fetchall()):
            song_id, recording_mbid, pos = x
            # song = getSongs(songID=song_id)[0]
            if idx != pos:
                print('ERROR: playlist items in the database are '
                      'not correctly positioned')
            item = (song_id, recording_mbid)
            self.songs.append(item)

    def set_name(self, name):
        self.name = name
        if self.id:
            c = MusicDatabase.getCursor()
            sql = text('UPDATE playlists SET name = :name WHERE id = :id')
            c.execute(sql.bindparams(name=self.name, id=self.id))
            c.commit()

    def create_in_db(self):
        if self.id:
            return
        c = MusicDatabase.getCursor()
        sql = text('INSERT INTO playlists (name, owner_id, playlist_type)'
                   'VALUES (:name, :owner_id, :playlist_type)')
        c.execute(sql.bindparams(name=self.name, owner_id=self.owner_id,
                                 playlist_type=self.playlist_type))

        try:
            sql = "SELECT currval(pg_get_serial_sequence('playlists','id'))"
            result = c.execute(sql)
        except exc.OperationalError:
            # Try the sqlite way
            sql = 'SELECT last_insert_rowid()'
            result = c.execute(sql)
        self.id = result.fetchone()[0]

        pls = table('playlist_songs')
        for idx, item in enumerate(self.songs):
            entry = {
                'playlist_id': self.id,
                'song_id': item[0],
                'recording_mbid': item[1],
                'pos': idx,
            }

            MusicDatabase.insert_or_update(pls, entry,
                                           and_(pls.c.playlist_id == self.id,
                                                pls.c.pos == idx),
                                           connection=c)
        c.commit()

    def append_song(self, song_id, mbid=None, *, connection=None):
        assert song_id, "song_id must be used"
        if not mbid:
            mbid = MusicDatabase.getRecordingMBID(song_id)
        item = (song_id, mbid)
        self.songs.append(item)

        if self.id:
            pos = len(self.songs)
            c = connection or MusicDatabase.getCursor()
            entry = {
                'playlist_id': self.id,
                'song_id': song_id,
                'recording_mbid': mbid,
                'pos': pos,
            }

            pls = table('playlist_songs')
            MusicDatabase.insert_or_update(pls, entry,
                                           and_(pls.c.playlist_id == self.id,
                                                pls.c.pos == pos),
                                           connection=c)
            if not connection:
                c.commit()

    def insert_song(self, position, song_id=None, mbid=None, *,
                    connection=None):
        assert song_id, "song_id must be used"
        if position > len(self.songs):
            position = len(self.songs)

        if not mbid:
            mbid = MusicDatabase.getRecordingMBID(song_id)

        item = (song_id, mbid)

        self.songs.insert(position, item)

        if self.id:
            c = connection or MusicDatabase.getCursor()
            self._update_positions_in_db(len(self.songs) - 1, position, 1, c)

            entry = {
                'playlist_id': self.id,
                'pos': position,
                'song_id': song_id,
                'recording_mbid': mbid,
            }

            pls = table('playlist_songs')
            MusicDatabase.insert_or_update(pls, entry,
                                           and_(pls.c.playlist_id == self.id,
                                                pls.c.pos == position),
                                           connection=c)
            if not connection:
                c.commit()

    def _update_positions_in_db(self, from_position, to_position, delta,
                                connection):
        if delta > 0:
            s_delta = f'+{delta}'
        elif delta < 0:
            s_delta = f'{delta}'
        else:
            return

        if to_position < from_position:
            from_position -= 1
            to_position -= 1
            step = -1
        else:
            step = 1

        for pos in range(from_position, to_position, step):
            sql = text(f'UPDATE playlist_songs SET pos=pos{s_delta} '
                       'WHERE playlist_id = :playlist_id '
                       ' AND pos = :pos')
            print(sql, pos)
            connection.execute(sql.bindparams(playlist_id=self.id, pos=pos))

    def remove_song(self, position, *, connection=None):
        if position < 0 or position >= len(self.songs):
            raise ValueError('Trying to remove an out-of-range element '
                             'from the playlist')

        r = self.songs.pop(position)
        if self.id:
            c = connection or MusicDatabase.getCursor()
            sql = text('DELETE FROM playlist_songs '
                       'WHERE playlist_id = :playlist_id '
                       ' AND pos = :position')
            c.execute(sql.bindparams(playlist_id=self.id, position=position))

            sql = text('SELECT song_id, pos FROM playlist_songs ORDER BY pos')
            x = c.execute(sql).fetchall()
            for z in x:
                print(z)

            self._update_positions_in_db(position + 1, len(self.songs) + 1, -1,
                                         c)
            if not connection:
                c.commit()
        return r

    def move_song(self, from_position, to_position, *, connection=None):
        c = connection or MusicDatabase.getCursor()
        item = self.remove_song(from_position, connection=c)
        if to_position > from_position:
            to_position -= 1
        self.insert_song(to_position, item=item, connection=c)
        if not connection:
            c.commit()
