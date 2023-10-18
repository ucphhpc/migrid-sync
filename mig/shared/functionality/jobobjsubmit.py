#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobobjsubmit - Submit a job object/dictionary directly
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Takes a job object/dictionary, writes the mRSL file and submits it"""

from __future__ import absolute_import

import os
import tempfile

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.conf import get_configuration_object
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables
from mig.shared.job import new_job, fields_to_mrsl, \
    create_job_object_from_pickled_mrsl
from mig.shared.mrslkeywords import get_job_specs, get_keywords_dict


def signature():
    defaults = {}
    configuration = get_configuration_object()
    show_fields = get_job_specs(configuration)

    for (key, specs) in show_fields:
        if key not in defaults:

            # make sure required fields are set but do not overwrite

            if specs['Required']:
                defaults[key] = REJECT_UNSET
            else:
                defaults[key] = []
    return ['jobobj', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
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

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Job execution is not enabled on this system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    external_dict = get_keywords_dict(configuration)
    mrsl = fields_to_mrsl(configuration, user_arguments_dict, external_dict)

    tmpfile = None

    # save to temporary file

    try:
        (filehandle, real_path) = tempfile.mkstemp(text=True)
        relative_path = os.path.basename(real_path)
        os.write(filehandle, mrsl)
        os.close(filehandle)
    except Exception as err:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Failed to write temporary mRSL file!'})
        logger.error("could not write temp mRSL: %s" % err)
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # submit it

    (submit_status, newmsg, job_id) = new_job(real_path, client_id,
                                              configuration, False, True)
    if not submit_status:
        output_objects.append({'object_type': 'error_text', 'text':
                               newmsg})
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
        output_objects.append({'object_type': 'error_text', 'text':
                               new_job_obj})
        status = returnvalues.CLIENT_ERROR
    else:

        # return new_job_obj

        output_objects.append({'object_type': 'jobobj', 'jobobj': new_job_obj})
    return (output_objects, status)
