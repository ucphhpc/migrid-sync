#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resubmit - [insert a few words of module description on this line]
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

"""Resubmit a job
The idea is to reuse the existing job submit code (new_job()) and
make a resubmit like any other job submission (textarea, mRSL file upload). 

The client specifies a job_id, and this script loops all relevant fields, generates a 
temp file in mRSL format and submits the tempfile to new_job()
"""

import os
import sys
import time
import tempfile
import glob

from shared.job import new_job
from shared.fileio import unpickle
from shared.validstring import valid_user_path
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET}
    return ['resubmitobjs', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()
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
    patterns = accepted['job_id']

    if not patterns:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'No job_id specified!'})
        return (output_objects, returnvalues.NO_SUCH_JOB_ID)
    base_dir = os.path.abspath(configuration.mrsl_files_dir + os.sep
                                + cert_name_no_spaces) + os.sep
    filelist = []
    for pattern in patterns:
        pattern = pattern.strip()

        # Backward compatibility - keyword ALL should match all jobs

        if pattern == 'ALL':
            pattern = '*'

        # Check directory traversal attempts before actual handling to
        # avoid leaking information about file system layout while
        # allowing consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern + '.mRSL')
        match = []
        for server_path in unfiltered_match:
            real_path = os.path.abspath(server_path)
            if not valid_user_path(real_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.error('%s tried to use %s %s outside own home! (pattern %s)'
                              % (cert_name_no_spaces, op_name,
                             real_path, pattern))
                continue

            # Insert valid job files in filelist for later treatment

            match.append(real_path)

        # Now actually treat list of allowed matchings and notify if
        # no (allowed) match

        if not match:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : '%s: You do not have any matching job IDs!'
                                   % pattern})
            status = returnvalues.CLIENT_ERROR
        else:
            filelist += match

    # resubmit is hard on the server

    if len(filelist) > 100:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many matching jobs (%s)!'
                               % len(filelist)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    resubmitobjs = []
    status = returnvalues.OK
    for filepath in filelist:
        mrsl_file = filepath.replace(base_dir, '')
        job_id = mrsl_file.replace('.mRSL', '')

        # ("Resubmitting job with job_id: %s" % job_id)

        resubmitobj = {'object_type': 'resubmitobj', 'job_id': job_id}

        # filename = configuration.mrsl_files_dir + "/" + cert_name_no_spaces + "/" + job_id + ".mRSL"

        dict = unpickle(filepath, logger)
        if not dict:

            # o.out("You can only resubmit your own jobs. Please verify that you submitted the job with job id '%s' (Could not unpickle mRSL file)" % job_id, filepath)
            # o.reply_and_exit(o.CLIENT_ERROR)

            resubmitobj['message'] = \
                "You can only resubmit your own jobs. Please verify that you submitted the job with job id '%s' (Could not unpickle mRSL file)"\
                 % (job_id, filepath)
            status = returnvalues.CLIENT_ERROR
            resubmitobjs.append(resubmitobj)
            continue

        resubmit_items = [
            'VGRID',
            'EXECUTE',
            'RUNTIMEENVIRONMENT',
            'ENVIRONMENT',
            'VERIFYFILES',
            'INPUTFILES',
            'EXECUTABLES',
            'DISK',
            'CPUTIME',
            'MAXPRICE',
            'PROJECT',
            'CPUCOUNT',
            'NOTIFY',
            'NODECOUNT',
            'OUTPUTFILES',
            'JOBNAME',
            'ARCHITECTURE',
            'MEMORY',
            ]

        # loop selected keywords and create mRSL string

        resubmit_job_string = ''

        for dict_elem in resubmit_items:
            value = ''
            if type(dict[dict_elem]) == type([]):
                for elem in dict[dict_elem]:
                    if elem:
                        value += '%s\n' % elem.rstrip()
            else:
                if str(dict[dict_elem]):
                    value += '%s\n' % str(dict[dict_elem]).rstrip()

            # Only insert keywords with an associated value

            if value:
                if value.rstrip() != '':
                    resubmit_job_string += '''::%s::
%s

'''\
                         % (dict_elem, value.rstrip())

        # save tempfile

        (filehandle, tempfilename) = \
            tempfile.mkstemp(dir=configuration.mig_system_files,
                             text=True)
        os.write(filehandle, resubmit_job_string)
        os.close(filehandle)

        # submit job the usual way

        (new_job_status, msg, new_job_id) = new_job(tempfilename,
                cert_name_no_spaces, configuration, False, True)
        if not new_job_status:
            resubmitobj['status'] = False
            resubmitobj['message'] = msg
            status = returnvalues.SYSTEM_ERROR
            resubmitobjs.append(resubmitobj)
            continue

            # o.out("Resubmit failed: %s" % msg)
            # o.reply_and_exit(o.ERROR)

        resubmitobj['status'] = True
        resubmitobj['new_job_id'] = new_job_id
        resubmitobjs.append(resubmitobj)

        # o.out("Resubmit successful: %s" % msg)
        # o.out("%s" % msg)

    output_objects.append({'object_type': 'resubmitobjs', 'resubmitobjs'
                          : resubmitobjs})

    return (output_objects, status)


