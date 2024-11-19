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

#include <stdio.h>
#include <string>
#include <iostream>
#include <vector>
#include <tuple>
#include <algorithm>
#include "bufferaviocontext.h"
#include "decodeoutput.h"

#ifdef __cplusplus
extern "C" {
#endif

#include <libavutil/channel_layout.h>
#include <libavcodec/version.h>

#ifdef __cplusplus
}
#endif

using std::string;
struct AVPacket;
struct AVFrame;
struct SwrContext;
struct AVCodec;
struct AVCodecContext;
struct AVFormatContext;


class AudioFile
{
public:
    enum LogLevel {
        Critical = 0,
        Fatal = 1,
        Error = 2,
        Warning = 3,
        Info = 4,
        Verbose = 5,
        Debug = 6,
        Trace = 7
    };
    typedef std::tuple<double, AudioFile::LogLevel, std::string> LogRecord;

    AudioFile();
    ~AudioFile();
    int open(const string &path);
    int open(const char *data, long size, const std::string &filename=std::string());

    void printStreamInformation(int audioStreamIndex);
    int firstAudioStreamIndex() const;
    std::vector <int> audioStreamIndexes() const;
    int selectAudioStream(int audioStream);

    int channels() const;
    int sampleRate() const;
    void setRequestSampleFormat(const std::string &sampleFormat);
    std::string requestSampleFormat() const;

    void setOutChannels(int channels);
    void setOutChannelLayout(const std::string &channelLayout);
    int outChannels() const;
    void setOutSampleRate(int sampleRate);
    int outSampleRate() const;
    void setOutSampleFormat(const std::string &sampleFormat);
    std::string outSampleFormat() const;

    void setOutput(DecodeOutput *output);

    int decode();

    std::vector<std::string> errors() const;

    std::string codecName() const;
    std::string formatName() const;
    double containerDuration() const;
    int containerBitrate() const;
    int streamBitrate() const;
    int streamBytesPerSample() const;
    int streamBitsPerRawSample() const;
    std::string streamSampleFormatName() const;

    std::vector<LogRecord> loggedMessages() const;

    static LogLevel avlogToLog(int log);

protected:
    int readStreamsInfo();

    static void avlog_callback(void *avcl, int level, const char *fmt, va_list vl);

    int logError(const std::string &msg, int errorCode=1);
    void pushBackLogMessage(AudioFile::LogLevel level, const string &msg);
    double currentDecodingPosition() const;
//    double getSample(uint8_t* buffer, int sampleIndex) const;
    void handleFrame(const AVFrame* frame);
    int receiveFramesAndHandle();
    void drainDecoder();



    const AVCodec *m_codec = nullptr;
    AVCodecContext *m_codecCtx = nullptr;
    AVFormatContext *m_formatCtx = nullptr;
    int m_audioStreamIndex = -1;
    SwrContext *m_swrCtx = nullptr;
    AVFrame *m_frame = nullptr;

    string m_filename;
    string m_outFilename;

#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    uint64_t m_outChannelLayout = 0;
    int m_outChannelNumber = 0;
#else
    bool m_outChannelLayoutIsSet = false;
    AVChannelLayout m_outChannelLayout;
#endif
    int m_outSampleRate = 0;
    enum AVSampleFormat m_outSampleFmt = AV_SAMPLE_FMT_S16;

#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    uint64_t m_inChannelLayout = 0;
#else
    AVChannelLayout m_inChannelLayout;
#endif
    int m_inSampleRate = 0;
    enum AVSampleFormat m_inSampleFmt = AV_SAMPLE_FMT_S16;

    int64_t m_lastDecodedPTS = 0;

    BufferAVIOContext *m_avioContext = nullptr;
    DecodeOutput *m_output = nullptr;

    std::vector<LogRecord> m_loggedMessages;

#ifdef DEBUG
    int m_packets_sent_ok = 0;
    int m_packets_sent_total = 0;
    int m_frames_received_ok = 0;
    int m_frames_received_total = 0;
#endif

    static AudioFile *s_self;
};

