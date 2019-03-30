from flask import Flask, request, Response, render_template, url_for, \
    jsonify, abort, session, redirect
from jinja2 import FileSystemLoader
from flask_cors import CORS
from flask_login import LoginManager, login_required, login_user, logout_user
from bard.user import User
from bard.web_utils import get_redirect_target
from PIL import Image

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


@app.route('/api/v1/search')
def api_v1_search():
    print(request.method)
    print(request.args)
    print(request.args['query'])
    result = []
    for song in app.bard.getSongs(request.args['query'], metadata=True):
        result.append(structFromSong(song))
    return jsonify(result)


@app.route('/api/v1/metadata/song/<songID>')
def api_v1_metadata_song(songID):
    result = []
    for song in app.bard.getSongs(songID=songID, metadata=True):
        result.append(structFromSong(song))
    return jsonify(result)


@app.route('/api/v1/audio/song/<songID>')
def api_v1_audio_song(songID):
    songs = app.bard.getSongs(songID=songID)
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
    songs = app.bard.getSongs(songID=songID)
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
    if page in ('home', 'artists', 'albums', 'genres', 'about'):
        return render_template('%s.html' % page)
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
