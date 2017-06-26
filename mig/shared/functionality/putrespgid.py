#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# putrespgid - Put PGID of process on resource for kill in clean up
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

"""This is a job kill helper for resources"""

import fcntl
import os

import shared.returnvalues as returnvalues
from shared.base import valid_dir_input
from shared.conf import get_resource_configuration
from shared.functional import validate_input, REJECT_UNSET
from shared.httpsclient import check_source_ip
from shared.init import initialize_main_variables
from shared.resadm import put_fe_pgid, put_exe_pgid


def signature():
    """Signature of the main function"""

    defaults = {'type': REJECT_UNSET, 'unique_resource_name': REJECT_UNSET,
                'exe_name': [''], 'pgid': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False, op_title=False,
                                  op_menu=client_id)

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    remote_ip = str(os.getenv('REMOTE_ADDR'))

    res_type = accepted['type'][-1]
    unique_resource_name = accepted['unique_resource_name'][-1]
    exe_name = accepted['exe_name'][-1]
    pgid = accepted['pgid'][-1]

    status = returnvalues.OK

    # Web format for cert access and no header for SID access
    if client_id:
        output_objects.append({'object_type': 'title', 'text'
                               : 'Load resource script PGID'})
        output_objects.append({'object_type': 'header', 'text'
                               : 'Load resource script PGID'})
    else:
        output_objects.append({'object_type': 'start'})

    # Please note that base_dir must end in slash to avoid access to other
    # resource dirs when own name is a prefix of another resource name
    
    base_dir = os.path.abspath(os.path.join(configuration.resource_home,
                                            unique_resource_name)) + os.sep

    # We do not have a trusted base dir here since there's no certificate data.
    # Manually check input variables

    if not valid_dir_input(configuration.resource_home,
                           unique_resource_name):

        # out of bounds - rogue resource!?!?

        msg = 'invalid unique_resource_name! %s' % unique_resource_name
        logger.error('putrespgid FE called with illegal parameter(s) in what appears to be an illegal directory traversal attempt!: unique_resource_name %s, exe %s, client_id %s' \
                     % (unique_resource_name, exe_name, client_id))
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not valid_dir_input(base_dir, 'EXE_%s.PGID' % exe_name):

        # out of bounds - rogue resource!?!?
        
        msg = 'invalid unique_resource_name / exe_name! %s / %s' \
              % (unique_resource_name, exe_name)
        logger.error('putrespgid EXE called with illegal parameter(s) in what appears to be an illegal directory traversal attempt!: unique_resource_name %s, exe %s, client_id %s' \
                                        % (unique_resource_name, exe_name, client_id))
        return (output_objects, returnvalues.CLIENT_ERROR)

    (load_status, resource_conf) = \
                  get_resource_configuration(configuration.resource_home,
                                             unique_resource_name, logger)
    if not load_status:
        logger.error("Invalid putrespgid - no resouce_conf for: %s : %s" % \
                     (unique_resource_name, resource_conf))
        output_objects.append({'object_type': 'error_text', 'text':
                               'invalid request: no such resource!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Check that resource address matches request source to make DoS harder
    proxy_fqdn = resource_conf.get('FRONTENDPROXY', None)
    try:
        check_source_ip(remote_ip, unique_resource_name, proxy_fqdn)
    except ValueError, vae:
        logger.error("Invalid put pgid: %s" % vae)
        output_objects.append({'object_type': 'error_text', 'text':
                               'invalid request: %s' % vae})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO: add full session ID check here

    if 'FE' == res_type:
        (result, msg) = put_fe_pgid(configuration.resource_home,
                                    unique_resource_name, pgid, logger, True)
        if result:
            msg += '(%s) (%s)' % (remote_ip, res_type)
    elif 'EXE' == res_type:
        (result, msg) = put_exe_pgid(configuration.resource_home,
                                     unique_resource_name, exe_name, pgid,
                                     logger, True)
        if result:
            msg += '(%s) (%s)' % (remote_ip, res_type)
    else:
        msg = "Unknown type: '%s'" % res_type
        status = returnvalues.CLIENT_ERROR

    # Status code line followed by raw output
    if not client_id:
        output_objects.append({'object_type': 'script_status', 'text': ''})
        output_objects.append({'object_type': 'binary', 'data': '%s' % status[0]})
    output_objects.append({'object_type': 'binary', 'data': msg})
    return (output_objects, status)
