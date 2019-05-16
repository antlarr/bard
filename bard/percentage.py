# -*- coding: utf-8 -*-


class Percentage:
    def __init__(self):
        """Create a Percentage object."""
        self.max_value = 100
        self.min_value = 0
        self.value = 0
        self.last_text = ''
        self.printed = False

    def set_value(self, value, print_=True):
        self.value = value
        if print_:
            self.print_percentage()

    def remove_print(self):
        if not self.printed:
            return
        backspaces = '\b' * len(self.last_text)
        print(backspaces, end='', flush=True)
        self.printed = False

    def print_percentage(self):
        tmp = '%d%%' % ((self.value - self.min_value) * 100.0 /
                        (self.max_value - self.min_value))
        if tmp != self.last_text:
            self.remove_print()
            print(tmp, end='', flush=True)
            self.last_text = tmp
            self.printed = True
