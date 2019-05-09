# -*- coding: utf-8 -*-
import subprocess
import math


def fixEncoding(s):
    # pos=s.find('don')
    # print(pos)
    # print(ord(s[pos+3]))
    # while pos!=-1 and ord(s[pos+3])==65533:
    #    s=s[:pos+3]+"'"+s[pos+4:]
    #    pos=s.find('don', pos+3)

    orig = s
    s = s.decode('utf-8', 'replace')
    pos = s.find(chr(65533))
    if pos == -1:
        print('Error fixing encoding: Unknown bad character in %s' % s)
        raise

    while pos > 0 and s[pos - 1] == 'I' and s[pos + 1] == 'm':
        s = s[:pos] + "'" + s[pos + 1:]
        pos = s.find(chr(65533))

    print("%s Changed to %s" % (orig, s))
    return s


class FFProbeMetadata(dict):

    def __init__(self, path):
        # print('Using ffprobe!', path)
        try:
            # ffprobe -v error -select_streams a:0 -show_format -show_streams -of flat -i file
            output = subprocess.check_output(['ffprobe', '-v', 'error',
                                              '-select_streams', 'a:0',
                                              '-show_format', '-show_streams',
                                              '-of', 'flat', '-i', path],
                                             stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            output = e.output
            if 'Failed to recognize file format' in output.decode('utf-8',
                                                                  'ignore'):
                print('Failed to recognize file format of %s: %s' % (path,
                      output))
                return None

        self.parseFFProbeOutput(output)

        try:
            stream_duration = self.get('streams.stream.0.duration')
            format_duration = self.get('format.duration')
            if (stream_duration != format_duration and
               math.fabs(float(stream_duration) - float(format_duration)) >
               0.00001):
                print('duration mismatch in %s : stream(%s) != format(%s)' %
                      (path, self.get('streams.stream.0.duration'),
                       self.get('format.duration')))
        except KeyError:
            print(path)
            raise

    def parseFFProbeOutput(self, output):
        # print(output)
        for line in output.split(b'\n'):
            try:
                s = line.decode('utf-8')
            except UnicodeError:
                s = fixEncoding(line)

            sep = s.find('=')
            value = s[sep + 1:]
            if value and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            value = value.replace('\\"', '"')
            self[s[:sep].lower()] = value
