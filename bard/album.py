from os.path import basename, dirname, join, exists
import re


patterns = [re.compile(f'{medium}[0-9]*')
            for medium in ('CD', 'LP', 'DVD', 'BD', 'SACD')]


def isMediumPath(path):
    return any(pat.match(path) for pat in patterns)


def albumPath(filePath=None, dirPath=None):
    if filePath:
        directory = dirname(filePath)
    elif dirPath:
        directory = dirPath
    else:
        raise ValueError('Either filePath or dirPath have to be set')
    if isMediumPath(basename(directory)):
        return dirname(directory)
    return directory


def coverAtPath(path):
    for cover in ['cover.jpg', 'cover.png']:
        coverfilename = join(path, cover)
        if exists(coverfilename):
            return coverfilename
    return None
