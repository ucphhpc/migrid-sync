#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# base - shared base helper functions
# Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter
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

"""Base helper functions"""

# IMPORTANT: do not import any other MiG modules here - to avoid import loops
from shared.defaults import sandbox_names


def client_id_dir(client_id):
    """Map client ID to a valid directory name:
    client_id is a distinguished name on the form /X=ab/Y=cdef ghi/Z=klmn...
    so we just replace slashes with plus signs and space with underscore
    to avoid file system problems.
    """

    return client_id.replace('/', '+').replace(' ', '_')

# TODO: old_id_format should be eliminated after complete migration to full DN

def old_id_format(client_id):
    """Map client ID to the old underscore CN only ID:
    client_id is a distinguished name on the form /X=ab/Y=cdef ghi/CN=klmn...
    so we just extract the CN field and replace space with underscore.
    """

    try:
        old_id = client_id.split('/CN=', 1)[1]
        old_id = old_id.split('/', 1)[0]
        return old_id.replace(' ', '_')
    except:
        return client_id

def sandbox_resource(unique_resource_name):
    """Returns boolean indicating if the resource is a sandbox"""
    fqdn = unique_resource_name.rsplit('.', 1)[0]
    return fqdn in sandbox_names
