
#include "encoder.h"
#include "log.h"
#include <string>
#include <iostream>

#ifdef __cplusplus
extern "C" {
#endif

#include <libavformat/avio.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/opt.h>
#include <libavutil/audio_fifo.h>

#ifdef __cplusplus
}
#endif

Encoder::Encoder()
{
}

Encoder::~Encoder()
{
    av_audio_fifo_free(m_fifo);
    m_fifo = nullptr;
    avcodec_free_context(&m_codecCtx);
    m_codecCtx = nullptr;
    avio_closep(&(m_formatCtx)->pb);
    avformat_free_context(m_formatCtx);
    m_formatCtx = nullptr;
}

void Encoder::setChannelLayout(const AVChannelLayout &channelLayout)
{
//#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(61,19,100)
//    m_outChannelLayout = av_get_channel_layout(channelLayout.c_str());
//    m_outChannelNumber = av_get_channel_layout_nb_channels(m_outChannelLayout);
//#else
    av_channel_layout_copy(&m_channelLayout, &channelLayout);
    m_channelLayoutIsSet = true;
//#endif
}

void Encoder::setSampleRate(int sampleRate)
{
    m_sampleRate = sampleRate;
}

void Encoder::setSampleFormat(const enum AVSampleFormat &sampleFormat)
{
    m_sampleFmt = sampleFormat;
}

int Encoder::openOutput(const string &filename, const string &encoder, int bitrate)
{
    AVIOContext *avioCtx = nullptr;
    AVStream *stream = nullptr;
    int err;

    m_pts = 0;

    if ((err = avio_open(&avioCtx, filename.c_str(), AVIO_FLAG_WRITE)) < 0)
    {
        std::cerr << "Error: Cannot open output file "
                  << filename << av_err2str(err) << std::endl;
        return err;
    }

    if (!(m_formatCtx = avformat_alloc_context()))
    {
        std::cerr << "Error: Cannot allocate output format context" << std::endl;
        return AVERROR(ENOMEM);
    }

    m_formatCtx->pb = avioCtx;

    if (!(m_formatCtx->oformat = av_guess_format(NULL, filename.c_str(), NULL)))
    {
        std::cerr << "Error: Cannot find output file format" << std::endl;
        return -1;
    }

    if (!(m_formatCtx->url = av_strdup(filename.c_str())))
    {
        std::cerr << "Error: Cannot dup filename" << std::endl;
        return AVERROR(ENOMEM);
    }


    if (!(m_codec = avcodec_find_encoder_by_name(encoder.c_str())))
    {
        std::cerr << "Error: Cannot find encoder" << std::endl;
        return AVERROR(ENOMEM);
    }

    if (!(stream = avformat_new_stream(m_formatCtx, NULL))) {
        std::cerr << "Error: Cannot allocate new stream" << std::endl;
        return AVERROR(ENOMEM);
    }

    m_codecCtx = avcodec_alloc_context3(m_codec);
    if (!m_codecCtx) {
        std::cerr << "Error: Cannot allocate encoding context" << std::endl;
        return AVERROR(ENOMEM);
    }

    /* Set the basic encoder parameters.
     * The input file's sample rate is used to avoid a sample rate conversion. */
    av_channel_layout_copy(&m_codecCtx->ch_layout, &m_channelLayout);
    m_codecCtx->sample_rate    = m_sampleRate;
    m_codecCtx->sample_fmt     = m_sampleFmt;
//    m_codecCtx->bit_rate       = bitrate;

    /* Set the sample rate for the container. */
    stream->time_base.den = m_sampleRate;
    stream->time_base.num = 1;

    /* Some container formats (like MP4) require global headers to be present.
     * Mark the encoder so that it behaves accordingly. */
    if (m_formatCtx->oformat->flags & AVFMT_GLOBALHEADER)
        m_codecCtx->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;

    /* Open the encoder for the audio stream to use it later. */
    if ((err = avcodec_open2(m_codecCtx, m_codec, NULL)) < 0) {
        fprintf(stderr, "Could not open output codec (error '%s')\n",
                av_err2str(err));
        return err;
    }

    err = avcodec_parameters_from_context(stream->codecpar, m_codecCtx);
    if (err < 0) {
        std::cerr << "Error: Cannot set stream parameters from codecCtx" << std::endl;
        return err;
    }

    if (!(m_fifo = av_audio_fifo_alloc(m_codecCtx->sample_fmt,
                                      m_codecCtx->ch_layout.nb_channels, 1)))
    {
        std::cerr << "Error allocating fifo" << std::endl;
        return AVERROR(ENOMEM);
    }


    if ((err = avformat_write_header(m_formatCtx, NULL)) < 0) {
        std::cerr << "Error: Cannot write header: " << av_err2str(err) << std::endl;
        return err;
    }
    return 0;
}

int Encoder::addSamples(const AVFrame *frame)
{
    int err;
    if ((err = av_audio_fifo_realloc(m_fifo, av_audio_fifo_size(m_fifo) + frame->nb_samples)) < 0) {
        std::cerr << "Error: Cannot resize fifo" << std::endl;
        return err;
    }

    int written = av_audio_fifo_write(m_fifo, (void **)frame->extended_data, frame->nb_samples);
    if (written < frame->nb_samples) {
        std::cerr << "Error: Cannot write to fifo. Wrote " << written << " of " << frame->nb_samples << " samples (fifo size: " << av_audio_fifo_size(m_fifo) << ")" << std::endl;
        return AVERROR_EXIT;
    }
    return 0;
}

int Encoder::encodeFrame(AVFrame *frame, bool *frame_encoded)
{
    AVPacket *output_packet;
    int err;
    if (frame_encoded)
        *frame_encoded = false;
    if (!(output_packet = av_packet_alloc())) {
        std::cerr << "Error: Cannot allocate packet" << std::endl;
        return AVERROR(ENOMEM);
    }

    if (frame)
    {
        frame->pts = m_pts;
        m_pts += frame->nb_samples;
        std::cout << "last encoded pts " << frame->pts <<  "      next:" << m_pts << std::endl;
    }

    err = avcodec_send_frame(m_codecCtx, frame);

    if (err < 0 && err != AVERROR_EOF) {
        std::cerr << "Error: Cannot send frame: " << av_err2str(err) << std::endl;
        av_packet_free(&output_packet);
        return err;
    }

    err = avcodec_receive_packet(m_codecCtx, output_packet);

    if (err == AVERROR(EAGAIN) || err == AVERROR_EOF)
    {
        av_packet_free(&output_packet);
        return 0;
    }
    else if (err < 0)
    {
        std::cerr << "Error: Cannot encode frame: " << av_err2str(err) << std::endl;
        av_packet_free(&output_packet);
        return err;
    }
    if (frame_encoded)
        *frame_encoded = true;

    err = av_write_frame(m_formatCtx, output_packet);
    if (err < 0)
    {
        std::cerr << "Error: Cannot write frame: " << av_err2str(err) << std::endl;
        av_packet_free(&output_packet);
        return err;
    }

    av_packet_free(&output_packet);
    return 0;
}

int Encoder::pushFrame(const AVFrame *frame)
{
    int err;
    static int samples_popped = 0;
    if (frame && (err = addSamples(frame)))
        return err;

    if (av_audio_fifo_size(m_fifo) < m_codecCtx->frame_size && frame)
        return 0;

    if (!frame && av_audio_fifo_size(m_fifo) == 0)
        return 0;

    AVFrame *output_frame;
    int frame_size = FFMIN(av_audio_fifo_size(m_fifo), m_codecCtx->frame_size);

    if (!(output_frame = av_frame_alloc()))
    {
        std::cerr << "Error: Cannot allocate output frame" << std::endl;
        return AVERROR(ENOMEM);
    }
    output_frame->nb_samples     = frame_size;
    av_channel_layout_copy(&(output_frame->ch_layout), &(m_codecCtx->ch_layout));
    output_frame->format         = m_codecCtx->sample_fmt;
    output_frame->sample_rate    = m_codecCtx->sample_rate;

    if ((err = av_frame_get_buffer(output_frame, 0)) < 0)
    {
        std::cerr << "Error: Cannot allocate output frame buffer " << av_err2str(err) << std::endl;
        av_frame_free(&output_frame);
        return err;
    }

    while ((frame && av_audio_fifo_size(m_fifo) >= frame_size)
            || (!frame && av_audio_fifo_size(m_fifo) > 0))
    {
        frame_size = FFMIN(av_audio_fifo_size(m_fifo), m_codecCtx->frame_size);
        int data_read = av_audio_fifo_read(m_fifo, (void **)output_frame->data, frame_size);

        if (data_read < frame_size)
        {
            std::cerr << "Error: Read less than expected from fifo: " << data_read << " from expected: " << frame_size << ". Fifo size: " << av_audio_fifo_size(m_fifo) << std::endl;
            av_frame_free(&output_frame);
            return AVERROR_EXIT;
        }
        samples_popped += data_read;
        logDebug(TraceSamples) << "popped: " << data_read << " . Total popped " << samples_popped << std::endl;

        if (encodeFrame(output_frame, nullptr))
        {
            av_frame_free(&output_frame);
            return AVERROR_EXIT;
        }
    }
    av_frame_free(&output_frame);

    return 0;
}


int Encoder::terminate()
{
    bool frame_encoded = true;
    pushFrame(0L);
    while (frame_encoded)
        encodeFrame(0L, &frame_encoded);

    const int frame_size = m_codecCtx->frame_size;
    std::cout << "terminating: frame_size: " << frame_size << ". Fifo size: " << av_audio_fifo_size(m_fifo) << std::endl;
    //pushFrame(0L);
    std::cout << "frame_size: " << frame_size << ". Fifo size: " << av_audio_fifo_size(m_fifo) << std::endl;

    int err;
    if ((err = av_write_trailer(m_formatCtx)) < 0)
    {
        std::cerr << "Error: Cannot write trailer: " << av_err2str(err) << std::endl;
        return err;
    }
    return 0;
}
