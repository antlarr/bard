# -*- coding: utf-8 -*-
# See https://en.wikipedia.org/wiki/ANSI_escape_code for reference


class TerminalColors:
    Red = '\033[91m'
    DarkRed = '\033[31m'
    DarkGreen = '\033[32m'
    DarkYellow = '\033[33m'
    DarkBlue = '\033[34m'
    DarkMagenta = '\033[35m'
    DarkCyan = '\033[36m'
    Red1 = '\033[38;5;52m'
    Red2 = '\033[38;5;88m'
    Red3 = '\033[38;5;124m'
    Red4 = '\033[38;5;160m'
    Red5 = '\033[38;5;196m'
    Green = '\033[92m'
    Yellow = '\033[93m'
    Blue = '\033[94m'
    Magenta = '\033[95m'
    Cyan = '\033[96m'
    White = '\033[97m'
    Grey = '\033[90m'
    Black = '\033[90m'
    Gradient = ['\033[38;5;52m',
                '\033[38;5;88m',
                '\033[38;5;124m',
                '\033[38;5;160m',
                '\033[38;5;196m',
                '\033[38;5;166m',
                '\033[38;5;136m',
                '\033[38;5;106m',
                '\033[38;5;76m',
                '\033[38;5;46m']

    Ok = Green
    Warning = Yellow
    Fail = Red
    Error = Red

    Filename = White
    Host = Cyan
    Size = Yellow
    DateTime = Blue

    New = Green
    Modified = Yellow
    Removed = Red

    Worse = Red
    Better = Green
    Highlight = Yellow
    Header = White

    First = Red
    Second = Green

    DifferentLength = Magenta
    CantCompareSongs = Cyan

    BackgroundRed = '\033[48;5;52m'
    BackgroundGreen = '\033[48;5;22m'
    BackgroundBlue = '\033[48;5;4'

    ENDC = '\033[0m'
    ENDFG = '\033[39m'
    BOLD = '\033[1m'
    ITALIC = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def rgb(r, g, b):
        return f'\033[38;2;{r};{g};{b}m'
