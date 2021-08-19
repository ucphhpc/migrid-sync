#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# refunctions - runtime environment functions
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

"""Runtime Environment functions"""

from __future__ import absolute_import

import base64
import datetime
import fcntl
import os
import time

from mig.shared.modified import mark_re_modified, check_res_modified, \
    reset_res_modified
from mig.shared.rekeywords import get_keywords_dict as re_get_keywords_dict
from mig.shared.parser import parse, check_types
from mig.shared.serial import load, dump

WRITE_LOCK = 'write.lock'
RTE_SPECIALS = RUNTIMEENVS, CONF, MODTIME = \
    ['__runtimeenvs__', '__conf__', '__modtime__']

# Never repeatedly refresh maps within this number of seconds in same process
# Used to avoid refresh floods with e.g. runtime envs page calling
# refresh for each env when extracting providers.
MAP_CACHE_SECONDS = 60

last_refresh = {RUNTIMEENVS: 0}
last_load = {RUNTIMEENVS: 0}
last_map = {RUNTIMEENVS: {}}


def load_re_map(configuration, do_lock=True):
    """Load map of runtime environments. Uses a pickled dictionary for
    efficiency. The do_lock option is used to enable and disable locking
    during load.
    Returns tuple with map and time stamp of last map modification.
    Please note that time stamp is explicitly set to start of last update
    to make sure any concurrent updates get caught in next run.
    """
    map_path = os.path.join(configuration.mig_system_files, "runtimeenvs.map")
    lock_path = map_path.replace('.map', '.lock')
    if do_lock:
        lock_handle = open(lock_path, 'a')
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    try:
        configuration.logger.info("before re map load")
        re_map = load(map_path)
        configuration.logger.info("after re map load")
        map_stamp = os.path.getmtime(map_path)
    except IOError:
        configuration.logger.warning("No re map to load")
        re_map = {}
        map_stamp = -1
    if do_lock:
        lock_handle.close()
    return (re_map, map_stamp)


def refresh_re_map(configuration):
    """Refresh map of runtime environments and their configuration. Uses a
    pickled dictionary for efficiency. 
    Only update map for runtime environments that appeared or disappeared after
    last map save.
    NOTE: Save start time so that any concurrent updates get caught next time.
    """
    start_time = time.time()
    dirty = []
    map_path = os.path.join(configuration.mig_system_files, "runtimeenvs.map")
    lock_path = map_path.replace('.map', '.lock')
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    re_map, map_stamp = load_re_map(configuration, do_lock=False)

    # Find all runtimeenvs and their configurations

    (load_status, all_res) = list_runtime_environments(configuration)
    if not load_status:
        configuration.logger.error(
            "failed to load runtimeenv list: %s" % all_res)
        return re_map
    for re_name in all_res:
        re_path = os.path.join(configuration.re_home, re_name)
        re_mtime = 0
        if os.path.isfile(re_path):
            re_mtime = os.path.getmtime(re_path)

        # init first time
        re_map[re_name] = re_map.get(re_name, {})
        if CONF not in re_map[re_name] or re_mtime >= map_stamp:
            re_conf = get_re_conf(re_name, configuration)
            if not re_conf:
                re_conf = {}
            re_map[re_name][CONF] = re_conf
            re_map[re_name][MODTIME] = map_stamp
            dirty += [re_name]
    # Remove any missing runtimeenvs from map
    missing_re = [re_name for re_name in re_map if not re_name in all_res]
    for re_name in missing_re:
        del re_map[re_name]
        dirty += [re_name]

    if dirty:
        try:
            dump(re_map, map_path)
            os.utime(map_path, (start_time, start_time))
        except Exception as exc:
            configuration.logger.error("Could not save re map: %s" % exc)

    last_refresh[RUNTIMEENVS] = start_time
    lock_handle.close()

    return re_map


def get_re_map(configuration):
    """Returns the current map of runtime environments and their
    configurations. Caches the map for load prevention with repeated calls
    within short time span.
    """
    if last_load[RUNTIMEENVS] + MAP_CACHE_SECONDS > time.time():
        configuration.logger.debug("using cached re map")
        return last_map[RUNTIMEENVS]
    modified_res, _ = check_res_modified(configuration)
    if modified_res:
        configuration.logger.info("refreshing re map (%s)" % modified_res)
        map_stamp = time.time()
        re_map = refresh_re_map(configuration)
        reset_res_modified(configuration)
    else:
        configuration.logger.debug("No changes - not refreshing")
        re_map, map_stamp = load_re_map(configuration)
    last_map[RUNTIMEENVS] = re_map
    last_refresh[RUNTIMEENVS] = map_stamp
    last_load[RUNTIMEENVS] = map_stamp
    return re_map


def list_runtime_environments(configuration):
    """Find all runtime environments"""
    re_list = []
    dir_content = []

    try:
        dir_content = os.listdir(configuration.re_home)
    except Exception:
        if not os.path.isdir(configuration.re_home):
            try:
                os.mkdir(configuration.re_home)
            except Exception as err:
                configuration.logger.info(
                    'refunctions.py: not able to create directory %s: %s'
                    % (configuration.re_home, err))
                return (False, "runtime env setup is broken")
            dir_content = []

    for entry in dir_content:

        # Skip dot files/dirs and the write lock

        if (entry.startswith('.')) or (entry == WRITE_LOCK):
            continue
        if os.path.isfile(os.path.join(configuration.re_home, entry)):

            # entry is a file and hence a runtime environment

            re_list.append(entry)
        else:
            configuration.logger.warning(
                '%s in %s is not a plain file, move it?'
                % (entry, configuration.re_home))

    return (True, re_list)


def is_runtime_environment(re_name, configuration):
    """Check that re_name is an existing runtime environment"""
    if os.path.isfile(os.path.join(configuration.re_home, re_name)):
        return True
    else:
        return False


def get_re_dict(name, configuration):
    """Helper to extract a saved runtime environment"""
    re_dict = load(os.path.join(configuration.re_home, name))
    if not re_dict:
        return (False, 'Could not open runtime environment %s' % name)
    else:
        return (re_dict, '')


def get_re_conf(re_name, configuration):
    """Wrapper to mimic other get_X_conf functions but using get_re_dict"""
    (conf, msg) = get_re_dict(re_name, configuration)
    return conf


def delete_runtimeenv(re_name, configuration):
    """Delete an existing runtime environment"""
    status, msg = True, ""
    # Lock the access to the runtime env files, so that deletion is done
    # with exclusive access.
    lock_path = os.path.join(configuration.re_home, WRITE_LOCK)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    filename = os.path.join(configuration.re_home, re_name)
    if os.path.isfile(filename):
        try:
            os.remove(filename)
            mark_re_modified(configuration, re_name)
        except Exception as err:
            msg = "Exception during deletion of runtime enviroment '%s': %s"\
                  % (re_name, err)
            status = False
    else:
        msg = "Tried to delete non-existing runtime enviroment '%s'" % re_name
        configuration.logger.warning(msg)
        status = False
    lock_handle.close()
    return (status, msg)


def create_runtimeenv(filename, client_id, configuration):
    """Create a new runtime environment"""
    result = parse(filename)
    external_dict = re_get_keywords_dict()

    (status, parsemsg) = check_types(result, external_dict, configuration)

    try:
        os.remove(filename)
    except Exception as err:
        msg = \
            'Exception removing temporary runtime environment file %s, %s'\
            % (filename, err)

    if not status:
        msg = 'Parse failed (typecheck) %s' % parsemsg
        return (False, msg)

    new_dict = {}

    # move parse result to a dictionary

    for (key, value_dict) in external_dict.items():
        new_dict[key] = value_dict['Value']

    new_dict['CREATOR'] = client_id
    new_dict['CREATED_TIMESTAMP'] = datetime.datetime.now()

    re_name = new_dict['RENAME']

    re_filename = os.path.join(configuration.re_home, re_name)

    # Lock the access to the runtime env files, so that creation is done
    # with exclusive access.
    lock_path = os.path.join(configuration.re_home, WRITE_LOCK)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    status, msg = True, ''
    if os.path.exists(re_filename):
        status = False
        msg = \
            "can not recreate existing runtime environment '%s'!" % re_name

    try:
        dump(new_dict, re_filename)
        mark_re_modified(configuration, re_name)
    except Exception as err:
        status = False
        msg = 'Internal error saving new runtime environment: %s' % err

    lock_handle.close()
    return (status, msg)


def update_runtimeenv_owner(re_name, old_owner, new_owner, configuration):
    """Update owner on an existing runtime environment if existing owner
    matches old_owner.
    """
    status, msg = True, ""
    # Lock the access to the runtime env files, so that edit is done
    # with exclusive access.
    lock_path = os.path.join(configuration.re_home, WRITE_LOCK)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    re_filename = os.path.join(configuration.re_home, re_name)
    try:
        re_dict = load(re_filename)
        if re_dict['CREATOR'] == old_owner:
            re_dict['CREATOR'] = new_owner
            dump(re_dict, re_filename)
            mark_re_modified(configuration, re_name)
        else:
            status = False
    except Exception as err:
        msg = "Failed to edit owner of runtime enviroment '%s': %s" % \
              (re_name, err)
        configuration.logger.warning(msg)
        status = False
    lock_handle.close()
    return (status, msg)


def build_reitem_object(configuration, re_dict):
    """Build a runtimeenvironment object based on input re_dict"""

    software_list = []
    soft = re_dict['SOFTWARE']
    if len(soft) > 0:
        for software_item in soft:
            if software_item['url'].find('://') < 0:
                software_item['url'] = 'http://%(url)s' % software_item
            software_list.append({
                'object_type': 'software',
                'name': software_item['name'],
                'icon': software_item['icon'],
                'url': software_item['url'],
                'description': software_item['description'],
                'version': software_item['version'],
            })

    # anything specified?

    testprocedure = ''
    if len(re_dict['TESTPROCEDURE']) > 0:
        base64string = ''
        for stringpart in re_dict['TESTPROCEDURE']:
            base64string += stringpart
        testprocedure = base64.decodestring(base64string)

    verifystdout = ''
    if len(re_dict['VERIFYSTDOUT']) > 0:
        for string in re_dict['VERIFYSTDOUT']:
            verifystdout += string

    verifystderr = ''
    if len(re_dict['VERIFYSTDERR']) > 0:
        for string in re_dict['VERIFYSTDERR']:
            verifystderr += string

    verifystatus = ''
    if len(re_dict['VERIFYSTATUS']) > 0:
        for string in re_dict['VERIFYSTATUS']:
            verifystatus += string

    environments = []
    env = re_dict['ENVIRONMENTVARIABLE']
    if len(env) > 0:
        for environment_item in env:
            environments.append({
                'object_type': 'environment',
                'name': environment_item['name'],
                'example': environment_item['example'],
                'description': environment_item['description'],
            })
    created_timetuple = re_dict['CREATED_TIMESTAMP'].timetuple()
    created_asctime = time.asctime(created_timetuple)
    created_epoch = time.mktime(created_timetuple)
    return {
        'object_type': 'runtimeenvironment',
        'name': re_dict['RENAME'],
        'description': re_dict['DESCRIPTION'],
        'creator': re_dict['CREATOR'],
        'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
                                                        created_asctime),
        'job_count': '(not implemented yet)',
        'testprocedure': testprocedure,
        'verifystdout': verifystdout,
        'verifystderr': verifystderr,
        'verifystatus': verifystatus,
        'environments': environments,
        'software': software_list,
    }
