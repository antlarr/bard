from flask import Flask, request, Response, render_template, url_for, \
    jsonify, abort, redirect, send_file
from jinja2 import FileSystemLoader
from flask_cors import CORS
from flask_login import LoginManager, login_required, login_user, \
    logout_user, current_user
from bard.user import User
from bard.web_utils import get_redirect_target
from bard.config import config
from PIL import Image
from bard.musicdatabase_songs import getSongs
from bard.musicbrainz_database import MusicBrainzDatabase, MediumFormatEnum
from bard.musicdatabase import MusicDatabase
from bard.playlist import Playlist
from bard.album import coverAtPath
from bard.searchquery import SearchQuery
from bard.searchplaylist import SearchPlaylist
from bard.playlistsonginfo import PlaylistSongInfo

import mimetypes
import base64
import os.path
import re
import werkzeug


app = Flask(__name__, static_url_path='/kakaka')

app.jinja_loader = FileSystemLoader('templates')
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = '/login'


def read_or_generate_key():
    directory = os.path.expanduser('~/.local/share/bard')
    os.makedirs(directory, exist_ok=True)
    key_file = os.path.join(directory, 'private_key')
    try:
        with open(key_file, 'r') as fh:
            for line in fh.readlines():
                if line.startswith('key='):
                    encodedkey = line[4:-1]
                    print(encodedkey, type(encodedkey))
                    return base64.decodebytes(encodedkey.encode('utf8'))
    except FileNotFoundError:
        pass

    secret_key = os.urandom(16)

    with open(os.open(key_file, os.O_CREAT | os.O_WRONLY, 0o600)) as fh:
        fh.write('# Private key for web sessions\n')
        fh.write('# If this file is removed, a new key will be generated\n')
        fh.write('key=' + base64.encodebytes(secret_key).decode('utf8') + '\n')

    return secret_key


def init_flask_app():
    app.secret_key = read_or_generate_key()


@login_manager.user_loader
def load_user(user_id):
    print('loading user', user_id)
    return User(user_id)


@login_manager.request_loader
def load_user_from_request(request):

    # first, try to login using the api_key url arg
    api_key = request.args.get('api_key')
    if api_key:
        user = User.query.filter_by(api_key=api_key).first()
        if user:
            return user

    # next, try to login using Basic Auth
    api_key = request.headers.get('Authorization')
    if api_key:
        api_key = api_key.replace('Basic ', '', 1)
        try:
            api_key = base64.b64decode(api_key)
        except TypeError:
            pass
        user = User.query.filter_by(api_key=api_key).first()
        if user:
            return user

    # finally, return None if both methods did not login the user
    return None


def base_href():
    use_ssl = config['use_ssl']
    hostname = config['hostname']
    port = config['port']
    protocol = {False: 'http', True: 'https'}[use_ssl]
    return f'{protocol}://{hostname}:{port}'


@app.route('/')
@login_required
def index():
    return render_template('index.html', base_href=base_href())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = load_user(username)
        user.validate(password)
        if user.is_authenticated:
            login_user(user)
            print('url_for_index', url_for('index'))
            next_target = get_redirect_target('index')
            print('redirecting to', next_target)
            return redirect(next_target)

    return render_template('login.html')


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/login')


def structFromSong(song):
    r = {}
    r['id'] = song.id
    r['path'] = song.path()
    r['filename'] = os.path.basename(song.path())
    r['title'] = song.getTagIfAvailable('title')
    r['artist'] = song.getTagIfAvailable('artist')
    return r


def structFromArtistAlias(aliasRow):
    r = {}
    r['name'] = aliasRow.name
    r['locale'] = aliasRow.locale
    r['artist_alias_type'] = aliasRow.artist_alias_type
    r['primary_for_locale'] = aliasRow.primary_for_locale
    return r


def structFromArtist(artistRow, aliasesRows=[]):
    r = {}
    r['id'] = artistRow.id
    r['mbid'] = artistRow.mbid
    r['name'] = artistRow.name
    r['artist_type'] = artistRow.artist_type
    r['area_id'] = artistRow.area_id
    r['gender'] = artistRow.gender
    r['disambiguation'] = artistRow.disambiguation
    r['locale_name'] = artistRow.locale_name
    r['has_image'] = bool(artistRow.image_path)
    if aliasesRows:
        r['aliases'] = [structFromArtistAlias(x) for x in aliasesRows]
    else:
        r['aliases'] = []
    return r


def structFromReleaseGroup(rg):
    r = {}
    r['id'] = rg.id
    r['mbid'] = rg.mbid
    r['name'] = rg.name
    r['disambiguation'] = rg.disambiguation
    r['release_group_type'] = rg.release_group_type
    r['artist_credit_id'] = rg.artist_credit_id
    r['artist_credit_name'] = rg.artist_credit_name
    r['secondary_types'] = \
        MusicBrainzDatabase.get_release_group_secondary_types(rg.id)
    return r


def album_properties_to_string(prop):
    r = dict(prop)
    s = []
    if prop['format'] in ['mp3', 'wma']:
        if prop['min_bitrate'] != prop['max_bitrate']:
            s.append(f"{prop['min_bitrate']//1000}-"
                     f"{prop['max_bitrate']//1000}kbps")
        else:
            s.append(f"{prop['min_bitrate']//1000}kbps")

    if prop['min_sample_rate'] != prop['max_sample_rate']:
        s.append(f"{prop['min_sample_rate']}-{prop['max_sample_rate']}Hz")
    elif prop['min_sample_rate'] != 44100:
        s.append(f"{prop['min_sample_rate']}Hz")

    if prop['min_bits_per_sample'] != prop['max_bits_per_sample']:
        s.append(f"{prop['min_bits_per_sample']}-"
                 f"{prop['max_bits_per_sample']}bits")
    elif prop['min_bits_per_sample'] != 16:
        s.append(f"{prop['min_bits_per_sample']}bits")

    if prop['min_channels'] != prop['max_channels']:
        s.append(f"{prop['min_channels']}-{prop['max_channels']}ch")
    elif prop['min_channels'] != 2:
        s.append(f"{prop['min_channels']}ch")

    r['string'] = prop['format'].upper() + ((':' + ','.join(s)) if s else '')
    return r


@app.route('/api/v1/song/search')
def api_v1_song_search():
    plman = app.bard.playlist_manager
    sq = SearchQuery.from_request(request, current_user.userID, plman)
    if not sq:
        raise ValueError('No SearchQuery!')
    pl = plman.get_search_result_playlist(sq)
    if not pl:
        pl = SearchPlaylist(sq)
        plman.add_search_playlist(pl)

    songs = MusicBrainzDatabase.search_songs_for_webui(sq.query,
                                                       sq.offset,
                                                       sq.page_size)

    song_ids = [song['song_id'] for song in songs]
    for song_id in song_ids:
        pl.append_song(song_id)

    ratings = MusicDatabase.get_songs_ratings(song_ids, current_user.userID)
    songs = [{'rating': ratings[song['song_id']],
              **dict(song)} for song in songs]
    result = {'search_playlist_id': pl.searchPlaylistID,
              'search_query': sq.as_dict(),
              'songs': songs}
    return jsonify(result)


@app.route('/api/v1/metadata/song/<songID>')
def api_v1_metadata_song(songID):
    song = getSongs(songID=songID, metadata=True)
    if not song:
        return ''
    song = song[0]
    return jsonify(structFromSong(song))


@app.after_request
def after_request(response):
    response.headers.add('Accept-Ranges', 'bytes')
    return response


def send_file_partial(path, *args, **kwargs):
    """send_file replacemnt with support for HTTP 206 Partial Content."""
    range_header = request.headers.get('Range', None)
    if not range_header or not range_header.startswith('bytes='):
        return send_file(path, *args, **kwargs)

    size = os.path.getsize(path)

    range_header = range_header[6:].strip()

    if range_header[0] == '-':
        # It's a suffix-byte-range-spec in RFC 7233
        length = -int(range_header)
        begin = size - length
        end = size
    else:
        m = re.search(r'(\d+)-(\d*)', range_header)
        begin, end = (int(x) if x else None for x in m.groups())

        if end:
            length = end - begin + 1
        else:
            length = size - begin

    data = None
    with open(path, 'rb') as f:
        f.seek(begin)
        data = f.read(length)

    rv = Response(data,
                  206,
                  mimetype=mimetypes.guess_type(path)[0],
                  direct_passthrough=True)
    rv.headers.add('Content-Range',
                   f'bytes {begin}-{begin + length - 1}/{size}')

    return rv


@app.route('/api/v1/audio/song/<songID>')
def api_v1_audio_song(songID):
    try:
        songs = getSongs(songID=int(songID))
        if not songs:
            raise ValueError
    except ValueError:
        abort(404)
    song = songs[0]
    print('Delivering song %s: %s' % (songID, song.path()))
    localfilename = song.path()
    return send_file(localfilename)


@app.route('/api/v1/coverart/song/<songID>')
def api_v1_coverart_song(songID):
    songs = getSongs(songID=songID)
    if not songs:
        abort(404)
    song = songs[0]
    print('Delivering coverart of song %s: %s' % (songID, song.path()))
    coverart = song.getCoverImage()
    if isinstance(coverart, str):
        return send_file(coverart)
    elif isinstance(coverart, tuple):
        image, data = coverart
        response = Response(data, status=200)
        return response
    elif isinstance(coverart, Image.Image):
        data = coverart.tobytes()
        mime = Image.MIME[coverart.format]
        response = Response(data, status=200, mimetype=mime)
        response.headers["Content-Type"] = mime
        return response

    return ''


@app.route('/user/<username>')
def profile(username):
    # TODO: Some extra authentication would be nice here :)
    return '{}\'s profile'.format(username)


@app.route('/component/<page>')
def component(page):
    print('component!')
    if request.method != 'GET':
        return None
    if page in ('home', 'albums', 'genres', 'about'):
        return render_template('%s.html' % page)
    elif page in ('artists',):
        letter = request.args.get('letter', default='0', type=str)
        return render_template('%s.html' % page, letter=letter)
    elif page in ('artist', 'release-group', 'album', 'playlist'):
        _id = request.args.get('id', default=0, type=int)
        print('artist page', _id)
        return render_template('%s.html' % page, _id=_id)
    return '<p>Unknown page</p>'


@app.route('/hello')
def hello():
    return 'Hello, World'


@app.route('/favicon.ico')
def serve_favicon():
    filename = 'favicon.ico'
    localfilename = 'web-root/%s' % filename
    print(localfilename)
    s = open(localfilename, 'rb').read()
    mime = mimetypes.guess_type(localfilename)
    return Response(s, mimetype=mime[0])


@app.route('/static/<path:filename>')
def static_file(filename):
    localfilename = 'web-root/%s' % filename
    print(localfilename)
    s = open(localfilename, 'rb').read()
    mime = mimetypes.guess_type(localfilename)
    return Response(s, mimetype=mime[0])


@app.route('/api/v1/artists/list')
def artists_list():
    if request.method != 'GET':
        return None
    offset = request.args.get('offset', default=0, type=int)
    page_size = request.args.get('page_size', default=500, type=int)
    print('/api/v1/artists/list', offset, page_size)
    # result = []
    # for artist in getArtists(from_idx, to_idx, metadata=True):
    #    result.append(artist)
    result = [structFromArtist(x)
              for x in MusicBrainzDatabase.get_range_artists(
                  offset, page_size, metadata=True)]
    return jsonify(result)


@app.route('/api/v1/artists/letterOffset')
def artists_letter_offset():
    if request.method != 'GET':
        return None
    letter = request.args.get('letter', default='0', type=str)
    print(letter)
    result = {'offset':
              MusicBrainzDatabase.get_letter_offset_for_artist(letter)}
    return jsonify(result)


@app.route('/api/v1/artist/image')
def artist_get_image():
    artist_id = request.args.get('id', type=int)
    path = MusicBrainzDatabase.get_artist_image_path(artist_id)
    if not path:
        path = 'web-root/images/artist.png'
    print('Delivering artist image of artist %s: %s' % (artist_id, path))
    return send_file(path)


@app.route('/api/v1/artist/info')
def artist_info():
    if request.method != 'GET':
        return None
    artistID = request.args.get('id', type=int)
    print('id', artistID)
    result = MusicBrainzDatabase.get_artist_info(artistID)
    result_aliases = MusicBrainzDatabase.get_artist_aliases(
        artistID, locales=['es', 'en'])
    return jsonify(structFromArtist(result, result_aliases))


@app.route('/api/v1/artist/member_relations')
def artist_member_relations():
    if request.method != 'GET':
        return None
    artistID = request.args.get('id', type=int)
    r1, r2 = \
        MusicBrainzDatabase.get_artist_members_of_band_relations(artistID)
    result = {'members': r1, 'memberOf': r2}
    print(result)
    return jsonify(result)


@app.route('/api/v1/artist/release_groups')
def artist_release_groups():
    if request.method != 'GET':
        return None
    artistID = request.args.get('id', type=int)
    print('artist release groups id=', artistID)

    result = [structFromReleaseGroup(x)
              for x in MusicBrainzDatabase.get_artist_release_groups(artistID)]
    return jsonify(result)


@app.route('/api/v1/release_group/image')
def release_group_get_image():
    release_group_mbid = request.args.get('mbid', type=str)
    dirnames = MusicBrainzDatabase.get_release_group_directories(
        release_group_mbid)
    path = 'web-root/images/cd.png'
    for dirname in dirnames:
        cover = os.path.join(dirname, 'cover.jpg')
        if os.path.exists(cover):
            path = cover
            break
        cover = cover[:-3] + 'png'
        if os.path.exists(cover):
            path = cover
            break

    print('Delivering release_group image of release_group %s: %s' %
          (release_group_mbid, path))
    return send_file(path)


@app.route('/api/v1/release_group/info')
def release_group_info():
    if request.method != 'GET':
        return None
    rgID = request.args.get('id', type=int)
    print('id', rgID)
    result = MusicBrainzDatabase.get_release_group_info(rgID)
    print('release_group_info', dict(result))
    return jsonify(dict(result))


@app.route('/api/v1/release_group/releases')
def release_group_releases():
    if request.method != 'GET':
        return None
    rgID = request.args.get('id', type=int)
    print('id', rgID)
    releases = MusicBrainzDatabase.get_release_group_releases(rgID)
    result = []
    for release in releases:
        mediums = MusicBrainzDatabase.get_release_mediums(release['id'])
        rel = dict(release)
        rel['mediums_desc'] = MusicBrainzDatabase.mediumlist_to_string(mediums)
        rel['audio_properties'] = [album_properties_to_string(x)
                                   for x in MusicDatabase.getAlbumProperties(
                                       release['album_id'])]
        rel['album_disambiguation'] = \
            MusicBrainzDatabase.getAlbumDisambiguation(release)

        result.append(rel)

    return jsonify(result)


@app.route('/api/v1/release/image')
def release_get_image():
    release_mbid = request.args.get('mbid', type=str)
    dirnames = MusicBrainzDatabase.get_release_directories(release_mbid)
    path = 'web-root/images/cd.png'
    for dirname in dirnames:
        cover = os.path.join(dirname, 'cover.jpg')
        if os.path.exists(cover):
            path = cover
            break
        cover = cover[:-3] + 'png'
        if os.path.exists(cover):
            path = cover
            break

    print('Delivering release image of release %s: %s' %
          (release_mbid, path))
    return send_file(path)


@app.route('/api/v1/album/tracks')
def album_tracks():
    if request.method != 'GET':
        return None
    albumID = request.args.get('id', type=int)
    # songIDs = {x['releasetrackid']: x['song_id']
    #            for x in MusicBrainzDatabase.get_album_songs(albumID)}

    all_tracks = MusicBrainzDatabase.get_album_tracks(albumID)
    existing_tracks = MusicBrainzDatabase. \
        get_album_songs_information_for_webui(albumID)

    song_ids = [track['song_id'] for track in existing_tracks]
    ratings = MusicDatabase.get_songs_ratings(song_ids, current_user.userID)

    existing_tracks = {x['track_mbid']: {'rating': ratings[x['song_id']],
                                         **dict(x)} for x in existing_tracks}
    result = []
    medium = {'number': None, 'tracks': []}
    current_medium_number = None
    for track in all_tracks:
        if track['medium_number'] != current_medium_number:
            if current_medium_number:
                result.append(medium)
            current_medium_number = track['medium_number']
            format_id = track['medium_format_id']
            medium_format_name = (MediumFormatEnum.name(format_id) or
                                  'Unknown Format')

            medium = {'number': track['medium_number'],
                      'name': track['medium_name'],
                      'format': medium_format_name,
                      'tracks': []}
        try:
            medium['tracks'].append(existing_tracks[track['track_mbid']])
        except KeyError:
            trk = dict(track)
            trk['song_id'] = None
            trk['rating'] = (5, None)
            medium['tracks'].append(trk)

    result.append(medium)
    return jsonify(result)


@app.route('/api/v1/album/image')
def album_cover():
    if request.method != 'GET':
        return None
    album_id = request.args.get('id', type=int)
    medium_number = request.args.get('medium_number', type=int, default=None)
    print(f'Delivering coverart of album {album_id} medium {medium_number}')

    path = MusicDatabase.getAlbumPath(album_id, medium_number)
    if not path:
        print('ERROR getting album image for album'
              f'{album_id}/{medium_number}')
        return ''
    coverfilename = coverAtPath(path)

    if coverfilename:
        return send_file(coverfilename)
    else:
        print(f'Error cover not found at {path}')

    return ''


@app.route('/api/v1/playlist/list')
def playlist_list():
    if request.method != 'GET':
        return None
    print(current_user.username, current_user.userID)
    result = []
    for x in MusicDatabase.getPlaylistsForUser(current_user.userID):
        result.append({'id': x['id'],
                       'name': x['name'],
                       'type': x['playlist_type']})
    print(result)
    return jsonify(result)


@app.route('/api/v1/playlist/info')
def playlist_info():
    if request.method != 'GET':
        return None
    print(current_user.username, current_user.userID)
    playlistID = request.args.get('id', type=int)
    r = MusicDatabase.getPlaylistsForUser(current_user.userID, playlistID)
    if not r:
        return {}
    r = r[0]
    result = {'id': r['id'],
              'name': r['name'],
              'type': r['playlist_type']}
    return jsonify(result)


@app.route('/api/v1/playlist/new')
def playlist_new():
    if request.method != 'GET':
        return None
    print(current_user.username, current_user.userID)
    name = request.args.get('name', type=str)
    print(f'Request to create playlist with name {name}')
    pl = Playlist(None, owner_id=current_user.userID)
    pl.set_name(name)
    pl.create_in_db()
    return jsonify([])


@app.route('/api/v1/playlist/add_song')
def playlist_add_song():
    if request.method != 'GET':
        return None
    print(current_user.username, current_user.userID)

    playlistID = request.args.get('playlistID', type=int)
    songID = request.args.get('songID', type=int)
    print(playlistID, songID)
    playlist = Playlist.load_id_from_db(playlistID, current_user.userID)
    playlist.append_song(songID)
    print(playlist.songs)
    return ''


@app.route('/api/v1/playlist/tracks')
def playlist_tracks():
    if request.method != 'GET':
        return None

    playlistID = request.args.get('id', type=int)
    songs = MusicBrainzDatabase.get_playlist_songs_information_for_webui(
        playlistID)
    song_ids = [song['song_id'] for song in songs]
    ratings = MusicDatabase.get_songs_ratings(song_ids, current_user.userID)
    result = [{'rating': ratings[song['song_id']],
               **dict(song)} for song in songs]
    return jsonify(result)


@app.route('/api/v1/artist_credit/info')
def artist_credit_info():
    if request.method != 'GET':
        return None

    artistCreditID = request.args.get('id', type=int)
    print('artistCredit: ', artistCreditID)
    result = MusicBrainzDatabase.get_artist_credit_info(artistCreditID)

    result = [dict(x) for x in result]
    return jsonify(result)


@app.route('/api/v1/playlist/current/next_song', methods=['POST'])
def playlist_current_next_song():
    if request.method != 'POST':
        return None
    print(request.form)
    playlistSongInfo = PlaylistSongInfo.from_request(request)
    playlistSongInfo.set_current_user(current_user.userID)
    nextSongInfo = playlistSongInfo.next_song()

    print(nextSongInfo)
    return jsonify(nextSongInfo.as_dict())


@app.route('/api/v1/song/set_ratings')
def song_set_ratings():
    if request.method != 'GET':
        return None
    song_id = request.args.get('id', type=int)
    rating = request.args.get('rating', type=int)
    song = getSongs(songID=song_id)
    if not song:
        return ''
    song = song[0]
    song.setUserRating(rating, current_user.userID)

    return ''


@app.errorhandler(werkzeug.exceptions.BadRequest)
def handle_bad_request(e):
    print('Bad Request:', e)
    return '', 400
