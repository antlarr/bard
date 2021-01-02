# -*- coding: utf-8 -*-
# See https://en.wikipedia.org/wiki/ANSI_escape_code for reference

from bard.terminalcolors import TerminalColors
import termios
import enum
import sys
import fcntl
import os
import readline


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
    KEY_SPACE = ' '


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
    def __init__(self, options, msg='Choose one of:', multiselection=False):
        """Create a Chooser object."""
        self.selected = 0
        self.options = options
        self.msg = msg
        self.multiselection = multiselection
        self.multiselected = []

    def choose(self, key_callbacks={}):
        print(self.msg)
        self.print_options()
        key = None
        self.multiselected = []
        while key != TerminalKey.KEY_ENTER:
            key = read_key()
            if key == TerminalKey.KEY_UP:
                self.selected = max(0, self.selected - 1)
            elif key == TerminalKey.KEY_DOWN:
                self.selected = min(len(self.options) - 1, self.selected + 1)
            elif key == TerminalKey.KEY_ESC:
                return None
            elif self.multiselection and key == TerminalKey.KEY_SPACE:
                if self.selected in self.multiselected:
                    self.multiselected.remove(self.selected)
                else:
                    self.multiselected.append(self.selected)
            elif key in key_callbacks:
                callback = key_callbacks[key]
                r = callback(self)
                if r is not None:
                    return r

            self.go_back_to_beginning_of_list()
            self.print_options()
        if self.multiselection:
            if self.multiselected:
                return self.multiselected
            return [self.selected]
        return self.selected

    def go_back_to_beginning_of_list(self):
        # Go up
        sys.stdout.write('\033[1A' * len(self.options))
        # Go left to the beginning of the line
        sys.stdout.write('\033[1D' * (max([len(x) for x in self.options]) + 3))
        sys.stdout.flush()

    def edit_option(self, idx):
        # Go up
        sys.stdout.write('\033[1A' * (len(self.options) - idx))
        # Go left to the beginning of the line
        sys.stdout.write('\033[1D' * (max([len(x) for x in self.options]) + 3))
        sys.stdout.flush()
        prev_value = self.options[idx]
        readline.set_startup_hook(lambda: readline.insert_text(prev_value))
        try:
            new_value = input('E: ')
        finally:
            readline.set_startup_hook()

        self.options[idx] = new_value
        sys.stdout.write('\033[1A' * (idx + 1))
        sys.stdout.write('\033[1D' * (max([len(x) for x in self.options]) + 3))
        sys.stdout.flush()
        self.print_options()
        return prev_value, new_value

    def print_options(self, highlight_selected=True):
        for idx, item in enumerate(self.options):
            if highlight_selected and idx == self.selected:
                print(TerminalColors.White + '->', item + TerminalColors.ENDC)
            elif (highlight_selected and self.multiselection and
                  idx in self.multiselected):
                print(TerminalColors.Yellow + '  ', item + TerminalColors.ENDC)
            else:
                print('  ', item)


def ask_user_to_choose_one_option(options, msg=''):
    c = Chooser(options, msg)
    return c.choose()
