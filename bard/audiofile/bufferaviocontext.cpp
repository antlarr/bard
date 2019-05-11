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

#include "bufferaviocontext.h"

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

#if (__GNUC__ && __GNUC__ < 7) || (__clang_major &&  __clang_major__ < 5)
namespace std
{
    template<class T1, class T2, class T3>
    constexpr const T1 clamp( const T1& v, const T2& lo, const T3& hi )
    {
        if (v < lo) return lo;
        else if (v > hi) return hi;
        return v;
    }

};
#endif

BufferAVIOContext::BufferAVIOContext(const char *data, long size, long buffer_size)
       : m_data(reinterpret_cast<const unsigned char *>(data)), m_size(size), m_currentPtr(m_data)
{
    unsigned char *buffer = reinterpret_cast<unsigned char *>(av_malloc(buffer_size));
    if (buffer)
        m_ctx = ::avio_alloc_context(buffer, buffer_size, 0, this, &BufferAVIOContext::read, NULL, &BufferAVIOContext::seek);
}

BufferAVIOContext::~BufferAVIOContext()
{
    ::av_free(m_ctx->buffer);
    ::av_free(m_ctx);
}

int BufferAVIOContext::read(void *opaque, unsigned char *buf, int buf_size)
{
    BufferAVIOContext *b = static_cast<BufferAVIOContext*>(opaque);
    return b->read(buf, buf_size);
}

int64_t BufferAVIOContext::seek(void *opaque, int64_t offset, int whence)
{
    BufferAVIOContext *b = static_cast<BufferAVIOContext*>(opaque);
    return b->seek(offset, whence);
}

int BufferAVIOContext::read(unsigned char *buf, int buf_size)
{
    int size = std::clamp(buf_size, 0, (int)(m_size - m_currentPos));
    if (!size)
        return AVERROR_EOF;
    memcpy(buf, m_currentPtr, size);
    m_currentPtr += size;
    m_currentPos += size;
    return size;
}

int64_t BufferAVIOContext::seek(int64_t offset, int whence)
{
    if (whence == SEEK_SET)
    {
        offset = std::clamp(offset, 0L, m_size);
        m_currentPtr = m_data + offset;
        m_currentPos = offset;
    }
    else if (whence == SEEK_CUR)
    {
        offset = std::clamp(offset, (int64_t)-m_currentPos, m_size - m_currentPos);
        m_currentPtr += offset;
        m_currentPos += offset;
    }
    else if (whence == SEEK_END)
    {
        offset = std::clamp(offset, -m_size, 0L);
        m_currentPtr = m_data + m_size + offset;
        m_currentPos = m_size + offset;
    }
    else if (whence == 65536)
        return m_size;
    else
        return -1;

    return 0;
}
