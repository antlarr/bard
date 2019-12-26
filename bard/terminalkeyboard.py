# -*- coding: utf-8 -*-
# See https://en.wikipedia.org/wiki/ANSI_escape_code for reference

from bard.terminalcolors import TerminalColors
import termios
import enum
import sys
import fcntl
import os


class TerminalKey(enum.Enum):
    KEY_UP = '\033[A'
    KEY_DOWN = '\033[B'
    KEY_RIGHT = '\033[C'
    KEY_LEFT = '\033[D'
    KEY_INSERT = '\033[2~'
    KEY_SUPR = '\033[3~'
    KEY_PREVPAG = '\033[5~'
    KEY_NEXTPAG = '\033[6~'
    KEY_HOME = '\033[H'
    KEY_END = '\033[F'
    KEY_F1 = '\033OP'
    KEY_F2 = '\033OQ'
    KEY_F3 = '\033OR'
    KEY_F4 = '\033OS'
    KEY_F5 = '\033[15~'
    KEY_F6 = '\033[17~'
    KEY_F7 = '\033[18~'
    KEY_F8 = '\033[19~'
    KEY_F9 = '\033[20~'
    KEY_F10 = '\033[21~'
    KEY_F11 = '\033[23~'
    KEY_F12 = '\033[24~'
    KEY_ESC = '\033'
    KEY_TAB = '\011'
    KEY_ENTER = '\n'


TerminalKeyDict = {y.value: y for x, y in TerminalKey.__members__.items()}


def characters_left_for_sequence(seq):
    if not seq:
        return True
    return seq[0] in ['\033', '\027']


def read_key():
    fd = sys.stdin.fileno()

    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    oldstdinfl = fcntl.fcntl(1, fcntl.F_GETFL)
    try:
        seq = ''
        while characters_left_for_sequence(seq):
            if len(seq) > 0:
                fcntl.fcntl(1, fcntl.F_SETFL, oldstdinfl | os.O_NONBLOCK)
            ch = sys.stdin.read(1)
            if not ch:
                break
            seq += ch
    except IOError:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(1, fcntl.F_SETFL, oldstdinfl)

    try:
        result = TerminalKeyDict[seq]
    except KeyError:
        result = seq

    return result


class Chooser:
    def __init__(self, options, msg='Choose one of:'):
        """Create a Chooser object."""
        self.selected = 0
        self.options = options
        self.msg = msg

    def choose(self):
        print(self.msg)
        self.print_options()
        key = None
        while key != TerminalKey.KEY_ENTER:
            key = read_key()
            if key == TerminalKey.KEY_UP:
                self.selected = max(0, self.selected - 1)
            elif key == TerminalKey.KEY_DOWN:
                self.selected = min(len(self.options) - 1, self.selected + 1)
            elif key == TerminalKey.KEY_ESC:
                return None
            self.go_back_to_beginning_of_list()
            self.print_options()
        return self.selected

    def go_back_to_beginning_of_list(self):
        # Go up
        sys.stdout.write('\033[1A' * len(self.options))
        # Go left to the beginning of the line
        sys.stdout.write('\033[1D' * (max([len(x) for x in self.options]) + 3))
        sys.stdout.flush()

    def print_options(self):
        for idx, item in enumerate(self.options):
            if idx == self.selected:
                print(TerminalColors.White + '->', item + TerminalColors.ENDC)
            else:
                print('  ', item)


def ask_user_to_choose_one_option(options, msg=''):
    c = Chooser(options, msg)
    return c.choose()
