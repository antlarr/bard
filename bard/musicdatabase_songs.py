from bard.musicdatabase import MusicDatabase
from bard.song import Song
from sqlalchemy import text
import os.path


def getMusic(where_clause='', where_values=None, tables=[],
             order_by=None, limit=None, metadata=False):
    # print(where_clause)
    c = MusicDatabase.getCursor()

    if 'songs' not in tables:
        tables.insert(0, 'songs')
    statement = ('SELECT id, root, path, mtime, title, artist, album, '
                 'albumArtist, track, date, genre, discNumber, '
                 'coverWidth, coverHeight, coverMD5 FROM %s %s' %
                 (','.join(tables), where_clause))
    if order_by:
        statement += ' ORDER BY %s' % order_by
    if limit:
        statement += ' LIMIT %d' % limit

    # print(statement, where_values)
    if where_values:
        result = c.execute(text(statement).bindparams(**where_values))
    else:
        result = c.execute(text(statement))
    r = [Song(x) for x in result.fetchall()]
    if metadata:
        MusicDatabase.updateSongsTags(r)
    return r


def getSongs(path=None, songID=None, query=None, metadata=False):
    where = ''
    values = None
    like = MusicDatabase.like
    if songID:
        where = ['id = :id']
        values = {'id': songID}
    elif (not path.startswith('/') or path.endswith('/') or
          os.path.isdir(path)):
        where = [f"path {like} :path"]
        values = {'path': '%' + path + '%'}
    else:
        where = ["path = :path"]
        values = {'path': path}
    tables = []
    if query:
        if query.root:
            where.append('root = :root')
            values['query'] = query.root
        if query.genre:
            tables = ['tags']
            where.append(f'''id = tags.song_id
                        AND (lower(tags.name) = 'genre'
                             OR tags.name='TCON')
                        AND tags.value {like} :tag''')
            values['tag'] = query.genre

    where = 'WHERE ' + ' AND '.join(where)
    return getMusic(where_clause=where, where_values=values,
                    tables=tables, metadata=metadata, order_by='path')


def getSongsAtPath(path, exact=False):
    if exact:
        where = "WHERE path = :path"
        values = {'path': path}
    else:
        like = MusicDatabase.like
        where = f"WHERE path {like} :path"
        values = {'path': path + '%'}
    return getMusic(where_clause=where, where_values=values)


def getSongsFromIDorPath(id_or_path, query=None):
    try:
        songID = int(id_or_path)
    except ValueError:
        songID = None

    if songID:
        return getSongs(songID=songID, query=query)

    return getSongs(path=id_or_path, query=query)
