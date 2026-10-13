# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# permissions - permission checks for peers management
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Permission checks for peers management."""

import re


def peers_prefilter_allowed(configuration, user_dict):
    """Check if user with user_dict is potentially allowed to manage peers
    soleley based on optional configuration prefilter.
    Please use peers_permit_allowed too before actually allowing user as peer.
    """
    for key, val in configuration.site_peers_prefilter:
        if not re.match(val, user_dict.get(key, "NO SUCH FIELD")):
            return False
    return True


def peers_permit_allowed(configuration, user_dict):
    """Check if user with user_dict is allowed to manage peers based on
    optional configuration limits.
    """
    for key, val in configuration.site_peers_permit:
        if not re.match(val, user_dict.get(key, "NO SUCH FIELD")):
            return False
    return True


def prefilter_potential_peers(peers_list, configuration):
    """Return entries from peers_list that fit local prefilter policy"""
    potential_peers = []
    for peer_dict in peers_list:
        if peers_prefilter_allowed(configuration, peer_dict):
            potential_peers.append(peer_dict)
    return potential_peers
