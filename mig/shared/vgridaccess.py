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


from shared.conf import get_all_exe_vgrids
from shared.resource import list_resources
from shared.vgrid import user_allowed_vgrids, vgrid_match_resources


def user_allowed_resources(configuration, client_id):
    """Extract a list of resources that client_id can submit to.
    There is no guarantee that they will ever accept any further jobs.
    
    Please note that vgrid participation is a mutual agreement between vgrid
    owners and resource owners, so that a resource only truly participates
    in a vgrid if the vgrid *and* resource owners configured it so.
    """
    allowed = []
    vgrid_map = {}
    allowed_vgrids = user_allowed_vgrids(configuration, client_id)

    # Find all potential resources from vgrid sign up

    # TODO: add caching to this expensive vgrid map lookup
    # Save map to pickle and only update entries if resource config
    # timestamp changed since pickle timestamp

    all_resources = list_resources(configuration.resource_home)
    for res in all_resources:
        vgrid_map[res] = get_all_exe_vgrids(res)
        total = []
        for exe_vgrids in vgrid_map[res].values():
            total += exe_vgrids
        vgrid_map[res]['all_exes'] = total

    # Now select only the ones that actually still are allowed for that vgrid

    for vgrid in allowed_vgrids:
        match = vgrid_match_resources(vgrid, all_resources, configuration)
        for res in match:
            if res in allowed:
                continue
            if vgrid in vgrid_map[res]['all_exes']:
                allowed.append(res)
    return allowed
