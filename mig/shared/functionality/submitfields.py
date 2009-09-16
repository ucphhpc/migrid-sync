#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# submitfields - Submit a job through the fields interface
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

"""Takes job fields and submits it with the usual submit status"""

import os
import tempfile

import shared.returnvalues as returnvalues
from shared.conf import get_configuration_object
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.job import new_job, fields_to_mrsl
from shared.mrslkeywords import get_job_specs, get_keywords_dict
from shared.useradm import client_id_dir


def signature():
    defaults = {}
    configuration = get_configuration_object()
    show_fields = get_job_specs(configuration)

    for (key, specs) in show_fields:
        if not defaults.has_key(key):

            # make sure required fields are set but do not overwrite

            if specs['Required']:
                defaults[key] = REJECT_UNSET
            else:
                defaults[key] = []
    return ['submitstatuslist', defaults]


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

    external_dict = get_keywords_dict(configuration)
    mrsl = fields_to_mrsl(configuration, user_arguments_dict, external_dict)

    tmpfile = None

    # save to temporary file

    try:
        (filehandle, real_path) = tempfile.mkstemp(text=True)
        relative_path = os.path.basename(real_path)
        os.write(filehandle, mrsl)
        os.close(filehandle)
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Failed to write temporary mRSL file: %s' % err})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # submit it

    submitstatuslist = []
    submitstatus = {'object_type': 'submitstatus',
                    'name': relative_path}
    try:
        (job_status, newmsg, job_id) = new_job(real_path,
                                               client_id, configuration, False, True)
    except Exception, exc:
        logger.error("%s: failed on '%s': %s" % (op_name,
                                                 relative_path, exc))
        job_status = False
        newmsg = "%s failed on '%s' (invalid mRSL?)"\
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


