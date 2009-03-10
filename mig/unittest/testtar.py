#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# testtar - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""This module tests the server IO functions through the tarfile framework."""

import sys
import tarfile


def run_test(class_name):
    file_class = eval(class_name)

    local_path = 'input.txt'
    tar_path = 'input.tar'

    print '-locally opening file %s' % local_path
    fd = open(local_path, 'w')

    print '-writing lines to local file'
    lines = ['This is a test!', 'This is another test!\n',
             'This is a third test!\n', '..and a fourth!\n']
    fd.writelines(lines)
    fd.flush()
    print '-closing local file %s' % local_path
    fd.close()

    print '-opening tar file %s in write mode' % tar_path
    tar_fd = file_class(tar_path, 'w')
    print '-locking for write'
    tar_fd.lock(LOCK_EX)
    print '-accessing tar archive as TarFile'
    archive = tarfile.TarFile(tar_path, 'w', tar_fd)
    print '-add %s to tar archive %s' % (local_path, archive)
    archive.add(local_path)
    print '-closing TarFile'
    archive.close()
    print '-unlocking tar file'
    tar_fd.unlock()
    print '-closing tar file %s' % tar_path
    tar_fd.close()

    print '-opening tar file %s in read mode' % tar_path
    tar_fd = file_class(tar_path, 'r')
    print '-locking for read'
    tar_fd.lock(LOCK_SH)
    print '-accessing tar archive as TarFile'
    archive = tarfile.TarFile(tar_path, 'r', tar_fd)
    print '-list contents of tar archive %s' % archive
    contents = archive.getnames()
    print contents
    print '-closing TarFile'
    archive.close()
    print '-unlocking tar file'
    tar_fd.unlock()
    print '-closing tar file %s' % tar_path
    tar_fd.close()


class_name = 'LocalFile'
if len(sys.argv) > 1:
    class_name = sys.argv[1]

# import selected class

eval(compile('from %s import %s, LOCK_SH, LOCK_EX'
      % (class_name.lower(), class_name), '', 'single'))

# now test it

run_test(class_name)

