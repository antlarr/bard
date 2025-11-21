#include <string>
#include <map>

#ifdef __cplusplus
extern "C" {
#endif

#include <libavutil/channel_layout.h>
#include <libavutil/samplefmt.h>

#ifdef __cplusplus
}
#endif

using std::string;
using std::map;
struct AVPacket;
struct AVFrame;
struct AVCodec;
struct AVCodecContext;
struct AVFormatContext;
struct AVAudioFifo;

class Encoder
{
public:
    Encoder();
    virtual ~Encoder();

    void setChannelLayout(const AVChannelLayout &channelLayout);
    void setSampleRate(int sampleRate);
    void setSampleFormat(const enum AVSampleFormat &sampleFormat);

    int openOutput(const string &filename, const string &encoder, int bitrate=0);

    int pushFrame(const AVFrame *frame);

    int terminate();

protected:
    int addSamples(const AVFrame *frame);
    int encodeFrame(AVFrame *frame, bool *frame_encoded);

    AVAudioFifo *m_fifo = nullptr;
    AVFormatContext *m_formatCtx = nullptr;
    AVCodecContext *m_codecCtx = nullptr;
    const AVCodec *m_codec = nullptr;

    bool m_channelLayoutIsSet = false;
    AVChannelLayout m_channelLayout = {};
    int m_sampleRate = 0;
    enum AVSampleFormat m_sampleFmt = AV_SAMPLE_FMT_S16;

    int m_pts = 0;
};
