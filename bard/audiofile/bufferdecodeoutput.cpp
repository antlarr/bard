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

//#undef DEBUG

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
#ifdef DEBUG
    std::cout << "BufferDecodeOutput::init. estimated samples: " << estimatedSamples << std::endl;
#endif
    // If we don't have an estimated number of samples, reserve space for 30 seconds
    if (estimatedSamples < 1)
        estimatedSamples = 30L * sampleRate * channels;

    m_samplesCount = 0;
    m_bytesWritten = 0;
    m_samplesReserved = estimatedSamples;

    DecodeOutput::init(channels, sampleFmt, estimatedSamples, sampleRate);

    int sample_size = av_get_bytes_per_sample(sampleFmt);
    int64_t seconds = 60;
    while (((int64_t)channels * m_samplesReserved > ((uint64_t)INT_MAX - channels) / sample_size) && seconds > 1)
    {
        // We won't have space for the whole audio, so let's reserve 60 seconds and it'll be dumped and adjusted as needed
        m_samplesReserved = seconds * m_channelCount * m_sampleRate;
        std::cout << "Info: samplesReserved adjusted to " << m_samplesReserved << "  sample rate: " << sampleRate <<  " (" << seconds << " seconds)" << std::endl;
        seconds /= 2;
    }

    int ret = av_samples_alloc_array_and_samples(&m_data, &m_lineSize, channels,
                                     m_samplesReserved, sampleFmt, 0);
    m_isValid = ret >= 0;
    if (!m_isValid)
    {
        char errbuf[1024];
        av_strerror(ret, errbuf, sizeof(errbuf));
        std::cout << "Error: BufferDecodeOutput::init returning not valid! " << errbuf << std::endl;
        return;
    }

    m_buffer = m_data[0];
}

void BufferDecodeOutput::prepare(int samples)
{
#ifdef DEBUG
    std::cout << "samplesCount: " << m_samplesCount << " . prepare: " << samples << " (" << m_samplesCount + samples << ") . samples reserved: " << m_samplesReserved << std::endl;
#endif

    if (m_samplesCount + samples > m_samplesReserved)
    {
#ifdef DEBUG
        std::cout << "increasing buffer decode output size, samples:" << samples << std::endl;
#endif
        uint8_t **newData = nullptr;
        int newLineSize = 0;
        // Always reserve space for at least 5 more seconds
        int64_t newSamplesReserved = m_samplesReserved + std::max(samples * 3, 5 * m_channelCount * m_sampleRate);

        int ret = av_samples_alloc_array_and_samples(&newData, &newLineSize, m_channelCount,
                                                     newSamplesReserved, m_sampleFmt, 0);
        if (ret == AVERROR(EINVAL))
        {
            dumpDataToBuffer(m_buffer, m_bytesWritten, m_isPlanar);


            newSamplesReserved = std::max(samples * 3, 30 * m_channelCount * m_sampleRate);
            ret = av_samples_alloc_array_and_samples(&newData, &newLineSize, m_channelCount,
                                                     newSamplesReserved, m_sampleFmt, 0);
        }
        m_isValid = ret >= 0;
        if (!m_isValid)
        {
            char errbuf[1024];
            av_strerror(ret, errbuf, sizeof(errbuf));
            std::cout << "Error: av_samples_alloc_array_and_samples returning not valid! " << errbuf << std::endl;
        }

        m_data[0] = m_buffer;
        for (int ch = 1; m_isPlanar && ch < m_channelCount; ch++)
            m_data[ch] = m_data[ch-1] + m_lineSize;
        if (m_samplesCount)
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


void BufferDecodeOutput::dumpDataToBuffer(uint8_t *data, uint64_t size, bool planar)
{
    if (!m_outputBuffer)
    {
        uint64_t bufferSize = size * (planar ? m_channelCount : 1);
        m_outputBuffer = new uint8_t[bufferSize];
        m_outputBufferSize = size;
        m_outputBufferIsPlanar = planar;
        if (!m_outputBuffer)
            std::cout << "ERROR: can't reserve " << bufferSize << " bytes ####" << std::endl;

        if (planar)
        {
            uint8_t *src = data;
            uint8_t *tgt = m_outputBuffer;
            for (int ch=0; ch < m_channelCount ; ch++)
            {
                memcpy(tgt, src, size);
                src += m_lineSize;
                tgt += size;
            }
        }
        else
            memcpy(m_outputBuffer, data, size);

        m_samplesCount = 0;
        m_bytesWritten = 0;
        return;
    }

    uint64_t bufferSize = (m_outputBufferSize + size) * (planar ? m_channelCount : 1);
    uint8_t *newBuffer = new uint8_t[bufferSize];
    if (!m_outputBuffer)
        std::cout << "ERROR: can't reserve " << bufferSize << " bytes ####" << std::endl;

    uint64_t newBufferSize = m_outputBufferSize + size;

    if (m_outputBufferIsPlanar)
    {
        uint8_t *src1 = m_outputBuffer;
        uint8_t *src2 = data;
        uint8_t *tgt = newBuffer;
        for (int ch=0; ch < m_channelCount ; ch++)
        {
            memcpy(tgt, src1, m_outputBufferSize);
            tgt += m_outputBufferSize;
            src1 += m_outputBufferSize;
            memcpy(tgt, src2, size);
            src2 += m_lineSize;
            tgt += size;
        }
    }
    else
    {
        memcpy(newBuffer, m_outputBuffer, m_outputBufferSize);
        memcpy(newBuffer + m_outputBufferSize, data, size);
    }

    delete[] m_outputBuffer;
    m_outputBuffer = newBuffer;
    m_outputBufferSize = newBufferSize;
    m_samplesCount = 0;
    m_bytesWritten = 0;
}

void BufferDecodeOutput::terminate()
{
    if (m_outputBuffer)
        dumpDataToBuffer(m_buffer, m_bytesWritten, m_isPlanar);
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
