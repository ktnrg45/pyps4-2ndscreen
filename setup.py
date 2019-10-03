#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup for pyps4-2ndscreen."""

from setuptools import setup, find_packages
import pyps4_2ndscreen.__version__ as version

MIN_PY_VERSION = '.'.join(map(str, version.REQUIRED_PYTHON_VER))

REQUIRES = list(open('requirements.txt'))

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

with open('README.rst') as f:
    readme = f.read()

setup(name='pyps4_2ndscreen',
      version=version.__version__,
      description='PS4 2nd Screen Python Library',
      long_description=readme,
      long_description_content_type='text/markdown',
      author='ktnrg45',
      author_email='ktnrg45@gmail.com',
      packages=find_packages(),
      url='https://github.com/ktnrg45/pyps4-2ndscreen',
      license='LGPLv2+',
      classifiers=CLASSIFIERS,
      keywords='playstation sony ps4',
      install_requires=REQUIRES,
      python_requires='>={}'.format(MIN_PY_VERSION),
      test_suite='tests',
      include_package_data=True,
      entry_points={"console_scripts": ["pyps4-2ndscreen = pyps4_2ndscreen.__main__:cli"]}
      )
