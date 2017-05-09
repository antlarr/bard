# import subprocess
import hashlib
import mutagen
import mutagen.mp3
import mutagen.mp4
import mutagen.easymp4
import mutagen.monkeysaudio
import mutagen.asf
import mutagen.flac
import mutagen.wavpack
from PIL import Image
from bard.terminalcolors import TerminalColors
import io
# import os
# import shutil
# import tempfile


def loadImageFromData(data):
    if not data:
        return None
    image = Image.open(io.BytesIO(data))
    return (image, data)


def loadImageFromAPEBinaryValue(obj):
    data = obj.value[obj.value.find(b'\x00') + 1:]
    image = Image.open(io.BytesIO(data))
    return (image, data)


def loadImageFromASFByteArrayAttribute(obj):
    try:
        data = obj.value[obj.value.find(b'\x00\x00\x00\x00\x00') + 5:]
        image = Image.open(io.BytesIO(data))
    except OSError as e:
        print("Error reading image from ASFByteArrayAttribute (%s):" % obj, e)
        raise
#        return None
    return (image, data)


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
            return image, pic.data

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
