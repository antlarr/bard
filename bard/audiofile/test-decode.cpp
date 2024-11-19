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

// Usage: ./test-decode --buffer no --reference-file tests/test1.flac.raw.original ../test1.flac

#include "audiofile.h"
#include "filedecodeoutput.h"
#include "bufferdecodeoutput.h"
#include "referencedata.h"

#include <stdio.h>
#include <string>
#include <iostream>
#include <vector>
#include <algorithm>
#include <tuple>
#include <boost/program_options.hpp>

using namespace boost::program_options;
using std::string;

char *readFromFile(const string& filename, long *size)
{
    long fileSize;
    FILE *f = fopen(filename.c_str(), "r");
    if (!f)
    {
        int err = errno;
        std::cerr << "Error opening file:" << strerror(err) << std::endl;
        return nullptr;
    }

    fseek(f, 0, SEEK_END); // seek to end of file
    fileSize = ftell(f); // get current file pointer
    fseek(f, 0, SEEK_SET);

    char *data = (char *)malloc(fileSize);

    fileSize = fread(data, 1, fileSize, f);

    if (size)
        *size = fileSize;

    return data;
}

void saveToFile(BufferDecodeOutput *output, const string& filename)
{
    FILE* outFile;
    outFile = fopen(filename.c_str(), "w+");
    if (output->isPlanar())
    {
        for (int ch=0; ch < output->channelCount() ; ch++)
        {
            fwrite(output->data(ch), 1, output->size(), outFile);
        }
    }
    else
        fwrite(output->data(), 1, output->size(), outFile);

    fclose(outFile);
}

int main(int argc, char *argv[]) {
    options_description desc{"Options"};
    desc.add_options()
        ("help,h", "Help screen")
        ("buffer", value<bool>()->default_value(true), "Use buffer")
        ("input-file", value<string>()->required(), "Input file")
        ("reference-file", value<string>(), "File with reference data")
        ("sample-rate", value<long>()->default_value(0), "Set output sample rate")
        ("sample-format", value<string>()->default_value(""), "Set output sample format")
        ("channels", value<string>()->default_value(""), "Set output channels number")
        ("output", value<string>()->default_value(""), "Output file");

    positional_options_description p;
    p.add("input-file", 1);

    variables_map vm;
    store(command_line_parser(argc, argv).options(desc).positional(p).run(), vm);
    if (vm.count("help"))
    {
        std::cout << desc << std::endl;
        exit(1);
    }

    notify(vm);

    string filename = vm["input-file"].as<string>();

    char *data = nullptr;
    int err = 0;
    AudioFile audiofile;

    if (vm["buffer"].as<bool>())
    {
        long dataSize;
        data  = readFromFile(filename, &dataSize);
        if (!data)
        {
            std::cerr << "Can't read file: " << filename << std::endl;
            return 1;
        }
        err = audiofile.open(data, dataSize, "");
    }
    else
    {
        err = audiofile.open(filename);
    }

    if (err)
    {
        std::cerr << "Error opening file" << std::endl;
        return 1;
    }

    string outFilename = vm["output"].as<string>();
    if (outFilename.empty())
        outFilename = std::string(filename) + ".raw";

    if (vm["sample-rate"].as<long>())
    {
        audiofile.setOutSampleRate(vm["sample-rate"].as<long>());
    }
    if (!vm["sample-format"].as<string>().empty())
    {
        audiofile.setOutSampleFormat(vm["sample-format"].as<string>());
    }
    if (!vm["channels"].as<string>().empty())
    {
        // It can be a number or something like "5.1" or "quad"
        const std::string ch = vm["channels"].as<string>();
        if (ch.find_first_not_of("0123456789") == std::string::npos)
        {
            int nch = strtol(ch.c_str(), NULL, 10);
            audiofile.setOutChannels(nch);
        }
        else
        {
            std::cout << "set channels to " << vm["channels"].as<string>() << std::endl;
            audiofile.setOutChannelLayout(vm["channels"].as<string>());
        }
    }

    DecodeOutput *output;

    if (vm["buffer"].as<bool>())
        output = new BufferDecodeOutput();
    else
        output = new FileDecodeOutput(outFilename);

    if (vm.count("reference-file"))
    {
        output->setReferenceFile(vm["reference-file"].as<string>());
    }

    audiofile.setOutput(output);
    audiofile.decode();


    std::cout << "codec name: " << audiofile.codecName() << std::endl;
    std::cout << "format name: " << audiofile.formatName() << std::endl;
    std::cout << "duration: " << audiofile.containerDuration() << std::endl;
    std::cout << "decoded duration: " << output->duration() << std::endl;
    std::cout << "stream bitrate: " << audiofile.streamBitrate() << std::endl;
    std::cout << "container bitrate: " << audiofile.containerBitrate() << std::endl;
    std::cout << "stream bytes per sample: " << audiofile.streamBytesPerSample() << std::endl;
    std::cout << "stream bits per raw sample: " << audiofile.streamBitsPerRawSample() << std::endl;
    std::cout << "stream sample format: " << audiofile.streamSampleFormatName() << std::endl;
    std::cout << "output sample format: " << output->sampleFormatName() << std::endl;
    std::cout << "output bytes per sample: " << output->bytesPerSample() << std::endl;
    std::cout << "output sample rate: " << output->sampleRate() << std::endl;
    std::cout << "libavcodec: " << LIBAVCODEC_IDENT << std::endl;
    std::cout << "libavformat: " << LIBAVFORMAT_IDENT << std::endl;
    std::cout << "libavutil: " << LIBAVUTIL_IDENT << std::endl;
    std::cout << "libswresample: " << LIBSWRESAMPLE_IDENT << std::endl;
    auto loggedMessages = audiofile.loggedMessages();
    for (auto it: loggedMessages)
    {
        std::cout << std::get<0>(it) << std::get<1>(it) << std::get<2>(it) << std::endl;
    }

    bool ok = true;
    if (output->referenceData())
    {
        ok = output->referenceData()->isCheckOk();
        std::cout << "output matches reference data: "  << (ok ? "yes" : "no" ) << std::endl;
    }

    if (vm["buffer"].as<bool>())
        saveToFile(static_cast<BufferDecodeOutput *>(output), outFilename);

    delete output;
    if (data) free(data);
    return (ok ? 0 : 1);
}
