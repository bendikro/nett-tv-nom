#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup

import nett_tv_nom

setup(name='nett-tv-nom',
      version=nett_tv_nom.__version__,
      description="A simple python script for playing video from nrk nett-tv using media players such as vlc.",
      long_description="A simple python script for playing video from nrk nett-tv using media players such as vlc.",
      url='https://github.com/bendikro/nett-tv-nom',
      license="BSD",
      py_modules=["nett_tv_nom"],
      install_requires=[
          'termcolor',
          'lxml',
      ],
      entry_points = {'console_scripts': ['nett_tv_nom = nett_tv_nom:main']},
      classifiers=[
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: BSD License',
          'Natural Language :: English',
          'Operating System :: POSIX'
        ],
      )
