#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createre - create a new runtime environment
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

"""Creation of runtime environments"""
from __future__ import absolute_import

import os
import base64
import tempfile

from .shared import returnvalues
from .shared.base import valid_dir_input
from .shared.defaults import max_software_entries, max_environment_entries, \
     csrf_field
from .shared.functional import validate_input_and_cert, REJECT_UNSET
from .shared.handlers import safe_handler, get_csrf_limit
from .shared.init import initialize_main_variables
from .shared.refunctions import create_runtimeenv


def signature():
    """Signature of the main function"""

    defaults = {
        're_name': REJECT_UNSET,
        'redescription': ['Not available'],
        'testprocedure': [''],
        'software': [],
        'environment': [],
        'verifystdout': [''],
        'verifystderr': [''],
        'verifystatus': [''],
        }
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Create runtime environment'})
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

    re_name = accepted['re_name'][-1].strip().upper().strip()
    redescription = accepted['redescription'][-1].strip()
    testprocedure = accepted['testprocedure'][-1].strip()
    software = [i.strip() for i in accepted['software']]
    environment = [i.strip() for i in accepted['environment']]
    verifystdout = accepted['verifystdout'][-1].strip()
    verifystderr = accepted['verifystderr'][-1].strip()
    verifystatus = accepted['verifystatus'][-1].strip()

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not valid_dir_input(configuration.re_home, re_name):
        logger.warning(
            "possible illegal directory traversal attempt re_name '%s'"
            % re_name)
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Illegal runtime environment name: "%s"'
                               % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    software_entries = len(software)
    if software_entries > max_software_entries:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many software entries (%s), max %s'
                               % (software_entries,
                              max_software_entries)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    environment_entries = len(environment)
    if environment_entries > max_environment_entries:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many environment entries (%s), max %s'
                               % (environment_entries,
                              max_environment_entries)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create file to be parsed - force single line description

    content = """::RENAME::
%s

::DESCRIPTION::
%s

""" % (re_name,
            redescription.replace('\n', '<br />'))

    if testprocedure:
        verify_specified = []
        if verifystdout:
            content += '''::VERIFYSTDOUT::
%s

''' % verifystdout
            verify_specified.append('verify_runtime_env_%s.stdout'
                                     % re_name)
        if verifystderr:
            content += '''::VERIFYSTDERR::
%s

''' % verifystderr
            verify_specified.append('verify_runtime_env_%s.stderr'
                                     % re_name)
        if verifystatus:
            verify_specified.append('verify_runtime_env_%s.status'
                                     % re_name)
            content += '''::VERIFYSTATUS::
%s

''' % verifystatus
        if verify_specified:
            testprocedure += '''

::VERIFYFILES::
'''
        for to_verify in verify_specified:
            testprocedure += '%s\n' % to_verify

        # testprocedure must be encoded since it contains mRSL code and
        # keywords that may interfere with the runtime environment keywords
        # in reality it is \n::KEYWORD::\n lines that may cause problems.
        # For now the string is simply base64 encoded

        content += '''::TESTPROCEDURE::
%s

'''\
             % base64.encodestring(testprocedure).strip()

        #print "testprocedure %s decoded %s" % \
        #      (testprocedure,
        #      base64.decodestring(base64.encodestring(testprocedure).strip()))

    for software_ele in software:
        content += '''::SOFTWARE::
%s

''' % software_ele.strip()

    for environment_ele in environment:
        content += '''::ENVIRONMENTVARIABLE::
%s

'''\
             % environment_ele.strip()

    try:
        (filehandle, tmpfile) = tempfile.mkstemp(text=True)
        os.write(filehandle, content)
        os.close(filehandle)
    except Exception as err:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error preparing new runtime environment! %s'
                               % err})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    (retval, retmsg) = create_runtimeenv(tmpfile, client_id,
            configuration)
    if not retval:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error creating new runtime environment: %s'
                               % retmsg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    try:
        os.remove(tmpfile)
    except Exception:
        pass

    output_objects.append({'object_type': 'text', 'text'
                          : 'New runtime environment %s successfuly created!'
                           % re_name})
    output_objects.append({'object_type': 'link',
                           'destination': 'showre.py?re_name=%s' % re_name,
                           'class': 'viewlink iconspace',
                           'title': 'View your new runtime environment',
                           'text': 'View new %s runtime environment'
                           % re_name,
                           })
    return (output_objects, returnvalues.OK)


