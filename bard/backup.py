# -*- coding: utf-8 -*-

from bard.config import config
from bard.musicdatabase import MusicDatabase
from bard.musicdatabase_songs import getSongsFromIDorPath, getSongsAtPath
from bard.utils import calculateSHA256_data, printSongsInfo, alignColumns
from bard.terminalcolors import TerminalColors as Color
from bard.percentage import Percentage
from bard.song import Song
import io
from pydub import AudioSegment
from functools import total_ordering, partial
from itertools import chain

import os
import sys
import stat
from datetime import datetime
import re
import paramiko


def isAudioFormat(filename):
    """Test if a filename extension is that of an audio format."""
    filename = re.sub(r'(~|\.partial~?[0-9]*)$', '', filename)
    ext = os.path.splitext(filename)[1][1:].lower()
    return ext.strip('~') in ['mp3', 'flac', 'mp4', 'm4a', 'wv', 'ape', 'ogg',
                              'asf', 'mpc', 'wma', 'vorbis']


def parse_ssh_uri(uri):
    """Return the username, host and path of a ssh uri."""
    m = re.match(r'(\w*)@(\w*):([\w/\-_]*)', uri)
    if m:
        return m.groups()
    return None


def remoteFile(path, sftp):
    data = None
    percentage = Percentage()

    def proc(x, y):
        percentage.max_value = y
        percentage.set_value(x)

    data = io.BytesIO()
    print('Downloading... ', end='')
    sftp.getfo(path, data, proc)
    print('')
    data.seek(0)

    return data


def uploadFile(srcpath, tgtpath, sftp):
    percentage = Percentage()

    def proc(x, y):
        percentage.max_value = y
        percentage.set_value(x)

    print(' ... ', end='')
    tmptgtpath = tgtpath + '.partial'
    try:
        suffix = 1
        while sftp.stat(tmptgtpath):
            tmptgtpath = tgtpath + f'.partial~{suffix}'
            suffix += 1
    except FileNotFoundError:
        pass
    sftp.put(srcpath, tmptgtpath, proc)
    sftp.posix_rename(tmptgtpath, tgtpath)
    print('')


def remoteFileAudioSha256Sum(path, sftp):
    data = remoteFile(path, sftp)
    if not data:
        return None
    audio_segment = AudioSegment.from_file(data)
    return calculateSHA256_data(audio_segment.raw_data)


def remoteSong(path, sftp):
    try:
        data = remoteFile(path, sftp)
    except FileNotFoundError:
        print(f'File {path} not found')
        raise
    if not data:
        return None

    s = Song(None, data=data)
    try:
        desc = '@' + sftp.remote_hostname + ':' + path
    except AttributeError:
        desc = '@:' + path
    s.setDescription(desc)
    return s


def remoteWalk(path, sftp, deep_first=False):
    dirs = []
    nondirs = []
    for f_attr in sftp.listdir_attr(path):
        if stat.S_ISDIR(f_attr.st_mode):
            dirs.append(f_attr)
        else:
            nondirs.append(f_attr)

    if not deep_first:
        yield path, dirs, nondirs

    for dirname in dirs:
        newpath = os.path.join(path, dirname.filename)
        yield from remoteWalk(newpath, sftp, deep_first=deep_first)

    if deep_first:
        yield path, dirs, nondirs


def stat_size_and_date(path, attr=None):
    if not attr:
        attr = os.stat(path)
    date = datetime.fromtimestamp(int(attr.st_mtime))
    return (Color.Size + str(attr.st_size) + Color.ENDC,
            Color.DateTime + str(date) + Color.ENDC)


class SizeBalance:
    """Represents the space balance of a task."""

    def __init__(self, transfer_size=0, disk_balance=0, remote_remove=0):
        """Create a size balance object."""
        self.transfer_size = transfer_size
        self.disk_balance = disk_balance
        self.remote_remove = remote_remove

    def __add__(self, other):
        return SizeBalance(self.transfer_size + other.transfer_size,
                           self.disk_balance + other.disk_balance,
                           self.remote_remove + other.remote_remove)

    def __iadd__(self, other):
        self.transfer_size += other.transfer_size
        self.disk_balance += other.disk_balance
        self.remote_remove += other.remote_remove
        return self


def print_change_description(descs, prefix='', end='\n'):
    if isinstance(descs, tuple):
        print(prefix + ' '.join(descs), end=end)
        return
    print(prefix + '\n'.join(alignColumns(descs, (True, True, False, True))),
          end=end)


@total_ordering
class Task:
    """Base class for Tasks."""

    removed_sign = Color.Removed + '✗' + Color.ENDC
    new_sign = Color.New + '📤' + Color.ENDC
    modified_sign = Color.Modified + '🔃' + Color.ENDC
    equal_sign = ' '

    def __init__(self, source=None, target=None, src_attr=None, tgt_attr=None):
        """Define the base elements of a task."""
        self.source = source
        self.target = target
        try:
            self.basename = os.path.basename(source)
        except TypeError:
            self.basename = os.path.basename(target)

        self.src_attr = src_attr
        self.tgt_attr = tgt_attr
        self.overwrite = False

    def set_overwrite(self, overwrite):
        self.overwrite = overwrite

    def requires_confirmation(self):
        return False

    def is_src_file(self):
        return stat.S_ISREG(self.src_attr.st_mode)

    def is_src_dir(self):
        return stat.S_ISDIR(self.src_attr.st_mode)

    def is_tgt_file(self):
        return stat.S_ISREG(self.tgt_attr.st_mode)

    def is_tgt_dir(self):
        return stat.S_ISDIR(self.tgt_attr.st_mode)

    def __lt__(self, other):
        if hasattr(self, 'source') and hasattr(other, 'source'):
            return self.source < other.source
        if hasattr(self, 'target') and hasattr(other, 'target'):
            return self.target < other.target
        return False

    def __eq__(self, other):
        if hasattr(self, 'source') and hasattr(other, 'source'):
            return self.source == other.source
        if hasattr(self, 'target') and hasattr(other, 'target'):
            return self.target == other.target
        return False


class Upload(Task):
    """Upload class."""

    def __init__(self, source, target, src_attr, tgt_attr):
        """Create an upload task to copy a local file to remote."""
        super(Upload, self).__init__(source, target, src_attr, tgt_attr)

    def describe_change(self):
        if self.tgt_attr:
            if self.src_attr.st_size == self.tgt_attr.st_size:
                size = Color.Size + str(self.src_attr.st_size) + Color.ENDC
            else:
                size = ('%s -> %s' %
                        (Color.Size + str(self.src_attr.st_size) + Color.ENDC,
                         Color.Size + str(self.tgt_attr.st_size) + Color.ENDC))

            src_date = datetime.fromtimestamp(int(self.src_attr.st_mtime))
            tgt_date = datetime.fromtimestamp(int(self.tgt_attr.st_mtime))

            if src_date == tgt_date:
                date = Color.DateTime + str(src_date) + Color.ENDC
            else:
                date = ('%s -> %s' %
                        (Color.DateTime + str(src_date) + Color.ENDC,
                         Color.DateTime + str(tgt_date) + Color.ENDC))

            return [(Task.modified_sign,
                     Color.Filename + self.basename + Color.ENDC,
                     size, date)]

        src_date = datetime.fromtimestamp(int(self.src_attr.st_mtime))
        return [(Task.new_sign, Color.Filename + self.basename + Color.ENDC,
                 Color.Size + str(self.src_attr.st_size) + Color.ENDC,
                 Color.DateTime + str(src_date) + Color.ENDC)]

    def hasRemoteFile(self):
        return self.tgt_attr is not None

    def requires_confirmation(self):
        return self.tgt_attr is not None

    def compareAudioFiles(self, source, target, sftp):
        print('Comparing songs...')

        # src_song = getSongsAtPath(source, exact=True)[0]
        src_song = Song(source)
        tgt_song = remoteSong(target, sftp)
        basename = os.path.basename(source)
        colors = (Color.First, Color.Second)
        printSongsInfo(src_song, tgt_song, useColors=colors)
        if src_song.audioSha256sum() == tgt_song.audioSha256sum():
            print(f'{basename} has exactly the same audio in source and '
                  'target files')
        else:
            print(f'Audio tracks are different in local and remote files')
            comparison = src_song.audioCmp(tgt_song)
            print(comparison)
            tgt_audio_sha256 = tgt_song.audioSha256sum()
            song_ids = MusicDatabase.songsByAudioTrackSha256sum(
                tgt_audio_sha256)
            same_audio_songs = [getSongsFromIDorPath(songID)[0]
                                for songID in song_ids]

            if tgt_audio_sha256 and same_audio_songs:
                d = 'Files with exact same audio:\n'
                d += '\n'.join('      ' + Color.CantCompareSongs +
                               song.path() + Color.ENDC
                               for song in same_audio_songs)
                print(d)
            else:
                print(f'WARNING: The target file {target} will be overwritten '
                      'but has a unique audio track')
        return False

    def compareDirectories(self, source, target, sftp):
        for dirpath, dirnames, filenames in os.walk(source, topdown=True):
            print('----')
            print(source)
            print(dirpath)
            print(target, dirpath)
            print(filenames)
        return False

    def compareChanges(self, sftp):
        if not self.hasRemoteFile():
            return True

        if self.is_src_file() and isAudioFormat(self.source):
            return self.compareAudioFiles(self.source, self.target, sftp)

        if self.is_src_dir():
            return self.compareDirectories(self.source, self.target, sftp)

        return True

    def run(self, sftp):
        print_change_description(prefix="Uploading ",
                                 descs=self.describe_change(), end='')

        uploadFile(self.source, self.target, sftp)
        sftp.chmod(self.target, self.src_attr.st_mode)
        sftp.utime(self.target, (self.src_attr.st_atime,
                                 self.src_attr.st_mtime))

        src_size = self.src_attr.st_size
        try:
            tgt_size = self.tgt_attr.st_size
        except AttributeError:
            tgt_size = None
        if tgt_size and self.overwrite:
            return SizeBalance(transfer_size=src_size,
                               disk_balance=src_size - tgt_size)

        return SizeBalance(transfer_size=src_size,
                           disk_balance=src_size)


class CreateRemoteDir(Task):
    """CreateRemoteDir class."""

    def __init__(self, source, target, src_attr):
        """Create a copy of the source directory remotely."""
        super(CreateRemoteDir, self).__init__(source, target, src_attr)

    def describe_change(self):
        date = datetime.fromtimestamp(int(self.src_attr.st_mtime))
        return [(Task.new_sign,
                 Color.Filename + self.basename + Color.ENDC,
                 '<DIR>',
                 Color.DateTime + str(date) + Color.ENDC)]

    def requires_confirmation(self):
        return False

    def run(self, sftp):
        print_change_description(prefix="Creating directory ",
                                 descs=self.describe_change())
        sftp.mkdir(self.target, self.src_attr.st_mode)
        sftp.utime(self.target, (self.src_attr.st_atime,
                                 self.src_attr.st_mtime))
        return SizeBalance(disk_balance=4096)


class RemoveRemote(Task):
    """RemoveRemote class."""

    def __init__(self, source, target, src_attr=None, tgt_attr=None):
        """Create an RemoveRemote task to remove a remote file."""
        super(RemoveRemote, self).__init__(source, target, src_attr, tgt_attr)

        self.same_audio_songs = {}
        self.remote_attr_cache = {}

    def describe_change(self, verbose=False):
        is_dir = stat.S_ISDIR(self.tgt_attr.st_mode)
        size_or_dir = '<DIR>' if is_dir else str(self.tgt_attr.st_size)
        date = datetime.fromtimestamp(int(self.tgt_attr.st_mtime))

        d = (Task.removed_sign, Color.Filename + self.basename + Color.ENDC,
             Color.Size + size_or_dir + Color.ENDC,
             Color.DateTime + str(date) + Color.ENDC)
        if not verbose:
            return [d]

        r = []
        if is_dir or self.target not in self.same_audio_songs:
            r.append(d)

        for filename, same_songs in self.same_audio_songs.items():
            if same_songs:
                attr = self.remote_attr_cache.get(filename)
                size, date = stat_size_and_date(filename, attr=attr)
                d = (Task.removed_sign, Color.Filename + filename + Color.ENDC,
                     size, date)
                r.append(d)
                for song in same_songs:
                    attr = self.remote_attr_cache.get(song.path())
                    size, date = stat_size_and_date(song.path(), attr=attr)
                    d = ('', '   =👌 ' + Color.CantCompareSongs +
                         song.path() + Color.ENDC, size, date)
                    r.append(d)
            else:
                attr = self.remote_attr_cache.get(filename)
                size, date = stat_size_and_date(filename, attr=attr)
                d = (Task.removed_sign, Color.Filename + filename + Color.ENDC,
                     Color.Size + size + Color.ENDC,
                     Color.DateTime + str(date) + Color.ENDC)
                r.append(d)

        return r

    def requires_confirmation(self):
        return True

    def songsWithSameAudio(self, song, sftp):
        tgt_audio_sha256 = song.audioSha256sum()
        # self.remoteFileAudioSha256Sum(target)
        print(tgt_audio_sha256)

        song_ids = MusicDatabase.songsByAudioTrackSha256sum(tgt_audio_sha256)
        return [getSongsFromIDorPath(song_id)[0] for song_id in song_ids]

    def compareRemoteDirectory(self, target, sftp):
        for dirname, d_attrs, f_attrs in remoteWalk(target, sftp):
            for f_attr in sorted(f_attrs, key=lambda x: x.filename):
                filename = f_attr.filename
                print(filename)
                if isAudioFormat(filename):
                    path = os.path.join(dirname, filename)
                    song = remoteSong(path, sftp)
                    same_audio = self.songsWithSameAudio(song, sftp)
                    self.same_audio_songs.setdefault(path,
                                                     []).extend(same_audio)
                    self.remote_attr_cache[path] = f_attr

    def compareChanges(self, sftp):
        if self.is_tgt_file() and isAudioFormat(self.target):
            song = remoteSong(self.target, sftp)
            same_audio = self.songsWithSameAudio(song, sftp)
            self.same_audio_songs.setdefault(self.target,
                                             []).extend(same_audio)
            self.remote_attr_cache[self.target] = self.tgt_attr
        elif self.is_tgt_dir():
            self.compareRemoteDirectory(self.target, sftp)
        d = self.describe_change(verbose=True)
        print_change_description(d)
        return False

    def run(self, sftp):
        print_change_description(prefix="Removing remote ",
                                 descs=self.describe_change())
        if stat.S_ISDIR(self.tgt_attr.st_mode):
            for path, d_attrs, f_attrs in remoteWalk(self.target, sftp,
                                                     deep_first=True):
                for f_attr in sorted(f_attrs, key=lambda x: x.filename):
                    filename = f_attr.filename
                    fullpath = os.path.join(path, filename)
                    print('rm', fullpath)
                    sftp.remove(fullpath)
                for d_attr in d_attrs:
                    dirname = d_attr.filename
                    fullpath = os.path.join(path, dirname)
                    print('rmdir', fullpath)
                    sftp.rmdir(fullpath)

            sftp.rmdir(self.target)
        else:
            sftp.remove(self.target)

        return SizeBalance(disk_balance=-self.tgt_attr.st_size,
                           remote_remove=self.tgt_attr.st_size)


class BackupMusic:
    def __init__(self, source, target):
        """Create a BackupMusic object."""
        self.ask_stored_questions = True
        self.source = source
        self.target_prefix = source.replace('/', '_').strip('_')
        self.target = target
        self.username, self.server, self.path = parse_ssh_uri(target)
        self.ssh = paramiko.SSHClient()
        self.ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh",
                                "known_hosts")))
        try:
            self.ssh.connect(self.server, username=self.username)
        except paramiko.ssh_exception.SSHException as e:
            print(f'Error connecting to {self.server}: {e}')
            return

        self.sftp = self.ssh.open_sftp()
        self.sftp.remote_hostname = self.server

    def isValid(self):
        return hasattr(self, 'sftp')

    def targetPath(self, srcpath):
        if not srcpath.startswith(self.source):
            return None

        return os.path.normpath(self.path + '/' + self.target_prefix + '/' +
                                srcpath[len(self.source):])

    def compareSrcAndTgt(self, srcpath, tgtpath, remoteDirCache={}):
        srcstat = os.lstat(srcpath)
        try:
            try:
                tgtstat = remoteDirCache[tgtpath]
            except KeyError:
                tgtstat = self.sftp.lstat(tgtpath)
        except FileNotFoundError:
            return True, False, srcstat, None

        r = (srcstat.st_mode != tgtstat.st_mode or
             srcstat.st_size != tgtstat.st_size or
             int(srcstat.st_mtime) != int(tgtstat.st_mtime))
        return r, r, srcstat, tgtstat

    def askUser(self, txt, options, options_long, helpers={}):
        def_opts = [x for x in options if x.isupper()]
        default = def_opts[0].lower() if len(def_opts) == 1 else None
        options.append('?')
        options_long.append('(?) This help')

        key = None
        while key not in options:
            key = input(txt + '(' + '/'.join(options) + ') : ')
            if key == '?':
                key = input('\n' + '\n'.join(options_long) + '\n')
            if default and (key == '' or key == default):
                return default
            if key in helpers.keys():
                helpers[key]()
                key = ''

        return key

    def compareChangesInTasks(self, tasks):
        tasks_to_compare = [t for t in tasks if hasattr(t, 'compareChanges')]
        if not tasks_to_compare:
            return

        for idx, task in enumerate(tasks_to_compare):
            skip = task.compareChanges(self.sftp)
            if skip:
                print('Skipping', task.source or task.target)
                continue

            if idx < len(tasks_to_compare) - 1:
                options = ['y', 'N']
                options_long = ['(y)es, continue comparing the next song',
                                '(N)o, finish comparing songs']
                txt = 'Continue comparing songs?'
                user_input = self.askUser(txt, options, options_long)
                if user_input == 'n':
                    break
            else:
                input('Press Enter to continue')
        return

    def listDir(self, path, pending_changes=[], recursive=False, remote=False):
        remote_str = 'remote' if remote else 'local'
        print(f'Listing contents of {remote_str} directory:')
        descs = []
        inherited_symbols = {}
        if remote:
            walk_generator = remoteWalk(path, self.sftp)
            attribute = 'target'
            look_sign = '🔭'
        else:
            walk_generator = os.walk(path)
            attribute = 'source'
            look_sign = '🔍'

        def getattribute(c):
            return getattr(c, attribute, None)

        for dirpath, dirnames, filenames in walk_generator:
            change = [c for c in pending_changes if dirpath == getattribute(c)]
            if change:
                d = change[0].describe_change()
                d[0] = (d[0][0], dirpath + ':', d[0][2], d[0][3])
                descs.extend(d)
                current_symbol = d[0][0]
                inherited_symbols[dirpath + '/'] = current_symbol
            else:
                for path in sorted(inherited_symbols.keys(), reverse=True):
                    if (dirpath + '/').startswith(path):
                        current_symbol = inherited_symbols[path]
                        break
                else:
                    current_symbol = ''
                d = (current_symbol or look_sign, dirpath + ':', '', '')
                descs.append(d)
            if remote:
                attributes_f = {attr.filename: attr for attr in filenames}
                attributes_d = {attr.filename: attr for attr in dirnames}
                filenames = list(attributes_f.keys())
                dirnames = list(attributes_d.keys())

            filenames.sort()
            dirnames.sort()

            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                change = [c for c in pending_changes
                          if filepath == getattribute(c)]
                if change:
                    descs.extend(change[0].describe_change())
                    continue

                if remote:
                    attr = attributes_f[filename]
                else:
                    attr = os.stat(filepath)
                date = datetime.fromtimestamp(int(attr.st_mtime))
                d = (current_symbol, Color.Filename + filename + Color.ENDC,
                     Color.Size + str(attr.st_size) + Color.ENDC,
                     Color.DateTime + str(date) + Color.ENDC)
                descs.append(d)

            for filename in dirnames:
                filepath = os.path.join(dirpath, filename)
                change = [c for c in pending_changes
                          if filepath == getattribute(c)]
                if change:
                    descs.extend(change[0].describe_change())
                    continue

                if remote:
                    attr = attributes_d[filename]
                else:
                    attr = os.stat(filepath)
                date = datetime.fromtimestamp(int(attr.st_mtime))
                d = (current_symbol, Color.Filename + filename + Color.ENDC,
                     Color.Size + '<DIR>' + Color.ENDC,
                     Color.DateTime + str(date) + Color.ENDC)
                descs.append(d)
            if not recursive:
                break
        print_change_description(descs)
        print('')

    def listRemoteDir(self, path, pending_changes=[], recursive=False):
        self.listDir(path, pending_changes, recursive, remote=True)

    def listLocalDir(self, path, pending_changes=[], recursive=False):
        self.listDir(path, pending_changes, recursive, remote=False)

    def performBackup(self):
        size_balance = SizeBalance()
        user_input = ''

        for dirpath, dirnames, filenames in os.walk(self.source, topdown=True):
            print(dirpath)
            filenames.sort()
            dirnames.sort()
            target_dirpath = self.targetPath(dirpath)

            remoteDirCache = {os.path.join(target_dirpath, x.filename): x
                              for x in self.sftp.listdir_attr(target_dirpath)}
            pending_changes = []
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                target_path = self.targetPath(path)
                shouldCopy, isDifferent, src_attr, tgt_attr = \
                    self.compareSrcAndTgt(path, target_path, remoteDirCache)
                if shouldCopy:
                    upload = Upload(path, target_path, src_attr, tgt_attr)
                    pending_changes.append(upload)

            for dirname in dirnames:
                path = os.path.join(dirpath, dirname)
                target_path = self.targetPath(path)

                try:
                    attr = remoteDirCache[target_path]
                    if not stat.S_ISDIR(attr.st_mode):
                        print('Directory %s is a file in target %s (%s)' %
                              (Color.Filename + path + Color.ENDC,
                               Color.Host + self.target + Color.ENDC,
                               Color.Filename + target_path + Color.ENDC))
                        sys.exit(1)
                except (KeyError, FileNotFoundError):
                    src_attr = os.stat(path)
                    upload = CreateRemoteDir(path, target_path, src_attr)
                    pending_changes.append(upload)

            try:
                attr = self.sftp.stat(target_dirpath)
                iterate_tgt_dirpath = stat.S_ISDIR(attr.st_mode)
            except FileNotFoundError:
                iterate_tgt_dirpath = False

            if iterate_tgt_dirpath:
                for f_attr in remoteDirCache.values():
                    is_file = stat.S_ISREG(f_attr.st_mode)
                    is_dir = stat.S_ISDIR(f_attr.st_mode)
                    if ((is_file and f_attr.filename not in filenames) or
                            (is_dir and f_attr.filename not in dirnames)):
                        tgt_filename = os.path.join(target_dirpath,
                                                    f_attr.filename)
                        path = os.path.join(dirpath, f_attr.filename)
                        remove = RemoveRemote(path, tgt_filename,
                                              tgt_attr=f_attr)
                        pending_changes.append(remove)

            if any(c.requires_confirmation() for c in pending_changes):
                pending_changes.sort()
                if any(isinstance(c, RemoveRemote) for c in pending_changes):
                    descs = [c.describe_change()
                             for c in pending_changes]
                else:
                    descs = [c.describe_change()
                             for c in pending_changes
                             if c.requires_confirmation()]
                descs = [x for x in chain(*descs)]
                aligned_descs = alignColumns(descs, (True, True, False, True))

                txt = ('The following changes in %s require confirmation.\n'
                       '%s\n'
                       f'Submit changes to %s? \n' %
                       (Color.Filename + dirpath + Color.ENDC,
                        '\n'.join(aligned_descs),
                        Color.Host + self.server + Color.ENDC + ':' +
                        Color.Filename + target_dirpath + Color.ENDC))
                if user_input not in ['a', 'l']:
                    options = ['S', 'a', 'k', 'l', 'p', 'c',
                               'll', 'lr', 'llr', 'lrr']
                    helpers = {'c': partial(self.compareChangesInTasks,
                                            tasks=pending_changes),
                               'll': partial(self.listLocalDir,
                                             path=dirpath,
                                             pending_changes=pending_changes),
                               'lr': partial(self.listRemoteDir,
                                             path=target_dirpath,
                                             pending_changes=pending_changes),
                               'llr': partial(self.listLocalDir,
                                              path=dirpath,
                                              pending_changes=pending_changes,
                                              recursive=True),
                               'lrr': partial(self.listRemoteDir,
                                              path=target_dirpath,
                                              pending_changes=pending_changes,
                                              recursive=True)}
                    options_long = ['(s)ubmit', 'submit (a)lways',
                                    '(k)eep remote files', 'keep a(l)ways',
                                    'ski(p)', '(c)ompare',
                                    '(ll) list local', '(lr) list remote',
                                    '(llr) list local recursive',
                                    '(lrr) list remote recursive']
                    user_input = self.askUser(txt, options, options_long,
                                              helpers)
                else:
                    print(txt + user_input)

                for change in pending_changes:
                    if not change.requires_confirmation():
                        size_balance += change.run(self.sftp)
                        continue

                    if user_input == 'p':
                        continue

                    change.set_overwrite(user_input in ['s', 'a'])

                    size_balance += change.run(self.sftp)
            else:  # changes don't require confirmation
                for change in pending_changes:
                    size_balance += change.run(self.sftp)

        print('---------------------------------------')
        # print(f'Backing up: {self.source}')
        # print(f'to:         {self.target}')
        # print('')
        # print(f'Size of files to copy: {size_to_copy}')
        # print(f'Size to remove       : {size_to_remove}')
        # print(f'Size used in target  : {size_used_in_target}')
        # print('')
        # print('New files to backup: ', len(new_files_to_copy))
        # print('Files to remove from backup: ', len(files_to_remove))
        # print('Files to copy overwriting  : ',
        #       len(files_to_copy_overwriting))
        # print('Files to copy keeping tgt  : ',
        #       len(files_to_copy_without_overwrite))
        # print('Directories to remove from backup : ', len(dirs_to_remove))
        # print('---------------------------------------')

    def __del__(self):
        if self.isValid():
            self.sftp.close()
        self.ssh.close()


def backupMusic(target):
    print(f'Backup to {target}')
    target_config = config['backups'][target]
    for path in config['musicPaths']:
        try:
            target = target_config[path]
        except KeyError:
            target = target_config['']

        backup = BackupMusic(path, target)
        if not backup.isValid():
            continue
        backup.performBackup()
