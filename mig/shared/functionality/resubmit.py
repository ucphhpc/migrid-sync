#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resubmit - [insert a few words of module description on this line]
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

The client specifies a job_id, and this script loops all relevant fields,
generates a temp file in mRSL format and submits the tempfile to new_job()
"""

import os
import tempfile
import glob

import shared.mrslkeywords as mrslkeywords
import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import all_jobs
from shared.fileio import unpickle
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables
from shared.job import new_job
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'job_id': REJECT_UNSET}
    return ['resubmitobjs', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    client_dir = client_id_dir(client_id)
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

    patterns = accepted['job_id']

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
            '''Job execution is not enabled on this system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not patterns:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'No job_id specified!'})
        return (output_objects, returnvalues.NO_SUCH_JOB_ID)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                        client_dir)) + os.sep

    filelist = []
    keywords_dict = mrslkeywords.get_keywords_dict(configuration)
    for pattern in patterns:
        pattern = pattern.strip()

        # Backward compatibility - all_jobs keyword should match all jobs

        if pattern == all_jobs:
            pattern = '*'

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern + '.mRSL')
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                continue

            # Insert valid job files in filelist for later treatment

            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : '%s: You do not have any matching job IDs!' % pattern})
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

        mrsl_dict = unpickle(filepath, logger)
        if not mrsl_dict:
            resubmitobj['message'] = "No such job: %s (%s)" % (job_id,
                                                               mrsl_file)
            status = returnvalues.CLIENT_ERROR
            resubmitobjs.append(resubmitobj)
            continue

        resubmit_items = keywords_dict.keys()

        # loop selected keywords and create mRSL string

        resubmit_job_string = ''

        for dict_elem in resubmit_items:
            value = ''
            # Extract job value with fallback to default to support optional
            # fields
            job_value = mrsl_dict.get(dict_elem,
                                      keywords_dict[dict_elem]['Value'])
            if keywords_dict[dict_elem]['Type'].startswith('multiplekeyvalues'):
                for (elem_key, elem_val) in job_value:
                    if elem_key:
                        value += '%s=%s\n' % (str(elem_key).strip(),
                                              str(elem_val).strip())
            elif keywords_dict[dict_elem]['Type'].startswith('multiple'):
                for elem in job_value:
                    if elem:
                        value += '%s\n' % str(elem).rstrip()
            else:
                if str(job_value):
                    value += '%s\n' % str(job_value).rstrip()

            # Only insert keywords with an associated value

            if value:
                if value.rstrip() != '':
                    resubmit_job_string += '''::%s::
%s

''' % (dict_elem, value.rstrip())

        # save tempfile

        (filehandle, tempfilename) = \
            tempfile.mkstemp(dir=configuration.mig_system_files,
                             text=True)
        os.write(filehandle, resubmit_job_string)
        os.close(filehandle)

        # submit job the usual way

        (new_job_status, msg, new_job_id) = new_job(tempfilename,
                client_id, configuration, False, True)
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


