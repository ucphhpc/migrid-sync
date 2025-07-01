#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cgiscriptstub - cgi wrapper functions for functionality backends
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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
import os
import sys
import time

# DUMMY try/except to avoid autopep8 from mangling import order
try:
    cgitb.enable()
except:
    pass

from mig.lib.xgicore import get_output_format, override_output_format, \
    fill_start_headers
from mig.shared.bailout import crash_helper
from mig.shared.base import requested_backend, allow_script, \
    is_default_str_coding, force_default_str_coding_rec
from mig.shared.conf import get_configuration_object
from mig.shared.httpsclient import extract_client_id
from mig.shared.output import format_output, reject_main
from mig.shared.returnvalues import CLIENT_ERROR
from mig.shared.scriptinput import fieldstorage_to_dict


def init_cgi_script(environ, delayed_input=None):
    """Shared init"""
    configuration = get_configuration_object()
    logger = configuration.logger

    # get and log ID of user currently logged in

    client_id = extract_client_id(configuration, environ)
    if client_id:
        logger.info('script: %s , client id: %r' %
                    (requested_backend(environ, strip_ext=False), client_id))
    else:
        logger.debug('script: %s , no client ID available in SSL session' %
                     requested_backend(environ, strip_ext=False))
    if not delayed_input:
        fieldstorage = cgi.FieldStorage()
        user_arguments_dict = fieldstorage_to_dict(fieldstorage)
    else:
        user_arguments_dict = {'__DELAYED_INPUT__': delayed_input}
    return (configuration, logger, client_id, user_arguments_dict)


def finish_cgi_script(configuration, backend, output_format, ret_code, ret_msg,
                      output_objs):
    """Shared finalization"""

    logger = configuration.logger
    start_entry = fill_start_headers(configuration, output_objs, output_format)
    headers = start_entry['headers']

    output = format_output(configuration, backend, ret_code, ret_msg,
                           output_objs, output_format)

    # Explicit None means fatal error in output formatting.
    # An empty string on the other hand is quite okay.

    if output is None:
        logger.error("CGI %s output formatting failed!" % output_format)
        output = 'Error: output could not be correctly delivered!'

    if output_format != 'file' and not is_default_str_coding(output):
        logger.error(
            "Formatted output is NOT on default str coding: %s" % [output[:100]])
        err_mark = '__****__'
        output = format_output(configuration, backend, ret_code, ret_msg,
                               force_default_str_coding_rec(
                                   output_objs, highlight=err_mark),
                               output_format)
        logger.warning(
            "forced output to default coding with highlight: %s" % err_mark)

    header_out = '\n'.join(["%s: %s" % (key, val) for (key, val) in headers])

    # NOTE: we need to carefully handle byte output here as well
    # https://stackoverflow.com/questions/40450791/python-cgi-print-image-to-html

    try:
        #logger.debug("write headers: %s" % header_out)
        sys.stdout.write(header_out)
        sys.stdout.write("\n\n")
        #logger.debug("flush stdout")
        sys.stdout.flush()
        #logger.debug("write content: %s" % [output[:64], '..', output[-64:]])
        # NOTE: always output native strings to stdout but use raw buffer
        #       for byte output on py3 as explained above.
        if sys.version_info[0] < 3 or is_default_str_coding(output):
            sys.stdout.write(output)
        else:
            sys.stdout.buffer.write(output)
        # logger.debug("complete")
    except Exception as exc:
        logger.error("CGI output delivery crashed: %s" % exc)


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

    logger.debug("handling cgi request with python %s from %s  (%s)" %
                 (sys.version_info, client_id, environ))

    output_format = get_output_format(configuration, user_arguments_dict)

    # TODO: add environ arg support to all main backends and use here

    script_name = requested_backend(environ, strip_ext=False)
    backend = requested_backend(environ)
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

    # TODO: drop delay_format and rely on shared override_format marker instead
    if delay_format:
        output_format = get_output_format(configuration, user_arguments_dict)

    # NOTE: optional output_format override if backend requests it in start
    output_format = override_output_format(configuration, user_arguments_dict,
                                           out_obj, output_format)

    finish_cgi_script(configuration, backend, output_format,
                      ret_code, ret_msg, out_obj)


def run_cgi_script(main, delayed_input=None, delay_format=False):
    """Just a wrapper for run_cgi_script_possibly_with_cert now since we always
    verify client_id in backend anyway and have easier access to outputting a
    sane help page there.
    """
    return run_cgi_script_possibly_with_cert(main, delayed_input, delay_format)
