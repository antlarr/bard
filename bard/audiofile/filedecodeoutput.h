/*
    This file is part of Bard (https://github.com/antlarr/bard)
    Copyright (C) 2017-2019 Antonio Larrosa <antonio.larrosa@gmail.com>

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

#include <stdio.h>
#include <string>
#include <iostream>
#include <vector>
#include <algorithm>
#include "decodeoutput.h"

using std::string;

class FileDecodeOutput : public DecodeOutput
{
public:
    FileDecodeOutput(const std::string &filename);
    ~FileDecodeOutput();

    virtual void prepare(int samples);
    virtual uint8_t **getBuffer(int samples);
    virtual void written(int samples);

protected:
    std::string m_filename;

    uint8_t **m_data = nullptr;
    int m_maxSamples = -1;
    FILE* m_outFile = nullptr;
};

