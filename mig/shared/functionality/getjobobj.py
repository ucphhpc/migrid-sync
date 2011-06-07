#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# getjobobj - [insert a few words of module description on this line]
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

"""Get job on object format"""

import os

import shared.mrslkeywords as mrslkeywords
import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.conf import get_configuration_object
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.job import create_job_object_from_pickled_mrsl


def signature():
    defaults = {'job_id': REJECT_UNSET}

    configuration = get_configuration_object()
    external_dict = mrslkeywords.get_keywords_dict(configuration)
    for (key, value_dict) in external_dict.iteritems():
        if not defaults.has_key(key):

            # do not overwrite

            defaults[key] = []
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_title=False)
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
    job_id_list = accepted['job_id']
    external_dict = mrslkeywords.get_keywords_dict(configuration)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = \
        os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                        client_dir)) + os.sep

    status = returnvalues.OK
    for job_id in job_id_list:

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


