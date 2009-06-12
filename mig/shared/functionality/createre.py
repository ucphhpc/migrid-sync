#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createre - [insert a few words of module description on this line]
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

import os
import base64
import tempfile

from shared.refunctions import create_runtimeenv
from shared.validstring import valid_dir_input
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


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


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
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
    re_name = accepted['re_name'][-1].strip().upper()
    redescription = accepted['redescription'][-1].strip()
    testprocedure = accepted['testprocedure'][-1].strip()
    software = accepted['software']
    environment = accepted['environment']
    verifystdout = accepted['verifystdout'][-1].strip()
    verifystderr = accepted['verifystderr'][-1].strip()
    verifystatus = accepted['verifystatus'][-1].strip()
    output_objects.append({'object_type': 'header', 'text'
                          : 'Create runtime environment'})

    software_entries = len(software)
    max_software_entries = 40
    if software_entries > max_software_entries:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many software entries specified (%s), max %s'
                               % (software_entries,
                              max_software_entries)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    environment_entries = len(environment)
    max_environment_entries = 40
    if environment_entries > max_environment_entries:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many environment entries specified (%s), max %s'
                               % (environment_entries,
                              max_environment_entries)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create file to be parsed - force single line description

    content = """::RENAME::
%s

::DESCRIPTION::
%s

""" % (re_name,
            redescription.replace('\n', '<br>'))

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

        # testprocedure must be encoded since it contains mRSL code and keywords that may interfere with the runtime environment keywords
        # in reality it is \n::KEYWORD::\n lines that may cause problems. For now the string is simply base64 encoded

        content += '''::TESTPROCEDURE::
%s

'''\
             % base64.encodestring(testprocedure).strip()

        # print "testprocedure %s decoded %s" % (testprocedure, base64.decodestring(base64.encodestring(testprocedure).strip()))

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
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Exception writing temporary runtime environment file. New runtime environment not created! %s'
                               % err})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    (retval, retmsg) = create_runtimeenv(tmpfile, cert_name_no_spaces,
            configuration)
    if not retval:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error during creation of new runtime environment: %s'
                               % retmsg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    try:
        os.remove(tmpfile)
    except Exception, exc:
        pass

    output_objects.append({'object_type': 'text', 'text'
                          : 'New runtime environment %s successfuly created!'
                           % re_name})
    return (output_objects, returnvalues.OK)


