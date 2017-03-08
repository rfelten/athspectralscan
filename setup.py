#!/usr/bin/env python
#  -*- coding: utf-8 -*-
##
## This file is part of the athspectralscan project.
##
## Copyright (C) 2016-2017 Robert Felten - https://github.com/rfelten/
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
##

from setuptools import setup, find_packages
from codecs import open
from os import path


module = 'athspectralscan'

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='athspectralscan',
      version='0.2',
      description='TBA',
      url='https://github.com/rfelten/athspectralscan',
      author='Robert Felten',
      author_email='see github',
      license='GPLv3',
      packages=['athspectralscan'],
      long_description=long_description,
      #install_requires=['dep1', 'dep2'],
      zip_safe=False
      )
