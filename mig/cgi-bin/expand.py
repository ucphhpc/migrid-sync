#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# expand - [insert a few words of module description on this line]
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

# Minimum Intrusion Grid
# Jonas Bardino, 2005

"""CGI to expand a wildcard expression into actual file paths. This
is particularly useful as a helper application for the user scripts.
"""

import cgi
import cgitb; cgitb.enable()
import os
import sys
import glob
import ConfigParser
import time

from shared.cgishared import init_cgi_script_with_cert
from shared.html import get_cgi_html_header, get_cgi_html_footer
from shared.validstring import valid_user_path
from shared.parseflags import recursive


def get_select_all_javascript():
    l = "<SCRIPT LANGUAGE='JavaScript'> document.fileform.allbox.onclick = un_check; function un_check()"
    l += "{ for (var i = 0; i < document.fileform.elements.length; i++) { var e = document.fileform.elements[i];"
    l += "if ((e.name != 'allbox') && (e.type == 'checkbox'))" 
    l += "{ e.checked = document.fileform.allbox.checked; } } } </SCRIPT>"
    return l

def display_file(filename, file_with_dir, actual_file, dest=""):
    # Build entire line before printing to avoid newlines
    fileline = ""

    if printhtml:
        fileline += "<TR><TD><input type='checkbox' name='remove_files' value='%s'></TD>" % (filename)
        fileline += "<TD><A HREF=/%s/%s>" %  ("cert_redirect", file_with_dir)

    fileline += file_with_dir
    if printhtml:
        fileline += "</A></TD>"

    if showdest:
        if printhtml:
            fileline += "<TD>"

        fileline += "\t%s" % dest
        if printhtml:
            fileline += "</TD>"

    if printhtml:
        fileline += "</TR>"

    o.client(fileline)
# end display_file

def display_dir(dirname, dirname_with_dir, actual_dir, dest=""):
    dirline = ""

    if printhtml:
        dirline += "<TR><TD><input type='checkbox' name='remove_dirs' value='%s'></TD>" % (dirname)
        dirline += "<TD><A HREF='ls.py?path=%s'>" % (dirname_with_dir)

    dirline += dirname_with_dir
 
    if printhtml:
        dirline += "</A></TD>"

    if showdest:
        if printhtml:
            fileline += "<TD>"

        fileline += dest
        if printhtml:
            fileline += "</TD>"

    if printhtml:
        fileline += "</TR>"

    o.client(dirline)
# end display_dir

def display_expand(real_path, flags="", dest="", depth=0):
    """Recursive function to expand paths in a way not unlike ls, but only
    files are interesting in this context. The order of recursively expanded
    paths is different from that in ls since it simplifies the code and
    doesn't really matter to the clients.
    """
    
    # Sanity check
    if depth > 256:
        o.client("Error: file recursion maximum exceeded!")
        return

    # references to '.' or similar are stripped by abspath
    if real_path == base_dir[:-1]:
        base_name = relative_path = "."
    else:
        base_name = os.path.basename(real_path)
        relative_path = real_path.replace(base_dir, "")

    if os.path.isfile(real_path):
        display_file(base_name, relative_path, real_path, dest)
    elif recursive(flags):
        try:
            contents = os.listdir(real_path)
        except Exception, e:
            if printhtml:
                o.client("<TR><TD>")
            o.client("Failed to list contents of %s: %s" % (base_name, e))
            if printhtml:
                o.client("</TD></TR>")
            return
                
        contents.sort()

        for name in contents:
            path = real_path + os.sep + name
            rel_path = path.replace(base_dir, "")
            if os.path.isfile(path):
                display_file(name, rel_path, path, dest + name)
            elif os.path.isdir(path):
                display_expand(path, flags, dest + name + os.sep, depth+1)
# end display_expand


### Main ###
(logger, configuration, cert_name_no_spaces, o) = init_cgi_script_with_cert()
op_name = os.path.basename(sys.argv[0]).replace(".py","")

# Please note that base_dir must end in slash to avoid access to other
# user dirs when own name is a prefix of another user name
base_dir = os.path.abspath(configuration.user_home + os.sep + cert_name_no_spaces) + os.sep

fieldstorage = cgi.FieldStorage()

htmlquery = fieldstorage.getfirst("with_html", "true")
# Default values: no flags, no paths
flags = fieldstorage.getfirst("flags", "")
pattern_list = fieldstorage.getlist("path")
destquery = fieldstorage.getfirst("with_dest", "false")
output_format = fieldstorage.getfirst("output_format", "html")
status = o.OK

printhtml = False
if htmlquery == "true":
    printhtml = True
showdest = False
if destquery == "true":
    showdest = True
    
# tmp hack
if output_format == "html":
    printhtml = True
else:
    printhtml = False
    
if printhtml:
    o.client(get_cgi_html_header("", "", scripts = get_select_all_javascript()))
    o.client("<div class='migcontent'>")
    #o.client("<html><head></head><body>")
    #PrintSelectAllJavascript()
    o.client("<div class='subsection'>")
    o.client("Expansion list for patterns %s by " % ', '.join(pattern_list))
    
    o.client(cert_name_no_spaces)
    o.client("</div><BR><BR>")
    o.client("<div class='migcontent'>")
    o.client("<form method='post' action='/cgi-bin/rm.py' name='fileform'>")
    o.client("<input type='hidden' name='with_html' value='true'>")
    o.client("<input type='submit' name='delete' value='DELETE!'>")
    o.client("<div class='container'>")
    o.client("<TABLE BORDER=1 class='migtable'><TR><TD>Delete</TD><TD>File</TD>")
    if showdest:
        o.client("<TD>Destination</TD>")

if not pattern_list:
    o.client("No 'path' argument(s) to be expanded!")
    status = o.CLIENT_ERROR
    
for pattern in pattern_list:
    # Check directory traversal attempts before actual handling to avoid leaking
    # information about file system layout while allowing consistent error messages
    unfiltered_match = glob.glob(base_dir + pattern)
    match = []
    for server_path in unfiltered_match:
        real_path = os.path.abspath(server_path)
        if not valid_user_path(real_path, base_dir, True):
            # out of bounds - save user warning for later to allow partial match:
            # ../*/* is technically allowed to match own files.
            o.internal("Warning: %s tried to %s %s outside own home! (using pattern %s)" % (cert_name_no_spaces, op_name, real_path, pattern))
            continue
        match.append(real_path)

    # Now actually treat list of allowed matchings and notify if no (allowed) match
    if not match:
        o.client_html("<TR><TD>", printhtml)
        o.out("%s: no such file or directory!" % pattern)
        o.client_html("</TD></TR>", printhtml)
        status = o.CLIENT_ERROR
        
    for real_path in match:
        relative_path = real_path.replace(base_dir,'') 

        dest = ""
        if destquery:
            if os.path.isfile(real_path):
                dest = os.path.basename(real_path)
            elif recursive(flags):
                # references to '.' or similar are stripped by abspath
                if real_path == base_dir[:-1]:
                    dest = ""
                else:
                    # dest = os.path.dirname(real_path).replace(base_dir, "")
                    dest = os.path.basename(real_path) + os.sep
            
        display_expand(real_path, flags, dest)

if printhtml:
 #   o.client("</TABLE></form></body></html>")
    o.client("</table></div></div>")
    o.client("</div>")
    o.client(get_cgi_html_footer("<p><a href='../'>Back</a>"))

o.reply_and_exit(status)
