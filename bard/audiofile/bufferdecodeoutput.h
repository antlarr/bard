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
#include "decodeoutput.h"

using std::string;

class BufferDecodeOutput : public DecodeOutput
{
public:
    BufferDecodeOutput();
    ~BufferDecodeOutput();

    virtual void init(int channels, enum AVSampleFormat sampleFmt, int64_t estimatedSamples, int sampleRate);
    virtual void prepare(int samples);
    virtual uint8_t **getBuffer(int samples);
    virtual void written(int samples);

    uint8_t *data(int channel=0) const
    {
        if (channel >= m_channelCount)
            return nullptr;
        if (!m_isPlanar)
            return m_buffer;

        return m_buffer + m_lineSize * channel;
    };

    uint64_t size() const { return m_bytesWritten; };
    int lineSize() const  { return m_lineSize; };

protected:
    uint8_t **m_data = nullptr;
    uint8_t *m_buffer = nullptr;
    uint64_t m_bytesWritten = 0;
    uint64_t m_samplesReserved = 0;
    int m_lineSize = 0;
};
