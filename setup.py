from setuptools import setup

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
    ],
    data_files=[('share/doc/packages/bard/', ['config/bard', 'README.md', 'LICENSE'])],
    scripts=["scripts/bard"],
    license="GPLv3",
)
