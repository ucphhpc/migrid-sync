#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# setup.py - Setup for python luste quota
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

from setuptools import setup, Extension

from pylustrequota import version_string, short_name, project_team, \
    project_email, short_desc, long_desc, project_url, download_url, \
    license_name, project_class, project_keywords, versioned_requires, \
    project_requires, project_extras, project_platforms, maintainer_team, \
    maintainer_email

setup(
    name=short_name,
    version=version_string,
    description=short_desc,
    long_description=long_desc,
    author=project_team,
    author_email=project_email,
    maintainer=maintainer_team,
    maintainer_email=maintainer_email,
    url=project_url,
    download_url=download_url,
    license=license_name,
    classifiers=project_class,
    keywords=project_keywords,
    platforms=project_platforms,
    install_requires=versioned_requires,
    requires=project_requires,
    extras_require=project_extras,
    scripts=['bin/miglustrequota.py',
             ],
    packages=['pylustrequota'],
    package_dir={'pylustrequota': 'pylustrequota',
                 },
    package_data={},
    ext_modules=[
        Extension('pylustrequota.lfs',
                  include_dirs=['/usr/include',
                                '/usr/include/python3',
                                'lustre-release/libcfs/include',
                                'lustre-release/lustre/include',
                                'lustre-release/lustre/include/uapi',
                                'lustre-release/lnet/include/uapi',
                                'lustre-release/lustre/utils',
                                ],
                  library_dirs=[],
                  libraries=[],
                  sources=['pylustrequota/lfs.c',
                           'lustre-release/lustre/utils/lfs_project.c'],
                  extra_objects=[
                      'lustre-release/lustre/utils/.libs/liblustreapi.a'],
                  define_macros=[('_DEBUG', 0)],
                  ),
    ]
)
