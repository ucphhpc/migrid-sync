#!/usr/bin/env python

#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vms - A "library" of functions for doing various stuff specific for the use
#       virtual machines, creation of mRsl for start, grabbing status, listing machines etc.
#
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
import os.path
from glob import glob

"""

 vmslist,
 
 Returns a list of dicts describing users available virtual machines
 described by following keys:
 
 'name', 'ram', 'state'
 
 TODO:  - grab machine information from xml
        - grab state by traversing the job queue to find out whether it
          has been submitted to a resource yet.
        1) Safeguard the globbing
 
"""
def vms_list(configuration, cert_name_no_spaces):
        
    # Grab the base directory of the user
    base_dir = os.path.abspath(configuration.user_home + os.sep
                                + cert_name_no_spaces) + os.sep
    
    # Append the virtual machine directory
    vms_root    = base_dir + 'vms' + os.sep
    vms_paths   = glob(vms_root+'*')
    
    vms = [] # List of virtual machines
    for vm_name in vms_paths:
        
        vm = {'name':'Unknown',
              'specs':'Unknown',
              'state':'Unknown'}
        
        vm['name'] = os.path.basename(vm_name)
        
        # Grab the xml file defining the vm
        vm_def_path = glob(vm_name+os.sep+'*.xml')
        vm_def_base = os.path.basename(vm_def_path[0]) # TODO: 1
        
        vm['specs'] = vm_def_base  
        
        # TODO: grab machine state by traversing job-queue searching for input files
        
        # Todo: grab machine details such as ram from machine definition
        
        vms.append(vm)
    
    return vms
  
"""
 vnc_applet,
 
 Generates the html tag needed for loading the vnc applet.
 Takes care of fixing representation of the password.
 
 You just specifify a jobidentifier and where all happy.
 
"""
def vnc_applet(proxy_host, proxy_port, applet_port, width, height, password):
  
  applet = """<APPLET CODE="VncViewer" ARCHIVE="VncViewer.jar" """
  applet += " CODEBASE=\"http://%s:%d/tightvnc/\"" % (proxy_host, applet_port)
  applet += " WIDTH=\"%d\" HEIGHT=\"%d\">" % (width, height)
  applet += "<PARAM NAME=\"PORT\" VALUE=\"%d\">" % (proxy_port)
  applet += "<PARAM NAME=\"Encoding\" VALUE=\"Raw\">"
  applet += "</APPLET>"
  
  return applet

"""
 popup_snippet,
 
 Just a simple piece of js to popup a window.

"""
def popup_snippet():
    
  return """
    <script>
    function vncClientPopup() {
    var win = window.open("", "win", "menubar=no,toolbar=no");
    
    win.document.open("text/html", "replace");
    win.document.write('<HTML><HEAD><TITLE>MiG Remote Access</TITLE></HEAD><BODY>%s</BODY></HTML>');
    win.document.close();
    }
    </script>"""