# -*- coding: utf-8 -*-

import subprocess
import time
import hashlib
import audioread
import mutagen
import mutagen.mp3
import mutagen.mp4
import mutagen.easymp4
import mutagen.monkeysaudio
import mutagen.asf
import mutagen.flac
import mutagen.wavpack
from collections import namedtuple
from PIL import Image
from bard.terminalcolors import TerminalColors
import io
# import tempfile

ImageDataTuple = namedtuple('ImageDataTuple', ['image', 'data'])


def printSongsInfo(song1, song2,
                   useColors=(TerminalColors.FAIL, TerminalColors.OKGREEN)):
    song1.calculateCompleteness()
    song2.calculateCompleteness()

    print(useColors[0] + song1.path() + TerminalColors.ENDC)
    print(useColors[1] + song2.path() + TerminalColors.ENDC)

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
#        return None
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
    changedKeys = [x for x in dict2.keys()
                   if x in removedKeys and
                   dict2.get(x, None) != dict1.get(x, None)]
    newKeys = [x for x in dict2.keys() if x not in dict1.keys()]

    if not forcePrint and not removedKeys and not changedKeys and not newKeys:
        return False

    allKeys = list(dict1.keys()) + [x for x in dict2.keys()
                                    if x not in dict1.keys()]
    allKeys.sort()
    print(removedKeys)
    print(changedKeys)
    print(newKeys)

    print(dict1.get('COMM::eng', None))
    print(dict2.get('COMM::eng', None))
    for k in allKeys:
        if k in changedKeys:
            print(str(k), ':', TerminalColors.WARNING, repr(dict1[k])[:50],
                  TerminalColors.ENDC, ' -> ', TerminalColors.WARNING,
                  str(dict2[k])[:50], TerminalColors.ENDC)
        elif k in removedKeys:
            print(str(k), ':', TerminalColors.FAIL, repr(dict1[k])[:100],
                  TerminalColors.ENDC)
        elif k in newKeys:
            print(str(k), ':', TerminalColors.OKGREEN, repr(dict2[k])[:100],
                  TerminalColors.ENDC)
        else:
            print(str(k), ':', repr(dict1[k])[:100])

    return True


def printPropertiesDiff(song1, song2, forcePrint=False):
    properties = [('', '_format', str),
                  (' s', 'length', lambda x: '%03g' % x),
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
            values1.append(TerminalColors.FAIL + propformatter(val1) +
                           TerminalColors.ENDC + suffix)

        if not val2:
            values2.append('-' + suffix)
        else:
            values2.append(TerminalColors.OKGREEN + propformatter(val2) +
                           TerminalColors.ENDC + suffix)
    print('Properties: ' + ', '.join(values1))
    print('Properties: ' + ', '.join(values2))


def printProperties(song):
    properties = [('', '_format'),
                  (' s', 'length'),
                  (' bits/s', 'bitrate'),
                  (' bits/sample', 'bits_per_sample'),
                  (' channels', 'channels'),
                  (' Hz', 'sample_rate')]
    values = []
    for suffix, prop in properties:
        try:
            val = getattr(song.metadata.info, prop)
        except AttributeError:
            val = getattr(song, prop)
        if callable(val):
            val = val()
        if not val:
            values.append('-' + suffix)
        else:
            values.append(TerminalColors.WARNING + str(val) +
                          TerminalColors.ENDC + suffix)

    print('Properties: ' + ', '.join(values))


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

    # print('Before:')
    # for k, v in originalValues.items():
    #     msg = '%s : %s' % (str(k), repr(v)[:100])
    #     if k in changedKeys:
    #         print(TerminalColors.WARNING + msg + TerminalColors.ENDC)
    #     elif k in removedKeys:
    #         print(TerminalColors.FAIL + msg + TerminalColors.ENDC)
    #     else:
    #         print(msg)
    #
    #  print('')
    # print('After:')
    # for k, v in mutagenFile.items():
    #     msg = '%s : %s' % (str(k), repr(v)[:100])
    #     if k in changedKeys:
    #         print(TerminalColors.WARNING + msg + TerminalColors.ENDC)
    #     else:
    #         print(msg)
    # print('')

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


def calculateFileSHA256(filename):
    hash_sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096 * 1024), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def calculateSHA256(filelike):
    hash_sha256 = hashlib.sha256()
    for chunk in iter(lambda: filelike.read(4096 * 1024), b""):
        hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def removeAllTagsFromPath(path):
    # subprocess.check_output(['id3v2', '--delete-all', path])
    mutagenFile = mutagen.File(path)
    print(type(mutagenFile), path)

    if isinstance(mutagenFile, mutagen.flac.FLAC):
        mutagenFile.clear_pictures()
        mutagenFile.delete(path)
        # mutagenFile.save(path, deleteid3=True, padding=lambda x: 0)
        return
    elif isinstance(mutagenFile, mutagen.id3.ID3FileType):
        mutagenFile.delete(path)
        return
    elif isinstance(mutagenFile, mutagen.apev2.APEv2File):
        mutagenFile.delete(path)
        return

    mutagenFile.delete(path)


def removeAllTags(filelike, recurse=True):
    try:
        filelike.seek(0)
        id3 = mutagen.id3.ID3(filelike)
    except mutagen.id3._util.ID3NoHeaderError:
        pass
    else:
        filelike.seek(0)
        id3.delete(filelike)

    filelike.seek(0)
    mutagenFile = mutagen.File(filelike)
    # print(type(mutagenFile), filelike.name)

    if isinstance(mutagenFile, mutagen.flac.FLAC) and mutagenFile.pictures:
        mutagenFile.clear_pictures()
        filelike.seek(0)
        mutagenFile.save(filelike, padding=lambda x: 0)

    filelike.seek(0)
    if mutagenFile:
        mutagenFile.delete(filelike)


def calculateAudioTrackSHA256(path, tmpdir='/tmp'):
    # extension=path[path.rfind('.'):]
    # (fn, tmpfilename) = tempfile.mkstemp(suffix=extension, dir=tmpdir)

    filelike = io.BytesIO(open(path, 'rb').read())
    filelike.name = path
    # filelike.filename = path
    # print(path, tmpfilename)
    # try:
    removeAllTags(filelike)
    # shutil.copyfile(path, tmpfilename)
    # removeAllTags(tmpfilename)
    # if os.path.getsize(tmpfilename) >= os.path.getsize(path):
    #     print('Error removing tags from %s (%d >= %d)' % \
    #           (path, os.path.getsize(tmpfilename), os.path.getsize(path)))
    print(len(filelike.getvalue()))
    # open('/tmp/output9.mp3','wb').write(filelike.getvalue())
    filelike.seek(0)
    return calculateSHA256(filelike)
    # finally:
    #     os.close(fn)
    #     os.unlink(tmpfilename)

    # return None


def calculateAudioTrackSHA256_audioread(path):
    hash_sha256 = hashlib.sha256()
    with audioread.audio_open(path) as audiofile:
        for block in audiofile:
            hash_sha256.update(block)
    return hash_sha256.hexdigest()


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
