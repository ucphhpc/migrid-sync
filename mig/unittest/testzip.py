#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# testzip - test server zip module
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""This module tests the server IO functions through the zipfile framework."""

import sys
import zipfile

# NOTE: dummy init before inline compile in code to make pylint happy
LOCK_EX = LOCK_SH = None


def run_test(class_name):
    file_class = eval(class_name)

    local_path = 'input.txt'
    zip_path = 'input.zip'

    print '-locally opening file %s' % local_path
    fd = open(local_path, 'w')

    print '-writing lines to local file'
    lines = ['This is a test!', 'This is another test!\n',
             'This is a third test!\n', '..and a fourth!\n']
    fd.writelines(lines)
    fd.flush()
    print '-closing local file %s' % local_path
    fd.close()

    print '-opening zip file %s in write mode' % zip_path
    fd = file_class(zip_path, 'w')
    print '-locking for write'
    fd.lock(LOCK_EX)
    print '-accessing zip archive as ZipFile'
    archive = zipfile.ZipFile(fd, 'w')
    print '-add %s to zip archive %s' % (local_path, archive)
    archive.write(local_path)
    print '-closing ZipFile'
    archive.close()
    print '-unlocking zip file'
    fd.unlock()
    print '-closing zip file %s' % zip_path
    fd.close()

    print '-opening zip file %s in read mode' % zip_path
    fd = file_class(zip_path, 'r')
    print '-locking for read'
    fd.lock(LOCK_SH)
    print '-accessing zip archive as ZipFile'
    archive = zipfile.ZipFile(fd, 'r')
    print '-test integrity of zip archive %s' % archive
    archive.testzip()
    print '-list contents of zip archive %s' % archive
    contents = archive.namelist()
    print contents
    print '-closing ZipFile'
    archive.close()
    print '-unlocking zip file'
    fd.unlock()
    print '-closing zip file %s' % zip_path
    fd.close()


class_name = 'LocalFile'
if len(sys.argv) > 1:
    class_name = sys.argv[1]

# import selected class

eval(compile('from %s import %s, LOCK_SH, LOCK_EX'
             % (class_name.lower(), class_name), '', 'single'))

# now test it

run_test(class_name)
