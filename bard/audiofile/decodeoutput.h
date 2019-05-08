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

#ifndef __DECODEOUTPUT_H
#define __DECODEOUTPUT_H

#include <stdio.h>
#include <string>
#include "common.h"

class DecodeOutput
{
public:
    virtual ~DecodeOutput();

    virtual void init(int channels, enum AVSampleFormat sampleFmt, int64_t estimatedSamples, int sampleRate);
    virtual void prepare(int samples) = 0;
    virtual uint8_t **getBuffer(int samples) = 0;
    virtual void written(int samples) = 0;

    std::string sampleFormatName() const;
    int channelCount() const { return m_channelCount; };
    int bytesPerSample() const { return m_bytesPerSample; };
    bool isPlanar() const { return m_isPlanar; };
    bool isValid() const { return m_isValid; };
    uint64_t samplesCount() const { return m_samplesCount; };

    double duration() const { return m_samplesCount / (double)m_sampleRate; };

    void setReferenceFile(const std::string &referenceFile);

protected:
    int m_channelCount = 0;
    enum AVSampleFormat m_sampleFmt = AV_SAMPLE_FMT_NONE;
    int m_bytesPerSample = 0;
    int64_t m_estimatedSamples = 0;
    bool m_isPlanar = false;
    bool m_isValid = false;
    uint64_t m_samplesCount = 0;
    int m_sampleRate = 1;

    class ReferenceData *m_referenceData = nullptr;
};

#endif
