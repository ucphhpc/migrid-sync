#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridaccess - user access in VGrids
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

"""User access to VGrids"""

import copy
import os
import time
import fcntl

from shared.base import sandbox_resource, client_id_dir
from shared.conf import get_all_exe_vgrids, get_resource_fields, \
     get_resource_configuration
from shared.defaults import settings_filename, profile_filename, default_vgrid
from shared.modified import home_paths, mark_resource_modified, \
     mark_vgrid_modified, check_users_modified, check_resources_modified, \
     check_vgrids_modified, reset_users_modified, reset_resources_modified, \
     reset_vgrids_modified
from shared.resource import list_resources, real_to_anon_res_map
from shared.serial import load, dump
from shared.user import list_users, real_to_anon_user_map, get_user_conf
from shared.vgrid import vgrid_list_vgrids, vgrid_allowed, vgrid_resources, \
     user_allowed_vgrids, vgrid_owners, vgrid_members, vgrid_settings, \
     vgrid_list_subvgrids, vgrid_list_parents

MAP_SECTIONS = (USERS, RESOURCES, VGRIDS) = ("__users__", "__resources__",
                                             "__vgrids__")
RES_SPECIALS = (ALLOW, ASSIGN, USERID, RESID, OWNERS, MEMBERS, CONF, MODTIME) = \
               ('__allow__', '__assign__', '__userid__', '__resid__',
                '__owners__', '__members__', '__conf__', '__modtime__')
# VGrid-specific settings
SETTINGS = '__settings__'

# Never repeatedly refresh maps within this number of seconds in same process
# Used to avoid refresh floods with e.g. runtime envs page calling
# refresh for each env when extracting providers.
MAP_CACHE_SECONDS = 30

last_refresh = {USERS: 0, RESOURCES: 0, VGRIDS: 0}
last_load = {USERS: 0, RESOURCES: 0, VGRIDS: 0}
last_map = {USERS: {}, RESOURCES: {}, VGRIDS: {}}

def load_entity_map(configuration, kind, do_lock):
    """Load map of given entities and their configuration. Uses a pickled
    dictionary for efficiency. The do_lock option is used to enable and
    disable locking during load.
    Entity IDs are stored in their raw (non-anonymized form).
    Returns tuple with map and time stamp of last map modification.
    """
    home_map = home_paths(configuration)
    map_path = os.path.join(configuration.mig_system_files, "%s.map" % kind)
    lock_path = os.path.join(configuration.mig_system_files, "%s.lock" % kind)
    if do_lock:
        lock_handle = open(lock_path, 'a')
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    try:
        configuration.logger.info("before %s map load" % kind)
        entity_map = load(map_path)
        configuration.logger.info("after %s map load" % kind)
        map_stamp = os.path.getmtime(map_path)
    except IOError:
        configuration.logger.warn("No %s map to load" % kind)
        entity_map = {}
        map_stamp = -1
    if do_lock:
        lock_handle.close()
    return (entity_map, map_stamp)

def load_user_map(configuration, do_lock=True):
    """Load map of users and their configuration. Uses a pickled
    dictionary for efficiency. Optional do_lock option is used to enable and
    disable locking during load.
    User IDs are stored in their raw (non-anonymized form).
    Returns tuple with map and time stamp of last map modification.
    """
    return load_entity_map(configuration, 'user', do_lock)

def load_resource_map(configuration, do_lock=True):
    """Load map of resources and their configuration. Uses a pickled
    dictionary for efficiency. Optional do_lock option is used to enable and
    disable locking during load.
    Resource IDs are stored in their raw (non-anonymized form).
    """
    return load_entity_map(configuration, 'resource', do_lock)

def load_vgrid_map(configuration, do_lock=True):
    """Load map of vgrids and their configuration. Uses a pickled
    dictionary for efficiency. Optional do_lock option is used to enable and
    disable locking during load.
    Resource IDs are stored in their raw (non-anonymized form).
    """
    return load_entity_map(configuration, 'vgrid', do_lock)

def refresh_user_map(configuration):
    """Refresh map of users and their configuration. Uses a pickled
    dictionary for efficiency. 
    User IDs are stored in their raw (non-anonymized form).
    Only update map for users that updated conf after last map save.
    """
    dirty = []
    map_path = os.path.join(configuration.mig_system_files, "user.map")
    lock_path = os.path.join(configuration.mig_system_files, "user.lock")
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    user_map, map_stamp = load_user_map(configuration, do_lock=False)

    # Find all users and their configurations
    
    all_users = list_users(configuration.user_home)
    real_map = real_to_anon_user_map(configuration.user_home)
    for user in all_users:
        settings_path = os.path.join(configuration.user_settings,
                                     client_id_dir(user), settings_filename)
        profile_path = os.path.join(configuration.user_settings,
                                    client_id_dir(user), profile_filename)
        settings_mtime, profile_mtime = 0, 0
        if os.path.isfile(settings_path):
            settings_mtime = os.path.getmtime(settings_path)
        if os.path.isfile(profile_path):
            profile_mtime = os.path.getmtime(profile_path)

        if settings_mtime + profile_mtime > 0:
            conf_mtime = max(settings_mtime, profile_mtime)
        else:
            conf_mtime = -1
        # init first time
        user_map[user] = user_map.get(user, {})
        if not user_map[user].has_key(CONF) or conf_mtime >= map_stamp:
            user_conf = get_user_conf(user, configuration, True)
            if not user_conf:
                user_conf = {}
            user_map[user][CONF] = user_conf
            public_id = user
            if user_conf.get('ANONYMOUS', True):
                public_id = real_map[user]
            user_map[user][USERID] = public_id
            user_map[user][MODTIME] = map_stamp
            dirty += [user]
    # Remove any missing users from map
    missing_user = [user for user in user_map.keys() \
                   if not user in all_users]
    for user in missing_user:
        del user_map[user]
        dirty += [user]

    if dirty:
        try:
            dump(user_map, map_path)
        except Exception, exc:
            configuration.logger.error("Could not save user map: %s" % exc)

    last_refresh[USERS] = time.time()
    lock_handle.close()

    return user_map

def refresh_resource_map(configuration):
    """Refresh map of resources and their configuration. Uses a pickled
    dictionary for efficiency. 
    Resource IDs are stored in their raw (non-anonymized form).
    Only update map for resources that updated conf after last map save.
    """
    dirty = []
    map_path = os.path.join(configuration.mig_system_files, "resource.map")
    lock_path = os.path.join(configuration.mig_system_files, "resource.lock")
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    resource_map, map_stamp = load_resource_map(configuration, do_lock=False)

    # Find all resources and their configurations
    
    all_resources = list_resources(configuration.resource_home,
                                   only_valid=True)
    real_map = real_to_anon_res_map(configuration.resource_home)
    for res in all_resources:
        # Sandboxes do not change their configuration
        if resource_map.has_key(res) and sandbox_resource(res):
            continue
        conf_path = os.path.join(configuration.resource_home, res, "config")
        if not os.path.isfile(conf_path):
            continue
        conf_mtime = os.path.getmtime(conf_path)
        owners_path = os.path.join(configuration.resource_home, res, "owners")
        if not os.path.isfile(owners_path):
            continue
        owners_mtime = os.path.getmtime(owners_path)
        # init first time
        resource_map[res] = resource_map.get(res, {})
        if not resource_map[res].has_key(CONF) or conf_mtime >= map_stamp:
            (status, res_conf) = get_resource_configuration(
                configuration.resource_home, res, configuration.logger)
            if not status:
                continue
            resource_map[res][CONF] = res_conf
            public_id = res
            if res_conf.get('ANONYMOUS', True):
                public_id = real_map[res]
            resource_map[res][RESID] = public_id
            resource_map[res][MODTIME] = map_stamp
            dirty += [res]
        if not resource_map[res].has_key(OWNERS) or owners_mtime >= map_stamp:
            owners = load(owners_path)
            resource_map[res][OWNERS] = owners
            resource_map[res][MODTIME] = map_stamp
            dirty += [res]
    # Remove any missing resources from map
    missing_res = [res for res in resource_map.keys() \
                   if not res in all_resources]
    for res in missing_res:
        del resource_map[res]
        dirty += [res]

    if dirty:
        try:
            dump(resource_map, map_path)
        except Exception, exc:
            configuration.logger.error("Could not save resource map: %s" % exc)

    last_refresh[RESOURCES] = time.time()
    lock_handle.close()

    return resource_map

def refresh_vgrid_map(configuration):
    """Refresh map of users and resources with their direct vgrid
    participation. That is, without inheritance. Uses a pickled dictionary for
    efficiency. 
    Resource and user IDs are stored in their raw (non-anonymized form).
    Only update map for users and resources that updated conf after last map
    save.
    """
    dirty = {}
    vgrid_changes = {}
    map_path = os.path.join(configuration.mig_system_files, "vgrid.map")
    lock_path = os.path.join(configuration.mig_system_files, "vgrid.lock")
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    vgrid_map, map_stamp = load_vgrid_map(configuration, do_lock=False)
    
    vgrid_helper = {default_vgrid: {RESOURCES: ['*'], OWNERS: [], MEMBERS: ['*'],
                                    SETTINGS: []}}
    if not vgrid_map.has_key(VGRIDS):
        vgrid_map[VGRIDS] = vgrid_helper
        dirty[VGRIDS] = dirty.get(VGRIDS, []) + [default_vgrid]
    if not vgrid_map.has_key(RESOURCES):
        vgrid_map[RESOURCES] = {}
        dirty[RESOURCES] = dirty.get(RESOURCES, [])
    if not vgrid_map.has_key(USERS):
        vgrid_map[USERS] = {}
        dirty[USERS] = dirty.get(USERS, [])

    # Find all vgrids and their allowed users and resources

    (status, all_vgrids) = vgrid_list_vgrids(configuration)
    if not status:
        all_vgrids = []

    conf_read = [(RESOURCES, configuration.vgrid_resources, vgrid_resources),
                 (OWNERS, configuration.vgrid_owners, vgrid_owners),
                 (MEMBERS, configuration.vgrid_members, vgrid_members),
                 (SETTINGS, configuration.vgrid_settings, vgrid_settings)]

    for vgrid in all_vgrids:
        for (field, name, list_call) in conf_read:
            conf_path = os.path.join(configuration.vgrid_home, vgrid, name)
            if not os.path.isfile(conf_path):
                configuration.logger.warning('missing file: %s' % (conf_path)) 
                # Make sure vgrid dict exists before filling it
                vgrid_map[VGRIDS][vgrid] = vgrid_map[VGRIDS].get(vgrid, {})
                vgrid_map[VGRIDS][vgrid][field] = []
                dirty[VGRIDS] = dirty.get(VGRIDS, []) + [vgrid]

            elif not vgrid_map[VGRIDS].has_key(vgrid) or \
                   os.path.getmtime(conf_path) >= map_stamp:
                (status, entries) = list_call(vgrid, configuration,
                                              recursive=False)
                if not status:
                    entries = []
                vgrid_changes[vgrid] = vgrid_changes.get(vgrid, {})
                map_entry = vgrid_map[VGRIDS].get(vgrid, {})
                vgrid_changes[vgrid][field] = (map_entry.get(field, []),
                                               entries)
                vgrid_map[VGRIDS][vgrid] = map_entry
                vgrid_map[VGRIDS][vgrid][field] = entries
                dirty[VGRIDS] = dirty.get(VGRIDS, []) + [vgrid]
    # Remove any missing vgrids from map
    missing_vgrids = [vgrid for vgrid in vgrid_map[VGRIDS].keys() \
                   if not vgrid in all_vgrids]
    for vgrid in missing_vgrids:
        vgrid_changes[vgrid] = vgrid_changes.get(vgrid, {})
        map_entry = vgrid_map[VGRIDS].get(vgrid, {})
        for (field, _, _) in conf_read:
            vgrid_changes[vgrid][field] = (map_entry.get(field, []), [])
        del vgrid_map[VGRIDS][vgrid]
        dirty[VGRIDS] = dirty.get(VGRIDS, []) + [vgrid]

    # Find all resources and their vgrid assignments
    
    # TODO: use get_resource_map output instead?
    all_resources = list_resources(configuration.resource_home, only_valid=True)
    real_map = real_to_anon_res_map(configuration.resource_home)
    for res in all_resources:
        # Sandboxes do not change their vgrid participation
        if vgrid_map[RESOURCES].has_key(res) and sandbox_resource(res):
            continue
        conf_path = os.path.join(configuration.resource_home, res, "config")
        if not os.path.isfile(conf_path):
            continue
        if os.path.getmtime(conf_path) >= map_stamp:
            vgrid_map[RESOURCES][res] = get_all_exe_vgrids(res)
            assigned = []
            all_exes = [i for i in vgrid_map[RESOURCES][res].keys() \
                        if not i in RES_SPECIALS]
            for exe in all_exes:
                exe_vgrids = vgrid_map[RESOURCES][res][exe]
                assigned += [i for i in exe_vgrids if i and i not in assigned]
            vgrid_map[RESOURCES][res][ASSIGN] = assigned
            vgrid_map[RESOURCES][res][ALLOW] = vgrid_map[RESOURCES][res].get(ALLOW, [])
            public_id = res
            anon_val = get_resource_fields(configuration.resource_home, res,
                                           ['ANONYMOUS'], configuration.logger)
            if anon_val.get('ANONYMOUS', True):
                public_id = real_map[res]
            vgrid_map[RESOURCES][res][RESID] = public_id
            dirty[RESOURCES] = dirty.get(RESOURCES, []) + [res]
    # Remove any missing resources from map
    missing_res = [res for res in vgrid_map[RESOURCES].keys() \
                   if not res in all_resources]
    for res in missing_res:
        del vgrid_map[RESOURCES][res]
        dirty[RESOURCES] = dirty.get(RESOURCES, []) + [res]

    # Update list of mutually agreed vgrid participations for dirty resources
    # and resources assigned to dirty vgrids
    configuration.logger.info("update res vgrid participations: %s" % vgrid_changes)
    update_res = [i for i in dirty.get(RESOURCES, []) if i not in MAP_SECTIONS]
    # configuration.logger.info("update vgrid allow res")
    for (vgrid, changes) in vgrid_changes.items():
        old, new = changes.get(RESOURCES, ([], []))
        if old == new:
            configuration.logger.debug("skip res update of vgrid %s (%s)" % \
                                       (vgrid, changes))
            continue
        # configuration.logger.info("update res vgrid %s" % vgrid)
        for res in [i for i in vgrid_map[RESOURCES].keys() \
                    if i not in update_res]:
            # Sandboxes do not change their vgrid participation
            if sandbox_resource(res):
                continue
            # configuration.logger.info("update res vgrid %s for res %s" % (vgrid, res))
            if vgrid_allowed(res, old) != vgrid_allowed(res, new):
                update_res.append(res)
    # configuration.logger.info("update res assign vgrid")
    for res in [i for i in update_res if i not in missing_res]:
        allow = []
        for vgrid in vgrid_map[RESOURCES][res][ASSIGN]:
            if vgrid_allowed(res, vgrid_map[VGRIDS][vgrid][RESOURCES]):
                allow.append(vgrid)
            vgrid_map[RESOURCES][res][ALLOW] = allow

    configuration.logger.info("done updating vgrid res participations")

    # Find all users and their vgrid assignments
    
    # TODO: use get_user_map output instead?
    all_users = list_users(configuration.user_home)
    real_map = real_to_anon_user_map(configuration.user_home)
    for user in all_users:
        settings_path = os.path.join(configuration.user_settings,
                                     client_id_dir(user), settings_filename)
        profile_path = os.path.join(configuration.user_settings,
                                    client_id_dir(user), profile_filename)
        settings_mtime, profile_mtime = 0, 0
        if os.path.isfile(settings_path):
            settings_mtime = os.path.getmtime(settings_path)
        if os.path.isfile(profile_path):
            profile_mtime = os.path.getmtime(profile_path)

        if settings_mtime + profile_mtime > 0:
            conf_mtime = max(settings_mtime, profile_mtime)
            user_conf = get_user_conf(user, configuration)
        else:
            conf_mtime = -1
            user_conf = {}
        if conf_mtime >= map_stamp:
            vgrid_map[USERS][user] = user_conf
            vgrid_map[USERS][user][ASSIGN] = vgrid_map[USERS][user].get(ASSIGN,
                                                                        [])
            vgrid_map[USERS][user][ALLOW] = vgrid_map[USERS][user].get(ALLOW,
                                                                       [])
            public_id = user
            if user_conf.get('ANONYMOUS', True):
                public_id = real_map[user]
            vgrid_map[USERS][user][USERID] = public_id
            dirty[USERS] = dirty.get(USERS, []) + [user]
    # Remove any missing users from map
    missing_user = [user for user in vgrid_map[USERS].keys() \
                   if not user in all_users]
    for user in missing_user:
        del vgrid_map[USERS][user]
        dirty[USERS] = dirty.get(USERS, []) + [user]

    # Update list of mutually agreed vgrid participations for dirty users
    # and users assigned to dirty vgrids
    update_user = [i for i in dirty.get(USERS, []) if i not in MAP_SECTIONS]
    for (vgrid, changes) in vgrid_changes.items():
        old_owners, new_owners = changes.get(OWNERS, ([], []))
        old_members, new_members = changes.get(MEMBERS, ([], []))
        if old_owners == new_owners and old_members == new_members:
            configuration.logger.debug("skip user update of vgrid %s (%s)" % \
                                      (vgrid, changes))
            continue
        (old, new) = (old_owners + old_members, new_owners + new_members)
        for user in [i for i in vgrid_map[USERS].keys() \
                    if i not in update_user]:
            if vgrid_allowed(user, old) != vgrid_allowed(user, new):
                configuration.logger.info("update user vgrid %s for user %s" % \
                                          (vgrid, user))
                update_user.append(user)
    for user in [i for i in update_user if i not in missing_user]:
        allow = []
        for vgrid in vgrid_map[USERS][user][ASSIGN]:
            if vgrid_allowed(user, vgrid_map[VGRIDS][vgrid][OWNERS]) or \
                   vgrid_allowed(user, vgrid_map[VGRIDS][vgrid][MEMBERS]):
                allow.append(vgrid)
            # users implicitly assign all vgrids
            vgrid_map[USERS][user][ASSIGN] = allow
            vgrid_map[USERS][user][ALLOW] = allow

    if dirty:
        try:
            dump(vgrid_map, map_path)
        except Exception, exc:
            configuration.logger.error("Could not save vgrid map: %s" % exc)

    last_refresh[VGRIDS] = time.time()
    lock_handle.close()

    return vgrid_map

def get_user_map(configuration):
    """Returns the current map of users and their configurations. Caches the
    map for load prevention with repeated calls within short time span.
    """
    if last_load[USERS] + MAP_CACHE_SECONDS > time.time():
        configuration.logger.debug("using cached user map")
        return last_map[USERS]
    modified_users, modified_stamp_ = check_users_modified(configuration)
    if modified_users or last_load[USERS] <= 0:
        configuration.logger.info("refreshing user map (%s)" % modified_users)
        user_map = refresh_user_map(configuration)
        reset_users_modified(configuration)
        last_map[USERS] = user_map
    else:
        configuration.logger.debug("No changes - not refreshing")
        user_map, map_stamp = load_user_map(configuration)
        last_map[USERS] = user_map
        last_refresh[USERS] = map_stamp
    last_load[USERS] = time.time()
    return user_map

def get_resource_map(configuration):
    """Returns the current map of resources and their configurations. Caches the
    map for load prevention with repeated calls within short time span.
    """
    if last_load[RESOURCES] + MAP_CACHE_SECONDS > time.time():
        configuration.logger.debug("using cached resource map")
        return last_map[RESOURCES]
    modified_resources, modified_stamp_ = check_resources_modified(configuration)
    if modified_resources or last_load[RESOURCES] <= 0:
        configuration.logger.info("refreshing resource map (%s)" % modified_resources)
        resource_map = refresh_resource_map(configuration)
        reset_resources_modified(configuration)
        last_map[RESOURCES] = resource_map
    else:
        configuration.logger.debug("No changes - not refreshing")
        resource_map, map_stamp = load_resource_map(configuration)
        last_map[RESOURCES] = resource_map
        last_refresh[RESOURCES] = map_stamp
    last_load[RESOURCES] = time.time()
    return resource_map

def vgrid_inherit_map(configuration, vgrid_map):
    """Takes a vgrid_map and returns a copy extended with inherited values.
    That is, if the vgrid_map has vgrid A with owner John Doe all sub-vgrids
    A/B, A/B/C, A/M, etc. get their owner list set to include John Doe as well.
    """
    inherit_map = copy.deepcopy(vgrid_map)
    # Sort vgrids and extend participation from the end to keep it simple
    # and efficient
    all_vgrids = inherit_map[VGRIDS].keys()
    all_vgrids.sort()
    for vgrid_name in all_vgrids[::-1]:
        vgrid = inherit_map[VGRIDS][vgrid_name]
        for parent_name in vgrid_list_parents(vgrid_name, configuration):
            parent_vgrid = inherit_map[VGRIDS][parent_name]
            for field in (OWNERS, MEMBERS, RESOURCES):
                vgrid[field] += [i for i in parent_vgrid[field] if not i in \
                                 vgrid[field]]
    return inherit_map
                
def get_vgrid_map(configuration, recursive=True):
    """Returns the current map of vgrids and their configurations. Caches the
    map for load prevention with repeated calls within short time span.
    the recursive parameter is there to request extension of all sub-vgrids
    participation with inherited entities. The raw vgrid map only mirrors the
    direct participation.
    """
    if last_load[VGRIDS] + MAP_CACHE_SECONDS > time.time():
        configuration.logger.debug("using cached vgrid map")
        vgrid_map = last_map[VGRIDS]
    else:
        modified_vgrids, modified_stamp_ = check_vgrids_modified(configuration)
        if modified_vgrids or last_load[VGRIDS] <= 0:
            configuration.logger.info("refreshing vgrid map (%s)" % \
                                      modified_vgrids)
            vgrid_map = refresh_vgrid_map(configuration)
            reset_vgrids_modified(configuration)
            last_map[VGRIDS] = vgrid_map
        else:
            configuration.logger.debug("No changes - not refreshing")
            vgrid_map, map_stamp = load_vgrid_map(configuration)
            last_map[VGRIDS] = vgrid_map
            last_refresh[VGRIDS] = map_stamp
        last_load[VGRIDS] = time.time()
    if recursive:
        return vgrid_inherit_map(configuration, vgrid_map)
    else:
        return vgrid_map

def user_owned_res_confs(configuration, client_id):
    """Extract a map of resources that client_id owns.

    Returns a map from resource IDs to resource conf dictionaries.

    Resource IDs are anonymized unless explicitly configured otherwise, but
    the resource confs are always raw.
    """
    owned = {}
    resource_map = get_resource_map(configuration)

    # Map only contains the raw resource names - anonymize as requested

    anon_map = {}
    for res in resource_map.keys():
        anon_map[res] = resource_map[res][RESID]

    for (res_id, res) in resource_map.items():
        if vgrid_allowed(client_id, res[OWNERS]):
            owned[anon_map[res_id]] = res[CONF]
    return owned

def user_allowed_res_confs(configuration, client_id):
    """Extract a map of resources that client_id can really submit to.
    There is no guarantee that they will ever accept any further jobs.

    Returns a map from resource IDs to resource conf dictionaries.

    Resources are anonymized unless explicitly configured otherwise, but
    the resource confs are always raw.
    
    Please note that vgrid participation is a mutual agreement between vgrid
    owners and resource owners, so that a resource only truly participates
    in a vgrid if the vgrid *and* resource owners configured it so.
    """
    allowed = {}

    # Extend allowed_vgrids with any parent vgrids here to fit inheritance

    allowed_vgrids = user_allowed_vgrids(configuration, client_id,
                                         inherited=True)

    # Find all potential resources from vgrid sign up

    vgrid_map = get_vgrid_map(configuration)
    vgrid_map_res = vgrid_map[RESOURCES]
    resource_map = get_resource_map(configuration)

    # Map only contains the raw resource names - anonymize as requested

    anon_map = {}
    for res in vgrid_map_res.keys():
        anon_map[res] = vgrid_map_res[res][RESID]

    # Now select only the ones that actually still are allowed for that vgrid

    for (res, all_exes) in vgrid_map_res.items():
        shared = [i for i in all_exes[ALLOW] if i in allowed_vgrids]
        if not shared:
            continue
        allowed[anon_map[res]] = resource_map.get(res, {CONF: {}})[CONF]
    return allowed


def user_visible_res_confs(configuration, client_id):
    """Extract a map of resources that client_id owns or can submit jobs to.
    This is a wrapper combining user_owned_res_confs and
    user_allowed_res_confs.

    Returns a map from resource IDs to resource conf dictionaries.
    
    Resource IDs are anonymized unless explicitly configured otherwise, but
    the resource confs are always raw.
    """
    visible = user_allowed_res_confs(configuration, client_id)
    visible.update(user_owned_res_confs(configuration, client_id))
    return visible

def user_owned_res_exes(configuration, client_id):
    """Extract a map of resources that client_id owns.

    Returns a map from resource IDs to lists of exe node names.

    Resource IDs are anonymized unless explicitly configured otherwise.
    """
    owned = {}
    owned_confs = user_owned_res_confs(configuration, client_id)
    for (res_id, res) in owned_confs.items():
        owned[res_id] = [exe["name"] for exe in res["EXECONFIG"]]
    return owned

def user_allowed_res_exes(configuration, client_id):
    """Extract a map of resources that client_id can really submit to.
    There is no guarantee that they will ever accept any further jobs.

    Returns a map from resource IDs to lists of exe node names.

    Resource IDs are anonymized unless explicitly configured otherwise.
    
    Please note that vgrid participation is a mutual agreement between vgrid
    owners and resource owners, so that a resource only truly participates
    in a vgrid if the vgrid *and* resource owners configured it so.
    """
    allowed = {}

    # Extend allowed_vgrids with any parent vgrids here to fit inheritance

    allowed_vgrids = user_allowed_vgrids(configuration, client_id,
                                         inherited=True)

    # Find all potential resources from vgrid sign up

    vgrid_map = get_vgrid_map(configuration)
    vgrid_map_res = vgrid_map[RESOURCES]

    # Map only contains the raw resource names - anonymize as requested

    anon_map = {}
    for res in vgrid_map_res.keys():
        anon_map[res] = vgrid_map_res[res][RESID]

    # Now select only the ones that actually still are allowed for that vgrid

    for (res, all_exes) in vgrid_map_res.items():
        shared = [i for i in all_exes[ALLOW] if i in allowed_vgrids]
        if not shared:
            continue
        match = []
        for exe in [i for i in all_exes.keys() if i not in RES_SPECIALS]:
            if [i for i in shared if i in all_exes[exe]]:
                match.append(exe)
        allowed[anon_map[res]] = match
    return allowed

def user_visible_res_exes(configuration, client_id):
    """Extract a map of resources that client_id owns or can submit jobs to.
    This is a wrapper combining user_owned_res_exes and
    user_allowed_res_exes.

    Returns a map from resource IDs to resource exe node names.
    
    Resource IDs are anonymized unless explicitly configured otherwise.
    """
    visible = user_allowed_res_exes(configuration, client_id)
    visible.update(user_owned_res_exes(configuration, client_id))
    return visible

def user_allowed_user_confs(configuration, client_id):
    """Extract a map of users that client_id can really view and maybe
    contact.

    Returns a map from user IDs to lists of user confs.

    User IDs are anonymized unless explicitly configured otherwise.
    """
    allowed = {}
    allowed_vgrids = user_allowed_vgrids(configuration, client_id)

    # Find all potential users from vgrid member and ownership

    user_map = get_user_map(configuration)

    # Map only contains the raw user names - anonymize as requested

    anon_map = {}
    for user in user_map.keys():
        anon_map[user] = user_map[user][USERID]

    # Now select only the ones that actually still are allowed for that vgrid

    for (user, conf) in user_map.items():
        allowed[anon_map[user]] = conf
    return allowed

def user_visible_user_confs(configuration, client_id):
    """Extract a map of users that client_id is allowed to view or contact.

    Returns a map from user IDs to user conf dictionaries.
    
    User IDs are anonymized unless explicitly configured otherwise, but
    the user confs are always raw.
    """
    visible = user_allowed_user_confs(configuration, client_id)
    return visible

def resources_using_re(configuration, re_name):
    """Find resources implementing the re_name runtime environment.

    Resources are anonymized unless explicitly configured otherwise.
    """
    resources = []
    resource_map = get_resource_map(configuration)

    # Map only contains the raw resource names - anonymize as requested

    anon_map = {}
    for res in resource_map.keys():
        anon_map[res] = resource_map[res][RESID]
    for (res_id, res) in resource_map.items():
        for env in resource_map[res_id][CONF]['RUNTIMEENVIRONMENT']:
            if env[0] == re_name:
                resources.append(anon_map[res_id])
    return resources

def unmap_resource(configuration, res_id):
    """Remove res_id from resource and vgrid maps - simply force refresh"""
    mark_resource_modified(configuration, res_id)
    mark_vgrid_modified(configuration, res_id)

def unmap_vgrid(configuration, vgrid_name):
    """Remove vgrid_name from vgrid map - simply force refresh"""
    mark_vgrid_modified(configuration, vgrid_name)

def unmap_inheritance(configuration, vgrid_name, cert_id):
    """Remove cert_id inherited access to all vgrid_name sub vgrids: Simply
    force refresh of those vgrids as cert_id was never really there.
    """
    (status, sub_vgrids) = vgrid_list_subvgrids(vgrid_name, configuration)
    for sub in sub_vgrids:
        mark_vgrid_modified(configuration, sub)
    

if "__main__" == __name__:
    import sys
    from shared.conf import get_configuration_object
    user_id = 'anybody'
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    runtime_env = 'PYTHON'
    if len(sys.argv) > 2:
        runtime_env = sys.argv[2]
    conf = get_configuration_object()
    res_map = get_resource_map(conf)
    print "raw resource map: %s" % res_map
    all_resources = res_map.keys()
    print "raw resource IDs: %s" % ', '.join(all_resources)
    all_anon = [res_map[i][RESID] for i in all_resources]
    print "raw anon names: %s" % ', '.join(all_anon)
    print
    user_map = get_user_map(conf)
    print "raw user map: %s" % user_map
    all_users = user_map.keys()
    print "raw user IDs: %s" % ', '.join(all_users)
    all_anon = [user_map[i][USERID] for i in all_users]
    print "raw anon names: %s" % ', '.join(all_anon)
    print
    full_map = get_vgrid_map(conf)
    print "raw vgrid map: %s" % full_map
    all_resources = full_map[RESOURCES].keys()
    print "raw resource IDs: %s" % ', '.join(all_resources)
    all_users = full_map[USERS].keys()
    print "raw user IDs: %s" % ', '.join(all_users)
    all_vgrids = full_map[VGRIDS].keys()
    print "raw vgrid names: %s" % ', '.join(all_vgrids)
    print
    user_access_exes = user_allowed_res_exes(conf, user_id)
    user_access_confs = user_allowed_res_confs(conf, user_id)
    print "%s can access: %s" % \
          (user_id, ', '.join(["%s: %s" % (i, j) for (i, j) \
                               in user_access_exes.items()]))
    user_owned_exes = user_owned_res_exes(conf, user_id)
    user_owned_confs = user_owned_res_confs(conf, user_id)
    print "%s owns: %s" % \
          (user_id, ', '.join(["%s" % i for i in \
                               user_owned_confs.keys()]))
    user_visible_exes = user_visible_res_exes(conf, user_id)
    user_visible_confs = user_visible_res_confs(conf, user_id)
    user_visible_users = user_visible_user_confs(conf, user_id)
    print "%s can view: %s" % \
          (user_id, ', '.join([i for i in user_visible_exes.keys()]))
    print "full access exe dicts for %s:\n%s\n%s\n%s" % \
          (user_id, user_access_exes, user_owned_exes, user_visible_exes)
    print "full access conf dicts for %s:\n%s\n%s\n%s" % \
          (user_id, user_access_confs, user_owned_confs, user_visible_confs)
    print "%s can view: %s" % \
          (user_id, ', '.join([i for i in user_visible_users.keys()]))
    re_resources = resources_using_re(conf, runtime_env)
    print "%s in use on resources: %s" % \
          (runtime_env, ', '.join([i for i in re_resources]))
    direct_map = get_vgrid_map(conf, recursive=False)
    print "direct vgrid map vgrids: %s" % direct_map[VGRIDS]
    inherited_map = get_vgrid_map(conf, recursive=True)
    print "inherited vgrid map vgrids: %s" % inherited_map[VGRIDS]
