#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# modernizeall - a simple helper to run python-modernize on all project code.
# Copyright (C) 2020  Jonas Bardino
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

"""Reformat all python source code to python 3 friendly format using the
python-modernize tool from
https://pypi.org/project/modernize/

A few manual tweaks are needed afterwards to avoid breakage.
"""

from __future__ import absolute_import
from __future__ import print_function

import mimetypes
import os
import subprocess
import sys

exclude_dirs = ['.svn', 'user-projects']

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: %s TARGET' % sys.argv[0])
        print('Run modernize on all python source code in TARGET and fix breakage')
        sys.exit(1)

    target = os.getcwd()
    if sys.argv[1:]:
        target = os.path.abspath(sys.argv[1])

    print('Modernizing python code in %s' % target)
    print('--- ignoring all %s dirs ---' % ', '.join(exclude_dirs))
    mime_helper = mimetypes.MimeTypes()
    modernize_base = ['python-modernize', '-w']
    # NOTE: fix import lines broken by modernize and leave Copyright line alone
    sed_rules = ['s/from .shared/from shared/g', 's/from . import /import /g']
    postprocess_base = ['sed', '-i'] + [';'.join(sed_rules)]
    for (root, dirs, files) in os.walk(target):
        for exclude in exclude_dirs:
            if exclude in dirs:
                dirs.remove(exclude)
        for name in files:
            path = os.path.normpath(os.path.join(root, name))
            rel_path = path.replace(target+os.sep, '')
            # Python source code either has .py or no extension
            # Detect based on mimetype or hashbang line for the latter.
            file_ext = os.path.splitext(path)[1]
            if not file_ext:
                mime_type = mime_helper.guess_type(path)[0]
                if mime_type is None:
                    with open(path, 'r') as src_fd:
                        if src_fd.readline().startswith('#!/usr/bin/python'):
                            mime_type = 'text/x-python'
                        else:
                            mime_type = 'unknown'

                if mime_type.find('x-python') == -1:
                    #print("DEBUG: skip non-python file in %s" % rel_path)
                    continue
            elif file_ext != '.py':
                #print("DEBUG: skip %s file in %s" % (file_ext, rel_path))
                continue

            print('Run modernize on python code in %s' % rel_path)
            #modernize_cmd = ['echo'] + modernize_base + [path]
            modernize_cmd = modernize_base + [path]
            modernize_retval = subprocess.call(modernize_cmd)
            if modernize_retval != 0:
                print("ERROR: failed to modernize %s" % rel_path)
                continue
            #postprocess_cmd = ['echo'] + postprocess_base + [path]
            postprocess_cmd = postprocess_base + [path]
            postprocess_retval = subprocess.call(postprocess_cmd)
            if postprocess_retval != 0:
                print("ERROR: failed to postprocess %s" % rel_path)
                continue

    print('Finished modernizing source code in %s' % target)
