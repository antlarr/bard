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

#include "audiofile.h"
#include "log.h"
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

//#define TRACE 1
//#undef DEBUG
//

AudioFile::AudioFile()
{
    s_self = this;
    av_log_set_callback(avlog_callback);

#if LIBAVFORMAT_VERSION_INT < AV_VERSION_INT(58,9,100)
    av_register_all();
#endif
}

AudioFile::~AudioFile()
{
    av_frame_free(&m_frame);
    av_frame_free(&m_outFrame);

    swr_free(&m_swrCtx);

    avcodec_free_context(&m_codecCtx);

    avformat_close_input(&m_formatCtx);

    delete m_avioContext;

    av_log_set_callback(av_log_default_callback);

    s_self = nullptr;
}

int AudioFile::open(const string &path)
{
    m_filename = path;

    m_formatCtx = avformat_alloc_context();
    if (!m_formatCtx)
        return logError("Error allocating avformat context");

    m_formatCtx->flags = 0;

    int err;
    if ((err = avformat_open_input(&m_formatCtx, path.c_str(), NULL, 0)) != 0) {
        return logError("Error opening file", err);
    }

    return readStreamsInfo();
}

int AudioFile::open(const char *data, long size, const std::string &filename)
{
    m_filename = filename;
    m_avioContext = new BufferAVIOContext(data, size);
    m_formatCtx = avformat_alloc_context();
    if (!m_formatCtx)
        return logError("Error allocating avformat context");

    m_formatCtx->flags = 0;

    m_formatCtx->pb = m_avioContext->avioContext();

    AVProbeData probeData;
    probeData.buf = const_cast<unsigned char *>(reinterpret_cast<const unsigned char *>(data));
    probeData.buf_size = std::min(size, 512*1024L);
    probeData.filename = filename.c_str();
    probeData.mime_type = filename.c_str();

    m_formatCtx->iformat = av_probe_input_format(&probeData, 1);
    m_formatCtx->flags |= AVFMT_FLAG_CUSTOM_IO;

    int err;
    if ((err = avformat_open_input(&m_formatCtx, "", NULL, 0)) != 0) {
        return logError("Error opening file.", err);
    }

    return readStreamsInfo();
}

int AudioFile::readStreamsInfo()
{
    avformat_find_stream_info(m_formatCtx, NULL);

    int audioStreamIndex = firstAudioStreamIndex();
    if(audioStreamIndex == -1) {
        logError("No audio streams found");
        avformat_close_input(&m_formatCtx);
        return -1;
    }

    return selectAudioStream(audioStreamIndex);
}

int AudioFile::selectAudioStream(int audioStream)
{
    avcodec_free_context(&m_codecCtx);
    m_codecCtx = nullptr;

    m_audioStreamIndex = audioStream;
    m_codec = avcodec_find_decoder(m_formatCtx->streams[m_audioStreamIndex]->codecpar->codec_id);
    if (m_codec == NULL) {
        return logError(std::string("Decoder not found. The codec '") + std::to_string(m_formatCtx->streams[m_audioStreamIndex]->codecpar->codec_id) + "' is not supported");
    }

    m_codecCtx = avcodec_alloc_context3(m_codec);
    if (m_codecCtx == NULL) {
        return logError("Could not allocate a decoding context");
    }

    int err;
    if ((err = avcodec_parameters_to_context(m_codecCtx, m_formatCtx->streams[m_audioStreamIndex]->codecpar)) != 0)
    {
        return logError("Error setting codec context parameters.", err);
    }

    m_codecCtx->request_sample_fmt = m_codecCtx->sample_fmt;
    m_codecCtx->skip_frame = AVDISCARD_NONE;
    m_codecCtx->skip_loop_filter = AVDISCARD_NONE;
    m_codecCtx->skip_idct = AVDISCARD_NONE;

    m_outSampleFmt = av_get_alt_sample_fmt(m_codecCtx->sample_fmt, 0);

    if ((m_outSampleFmt == AV_SAMPLE_FMT_FLT || m_outSampleFmt == AV_SAMPLE_FMT_FLTP)
        && (m_codecCtx->codec_id == AV_CODEC_ID_MP2
         || m_codecCtx->codec_id == AV_CODEC_ID_MP3
         || m_codecCtx->codec_id == AV_CODEC_ID_AAC
         || m_codecCtx->codec_id == AV_CODEC_ID_OPUS
         || m_codecCtx->codec_id == AV_CODEC_ID_VORBIS
         || m_codecCtx->codec_id == AV_CODEC_ID_WMAV1
         || m_codecCtx->codec_id == AV_CODEC_ID_WMAV2 ))
        m_outSampleFmt = AV_SAMPLE_FMT_S16;

// ffmpeg 5.1.4 59.37.100
// ffmpeg 6.1.1 60.31.102
// ffmpeg 7.1   61.19.100
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    if (m_codecCtx->channel_layout == 0)
    {
        pushBackLogMessage(Error, "Input channel count and layout are unset. Assuming stereo audio");
        m_codecCtx->channel_layout = av_get_default_channel_layout(2);
    }
    m_outChannelLayout = m_codecCtx->channel_layout;
    m_outChannelNumber = av_get_channel_layout_nb_channels(m_outChannelLayout);
#else
    if (m_codecCtx->ch_layout.nb_channels == 0)
    {
        pushBackLogMessage(Error, "Input channel count and layout are unset. Assuming stereo audio");
        av_channel_layout_default(&m_codecCtx->ch_layout, 2);
    }
    av_channel_layout_copy(&m_outChannelLayout, &(m_codecCtx->ch_layout));
    m_outChannelLayoutIsSet = true;
#endif
    m_outSampleRate = m_codecCtx->sample_rate;

    return 0;
}

void AudioFile::setRequestSampleFormat(const std::string &sampleFormat)
{
    m_codecCtx->request_sample_fmt = av_get_sample_fmt(sampleFormat.c_str());
}

std::string AudioFile::requestSampleFormat() const
{
    if (!m_codecCtx)
        return std::string();
    return std::string(av_get_sample_fmt_name(m_codecCtx->request_sample_fmt));
}

int AudioFile::channels() const
{
    if (!m_codecCtx)
        return 0;
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    return av_get_channel_layout_nb_channels(m_codecCtx->channel_layout);
#else
    return m_codecCtx->ch_layout.nb_channels;
#endif
}

int AudioFile::sampleRate() const
{
    if (!m_codecCtx)
        return 0;
    return m_codecCtx->sample_rate;
}

void AudioFile::setOutChannels(int channels)
{
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    m_outChannelNumber = channels;
    m_outChannelLayout = av_get_default_channel_layout(channels);
#else
    av_channel_layout_default(&m_outChannelLayout, channels);
    m_outChannelLayoutIsSet = true;
#endif
}

void AudioFile::setOutChannelLayout(const std::string &channelLayout)
{
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    m_outChannelLayout = av_get_channel_layout(channelLayout.c_str());
    m_outChannelNumber = av_get_channel_layout_nb_channels(m_outChannelLayout);
#else
    av_channel_layout_from_string(&m_outChannelLayout, channelLayout.c_str());
    m_outChannelLayoutIsSet = true;
#endif
}

int AudioFile::outChannels() const
{
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    return m_outChannelNumber;
#else
    return m_outChannelLayout.nb_channels;
#endif
}

void AudioFile::setOutSampleRate(int sampleRate)
{
    m_outSampleRate = sampleRate;
}

int AudioFile::outSampleRate() const
{
    return m_outSampleRate;
}

void AudioFile::setOutSampleFormat(const std::string &sampleFormat)
{
    m_outSampleFmt = av_get_sample_fmt(sampleFormat.c_str());
}

std::string AudioFile::outSampleFormat() const
{
    return std::string(av_get_sample_fmt_name(m_outSampleFmt));
}

void AudioFile::avlog_callback(void *avcl, int level, const char *fmt, va_list vl)
{
    if (level > av_log_get_level())
         return;
    int buffer_size = 128;
    char buffer[buffer_size];
    vsnprintf(buffer, buffer_size, fmt, vl);
    if (buffer[std::max((size_t)0, strlen(buffer)-1)] == '\n')
        buffer[std::max((size_t)0, strlen(buffer)-1)] = 0;
    if (buffer[std::max((size_t)0, strlen(buffer)-1)] == '.')
        buffer[std::max((size_t)0, strlen(buffer)-1)] = 0;
    if (s_self)
    {
        s_self->pushBackLogMessage(avlogToLog(level), buffer);
    }
    else
    {
        printf("bard: (%d) %s\n", level, buffer);
    }
}

AudioFile *AudioFile::s_self = nullptr;

double AudioFile::currentDecodingPosition() const
{
    if (m_codecCtx && m_formatCtx)
    {
        AVStream *stream = m_formatCtx->streams[m_audioStreamIndex];

#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
        return m_codecCtx->pts_correction_last_pts * (double)stream->time_base.num / (double)stream->time_base.den;
#else
        return m_lastDecodedPTS * (double)stream->time_base.num / (double)stream->time_base.den;
#endif
    }
    return 0;
}

void AudioFile::pushBackLogMessage(AudioFile::LogLevel level, const string &msg)
{
    double pos = currentDecodingPosition();
    m_loggedMessages.push_back(std::make_tuple(pos, level, msg));
}

AudioFile::LogLevel AudioFile::avlogToLog(int log)
{
    switch (log)
    {
        case (AV_LOG_PANIC):  return Critical;
        case (AV_LOG_FATAL):  return Fatal;
        case (AV_LOG_ERROR):  return Error;
        case (AV_LOG_WARNING):return Warning;
        case (AV_LOG_INFO):   return Info;
        case (AV_LOG_VERBOSE):return Verbose;
        case (AV_LOG_DEBUG):  return Debug;
        case (AV_LOG_TRACE):  return Trace;
        default:
            std::cerr << "Unknown avlog: " << log << std::endl;
            return Error;
    };
}

std::vector<AudioFile::LogRecord> AudioFile::loggedMessages() const
{
    return m_loggedMessages;
}

int AudioFile::logError(const std::string &msg, int errorCode)
{
    if (errorCode >= 0)
        return 0;

    const size_t bufsize = 64;
    char buf[bufsize];
    std::string error;

    if(av_strerror(errorCode, buf, bufsize) == 0)
    {
        error = buf;
    }
    else
    {
        error = std::string("UNKNOWN_ERROR: ") + std::to_string(errorCode);
    }
#ifdef DEBUG
    std::cerr << msg << ": " << error << std::endl;
#endif

    pushBackLogMessage((errorCode<0)? AudioFile::Error : AudioFile::Info, error);

    return errorCode;
}

void AudioFile::resampleFrame(AVFrame *outFrame, const AVFrame *inFrame)
{
    int dst_nb_samples = inFrame->nb_samples;
    int out_samples = swr_get_out_samples(m_swrCtx, inFrame->nb_samples);
    dst_nb_samples = out_samples;

    outFrame->format = m_outSampleFmt;
    outFrame->sample_rate = m_outSampleRate;
    av_channel_layout_copy(&(outFrame->ch_layout), &m_outChannelLayout);

#ifdef DEBUG
    logDebug(TraceDecode) << "handling frame at " << currentDecodingPosition() << std::endl;
    logDebug(TraceDecode) << "preparing " << dst_nb_samples << " samples" << std::endl;
#endif


    if (inFrame->sample_rate != m_inSampleRate
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
        || inFrame->channel_layout != m_inChannelLayout
#else
        || av_channel_layout_compare(&(inFrame->ch_layout), &m_inChannelLayout) != 0
#endif
        || inFrame->format != m_inSampleFmt)
    {
        logDebug(DecodeBrokenFrame) << "broken frame with " << inFrame->nb_samples << " samples and invalid params at " << currentDecodingPosition() << std::endl;
        if (inFrame->sample_rate != m_inSampleRate)
        {
            logDebug(DecodeBrokenFrame) << "  sample_rate:" << inFrame->sample_rate << " (m_inSampleRate: " << m_inSampleRate << ")" << std::endl;
        }
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
        if (inFrame->channel_layout != m_inChannelLayout)
        {
            logDebug(DecodeBrokenFrame) << "  channel_layout:" << inFrame->channel_layout << " (m_inChannelLayout: " << m_inChannelLayout << ")" << std::endl;
        }
#else
        if (av_channel_layout_compare(&(inFrame->ch_layout), &m_inChannelLayout) != 0)
        {
            char buf_frame[128];
            char buf_in[128];
            av_channel_layout_describe(&(inFrame->ch_layout), buf_frame, 128);
            av_channel_layout_describe(&m_inChannelLayout, buf_in, 128);
            logDebug(DecodeBrokenFrame) << "  channel_layout:" << buf_frame << " (m_inChannelLayout: " << buf_in << ")" << std::endl;
        }
#endif
        if (inFrame->format != m_inSampleFmt)
        {
            logDebug(DecodeBrokenFrame) << "  sample_fmt:" << inFrame->format << " (m_inSampleFmt: " << m_inSampleFmt << ")" << std::endl;
        }

        SwrContext *tmpSwrCtx = swr_alloc();
        if (!tmpSwrCtx)
        {
            logError("Could not allocate resampler context");
            return;
        }

#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
        av_opt_set_int(tmpSwrCtx, "in_channel_layout", inFrame->channel_layout, 0);
        av_opt_set_int(tmpSwrCtx, "out_channel_layout", m_outChannelLayout, 0);
#else
        av_opt_set_chlayout(tmpSwrCtx, "in_chlayout", &(inFrame->ch_layout), 0);
        av_opt_set_chlayout(tmpSwrCtx, "out_chlayout", &(m_outChannelLayout), 0);
#endif

        av_opt_set_int(tmpSwrCtx, "in_sample_rate", inFrame->sample_rate, 0);
        av_opt_set_sample_fmt(tmpSwrCtx, "in_sample_fmt", static_cast<AVSampleFormat>(inFrame->format), 0);

        av_opt_set_int(tmpSwrCtx, "out_sample_rate", m_outSampleRate, 0);
        av_opt_set_sample_fmt(tmpSwrCtx, "out_sample_fmt", m_outSampleFmt, 0);

#ifdef DEBUG
 #if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
        logDebug(DecodeBrokenFrame) << "Temporarily resampling frame from "
                  << inFrame->channel_layout << "/" << inFrame->sample_rate << "/" << av_get_sample_fmt_name(static_cast<AVSampleFormat>(inFrame->format))
                  << " to "
                  << m_outChannelLayout << "/" << m_outSampleRate << "/" << av_get_sample_fmt_name(m_outSampleFmt) << std::endl;
 #else
        char buf_in[128];
        char buf_out[128];
        av_channel_layout_describe(&inFrame->ch_layout, buf_in, 128);
        av_channel_layout_describe(&m_outChannelLayout, buf_out, 128);
        logDebug(DecodeBrokenFrame) << "Temporarily resampling frame from "
                  << buf_in << "/" << inFrame->sample_rate << "/" << av_get_sample_fmt_name(static_cast<AVSampleFormat>(inFrame->format))
                  << " to "
                  << buf_out << "/" << m_outSampleRate << "/" << av_get_sample_fmt_name(m_outSampleFmt) << std::endl;
 #endif
#endif

        if ((swr_init(tmpSwrCtx)) < 0)
        {
            logError("Failed to initialize the resampling context for broken frame");
            return;
        }

        //int r = swr_convert_frame(tmpSwrCtx, outFrame, inFrame);
        outFrame->nb_samples = swr_get_out_samples(tmpSwrCtx, inFrame->nb_samples);

        int ret;
        if ((ret = av_frame_get_buffer(outFrame, 0)) < 0) {
            logError("Error obtaining buffer for output frame", ret);
            return;
        }

        ret = swr_convert(tmpSwrCtx, (uint8_t **)outFrame->extended_data, outFrame->nb_samples,
                                     (const uint8_t **)inFrame->extended_data, inFrame->nb_samples);
        if (ret < 0)
        {
            outFrame->nb_samples = 0;
            logError("Error resampling", ret);
            return;
        }

        outFrame->nb_samples = ret;

        logDebug(DecodeBrokenFrame) << "input  Frame samples: " << inFrame->nb_samples << std::endl;
        logDebug(DecodeBrokenFrame) << "output Frame samples: " << outFrame->nb_samples << std::endl;

        int remaining_samples = swr_get_out_samples(tmpSwrCtx, 0);
        if (ret > 0 && remaining_samples > 0)
        {
            logDebug(DecodeBrokenFrame) << "Remaining samples: " << remaining_samples << std::endl;
            handleOutFrame(outFrame);
            //AVFrame *tmp1 = av_frame_clone(outFrame);
            av_frame_unref(outFrame);

            //AVFrame *tmp2 = av_frame_alloc();

            outFrame->format = m_outSampleFmt;
            outFrame->sample_rate = m_outSampleRate;
            av_channel_layout_copy(&(outFrame->ch_layout), &m_outChannelLayout);

            outFrame->nb_samples = remaining_samples;

            if ((ret = av_frame_get_buffer(outFrame, 0)) < 0) {
                logError("Error obtaining buffer for output remaining frame", ret);
                return;
            }

            ret = swr_convert(tmpSwrCtx, (uint8_t **)outFrame->extended_data, outFrame->nb_samples,
                                         NULL, 0);
            if (ret < 0)
            {
                outFrame->nb_samples = 0;
                logError("Error resampling", ret);
                return;
            }
            outFrame->nb_samples = ret;


            remaining_samples = swr_get_out_samples(tmpSwrCtx, 0);
        }
        logDebug(DecodeBrokenFrame) << "Remaining samples: " << remaining_samples << std::endl;

        swr_free(&tmpSwrCtx);

        return;
    }

    logDebug() << "prepared " << std::endl;

#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    logDebug() << "decode samples: " << inFrame->nb_samples << " (" << m_inSampleRate << ") -> " << dst_nb_samples << " (" << m_outSampleRate << ") . channel " << inFrame->channel_layout << std::endl;
#else
    char buf_in[128];
    av_channel_layout_describe(&inFrame->ch_layout, buf_in, 128);
    logDebug() << "decode samples: " << inFrame->nb_samples << " (" << m_inSampleRate << ") -> " << dst_nb_samples << " (" << m_outSampleRate << ") . channel " << buf_in << std::endl;
#endif
    int r = swr_convert_frame(m_swrCtx, outFrame, inFrame);
    if (r != 0)
    {
        logError("error resampling frame", r);
    }


#ifdef DEBUG
    int remaining_samples = swr_get_out_samples(m_swrCtx, 0);
    if (remaining_samples)
        logDebug(TraceSamples) << "Remaining samples: " << remaining_samples << std::endl;

    logDebug(TraceDecode) << "resampled frame at " << currentDecodingPosition() << std::endl;
#endif
}

void AudioFile::writeOutFrame(const AVFrame *frame)
{
#ifdef DEBUG
    logDebug(TraceDecode) << "writting frame to output (" << frame->nb_samples << " samples)" << std::endl;
#endif
    m_output->prepare(frame->nb_samples);
    uint8_t **buffer = m_output->getBuffer(frame->nb_samples);
    int channels = frame->ch_layout.nb_channels;
    av_samples_copy(buffer, frame->extended_data, 0, 0, frame->nb_samples, channels, static_cast<AVSampleFormat>(frame->format));
    m_output->written(frame->nb_samples);
#ifdef DEBUG
    logDebug(TraceDecode) << "written" << std::endl;
#endif
}

void AudioFile::handleOutFrame(const AVFrame *frame)
{
    writeOutFrame(frame);
}

int AudioFile::firstAudioStreamIndex() const
{
    int audioStreamIndex = -1;
    for(size_t i = 0; i < m_formatCtx->nb_streams; ++i) {
        if(m_formatCtx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO) {
            audioStreamIndex = i;
            break;
        }
    }
    return audioStreamIndex;
}

std::vector<int> AudioFile::audioStreamIndexes() const
{
    std::vector <int> indexes;
    for(size_t i = 0; i < m_formatCtx->nb_streams; ++i) {
        if(m_formatCtx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO) {
            indexes.push_back(i);
        }
    }
    return indexes;
}

int AudioFile::receiveFramesAndHandle() {
    int err = 0;
#ifdef TRACE
    std::cout << "receiveFramesAndHandle" << std::endl;
#endif
    while((err = avcodec_receive_frame(m_codecCtx, m_frame)) == 0) {
        m_lastDecodedPTS = m_frame->pts;

        resampleFrame(m_outFrame, m_frame);
        handleOutFrame(m_outFrame);

        av_frame_unref(m_outFrame);
        av_frame_unref(m_frame);
    }
    return err;
}

void AudioFile::drainDecoder()
{
    int err = 0;
    logDebug(TraceDecode) << "drainDecoder" << std::endl;
    if ((err = avcodec_send_packet(m_codecCtx, NULL)) == 0)
    {
        err = receiveFramesAndHandle();
        if (err != AVERROR(EAGAIN) && err != AVERROR_EOF)
            logError("Receive error", err);
    }
    else
    {
        logError("Send error", err);
    }

// Now we drain the resampler context which might be buffering data

    int out_samples = swr_get_out_samples(m_swrCtx, 0);
    logDebug(TraceDecode) << "draining swr prepare " << out_samples << " samples" << std::endl;

    m_output->prepare(out_samples);
    uint8_t **buffer = m_output->getBuffer(out_samples);
    if (!buffer)
    {
        std::cout << "buffer is NULL" << std::endl;
        return;
    }
    int real_out_samples = swr_convert(m_swrCtx, buffer, out_samples,
                                       NULL, 0);
    if (real_out_samples<0)
        logError("Error resampling", real_out_samples);

    logDebug(TraceDecode) << "draining swr using actually " << real_out_samples << " samples" << std::endl;

    m_output->written(real_out_samples);
}

void AudioFile::setOutput(DecodeOutput *output)
{
    m_output = output;
}

int AudioFile::decode()
{
    int err;

    if ((err = avcodec_open2(m_codecCtx, m_codec, NULL)) != 0)
    {
        logError("Error opening codec", err);
        return -1;
    }

    m_swrCtx = swr_alloc();
    if (!m_swrCtx) {
        logError("Could not allocate resampler context");
        return AVERROR(ENOMEM);
    }
    logDebug(DecodeParameters) << "sample_rate: " << m_codecCtx->sample_rate << std::endl;
    logDebug(DecodeParameters) << "request_sample_fmt: " << av_get_sample_fmt_name (m_codecCtx->request_sample_fmt) << std::endl;

    logDebug(DecodeParameters) << "out sample_rate: " << m_outSampleRate << std::endl;
    logDebug(DecodeParameters) << "out request_sample_fmt: " << av_get_sample_fmt_name(m_outSampleFmt) << std::endl;

#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
    av_opt_set_int(m_swrCtx, "in_channel_layout", m_codecCtx->channel_layout, 0);
    m_inChannelLayout = m_codecCtx->channel_layout;
    av_opt_set_int(m_swrCtx, "out_channel_layout", m_outChannelLayout, 0);
    logDebug(DecodeParameters) << "channel_layout: " << m_codecCtx->channel_layout << std::endl;
    logDebug(DecodeParameters) << "out channel_layout: " << m_outChannelLayout << std::endl;
#else

    av_channel_layout_copy(&m_inChannelLayout, &(m_codecCtx->ch_layout));

    if (m_inChannelLayout.order == AV_CHANNEL_ORDER_UNSPEC)
        av_channel_layout_default(&m_inChannelLayout, m_inChannelLayout.nb_channels);

    av_opt_set_chlayout(m_swrCtx, "in_chlayout", &m_inChannelLayout, 0);
    av_opt_set_chlayout(m_swrCtx, "out_chlayout", &m_outChannelLayout, 0);

    char buf_in[128];
    char buf_out[128];
    av_channel_layout_describe(&m_inChannelLayout, buf_in, 128);
    av_channel_layout_describe(&m_outChannelLayout, buf_out, 128);
    logDebug(DecodeParameters) << "channel_layout: " << buf_in << std::endl;
    logDebug(DecodeParameters) << "out channel_layout:" << buf_out << std::endl;
#endif
    av_opt_set_int(m_swrCtx, "in_sample_rate", m_codecCtx->sample_rate, 0);
    av_opt_set_sample_fmt(m_swrCtx, "in_sample_fmt", m_codecCtx->request_sample_fmt, 0);
    m_inSampleRate = m_codecCtx->sample_rate;
    m_inSampleFmt = m_codecCtx->request_sample_fmt;

    av_opt_set_int(m_swrCtx, "out_sample_rate", m_outSampleRate, 0);
    av_opt_set_sample_fmt(m_swrCtx, "out_sample_fmt", m_outSampleFmt, 0);

    if ((swr_init(m_swrCtx)) < 0) {
        std::cerr << "Failed to initialize the resampling context" << std::endl;
        return -1;
    }

    AVStream *stream = m_formatCtx->streams[m_audioStreamIndex];

    int64_t estimatedSamples = (int) ((m_outSampleRate * (double)stream->time_base.num / stream->time_base.den) * stream->duration);

    m_output->init(
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
            m_outChannelNumber,
#else
            m_outChannelLayout.nb_channels,
#endif
            m_outSampleFmt, estimatedSamples, m_outSampleRate);
    if (!m_output->isValid())
    {
        std::cerr << "Error initializing output" << std::endl;
        return -2;
    }

    m_frame = av_frame_alloc();
    if (m_frame == NULL) {
        return -1;
    }

    m_outFrame = av_frame_alloc();
    if (m_outFrame == NULL) {
        return -1;
    }

    AVPacket* packet = av_packet_alloc();
    logDebug(TraceDecode) << "iterating on frames..." << std::endl;

    int frame_idx = 0;

    while ((err = av_read_frame(m_formatCtx, packet)) != AVERROR_EOF)
    {
        logDebug(TraceDecode) << "reading frame " << frame_idx++ << std::endl;
        if(err != 0)
        {
            logError("Read frame error", err);
            break;
        }
        if(packet->stream_index != m_audioStreamIndex)
        {
            logDebug(TraceDecode) << "packet not from audio stream" << std::endl;
            av_packet_unref(packet);
            continue;
        }

        if((err = avcodec_send_packet(m_codecCtx, packet)) == 0)
        {
            av_packet_unref(packet);
        } else {
            if (err == AVERROR(EAGAIN))
                logError("Send packet error eagain", err);
            else
                logError("Send packet error", err);
            av_packet_unref(packet);
        }

        // EAGAIN -> more packets need to be sent to the codec in order to receive a frame back.
        if((err = receiveFramesAndHandle()) != AVERROR(EAGAIN))
        {
            logError("Receive frame error", err);
        }
    }

    logDebug(TraceDecode) << "will drain now" << std::endl;

    drainDecoder();

    m_output->terminate();
    av_packet_free(&packet);

    return 0;
}

std::string AudioFile::codecName() const
{
    return m_codec->name;
}

std::string AudioFile::formatName() const
{
    return m_formatCtx->iformat->name;
}

double AudioFile::containerDuration() const
{
    return m_formatCtx->duration / (double)AV_TIME_BASE;
}

int AudioFile::containerBitrate() const
{
    return m_formatCtx->bit_rate;
}

int AudioFile::streamBitrate() const
{
    return m_formatCtx->streams[m_audioStreamIndex]->codecpar->bit_rate;
}

std::string AudioFile::streamSampleFormatName() const
{
    AVSampleFormat format=static_cast<AVSampleFormat>(m_formatCtx->streams[m_audioStreamIndex]->codecpar->format);
    return av_get_sample_fmt_name(format);
}

int AudioFile::streamBytesPerSample() const
{
    AVSampleFormat format=static_cast<AVSampleFormat>(m_formatCtx->streams[m_audioStreamIndex]->codecpar->format);
    return av_get_bytes_per_sample(format);
}

int AudioFile::streamBitsPerRawSample() const
{
    return m_formatCtx->streams[m_audioStreamIndex]->codecpar->bits_per_raw_sample;
}
