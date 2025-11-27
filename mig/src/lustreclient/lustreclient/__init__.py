#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# __init__ - lustre client python extension
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#
"""This package provide lustre client functionality"""

__dummy = True

# above line is only to make python tidy behave and not
# move module doc string inside header

# All sub modules to load in case of 'from X import *'

__all__ = []
	
# Collect all package information here for easy use from scripts and helpers

package_name = 'Lustre Client Python extension'
short_name = 'lustreclient'

# IMPORTANT: Please keep version in sync with doc-src/README.t2t

version_tuple = (0, 0, 1)
version_suffix = ''
version_string = '.'.join([str(i) for i in version_tuple]) + version_suffix
package_version = '%s %s' % (package_name, version_string)
project_team = 'The MiG Project by the Science HPC Center at UCPH'
project_email = 'info@migrid.org'
maintainer_team = 'The migrid.org maintainers'
maintainer_email = 'info@migrid.org'
project_url = 'https://github.com/ucphhpc/migrid-sync'
download_url = 'https://github.com/ucphhpc/migrid-sync/releases'
license_name = 'GNU GPL v2'
short_desc = \
    'Lustre client python extension'
long_desc = \
    """Lustre client python extension:
Documentation: https://github.com/ucphhpc/migrid-sync
"""
project_class = [
    'Development Status :: 1 - Beta',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
    'Topic :: Software Development :: Debuggers',
    ]
project_keywords = [
    'Python',
    'Python C extensions',
    'lustre',
    ]

# Requirements

full_requires = []
versioned_requires = []
project_requires = []

# Optional packages required for additional functionality (for extras_require)

project_extras = {}
package_provides = short_name
project_platforms = ['All']
