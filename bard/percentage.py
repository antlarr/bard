# -*- coding: utf-8 -*-
import os
import sys
from bard.terminalcolors import TerminalColors
from bard.utils import printableLen


class Percentage:
    def __init__(self, precision=0, prefix=''):
        """Create a Percentage object."""
        self.max_value = 100
        self.min_value = 0
        self.value = 0
        self.last_text = ''
        self.printed = False
        self.isatty = sys.stdout.isatty()
        if not self.isatty:
            print(prefix, end='')
        self.prefix = prefix
        self.format = '%%.%df' % precision

    def set_value(self, value, print_=True):
        self.value = value
        if print_:
            self.print_percentage()

    def remove_print(self):
        if not self.printed or not self.isatty:
            return
        backspaces = '\b' * len(self.last_text)
        print(backspaces, end='', flush=True)
        self.printed = False

    def print_percentage(self):
        max_width = os.get_terminal_size().columns
        percent = ((self.value - self.min_value) * 100.0 /
                   (self.max_value - self.min_value))

        if not self.isatty:
            if percent == 100:
                print('100%')
            return

        tmp = (self.prefix + self.format % percent) + '%'
        if max_width > 30:
            max_width -= 10 + printableLen(tmp)
            bar_len = int(max_width * percent // 100)
            if percent < 100:
                tmp += (' ' + TerminalColors.Red + ('━' * bar_len) +
                        TerminalColors.ENDC + '━' * int(max_width - bar_len))
            else:
                tmp += ' ' * (max_width + 1)

        if tmp != self.last_text:
            self.remove_print()
            print(tmp, end='', flush=True)
            self.last_text = tmp
            self.printed = True
