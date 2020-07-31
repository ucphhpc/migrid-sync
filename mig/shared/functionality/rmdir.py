#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmdir - remove directory in user home
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Emulate the un*x function with the same name"""
from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.fileio import check_write_access
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.parseflags import parents, verbose
from mig.shared.sharelinks import extract_mode_id
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'path': REJECT_UNSET, 'current_dir': [''], 'flags': [''],
                'share_id': ['']}
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(
        user_arguments_dict,
        defaults,
        output_objects,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    patterns = accepted['path']
    current_dir = accepted['current_dir']
    share_id = accepted['share_id'][-1]

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Either authenticated user client_id set or sharelink ID
    if client_id:
        user_id = client_id
        target_dir = client_id_dir(client_id)
        base_dir = configuration.user_home
        id_query = ''
        page_title = 'Remove User Directory'
        userstyle = True
        widgets = True
    elif share_id:
        try:
            (share_mode, _) = extract_mode_id(configuration, share_id)
        except ValueError as err:
            logger.error('%s called with invalid share_id %s: %s' % \
                         (op_name, share_id, err))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Invalid sharelink ID: %s' % share_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        # TODO: load and check sharelink pickle (currently requires client_id)
        user_id = 'anonymous user through share ID %s' % share_id
        if share_mode == 'read-only':
            logger.error('%s called without write access: %s' % \
                         (op_name, accepted))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'No write access!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        target_dir = os.path.join(share_mode, share_id)
        base_dir = configuration.sharelink_home
        id_query = '?share_id=%s' % share_id
        page_title = 'Remove Shared Directory'
        userstyle = False
        widgets = False
    else:
        logger.error('%s called without proper auth: %s' % (op_name, accepted))
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Authentication is missing!'
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
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid client/sharelink id!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    for pattern in patterns:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages
        # NB: Globbing disabled on purpose here

        unfiltered_match = [base_dir + pattern]
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                continue
            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : "%s: cannot remove directory '%s': Permission denied"
                 % (op_name, pattern)})
            status = returnvalues.CLIENT_ERROR

        for abs_path in match:
            relative_path = abs_path.replace(base_dir, '')
            if verbose(flags):
                output_objects.append({'object_type': 'file', 'name'
                        : relative_path})
            if not os.path.exists(abs_path):
                output_objects.append({'object_type': 'file_not_found',
                        'name': relative_path})
                continue
            if not check_write_access(abs_path):
                logger.warning('%s called without write access: %s' % \
                               (op_name, abs_path))
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'cannot remove "%s": inside a read-only location!' % \
                     pattern})
                status = returnvalues.CLIENT_ERROR
                continue
            try:
                if parents(flags):

                    # Please note that 'rmdir -p X' should give error if X
                    #  doesn't exist contrary to 'mkdir -p X' not giving error
                    # if X exists.

                    os.removedirs(abs_path)
                else:
                    os.rmdir(abs_path)
                logger.info('%s %s done' % (op_name, abs_path))
            except Exception as exc:
                output_objects.append({'object_type': 'error_text',
                        'text': "%s '%s' failed!" % (op_name,
                        relative_path)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                             relative_path, exc))
                status = returnvalues.SYSTEM_ERROR
                continue
            output_objects.append({'object_type': 'text',
                        'text': "removed directory %s" % (relative_path)})

    output_objects.append({'object_type': 'link',
                           'destination': 'ls.py%s' % id_query,
                           'text': 'Return to files overview'})
    return (output_objects, status)


