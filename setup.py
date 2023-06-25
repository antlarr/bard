import os
from setuptools import setup, Extension
from bard import __version__


BOOST_PYTHON_LIB = os.getenv('BOOST_PYTHON_LIB', 'boost_python-py3')

extra_compile_args = ['-std=gnu++17', '-fopenmp', '-Ofast', '-mtune=native',
                      '-funroll-loops']
machine = os.uname().machine
if machine not in ['ppc64', 'ppc64le']:
    extra_compile_args.append('-march=native')

bard_ext = Extension('bard.bard_ext',
                     define_macros=[('MAJOR_VERSION', '1'),
                                    ('MINOR_VERSION', '0'),
                                    ('_GLIBCXX_PARALLEL', None)],
                     include_dirs=['/usr/include/boost'],
                     libraries=[BOOST_PYTHON_LIB, 'gomp'],
                     sources=['bard/bard_ext.cpp'],
                     extra_compile_args=extra_compile_args + ['-fopenmp'])


bard_audiofile = Extension('bard.bard_audiofile',
                           define_macros=[('MAJOR_VERSION', '1'),
                                          ('MINOR_VERSION', '0'),
                                          ('_GLIBCXX_PARALLEL', None)],
                           include_dirs=['/usr/include/boost',
                                         '/usr/include/ffmpeg'],
                           libraries=[BOOST_PYTHON_LIB, 'avcodec',
                                      'avformat', 'avutil', 'swresample'],
                           sources=['bard/audiofile/audiofile.cpp',
                                    'bard/audiofile/bufferaviocontext.cpp',
                                    'bard/audiofile/bufferdecodeoutput.cpp',
                                    'bard/audiofile/decodeoutput.cpp',
                                    'bard/audiofile/filedecodeoutput.cpp',
                                    'bard/audiofile/referencedata.cpp',
                                    'bard/audiofile/pyaudiofile.cpp'],
                           extra_compile_args=extra_compile_args)
setup(
    name="bard",
    version=__version__,
    author="Antonio Larrosa",
    author_email="larrosa@kde.org",
    packages=["bard"],
    include_package_data=True,
    url="https://github.com/antlarr/bard",
    description="Bard Music Manager - A database to manage your music, "
                "find duplicates and fix tags",
    long_description="Bard is a music manager that uses a database to store "
                     "all information about your music: location, tags, "
                     "properties, audio analysis, etc. Bard can also find "
                     "audio duplicates (not using tags, but the audio itself) "
                     "and run different kind of queries on the database.",
    python_requires=">=3.5",
    install_requires=[
        "pyacoustid",
        "mutagen",
        "Pillow",
        "pydub",
        "numpy",
        "dbus-python",
        "SQLAlchemy >= 2.0",
        "SQLAlchemy-Utils",
        "alembic",
        "Werkzeug",
        "Flask",
        "Flask-Cors",
        "Flask-Login",
        "Jinja2",
        "bcrypt",
        "paramiko",
        "importlib_resources; python_version < '3.7'"
    ],
    data_files=[('share/doc/packages/bard/',
                 ['README.md'])],
    scripts=["scripts/bard"],
    license="GPL-3.0-only AND MIT",
    ext_modules=[bard_ext, bard_audiofile],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Multimedia :: Sound/Audio",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
)
