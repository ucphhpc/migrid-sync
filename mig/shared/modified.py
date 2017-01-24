#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# modified - entity modification mark manipulation
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

import fcntl
import os
import time

from shared.defaults import keyword_all
from shared.serial import load, dump

def mark_entity_modified(configuration, kind, name):
    """Mark name of given kind modified to signal reload before use from other
    locations.
    """
    modified_path = os.path.join(configuration.mig_system_files,
                                 "%s.modified" % kind)
    lock_path = os.path.join(configuration.mig_system_files, "%s.lock" % kind)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    try:
        if os.path.exists(modified_path):
            modified_list = load(modified_path)
        else:
            modified_list = []
        if not name in modified_list:
            modified_list.append(name)
        dump(modified_list, modified_path)
    except Exception, exc:
        configuration.logger.error("Could not update %s modified mark: %s" % \
                                   (kind, exc))
    lock_handle.close()

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

def check_entities_modified(configuration, kind):
    """Check and return any name of given kind that are marked as modified
    along with a time stamp for the latest modification"""
    modified_path = os.path.join(configuration.mig_system_files,
                                 "%s.modified" % kind)
    map_path = os.path.join(configuration.mig_system_files, "%s.map" % kind)
    lock_path = os.path.join(configuration.mig_system_files, "%s.lock" % kind)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    try:
        if not os.path.isfile(map_path):
            configuration.logger.warning("%s map doesn't exist, new install?" \
                                         % kind)
            raise Exception("%s map does not exist" % kind)
        modified_list = load(modified_path)
        modified_stamp = os.path.getmtime(modified_path)
    except Exception, exc:
        # No modified list - probably first time so force update
        modified_list = [keyword_all]
        modified_stamp = time.time()
    lock_handle.close()
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

def reset_entities_modified(configuration, kind):
    """Reset all modified entity marks of given kind"""
    modified_path = os.path.join(configuration.mig_system_files,
                                 "%s.modified" % kind)
    lock_path = os.path.join(configuration.mig_system_files, "%s.lock" % kind)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    try:
        dump([], modified_path)
    except Exception, exc:
        configuration.logger.error("Could not reset %s modified mark: %s" % \
                                   (kind, exc))
    lock_handle.close()

def reset_users_modified(configuration):
    """Reset user modified marks"""
    return reset_entities_modified(configuration, 'user')

def reset_resources_modified(configuration):
    """Reset resource modified marks"""
    return reset_entities_modified(configuration, 'resource')

def reset_vgrids_modified(configuration):
    """Reset vgrid modified marks"""
    return reset_entities_modified(configuration, 'vgrid')

def reset_res_modified(configuration):
    """Reset res modified marks"""
    return reset_entities_modified(configuration, 'runtimeenvs')

if __name__ == "__main__":
    import sys
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    re_name = 'BASH-ANY-1'
    if sys.argv[1:]:
        re_name = sys.argv[1]
    print "Check runtime envs modified: %s %s" % check_res_modified(conf)
    print "Marking runtime envs modified: %s" % re_name
    mark_re_modified(conf, re_name)
    print "Check runtime envs modified: %s %s" % check_res_modified(conf)
        
