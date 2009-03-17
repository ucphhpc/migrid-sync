#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# makerelease - a simple helper to create a MiG project code release.
# Copyright (C) 2009  Jonas Bardino
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

"""Pack relevant parts of the code in a versioned tarball"""

import os
import sys
import tarfile

if len(sys.argv) < 2:
    print 'Usage: %s VERSION TARGET' % sys.argv[0]
    print 'Make a release tarball of all code in TARGET and stamp it as VERSION'
    sys.exit(1)

version = sys.argv[1]
try:
    target = sys.argv[2]
except:
    target = os.getcwd()

exclude_dirs = ['.svn', 'user-projects']
archive_base = 'mig-%s' % version
tar_path = '%s.tgz' % archive_base

if '__main__' == __name__:
    print 'Creating release of %s in %s' % (target, tar_path)
    print '--- ignoring all %s dirs ---' % ', '.join(exclude_dirs)
    tar_ball = tarfile.open(tar_path, 'w:gz')
    for (root, dirs, files) in os.walk(target):
        for exclude in exclude_dirs:
            if exclude in dirs:
                dirs.remove(exclude)
        for name in files:
            if name == tar_path:
                continue
            path = os.path.normpath(os.path.join(root, name))
            rel_path = path.replace(os.path.dirname(target), '')
            archive_path = os.path.join(archive_base, rel_path)
            print 'Adding %s' % archive_path
            tar_ball.add(rel_path, archive_path, recursive=False)
    tar_ball.close()
    print 'Wrote release of %s in %s' % (target, tar_path)

