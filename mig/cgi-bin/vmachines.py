#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# submitjob - [insert a few words of module description on this line]
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
import os
import sys
import cgi
import cgitb
import glob

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.cgiscriptstub import run_cgi_script
from shared.validstring import valid_user_path
from shared.html import renderMenu
from shared import vms # Yeah this is the shit!

#from shared.functionality.submitjob import main

def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)

    status = returnvalues.OK
    defaults = {}
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


    menu_items  = (
                        {
                        'class'    : 'vmachines add',
                        'url'       : 'vmachines_create.py',
                        'title'     : 'Request Virtual Machine',
                        'attr' : ''
                        
                        }             ,
                        #{
                        #'class'    : 'vmachines connect',
                        #'url'       : '#',
                        #'title'     : 'Connect to remote access service',
                        #'attr'  : 'onClick="vncClientPopup(); return false;"'
                        #},
                  )

    # Html fragments
    submenu = renderMenu('navsubmenu', menu_items)

    welcomeText     = 'Welcome to MiG virtual machine management!'
    descriptionText = '<p>In this part of MiG you can: <ul>'+\
                      '<li>See your virtual machines in the list below.</li>'+\
                      '<li>Start, stop and connect to your Virtual Machine</li>'+\
                      '<li>Request Virtual Machines, by clicking on the button above</li>'+\
                      '</ul></p>'
                          
    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Virtual Machines'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Virtual Machines'})
    output_objects.append({'object_type': 'text', 'text': submenu })
    output_objects.append({'object_type': 'text', 'text'
                              : '<p>&nbsp;</p>'
                              })
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : welcomeText
                          })    
    output_objects.append({'object_type': 'text', 'text': descriptionText})
    
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Your machines:'
                          })
    
    # List the machines here
    
    # Grab the vms available for the user
    machines = vms.vms_list(configuration, cert_name_no_spaces)
        
    if len(machines)>0:
        
        # Create a pretty list with start/stop/connect links
        pretty_machines = '<table style="border: 0; background: none;"><tr>'
        side_by_side = 3 # How many machines should be shown in a row?
                
        col = 0;
        for machine in machines:
            
            # Machines on a row
            if col % side_by_side == 0:
                pretty_machines += "</tr><tr>"
            col += 1;
                        
            # Html format machine specifications in a fieldset
            specs = "<fieldset><legend>Specs:</legend><ul><li>Ram: %s</li><li>State: %s</li></ul></fieldset>" % (machine['specs'], machine['state'])

            # Smack all the html together
            pretty_machines += "<td style=\"vertical-align: top;\"><fieldset><legend>%s</legend><img src=\"/images/vms/vm_off.jpg\"> %s </fieldset></td>" % (machine['name'], specs)
        
        pretty_machines += "</tr></table>"
        
        output_objects.append({'object_type': 'text', 'text'
                              : pretty_machines
                              })
    else:        
        output_objects.append({'object_type': 'text', 'text'
                              : "You don't have any virtual machines! Click 'Request Virtual Machine' to become a proud owner :)"
                              })
        
    #output_objects.append({'object_type': 'text', 'text'
    #                          : vms.popup_snippet() + vms.vnc_applet('amigos18.diku.dk', 8111, 8114, 1024, 768, 'leela')
    #                          })

    return (output_objects, status)

cgitb.enable()
run_cgi_script(main)