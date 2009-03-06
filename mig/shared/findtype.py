#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# findtype - [insert a few words of module description on this line]
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

"""Entity check"""

import os
from string import letters, digits

from shared.listhandling import is_item_in_pickled_list

VALID_FQDN_CHARACTERS = letters + digits + ".-"
MIG_SERVER_ID = "MiG-Server"

def is_user(cert_name, user_home):
    """loop though user_home and find out if a matching directory
    is found"""
    if cert_name.strip() == "":
        return False
    cert_upper = cert_name.upper()
    dir_list = os.listdir(user_home)
    for dir_entry in dir_list:
        if dir_entry.upper() == cert_upper:
            #print "Cert found as a User cert!"
            return True
    return False
    
def is_server(cert_name, server_home, local=False):
    """Check that cert_name is a valid FQDN and make sure that
    org_unit matches a predefined MiG server ID string.
    When called from a basic cgi handler all IO must remain local
    to avoid loops. Thus the optional local flag is available.
    """
    cert_lower = cert_name.lower()
    for char in cert_lower:
        if not char in VALID_FQDN_CHARACTERS:
            return False
    # print "Cert found as a Server cert!"
    return True                                        
    
def is_resource(cert_name, resource_home):
    """loop though resource_home and find out if a matching
    directory is found"""
    cert_upper = cert_name.upper()
    dir_list = os.listdir(resource_home)
    for dir_entry in dir_list:
        # print dir_entry.upper() + "==" + cert_upper
        if dir_entry.upper().strip() == cert_upper.strip():
            # print "Cert found as a Resource cert!"
            return True
    return False

def is_owner(cert_no_spaces, unique_config_name, config_home, logger):
    config_file = os.path.abspath(config_home) + os.sep + unique_config_name + os.sep + "owners"
    # Check validity of unique_config_name
    if os.path.abspath(config_file) <> config_file:
        # Extract caller information
        from traceback import format_stack
        caller = (''.join(format_stack()[:-1])).strip()
        logger.warning("is_owner registered possible illegal directory traversal attempt by '%s': resource name '%s' (caller: %s)" % (cert_no_spaces, unique_config_name, caller))
        return False
    return is_item_in_pickled_list(config_file, cert_no_spaces, logger)
