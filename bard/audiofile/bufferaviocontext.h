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

#include <stdint.h>

struct AVIOContext;

class BufferAVIOContext
{
private:
    BufferAVIOContext(BufferAVIOContext const &);
    BufferAVIOContext& operator = (BufferAVIOContext const &);

public:
    BufferAVIOContext(const char *data, int64_t size, long buffer_size = 4096);
    ~BufferAVIOContext();

    AVIOContext *avioContext() const { return m_ctx; }

    int read(unsigned char *buf, int buf_size);
    int64_t seek(int64_t offset, int whence);

    static int read(void *opaque, unsigned char *buf, int buf_size);
    static int64_t seek(void *opaque, int64_t offset, int whence);

protected:
    const unsigned char *m_data;
    int64_t m_size = 0;
    const unsigned char *m_currentPtr;
    int64_t m_currentPos = 0;
    AVIOContext *m_ctx = nullptr;
};

