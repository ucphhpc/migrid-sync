#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# editing - [insert a few words of module description on this line]
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

"""This module contains general functions used for the online
file editor.
"""

import os
import time

# Edit lock functions


def get_edit_lock_suffix():
    return '.editor_lock__'


def get_edit_lock_default_timeout():
    """Allow locking files for 600 seconds i.e. 10 minutes."""

    return 600


def acquire_edit_lock(real_path, cert_name_no_spaces):
    """Try to lock file in real_path for exclusive editing. On success the
    file is locked and cert_name_no_spaces is returned along with the
    default timeout in seconds. In case someone else actively holds the lock,
    the corresponding cert_name_no_spaces is returned along with the
    remaining time in seconds before the current lock will expire.
    If the file is already locked by the requester the lock is updated in order
    to reset the timeout. Stale locks are simply removed before the check.
    Please note that locks don't prevent users from seeing the last saved
    version of the file, only from truncating any concurrent changes.
    """

    default_timeout = get_edit_lock_default_timeout()
    take_lock = False
    lock_path = real_path + get_edit_lock_suffix()
    info_path = lock_path + os.sep + 'info'

    # We need atomic operation in locking - check for file or create followed by
    # lock won't do! mkdir is atomic, so it can work as a lock.

    try:
        os.makedirs(lock_path)
        lock_exists = False
    except OSError, ose:

        # lock dir exists - previously locked

        lock_exists = True

    now = time.mktime(time.gmtime())
    if lock_exists:

        # Read lock info - any error here means an invalid lock -> truncate

        try:
            info_fd = open(info_path, 'r+')
            info_lines = info_fd.readlines()
            info_fd.close()
            owner = info_lines[0].strip()
            timestamp = float(info_lines[1].strip())
            time_left = default_timeout - (now - timestamp)
        except Exception, err:
            print 'Error: %s - taking broken lock' % err
            owner = cert_name_no_spaces
            time_left = default_timeout
            take_lock = True

        if owner == cert_name_no_spaces or time_left < 0:
            take_lock = True
    else:
        take_lock = True

    if take_lock:
        owner = cert_name_no_spaces
        time_left = default_timeout

        # Truncate info file

        try:
            info_fd = open(info_path, 'w')
            info_fd.write('''%s
%f
''' % (cert_name_no_spaces, now))
            info_fd.close()
        except Exception, err:
            print 'Error opening or writing to %s, (%s)' % (info_path,
                    err)

    return (owner, time_left)


def got_edit_lock(real_path, cert_name_no_spaces):
    """Check that caller actually acquired the required file editing lock. 
    """

    lock_path = real_path + get_edit_lock_suffix()
    info_path = lock_path + os.sep + 'info'

    # We need atomic operation in locking - check for file or create followed by
    # lock won't do! mkdir is atomic, so it can work as a lock.

    try:
        os.mkdir(lock_path)

        # lock didn't exist - clean up and fail

        os.rmdir(lock_path)
        return False
    except OSError, ose:

        # lock dir exists - previously locked

        pass

    # Read lock info - any error here means an invalid lock

    try:
        info_fd = open(info_path, 'r+')
        info_lines = info_fd.readlines()
        info_fd.close()
        now = time.mktime(time.gmtime())
        owner = info_lines[0].strip()
        timestamp = float(info_lines[1].strip())
        time_left = get_edit_lock_default_timeout() - (now - timestamp)
    except Exception, err:
        print 'Error: %s - not accepting invalid lock' % err
        return False

    if owner != cert_name_no_spaces:
        print "Error: You don't have the lock for %s - %s does"\
             % (real_path, owner)
        return False
    elif time_left < 0:

        print "Error: You don't have the lock for %s any longer - time out %f seconds ago"\
             % (real_path, -time_left)
        return False
    else:
        return True


def release_edit_lock(real_path, cert_name_no_spaces):
    """Try to release an acquired file editing lock. Check that owner
    matches release caller.
    """

    if not got_edit_lock(real_path, cert_name_no_spaces):
        return False

    # We need atomic operation in locking - remove info file followed by
    # rmdir won't do! rename is atomic, so it can work as removal of lock.
    # create unique dir in tmp to avoid clashes and manual clean up on errors

    lock_path = real_path + get_edit_lock_suffix()
    stale_lock_path = lock_path + 'stale__'
    stale_info_path = stale_lock_path + os.sep + 'info'
    try:
        os.rename(lock_path, stale_lock_path)
        os.remove(stale_info_path)
        os.rmdir(stale_lock_path)
    except OSError, ose:

        # rename failed - previously locked

        print 'Error: renaming and removing lock dir: %s' % ose
        return False
    return True


