#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vmviewer - Virtual machine client based on the tightVNC applet
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

import os
import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert
import ConfigParser

def generate_vnc_applet(vm_host, proxy_host, vm_port, width, height, password):
    """Return an html applet tag."""
    applet = """<APPLET CODE="vncviewer" ARCHIVE="vncviewer.jar" """
    applet += " CODEBASE=\"%s/vnc/\"" % proxy_host
    applet += " WIDTH=%d HEIGHT=%d >" % (width, height)
    applet += "<PARAM NAME=\"PORT\" VALUE=\"%d\">" % vm_port
    applet += "<PARAM NAME=\"PASSWORD\" VALUE=\"%s\">" % (password)
    applet += "<PARAM NAME=\"HOST\" VALUE=\"%s\">" % vm_host 
    applet += "<PARAM NAME=\"ENCODING\" VALUE=\"Auto\">"  
    applet += "<PARAM NAME=\"Scaling factor\" VALUE=\"120\">" 
    applet += "<PARAM NAME=\"Show controls\" VALUE=\"no\">"  
  
    applet += "</APPLET>"
  
    return applet

def signature():
    defaults = {'resource' : [''], 
                    'width' : [''], 
                    'height' : [''] }
                    
    return ['', defaults]

def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(cert_name_no_spaces, op_header=False, op_title=False)

    status = returnvalues.OK
    defaults = signature()[1]
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

    # look up needed information about VM in the config file

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
    output_objects.append({'object_type': 'html_form', 'text': generate_vnc_applet(url, applet_url, port, width, height, passw)
                              })
    return (output_objects, status)
    