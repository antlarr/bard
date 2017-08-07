from setuptools import setup, Extension


module1 = Extension('bard_ext',
                    define_macros=[('MAJOR_VERSION', '1'),
                                   ('MINOR_VERSION', '0')],
                    include_dirs=['/usr/include/boost'],
                    libraries=['boost_python-py3'],
                    library_dirs=['/usr/lib'],
                    sources=['bard/bard_ext.cpp'],
                    extra_compile_args=['-std=c++1z'])

setup(
    # Application name:
    name="bard",

    # Version number (initial):
    version="0.1.0",

    # Application author details:
    author="Antonio Larrosa",
    author_email="larrosa@kde.org",

    # Packages
    packages=["bard"],

    # Include additional files into the package
    # include_package_data=True,

    # Details
    url="https://github.com/antlarr/bard",

    #
    # license="LICENSE.txt",
    description="Bard Music Manager - A database to manage your music, find duplicates and fix tags",

    # long_description=open("README.txt").read(),

    # Dependent packages (distributions)
    install_requires=[
        "pyacoustid",
        "mutagen",
        "Pillow",
    ],
    data_files=[('share/doc/packages/bard/', ['config/bard', 'README.md', 'LICENSE'])],
    scripts=["scripts/bard"],
    license="GPLv3",
    ext_modules=[module1]
)
