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

#include "decodeoutput.h"
#include <iostream>
#include <string>
#include "referencedata.h"

DecodeOutput::~DecodeOutput()
{
    delete m_referenceData;
}

void DecodeOutput::init(int channels, enum AVSampleFormat sampleFmt, int64_t estimatedSamples, int sampleRate)
{
    m_channelCount = channels;
    m_sampleFmt = sampleFmt;
    m_isPlanar  = av_sample_fmt_is_planar(sampleFmt);
    m_bytesPerSample = av_get_bytes_per_sample(sampleFmt);
    m_estimatedSamples = estimatedSamples;
    m_sampleRate = sampleRate;
    m_isValid = true;
    if (m_referenceData)
        m_referenceData->init(channels, sampleFmt);
}

std::string DecodeOutput::sampleFormatName() const
{
    const char *name = av_get_sample_fmt_name(m_sampleFmt);
    if (!name)
        return std::string();

    return name;
}

void DecodeOutput::setReferenceFile(const std::string &referenceFile)
{
    delete m_referenceData;
    m_referenceData = new ReferenceData;
    m_referenceData->setReferenceFile(referenceFile);
}
