/*
    This file is part of Bard (https://github.com/antlarr/bard)
    Copyright (C) 2024 Antonio Larrosa <antonio.larrosa@gmail.com>

    Bard is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, version 3.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

#include <iostream>

enum LogLevel {
    Critical = 0,
    Fatal = 1,
    Error = 2,
    Warning = 3,
    Info = 4,
    Verbose = 5,
    Debug = 6,
    Trace = 7
};

enum LogArea {
    Default = 0,
    DecodeParameters,
    DecodeBrokenFrame,
    TraceDecode,
    TraceSamples,
    BufferDecodeOutputArea,
    LastArea
};

void initLog();

std::ostream &logDebug(LogArea area=Default);

void setLogLevel(LogLevel level);
void setLogAreaState(LogArea area, bool enable);
