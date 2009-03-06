#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cleanfe - [insert a few words of module description on this line]
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

import cgi
import os
import sys

from shared.findtype import is_owner
from shared.resadm import clean_resource_frontend, stop_resource_frontend
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues

def signature():
    defaults = {'unique_resource_name':REJECT_UNSET}
    return ["text", defaults]
    
def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""
    configuration, logger, output_objects, op_name = initialize_main_variables()
    output_objects.append({"object_type": "text", "text":"--------- Trying to Clean front end ----------"})
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(user_arguments_dict, defaults, output_objects, cert_name_no_spaces, configuration, allow_rejects = False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    
    unique_resource_name = (accepted['unique_resource_name'])[-1]
    
    if not is_owner(cert_name_no_spaces, unique_resource_name, configuration.resource_home, logger):
        output_objects.append({"object_type":"error_text", "text":"Failure: You must be an owner of " + unique_resource_name + " to clean the front end!"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    exit_status = returnvalues.OK
    (status, msg) = stop_resource_frontend(unique_resource_name, configuration, logger)
    if not status:
        output_objects.append({"object_type":"error_text", "text": "Problems stopping front end during clean: %s" % msg})
        o.client(o.CLIENT_ERROR)
                        
    (status2, msg2) = clean_resource_frontend(unique_resource_name, configuration.resource_home, logger)
    if not status2:
        output_objects.append({"object_type":"error_text", "text": "Problems cleaning front end during clean: %s" % msg2})
        exit_status = returnvalues.SYSTEM_ERROR
    if status and status2:
        output_objects.append({"object_type":"text", "text":"Clean front end success: Stop output: %s Clean output %s" % (msg, msg2)})
   
    return (output_objects, exit_status)
