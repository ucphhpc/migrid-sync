#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# pack - Pack one or more files/dirs into a zip/tar archive
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

"""Archiver used to pack a one or more files and directories in
the home directory of a user into a zip/tar file.
"""

import glob
import os

import shared.returnvalues as returnvalues
from shared.archives import pack_archive
from shared.base import client_id_dir
from shared.fileio import check_write_access
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables, find_entry
from shared.parseflags import verbose
from shared.validstring import valid_user_path
from shared.vgrid import in_vgrid_share


def signature():
    """Signature of the main function"""

    defaults = {'src': REJECT_UNSET, 'flags': [''],
                'dst': REJECT_UNSET, 'current_dir': ['.']}
    return ['link', defaults]


def usage(output_objects):
    """Usage help"""

    output_objects.append({'object_type': 'header', 'text': 'pack usage:'})
    output_objects.append(
        {'object_type': 'text', 'text':
         'SERVER_URL/pack.py?[output_format=(html|txt|xmlrpc|..);]'
         '[flags=h;][src=src_path;[...]]src=src_path;dst=dst_path'})
    output_objects.append(
        {'object_type': 'text', 'text':
         '- output_format specifies how the script should format the output'
         })
    output_objects.append(
        {'object_type': 'text', 'text':
         '- flags is a string of character flags to be passed to the script'
         })
    output_objects.append(
        {'object_type': 'text', 'text':
         '- each src specifies a path in your home to include in the archive'
         })
    output_objects.append(
        {'object_type': 'text', 'text':
         '- dst is the path where the generated archive will be stored. ' +
         'The file extension decides the archive format (zip, tar, tar.gz)'
         })
    return (output_objects, returnvalues.OK)


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    dst = accepted['dst'][-1].lstrip(os.sep)
    pattern_list = accepted['src']
    current_dir = accepted['current_dir'][-1].lstrip(os.sep)

    # All paths are relative to current_dir

    pattern_list = [os.path.join(current_dir, i) for i in pattern_list]
    dst = os.path.join(current_dir, dst)

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'ZIP/TAR archiver'
    output_objects.append(
        {'object_type': 'header', 'text': 'ZIP/TAR archiver'})

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text':
                                   '%s using flag: %s' % (op_name, flag)})

    if 'h' in flags:
        usage(output_objects)

    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_dir = os.path.abspath(os.path.join(base_dir,
                                           current_dir.lstrip(os.sep)))
    if not valid_user_path(configuration, abs_dir, base_dir, True):

        # out of bounds

        output_objects.append({'object_type': 'error_text', 'text':
                               "You're not allowed to work in %s!"
                               % current_dir})
        logger.warning('%s tried to %s restricted path %s ! (%s)'
                       % (client_id, op_name, abs_dir, current_dir))
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append(
        {'object_type': 'text', 'text': "working in %s" % current_dir})

    # NOTE: dst already incorporates current_dir prefix here
    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_dest = os.path.abspath(os.path.join(base_dir, dst))
    logger.info('pack in %s' % abs_dest)

    # Don't use abs_path in output as it may expose underlying
    # fs layout.

    relative_dest = abs_dest.replace(base_dir, '')
    if not valid_user_path(configuration, abs_dest, base_dir, True):

        # out of bounds

        output_objects.append(
            {'object_type': 'error_text', 'text':
             "Invalid path! (%s expands to an illegal path)" % dst})
        logger.warning('%s tried to %s restricted path %s !(%s)'
                       % (client_id, op_name, abs_dest, dst))
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not os.path.isdir(os.path.dirname(abs_dest)):
        output_objects.append({'object_type': 'error_text', 'text':
                               "No such destination directory: %s"
                               % os.path.dirname(relative_dest)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not check_write_access(abs_dest, parent_dir=True):
        logger.warning('%s called without write access: %s' %
                       (op_name, abs_dest))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'cannot pack to "%s": inside a read-only location!' %
             relative_dest})
        return (output_objects, returnvalues.CLIENT_ERROR)

    status = returnvalues.OK

    for pattern in pattern_list:

        # Check directory traversal attempts before actual handling to avoid
        # leaking information about file system layout while allowing
        # consistent error messages

        unfiltered_match = glob.glob(base_dir + pattern)
        match = []
        for server_path in unfiltered_match:
            logger.debug("%s: inspecting: %s" % (op_name, server_path))
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):

                # out of bounds - save user warning for later to allow
                # partial match:
                # ../*/* is technically allowed to match own files.

                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                continue
            else:
                match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append({'object_type': 'error_text', 'text':
                                   "%s: cannot pack '%s': no valid src paths"
                                   % (op_name, pattern)})
            status = returnvalues.CLIENT_ERROR
            continue

        for abs_path in match:
            relative_path = abs_path.replace(base_dir, '')
            # Generally refuse handling symlinks including root vgrid shares
            if os.path.islink(abs_path):
                output_objects.append(
                    {'object_type': 'warning', 'text': """You're not allowed to
pack entire special folders like %s shared folders!""" %
                     configuration.site_vgrid_label})
                status = returnvalues.CLIENT_ERROR
                continue
            # Additionally refuse operations on inherited subvgrid share roots
            elif in_vgrid_share(configuration, abs_path) == relative_path:
                output_objects.append(
                    {'object_type': 'warning', 'text': """You're not allowed to
pack entire %s shared folders!""" % configuration.site_vgrid_label})
                status = returnvalues.CLIENT_ERROR
                continue
            elif os.path.realpath(abs_path) == os.path.realpath(base_dir):
                logger.error("%s: refusing pack home dir: %s" % (op_name,
                                                                 abs_path))
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     "You're not allowed to pack your entire home directory!"
                     })
                status = returnvalues.CLIENT_ERROR
                continue
            elif os.path.realpath(abs_dest) == os.path.realpath(abs_path):
                output_objects.append({'object_type': 'warning', 'text':
                                       'overlap in source and destination %s'
                                       % relative_dest})
                status = returnvalues.CLIENT_ERROR
                continue
            if verbose(flags):
                output_objects.append(
                    {'object_type': 'file', 'name': relative_path})

            (pack_status, msg) = pack_archive(configuration, client_id,
                                              relative_path, relative_dest)
            if not pack_status:
                output_objects.append({'object_type': 'error_text',
                                       'text': 'Error: %s' % msg})
                status = returnvalues.CLIENT_ERROR
                continue
            output_objects.append({'object_type': 'text', 'text':
                                   'Added %s to %s' % (relative_path,
                                                       relative_dest)})

    output_objects.append({'object_type': 'text', 'text':
                           'Packed archive of %s is now available in %s'
                           % (', '.join(pattern_list), relative_dest)})
    output_objects.append({'object_type': 'link', 'text': 'Download archive',
                           'destination': os.path.join('..', client_dir,
                                                       relative_dest)})

    return (output_objects, status)
