# -*- coding: utf-8 -*-
# See https://en.wikipedia.org/wiki/ANSI_escape_code for reference


class TerminalColors:
    Red = '\033[91m'
    DarkRed = '\033[31m'
    Red1 = '\033[38;5;52m'
    Red2 = '\033[38;5;88m'
    Red3 = '\033[38;5;124m'
    Red4 = '\033[38;5;160m'
    Red5 = '\033[38;5;196m'
    Green = '\033[92m'
    Yellow = '\033[93m'
    Blue = '\033[94m'
    Cyan = '\033[96m'
    White = '\033[97m'
    Magenta = '\033[95m'
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
    BOLD = '\033[1m'
    ITALIC = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def rgb(r, g, b):
        return '\033[38;2;{r};{g};{b}m'
