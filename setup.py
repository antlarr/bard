from setuptools import setup, Extension


bard_ext = Extension('bard_ext',
                     define_macros=[('MAJOR_VERSION', '1'),
                                    ('MINOR_VERSION', '0'),
                                    ('_GLIBCXX_PARALLEL', None)],
                     include_dirs=['/usr/include/boost'],
                     libraries=['boost_python-py3', 'gomp'],
                     library_dirs=['/usr/lib'],
                     sources=['bard/bard_ext.cpp'],
                     extra_compile_args=['-std=gnu++17', '-fopenmp', '-Ofast',
                                         '-march=native', '-mtune=native',
                                         '-funroll-loops'])


bard_audiofile = Extension('bard_audiofile',
                           define_macros=[('MAJOR_VERSION', '1'),
                                          ('MINOR_VERSION', '0'),
                                          ('_GLIBCXX_PARALLEL', None)],
                           include_dirs=['/usr/include/boost',
                                         '/usr/include/ffmpeg'],
                           libraries=['boost_python-py3', 'avcodec',
                                      'avformat', 'avutil', 'swresample'],
                           library_dirs=['/usr/lib'],
                           sources=['bard/audiofile/audiofile.cpp',
                                    'bard/audiofile/bufferaviocontext.cpp',
                                    'bard/audiofile/bufferdecodeoutput.cpp',
                                    'bard/audiofile/decodeoutput.cpp',
                                    'bard/audiofile/filedecodeoutput.cpp',
                                    'bard/audiofile/referencedata.cpp',
                                    'bard/audiofile/pyaudiofile.cpp'],
                           extra_compile_args=['-std=gnu++17', '-Ofast',
                                               '-march=native',
                                               '-mtune=native',
                                               '-funroll-loops'])
setup(
    name="bard",
    version="0.3.0",
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
    install_requires=[
        "pyacoustid",
        "mutagen",
        "Pillow",
        "pydub",
        "numpy",
        "dbus-python",
        "SQLAlchemy",
        "Werkzeug",
        "Flask",
        "Flask-Cors",
        "Flask-Login",
        "Jinja2",
        "bcrypt"
    ],
    data_files=[('share/doc/packages/bard/',
                 ['config/bard', 'README.md'])],
    scripts=["scripts/bard"],
    license="GPL-3.0-only AND MIT",
    ext_modules=[bard_ext, bard_audiofile],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Multimedia :: Sound/Audio",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
)
