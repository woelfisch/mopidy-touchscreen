from __future__ import unicode_literals

import re

from setuptools import find_packages, setup


def get_version(filename):
    with open(filename) as fh:
        metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", fh.read()))
        return metadata['version']


setup(
    name='Mopidy-Touchscreen',
    version=get_version('mopidy_touchscreen/__init__.py'),
    url='https://github.com/woelfisch/mopidy-touchscreen',
    license='Apache License, Version 2.0',
    author='9and3r <9and3r@gmail.com>, woelfisch <woelfisch@gmail.com>',
    description='Mopidy extension to show info on a display and control from it',
    long_description=open('README.rst').read(),
    packages=find_packages(exclude=['tests', 'tests.*']),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'setuptools',
        'Mopidy >= 3.2',
        'Pykka >= 3.0',
        'musicbrainzngs >= 0.7.1',
        'pygame >= 2.1'
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose',
        'mock >= 1.0',
    ],
    entry_points={
        'mopidy.ext': [
            'touchscreen = mopidy_touchscreen:Extension',
        ],
    },
    classifiers=[
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
)
