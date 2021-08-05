#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rangefileaccess - read or write byte range inside file
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

"""CGI module that enables MiG jobs to perform ranged GET/PUT and
DELETE http requests.
NOTE: ranges (filepositions) are handled according to the w3c HTTP
standard rfc2616.
"""

from __future__ import absolute_import

import os
import sys

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.fileio import check_write_access
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {
        'path': REJECT_UNSET,
        'filename': [''],
        'iosessionid': [''],
        'file_startpos': [-1],
        'file_endpos': [-1],
    }
    return ['', defaults]


def do_get(configuration, output_objects, abs_path, start_pos, end_pos):
    """Extract and return specified byte range from abs_path"""
    _logger = configuration.logger
    try:
        filelen = os.path.getsize(abs_path)
        filehandle = open(abs_path, 'rb')
    except Exception as err:
        # TODO: add output_objects?
        _logger.error('rangefileaccess get: %s' % err)
        return False

    if start_pos < 0:
        start_pos = 0
    if end_pos == -1 or end_pos > filelen - 1:
        end_pos = filelen - 1

    # Startpos is after end of file

    if start_pos >= filelen:
        # TODO: add output_objects?
        _logger.error('start_pos: %s after end of file: %s '
                      % (start_pos, filelen))
        return False
    elif start_pos > end_pos:
        # Apache handles 'start_pos>end_pos' by serving the whole file
        # Due to compatibility, so do we.
        start_pos = 0
        end_pos = filelen - 1

    datalen = end_pos - start_pos + 1

    # _logger.debug("file_start: %s" % start_pos)
    # _logger.debug("file_end: %s" % end_pos)
    # _logger.debug("filelen: %s" % filelen)
    # _logger.debug("datalen: %s" % datalen)

    # Note that we do not use CGIOutput for data, due to performance issues,
    # We do however use the cgi protocol: status + \n + data
    # If seek fails, abort.

    try:
        filehandle.seek(start_pos, 0)
    except Exception as err:
        _logger.error("Seeking File: '%s' failed: %s\n" % (err, abs_path))
        # TODO: add output_objects?
        return False

    # If write fails, do nothing, it's up to the client,
    # to find out how many bytes were actually sent to him.

    read_status = True
    output_lines = []
    try:

        # Write status

        # sys.stdout.write('0\n')
        # sys.stdout.flush()

        # Write data in chuncks of 'block_size'
        # This is done as large files will fill up the buffers
        # and use up the servers memory, if flush'es are not made frequently

        block_size = 65536

        bytes_left = datalen
        while bytes_left > 0:
            if bytes_left < block_size:
                block_size = bytes_left
            # sys.stdout.write(filehandle.read(block_size))
            # sys.stdout.flush()
            output_lines.append(filehandle.read(block_size))
            bytes_left -= block_size
        entry = {'object_type': 'file_output',
                 'lines': output_lines,
                 'wrap_binary': True,
                 'wrap_targets': ['lines']}

    except Exception as err:
        # TODO: add output_objects?
        _logger.error("Reading File: %r failed: %s" % (err, abs_path))
        read_status = False

    # If close fails, do nothing

    try:
        filehandle.close()
    except Exception as err:
        _logger.error("Closing File: %r failed: %s" % (err, abs_path))
        read_status = False

    return read_status


def do_put(configuration, output_objects, abs_path, start_pos, end_pos):
    """Write inline content to specified byte range in abs_path"""
    _logger = configuration.logger

    # Convert content_length to int
    try:
        content_length = int(os.getenv('CONTENT_LENGTH'))
    except Exception as err:
        content_length = 0

    # If file exists we update it, otherwise it is created.

    if os.path.isfile(abs_path):
        try:
            filehandle = open(abs_path, 'r+b')
        except Exception as err:
            _logger.error('failed to open %s for writing: %s' % (abs_path,
                                                                 err))
            # TODO: add output_objects?
            return False
    else:
        try:
            filehandle = open(abs_path, 'w+b')
        except Exception as err:
            _logger.error('failed to create %s for writing: %s' % (abs_path,
                                                                   err))
            # TODO: add output_objects?
            return False

    # If content_length is 0, we do nothing
    # and an empty file is created if file doesn't exist.

    datalen = 0
    if content_length > 0:
        if start_pos == -1 and end_pos != -1:

            # If start_pos not given use fileend_pos and content_length

            start_pos = (end_pos - content_length) - 1
        elif start_pos != -1 and end_pos == -1 or start_pos\
                != -1 and end_pos - start_pos > content_length - 1:

            # If end_pos not given or end_pos exceeds the amount
            # of data retrieved, use filestart_pos and content_length

            end_pos = (start_pos + content_length) - 1
        elif start_pos == -1 and end_pos == -1:

            # Write the whole file

            start_pos = 0
            end_pos = content_length - 1

        datalen = end_pos - start_pos + 1

        # _logger.debug("file_start: %s" % start_pos)
        # _logger.debug("file_end: %s" % end_pos)
        # _logger.debug("content: %s" % content_length)
        # _logger.debug("datalen: %s" % datalen)

        try:
            filehandle.seek(start_pos, 0)
            filehandle.write(sys.stdin.read(datalen))
        except Exception as err:
            _logger.error('failed to write data range to %s: %s' % (abs_path,
                                                                    err))
            # TODO: add output_objects?
            return False

        try:
            filehandle.close()
        except Exception as err:
            _logger.error('failed to close %s after writing: %s' % (abs_path,
                                                                    err))
            # TODO: add output_objects?
            return False

    _logger.info("File %r <- %s bytes written successfully" % (abs_path,
                                                               datalen))
    return True


def do_delete(configuration, output_objects, abs_path):
    """Actually delete abs_path"""
    _logger = configuration.logger
    rel_path = os.path.basename(abs_path)
    try:
        os.remove(abs_path)
    except Exception as err:
        configuration.logger.warning("could not delete %s" % abs_path)
        return False
    return True


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    # TODO: this handler is incomplete and NOT yet hooked up with Xgi-bin
    return (output_objects, returnvalues.SYSTEM_ERROR)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(
        user_arguments_dict,
        defaults,
        output_objects,
        allow_rejects=False,
        # NOTE: path cannot use wildcards here
        typecheck_overrides={},
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    filename = accepted['filename'][-1]
    patterns = accepted['path']
    iosessionid = accepted['iosessionid'][-1]
    file_startpos = accepted['file_startpos'][-1]
    file_endpos = accepted['file_endpos'][-1]

    if file_startpos:
        file_startpos = int(file_startpos)
    else:
        file_startpos = -1
    if file_endpos:
        file_endpos = int(file_endpos)
    else:
        file_endpos = -1

    # Legacy naming
    if filename:
        patterns = [filename]

    valid_methods = ['GET', 'PUT', 'DELETE']
    action = os.getenv('REQUEST_METHOD')
    if not action in valid_methods:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''Only accepting %s requests''' % ', '.join(valid_methods)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # TODO: introduce CSRF protection here when clients support it
    # if not safe_handler(configuration, action, op_name, client_id,
    #                    get_csrf_limit(configuration), accepted):
    #    output_objects.append(
    #        {'object_type': 'error_text', 'text':
    #         '''Only accepting CSRF-filtered POST requests to prevent unintended updates'''
    #         })
    #    return (output_objects, returnvalues.CLIENT_ERROR)

    # Either authenticated user client_id set or job IO session ID
    if client_id:
        user_id = client_id
        target_dir = client_id_dir(client_id)
        base_dir = configuration.user_home
        page_title = 'User range file access'
        widgets = True
        userstyle = True
    elif iosessionid:
        user_id = iosessionid
        target_dir = iosessionid
        base_dir = configuration.webserver_home
        page_title = 'Create Shared Directory'
        widgets = False
        userstyle = False
    else:
        logger.error('%s called without proper auth: %s' % (op_name, accepted))
        output_objects.append({'object_type': 'error_text',
                               'text': 'Authentication is missing!'
                               })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(base_dir, target_dir)) + os.sep

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = page_title
    title_entry['skipwidgets'] = not widgets
    title_entry['skipuserstyle'] = not userstyle
    output_objects.append({'object_type': 'header', 'text': page_title})

    # Input validation assures target_dir can't escape base_dir
    if not os.path.isdir(base_dir):
        output_objects.append({'object_type': 'error_text',
                               'text': 'Invalid client/iosession id!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    for pattern in patterns:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages
        # NB: Globbing disabled on purpose here

        unfiltered_match = [base_dir + os.sep + pattern]
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.warn('%s tried to %s %s restricted path! (%s)'
                            % (client_id, op_name, abs_path, pattern))
                continue
            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append(
                {'object_type': 'error_text',
                 'text': "%s: cannot access file '%s': Permission denied"
                 % (op_name, pattern)})
            status = returnvalues.CLIENT_ERROR

        for abs_path in match:
            relative_path = abs_path.replace(base_dir, '')
        if action == 'GET':
            if not do_get(configuration, output_objects, abs_path,
                          file_startpos, file_endpos):
                output_objects.append({'object_type': 'error_text', 'text':
                                       '''Could not gett %r''' % pattern})
                status = returnvalues.SYSTEM_ERROR
        elif action == 'PUT':
            if not do_put(configuration, output_objects, abs_path,
                          file_startpos, file_endpos):
                output_objects.append({'object_type': 'error_text', 'text':
                                       '''Could not put %r''' % pattern})
                status = returnvalues.SYSTEM_ERROR
        elif action == 'DELETE':
            if not do_delete(configuration, output_objects, abs_path):
                output_objects.append({'object_type': 'error_text', 'text':
                                       '''Could not delete %r''' % pattern})
                status = returnvalues.SYSTEM_ERROR
        else:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Unsupported action: %r' % action})
            return (output_objects, returnvalues.CLIENT_ERROR)

    return (output_objects, status)
