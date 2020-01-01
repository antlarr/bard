from flask import Flask, request, Response, render_template, url_for, \
    jsonify, abort, redirect
from jinja2 import FileSystemLoader
from flask_cors import CORS
from flask_login import LoginManager, login_required, login_user, logout_user
from bard.user import User
from bard.web_utils import get_redirect_target
from PIL import Image
from bard.musicdatabase_songs import getSongs
from bard.musicbrainz_database import MusicBrainzDatabase

import mimetypes
import base64
import os.path


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


@app.route('/')
@login_required
def index():
    return render_template('index.html')


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
    print(artistRow)
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
    print(rg)
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


@app.route('/api/v1/search')
def api_v1_search():
    print(request.method)
    print(request.args)
    print(request.args['query'])
    result = []
    for song in getSongs(request.args['query'], metadata=True):
        result.append(structFromSong(song))
    return jsonify(result)


@app.route('/api/v1/metadata/song/<songID>')
def api_v1_metadata_song(songID):
    result = []
    for song in getSongs(songID=songID, metadata=True):
        result.append(structFromSong(song))
    return jsonify(result)


@app.route('/api/v1/audio/song/<songID>')
def api_v1_audio_song(songID):
    songs = getSongs(songID=songID)
    if not songs:
        abort(404)
    song = songs[0]
    print('Delivering song %s: %s' % (songID, song.path()))
    localfilename = song.path()
    s = open(localfilename, 'rb').read()
    mime = mimetypes.guess_type(localfilename)
    print(mime)
    response = Response(s, status=200, mimetype=mime[0])
    response.headers["Content-Type"] = mime[0]
    return response


@app.route('/api/v1/coverart/song/<songID>')
def api_v1_coverart_song(songID):
    songs = getSongs(songID=songID)
    if not songs:
        abort(404)
    song = songs[0]
    print('Delivering coverart of song %s: %s' % (songID, song.path()))
    coverart = song.getCoverImage()
    if isinstance(coverart, str):
        data = open(coverart, 'rb').read()
        mime = mimetypes.guess_type(coverart)
        response = Response(data, status=200, mimetype=mime[0])
        response.headers["Content-Type"] = mime[0]
        return response
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
    elif page in ('artist', 'release-group'):
        _id = request.args.get('id', default=0, type=int)
        print('artist page', _id)
        return render_template('%s.html' % page, _id=_id)
    return '<p>Unknown page</p>'


@app.route('/hello')
def hello():
    return 'Hello, World'


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
    data = open(path, 'rb').read()
    mime = mimetypes.guess_type(path)
    response = Response(data, status=200, mimetype=mime[0])
    response.headers["Content-Type"] = mime[0]
    return response


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
    data = open(path, 'rb').read()
    mime = mimetypes.guess_type(path)
    response = Response(data, status=200, mimetype=mime[0])
    response.headers["Content-Type"] = mime[0]
    return response


@app.route('/api/v1/release_group/info')
def release_group_info():
    if request.method != 'GET':
        return None
    rgID = request.args.get('id', type=int)
    print('id', rgID)
    result = MusicBrainzDatabase.get_release_group_info(rgID)
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
        result.append(rel)

    print('aaa', result)
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
    data = open(path, 'rb').read()
    mime = mimetypes.guess_type(path)
    response = Response(data, status=200, mimetype=mime[0])
    response.headers["Content-Type"] = mime[0]
    return response
