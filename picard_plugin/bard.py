from picard.file import register_file_post_addition_to_track_processor, \
    register_file_post_save_processor
from picard.metadata import register_track_metadata_processor, \
    register_album_metadata_processor
from picard.script import register_script_function
from collections import Counter
import os.path
import mutagen
import unicodedata

PLUGIN_NAME = "Bard tags"
PLUGIN_AUTHOR = "Antonio Larrosa"
PLUGIN_DESCRIPTION = """
Add bard tags that can be used by the bard file naming script.

Create .artist_mbid and .releasegroup_mbid files in the appropriate
directories when saving music files.

Adds a $original_value() function that returns the original value of a tag
as it can be found currently on the file."""

PLUGIN_VERSION = "0.1"
PLUGIN_API_VERSIONS = ["2.0", "2.1", "2.2"]
PLUGIN_LICENSE = "GPL-3.0"
PLUGIN_LICENSE_URL = "https://www.gnu.org/licenses/gpl-3.0.html"


def find_organized_folder():
    cfg = os.path.expanduser('~/.config/MusicBrainz/Picard.ini')
    line = [x for x in open(cfg, 'r').readlines()
            if x.startswith('move_files_to')][0]
    value = line[line.find('=') + 1:-1]
    if not value.endswith('/'):
        value += '/'
    return value


ORGANIZED_FOLDER = find_organized_folder()


@register_script_function
def original_value(parser, tag):
    if parser.file:
        print(f'Use parser.file.orig_metadata to read tag {tag}')
        try:
            return parser.file.orig_metadata[tag]
        except KeyError:
            return ''

    context = parser.context
    try:
        dirname = context['~dirname']
        filename = context["~filename"]
        extension = context["~extension"]
    except KeyError:
        print('Cannot get filename')
        return ''
    path = os.path.join(dirname, f'{filename}.{extension}')

    if not path or path == '.':
        return ''

    print(f'Loading metadata from {path} to read tag {tag}')
    try:
        metadata = mutagen.File(path)
    except mutagen.MutagenError as e:
        print(f'error opening {path}', e)
        return ''
    try:
        return ';'.join(metadata[tag])
    except KeyError:
        return ''

    return ''


@register_file_post_addition_to_track_processor
def bard_keep_good_tags(track, file):
    if file.filename.startswith(ORGANIZED_FOLDER):
        print('Keeping genre and images: File is already correctly tagged')
        track.metadata['genre'] = track.orig_metadata['genre']
        track.keep_original_images()
        track.update()


def is_latin(uchr):
    return 'LATIN' in unicodedata.name(uchr)


def only_roman_chars(unistr):
    return all('LATIN' in unicodedata.name(uchr)
               for uchr in unistr if uchr.isalpha())


def find_alias(aliases, primary=None, locale=None):
    for alias in aliases:
        if ((not primary or alias['primary'] == primary) and
                (not locale or alias['locale'] == locale)):
            return alias['name']
    return None


def get_artist_name(artist_metadata):
    # This is my preference order for primary_alias and locales.
    # You might want to set a different one
    options = [(True, 'en'), (True, 'es'), (None, 'en'), (None, 'es'),
               (True, 'fr'), (True, 'de'), (None, 'fr'), (None, 'de')]
    for primary, locale in options:
        name = find_alias(artist_metadata['aliases'],
                          primary=True, locale='en')
        if name:
            return name

    if only_roman_chars(artist_metadata['name']):
        return artist_metadata['name']

    for alias in artist_metadata['aliases']:
        if only_roman_chars(alias['name']):
            return alias['name']

    return artist_metadata['name']


def directory_matches_mbids(dirname, mbids, mbid_filename):
    d = os.path.join(ORGANIZED_FOLDER, dirname)
    if not os.path.isdir(d):
        return True

    filename = os.path.join(d, mbid_filename)
    if not os.path.exists(filename) or os.path.getsize(filename) < 36:
        return True

    with open(filename, 'r') as fd:
        dir_mbids = [line.strip('\n') for line in fd.readlines()]

    return dir_mbids == mbids


def directory_matches_artist_mbids(dirname, mbids):
    return directory_matches_mbids(dirname, mbids, '.artist_mbid')


def directory_matches_releasegroup_mbids(dirname, mbids):
    return directory_matches_mbids(dirname, mbids, '.releasegroup_mbid')


def get_albumartist_folder_tag(tagger, metadata, track, release,
                               use_disambiguation=True):
    result = ''
    if release:
        artists = release['artist-credit']
    else:  # is a non-album track
        artists = track['artist-credit']

    if metadata['useonlyfirstartist'] == '1':
        artists = [artists[0]]

    last = len(artists) - 2
    mbids = []
    for idx, artist in enumerate(artists):
        a = artist['artist']
        name = get_artist_name(a)
        mbids.append(a['id'])
        disambiguation = a['disambiguation']
        if not use_disambiguation or disambiguation == '.':
            disambiguation = ''
        elif disambiguation:
            disambiguation = ' (' + disambiguation + ')'
        result += name + disambiguation
        if idx < last:
            result += ', '
        elif idx == last:
            if artist['joinphrase'] == ' y ':
                result += ' y '
            else:
                result += ' & '

    return result, mbids


def add_bard_albumartist_folder_tag(tagger, metadata, track, release):

    dirname, mbids = get_albumartist_folder_tag(tagger, metadata, track,
                                                release,
                                                use_disambiguation=False)
    if directory_matches_artist_mbids(dirname, mbids):
        metadata['~bard_albumartist_folder'] = [dirname]
        return

    dirname, mbids = get_albumartist_folder_tag(tagger, metadata, track,
                                                release,
                                                use_disambiguation=True)
    metadata['~bard_albumartist_folder'] = [dirname]


@register_track_metadata_processor
def add_bard_tags(tagger, metadata, track, release):
    add_bard_albumartist_folder_tag(tagger, metadata, track, release)


def get_artist_directory(filename):
    if not filename.startswith(ORGANIZED_FOLDER):
        return None
    return filename[:filename.find('/', len(ORGANIZED_FOLDER))]


def save_artist_mbid_file(file):
    artist_directory = get_artist_directory(file.filename)

    if not artist_directory:
        return
    filename = os.path.join(artist_directory, '.artist_mbid')
    if os.path.exists(filename) and os.path.getsize(filename) >= 36:
        return

    if 'musicbrainz_albumartistid' in file.metadata:
        mbids_tag_value = file.metadata['musicbrainz_albumartistid']
        mbids = [x.strip()
                 for x in mbids_tag_value.split(';')]
    else:
        mbids_tag_value = file.metadata['musicbrainz_artistid']
        mbids = [x.strip()
                 for x in mbids_tag_value.split(';')]
        mbids = mbids[:1]

    if mbids:
        with open(filename, 'w') as fd:
            for mbid in mbids:
                fd.write(mbid + '\n')
    return artist_directory


def save_releasegroup_mbid_file(file, artist_directory=None):
    if file.metadata['usereleasegroupinpath'] != '1':
        return

    if not artist_directory:
        artist_directory = get_artist_directory(file.filename)
        if not artist_directory:
            return

    path = file.filename
    rg_directory = path[:path.find('/', len(artist_directory) + 1)]
    filename = os.path.join(rg_directory, '.releasegroup_mbid')

    if os.path.exists(filename) and os.path.getsize(filename) >= 36:
        return

    mbids = [file.metadata['musicbrainz_releasegroupid']]
    with open(filename, 'w') as fd:
        for mbid in mbids:
            fd.write(mbid + '\n')


@register_file_post_save_processor
def save_mbid_files(file):
    artist_directory = save_artist_mbid_file(file)
    save_releasegroup_mbid_file(file, artist_directory)


@register_album_metadata_processor
def bard_add_release_media_description(tagger, metadata, release):
    c = dict(Counter(media['format'] for media in release['media']))
    txt = ''
    # We want to keep the order of media formats
    ordered = {}
    for media in release['media']:
        if media['format'] not in ordered:
            ordered[media['format']] = c[media['format']]

    txt = '+'.join(f'{num}x{format}' if num > 1 else str(format)
                   for format, num in ordered.items())
    metadata['~bard_album_mediaformat'] = txt
