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

    applet = """<APPLET CODE="VncViewer" ARCHIVE="VncViewer.jar" CODEBASE="http://amigos18.diku.dk:8114/tightvnc/" WIDTH="1024" HEIGHT="800"><PARAM NAME="PORT" VALUE="8111"><PARAM NAME="Encoding" VALUE="Raw"></APPLET>"""
    
    popup = """
    <script>
    function vncClientPopup() {
    var win = window.open("", "win", "menubar=no,toolbar=no");
    
    win.document.open("text/html", "replace");
    win.document.write('<HTML><HEAD><TITLE>MiG Remote Access</TITLE></HEAD><BODY>%s</BODY></HTML>');
    win.document.close();
    }
    </script>""" % applet

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Virtual Machines'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Virtual Machines'})
    output_objects.append({'object_type': 'sectionheader', 'text': ''})
    output_objects.append({'object_type': 'text',
                           'text' : '<a href="#" onClick="vncClientPopup(); return false;">Connect to virtual machine</a>'}
                          )
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Your machines:' + popup
                          })
    output_objects.append({'object_type': 'text', 'text'
                              : 'Not implemented yet'
                              })

    return (output_objects, status)
  
cgitb.enable()
run_cgi_script(main)