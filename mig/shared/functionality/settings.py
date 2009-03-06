#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settings - [insert a few words of module description on this line]
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

import sys
import os
from shared.settingskeywords import get_keywords_dict
from shared.fileio import unpickle
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues

def signature():
    defaults = {}
    return ["html_form", defaults]
    
def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""
    configuration, logger, output_objects, op_name = initialize_main_variables(op_header=False, op_title=False)
    
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(user_arguments_dict, defaults, output_objects, cert_name_no_spaces, configuration, allow_rejects = False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    output_objects.append({"object_type":"title", "text":"MiG Settings"})
    output_objects.append({"object_type":"header", "text":"MiG Settings"})
    output_objects.append({"object_type":"sectionheader", "text":"Change your MiG settings"})
    output_objects.append({"object_type":"text", "text":"Multiple addresses and accounts must be separated with new lines, not commas."})
    # unpickle current settings
    current_settings_dict = unpickle(configuration.user_home + cert_name_no_spaces + os.sep + ".settings", logger)
    if not current_settings_dict:
        # no current settings found
        current_settings_dict = {}

    html = """<form method="post" action="/cgi-bin/settingsaction.py">"""
    keywords_dict = get_keywords_dict()
    for keyword in keywords_dict.keys():
        html += "<BR><B>%s</B><BR>" % keyword
        if keywords_dict[keyword]["Type"] == "multiplestrings":
            html += """<textarea cols="40" rows="5" wrap="off" name="%s">""" % keyword 
            if current_settings_dict.has_key(keyword):
                html += "<BR>".join(current_settings_dict[keyword])
            html += "</textarea><BR>"
        elif keywords_dict[keyword]["Type"] == "string":
            # get valid choices from conf
            valid_choices = eval("configuration.%s" % keyword.lower())
            current_choice = ""
            if current_settings_dict.has_key(keyword):
                current_choice = current_settings_dict[keyword]
                
            if len(valid_choices) > 0:
                html += "<select name=%s>" % keyword
                for choice in valid_choices:
                    selected = ""
                    if choice == current_choice:
                        selected = "SELECTED"
                    html += "<option %s value=%s>%s</option>" % (selected, choice, choice)
                html += "</select><BR>"
                        
    html += """<BR><BR><input type="submit" value="Save">"""
    html += "</form>"
    
    output_objects.append({"object_type":"html_form", "text":html})
    return (output_objects, returnvalues.OK)
