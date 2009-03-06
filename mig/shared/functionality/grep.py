#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grep - [insert a few words of module description on this line]
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


"""Emulate the un*x function with the same name."""

import os
import sys
import glob
import re
import time

import shared.returnvalues as returnvalues
from shared.validstring import valid_user_path
from shared.parseflags import verbose
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET

def pattern_match_file(pattern, filename, allowed_time=5.0):
    """Return lines in file which match the provided pattern"""
    # Allow comparison to take up to allowed_time seconds
    fit = []
    start_time = time.time()
    file_fd = open(filename, 'r')
    for line in file_fd:
        compare_time = time.time() - start_time
        if compare_time > allowed_time:
            # print "Template fit of %s against %s timed out after %d lines (%d seconds)" % (template, filename, i, compare_time)
            break
        
        line = line.strip()
        if re.match(pattern, line):
            fit.append(line)
    file_fd.close()

    # print "Comparison of %s against %s done in %.4f seconds" % (template, filename, compare_time)
    return fit

def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""
    configuration, logger, output_objects, op_name = initialize_main_variables()
    
    status = returnvalues.OK
    defaults = {'path':REJECT_UNSET, 'flags':[''], 'pattern':REJECT_UNSET}
    (validate_status, accepted) = validate_input_and_cert(user_arguments_dict, defaults, output_objects, cert_name_no_spaces, configuration, allow_rejects = False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
                  
    flags = ''.join((accepted['flags']))
    patterns = accepted['path']
    search = (accepted['pattern'])[-1]
        
    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name
    base_dir = os.path.abspath(configuration.user_home + os.sep + \
                               cert_name_no_spaces) + os.sep
    
    if verbose(flags):
        for flag in flags:
            output_objects.append({"object_type":"text", "text": "%s using flag: %s" % (op_name, flag)})
            
    for pattern in patterns:
        # Check directory traversal attempts before actual handling
        # to avoid leaking information about file system layout while
        # allowing consistent error messages
        unfiltered_match = glob.glob(base_dir + pattern)
        match = []
        for server_path in unfiltered_match:
            real_path = os.path.abspath(server_path)
            if not valid_user_path(real_path, base_dir, True):
                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.
                logger.error(
                    "Warning: %s tried to %s %s outside own home! (%s)" % \
                    (cert_name_no_spaces, op_name, real_path, pattern))
                continue
            match.append(real_path)

        # Now actually treat list of allowed matchings and notify if
        # no (allowed) match
        if not match:
            output_objects.append({"object_type":"file_not_found",
                                   "name":pattern})
            status = returnvalues.FILE_NOT_FOUND
    
        for real_path in match:
            relative_path = real_path.replace(base_dir,'') 
            output_lines = []
            try:
                matching = pattern_match_file(search, real_path)
                for line in matching:
                    output_lines.append(line.strip())
            except Exception, exc:
                output_objects.append({"object_type":"error_text",
                                       "text":"%s: '%s': %s" % \
                                       (op_name, relative_path, exc)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                                                         relative_path, exc))
                status = returnvalues.SYSTEM_ERROR
                continue
            if verbose(flags):
                output_objects.append({"object_type":"file_output", "path":relative_path, "lines":output_lines})
            else:
                output_objects.append({"object_type":"file_output", "lines":output_lines})
                                                 
    return (output_objects, status)
