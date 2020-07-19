#!/usr/bin/python3
from bard import bard_audiofile
import sys
try:
    input_file = sys.argv[1]
except IndexError:
    print('Error: please, specify an input file '
          '(and optionally an output raw file)')

try:
    output_file = sys.argv[2]
except IndexError:
    output_file = 'output.raw'

# x = bard_audiofile.decode(path='test4-header-missing.mp3')
# with open('test4-header-missing.mp3', 'rb') as f:
#    data = f.read()

# x = bard_audiofile.decode(path='test4-header-missing.mp3')
# x = bard_audiofile.decode(data=data)
x = bard_audiofile.decode(path=input_file)


with open(output_file, 'wb') as f:
    f.write(x[0])

print(x[1])
