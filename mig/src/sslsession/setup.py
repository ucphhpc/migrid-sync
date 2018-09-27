#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# setup.py - Setup for SSL session information
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

from distutils.core import setup, Extension
setup(name='sslsession',
      version='0.1',
      description='Module for extracting SSL session information',
      long_description='Module for extracting SSL session information',
      author='The MiG Project lead by Brian Vinter',
      author_email='NA',
      license='GPLv2',
      platforms=['Python 2.7'],
      url='https://sourceforge.net/projects/migrid/',
      ext_modules=[Extension('_sslsession',
                             ['_sslsession.c'],
                             include_dirs=['include'],
                             libraries=["ssl"]
                             )])
