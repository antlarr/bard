# -*- coding: utf-8 -*-


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

    Worse = Red
    Better = Green
    Highlight = Yellow
    Header = White

    First = Red
    Second = Green

    DifferentLength = Magenta
    CantCompareSongs = Cyan

    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
