#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# findtype - Detect client entity type
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

"""Entity kind detection"""

import os
from string import letters, digits

from shared.listhandling import is_item_in_pickled_list
from shared.useradm import client_id_dir, old_id_format
from shared.validstring import valid_user_path

VALID_FQDN_CHARACTERS = letters + digits + '.-'
MIG_SERVER_ID = 'MiG-Server'


def is_user(entity_id, user_home):
    """Check if if a matching user home directory exists"""

    # TODO: lookup in user DB instead?

    if not entity_id:
        return False
    home_dir = os.path.join(user_home, client_id_dir(entity_id))
    if os.path.isdir(home_dir):
        return True
    return False


def is_server(entity_id, server_home, local=False):
    """Check that entity_id is a valid FQDN and make sure that
    org_unit matches a predefined MiG server ID string.
    When called from a basic cgi handler all IO must remain local
    to avoid loops. Thus the optional local flag is available.
    """

    entity_lower = entity_id.lower()
    for char in entity_lower:
        if not char in VALID_FQDN_CHARACTERS:
            return False

    # print "Cert found as a Server cert!"

    return True


def is_resource(entity_id, resource_home):
    """loop though resource_home and find out if a matching
    directory is found"""

    entity_upper = entity_id.upper()
    dir_list = os.listdir(resource_home)
    for dir_entry in dir_list:
        if dir_entry.upper().strip() == entity_upper.strip():
            return True
    return False


def is_owner(
    client_id,
    unique_config_name,
    config_home,
    logger,
    ):
    """Check that client_id is listed in pickled owners file"""
    config_path = os.path.abspath(os.path.join(config_home, unique_config_name,
                                               'owners'))

    # Check validity of unique_config_name

    if not valid_user_path(config_path, config_home):

        # Extract caller information

        from traceback import format_stack
        caller = ''.join(format_stack()[:-1]).strip()
        logger.warning("""is_owner caught possible illegal directory traversal attempt
by client: '%s'
unique name: '%s'

caller: %s""" % (client_id, unique_config_name, caller))
        return False
    return (is_item_in_pickled_list(config_path, client_id, logger) or \
            is_item_in_pickled_list(config_path, old_id_format(client_id), logger))


