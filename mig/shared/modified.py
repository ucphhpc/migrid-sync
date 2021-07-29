#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# modified - entity modification mark manipulation
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Functions for marking and checking modification status of entities"""

from __future__ import print_function
from __future__ import absolute_import

import fcntl
import os
import time

from mig.shared.defaults import keyword_all
from mig.shared.fileio import acquire_file_lock, release_file_lock
from mig.shared.serial import load, dump, dumps

EMPTY_PICKLE_SIZE = len(dumps([]))


def mark_entity_modified(configuration, kind, name):
    """Mark name of given kind modified to signal reload before use from other
    locations.
    """
    _logger = configuration.logger
    success = False
    modified_path = os.path.join(configuration.mig_system_files,
                                 "%s.modified" % kind)
    lock_path = os.path.join(configuration.mig_system_files, "%s.lock" % kind)
    lock_handle = None
    try:
        lock_handle = acquire_file_lock(lock_path, exclusive=True)
        if os.path.exists(modified_path):
            modified_list = load(modified_path)
        else:
            modified_list = []
        if not name in modified_list:
            modified_list.append(name)
        dump(modified_list, modified_path)
        success = True
    except Exception as exc:
        _logger.error("Could not update %s modified mark: %s" % (kind, exc))
    finally:
        if lock_handle:
            release_file_lock(lock_handle)
            lock_handle = None
    return success


def mark_user_modified(configuration, user_name):
    """Mark user_name modified to signal e.g. user_map refresh before next
    use"""
    return mark_entity_modified(configuration, 'user', user_name)


def mark_resource_modified(configuration, resource_name):
    """Mark resource_name modified to signal e.g. resource_map refresh before
    next use"""
    return mark_entity_modified(configuration, 'resource', resource_name)


def mark_vgrid_modified(configuration, vgrid_name):
    """Mark vgrid_name modified to signal e.g. vgrid_map refresh before next
    use.
    """
    return mark_entity_modified(configuration, 'vgrid', vgrid_name)


def mark_re_modified(configuration, re_name):
    """Mark re_name modified to signal e.g. re_map refresh
    before next use"""
    return mark_entity_modified(configuration, 'runtimeenvs', re_name)


def mark_workflow_p_modified(configuration, workflow_pattern_name):
    """Mark workflow pattern modified to signal e.g.
    workflow_p_map refresh before next use"""
    return mark_entity_modified(configuration, 'workflowpatterns',
                                workflow_pattern_name)


def mark_workflow_r_modified(configuration, workflow_recipe_name):
    """Mark workflow recipe modified to signal e.g.
    workflow_r_map refresh before next use"""
    return mark_entity_modified(configuration, 'workflowrecipes',
                                workflow_recipe_name)


def check_entities_modified(configuration, kind):
    """Check and return any name of given kind that are marked as modified
    along with a time stamp for the latest modification"""
    _logger = configuration.logger
    modified_path = os.path.join(configuration.mig_system_files,
                                 "%s.modified" % kind)
    map_path = os.path.join(configuration.mig_system_files, "%s.map" % kind)
    lock_path = os.path.join(configuration.mig_system_files, "%s.lock" % kind)
    lock_handle = None
    try:
        # NOTE: we only need shared lock here to read modified
        lock_handle = acquire_file_lock(lock_path, exclusive=False)
        if not os.path.isfile(map_path):
            raise Exception("%s map does not exist" % kind)
        modified_list = load(modified_path)
        modified_stamp = os.path.getmtime(modified_path)
    except Exception as exc:
        # Okay if a new install
        _logger.warning("could not check %s modified: %s" % (kind, exc))
        # No modified list - probably first time so force update
        modified_list = [keyword_all]
        modified_stamp = time.time()
    finally:
        if lock_handle:
            release_file_lock(lock_handle)
            lock_handle = None
    return (modified_list, modified_stamp)


def check_users_modified(configuration):
    """Check for modified users and return list of such IDs"""
    return check_entities_modified(configuration, 'user')


def check_resources_modified(configuration):
    """Check for modified resources and return list of such IDs"""
    return check_entities_modified(configuration, 'resource')


def check_vgrids_modified(configuration):
    """Check for modified vgrids and return list of such IDs"""
    return check_entities_modified(configuration, 'vgrid')


def check_res_modified(configuration):
    """Check for modified re and return list of such IDs"""
    return check_entities_modified(configuration, 'runtimeenvs')


def check_workflow_p_modified(configuration):
    """Check for modified workflow patterns and return a list of such IDs"""
    return check_entities_modified(configuration, 'workflowpatterns')


def check_workflow_r_modified(configuration):
    """Check for modified workflow recipes and return a list of such IDs"""
    return check_entities_modified(configuration, 'workflowrecipes')


def pending_entities_update(configuration, kind):
    """Check if entities modified file - including total absence - indicates a
    pending update. The latter is the case on first run where helper maps are
    not yet generated.
    """
    _logger = configuration.logger
    modified_path = os.path.join(configuration.mig_system_files,
                                 "%s.modified" % kind)
    # NOTE: check if modified file exists with size above pickled empty list
    if not os.path.exist(modified_path):
        _logger.debug("no %s file - require update" % modified_path)
        return True
    try:
        return os.path.getsize(modified_path) > EMPTY_PICKLE_SIZE
    except Exception as exc:
        # Probably because modified file doesn't exist so just ignore
        _logger.debug("could not get size of %s: %s" % (modified_path, exc))
        return False


def pending_users_update(configuration):
    """Check if user modified file indicates a pending update"""
    return pending_entities_update(configuration, 'user')


def pending_resources_update(configuration):
    """Check if resource modified file indicates a pending update"""
    return pending_entities_update(configuration, 'resource')


def pending_vgrids_update(configuration):
    """Check if vgrid modified file indicates a pending update"""
    return pending_entities_update(configuration, 'vgrid')


def pending_res_update(configuration):
    """Check if re modified file indicates a pending update"""
    return pending_entities_update(configuration, 'runtimeenvs')


def reset_entities_modified(configuration, kind, only_before=-1):
    """Reset all modified entity marks of given kind. If the optional
    only_before argument is a positive value the reset will ONLY happen if the
    entities modified file is older than that timestamp. This is important in
    preventing very recent changes getting lost during the actual map update.
    """
    _logger = configuration.logger
    success = False
    modified_path = os.path.join(configuration.mig_system_files,
                                 "%s.modified" % kind)
    lock_path = os.path.join(configuration.mig_system_files, "%s.lock" % kind)
    lock_handle = None
    try:
        lock_handle = acquire_file_lock(lock_path, exclusive=True)
        if only_before >= 0 and os.path.exists(modified_path) and \
                os.path.getmtime(modified_path) > only_before:
            _logger.info("skip reset of modified mark for on-going operation")
        else:
            dump([], modified_path)
            success = True
    except Exception as exc:
        _logger.error("Could not reset %s modified mark: %s" % (kind, exc))
    finally:
        if lock_handle:
            release_file_lock(lock_handle)
            lock_handle = None
    return success


def reset_users_modified(configuration, only_before=-1):
    """Reset user modified marks"""
    return reset_entities_modified(configuration, 'user', only_before)


def reset_resources_modified(configuration, only_before=-1):
    """Reset resource modified marks"""
    return reset_entities_modified(configuration, 'resource', only_before)


def reset_vgrids_modified(configuration, only_before=-1):
    """Reset vgrid modified marks"""
    return reset_entities_modified(configuration, 'vgrid', only_before)


def reset_res_modified(configuration, only_before=-1):
    """Reset res modified marks"""
    return reset_entities_modified(configuration, 'runtimeenvs', only_before)


def reset_workflow_p_modified(configuration, only_before=-1):
    """Reset workflow patterns modified marks"""
    return reset_entities_modified(configuration, 'workflowpatterns',
                                   only_before)


def reset_workflow_r_modified(configuration, only_before=-1):
    """Reset workflow recipes modified marks"""
    return reset_entities_modified(configuration, 'workflowrecipes',
                                   only_before)


if __name__ == "__main__":
    import sys
    from mig.shared.conf import get_configuration_object
    conf = get_configuration_object()
    re_name = 'BASH-ANY-1'
    if sys.argv[1:]:
        re_name = sys.argv[1]
    print("Check runtime envs modified: %s %s" % check_res_modified(conf))
    print("Marking runtime envs modified: %s" % re_name)
    mark_re_modified(conf, re_name)
    print("Check runtime envs modified: %s %s" % check_res_modified(conf))
