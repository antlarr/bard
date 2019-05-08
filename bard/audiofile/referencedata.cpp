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

#include "referencedata.h"

#ifdef __cplusplus
extern "C" {
#endif

#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswresample/swresample.h>
#include <libavutil/opt.h>

#ifdef __cplusplus
}
#endif

#include <stdio.h>
#include <string>
#include <iostream>
#include <vector>
#include <algorithm>

using std::string;

ReferenceData::ReferenceData()
{
}

ReferenceData::~ReferenceData()
{
    delete[] m_reference;
}

void ReferenceData::init(int channels, enum AVSampleFormat sampleFmt)
{
    m_channelCount = channels;
    m_sampleFmt = sampleFmt;
    m_isPlanar  = av_sample_fmt_is_planar(sampleFmt);
    m_bytesPerSample = av_get_bytes_per_sample(sampleFmt);
    m_lineSize = m_referenceSize / (m_isPlanar ? m_channelCount : 1);
    m_bytesWritten = 0;
}

char *ReferenceData::readFromFile(const string& filename, uint64_t *size)
{
    uint64_t fileSize;
    FILE *f = fopen(filename.c_str(), "r");
    fseek(f, 0, SEEK_END); // seek to end of file
    fileSize = ftell(f); // get current file pointer
    fseek(f, 0, SEEK_SET);

    char *data = new char[fileSize];

    fileSize = fread(data, 1, fileSize, f);

    if (size)
        *size = fileSize;

    return data;
}

void ReferenceData::setReferenceFile(const string &filename)
{
    m_reference = reinterpret_cast<uint8_t *>(readFromFile(filename, &m_referenceSize));
}

void ReferenceData::checkData(uint8_t *buffer, uint64_t size, int bufferLineSize)
{
    uint64_t preBytesWritten = m_bytesWritten;
    uint64_t postBytesWritten = m_bytesWritten + size;
    if (postBytesWritten > m_referenceSize)
    {
        std::cerr << "Wrote more (" << postBytesWritten << ") than reference size (" << m_referenceSize << ")" << std::endl;
        return;
    }

    int r;
    uint8_t * tmp_ref = m_reference + m_bytesWritten;
    uint8_t * tmp_buf = buffer;
#ifdef DEBUG
    std::cerr << "Wrote " << size << " bytes at " << preBytesWritten << std::endl;
#endif
    r = memcmp(tmp_ref, tmp_buf, size);
    if (r != 0)
        std::cerr << "Changes with reference at " << preBytesWritten << " bytes (size: " << size << ") !" << std::endl;
    for (int ch = 1; m_isPlanar && ch < m_channelCount; ch++)
    {
        tmp_ref += m_lineSize;
        tmp_buf += bufferLineSize;
        r = memcmp(tmp_ref, tmp_buf, size);
        if (r != 0)
            std::cerr << "Changes with reference at " << preBytesWritten << " bytes (size: " << size << ", ch: " << ch << ") !" << std::endl;
    }

    m_bytesWritten += size;
}
