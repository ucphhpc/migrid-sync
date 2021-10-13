#!/usr/bin/env python-version-from-mod-wsgi
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migwsgi.py - Provides the entire WSGI interface
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

from builtins import range
import cgi
import importlib
import os
import sys
import time

from mig.shared import returnvalues
from mig.shared.bailout import bailout_helper, crash_helper
from mig.shared.base import requested_page, allow_script, \
    is_default_str_coding, force_native_str_rec, force_utf8, force_utf8_rec
from mig.shared.defaults import download_block_size, default_fs_coding
from mig.shared.conf import get_configuration_object
from mig.shared.objecttypes import get_object_type_info
from mig.shared.output import validate, format_output, dummy_main, reject_main
from mig.shared.safeinput import valid_backend_name, html_escape, InputException
from mig.shared.scriptinput import fieldstorage_to_dict


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

    _logger.debug("stub for backend %r" % backend)

    # IMPORTANT: we cannot trust potentially user-provided backend value.
    #            NEVER print/output it verbatim before it is validated below.

    try:
        valid_backend_name(backend)
    except InputException as iex:
        _logger.error("%s refused to import invalid backend %r (%s): %s" %
                      (_addr, backend, import_path, iex))
        bailout_helper(configuration, backend, output_objects,
                       header_text='User Error')
        output_objects.extend([
            {'object_type': 'error_text', 'text':
             'Invalid backend: %s' % html_escape(backend)},
            {'object_type': 'link', 'text': 'Go to default interface',
             'destination': configuration.site_landing_page}
        ])
        return (output_objects, returnvalues.CLIENT_ERROR)

    try:
        # Import main from backend module

        #_logger.debug("import main from %r" % import_path)
        # NOTE: dynamic module loading to find corresponding main function
        module_handle = importlib.import_module(import_path)
        main = module_handle.main
    except Exception as err:
        _logger.error("%s could not import %r (%s): %s" %
                      (_addr, backend, import_path, err))
        bailout_helper(configuration, backend, output_objects)
        output_objects.extend([
            {'object_type': 'error_text', 'text':
             'Could not load backend: %s' % html_escape(backend)},
            {'object_type': 'link', 'text': 'Go to default interface',
             'destination': configuration.site_landing_page}
        ])
        return (output_objects, returnvalues.SYSTEM_ERROR)

    #_logger.debug("imported main %s" % main)

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
    except Exception as err:
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

    # TODO: verify security of this environment exposure or limit to known vars
    # NOTE: pass environment on to sub handlers

    os.environ = environ

    # NOTE: enable to debug runtime environment to apache error log
    # print("DEBUG: python %s" %
    #      (sys.version_info, ), file=environ['wsgi.errors'])
    #print("DEBUG: path %s" % sys.path, file=environ['wsgi.errors'])

    # TODO: we should avoid print calls completely in backends
    # make sure print calls do not interfere with wsgi

    # NOTE: redirect stdout to stderr in python 2 only. It breaks logger in 3
    #       and stdout redirection apparently is already handled there.
    if sys.version_info[0] < 3:
        sys.stdout = sys.stderr

    configuration = get_configuration_object()
    _logger = configuration.logger

    # get and log ID of user currently logged in

    # We can't import helper before environ is ready because it indirectly
    # tries to use pre-mangled environ for conf loading

    from mig.shared.httpsclient import extract_client_id
    client_id = extract_client_id(configuration, environ)

    # default to html

    default_content = 'text/html'
    output_format = 'html'

    backend = "UNKNOWN"
    output_objs = []
    user_arguments_dict = {}

    _logger.debug("handling wsgi request with python %s from %s" %
                  (sys.version_info, client_id))
    default_enc, fs_enc = sys.getdefaultencoding(), sys.getfilesystemencoding()
    _logger.debug("using %s default and %s file system encoding" %
                  (default_enc, fs_enc))
    # IMPORTANT: we want to avoid 'ascii' as file system encoding, which is
    #            the default here on Python3 unless environment is correctly
    #            set up. If so it breaks actual utf8 paths and thus client_id
    #            by rendering them with unicode surrogate codes.
    if fs_enc != 'utf-8' and default_fs_coding == 'utf8':
        _logger.error("Expected utf-8 filesys encoding but found %r!" % fs_enc)

    try:
        if not configuration.site_enable_wsgi:
            _logger.error("WSGI interface is disabled in configuration")
            raise Exception("WSGI interface not enabled for this site")

        fieldstorage = cgi.FieldStorage(fp=environ['wsgi.input'],
                                        environ=environ)
        user_arguments_dict = fieldstorage_to_dict(fieldstorage)
        if 'output_format' in user_arguments_dict:
            output_format = user_arguments_dict['output_format'][0]

        # Environment contains python script _somewhere_ , try in turn
        # and fall back to dashboard if all fails
        script_path = requested_page(environ, configuration.site_landing_page)
        script_name = os.path.basename(script_path)
        backend = os.path.splitext(script_name)[0]
        # _logger.debug("handling wsgi %r request from %s" %
        #              (backend, client_id))
        module_path = 'mig.shared.functionality.%s' % backend
        (allow, msg) = allow_script(configuration, script_name, client_id)
        if allow:
            #_logger.debug("wsgi handling script: %s" % script_name)
            (output_objs, ret_val) = stub(configuration, client_id,
                                          module_path, backend,
                                          user_arguments_dict, environ)
        else:
            _logger.warning("wsgi handling refused script:%s" % script_name)
            (output_objs, ret_val) = reject_main(client_id,
                                                 user_arguments_dict)
        status = '200 OK'
    except Exception as exc:
        import traceback
        _logger.error("wsgi handling crashed:\n%s" % traceback.format_exc())
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

    _logger.debug("call format %r output to %s" % (backend, output_format))
    output = format_output(configuration, backend, ret_code, ret_msg,
                           output_objs, output_format)
    #_logger.debug("formatted %s output to %s" % (backend, output_format))
    #_logger.debug("output:\n%s" % [output])

    if not is_default_str_coding(output):
        _logger.error(
            "Formatted output is NOT on default str coding: %s" % [output[:100]])
        err_mark = '__****__'
        output = format_output(configuration, backend, ret_code, ret_msg,
                               force_native_str_rec(output_objs,
                                                    highlight=err_mark),
                               output_format)
        _logger.warning(
            "forced output to default coding with highlight: %s" % err_mark)

    # Explicit None means fatal error in output formatting.
    # An empty string on the other hand is quite okay.

    if output is None:
        _logger.error("WSGI %s output formatting failed" % output_format)
        output = 'Error: output could not be correctly delivered!'

    content_length = len(output)
    if not [i for i in response_headers if 'Content-Length' == i[0]]:
        # _logger.debug("WSGI adding explicit content length %s" % content_length)
        response_headers.append(('Content-Length', "%d" % content_length))

    _logger.debug("send %r response as %s to %s" %
                  (backend, output_format, client_id))
    # NOTE: send response to client but don't crash e.g. on closed connection
    try:
        # IMPORTANT: headers must be on native string format here
        native_headers = force_native_str_rec(response_headers)
        #_logger.debug("native headers: %s" % native_headers)
        start_response(status, native_headers)
        #_logger.debug("started response to client")

        # NOTE: we consistently hit download error for archive files reaching ~2GB
        #       with showfreezefile.py on wsgi but the same on cgi does NOT suffer
        #       the problem for the exact same files. It seems wsgi has a limited
        #       output buffer, so we explicitly force significantly smaller chunks
        #       here as a workaround.
        chunk_parts = 1
        if content_length > download_block_size:
            chunk_parts = content_length // download_block_size
            if content_length % download_block_size != 0:
                chunk_parts += 1
            _logger.info("WSGI %s yielding %d output parts (%db)" %
                         (backend, chunk_parts, content_length))
        #_logger.debug("send chunked %r response to client" % backend)
        for i in range(chunk_parts):
            # _logger.debug("WSGI %s yielding part %d / %d output parts" %
            #              (backend, i+1, chunk_parts))
            # end index may be after end of content - but no problem
            part = output[i*download_block_size:(i+1)*download_block_size]
            #_logger.debug("yield %r chunk to client" % backend)
            # IMPORTANT: bytes are required here for all python versions
            yield force_utf8(part)
        if chunk_parts > 1:
            _logger.info("WSGI %s finished yielding all %d output parts" %
                         (backend, chunk_parts))
        _logger.debug("done sending %d chunk(s) of %r response to client" %
                      (chunk_parts, backend))
    except IOError as ioe:
        _logger.warning("WSGI %s for %s could not deliver output: %s" %
                        (backend, client_id, ioe))
    except Exception as exc:
        _logger.error("WSGI %s for %s crashed during response: %s" %
                      (backend, client_id, exc))
