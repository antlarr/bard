#!/usr/bin/env python3
#
# gen_noise.py - generate a test audio file with ffmpeg:
#
#   [ <leading_silence_ms> silence ] + [ <noise_ms> white noise @ <db> ] + [ <trailing_silence_ms> silence ]
#
# Usage: gen_noise.py <leading_silence_ms> <noise_ms> <db> <trailing_silence_ms> <format>
#
#   leading_silence_ms   leading silence, in milliseconds (integer)
#   noise_ms             length of the noise segment in milliseconds (integer)
#   db                   noise level in dB, e.g. -20 (0 = full scale); a positive
#                        value like 20 is interpreted as -20 dBFS
#   trailing_silence_ms  trailing silence, in milliseconds (integer)
#   format               output audio format, e.g. wav, flac, mp3, aac, ogg, m4a
#
# Example: gen_noise.py 500 1000 -20 1000 wav
#
# Output is written to: sil<ms>ms_noise<db>db_sil<ms>ms.<format> in the cwd.

import argparse
import subprocess
import sys

SR = 44100


def nonneg_int(value):
    try:
        iv = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not an integer number of ms")
    if iv < 0:
        raise argparse.ArgumentTypeError(f"'{value}' must not be negative")
    return iv


def ms2sec(ms):
    """ms -> seconds string with millisecond precision, e.g. 500 -> '0.500'."""
    return f"{ms // 1000}.{ms % 1000:03d}"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Generate [silence + white noise + silence] audio with ffmpeg.",
        epilog="Example: gen_noise.py 500 1000 -20 1000 wav",
    )
    parser.add_argument("leading_silence_ms", type=nonneg_int,
                        help="leading silence, in milliseconds")
    parser.add_argument("noise_ms", type=nonneg_int,
                        help="length of the noise segment, in milliseconds")
    parser.add_argument("db", type=float,
                        help="noise level in dB, e.g. -20 (0 = full scale)")
    parser.add_argument("trailing_silence_ms", type=nonneg_int,
                        help="trailing silence, in milliseconds")
    parser.add_argument("format",
                        help="output audio format, e.g. wav, flac, mp3, aac, ogg, m4a")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)

    if args.noise_ms == 0:
        print("Error: noise duration must be greater than 0", file=sys.stderr)
        return 1

    # interpret a positive dB value as dB below full scale: 20 -> -20
    db = -args.db if args.db > 0 else args.db

    fmt = args.format[1:] if args.format.startswith(".") else args.format
    if not fmt:
        print("Error: format must not be empty", file=sys.stderr)
        return 1

    # anoisesrc expects a linear amplitude (0..1), so convert dBFS to linear
    amp = format(10 ** (db / 20), ".10g")

    # build the segment list, dropping zero-length silences
    segs = []
    if args.leading_silence_ms > 0:
        segs.append(f"aevalsrc=0:d={ms2sec(args.leading_silence_ms)}:s={SR}:c=stereo")
    segs.append(f"anoisesrc=d={ms2sec(args.noise_ms)}:r={SR}:a={amp}")
    if args.trailing_silence_ms > 0:
        segs.append(f"aevalsrc=0:d={ms2sec(args.trailing_silence_ms)}:s={SR}:c=stereo")

    # let the output muxer pick the native codec (wav->pcm_s16le, mp3->libmp3lame, ...)
    out = f"sil{args.leading_silence_ms}ms_noise{db:g}db_sil{args.trailing_silence_ms}ms.{fmt}"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for seg in segs:
        cmd += ["-f", "lavfi", "-i", seg]
    labels = "".join(f"[{i}:a]" for i in range(len(segs)))
    cmd += ["-filter_complex", f"{labels}concat=n={len(segs)}:v=0:a=1", out]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Error: ffmpeg failed (exit code {result.returncode})", file=sys.stderr)
        return 1

    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
