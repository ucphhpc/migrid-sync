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
import fcntl

from shared.conf import get_all_exe_vgrids, get_resource_fields
from shared.resource import list_resources, anon_resource_id
from shared.serial import load, dump
from shared.vgrid import vgrid_list_vgrids, vgrid_allowed, vgrid_resources, \
     default_vgrid, user_allowed_vgrids

MAP_SECTIONS = (RESOURCES, VGRIDS) = ("__resources__", "__vgrids__")
RES_SPECIALS = (ALLOW, ASSIGN, RESID) = \
               ('__allow__', '__assign__', '__resid__')

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
        dirty[VGRIDS] = dirty.get(VGRIDS, []) + [VGRIDS]
    if not vgrid_map.has_key(RESOURCES):
        old_map = vgrid_map
        vgrid_map = {}
        vgrid_map[RESOURCES] = old_map
        dirty[RESOURCES] = dirty.get(RESOURCES, []) + [RESOURCES]

    # Find all vgrids and their resources allowed

    (status, all_vgrids) = vgrid_list_vgrids(configuration)
    if not status:
        all_vgrids = []
    for vgrid in all_vgrids:
        conf_path = os.path.join(configuration.vgrid_home, vgrid, "resources")
        if not os.path.isfile(conf_path):
            continue
        if os.path.getmtime(conf_path) >= map_stamp:
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
    
    all_resources = list_resources(configuration.resource_home)
    for res in all_resources:
        # Sandboxes do not change their vgrid participation
        if vgrid_map[RESOURCES].has_key(res) and \
               (res.startswith('sandbox.') or \
                res.startswith('oneclick.')):
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
                assigned += [i for i in exe_vgrids if i not in assigned]
            vgrid_map[RESOURCES][res][ASSIGN] = assigned
            vgrid_map[RESOURCES][res][ALLOW] = vgrid_map[RESOURCES][res].get(ALLOW, [])
            public_id = res
            if get_resource_fields(res, ['ANONYMOUS']).get('ANONYMOUS', True):
                public_id = anon_resource_id(public_id)
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
    for res in [i for i in update_res]:
        allow = []
        for vgrid in vgrid_map[RESOURCES][res][ASSIGN]:
            if vgrid_allowed(res, vgrid_map[VGRIDS][vgrid]):
                allow.append(vgrid)
            vgrid_map[RESOURCES][res][ALLOW] = allow

    if dirty:
        try:
            dump(vgrid_map, map_path)
            map_stamp = os.path.getmtime(map_path)
        except Exception, exc:
            configuration.logger.error("Could not save vgrid map: %s" % exc)

    lock_handle.close()

    return vgrid_map

def user_allowed_resources(configuration, client_id):
    """Extract a list of resources that client_id can really submit to.
    There is no guarantee that they will ever accept any further jobs.

    Resources are anonymized unless explicitly specifying otherwise.
    
    Please note that vgrid participation is a mutual agreement between vgrid
    owners and resource owners, so that a resource only truly participates
    in a vgrid if the vgrid *and* resource owners configured it so.
    """
    allowed = {}
    allowed_vgrids = user_allowed_vgrids(configuration, client_id)

    # Find all potential resources from vgrid sign up

    vgrid_map = refresh_vgrid_map(configuration)
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

if "__main__" == __name__:
    import sys
    from shared.conf import get_configuration_object
    user_id = 'anybody'
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    conf = get_configuration_object()
    full_map = refresh_vgrid_map(conf)
    print "raw vgrid map: %s" % full_map
    all_resources = full_map[RESOURCES].keys()
    print "raw resource IDs: %s" % ', '.join(all_resources)
    all_vgrids = full_map[VGRIDS].keys()
    print "raw vgrid names: %s" % ', '.join(all_vgrids)
    user_access = user_allowed_resources(conf, user_id)
    print "%s can access: %s" % \
          (user_id, ', '.join(["%s: %s" % (i, j) for (i, j) \
                               in user_access.items()]))
