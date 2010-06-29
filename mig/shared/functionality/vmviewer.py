#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vmachines_connect - [insert a few words of module description on this line]
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
import os, sys, cgi, cgitb, md5

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert
from shared.cgiscriptstub import run_cgi_script
from shared import vms # Yeah this is the shit!
import ConfigParser
#from shared.functionality.submitjob import main

def signature():
  defaults = {'flags': [''], 'path': ['.']}
  return ['dir_listings', defaults]

def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(cert_name_no_spaces, op_header=False, op_title=False)

    status = returnvalues.OK
    defaults = {'resource' : [''], 
                    'width' : [''], 
                    'height' : [''] }
    
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        cert_name_no_spaces,
        configuration,
        allow_rejects=False,
        )
    
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Virtual Desktop'})
    
    vm_id = accepted['resource'][0]
    width = int(accepted['width'][0])
    height = int(accepted['height'][0])

    config_file_path = os.path.join(configuration.vm_home, vm_id, "vm.conf")
    if not os.path.exists(config_file_path):
        output_objects.append({'object_type': 'text', 'text'
                          : 'Cannot find config file'})
        return (output_objects, returnvalues.ERROR)
        
    vm_config = ConfigParser.ConfigParser()
    vm_config.read(config_file_path)
    url = vm_config.get('VNC', 'url')
    passw = vm_config.get('VNC', 'pass')
    port = vm_config.getint('VNC', 'port')
    applet_url = "http://"+configuration.server_fqdn
    output_objects.append({'object_type': 'html_form', 'text': vms.generate_vnc_applet_tag(url, applet_url, port, 80, width, height, passw)
                              })
    return (output_objects, status)
    