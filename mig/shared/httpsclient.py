#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# httpsclient - Shared functions for all HTTPS clients
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Common HTTPS client functions for e.g. access control"""

import os

# All HTTPS clients coming through apache will have their unique
# certificate distinguished name available in this field

client_id_field = 'SSL_CLIENT_S_DN'

# Login based clients like OpenID ones will instead have their REMOTE_USER env
# set to some ID provided by the authenticator. In that case look up mapping
# to native user

client_login_field = 'REMOTE_USER'

def extract_client_id(id_map=None):
    """Extract unique user ID from HTTPS or REMOTE_USER Login environment"""

    distinguished_name = os.environ.get(client_id_field, '').strip()
    if id_map and not distinguished_name:
        lookup_login = os.environ.get(client_login_field, 'NOSUCHUSER').strip()
        distinguished_name = id_map.get(lookup_login, '')
    return distinguished_name


