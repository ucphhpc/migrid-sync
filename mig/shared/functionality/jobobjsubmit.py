#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobobjsubmit - Submit a job object/dictionary directly
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

"""Takes a job object/dictionary, writes the mRSL file and submits it"""

import os
import sys
import glob
import tempfile

import shared.mrslkeywords as mrslkeywords
from shared.conf import get_resource_configuration, \
    get_configuration_object
from shared.refunctions import get_re_dict, list_runtime_environments
from shared.fileio import unpickle
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues
from shared.job import new_job, create_job_object_from_pickled_mrsl
from shared.useradm import client_id_dir


def signature():
    defaults = {}
    configuration = get_configuration_object()
    external_dict = mrslkeywords.get_keywords_dict(configuration)

    for (key, value_dict) in external_dict.items():
        if not defaults.has_key(key):

            # make sure required fields are set but do not overwrite

            if value_dict['Required']:
                defaults[key] = REJECT_UNSET
            else:
                defaults[key] = []
    return ['html_form', defaults]

def init_job(configuration, user_args, client_id):
    """Prepare encoded input args for regular job format validation"""

    # Merge the variable fields like runtimeenvironmentX
    # into the final form suitable for parsing.
   
    re_list = []
    field_count = 0
    field_count_arg = user_args.get('runtime_env_fields', None)[-1]
    print field_count_arg
    if field_count_arg:
        field_count = int(field_count_arg)
        del user_args['runtime_env_fields']
    for i in range(field_count):
        runtime_env = 'runtimeenvironment' + str(i)
        if user_args.has_key(runtime_env):
            re_list.append(user_args[runtime_env][-1])
            del user_args[runtime_env]
    user_args['RUNTIMEENVIRONMENT'] = re_list
    return user_args


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables()
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
    defaults = signature()[1]

    # IMPORTANT: runtime envs may be encoded in multiple values here
    # Parse them to ordinary form first if so

    user_arguments_dict = init_job(configuration, user_arguments_dict, client_id)

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

    external_dict = mrslkeywords.get_keywords_dict(configuration)
    spec = []
    for (key, value_dict) in external_dict.items():
        attrName = key
        if user_arguments_dict.has_key(attrName):
            spec.append('::%s::' % attrName)
            attr = user_arguments_dict[attrName]

            # output_objects.append({"object_type":"text", "text":attrName})

            # FIXME: this type check is not perfect... I should be
            # able to extend on any sequence...

            if isinstance(attr, list):
                spec.extend(attr)
            elif isinstance(attr, tuple):
                spec.extend(attr)
            else:
                spec.append(attr)

            # if appendNewline:

            spec.append('')

    mrsl = '\n'.join(spec)

    tmpfile = None

    # save to temporary file

    try:
        (filehandle, tmpfile) = tempfile.mkstemp(text=True)
        os.write(filehandle, mrsl)
        os.close(filehandle)
    except Exception, err:
        submit_status = False

    # submit it

    (submit_status, newmsg, job_id) = new_job(tmpfile, client_id,
            configuration, False, True)
    if not submit_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : newmsg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                        client_dir)) + os.sep

    # job = Job()

    filepath = os.path.join(base_dir, job_id)
    filepath += '.mRSL'

    (new_job_obj_status, new_job_obj) = \
        create_job_object_from_pickled_mrsl(filepath, logger,
            external_dict)
    if not new_job_obj_status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : new_job_obj})
        status = returnvalues.CLIENT_ERROR
    else:

        # return new_job_obj

        output_objects.append({'object_type': 'jobobj', 'jobobj'
                              : new_job_obj})
    return (output_objects, status)


