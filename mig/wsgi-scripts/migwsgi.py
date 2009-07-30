#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migwsgi.py - Provides the entire WSGI interface
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
import sys
import cgi

import shared.returnvalues as returnvalues
from shared.cgiinput import fieldstorage_to_dict
from shared.httpsclient import extract_client_id
from shared.objecttypes import get_object_type_info
from shared.output import validate, format_output


def object_type_info(object_type):
    """Lookup object type"""

    return get_object_type_info(object_type)


def my_id():
    """Return DN of user currently logged in"""

    return extract_client_id()


def stub(function, user_arguments_dict):
    """Run backend function with supplied arguments"""

    # get ID of user currently logged in

    main = id
    client_id = extract_client_id()
    output_objects = []
    try:
        exec 'from %s import main' % function
    except Exception, err:
        output_objects.extend([{'object_type': 'error_text', 'text'
                              : 'Could not import module! %s: %s'
                               % (function, err)}])
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not isinstance(user_arguments_dict, dict):
        output_objects.extend([{'object_type': 'error_text', 'text'
                              : 'user_arguments_dict is not a dictionary/struct type!'
                              }])
        return (output_objects, returnvalues.INVALID_ARGUMENT)

    return_val = returnvalues.OK
    try:

        # return (user_arguments_dict)

        (output_objects, return_val) = main(client_id,
                user_arguments_dict)
    except Exception, err:
        output_objects.extend([{'object_type': 'error_text', 'text'
                              : 'Error calling function: %s' % err}])
        return (output_objects, returnvalues.ERROR)

    (val_ret, val_msg) = validate(output_objects)
    if not val_ret:
        return_val = returnvalues.OUTPUT_VALIDATION_ERROR

        # remove previous output
        # output_objects = []

        output_objects.extend([{'object_type': 'error_text', 'text'
                              : 'Validation error! %s' % val_msg},
                              {'object_type': 'title', 'text'
                              : 'Validation error!'}])
    return (output_objects, return_val)


# ## Main ###


def basic_application(environ, start_response):
    """Sample app called automatically by wsgi"""

    status = '200 OK'
    output = 'Hello World!'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]


def application(environ, start_response):
    """MiG app called automatically by wsgi"""

    # TODO: verify security of this environment exposure
    
    # pass environment on to sub handlers

    os.environ = environ

    # TODO: we should avoid print calls completely in backends
    # make sure print calls do not interfere with wsgi

    sys.stdout = sys.stderr
    fieldstorage = cgi.FieldStorage(fp=environ['wsgi.input'],
                                    environ=environ)
    user_arguments_dict = fieldstorage_to_dict(fieldstorage)

    # default to html

    output_format = 'html'
    if user_arguments_dict.has_key('output_format'):
        output_format = user_arguments_dict['output_format'][0]

    try:
        backend = os.path.basename(environ['SCRIPT_URL']).replace('.py'
                , '')
        module_path = 'shared.functionality.%s' % backend
        (output_objs, ret_val) = stub(module_path, user_arguments_dict)
    except Exception, exc:
        (output_objs, ret_val) = ([{'object_type': 'error_text', 'text'
                                  : exc}, {'object_type': 'text', 'text'
                                  : str(environ)}],
                                  returnvalues.SYSTEM_ERROR)
    if returnvalues.OK == ret_val:
        status = '200 OK'
    else:
        status = '403 ERROR'

    (ret_code, ret_msg) = ret_val

    default_content = 'text/html'
    if 'html' != output_format:
        default_content = 'text/plain'
    default_headers = [('Content-Type', default_content)]
    start_entry = None
    for entry in output_objs:
        if entry['object_type'] == 'start':
            start_entry = entry
    if not start_entry:
        start_entry = {'object_type': 'start', 'headers': default_headers}
        output_objs = [start_entry] + output_objs
    elif not start_entry.get('headers', []):
        start_entry['headers'] = default_headers
    response_headers = start_entry['headers']

    output = format_output(ret_code, ret_msg, output_objs, output_format)
    if not [i for i in response_headers if 'Content-Length' == i[0]]:
        response_headers.append(('Content-Length', str(len(output))))
    if not output:

        # Error occured during output print

        output = 'Output could _not_ be extracted!'

    start_response(status, response_headers)

    return [output]


