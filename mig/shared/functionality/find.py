#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# find - find backend
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

"""Emulate the un*x function with the same name"""

from __future__ import absolute_import

import fnmatch
import glob
import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import csrf_field
from mig.shared.fileio import walk
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables
from mig.shared.parseflags import verbose, file_info
from mig.shared.safeinput import valid_path_pattern
from mig.shared.url import quote
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {'path': ['.'], 'flags': [''], 'pattern': ['*']}
    return ['dir_listings', defaults]

# TODO: refactor to fileio and use from here and in ls?


def fileinfo_stat(path):
    """Additional stat information for file manager"""
    file_information = {'size': 0, 'created': 0, 'modified': 0, 'accessed': 0,
                        'ext': ''}
    if os.path.exists(path):
        ext = 'dir'
        if not os.path.isdir(path):
            ext = os.path.splitext(path)[1].lstrip('.')
        file_information['ext'] = ext
        try:
            file_information['size'] = os.path.getsize(path)
            file_information['created'] = os.path.getctime(path)
            file_information['modified'] = os.path.getmtime(path)
            file_information['accessed'] = os.path.getatime(path)
        except OSError as ose:
            pass
    return file_information


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        # NOTE: path can use wildcards
        typecheck_overrides={'path': valid_path_pattern},
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    patterns = accepted['path']
    name_pattern = accepted['pattern'][-1]

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text':
                                   '%s using flag: %s' % (op_name, flag)})

    # Shared URL helpers
    id_args = ''
    redirect_name = configuration.site_user_redirect
    redirect_path = redirect_name
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    ls_url_template = 'ls.py?%scurrent_dir=%%(rel_dir_enc)s;flags=%s' % \
                      (id_args, flags)
    csrf_token = make_csrf_token(configuration, form_method, 'rm', client_id,
                                 csrf_limit)
    rm_url_template = 'rm.py?%spath=%%(rel_path_enc)s;%s=%s' % \
                      (id_args, csrf_field, csrf_token)
    rmdir_url_template = 'rm.py?%spath=%%(rel_path_enc)s;flags=r;%s=%s' % \
        (id_args, csrf_field, csrf_token)
    editor_url_template = 'editor.py?%spath=%%(rel_path_enc)s' % id_args
    redirect_url_template = '/%s/%%(rel_path_enc)s' % redirect_path

    dir_listings = []
    output_objects.append({
        'object_type': 'dir_listings',
        'dir_listings': dir_listings,
        'flags': flags,
        'ls_url_template': ls_url_template,
        'rm_url_template': rm_url_template,
        'rmdir_url_template': rmdir_url_template,
        'editor_url_template': editor_url_template,
        'redirect_url_template': redirect_url_template,
    })

    for pattern in patterns:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern)
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
            output_objects.append({'object_type': 'file_not_found',
                                   'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        for abs_path in match:
            output_lines = []
            relative_path = abs_path.replace(base_dir, '')
            entries = []
            dir_listing = {
                'object_type': 'dir_listing',
                'relative_path': relative_path,
                'entries': entries,
                'flags': flags,
            }
            dir_listings.append(dir_listing)
            try:
                for (root, dirs, files) in walk(abs_path):
                    for filename in fnmatch.filter(files, name_pattern):
                        # IMPORTANT: this join always yields abs expanded path
                        abs_path = os.path.join(root, filename)
                        relative_path = abs_path.replace(base_dir, '')
                        if not valid_user_path(configuration, abs_path, base_dir,
                                               True):
                            continue
                        file_with_dir = relative_path
                        file_obj = {
                            'object_type': 'direntry',
                            'type': 'file',
                            'name': filename,
                            'rel_path': file_with_dir,
                            'rel_path_enc': quote(file_with_dir),
                            'rel_dir_enc': quote(os.path.dirname(file_with_dir)),
                            # NOTE: file_with_dir is kept for backwards compliance
                            'file_with_dir': file_with_dir,
                            'flags': flags,
                            'special': '',
                        }
                        if file_info(flags):
                            file_obj['file_info'] = fileinfo_stat(abs_path)
                        entries.append(file_obj)
            except Exception as exc:
                output_objects.append({'object_type': 'error_text',
                                       'text': "%s: '%s': %s" % (op_name,
                                                                 relative_path, exc)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                                                         relative_path, exc))
                status = returnvalues.SYSTEM_ERROR
                continue
            if verbose(flags):
                output_objects.append({'object_type': 'file_output',
                                       'path': relative_path, 'lines': output_lines})
            else:
                output_objects.append({'object_type': 'file_output',
                                       'lines': output_lines})

    return (output_objects, status)
