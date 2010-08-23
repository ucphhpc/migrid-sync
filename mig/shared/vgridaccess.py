#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridaccess - User access in VGrids
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

"""User access to VGrids"""

import os
import time
import fcntl

from shared.base import sandbox_resource
from shared.conf import get_all_exe_vgrids, get_resource_fields, \
     get_resource_configuration
from shared.defaults import default_vgrid
from shared.resource import list_resources, real_to_anon_res_map
from shared.serial import load, dump
from shared.vgrid import vgrid_list_vgrids, vgrid_allowed, vgrid_resources, \
     user_allowed_vgrids

MAP_SECTIONS = (RESOURCES, VGRIDS) = ("__resources__", "__vgrids__")
RES_SPECIALS = (ALLOW, ASSIGN, RESID, OWNERS, CONF, MODTIME) = \
               ('__allow__', '__assign__', '__resid__', '__owners__',
                '__conf__', '__modtime__')

# Never repeatedly refresh maps within this number of seconds in same process
# Used to avoid refresh floods with e.g. runtime envs page calling
# refresh for each env when extracting providers.
MAP_CACHE_SECONDS = 30

last_refresh = {RESOURCES: 0, VGRIDS: 0}
last_map = {RESOURCES: {}, VGRIDS: {}}

def refresh_resource_map(configuration):
    """Refresh map of resources and their configuration. Uses a pickled
    dictionary for efficiency. 
    Resource IDs are stored in their raw (non-anonymized form).
    Only update map for resources that updated conf after last map save.
    """
    dirty = []
    map_path = os.path.join(configuration.resource_home, "resource.map")
    lock_path = os.path.join(configuration.resource_home, "resource.lock")
    lock_handle = open(lock_path, 'a')

    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    try:
        resource_map = load(map_path)
        map_stamp = os.path.getmtime(map_path)
    except IOError:
        configuration.logger.warn("No resource map to load - ok first time")
        resource_map = {}
        map_stamp = -1

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
            (status, res_conf) = get_resource_configuration(configuration.resource_home,
                                                  res, configuration.logger)
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
    """Refresh map of resources and their vgrid participation. Uses a pickled
    dictionary for efficiency. 
    Resource IDs are stored in their raw (non-anonymized form).
    Only update map for resources that updated conf after last map save.
    """
    dirty = {}
    vgrid_changes = {}
    map_path = os.path.join(configuration.resource_home, "vgrid.map")
    lock_path = os.path.join(configuration.resource_home, "vgrid.lock")
    lock_handle = open(lock_path, 'a')

    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    try:
        vgrid_map = load(map_path)
        map_stamp = os.path.getmtime(map_path)
    except IOError:
        configuration.logger.warn("No vgrid map to load - ok first time")
        vgrid_map = {RESOURCES: {}, VGRIDS: {default_vgrid: '*'}}
        map_stamp = -1

    # Temporary backwards compatibility - old format had resource ID's as keys
    if not vgrid_map.has_key(VGRIDS):
        vgrid_map[VGRIDS] = {default_vgrid: '*'}
        dirty[VGRIDS] = dirty.get(VGRIDS, []) + [default_vgrid]
    if not vgrid_map.has_key(RESOURCES):
        old_map = vgrid_map
        vgrid_map = {}
        vgrid_map[RESOURCES] = old_map
        dirty[RESOURCES] = dirty.get(RESOURCES, []) + old_map.keys()

    # Find all vgrids and their resources allowed

    (status, all_vgrids) = vgrid_list_vgrids(configuration)
    if not status:
        all_vgrids = []
    for vgrid in all_vgrids:
        conf_path = os.path.join(configuration.vgrid_home, vgrid, "resources")
        if not os.path.isfile(conf_path):
            continue
        if not vgrid_map[VGRIDS].has_key(vgrid) or \
               os.path.getmtime(conf_path) >= map_stamp:
            (status, resources) = vgrid_resources(vgrid, configuration)
            if not status:
                resources = []
            vgrid_changes[vgrid] = (vgrid_map[VGRIDS].get(vgrid, []), resources)
            vgrid_map[VGRIDS][vgrid] = resources
            dirty[VGRIDS] = dirty.get(VGRIDS, []) + [vgrid]
    # Remove any missing vgrids from map
    missing_vgrids = [vgrid for vgrid in vgrid_map[VGRIDS].keys() \
                   if not vgrid in all_vgrids]
    for vgrid in missing_vgrids:
        vgrid_changes[vgrid] = (vgrid_map[VGRIDS][vgrid], [])
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
    update_res = [i for i in dirty.get(RESOURCES, []) if i not in MAP_SECTIONS]
    for (vgrid, (old, new)) in vgrid_changes.items():
        for res in [i for i in vgrid_map[RESOURCES].keys() \
                    if i not in update_res]:
            if vgrid_allowed(res, old) != vgrid_allowed(res, new):
                update_res.append(res)
    for res in [i for i in update_res if i not in missing_res]:
        allow = []
        for vgrid in vgrid_map[RESOURCES][res][ASSIGN]:
            if vgrid_allowed(res, vgrid_map[VGRIDS][vgrid]):
                allow.append(vgrid)
            vgrid_map[RESOURCES][res][ALLOW] = allow

    if dirty:
        try:
            dump(vgrid_map, map_path)
        except Exception, exc:
            configuration.logger.error("Could not save vgrid map: %s" % exc)

    last_refresh[VGRIDS] = time.time()
    lock_handle.close()

    return vgrid_map

def get_resource_map(configuration):
    """Returns the current map of resources and their configurations"""
    if last_refresh[RESOURCES] + MAP_CACHE_SECONDS > time.time():
        resource_map = last_map[RESOURCES]
    else:
        resource_map = refresh_resource_map(configuration)
        last_map[RESOURCES] = resource_map
    return resource_map

def get_vgrid_map(configuration):
    """Returns the current map of resources and their vgrid participations"""
    if last_refresh[VGRIDS] + MAP_CACHE_SECONDS > time.time():
        vgrid_map = last_map[VGRIDS]
    else:
        vgrid_map = refresh_vgrid_map(configuration)
        last_map[VGRIDS] = vgrid_map
    return vgrid_map

def user_owned_resources(configuration, client_id):
    """Extract a list of resources that client_id owns.

    Resources are anonymized unless explicitly configured otherwise.
    """
    owned = {}
    resource_map = get_resource_map(configuration)

    # Map only contains the raw resource names - anonomize as requested

    anon_map = {}
    for res in resource_map.keys():
        anon_map[res] = resource_map[res][RESID]

    for (res_id, res) in resource_map.items():
        if vgrid_allowed(client_id, res[OWNERS]):
            owned[anon_map[res_id]] = res
    return owned

def user_allowed_resources(configuration, client_id):
    """Extract a list of resources that client_id can really submit to.
    There is no guarantee that they will ever accept any further jobs.

    Resources are anonymized unless explicitly configured otherwise.
    
    Please note that vgrid participation is a mutual agreement between vgrid
    owners and resource owners, so that a resource only truly participates
    in a vgrid if the vgrid *and* resource owners configured it so.
    """
    allowed = {}
    allowed_vgrids = user_allowed_vgrids(configuration, client_id)

    # Find all potential resources from vgrid sign up

    vgrid_map = get_vgrid_map(configuration)
    map_resources = vgrid_map[RESOURCES]

    # Map only contains the raw resource names - anonomize as requested

    anon_map = {}
    for res in map_resources.keys():
        anon_map[res] = map_resources[res][RESID]

    # Now select only the ones that actually still are allowed for that vgrid

    for (res, all_exes) in map_resources.items():
        shared = [i for i in all_exes[ALLOW] if i in allowed_vgrids]
        if not shared:
            continue
        match = []
        for exe in [i for i in all_exes.keys() if i not in RES_SPECIALS]:
            if [i for i in shared if i in all_exes[exe]]:
                match.append(exe)
        if res in allowed:
            continue
        allowed[anon_map[res]] = match
    return allowed

def user_visible_resources(configuration, client_id):
    """Extract a list of resources that client_id owns or can submit jobs to.
    This is a wrapper combining user_owned_resources and
    user_allowed_resources.
    
    Resources are anonymized unless explicitly configured otherwise.
    """
    visible = user_allowed_resources(configuration, client_id)
    visible.update(user_owned_resources(configuration, client_id))
    return visible

def resources_using_re(configuration, re_name):
    """Find resources implementing the re_name runtime environment.

    Resources are anonymized unless explicitly configured otherwise.
    """
    resources = []
    resource_map = get_resource_map(configuration)

    # Map only contains the raw resource names - anonomize as requested

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
    refresh_resource_map(configuration)
    refresh_vgrid_map(configuration)


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
    full_map = get_vgrid_map(conf)
    print "raw vgrid map: %s" % full_map
    all_resources = full_map[RESOURCES].keys()
    print "raw resource IDs: %s" % ', '.join(all_resources)
    all_vgrids = full_map[VGRIDS].keys()
    print "raw vgrid names: %s" % ', '.join(all_vgrids)
    print
    user_access = user_allowed_resources(conf, user_id)
    print "%s can access: %s" % \
          (user_id, ', '.join(["%s: %s" % (i, j) for (i, j) \
                               in user_access.items()]))
    user_owned = user_owned_resources(conf, user_id)
    print "%s owns: %s" % \
          (user_id, ', '.join(["%s: %s" % (i, j[MODTIME]) for (i, j) \
                               in user_owned.items()]))
    user_visible = user_visible_resources(conf, user_id)
    print "%s can view: %s" % \
          (user_id, ', '.join([i for i in user_visible.keys()]))
    re_resources = resources_using_re(conf, runtime_env)
    print "%s in use on resources: %s" % \
          (runtime_env, ', '.join([i for i in re_resources]))
