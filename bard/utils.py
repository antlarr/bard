# -*- coding: utf-8 -*-

import subprocess
import time
import re
import hashlib
import math
from pydub import AudioSegment
import mutagen
import mutagen.mp3
import mutagen.mp4
import mutagen.easymp4
import mutagen.monkeysaudio
import mutagen.asf
import mutagen.flac
import mutagen.wavpack
import chromaprint
from collections import namedtuple
from PIL import Image
import bard.config as config
from bard.terminalcolors import TerminalColors
from bard import bard_audiofile
from pydub.utils import db_to_float
import itertools
import io

ImageDataTuple = namedtuple('ImageDataTuple', ['image', 'data'])

DecodedAudioPropertiesTuple = namedtuple('DecodedAudioPropertiesTuple',
                                         ['codec', 'format_name',
                                          'container_duration',
                                          'decoded_duration',
                                          'container_bitrate',
                                          'stream_bitrate',
                                          'stream_sample_format',
                                          'stream_bytes_per_sample',
                                          'stream_bits_per_raw_sample',
                                          'decoded_sample_format',
                                          'decoded_bytes_per_sample',
                                          'decoded_sample_rate',
                                          'decoded_channels',
                                          'is_planar',
                                          'samples',
                                          'channels',
                                          'sample_rate',
                                          'library_versions',
                                          'messages'])


class DecodeMessageRecord(namedtuple('DecodeMessageRecord',
                                     ['time_position', 'level', 'message'])):
    __slots__ = ()

    level_mapping = {0: 'Critical',
                     1: 'Fatal',
                     2: 'Error',
                     3: 'Warning',
                     4: 'Info',
                     5: 'Verbose',
                     6: 'Debug',
                     7: 'Trace'}

    @staticmethod
    def level_to_string(level):
        try:
            return DecodeMessageRecord.level_mapping[level]
        except KeyError:
            return 'Unknown level'

    @staticmethod
    def level_value(levelstring):
        for level, name in DecodeMessageRecord.level_mapping.items():
            if levelstring == name:
                return level
        return None

    @staticmethod
    def color_for_level(level):
        if level <= 2:
            return TerminalColors.Error
        if level <= 4:
            return TerminalColors.Highlight
        return ''

    def level_as_string(self):
        return self.level_to_string(self.level)

    def level_color(self):
        return self.color_for_level(self.level)

    def __str__(self):
        return '%.3f (%s): %s' % (self.time_position, self.level_color() +
                                  self.level_as_string() +
                                  TerminalColors.ENDC, self.message)


def detect_silence_at_beginning_and_end(audio_segment, min_silence_len=1000,
                                        silence_thresh=-16, seek_step=1):
    seg_len = len(audio_segment)

    # you can't have a silent portion of a sound that is longer than the sound
    if seg_len < min_silence_len:
        return []

    # convert silence threshold to a float value (so we can compare it to rms)
    silence_thresh = (db_to_float(silence_thresh) *
                      audio_segment.max_possible_amplitude)

    # check successive (1 sec by default) chunk of sound for silence
    # try a chunk at every "seek step" (or every chunk for a seek step == 1)
    last_slice_start = seg_len - min_silence_len
    slice_starts = range(0, last_slice_start + 1, seek_step)

    # guarantee last_slice_start is included in the range
    # to make sure the last portion of the audio is seached
    if last_slice_start % seek_step:
        slice_starts = itertools.chain(slice_starts, [last_slice_start])

    song_start = 0
    song_end = seg_len
    for i in slice_starts:
        audio_slice = audio_segment[i:i + min_silence_len]
        if audio_slice.rms > silence_thresh:
            if i == 0:
                song_start = 0
            else:
                song_start = i + min_silence_len
            break
    else:
        return [[0, 0], [song_end, song_end]]

    for i in reversed(slice_starts):
        audio_slice = audio_segment[i:i + min_silence_len]
        if audio_slice.rms > silence_thresh:
            if song_end == slice_starts[-1]:
                song_end = seg_len
            else:
                song_end = i
            break

    return [[0, song_start], [song_end, seg_len]]


def fingerprint_AudioSegment(audio_segment, maxlength=120000):
    """Fingerprint audio data given a pydub AudioSegment object.

    Raises a FingerprintGenerationError if anything goes wrong.
    Based on acoustid.py's fingerprint function.
    """
    maxlength /= 1000
    endposition = audio_segment.frame_rate * audio_segment.channels * maxlength
    try:
        fper = chromaprint.Fingerprinter()

        fper.start(audio_segment.frame_rate, audio_segment.channels)

        position = 0  # Samples of audio fed to the fingerprinter.
        for start in range(0, len(audio_segment.raw_data), 4096):
            block = audio_segment.raw_data[start:start + 4096]
            fper.feed(block)
            position += len(block) // 2  # 2 bytes/sample.
            if position >= endposition:
                break
        return fper.finish()
    except chromaprint.FingerprintError:
        raise chromaprint.FingerprintGenerationError("fingerprint calculation "
                                                     "failed")


def printSongsInfo(song1, song2,
                   useColors=(TerminalColors.First, TerminalColors.Second)):
    song1.calculateCompleteness()
    song2.calculateCompleteness()

    print(useColors[0] + (song1.path() or song1.description()) +
          TerminalColors.ENDC)
    print(useColors[1] + (song2.path() or song2.description()) +
          TerminalColors.ENDC)

    song1.loadMetadataInfo()
    song2.loadMetadataInfo()
    printDictsDiff(song1.metadata, song2.metadata, forcePrint=True)

    print('Completeness: %s%d%s <-> %s%d%s)' % (
          useColors[0], song1.completeness, TerminalColors.ENDC,
          useColors[1], song2.completeness, TerminalColors.ENDC))

    if song1.metadata == song2.metadata:
        print('Songs have identical metadata!')

    printPropertiesDiff(song1, song2, forcePrint=True)


def loadImageFromData(data):
    if not data:
        return None
    image = Image.open(io.BytesIO(data))
    return ImageDataTuple(image, data)


def loadImageFromAPEBinaryValue(obj):
    data = obj.value[obj.value.find(b'\x00') + 1:]
    image = Image.open(io.BytesIO(data))
    return ImageDataTuple(image, data)


def loadImageFromASFByteArrayAttribute(obj):
    try:
        data = obj.value[obj.value.find(b'\x00\x00\x00\x00\x00') + 5:]
        image = Image.open(io.BytesIO(data))
    except OSError as e:
        print("Error reading image from ASFByteArrayAttribute (%s):" % obj, e)
        raise
    return ImageDataTuple(image, data)


def extractAnyImageFromList(values):
    expandedList = [(key, val) for key, val in values.items()
                    if not isinstance(val, list)]
    for key, value in values.items():
        if key in ['WM/MCDI', 'WM/UserWebURL', 'CT_Custom', 'CT_MY_RATING']:
            continue

        if isinstance(value, list):
            for val in value:
                expandedList.append((key, val))
        else:
            expandedList.append((key, value))

    for key, value in expandedList:
        if isinstance(value, mutagen.apev2.APEBinaryValue):
            return loadImageFromAPEBinaryValue(value)

        if isinstance(value, mutagen.asf._attrs.ASFByteArrayAttribute):
            return loadImageFromASFByteArrayAttribute(value)

        if isinstance(value, mutagen.mp4.MP4Cover):
            return loadImageFromData(value)

        if isinstance(value, mutagen.id3.APIC) and value.data:
            return loadImageFromData(value.data)

    return None


def extractFrontCover(mutagenFile):
    for pic in getattr(mutagenFile, 'pictures', []):
        if pic.type == mutagen.id3.PictureType.COVER_FRONT:
            image = Image.open(io.BytesIO(pic.data))
            return ImageDataTuple(image, pic.data)

    if isinstance(getattr(mutagenFile, 'Cover Art (Front)', None),
                  mutagen.apev2.APEBinaryValue):
        return loadImageFromAPEBinaryValue(mutagenFile['Cover Art (Front)'])

    # print(mutagenFile)
    if ('WM/Picture' in mutagenFile and
       isinstance(mutagenFile['WM/Picture'][0],
                  mutagen.asf._attrs.ASFByteArrayAttribute)):
        return loadImageFromASFByteArrayAttribute(mutagenFile['WM/Picture'][0])

    if 'covr' in mutagenFile and isinstance(mutagenFile['covr'], list):
        return loadImageFromData(mutagenFile['covr'][0])

    if 'APIC:' in mutagenFile and isinstance(mutagenFile['APIC:'],
                                             mutagen.id3.APIC):
        return loadImageFromData(mutagenFile['APIC:'].data)

    return extractAnyImageFromList(mutagenFile)


def fixAPETextValuesWithEmptyMultipleValues(mutagenFile):
    for k, v in mutagenFile.items():
        if isinstance(v, mutagen.apev2.APETextValue) and v.value[-1] == '\x00':
            mutagenFile[k] = v.value[:-1]


def fixBrokenImages(mutagenFile):
    for k, v in mutagenFile.items():
        try:
            extractAnyImageFromList({k: v})
        except IOError:
            del mutagenFile[k]
            # mutagenFile['TPE1'] = mutagen.id3.TPE1(mutagen.id3.Encoding.UTF8,
            #                                        'test')


def printDictsDiff(dict1, dict2, forcePrint=False):
    # Calculate changes
    removedKeys = [x for x in dict1.keys() if x not in dict2.keys()]

    def is_changed(x):
        try:
            return (x in dict1 and dict1.get(x, None) != dict2.get(x, None))
        except ValueError:
            return True

    def is_in_dict1(x):
        try:
            return x in dict1.keys()
        except ValueError:
            return False

    changedKeys = [x for x in dict2.keys() if is_changed(x)]

    newKeys = [x for x in dict2.keys() if not is_in_dict1(x)]

#    changedKeys = [x for x in dict2.keys()
#                   if x in dict1 and dict1.get(x, None) != dict2.get(x, None)]
#    newKeys = [x for x in dict2.keys() if x not in dict1.keys()]

    if not forcePrint and not removedKeys and not changedKeys and not newKeys:
        return False

    allKeys = list(dict1.keys()) + [x for x in dict2.keys()
                                    if x not in dict1.keys()]
    allKeys.sort()
    # print('removed:', removedKeys)
    # print('changed:', changedKeys)
    # print('new    :', newKeys)

    # print(dict1.get('COMM::eng', None))
    # print(dict2.get('COMM::eng', None))
    def use_str_or_repr(x):
        return {True: str, False: repr}[all(hasattr(z, 'text') for z in x)]

    for k in sorted(allKeys):
        if k in changedKeys:
            try:
                str_repr = use_str_or_repr((dict1[k], dict2[k]))
            except ValueError:
                print(f'Error getting value for {k}')
                str_repr = '~~~'
            else:
                print(str(k), ':', TerminalColors.Highlight,
                      str_repr(dict1[k])[:100], TerminalColors.ENDC,
                      ' -> ', TerminalColors.Highlight,
                      str_repr(dict2[k])[:100], TerminalColors.ENDC)
        elif k in removedKeys:
            str_repr = use_str_or_repr((dict1[k],))
            print(str(k), ':', TerminalColors.First, str_repr(dict1[k])[:200],
                  TerminalColors.ENDC)
        elif k in newKeys:
            str_repr = use_str_or_repr((dict2[k],))
            print(str(k), ':', TerminalColors.Second, str_repr(dict2[k])[:200],
                  TerminalColors.ENDC)
        else:
            str_repr = use_str_or_repr((dict1[k],))
            print(str(k), ':', str_repr(dict1[k])[:200])

    return True


def formatLength(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, remseconds = divmod(remainder, 60)
    string = ''
    if hours:
        minformat = '%02d'
    else:
        minformat = '%d'

    if hours or minutes:
        minseconds = '%02d'
    else:
        minseconds = '%d'

    string = ':'.join([y % x for x, y in [(hours, '%d'), (minutes, minformat),
                                          (remseconds, minseconds)] if x])
    miliseconds = math.modf(remseconds)[0]
    if miliseconds:
        string += '{0:.3f}'.format(miliseconds)[1:]
    return string


def printPropertiesDiff(song1, song2, forcePrint=False):
    properties = [('', '_format', str),
                  (' s', 'length', formatLength),
                  (' bits/s', 'bitrate', str),
                  (' bits/sample', 'bits_per_sample', str),
                  (' channels', 'channels', str),
                  (' Hz', 'sample_rate', str)]
    values1 = []
    values2 = []
    for suffix, prop, propformatter in properties:
        try:
            val1 = getattr(song1.metadata.info, prop)
        except AttributeError:
            val1 = getattr(song1, prop)
        if callable(val1):
            val1 = val1()
        try:
            val2 = getattr(song2.metadata.info, prop)
        except AttributeError:
            val2 = getattr(song2, prop)
        if callable(val2):
            val2 = val2()
        if val1 and val2 and val1 == val2:
            values1.append(propformatter(val1) + suffix)
            values2.append(propformatter(val2) + suffix)
            continue
        if not val1:
            values1.append('-' + suffix)
        else:
            values1.append(TerminalColors.First + propformatter(val1) +
                           TerminalColors.ENDC + suffix)

        if not val2:
            values2.append('-' + suffix)
        else:
            values2.append(TerminalColors.Second + propformatter(val2) +
                           TerminalColors.ENDC + suffix)
    print('Properties: ' + ', '.join(values1))
    print('Properties: ' + ', '.join(values2))


def colorizeAll(color, text):
    return color + text + TerminalColors.ENDC


def colorizeTime(color, text):
    pos = text.find('.')
    if pos == -1:
        return colorizeAll(color, text)
    return color + text[:pos] + TerminalColors.ENDC + text[pos:]


def colorizeBps(color, text):
    pos = text.find('.')
    if pos == -1:
        return colorizeAll(color, text)
    pos -= 3
    return color + text[:pos] + TerminalColors.ENDC + text[pos:]


def getPropertiesAsString(song, colors={}):
    properties = [('', '_format', str, colorizeAll),
                  (' s', 'length', formatLength, colorizeTime),
                  (' s (w/o silences)', 'durationWithoutSilences',
                   formatLength, colorizeTime),
                  (' bits/s', 'bitrate', str, colorizeBps),
                  (' bits/sample', 'bits_per_sample', str, colorizeAll),
                  (' channels', 'channels', str, colorizeAll),
                  (' Hz', 'sample_rate', str, colorizeAll)]
    values = []
    for suffix, prop, propformatter, propcolorizer in properties:
        try:
            color = colors[prop]
        except KeyError:
            color = TerminalColors.Highlight
        try:
            val = getattr(song.metadata.info, prop)
        except AttributeError:
            val = getattr(song, prop)
        if callable(val):
            val = val()
        if not val:
            values.append(color + '-' + TerminalColors.ENDC + suffix)
        else:
            values.append(propcolorizer(color, propformatter(val)) + suffix)
    return ', '.join(values)


def printProperties(song):
    print('Properties: ' + getPropertiesAsString(song))


def fixTags(mutagenFile):
    # Save original values
    originalValues = {}
    originalValues.update(mutagenFile)

    # Apply fixes
    fixAPETextValuesWithEmptyMultipleValues(mutagenFile)
    fixBrokenImages(mutagenFile)

    # Print changes
    if not printDictsDiff(originalValues, mutagenFile):
        print('Nothing to be done for %s' % mutagenFile.filename)
        return False

    key = input('Do you want to write the changes? (y/n) ')
    if key == 'y':
        mutagenFile.save()

    return True


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096 * 1024), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def md5FromData(data):
    hash_md5 = hashlib.md5()
    hash_md5.update(data)
    return hash_md5.hexdigest()


def calculateFileSHA256(filething):
    def calculate(fileobj):
        hash_sha256 = hashlib.sha256()
        for chunk in iter(lambda: fileobj.read(4096 * 1024), b""):
            hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    if isinstance(filething, str):
        with open(filething, "rb") as f:
            sha256 = calculate(f)
    else:
        f = filething
        filething.seek(0)
        sha256 = calculate(f)

    return sha256


def calculateSHA256(filelike):
    hash_sha256 = hashlib.sha256()
    for chunk in iter(lambda: filelike.read(4096 * 1024), b""):
        hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def calculateSHA256_data(data):
    hash_sha256 = hashlib.sha256()
    hash_sha256.update(data)
    return hash_sha256.hexdigest()


def DecodedAudioPropertiesTupleFromDict(properties):
    messages = []
    for time_position, level, message in properties['messages']:
        messages.append(DecodeMessageRecord(time_position, level,
                                            message.decode("utf-8", "ignore")))
    if 'samples' not in properties:
        properties['decoded_duration'] = None
        properties['decoded_sample_format'] = None
        properties['decoded_sample_rate'] = None
        properties['decoded_bytes_per_sample'] = None
        properties['decoded_channels'] = None
        properties['is_planar'] = None
        properties['samples'] = None

    return DecodedAudioPropertiesTuple(**properties)._replace(
        messages=messages)


def decodeAudio(filething, **kwargs):
    if hasattr(filething, 'seek'):
        filething.seek(0)
        filecontents = filething.read()
        data, properties = bard_audiofile.decode(data=filecontents, **kwargs)
    else:
        data, properties = bard_audiofile.decode(path=filething, **kwargs)

    if config.config['enable_internal_checks']:
        files_pydub_cant_decode_correctly = \
            config.config['files_pydub_cant_decode_correctly']
        if hasattr(filething, 'seek'):
            filething.seek(0)
        audio_segment = AudioSegment.from_file(filething)
        if (audio_segment.raw_data != data and
                filething not in files_pydub_cant_decode_correctly):
            with open('/tmp/decoded-song-pydub.raw', 'wb') as f:
                f.write(audio_segment.raw_data)
            with open('/tmp/decoded-song-bard_audiofile.raw', 'wb') as f:
                f.write(data)
            raise Exception('DECODED AUDIO IS DIFFERENT BETWEEN '
                            'BARD_AUDIOFILE AND PYDUB')
        print('bard_audiofile/pydub decode check ' +
              TerminalColors.Ok + 'OK' + TerminalColors.ENDC)
    return data, DecodedAudioPropertiesTupleFromDict(properties)


def audioSegmentFromDataProperties(data, properties):
    return AudioSegment(data=data,
                        sample_width=properties.decoded_bytes_per_sample,
                        frame_rate=properties.sample_rate,
                        channels=properties.channels)


def windowsList():
    process = subprocess.run(['wmctrl', '-l'], stdout=subprocess.PIPE)
    lines = [x.split(maxsplit=3) for x in
             process.stdout.decode('utf-8').split('\n') if x]
    return [(x[0], x[3]) for x in lines]


def waitForWindowToOpen(title):
    while title not in [x[1] for x in windowsList()]:
        time.sleep(0.5)


def waitForWindowToClose(title):
    while title in [x[1] for x in windowsList()]:
        time.sleep(0.5)


def analyzeAudio(cmd, path):
    if cmd not in ['spek', 'audacity']:
        return None

    command = [cmd, path]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    return process


def manualAudioCmp(path1, path2, useColors=None):
    proc1 = analyzeAudio('spek', path1)
    proc2 = analyzeAudio('spek', path2)
    otherAction = ('a', '(A)udacity')
    omsg = 'Choose the preferred option (%s1%s/%s2%s/0 (equal)'
    if useColors:
        omsg = omsg % (useColors[0], TerminalColors.ENDC,
                       useColors[1], TerminalColors.ENDC)
    else:
        omsg = omsg % ('', '', '', '')

    omsg += '/%s/(Q)uit):'

    msg = omsg % otherAction[1]

    while True:
        option = input(msg).lower()
        if option == '1':
            r = -1
            break
        elif option == '2':
            r = 1
            break
        elif option == '0':
            r = 0
            break
        elif option == 'q':
            r = None
            break
        elif option == otherAction[0]:
            proc1.terminate()
            proc2.terminate()
            if option == 'a':
                proc1 = analyzeAudio('audacity', path1)
                waitForWindowToOpen('.aup')
                time.sleep(1)
                waitForWindowToClose('Recuperación automática')
                subprocess.run(['wmctrl', '-r', '.aup', '-N', 'Song 1'])
                proc2 = analyzeAudio('audacity', path2)
                waitForWindowToOpen('.aup')
                subprocess.run(['wmctrl', '-r', '.aup', '-N', 'Song 2'])
                otherAction = ('s', '(S)pek')
            elif option == 's':
                proc1 = analyzeAudio('spek', path1)
                proc2 = analyzeAudio('spek', path2)
                otherAction = ('a', '(A)udacity')
            msg = omsg % otherAction[1]

    proc1.terminate()
    proc2.terminate()

    return r


def simple_find_matching_square_bracket(txt, initial):
    count = 0
    for idx, c in enumerate(txt[initial:]):
        if c == '[':
            count += 1
        elif c == ']':
            count -= 1
            if count == 0:
                return idx + initial

    return None


def printableLen(text):
    """Return length of printable characters in string."""
    strip_ANSI_pat = re.compile(r"""\x1b\[[;\d]*[A-Za-z]""", re.VERBOSE)
    try:
        return len(strip_ANSI_pat.sub("", text))
    except TypeError:
        print(text, type(text))
        raise

def removeNonPrintableCharacters(text):
    if not text:
        return None
    r = ''.join(c for c in text if c.isprintable())
    return r if r else None

def alignColumns(lines, col_alignments=None):
    """Align columns of text.

    lines is a list containing lists of columns. The function returns a list
    of strings where the respective columns have been aligned. col_alignments
    can be passed as a list of boolean values for every column which specify
    if the column should be left aligned (True) or right aligned (False).
    """
    aligned = []
    if not lines:
        return []
    maxlengths = [max([printableLen(y) for y in x]) for x in zip(*lines)]
    maxlengths[-1] = 0

    if not col_alignments:
        col_alignments = [True for x in maxlengths]

    for cols in lines:
        newline = ''
        for col, maxlength, alignleft in zip(cols, maxlengths, col_alignments):
            num_spaces = maxlength - printableLen(col)
            if alignleft:
                newline += col + ' ' * (num_spaces + 1)
            else:
                newline += ' ' * num_spaces + col + ' '
        aligned.append(newline)
    return aligned


def cutStringAtMaxBytesLength(s, length):
    s = s[:length]
    while len(s.encode('utf-8')) > length:
        s = s[:-1]
    return s
