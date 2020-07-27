#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# testresupport - run test job to verify support for a runtime env
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

"""Run a test job to verify support for a certain runtime environment"""
from __future__ import absolute_import

import base64
import tempfile
import os

from .shared import returnvalues
from .shared.base import client_id_dir, valid_dir_input
from .shared.defaults import csrf_field
from .shared.fileio import unpickle, write_file
from .shared.findtype import is_owner
from .shared.functional import validate_input_and_cert, REJECT_UNSET
from .shared.handlers import safe_handler, get_csrf_limit
from .shared.init import initialize_main_variables, find_entry
from .shared.job import new_job
from .shared.refunctions import get_re_dict
from .shared.vgridaccess import user_visible_res_confs


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET, 're_name': REJECT_UNSET}
    return ['html_form', defaults]

def create_verify_files(types, re_name, re_dict, base_dir, logger):
    """Create runtime env test files"""
    for ver_type in types:
        if 'VERIFY%s' % ver_type.upper() in re_dict:
            if re_dict['VERIFY%s' % ver_type.upper()] != []:
                file_content = ''
                for line in re_dict['VERIFY%s' % ver_type.upper()]:
                    file_content += line + '\n'
                if not write_file(file_content.strip(),
                                  '%sverify_runtime_env_%s.%s'
                                   % (base_dir, re_name,
                                  ver_type.lower()), logger):
                    raise Exception('could not write test job %s' % \
                                    ver_type.upper())

def testresource_has_re_specified(unique_resource_name, re_name,
                                  configuration):
    """Check if unique_resource_name has runtime env enabled"""
    resource_config = unpickle(configuration.resource_home
                                + unique_resource_name + '/config',
                               configuration.logger)
    if not resource_config:
        configuration.logger.error('error unpickling resource config')
        return False

    for rre in resource_config['RUNTIMEENVIRONMENT']:
        (res_name, res_val) = rre
        if re_name == res_name:
            return True

    return False

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Runtime env support'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Test runtime environment support'})
    
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
        logger.warning('%s invalid input: %s' % (op_name, accepted))
        return (accepted, returnvalues.CLIENT_ERROR)
    resource_list = accepted['unique_resource_name']
    re_name = accepted['re_name'][-1]
    status = returnvalues.OK
    visible_res = user_visible_res_confs(configuration, client_id)

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not re_name:
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Please specify the name of the runtime environment!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not valid_dir_input(configuration.re_home, re_name):
        logger.warning(
            "possible illegal directory traversal attempt re_name '%s'"
            % re_name)
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Illegal runtime environment name: "%s"'
                               % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    for visible_res_name in resource_list:
        if not visible_res_name in visible_res.keys():
            logger.warning('User %s not allowed to view %s (%s)' % \
                           (client_id, visible_res_name, visible_res.keys()))
            output_objects.append({'object_type': 'error_text',
                                   'text': 'invalid resource %s' % \
                                   visible_res_name})
            status = returnvalues.CLIENT_ERROR
            continue

        if not is_owner(client_id, visible_res_name,
                        configuration.resource_home, logger):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'You must be an owner of the resource to validate runtime '
                 'environment support. (resource %s)' % visible_res_name})
            status = returnvalues.CLIENT_ERROR
            continue

        (re_dict, re_msg) = get_re_dict(re_name, configuration)
        if not re_dict:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Could not get re_dict %s' % re_msg})
            status = returnvalues.SYSTEM_ERROR
            continue

        if not testresource_has_re_specified(visible_res_name, re_name,
                                             configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'You must specify the runtime environment in the resource'
                 'configuration before verifying if it is supported!'})
            status = returnvalues.CLIENT_ERROR
            continue

        base64string = ''
        for stringpart in re_dict['TESTPROCEDURE']:
            base64string += stringpart

        mrslfile_content = base64.decodestring(base64string)

        try:
            (filehandle, mrslfile) = tempfile.mkstemp(text=True)
            os.write(filehandle, mrslfile_content)
            os.close(filehandle)
            create_verify_files(['status', 'stdout', 'stderr'], re_name,
                                re_dict, base_dir, logger)
        except Exception as exc:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Could not write test job for %s: %s' % (visible_res_name,
                                                         exc)})
            status = returnvalues.SYSTEM_ERROR
            continue

        forceddestination_dict = {'UNIQUE_RESOURCE_NAME': visible_res_name,
                                  'RE_NAME': re_name}

        (success, msg) = new_job(mrslfile, client_id, configuration,
                                forceddestination_dict)
        if not success:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Submit test job failed %s: %s' % (visible_res_name,
                                                    msg)})
            status = returnvalues.SYSTEM_ERROR

        try:
            os.remove(mrslfile)
        except:
            pass

        output_objects.append(
            {'object_type': 'text', 'text':
             'Runtime environment test job for %s successfuly submitted! %s' \
             % (visible_res_name, msg)})

    return (output_objects, status)
