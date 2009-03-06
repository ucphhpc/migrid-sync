#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# editfile - [insert a few words of module description on this line]
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

"""Editor back end"""

import os
import sys
import time
import glob
from shared.validstring import valid_user_path
from shared.editing import acquire_edit_lock, release_edit_lock
from shared.job import new_job
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues

def signature():
    defaults = {'path':REJECT_UNSET, 'newline':['unix'], 'submitjob':[False], "editarea":REJECT_UNSET}
    return ["submitstatuslist", defaults]
    
def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""
    configuration, logger, output_objects, op_name = initialize_main_variables(op_header = False)

    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(user_arguments_dict, defaults, output_objects, cert_name_no_spaces, configuration, allow_rejects = False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    path = (accepted['path'])[-1]
    chosen_newline = (accepted['newline'])[-1]
    submitjob = (accepted['submitjob'])[-1]                                
    
    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name
    base_dir = os.path.abspath(configuration.user_home + os.sep + cert_name_no_spaces) + os.sep
    # HTML spec dictates newlines in forms to be MS style (\r\n)
    # rather than un*x style (\n): change if requested.
    form_newline = "\r\n"
    allowed_newline = {"unix":"\n", "mac":"\r", "windows":"\r\n"}
    output_objects.append({"object_type":"header", "text": "Saving changes to edited file"})

    if not chosen_newline in allowed_newline.keys():
        output_objects.append({"object_type":"error_text", "text": "Unsupported newline style supplied: %s (must be one of %s)" % (chosen_newline, ", ".join(allowed_newline.keys()))})
        return (output_objects, returnvalues.CLIENT_ERROR)
        
    saved_newline = allowed_newline[chosen_newline]

    # Check directory traversal attempts before actual handling to avoid leaking
    # information about file system layout while allowing consistent error messages
    real_path = ""
    unfiltered_match = glob.glob(base_dir + path)
    for server_path in unfiltered_match:
        real_path = os.path.abspath(server_path)
        if not valid_user_path(real_path, base_dir, True):
            # ../*/* is technically allowed to match own files.
            logger.error("Warning: %s tried to %s outside own home! (path %s)" % (cert_name_no_spaces, op_name, path))
            output_objects.append({"object_type":"error_text", "text": "You're only allowed to edit your own files! (%s expands to an illegal path)" % path})
            return (output_objects, returnvalues.CLIENT_ERROR)
    # Do not allow modification of htaccess files
    if '.htaccess' == os.path.basename(real_path):
        logger.error("Warning: %s tried to %s htaccess! (path %s)" % (cert_name_no_spaces, op_name, path))
        output_objects.append({"object_type":"error_text", "text": "Access to .htaccess files is prohibited!"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if real_path == "":
        real_path = base_dir + path
        if not valid_user_path(real_path, base_dir, True):
            logger.error("Warning: %s tried to %s outside own home! (path %s)" % (cert_name_no_spaces, op_name, path))
            output_objects.append({"object_type":"error_text", "text": "You're only allowed to edit your own files! (%s expands to an illegal path)" % path})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
    owner, time_left = acquire_edit_lock(real_path, cert_name_no_spaces)
    if owner != cert_name_no_spaces:
        output_objects.append({"object_type":"error_text", "text": "You don't have the lock for %s!" % path})
        return (output_objects, returnvalues.CLIENT_ERROR)

    try:
        fh = open(real_path, "w+")
        fh.write(((user_arguments_dict["editarea"][0]).replace(form_newline, saved_newline)))
        fh.close()
        # everything ok
        output_objects.append({"object_type":"text", "text": "Saved changes to %s." % path})
        release_edit_lock(real_path, cert_name_no_spaces)
    except Exception, e:
        # Don't give away information about actual fs layout
        output_objects.append({"object_type":"error_text", "text": "%s could not be written! (%s)" % (path, str(e).replace(base_dir, ''))})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    if submitjob:
        output_objects.append({"object_type":"text", "text": "Submitting saved file to parser"})
        submitstatus = {"object_type":"submitstatus", "name":path}
        (status, msg, job_id) = new_job(real_path, cert_name_no_spaces, configuration, False, True)
        if not status:
            submitstatus["status"] = False
            submitstatus["message"] = msg
        else:
            submitstatus["status"] = True
            submitstatus["job_id"] = job_id
                            
        output_objects.append({"object_type":"submitstatuslist","submitstatuslist":[submitstatus]})
    
    return (output_objects, returnvalues.OK)
