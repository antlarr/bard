# -*- coding: utf-8 -*-
# See https://en.wikipedia.org/wiki/ANSI_escape_code for reference


class TerminalColors:
    Red = '\033[91m'
    Green = '\033[92m'
    Yellow = '\033[93m'
    Blue = '\033[94m'
    Cyan = '\033[96m'
    White = '\033[97m'
    Magenta = '\033[95m'
    Grey = '\033[90m'
    Black = '\033[90m'

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
