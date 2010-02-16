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
import time

from shared.conf import get_all_exe_vgrids, get_resource_fields
from shared.resource import list_resources, anon_resource_id
from shared.serial import load, dump
from shared.vgrid import user_allowed_vgrids, vgrid_match_resources


def refresh_vgrid_map(configuration):
    """Refresh map of resources and their vgrid participation. Uses a pickled
    dictionary for efficiency. 
    Resource IDs are stored in their raw (non-anonymized form).
    Only update map for resources that updated conf after last map save.
    """
    dirty = False
    map_path = os.path.join(configuration.resource_home, "vgrid.map")
    lock_path = os.path.join(configuration.resource_home, "vgrid.lock")
    lock_handle = open(lock_path, 'a')

    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    try:
        vgrid_map = load(map_path)
        map_stamp = os.path.getmtime(map_path)
    except IOError:
        configuration.logger.warn("No vgrid map to load - ok first time")
        vgrid_map = {}
        map_stamp = -1
    
    all_resources = list_resources(configuration.resource_home)
    for res in all_resources:
        # Sandboxes do not change their vgrid participation
        if vgrid_map.has_key(res) and (res.startswith('sandbox.') or \
                                       res.startswith('oneclick.')):
            continue
        conf_path = os.path.join(configuration.resource_home, res, "config")
        if not os.path.isfile(conf_path):
            continue
        if os.path.getmtime(conf_path) >= map_stamp:
            vgrid_map[res] = get_all_exe_vgrids(res)
            total = []
            for exe_vgrids in vgrid_map[res].values():
                total += exe_vgrids
            vgrid_map[res]['all_exes'] = total
            dirty = True

    if dirty:
        try:
            dump(vgrid_map, map_path)
            map_stamp = os.path.getmtime(map_path)
        except Exception, exc:
            configuration.logger.error("Could not save vgrid map: %s" % exc)

    lock_handle.close()

    vgrid_map['time_stamp'] = map_stamp
    return vgrid_map

def user_allowed_resources(configuration, client_id):
    """Extract a list of resources that client_id can submit to.
    There is no guarantee that they will ever accept any further jobs.

    Resources are anonymized unless explicitly specifying otherwise.
    
    Please note that vgrid participation is a mutual agreement between vgrid
    owners and resource owners, so that a resource only truly participates
    in a vgrid if the vgrid *and* resource owners configured it so.
    """
    allowed = []
    vgrid_map = {}
    allowed_vgrids = user_allowed_vgrids(configuration, client_id)

    # Find all potential resources from vgrid sign up

    vgrid_map = refresh_vgrid_map(configuration)
    # TODO: use map_stamp?
    map_stamp = vgrid_map['time_stamp']
    del vgrid_map['time_stamp']
    
    # Map only contains the raw resource names - anonomize as requested

    anon_map = {}
    for res in vgrid_map.keys():
        public_id = res
        if get_resource_fields(res, ['ANONYMOUS']).get('ANONYMOUS', True):
            public_id = anon_resource_id(public_id)
        anon_map[public_id] = res

    # Now select only the ones that actually still are allowed for that vgrid

    for vgrid in allowed_vgrids:
        match = vgrid_match_resources(vgrid, anon_map.keys(), configuration)
        for pub in match:
            if pub in allowed:
                continue
            if vgrid in vgrid_map[anon_map[pub]]['all_exes']:
                allowed.append(pub)
    return allowed

if "__main__" == __name__:
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    all_vgrids = refresh_vgrid_map(conf)
    print "raw vgrid map: %s" % all_vgrids
    all_resources = all_vgrids.keys()
    print "raw resource IDs: %s" % ', '.join(all_resources)
    anybody_access = user_allowed_resources(conf, 'anybody')
    print "Anybody can access: %s" % ', '.join(anybody_access)
