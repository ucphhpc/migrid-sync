#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# dashboard - [insert a few words of module description on this line]
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

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.cgiscriptstub import run_cgi_script

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

    welcomeTitle = 'Welcome <b>%s</b>' % cert_name_no_spaces.replace('_', ' ')
    welcomeText =   '<p>To the Minimum Intrusion GRID.</p>' +\
                    '<p><i>"This is your last chance.<br />' +\
                  'After this, there is no turning back.<br />' +\
    'You take the blue pill - the story ends, you wake up in your bed and believe whatever you want to believe.<br />'+\
    'You take the red pill - you stay in Wonderland and I show you how deep the rabbit-hole of grid-computing goes".</i><br /><b>quote</b>: MiG / Morpheus</p>' 

    helpText = 'For help go to the google group <a href="http://groups.google.com/group/migrid">http://groups.google.com/group/migrid</a><br />' +\
                '<p>The group is an open forum for users and developers of MiG.</p> '+\
                '<p>It is used for anything from support questions to discussions '+\
                'related to the development of the middleware.</p>'

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Dashboard'})
    output_objects.append({'object_type': 'header', 'text' : 'MiG Dashboard'})
    
    output_objects.append({'object_type': 'sectionheader', 'text' : welcomeTitle })
    output_objects.append({'object_type': 'text', 'text'
                              : welcomeText
                              })

    output_objects.append({'object_type': 'sectionheader', 'text' : 'Help'})
    output_objects.append({'object_type': 'text', 'text'
                              : helpText
                              })

    return (output_objects, status)
  
cgitb.enable()
run_cgi_script(main)
