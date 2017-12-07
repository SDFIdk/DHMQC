"""
Setup script for the kvadratnet module.
"""

import os
import subprocess
from setuptools import setup

import dhmqc

def readme():
    """
    Return a properly formatted readme text, if possible, that can be used
    as the long description for setuptools.setup.
    """
    # This will fail if pandoc is not in system path.
    #subprocess.call(['pandoc', 'readme.md', '--from', 'markdown', '--to', 'rst', '-s', '-o', 'readme.rst'])
    #with open('readme.rst') as f:
    #    readme = f.read()
    #os.remove('readme.rst')
    #return readme
    return "This is DHMQC. It's cool."

setup(
    name='DHMQC',
    version=dhmqc.__version__,
    description='Processing suite for the Danish Digital Elevation Model',
    long_description=readme(),
    classifiers=[
      'Development Status :: 4 - Beta',
      'Intended Audience :: Developers',
      'Intended Audience :: Science/Research',
      'License :: OSI Approved :: ISC License (ISCL)',
      'Topic :: Scientific/Engineering :: GIS',
      'Topic :: Utilities'
    ],
    entry_points = {
      'console_scripts': ['dhmqc=dhmqc.apps.main:main']
    },
    keywords='DHM pointcloud terrainmodel DTM DSM LiDAR',
    url='https://github.com/Kortforsyningen/DHMQC',
    author='SDFE',
    author_email='kreve@sdfe.dk',
    license='ISC',
    py_modules=['dhmqc', 'dhmqc.apps.main'],
    test_suite='nose.collector',
    tests_require=['nose']
)
