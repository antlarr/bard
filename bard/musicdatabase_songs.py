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


def getSongs(path=None, songID=None, query=None, metadata=False):  # noqa: C901
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
        if query.rating:
            tables += ['songs_ratings', 'avg_songs_ratings']
            txt = query.rating.lower()
            if ' and ' in txt:
                raise NotImplementedError('Complex rating query')
            elif txt.startswith('>') or txt.startswith('<'):
                rating = float(txt[1:])
                op = txt[0]
            else:
                rating = float(txt)
                op = '='

            where.append(f'''id = songs_ratings.song_id
                             AND songs_ratings.user_id = :user_id
                             AND id = avg_songs_ratings.song_id
                             AND avg_songs_ratings.user_id = :user_id
                             AND COALESCE(songs_ratings.rating,
                             avg_songs_ratings.avg_rating, 5) {op} {rating}''')
            values['user_id'] = query.user_id
        if query.my_rating:
            if 'songs_ratings' not in tables:
                tables += ['songs_ratings']
                where.append('id = songs_ratings.song_id '
                             'AND songs_ratings.user_id = :user_id')
                values['user_id'] = query.user_id

            txt = query.my_rating.lower()
            if ' and ' in txt:
                raise NotImplementedError('Complex rating query')
            elif txt.startswith('>') or txt.startswith('<'):
                rating = float(txt[1:])
                op = txt[0]
            else:
                rating = float(txt)
                op = '='

            where.append(f'songs_ratings.rating {op} {rating}')
        if query.others_rating:
            if 'avg_songs_ratings' not in tables:
                tables += ['avg_songs_ratings']
                where.append('id = avg_songs_ratings.song_id '
                             'AND avg_songs_ratings.user_id = :user_id')
                values['user_id'] = query.user_id

            txt = query.others_rating.lower()
            if ' and ' in txt:
                raise NotImplementedError('Complex rating query')
            elif txt.startswith('>') or txt.startswith('<'):
                rating = float(txt[1:])
                op = txt[0]
            else:
                rating = float(txt)
                op = '='

            where.append(f'avg_songs_ratings.avg_rating {op} {rating}')

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
