#!/usr/bin/python3
from bard import bard_audiofile

# x = bard_audiofile.decode(path='test4-header-missing.mp3')
# with open('test4-header-missing.mp3', 'rb') as f:
#    data = f.read()

# x = bard_audiofile.decode(path='test4-header-missing.mp3')
# x = bard_audiofile.decode(data=data)
x = bard_audiofile.decode(path='test16.mp3')

with open('output.raw', 'wb') as f:
    f.write(x[0])

print(x[1])
