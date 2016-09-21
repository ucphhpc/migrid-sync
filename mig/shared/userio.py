#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# userio - wrappers to keep user file I/O in a single replaceable module
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

"""All I/O operations on behalf of users - needed for e.g. trash/undelete"""

import os
import shutil
import sys
import tempfile 
import time

from shared.base import invisible_file
from shared.defaults import trash_folder
from shared.vgrid import in_vgrid_share, in_vgrid_priv_web, in_vgrid_pub_web

ACTIONS = (CREATED, MODIFIED, MOVED, DELETED) = \
          "created", "modified", "moved", "deleted"

def prepare_changes(configuration, changeset, action, target_list):
    """Prepare events file to match any future user I/O action. Useful for
    building the event set during recursive traversal and then only commit the
    changes after successful e.g. move or copy.
    The target argument may be a list of single path entries or (src, dst)
    tuples in case of a move. The action argument may take any of the change
    values CREATED, MODIFIED, MOVED and DELETED defined here.
    The changeset argument is used to mark the action as a part of a bigger
    operation, like e.g. a recursive copy or move.
    Returns a handle to a temporary file with the saved events.
    """
    _logger = configuration.logger
    _logger.debug("prepare %s %s event on %s" % (changeset, action, target_list))
    # Make sure events dir exists
    try:
        os.makedirs(configuration.events_home)
    except:
        pass
    tmp_path = os.path.join(configuration.events_home, ".%s-%s-pending" % \
                            (configuration.mig_server_id, changeset))

    if os.path.exists(tmp_path):
        mode = "a"
    else:
        mode = "w"
    try:
        cfd = open(tmp_path, mode)
        for target in target_list:
            cfd.write("%s:%s\n" % (action, target))
        cfd.close()
        return tmp_path
    except Exception, err:
        _logger.error("Failed to save event: %s %s %s: %s" % (target, action,
                                                              changeset, err))
        return None

def commit_changes(configuration, changeset, events_path):
    """Actually commit prepared events in events_path upon completion of any
    user I/O action. Used to get consistent event handling no matter where events
    come from.
    The events_path argument should point to a temporary events file made by
    prepare_changes.
    The changeset argument is used for the naming  of the resulting committed
    events file.
    """
    _logger = configuration.logger
    _logger.debug("commit %s events in %s" % (changeset, events_path))
    changeset_path = os.path.join(configuration.events_home, "%s-%s" % \
                                  (configuration.mig_server_id, changeset))
    try:
        os.rename(events_path, changeset_path)
        return changeset_path
    except Exception, err:
        _logger.error("Failed to commit %s events in %s: %s" % \
                      (changeset, events_path, err))
        return None

def on_changes(configuration, changeset, action, target_list):
    """Wrapper to prepare and commit an events file upon completion of any user
    I/O action. Used to get consistent event handling no matter where events
    come from.
    The target argument may be a single path or a (src, dst) tuple
    in case of a move. The action argument may take any of the change values
    CREATED, MODIFIED, MOVED and DELETED defined here.
    The optional changeset argument can be used to mark the change as part of a
    bigger operation like e.g. a recursive copy or move.
    """
    tmp_path = prepare_changes(configuration, changeset, action, target_list)
    if tmp_path is not None:
        return commit_changes(configuration, changeset, tmp_path)
    else:
        return None

def _wrap_walk(configuration, path, topdown=True):
    """Return usual os.walk result if path is a directory and fake a simple
    walk iterator if it is a plain file."""
    if os.path.isdir(path):
        return os.walk(path, topdown=topdown)
    else:
        return (os.path.dirname(path), [], [os.path.basename(path)]) 

def get_home_location(configuration, path):
    """Find the proper home folder for path. I.e. the corresponding user home
    or vgrid share or web home dir.
    """
    real_path = os.path.realpath(path)
    if real_path.startswith(configuration.user_home):
        suffix = real_path.replace(configuration.user_home, '').lstrip(os.sep)
        suffix = suffix.split(os.sep, 1)[0]        
        return os.path.join(configuration.user_home, suffix)
    elif real_path.startswith(configuration.vgrid_files_home):
        suffix = in_vgrid_share(configuration, real_path)
        return os.path.join(configuration.vgrid_files_home, suffix)
    elif real_path.startswith(configuration.vgrid_private_base):
        suffix = in_vgrid_priv_web(configuration, real_path)
        return os.path.join(configuration.vgrid_private_base, suffix)
    elif real_path.startswith(configuration.vgrid_public_base):
        suffix = in_vgrid_pub_web(configuration, real_path)
        return os.path.join(configuration.vgrid_public_base, suffix)
    else:
        return None

def get_trash_location(configuration, path):
    """Find the proper trash folder for path. I.e. the one in the root of the
    corresponding user home or vgrid share or web home dir.
    """
    trash_base = get_home_location(configuration, path)
    if trash_base is not None:
        trash_base = os.path.join(trash_base, trash_folder)
    return trash_base

def _prepare_recursive_op(configuration, changeset, action, path, operation):
    """Helper to walk and prepare events for a recursive action on path"""
    _logger = configuration.logger
    _logger.debug('%s user path: %s' % (operation, path))
    for (root, dirs, files) in _wrap_walk(configuration, path, topdown=False):
        if files:
            target_list = [os.path.join(root, name) for name in files]
            _logger.debug('%s user sub files: %s' % (operation, target_list))
            prepare_changes(configuration, changeset, action, target_list)
        if dirs:
            target_list = [os.path.join(root, name) for name in dirs]
            _logger.debug('%s user sub dirs: %s' % (operation, target_list))
            prepare_changes(configuration, changeset, action, target_list)
    tmp_path = prepare_changes(configuration, changeset, action, [path])
    return tmp_path

def delete_path(configuration, path):
    """Wrapper to handle direct deletion of user file in path. This version
    skips the user-friendly intermediate step of really just moving path to
    the trash folder in the user home or in the vgrid-special home, depending
    on the location of path.
    Automatically applies recursively for directories.
    """
    _logger = configuration.logger
    if not path:
        _logger.error('not allowed to delete without path')
        return False
    elif invisible_file(path):
        _logger.error('not allowed to delete invisible: %s' % path)
        return False
    elif os.path.islink(path):
        _logger.error('not allowed to delete link: %s' % path)
        return False
    elif not os.path.exists(path):
        _logger.error('no such file or directory %s' % path)
        return False

    result = True
    _logger.info('deleting user path: %s' % path)
    changeset = "delete-%f" % time.time()
    tmp_path = _prepare_recursive_op(configuration, changeset, DELETED, path,
                                     'delete')
    try:
        _logger.info('actually deleting user path %s' % path)
        shutil.rmtree(path)
        commit_changes(configuration, changeset, tmp_path)
    except Exception, err:
        _logger.error('could not delete dir: %s (%s)' % (path, err))
    return result

def remove_path(configuration, path):
    """Wrapper to handle removal of user file in path. This version uses the
    default behaviour of really just moving path to the trash folder in the
    user home or in the vgrid-special home, depending on the location of path.
    Automatically applies recursively for directories.
    """
    _logger = configuration.logger
    if not path:
        _logger.error('not allowed to remove without path')
        return False
    elif invisible_file(path):
        _logger.error('not allowed to remove invisible: %s' % path)
        return False
    elif os.path.islink(path):
        _logger.error('not allowed to remove link: %s' % path)
        return False
    elif not os.path.exists(path):
        _logger.error('no such file or directory %s' % path)
        return False

    home_base = get_home_location(configuration, path)
    trash_base = get_trash_location(configuration, path)
    if trash_base is None:
        _logger.error('no suitable trash folder for: %s' % path)
        return False
    else:
        # Make sure trash folder exists
        try:
            os.makedirs(trash_base)
        except:
            pass

    result = True
    _logger.info('remove user path: %s' % path)
    changeset = "remove-%f" % time.time()
    tmp_path = _prepare_recursive_op(configuration, changeset, DELETED, path,
                                     'remove')
    try:
        # Find free destination dir and remove last if necessary
        for suffix in [''] + ['.%d' % i for i in range(2, 100)]:
            trash_path = path.replace(home_base, trash_base) + suffix 
            if not os.path.exists(trash_path):
                break
        if os.path.exists(trash_path):
            shutil.rmtree(trash_path)
        _logger.info('actually moving user path %s to %s' % (path, trash_path))
        shutil.move(path, trash_path)
        commit_changes(configuration, changeset, tmp_path)
    except Exception, err:
        _logger.error('could not remove %s %s' % (path, err))
        result = False
    return result

def touch(configuration, path, timestamp=None):
    """Create or update timestamp for path"""
    _logger = configuration.logger
    changeset = "touch-%f" % time.time()
    try:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            filehandle = open(path, 'r+w')
            i = filehandle.read(1)
            filehandle.seek(0, 0)
            filehandle.write(i)
            filehandle.close()
        else:
            open(path, 'w').close()
            on_changes(configuration, changeset, CREATED, [path])

        if timestamp != None:

            # set timestamp to supplied value

            os.utime(path, (timestamp, timestamp))
            on_changes(configuration, changeset, MODIFIED, [path])
    except Exception, err:
        _logger.error("could not touch file: '%s' (%s)" % (path, err))
        return False


if __name__ == "__main__":
    from shared.base import client_id_dir
    from shared.conf import get_configuration_object
    print "Unit testing user I/O"
    client_id = "/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk"
    if sys.argv[1:]:
        client_id = sys.argv[1]
    print "Using client dir for %s for tests" % client_id
    client_dir = client_id_dir(client_id)
    configuration = get_configuration_object()
    tmp_dir = "userio-testdir"
    real_tmp = os.path.join(configuration.user_home, client_dir, tmp_dir)
    for del_func in (delete_path, remove_path):
        for sub_path in ("test1.txt", "sub1/test2.txt", "sub2/sub2.2/test4.txt"):
            real_path = os.path.join(real_tmp, sub_path)
            real_dir = os.path.dirname(real_path)
            try:
                os.makedirs(real_dir)
            except:
                pass
            fd = open(real_path, "w")
            fd.write('\n'.join(["sample line %d" % i for i in range(42)]))
            fd.close()
            print "Wrote tmp file %s" % real_path
        print "Run %s on %s" % (del_func, real_tmp)
        del_func(configuration, real_tmp)
