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

# NOTE: Use faster scandir if available
try:
    from scandir import walk
except ImportError:
    from os import walk
import os
import shutil
import sys
import time

from shared.base import invisible_path
from shared.defaults import trash_destdir, trash_linkname
from shared.vgrid import in_vgrid_share, in_vgrid_priv_web, in_vgrid_pub_web

ACTIONS = (CREATE, MODIFY, MOVE, DELETE) = "create", "modify", "move", "delete"

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

def get_trash_location(configuration, path, visible_link=False):
    """Find the proper trash folder for path. I.e. the one in the root of the
    corresponding user home or vgrid share or web home dir.
    If the optional visible_link argument is set the result is the path to the
    trash symlink instead.
    NOTE: we use this construct to prevent users from inadvertently deleting
    their entire trash folder and potentially to later change actual trash
    folder format.
    """
    trash_base = get_home_location(configuration, path)
    if trash_base is not None:
        if visible_link:
            trash_base = os.path.join(trash_base, trash_linkname)
        else:
            trash_base = os.path.join(trash_base, trash_destdir)
    return trash_base

def _check_access(configuration, action, target_list):
    """Verify access to action on paths in target_list"""
    _logger = configuration.logger
    for path in target_list:
        if invisible_path(path):
            _logger.warning("%s rejected on invisible path: %s" % (action, path))
            raise ValueError('contains protected files/folders')
        elif os.path.islink(path):
            _logger.warning("%s rejected on link %s" % (action, path))
            raise ValueError('contains special files/folders')

def _build_changes_path(configuration, changeset, pending=False):
    """Shared helper to build changes event path for changeset.
    The optional pending flag is used to build the temporary path rather than
    the final destination.
    """
    filename = "%s-%s" % (configuration.mig_server_id, changeset)
    if pending:
        filename = ".%s-pending" % filename
    changes_path = os.path.join(configuration.events_home, filename)
    return changes_path
    
def _fill_changes(configuration, changeset, action, target_list):
    """Helper to fill events file for a future user I/O action. Used internally
    by prepare_changes for building the event set during recursive traversal.
    The target_list argument may be a list of single path entries or (src, dst)
    tuples in case of a move. The action argument may take any of the change
    values CREATE, MODIFY, MOVE and DELETE defined here.
    The changeset argument is used to deduct the events file to use.
    Returns a handle to a temporary file with the saved events or None on
    failure.
    """
    _logger = configuration.logger
    _logger.debug("prepare %s %s event on %s" % (changeset, action, target_list))
    # Make sure events dir exists
    try:
        os.makedirs(configuration.events_home)
    except:
        pass
    pending_path = _build_changes_path(configuration, changeset, pending=True)

    if os.path.exists(pending_path):
        mode = "a"
    else:
        mode = "w"
    try:
        cfd = open(pending_path, mode)
        for target in target_list:
            cfd.write("%s:%s\n" % (action, target))
        cfd.close()
        return pending_path
    except Exception, err:
        _logger.error("Failed to save events: %s %s %s: %s" % \
                      (changeset, action, target_list, err))
        return None

def prepare_changes(configuration, operation, changeset, action, path,
                    recursive):
    """Prepare events file for a future user I/O action as a part of named
    operation. 
    The path argument may be a list of single path entries or (src, dst)
    tuples in case of a move. The action argument may take any of the change
    values CREATE, MODIFY, MOVE and DELETE defined here.
    The changeset argument is used to mark the action as a part of a bigger
    operation, like e.g. a recursive copy or move.
    The recursive argument can be used to automatically traverse any sub
    directories in move or copy operations.
    Returns a handle to a temporary file with the saved events or raises an
    exception in case changes would violate MiG file restrictions.
    """
    _logger = configuration.logger
    _logger.debug('%s user path: %s' % (operation, path))
    # TODO: properly handle MOVEs in walk below
    if action == MOVE:
        path = path[0]
    # First act on path itself
    target_list = [path]
    _check_access(configuration, action, target_list)
    pending_path = _fill_changes(configuration, changeset, action, target_list)
    # Use walk for recursive dir path - silently ignored for file path
    if not recursive or not os.path.isdir(path):
        return pending_path
    for (root, dirs, files) in walk(path, topdown=False, followlinks=True):
        for (kind, target) in [('files', files), ('dirs', dirs)]:
            if target:
                target_list = [os.path.join(root, name) for name in target]                
                _check_access(configuration, action, target_list)
                _logger.debug('%s user sub %s: %s' % (operation, kind,
                                                      target_list))
                _fill_changes(configuration, changeset, action, target_list)
    return pending_path

def commit_changes(configuration, changeset):
    """Actually commit events file after applying user I/O action. Used
    after building the event set with one or more calls to prepare_changes.
    The changeset argument is used to deduct the path to the pending and final
    events files.
    Returns a handle to the file with the committed events or None on error.
    """
    _logger = configuration.logger
    _logger.debug("commit %s events" % changeset)
    # Make sure events dir exists
    try:
        os.makedirs(configuration.events_home)
    except:
        pass
    changeset_path = _build_changes_path(configuration, changeset)
    pending_path = _build_changes_path(configuration, changeset, pending=True)
    try:
        os.rename(pending_path, changeset_path)
        return changeset_path
    except Exception, err:
        _logger.error("Failed to commit %s events in %s: %s" % \
                      (changeset, pending_path, err))
        return None

def abort_changes(configuration, changeset):
    """Abort prepared events in changeset upon early failure of any user I/O
    action. The temporary events file path created by any corresponding
    prepare_changes call(s) is automatically deducted from the changeset.
    """
    _logger = configuration.logger
    _logger.debug("abort %s events" % changeset)
    pending_path = _build_changes_path(configuration, changeset, pending=True)
    if not os.path.exists(pending_path):
        return True
    try:
        
        os.remove(pending_path)
        return True
    except Exception, err:
        _logger.error("failed to clean up after %s in %s" % (changeset,
                                                             pending_path))
        return None
    
def delete_path(configuration, path):
    """Wrapper to handle direct deletion of user file(s) in path. This version
    skips the user-friendly intermediate step of really just moving path to
    the trash folder in the user home or in the vgrid-special home, depending
    on the location of path.
    Automatically applies recursively for directories.
    """
    _logger = configuration.logger
    _logger.info('delete user path: %s' % path)
    result, errors = True, []
    changeset = "delete-%f" % time.time()
    if not path:
        _logger.error('not allowed to delete without path')
        result = False
        errors.append('no path provided')
        return (result, errors)
    elif not os.path.exists(path):
        _logger.error('no such file or directory %s' % path)
        result = False
        errors.append('no such path')
        return (result, errors)
        
    try:
        _logger.info('prepare delete user path %s' % path)
        pending_path = prepare_changes(configuration, 'delete', changeset,
                                       DELETE, path, True)
        _logger.info('actually deleting user path %s' % path)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except Exception, err:
        _logger.error('could not delete %s: %s' % (path, err))
        result = False
        errors.append("%s" % err)
            
    if result:
        commit_changes(configuration, changeset)
    else:
        abort_changes(configuration, changeset)
    return (result, errors)

def remove_path(configuration, path):
    """Wrapper to handle removal of user file(s) in path. This version uses the
    default behaviour of really just moving path to the trash folder in the
    corresponding user home or vgrid-special home, depending on the location
    of path.
    Automatically applies recursively for directories.
    """
    _logger = configuration.logger
    _logger.info('remove user path: %s' % path)
    result, errors = True, []
    changeset = "remove-%f" % time.time()
    if not path:
        _logger.error('not allowed to remove without path')
        result = False
        errors.append('no path provided')
        return (result, errors)
    elif not os.path.exists(path):
        _logger.error('no such file or directory %s' % path)
        result = False
        errors.append('no such path')
        return (result, errors)
    home_base = get_home_location(configuration, path)
    trash_base = get_trash_location(configuration, path)
    trash_link = get_trash_location(configuration, path, True)
    if trash_base is None:
        _logger.error('no suitable trash folder for: %s' % path)
        result = False
        errors.append('no suitable trash folder found')
        return (result, errors)

    real_path = os.path.realpath(path)
    if os.path.commonprefix([real_path, trash_base]) == trash_base:
        _logger.info('path %s is already in trash - do nothing' % real_path)
        return (result, errors)
    
    # Make sure trash folder and alias exists
    try:
        os.makedirs(trash_base)
    except:
        pass
    try:
        os.symlink(os.path.basename(trash_base), trash_link)
    except:
        pass

    try:
        _logger.info('prepare remove user path %s' % path)
        pending_path = prepare_changes(configuration, 'remove', changeset,
                                       DELETE, path, True)
        # Find free destination dir and remove last if necessary
        for suffix in [''] + ['.%d' % i for i in range(2, 100)]:
            sub_path = os.path.basename(path) + suffix
            trash_path = os.path.join(trash_base, sub_path)
            if not os.path.exists(trash_path):
                break
        if os.path.isdir(trash_path):
            shutil.rmtree(trash_path)
        _logger.info('actually moving user path %s to %s' % (path, trash_path))
        shutil.move(path, trash_path)
    except Exception, err:
        _logger.error('could not remove %s: %s' % (path, err))
        result = False
        errors.append("%s" % err)
            
    if result:
        commit_changes(configuration, changeset)
    else:
        abort_changes(configuration, changeset)
    return (result, errors)

def touch_path(configuration, path, timestamp=None):
    """Create path if it doesn't exist and set/update timestamp"""
    _logger = configuration.logger
    _logger.info('touch user path: %s (timestamp: %s)' % (path, timestamp))
    result, errors = True, []
    changeset = "touch-%f" % time.time()
    try:
        if not os.path.exists(path):
            prepare_changes(configuration, 'touch', changeset, CREATE, path,
                            False)
            open(path, 'w').close()

        if timestamp == None:
            timestamp = time.time()

        # set timestamp to supplied value

        prepare_changes(configuration, 'touch', changeset, MODIFY, path,
                        False)
        os.utime(path, (timestamp, timestamp))
        commit_changes(configuration, changeset)
    except Exception, err:
        _logger.error("could not touch %s: %s" % (path, err))
        result = False
        errors.append("%s" % err)
    return (result, errors)

def __make_test_files(configuration, test_path, dirs, files, links):
    """For unit testing setup"""
    try:
        os.makedirs(test_path)
    except:
        pass
    for sub_path in dirs + files + links:
        real_path = os.path.join(test_path, sub_path)
        if sub_path in dirs:
            try:
                os.makedirs(real_path)
            except:
                pass
        elif sub_path in files:
            fd = open(real_path, "w")
            fd.write('\n'.join(["sample line %d" % i for i in range(42)]))
            fd.close()
        else:
            os.symlink('.', real_path)

def __clean_test_files(configuration, test_path):
    """For unit testing cleanup"""
    try:
        shutil.rmtree(test_path)
    except:
        pass

if __name__ == "__main__":
    from shared.base import client_id_dir
    from shared.conf import get_configuration_object
    from shared.defaults import htaccess_filename
    print "Unit testing user I/O"
    client_id = "/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk"
    sub_dir = '.'
    if sys.argv[1:]:
        client_id = sys.argv[1]
    if sys.argv[2:]:
        sub_dir = sys.argv[2]
    client_dir = os.path.join(client_id_dir(client_id), sub_dir)
    configuration = get_configuration_object()
    tmp_dir = "userio-testdir"
    real_tmp = os.path.normpath(os.path.join(configuration.user_home,
                                             client_dir, tmp_dir))
    print "Using client tmp dir \n%s\nfor tests" % real_tmp
    basic_test = ([], ["test1.txt"], [])
    rec_test = (["sub1", "sub1/sub2", "sub1/sub2/sub3"],
                ["sub1/test1.txt", "sub1/test2.txt", "sub1/sub2/test4.txt",
                 "sub1/sub2/sub3/test5.txt"], [])
    invisible_test = ([], [htaccess_filename], [])
    link_test = ([], [], ['userio-testlink'])
    for (dirs, files, links) in [basic_test, rec_test, invisible_test,
                                 link_test]:
        real_target = os.path.join(real_tmp, (dirs + files + links)[0])
        for edit_func in (touch_path, ):
            __make_test_files(configuration, real_tmp, dirs, files, links)
            print "Run %s on %s" % (edit_func, real_target)
            print edit_func(configuration, real_target)
            __clean_test_files(configuration, real_tmp)
        for del_func in (delete_path, remove_path):
            __make_test_files(configuration, real_tmp, dirs, files, links)
            print "Run %s on %s" % (del_func, real_target)
            print del_func(configuration, real_target)
            __clean_test_files(configuration, real_tmp)
            
