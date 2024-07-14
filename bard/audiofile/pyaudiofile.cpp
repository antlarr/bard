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

#include <boost/python/module.hpp>
#include <boost/python/def.hpp>
#include <boost/python/extract.hpp>
#include <boost/python/stl_iterator.hpp>
#include <boost/python/list.hpp>
#include <boost/python/dict.hpp>
#include <boost/python/tuple.hpp>
#include <boost/python/class.hpp>
#include <boost/python/overloads.hpp>
#include <boost/python/return_internal_reference.hpp>

#include <string>
#include <iostream>

#include "audiofile.h"
#include "bufferdecodeoutput.h"
#include "version.h"

using namespace boost;
using namespace std;

python::dict versions()
{
    python::dict v;
    v["bard_audiofile"] = AV_STRINGIFY(BARD_AUDIOFILE_VERSION);
    v["libavcodec"]  = AV_STRINGIFY(LIBAVCODEC_VERSION);
    v["libavformat"] = AV_STRINGIFY(LIBAVFORMAT_VERSION);
    v["libavutil"]   = AV_STRINGIFY(LIBAVUTIL_VERSION);
    v["libswresample"] = AV_STRINGIFY(LIBSWRESAMPLE_VERSION);
    return v;
}

python::dict extractInfoDict(const AudioFile &audiofile, const BufferDecodeOutput &output)
{
    python::dict info;
    info["library_versions"] = versions();

    info["codec"] = audiofile.codecName();
    info["format_name"] = audiofile.formatName();
    info["container_duration"] = audiofile.containerDuration();
    info["container_bitrate"] = audiofile.containerBitrate();

    info["stream_bitrate"] = audiofile.streamBitrate();
    info["stream_bytes_per_sample"] = audiofile.streamBytesPerSample();
    info["stream_bits_per_raw_sample"] = audiofile.streamBitsPerRawSample();
    info["stream_sample_format"] = audiofile.streamSampleFormatName();

    if (output.isValid())
    {
        info["decoded_sample_format"] = output.sampleFormatName();
        info["decoded_bytes_per_sample"] = output.bytesPerSample();
        info["decoded_duration"] = output.duration();
        info["decoded_sample_rate"] = output.sampleRate();
        info["decoded_channels"] = output.channelCount();
        if (output.samplesCount() != 0)
        {
            info["samples"] = output.samplesCount();
        }
        else
        {
            Py_ssize_t size;
            if (output.isPlanar())
                size = output.channelCount() * output.lineSize();
            else
                size = output.size();
            info["samples"] = size / (output.bytesPerSample() * audiofile.channels());
        }
        info["is_planar"] = output.isPlanar();
    }

    info["channels"] = audiofile.channels();
    info["sample_rate"] = audiofile.sampleRate();
    info["messages"] = audiofile.loggedMessages();
    return info;
}

python::object convertToPythonBytes(const BufferDecodeOutput &output)
{
    Py_ssize_t size;
    if (output.isPlanar())
        size = output.channelCount() * output.lineSize();
    else
        size = output.size();

    const char *data = reinterpret_cast<char *>(output.data());
    python::object bytes(python::handle<>(PyBytes_FromStringAndSize(data, size)));
    return bytes;
}

python::tuple decode_from_data(const char *buffer, Py_ssize_t length, long sample_rate=0,
                               const std::string &sample_fmt=std::string(),
                               long channel_number=0, const std::string &channel_layout=std::string())
{
#ifdef DEBUG
    std::cout << "decode_from_data" << std::endl;
#endif
    AudioFile audiofile;
    BufferDecodeOutput output;

    audiofile.open(buffer, length, "");
    if (sample_rate)
        audiofile.setOutSampleRate(sample_rate);
    if (!sample_fmt.empty())
        audiofile.setOutSampleFormat(sample_fmt);
    if (!channel_layout.empty())
        audiofile.setOutChannelLayout(channel_layout);
    else if (channel_number > 0)
        audiofile.setOutChannels(channel_number);
    audiofile.setOutput(&output);
    audiofile.decode();

    python::dict info = extractInfoDict(audiofile, output);

    return python::make_tuple(convertToPythonBytes(output), info);
}

python::tuple decode_from_file(const std::string &path, long sample_rate=0,
                               const std::string &sample_fmt=std::string(),
                               long channel_number=0, const std::string &channel_layout=std::string())
{
#ifdef DEBUG
    std::cout << "decode_from_file" << std::endl;
#endif
    AudioFile audiofile;
    BufferDecodeOutput output;

    audiofile.open(path);
    if (sample_rate)
        audiofile.setOutSampleRate(sample_rate);
    if (!sample_fmt.empty())
        audiofile.setOutSampleFormat(sample_fmt);
    if (!channel_layout.empty())
        audiofile.setOutChannelLayout(channel_layout);
    else if (channel_number > 0)
        audiofile.setOutChannels(channel_number);

    audiofile.setOutput(&output);
    audiofile.decode();

    python::dict info = extractInfoDict(audiofile, output);

    return boost::python::make_tuple(convertToPythonBytes(output), info);
}

boost::python::object decode(const boost::python::object &path,
                             const boost::python::object &data,
                             const boost::python::object &sample_rate,
                             const boost::python::object &sample_fmt,
                             const boost::python::object &channel_number,
                             const boost::python::object &channel_layout,
                             const boost::python::object &use_tmp_file)
{
#ifdef DEBUG
    std::cout << "decode" << std::endl;
#endif
    if ((path.is_none() && data.is_none()) ||
        (!path.is_none() && !data.is_none()))
    {
        throw std::invalid_argument("invalid arguments");
    }
    bool use_temporary_file = PyObject_IsTrue(use_tmp_file.ptr());
    long csample_rate = 0;
    std::string csample_fmt;
    long cchannel_number = 0;
    std::string cchannel_layout;
    if (!sample_rate.is_none() && PyLong_Check(sample_rate.ptr()))
        csample_rate = PyLong_AsLong(sample_rate.ptr());
    if (!sample_fmt.is_none() && PyUnicode_Check(sample_fmt.ptr()))
        csample_fmt = boost::python::extract<std::string>(sample_fmt);

    if (!channel_layout.is_none() && PyUnicode_Check(channel_layout.ptr()))
        cchannel_layout = boost::python::extract<std::string>(channel_layout);
    else if (!channel_number.is_none() && PyLong_Check(channel_number.ptr()))
        cchannel_number = PyLong_AsLong(channel_number.ptr());


    if (data && !data.is_none())
    {
        if (!PyBytes_Check(data.ptr()))
        {
            throw std::invalid_argument("data must be of bytes type");
        }

        char *buffer;
        Py_ssize_t length;
        int r = PyBytes_AsStringAndSize(data.ptr(), &buffer, &length);
        if (r < 0)
            return boost::python::object();

        return decode_from_data(buffer, length, csample_rate, csample_fmt, cchannel_number, cchannel_layout);
    }
    else if (path && !path.is_none())
    {
#ifdef DEBUG
    std::cout << "decode path" << std::endl;
#endif

        if (!PyUnicode_Check(path.ptr()) && !PyBytes_Check(data.ptr()))
        {
            throw std::invalid_argument("data must be of str type");
        }
        std::string str_path = boost::python::extract<std::string>(path);

        return decode_from_file(str_path, csample_rate, csample_fmt, cchannel_number, cchannel_layout);
    }

    throw std::invalid_argument("invalid arguments. Must set path or data");
    return python::object();

}

struct LogRecordList_to_python_list
{
    static PyObject *convert(std::vector<AudioFile::LogRecord> const &x)
    {
        PyObject * l = PyList_New(0);
        for (auto it: x)
        {
            PyObject *record = PyTuple_New(3);
            PyTuple_SET_ITEM(record, 0, PyFloat_FromDouble(std::get<0>(it)));
            PyTuple_SET_ITEM(record, 1, PyLong_FromLong(static_cast<long>(std::get<1>(it))));
            const string &msg = std::get<2>(it);
            PyTuple_SET_ITEM(record, 2, PyBytes_FromStringAndSize(msg.c_str(), msg.size()));

            PyList_Append(l, record);
        }
        return l;
    };
};


BOOST_PYTHON_FUNCTION_OVERLOADS(decode_overloads, decode, 7, 7);

BOOST_PYTHON_MODULE(bard_audiofile)
{

    using namespace python;
    def("decode", decode, decode_overloads((python::arg("path")=object(), python::arg("data")=object(),
                                            python::arg("sample_rate")=object(), python::arg("sample_fmt")=object(),
                                            python::arg("channel_number")=object(), python::arg("channel_layout")=object(),
                                            python::arg("use_tmp_file")=object())));
    def("versions", versions);

    to_python_converter< std::vector<AudioFile::LogRecord>, LogRecordList_to_python_list>();
}
