#!/usr/bin/python3

import sys
from utils import decodeAudio, detect_silence_at_beginning_and_end
import dynamicrange as dynamicrange


def main():
    filename = sys.argv[1]
    audiodata, properties = decodeAudio(filename)

    r = dynamicrange.calculate(audiodata, properties)
    print('DR:', r)

    minlen=10
    thr=-67
    silences = detect_silence_at_beginning_and_end(audiodata,
                                                   properties,
                                                   min_silence_len=minlen,
                                                   silence_thresh=thr)
    print('Silences: ', silences)
    print(silences[0][1] - silences[0][0], silences[1][1] - silences[1][0])


if __name__ == "__main__":
    main()
