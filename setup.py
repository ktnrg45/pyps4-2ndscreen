#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup for pyps4-homeassistant."""

from setuptools import setup, find_packages
import pyps4_homeassistant.const as pyps4_const

MIN_PY_VERSION = '.'.join(map(str, pyps4_const.REQUIRED_PYTHON_VER))

REQUIRES = [
    'construct>=2.9.45',
    'pycryptodomex>=3.7.2',
]

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
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

setup(name=pyps4_const.__name__,
      version=pyps4_const.__version__,
      description='PS4 Python Library for Home Assistant',
      long_description=readme,
      author='ktnrg45',
      author_email='ktnrg45@gmail.com',
      packages=find_packages(),
      url='https://github.com/ktnrg45/pyps4-homeassistant',
      license='LGPLv2+',
      classifiers=CLASSIFIERS,
      keywords='playstation sony ps4',
      install_requires=REQUIRES,
      python_requires='>={}'.format(MIN_PY_VERSION),
      test_suite='tests',
      include_package_data=True,
      )
