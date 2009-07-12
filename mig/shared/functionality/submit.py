#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# submit - [insert a few words of module description on this line]
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

"""Explicit job submit"""

import os
import sys
import glob

import shared.returnvalues as returnvalues
from shared.validstring import valid_user_path
from shared.parseflags import verbose
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.job import new_job
from shared.useradm import client_id_dir


def signature():
    """Signature of the main function"""

    defaults = {'path': REJECT_UNSET, 'flags': ['']}
    return ['submitstatuslist', defaults]


def usage():
    """Usage help"""

    return """submit one or more job description files.
Takes a list of path entries relative to your MiG home directory and submits each one in turn.
The result is a structure with submit details for each submit attempt including status and job ID
upon success.
The flags parameter can be used to request more verbose output.
"""


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    patterns = accepted['path']

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

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

                logger.error('Warning: %s tried to %s %s outside own home! (%s)'
                              % (client_id, op_name, real_path,
                             pattern))
                continue
            match.append(real_path)

        # Now actually treat list of allowed matchings and notify if
        # no (allowed) match

        if not match:
            output_objects.append({'object_type': 'file_not_found',
                                  'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        submitstatuslist = []
        for real_path in match:
            output_lines = []
            relative_path = real_path.replace(base_dir, '')
            submitstatus = {'object_type': 'submitstatus',
                            'name': relative_path}

            try:
                (job_status, newmsg, job_id) = new_job(real_path,
                        client_id, configuration, False, True)
            except Exception, exc:
                logger.error("%s: failed on '%s': %s" % (op_name,
                             relative_path, exc))
                job_status = False
                newmsg = "%s failed on '%s' (is it a valid mRSL file?)"\
                     % (op_name, relative_path)
                job_id = None

            if not job_status:

                # output_objects.append({"object_type":"error_text", "text":"%s" % newmsg})

                submitstatus['status'] = False
                submitstatus['message'] = newmsg
                status = returnvalues.CLIENT_ERROR
            else:

                # return (output_objects, returnvalues.CLIENT_ERROR)

                submitstatus['status'] = True
                submitstatus['job_id'] = job_id

                # output_objects.append({"object_type":"text", "text":"%s" % newmsg})

            submitstatuslist.append(submitstatus)

        output_objects.append({'object_type': 'submitstatuslist',
                              'submitstatuslist': submitstatuslist})

    return (output_objects, status)


