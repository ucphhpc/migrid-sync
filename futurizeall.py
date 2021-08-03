#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# futurizeall - a simple helper to run futurize on all project code.
# Copyright (C) 2020-2021  Jonas Bardino
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
futurize tool available from
http://python-future.org/index.html

A few manual tweaks are needed afterwards to avoid breakage.
"""

from __future__ import absolute_import
from __future__ import print_function

import mimetypes
import os
import re
import subprocess
import sys
import time

exclude_dirs = ['state', 'user-projects', 'doc-src',
                'MiG-certificates', 'seafile', 'assets', 'images', 'previews']
exclude_patterns = ['generated-confs_*']

# Tweak to run stage 1 or stage2 as described on
# http://python-future.org/automatic_conversion.html
safe_only = True
# Whether to run any automated fixes after futurize - none available so far
enable_postprocessing = False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: %s TARGET [ONLYSAFE]' % sys.argv[0])
        print('Run futurize on all python source code in TARGET and fix breakage')
        print('The optional ONLYSAFE argument can be used to override the ')
        print('default of only applying supposedly safe transformations.')
        sys.exit(1)

    target = os.getcwd()
    if sys.argv[1:]:
        target = os.path.abspath(sys.argv[1])
    if sys.argv[2:]:
        safe_only = (sys.argv[2].lower() in ('true', 'yes'))

    print('Futurizing python code in %s' % target)
    print('--- ignoring all %s dirs ---' % ', '.join(exclude_dirs))
    print('--- ignoring all %s patterns ---' % ', '.join(exclude_patterns))
    mime_helper = mimetypes.MimeTypes()
    futurize_base = ['futurize', '-n', '-w']
    if safe_only:
        futurize_base += ['--stage1']
    else:
        futurize_base += ['--stage2']

    # TODO: use sed tool to fix any lines broken by futurize / 2to3
    sed_rules = ['']
    postprocess_base = ['sed', '-i'] + [';'.join(sed_rules)]
    # Mimic walk for single file target
    if os.path.isfile(target):
        root, filename = os.path.split(target)
        walk_helper = [(root, [], [filename])]
    else:
        walk_helper = os.walk(target)
    for (root, dirs, files) in walk_helper:
        timestamp = time.time()
        # Skip all dot-dirs and explicit removes
        for exclude in exclude_dirs + [i for i in dirs if i.startswith('.')]:
            if exclude in dirs:
                dirs.remove(exclude)
        for pattern in exclude_patterns:
            for exclude in [i for i in dirs if re.match(pattern, i)]:
                dirs.remove(exclude)
        # Skip all dot-files
        for name in [i for i in files if not i.startswith('.')]:
            path = os.path.normpath(os.path.join(root, name))
            if os.path.islink(path):
                #print("DEBUG: skip symlink in %s" % path)
                continue
            rel_path = path.replace(target+os.sep, '')
            # Python source code either has .py or no extension
            # Detect based on mimetype or hashbang line for the latter.
            file_ext = os.path.splitext(path)[1]
            if not file_ext:
                #print('DEBUG: detect mime type on %s' % path)
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

            print('Run futurize on python code in %s' % rel_path)
            #futurize_cmd = ['echo'] + futurize_base + [path]
            futurize_cmd = futurize_base + [path]
            futurize_retval = subprocess.call(futurize_cmd)
            if futurize_retval != 0:
                print("ERROR: failed to futurize %s" % rel_path)
                continue
            # Nothing to fix if import fix is disabled
            if not enable_postprocessing:
                continue
            # Skip postprocessing unless file actually changed
            if timestamp - os.path.getmtime(path) > 0:
                continue
            #postprocess_cmd = ['echo'] + postprocess_base + [path]
            postprocess_cmd = postprocess_base + [path]
            postprocess_retval = subprocess.call(postprocess_cmd)
            if postprocess_retval != 0:
                print("ERROR: failed to postprocess %s" % rel_path)
                continue

    print('Finished futurizing source code in %s' % target)
