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

#include "filedecodeoutput.h"

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

FileDecodeOutput::FileDecodeOutput(const std::string &filename) : m_filename(filename)
{
    m_outFile = fopen(filename.c_str(), "w+");
    if(m_outFile == NULL) {
        fprintf(stderr, "Unable to open output file \"%s\".\n", filename.c_str());
    }
}

FileDecodeOutput::~FileDecodeOutput()
{
    if (m_data)
        av_freep(&m_data[0]);
    av_freep(&m_data);

    fclose(m_outFile);
}

void FileDecodeOutput::prepare(int samples)
{
    if (samples <= m_maxSamples)
        return;
    if (m_data)
        av_freep(&m_data[0]);
    av_freep(&m_data);

    int dst_linesize;
    int ret = av_samples_alloc_array_and_samples(&m_data, &dst_linesize, m_channelCount,
                                     samples, m_sampleFmt, 0);

    if (ret<0)
        printf("Error1\n");
    m_maxSamples = samples;
}
uint8_t **FileDecodeOutput::getBuffer(int samples)
{
    return m_data;
}
void FileDecodeOutput::written(int samples)
{
    m_samplesCount += samples;
    int size = samples * m_channelCount * m_bytesPerSample;
    std::cout << "written " << size << " bytes" << std::endl;

    if (m_referenceData)
        m_referenceData->checkData(m_data[0], size, 0);

    fwrite(m_data[0], 1, size, m_outFile);
}
