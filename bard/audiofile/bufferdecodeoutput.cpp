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

#include "bufferdecodeoutput.h"

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

#include "referencedata.h"

using std::string;

BufferDecodeOutput::BufferDecodeOutput()
{
}

BufferDecodeOutput::~BufferDecodeOutput()
{
    av_freep(&m_buffer);
    av_freep(&m_data);
}

void BufferDecodeOutput::init(int channels, enum AVSampleFormat sampleFmt, int64_t estimatedSamples, int sampleRate)
{
    m_samplesCount = 0;
    m_bytesWritten = 0;
    m_samplesReserved = estimatedSamples;
    DecodeOutput::init(channels, sampleFmt, estimatedSamples, sampleRate);

    int ret = av_samples_alloc_array_and_samples(&m_data, &m_lineSize, channels,
                                     m_samplesReserved, sampleFmt, 0);
    m_isValid = ret >= 0;
    if (!m_isValid) return;

    m_buffer = m_data[0];
}

void BufferDecodeOutput::prepare(int samples)
{
#ifdef DEBUG
//    std::cout << "samplesCount: " << m_samplesCount << " . prepare: " << samples << std::endl;
#endif

    if (m_samplesCount + samples > m_samplesReserved)
    {
#ifdef DEBUG
        std::cout << "increasing buffer decode output size" << std::endl;
#endif
        uint8_t **newData = nullptr;
        int newLineSize = 0;
        int64_t newSamplesReserved = m_samplesReserved + samples * 3;

        int ret = av_samples_alloc_array_and_samples(&newData, &newLineSize, m_channelCount,
                                                     newSamplesReserved, m_sampleFmt, 0);
        m_isValid = ret >= 0;

        m_data[0] = m_buffer;
        for (int ch = 1; m_isPlanar && ch < m_channelCount; ch++)
            m_data[ch] = m_data[ch-1] + m_lineSize;
        av_samples_copy(newData, m_data, 0, 0, m_samplesCount, m_channelCount, m_sampleFmt);

        av_freep(&m_buffer);
        av_freep(&m_data);

        m_data = newData;
        m_buffer = m_data[0];
        m_lineSize = newLineSize;
        m_samplesReserved = newSamplesReserved;

        m_data[0] = m_buffer + m_bytesWritten;
        for (int ch = 1; m_isPlanar && ch < m_channelCount; ch++)
            m_data[ch] = m_data[ch-1] + m_lineSize;
    }
}

uint8_t **BufferDecodeOutput::getBuffer(int samples)
{
    return m_data;
}

void BufferDecodeOutput::written(int samples)
{
    m_samplesCount += samples;
    long sizeWritten = samples * (m_isPlanar ? 1 : m_channelCount) * m_bytesPerSample;

    if (m_referenceData)
        m_referenceData->checkData(m_data[0], sizeWritten, m_lineSize);

    m_bytesWritten += sizeWritten;
//    printf("%ld\n", (long)m_bytesWritten);
    m_data[0] = m_buffer + m_bytesWritten;
    for (int ch = 1; m_isPlanar && ch < m_channelCount; ch++)
        m_data[ch] = m_data[ch-1] + m_lineSize;
}
/*
PyObject* BufferDecodeOutput::memoryview()
{
    PyObject* pymemview;
    unsigned char* export_data = (unsigned char *)malloc(10000);
    memset(export_data, 0, 10000);
    Py_ssize_t size;
    if (m_isPlanar)
        size = m_bytesWritten * m_channelCount;
    else
        size = m_bytesWritten;

    pymemview = PyMemoryView_FromMemory((char*) m_buffer, size, PyBUF_READ);
    return pymemview;
}
*/
