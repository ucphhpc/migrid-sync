#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# unit - some simple unit tests against migfs
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Unit test migfs"""
from __future__ import print_function

import os
import subprocess
import sys
import traceback

from migfs import default_block_size

debug_mode = False


def debug(line):
    if debug_mode:
        print('DEBUG: %s' % line)


def show_diff(result, expected):
    """Shared function for displaying difference between result and expected"""

    max_len = 32
    part_len = max_len / 2
    if len(result) > max_len:
        first = result[:part_len] + ' .. ' + result[-part_len:]
    else:
        first = result
    if len(expected) > max_len:
        second = expected[:part_len] + ' .. ' + expected[-part_len:]
    else:
        second = expected
    print("\t'%s' != '%s'\n\t(len: %d vs. %d)" % (first, second,
            len(result), len(expected)))


def clean_test(test_dir):
    """Clean up everything in test_dir"""

    name = 'clean up'
    print('Starting %s test' % name)
    for (root, dirs, files) in os.walk(test_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(test_dir)
    success = not os.path.exists(test_dir)
    print('Got expected result:\t\t%s' % success)


def prepare_test(test_path):
    """Create and manipulate some subdirs including one for test_path"""

    name = 'create parent dir'
    print('Starting %s test' % name)
    target = os.path.dirname(test_path)
    try:
        os.makedirs(target)
    except Exception as exc:
        print('\tFailed to %s (%s): %s' % (name, target, exc))
    success = os.path.isdir(target)
    print('Got expected result:\t\t%s' % success)
    name = 'create sub dir'
    print('Starting %s test' % name)
    target = os.path.join(target, 'sub')
    try:
        os.mkdir(target)
    except Exception as exc:
        print('\tFailed to %s (%s): %s' % (name, target, exc))
    success = os.path.isdir(target)
    print('Got expected result:\t\t%s' % success)
    name = 'move sub dir'
    print('Starting %s test' % name)
    tmp_path = target + '.tmp'
    try:
        os.rename(target, tmp_path)
    except Exception as exc:
        print('\tFailed to %s (%s): %s' % (name, target, exc))
    success = os.path.isdir(tmp_path) and not os.path.exists(target)
    print('Got expected result:\t\t%s' % success)
    name = 'remove sub dir'
    print('Starting %s test' % name)
    target = tmp_path
    try:
        os.rmdir(target)
    except Exception as exc:
        print('\tFailed to %s (%s): %s' % (name, target, exc))
    success = not os.path.exists(target)
    print('Got expected result:\t\t%s' % success)


def write_test(test_path):
    """Write test using test_path"""

    data_len = 4
    tests = [('create file', ''), ('short write', '123'), ('long write'
             , '123' * default_block_size)]
    for (name, val) in tests:
        print('Starting %s test' % name)
        fd = open(test_path, 'w')
        debug('opened %s' % test_path)
        if val:
            fd.write(val)
            debug('wrote %s ...' % val[:data_len])
        fd.close()
        debug('closed %s' % test_path)
        fd = open(test_path, 'r')
        debug('opened %s' % test_path)
        result = fd.read()
        debug('read %s ... from %s' % (result[:data_len], test_path))
        fd.close()
        debug('closed %s' % test_path)
        success = result == val
        print('Got expected result:\t\t%s' % success)
        if not success:
            show_diff(val, result)


def append_test(test_path):
    """Append test using test_path"""

    tests = [('short append', '123'), ('long append', '123'
              * default_block_size)]
    prefix = 'abc'
    for (name, val) in tests:
        print('Starting %s test' % name)
        fd = open(test_path, 'w')
        fd.write(prefix)
        fd.close()
        fd = open(test_path, 'a')
        if val:
            fd.write(val)
        fd.close()
        fd = open(test_path, 'r')
        result = fd.read()
        fd.close()
        success = result[len(prefix):] == val
        print('Got expected result:\t\t%s' % success)
        if not success:
            show_diff(val, result)


def modify_test(test_path):
    """Modify test using test_path"""

    original = 'ABCD' * default_block_size
    short_string = '123'
    long_string = '1234567890'
    tests = [
        ('short prefix modify', short_string, 0),
        ('short modify', short_string, default_block_size + 3),
        ('short suffix modify', short_string, len(original)
          - len(short_string)),
        ('long prefix modify', long_string, 0),
        ('long modify', long_string * default_block_size,
         default_block_size + 3),
        ('long suffix modify', long_string, len(original)
          - len(long_string)),
        ]

    for (name, val, modify_index) in tests:
        print('Starting %s test' % name)
        fd = open(test_path, 'w')
        fd.write(original)
        fd.close()
        fd = open(test_path, 'r+')
        fd.seek(modify_index)
        if val:
            fd.write(val)
        fd.close()
        fd = open(test_path, 'r')
        result = fd.read()
        fd.close()
        expected_result = original[:modify_index] + val\
             + original[modify_index + len(val):]
        success = result == expected_result
        print('Got expected result:\t\t%s' % success)
        if not success:
            show_diff(val, result)


# ## Main ###

mount_point = 'mig-home'

# do_mount = False

do_mount = True

# debug_mode = True

if len(sys.argv) > 1:
    mount_point = sys.argv[1]
test_dir = os.path.join(mount_point, 'migfs-test')
test_path = os.path.join(test_dir, 'migfs-test', 'child', 'grandchild',
                         'testfile.txt')
if not os.path.isdir(mount_point):
    print('creating missing mount point %s' % mount_point)
    try:
        os.mkdir(mount_point)
    except OSError as ose:
        print('Failed to create missing mount point %s: %s'\
             % (mount_point, ose))
        sys.exit(1)

print('--- Starting unit tests ---')
print()
if do_mount:
    subprocess.call(['./mount.migfs', 'none', mount_point])
try:
    prepare_test(test_path)
    write_test(test_path)
    append_test(test_path)
    modify_test(test_path)
    clean_test(test_dir)
except Exception as err:
    print('Error during test: %s' % err)
    print('DEBUG: %s' % traceback.format_exc())

print()
print('--- End of unit tests ---')

if do_mount:
    subprocess.call(['fusermount', '-u', '-z', mount_point])
