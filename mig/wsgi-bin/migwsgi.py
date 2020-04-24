#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migwsgi.py - Provides the entire WSGI interface
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
import time

import shared.returnvalues as returnvalues
from shared.bailout import bailout_helper, crash_helper, filter_output_objects
from shared.base import requested_page, allow_script
from shared.defaults import download_block_size
from shared.conf import get_configuration_object
from shared.objecttypes import get_object_type_info
from shared.output import validate, format_output, dummy_main, reject_main
from shared.safeinput import valid_backend_name, html_escape
from shared.scriptinput import fieldstorage_to_dict


def object_type_info(object_type):
    """Lookup object type"""

    return get_object_type_info(object_type)


def stub(configuration, client_id, import_path, backend, user_arguments_dict,
         environ):
    """Run backend on behalf of client_id with supplied user_arguments_dict.
    I.e. import main from import_path and execute it with supplied arguments.
    """

    _logger = configuration.logger
    _addr = environ.get('REMOTE_ADDR', 'UNKNOWN')

    before_time = time.time()

    output_objects = []
    main = dummy_main

    # IMPORTANT: we cannot trust potentially user-provided backend value.
    #            NEVER print/output it verbatim before it is validated below.

    try:
        valid_backend_name(backend)

        # Import main from backend module

        exec 'from %s import main' % import_path
    except Exception, err:
        _logger.error("%s could not import %s: %s" % (_addr, import_path, err))
        bailout_helper(configuration, backend, output_objects)
        output_objects.extend([
            {'object_type': 'error_text', 'text':
             'Could not load backend: %s' % html_escape(backend)},
            {'object_type': 'link', 'text': 'Go to default interface',
             'destination': configuration.site_landing_page}
        ])
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Now backend value is validated to be safe for output

    if not isinstance(user_arguments_dict, dict):
        _logger.error("%s invalid user args %s for %s" % (_addr,
                                                          user_arguments_dict,
                                                          import_path))
        bailout_helper(configuration, backend, output_objects,
                       header_text='Input Error')
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'User input is not on expected format!'})
        return (output_objects, returnvalues.INVALID_ARGUMENT)

    try:

        # TODO: add environ arg to all main backends and pass it here

        (output_objects, (ret_code, ret_msg)) = main(client_id,
                                                     user_arguments_dict)
    except Exception, err:
        import traceback
        _logger.error("%s script crashed:\n%s" % (_addr,
                                                  traceback.format_exc()))
        crash_helper(configuration, backend, output_objects)
        return (output_objects, returnvalues.ERROR)

    (val_ret, val_msg) = validate(output_objects)
    if not val_ret:
        (ret_code, ret_msg) = returnvalues.OUTPUT_VALIDATION_ERROR
        bailout_helper(configuration, backend, output_objects,
                       header_text="Validation Error")
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Output validation error! %s' % val_msg})
    after_time = time.time()
    output_objects.append({'object_type': 'timing_info', 'text':
                           "done in %.3fs" % (after_time - before_time)})
    return (output_objects, (ret_code, ret_msg))


# ## Main ###

def application(environ, start_response):
    """MiG app called automatically by wsgi"""

    # TODO: verify security of this environment exposure

    # pass environment on to sub handlers

    os.environ = environ

    # TODO: we should avoid print calls completely in backends
    # make sure print calls do not interfere with wsgi

    sys.stdout = sys.stderr
    configuration = get_configuration_object()
    _logger = configuration.logger

    # get and log ID of user currently logged in

    # We can't import helper before environ is ready because it indirectly
    # tries to use pre-mangled environ for conf loading

    from shared.httpsclient import extract_client_id
    client_id = extract_client_id(configuration, environ)

    # default to html

    default_content = 'text/html'
    output_format = 'html'

    backend = "UNKNOWN"
    output_objs = []
    try:
        if not configuration.site_enable_wsgi:
            _logger.error("WSGI interface is disabled in configuration")
            raise Exception("WSGI interface not enabled for this site")

        fieldstorage = cgi.FieldStorage(fp=environ['wsgi.input'],
                                        environ=environ)
        user_arguments_dict = fieldstorage_to_dict(fieldstorage)
        if user_arguments_dict.has_key('output_format'):
            output_format = user_arguments_dict['output_format'][0]

        # Environment contains python script _somewhere_ , try in turn
        # and fall back to dashboard if all fails
        script_path = requested_page(environ, configuration.site_landing_page)
        script_name = os.path.basename(script_path)
        backend = os.path.splitext(script_name)[0]
        module_path = 'shared.functionality.%s' % backend
        (allow, msg) = allow_script(configuration, script_name, client_id)
        if allow:
            (output_objs, ret_val) = stub(configuration, client_id,
                                          module_path, backend,
                                          user_arguments_dict, environ)
        else:
            (output_objs, ret_val) = reject_main(client_id,
                                                 user_arguments_dict)
        status = '200 OK'
    except Exception, exc:
        _logger.error("handling of WSGI request for %s from %s failed: %s" %
                      (backend, client_id, exc))
        status = '500 ERROR'
        crash_helper(configuration, backend, output_objs)
        output_objs.append(
            {'object_type': 'link', 'text': 'Go to default interface',
             'destination': configuration.site_landing_page})
        ret_val = returnvalues.SYSTEM_ERROR

    (ret_code, ret_msg) = ret_val

    if 'json' == output_format:
        default_content = 'application/json'
    elif 'html' != output_format:
        default_content = 'text/plain'
    default_headers = [('Content-Type', default_content)]
    start_entry = None
    for entry in output_objs:
        if entry['object_type'] == 'start':
            start_entry = entry
    if not start_entry:
        # _logger.debug("WSGI adding explicit headers: %s" % default_headers)
        start_entry = {'object_type': 'start', 'headers': default_headers}
        output_objs = [start_entry] + output_objs
    elif not start_entry.get('headers', []):
        # _logger.debug("WSGI adding missing headers: %s" % default_headers)
        start_entry['headers'] = default_headers
    response_headers = start_entry['headers']

    output = format_output(configuration, ret_code,
                           ret_msg, output_objs, output_format)

    # Explicit None means error during output formatting - empty string is okay

    if output is None:
        output_filtered = filter_output_objects(configuration, output_objs)
        _logger.error("WSGI %s output formatting failed: %s" %
                      (output_format, output_filtered))
        output = 'Error: output could not be correctly delivered!'

    content_length = len(output)
    if not [i for i in response_headers if 'Content-Length' == i[0]]:
        # _logger.debug("WSGI adding explicit content length %s" % content_length)
        response_headers.append(('Content-Length', str(content_length)))

    start_response(status, response_headers)

    # NOTE: we consistently hit download error for archive files reaching ~2GB
    #       with showfreezefile.py on wsgi but the same on cgi does NOT suffer
    #       the problem for the exact same files. It seems wsgi has a limited
    #       output buffer, so we explicitly force significantly smaller chunks
    #       here as a workaround.
    chunk_parts = 1
    if content_length > download_block_size:
        chunk_parts = content_length / download_block_size
        if content_length % download_block_size != 0:
            chunk_parts += 1
        _logger.info("WSGI %s yielding %d output parts (%db)" %
                     (backend, chunk_parts, content_length))
    for i in xrange(chunk_parts):
        # _logger.debug("WSGI %s yielding part %d / %d output parts" % \
        #             (backend, i+1, chunk_parts))
        # end index may be after end of content - but no problem
        part = output[i*download_block_size:(i+1)*download_block_size]
        yield part
    if chunk_parts > 1:
        _logger.info("WSGI %s finished yielding all %d output parts" %
                     (backend, chunk_parts))
