#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cgiscriptstub - [insert a few words of module description on this line]
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

"""Interface between CGI and functionality"""

import sys
import cgi
import cgitb
cgitb.enable()
import time

import shared.returnvalues as returnvalues
from shared.scriptinput import fieldstorage_to_dict
from shared.conf import get_configuration_object
from shared.httpsclient import extract_client_id
from shared.output import format_output

def init_cgi_script(delayed_input=None):
    """Shared init"""
    configuration = get_configuration_object()
    logger = configuration.logger

    # get DN of user currently logged in

    client_id = extract_client_id()
    logger.info('script: %s cert: %s' % (sys.argv[0], client_id))
    if not delayed_input:
        fieldstorage = cgi.FieldStorage()
        user_arguments_dict = fieldstorage_to_dict(fieldstorage)
    else:
        user_arguments_dict = {'__DELAYED_INPUT__': delayed_input}
    return (configuration, logger, client_id, user_arguments_dict)


def finish_cgi_script(configuration, output_format, ret_code, ret_msg, output_objs):
    """Shared finalization"""

    logger = configuration.logger
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

    output = format_output(configuration, ret_code, ret_msg, output_objs, output_format)
    
    # Explicit None means error during output formatting - empty string is okay

    if output == None:
        output = 'Output could _not_ be extracted!'

    header_out = ''
    for (key, val) in headers:
        header_out += "%s: %s\n" % (key, val)
    
    # configuration.logger.debug("raw output:\n%s\n%s" % (header_out, output))
    
    print header_out
    print ''

    # Print without adding newline
    
    print output,

def run_cgi_script(main, delayed_input=None):
    """Get needed information and run the function received as argument.
    If delayed_input is not set to a function, the default cgi input will be
    extracted and parsed before being passed on to the main function. Some
    CGI operations like file upload won't work efficiently if the fieldstorage
    is passed around (huge memory consumption) so they can pass the form
    extracting function here and leave it to the back end to extract the
    form.
    """
    
    before_time = time.time()
    (configuration, logger, client_id, user_arguments_dict) = \
                    init_cgi_script(delayed_input)

    # default to html output

    output_format = user_arguments_dict.get('output_format', ['html'])[-1]

    if client_id:
        (out_obj, (ret_code, ret_msg)) = main(client_id,
                                                  user_arguments_dict)
    else:
        (ret_code, ret_msg) = returnvalues.CLIENT_ERROR
        out_obj = [{'object_type': 'error_text', 'text':
                    'No client ID available from SSL env - not authenticated!'
                    }]
    after_time = time.time()
    out_obj.append({'object_type': 'timing_info', 'text':
                    "done in %.3fs" % (after_time - before_time)})
    finish_cgi_script(configuration, output_format, ret_code, ret_msg, out_obj)


def run_cgi_script_possibly_with_cert(main, delayed_input=None):
    """Get needed information and run the function received as argument.
    If delayed_input is not set to a function, the default cgi input will be
    extracted and parsed before being passed on to the main function. Some
    CGI operations like file upload won't work efficiently if the fieldstorage
    is passed around (huge memory consumption) so they can pass the form
    extracting function here and leave it to the back end to extract the
    form.
    """

    before_time = time.time()
    (configuration, logger, client_id, user_arguments_dict) = \
                    init_cgi_script(delayed_input)

    # default to html output

    output_format = user_arguments_dict.get('output_format', ['html'])[-1]

    (out_obj, (ret_code, ret_msg)) = main(client_id,
            user_arguments_dict)
    after_time = time.time()
    out_obj.append({'object_type': 'timing_info', 'text':
                    "done in %.3fs" % (after_time - before_time)})

    finish_cgi_script(configuration, output_format, ret_code, ret_msg, out_obj)


