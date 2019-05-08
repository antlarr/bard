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

class ReferenceData
{
public:
    ReferenceData();
    virtual ~ReferenceData();

    void init(int channels, enum AVSampleFormat sampleFmt);

    void setReferenceFile(const string &filename);
    virtual void checkData(uint8_t *buffer, uint64_t size, int bufferLineSize);

protected:
    static char *readFromFile(const string& filename, uint64_t *size);

    uint8_t *m_reference = nullptr;
    uint64_t m_referenceSize = 0;
    uint64_t m_bytesWritten = 0;

    int m_channelCount = 0;
    enum AVSampleFormat m_sampleFmt = AV_SAMPLE_FMT_NONE;
    int m_bytesPerSample = 0;
    bool m_isPlanar = false;
    int m_lineSize = 0;
};
