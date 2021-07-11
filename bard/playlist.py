from bard.musicdatabase import MusicDatabase, DatabaseEnum, table
import bard.config as config
from sqlalchemy import text, exc, and_
import sqlite3
from sqlalchemy.engine.result import Row
import enum


class PlaylistTypes(enum.Enum):
    User = 'user'
    Album = 'album'
    Search = 'search'
    Generated = 'generated'


class Playlist:
    def __init__(self, db_row=None, owner_id=None):
        """Create a Playlist object."""
        self.id = None
        self.store_songs_in_db = True
        self.name = None
        if not owner_id:
            username = config.config['username']
            self.owner_id = MusicDatabase.getUserID(username)
        else:
            self.owner_id = owner_id
        self.playlist_type = DatabaseEnum('playlist_type').id_value('user')
        self.songs = []

        if isinstance(db_row, (sqlite3.Row, Row, dict)):
            self.id = db_row['id']
            self.name = db_row['name']
            self.owner_id = db_row['owner_id']

            self.load_playlist_songs()

    def load_playlist_songs(self):
        reenumerate_songs = False
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
                reenumerate_songs = True
            item = (song_id, recording_mbid)
            self.songs.append(item)
        if reenumerate_songs:
            self.reenumerate_songs_in_db()

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

        if self.store_songs_in_db:
            pls = table('playlist_songs')
            for idx, item in enumerate(self.songs):
                entry = {
                    'playlist_id': self.id,
                    'song_id': item[0],
                    'recording_mbid': item[1],
                    'pos': idx,
                }

                MusicDatabase.insert_or_update(pls, entry,
                                               and_(pls.c.playlist_id == self.id,  # noqa
                                                    pls.c.pos == idx),
                                               connection=c)
        c.commit()

    def append_song(self, song_id, mbid=None, *, connection=None):
        assert song_id, "song_id must be used"
        if not mbid:
            print(f'Obtaining MBID for song id {song_id}')
            mbid = MusicDatabase.getRecordingMBID(song_id)
        item = (song_id, mbid)
        self.songs.append(item)

        if self.id and self.store_songs_in_db:
            pos = len(self.songs) - 1
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

        if self.id and self.store_songs_in_db:
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
        if self.id and self.store_songs_in_db:
            c = connection or MusicDatabase.getCursor()
            sql = text('DELETE FROM playlist_songs '
                       'WHERE playlist_id = :playlist_id '
                       ' AND pos = :position')
            c.execute(sql.bindparams(playlist_id=self.id, position=position))

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

    def get_next_song(self, index):
        r = MusicDatabase.get_next_playlist_song(self.owner_id,
                                                 self.id, index)
        if not r:
            return None
        return (r['song_id'], r['pos'])

    def reenumerate_songs_in_db(self):
        c = MusicDatabase.getCursor()
        sql = ('SELECT pos '
               'FROM playlist_songs '
               'WHERE playlist_id = :id '
               'ORDER BY pos')
        result = c.execute(text(sql).bindparams(id=self.id))
        for idx, pos in enumerate(result.fetchall()):
            pos = pos[0]
            if pos != idx:
                sql = text('UPDATE playlist_songs SET pos = :idx '
                           'WHERE playlist_id = :playlist_id '
                           ' AND pos = :pos')
                c.execute(sql.bindparams(playlist_id=self.id, pos=pos,
                                         idx=idx))
        c.commit()
