#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cgiscriptstub - cgi wrapper functions for functionality backends
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Interface between CGI and functionality"""
from __future__ import print_function
from __future__ import absolute_import

import cgi
import cgitb
cgitb.enable()
import os
import time

from .shared.bailout import crash_helper
from .shared.base import requested_page, allow_script
from .shared.conf import get_configuration_object
from .shared.httpsclient import extract_client_id
from .shared.output import format_output, reject_main
from .shared.returnvalues import CLIENT_ERROR
from .shared.scriptinput import fieldstorage_to_dict


def init_cgi_script(environ, delayed_input=None):
    """Shared init"""
    configuration = get_configuration_object()
    logger = configuration.logger

    # get and log ID of user currently logged in

    client_id = extract_client_id(configuration, environ)
    logger.info('script: %s cert: %s' % (requested_page(), client_id))
    if not delayed_input:
        fieldstorage = cgi.FieldStorage()
        user_arguments_dict = fieldstorage_to_dict(fieldstorage)
    else:
        user_arguments_dict = {'__DELAYED_INPUT__': delayed_input}
    return (configuration, logger, client_id, user_arguments_dict)


def finish_cgi_script(configuration, output_format, ret_code, ret_msg,
                      output_objs):
    """Shared finalization"""

    default_content = 'text/html'
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
        start_entry = {'object_type': 'start', 'headers': default_headers}
        output_objs = [start_entry] + output_objs
    elif not start_entry.get('headers', []):
        start_entry['headers'] = default_headers
    headers = start_entry['headers']

    output = format_output(configuration, ret_code, ret_msg, output_objs,
                           output_format)

    # Explicit None means error during output formatting - empty string is okay

    if output is None:
        output = 'Error: output could not be correctly delivered!'

    header_out = '\n'.join(["%s: %s" % (key, val) for (key, val) in headers])

    # configuration.logger.debug("raw output:\n%s\n%s" % (header_out, output))

    print(header_out)
    print('')

    # Print without adding newline

    print(output, end=' ')


def run_cgi_script_possibly_with_cert(main, delayed_input=None,
                                      delay_format=False):
    """Get needed information and run the function received as argument.
    If delayed_input is not set to a function, the default cgi input will be
    extracted and parsed before being passed on to the main function. Some
    CGI operations like file upload won't work efficiently if the fieldstorage
    is passed around (huge memory consumption) so they can pass the form
    extracting function here and leave it to the back end to extract the
    form.
    Use the optional delay_format argument to delay output format evaluation
    until after running main so that it can override the format if needed.
    This is useful if some backends need to output e.g. a raw xrds document
    when called without explicit format like we do in oiddiscover.
    """

    before_time = time.time()
    # Always rely on os.environ here since only called from cgi scripts
    environ = os.environ
    (configuration, logger, client_id, user_arguments_dict) = \
        init_cgi_script(environ, delayed_input)

    # default to html output

    output_format = user_arguments_dict.get('output_format', ['html'])[-1]

    # TODO: add environ arg support to all main backends and use here

    script_name = os.path.basename(environ.get('SCRIPT_NAME', 'UNKNOWN'))
    backend = os.path.splitext(script_name)[0]
    logger.debug("check allow script %s from %s" % (script_name, client_id))
    (allow, msg) = allow_script(configuration, script_name, client_id)
    out_obj, ret_code, ret_msg = [], 0, ''
    try:
        if not allow:
            logger.warning("script %s rejected: %s" % (script_name, msg))
            # Override main function with reject helper
            main = reject_main
        (out_obj, (ret_code, ret_msg)) = main(client_id, user_arguments_dict)
    except:
        import traceback
        logger.error("script crashed:\n%s" % traceback.format_exc())
        crash_helper(configuration, backend, out_obj)

    after_time = time.time()
    out_obj.append({'object_type': 'timing_info', 'text':
                    "done in %.3fs" % (after_time - before_time)})
    if delay_format:
        output_format = user_arguments_dict.get('output_format', ['html'])[-1]

    finish_cgi_script(configuration, output_format, ret_code, ret_msg, out_obj)


def run_cgi_script(main, delayed_input=None, delay_format=False):
    """Just a wrapper for run_cgi_script_possibly_with_cert now since we always
    verify client_id in backend anyway and have easier access to outputting a
    sane help page there.
    """
    return run_cgi_script_possibly_with_cert(main, delayed_input, delay_format)
