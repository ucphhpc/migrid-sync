#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# getrespgid - Get PGID of process on resource for kill in clean up
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

"""This is a job kill helper for resources"""

from __future__ import absolute_import

import fcntl
import os

from mig.shared import returnvalues
from mig.shared.base import valid_dir_input
from mig.shared.findtype import is_owner
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.httpsclient import check_source_ip
from mig.shared.init import initialize_main_variables


def signature():
    """Signature of the main function"""

    defaults = {'type': REJECT_UNSET, 'unique_resource_name': REJECT_UNSET,
                'exe_name': ['']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_title=False,
                                  op_menu=client_id)

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(
        user_arguments_dict,
        defaults, output_objects, allow_rejects=False
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    remote_ip = "%s" % os.getenv('REMOTE_ADDR')

    res_type = accepted['type'][-1]
    unique_resource_name = accepted['unique_resource_name'][-1]
    exe_name = accepted['exe_name'][-1]

    status = returnvalues.OK

    if not configuration.site_enable_resources:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "Resources are not enabled on this site"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Web format for cert access and no header for SID access
    if client_id:
        output_objects.append(
            {'object_type': 'title', 'text': 'Load resource script PGID'})
        output_objects.append(
            {'object_type': 'header', 'text': 'Load resource script PGID'})
    else:
        output_objects.append({'object_type': 'start'})

    # Please note that base_dir must end in slash to avoid access to other
    # resource dirs when own name is a prefix of another resource name

    base_dir = os.path.abspath(os.path.join(configuration.resource_home,
                                            unique_resource_name)) + os.sep

    if not is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Only owners of %s can get the PGID!''' % unique_resource_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # is_owner incorporates unique_resource_name verification - no need to
    # specifically check for illegal directory traversal on that variable.
    # exe_name is not automatically checked however - do it manually

    if not valid_dir_input(base_dir, 'EXE_' + exe_name + '.PGID'):

        # out of bounds - rogue resource!?!?

        output_objects.append({'object_type': 'error_text', 'text':
                               'invalid exe_name! %s' % exe_name})
        logger.error('''getrespgid called with illegal parameter(s) in what
appears to be an illegal directory traversal attempt!: unique_resource_name %s,
exe %s, client_id %s''' % (unique_resource_name, exe_name, client_id))
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Check that resource address matches request source to make DoS harder
    try:
        check_source_ip(remote_ip, unique_resource_name)
    except ValueError as vae:
        logger.error("Invalid get pgid: %s" % vae)
        output_objects.append({'object_type': 'error_text', 'text':
                               'invalid get pgid request source'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO: add full session ID check here

    if 'FE' == res_type:
        pgid_path = os.path.join(base_dir, 'FE.PGID')
    elif 'EXE' == res_type:
        pgid_path = os.path.join(base_dir + 'EXE_%s.PGID' % exe_name)
    else:
        output_objects.append({'object_type': 'error_text', 'text':
                               "Unknown type: '%s'" % res_type})
        return (output_objects, returnvalues.CLIENT_ERROR)

    try:
        pgid_file = open(pgid_path, 'r+')
        fcntl.flock(pgid_file, fcntl.LOCK_EX)
        pgid_file.seek(0, 0)
        pgid = pgid_file.readline().strip()
        fcntl.flock(pgid_file, fcntl.LOCK_UN)
        pgid_file.close()

        msg = "%s\n'%s' PGID succesfully retrieved." % (pgid, res_type)
    except Exception as err:
        if 'FE' == res_type:
            msg = "Resource frontend: '%s' is stopped." % unique_resource_name
        elif 'EXE' == res_type:
            msg = ("Error reading PGID for resource: '%s' EXE: '%s'\n"
                   'Either resource has never been started or a server '
                   'error occurred.'
                   ) % (unique_resource_name, exe_name)
        status = returnvalues.CLIENT_ERROR

    # Status code line followed by raw output
    if not client_id:
        output_objects.append({'object_type': 'script_status', 'text': ''})
        output_objects.append({'object_type': 'binary', 'data': '%s' %
                               status[0]})
    output_objects.append({'object_type': 'binary', 'data': msg})
    return (output_objects, status)
