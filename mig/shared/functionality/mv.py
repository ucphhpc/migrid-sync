#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mv - backend to move files/directories in user home
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

"""Emulate the un*x function with the same name"""

import os
import glob
import shutil

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.fileio import check_write_access
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables
from shared.parseflags import verbose
from shared.userio import GDPIOLogError, gdp_iolog
from shared.validstring import valid_user_path
from shared.vgrid import in_vgrid_share


def signature():
    """Signature of the main function"""

    defaults = {'dst': REJECT_UNSET, 'src': REJECT_UNSET, 'flags': ['']}
    return ['', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ

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
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    src_list = accepted['src']
    dst = accepted['dst'][-1]

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

    status = returnvalues.OK

    abs_dest = base_dir + dst
    dst_list = glob.glob(abs_dest)
    if not dst_list:

        # New destination?

        if not glob.glob(os.path.dirname(abs_dest)):
            output_objects.append(
                {'object_type': 'error_text',
                 'text': 'Illegal dst path provided!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        else:
            dst_list = [abs_dest]

    # Use last match in case of multiple matches

    dest = dst_list[-1]
    if len(dst_list) > 1:
        output_objects.append(
            {'object_type': 'warning',
             'text': 'dst (%s) matches multiple targets - using last: %s'
             % (dst, dest)})

    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_dest = os.path.abspath(dest)

    # Don't use abs_path in output as it may expose underlying
    # fs layout.

    relative_dest = abs_dest.replace(base_dir, '')
    if not valid_user_path(configuration, abs_dest, base_dir, True):
        logger.warning('%s tried to %s to restricted path %s ! (%s)'
                       % (client_id, op_name, abs_dest, dst))
        output_objects.append(
            {'object_type': 'error_text',
             'text': "Invalid path! (%s expands to an illegal path)" % dst})
        return (output_objects, returnvalues.CLIENT_ERROR)
    if not check_write_access(abs_dest, parent_dir=True):
        logger.warning('%s called without write access: %s'
                       % (op_name, abs_dest))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'cannot move to "%s": inside a read-only location!'
             % relative_dest})
        return (output_objects, returnvalues.CLIENT_ERROR)

    for pattern in src_list:
        unfiltered_match = glob.glob(base_dir + pattern)
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, True):
                logger.warning('%s tried to %s restricted path %s ! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                continue
            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            output_objects.append({'object_type': 'error_text',
                                   'text': '%s: no such file or directory! %s'
                                   % (op_name, pattern)})
            status = returnvalues.CLIENT_ERROR

        for abs_path in match:
            relative_path = abs_path.replace(base_dir, '')
            if verbose(flags):
                output_objects.append(
                    {'object_type': 'file', 'name': relative_path})

            # Generally refuse handling symlinks including root vgrid shares
            if os.path.islink(abs_path):
                output_objects.append(
                    {'object_type': 'warning', 'text': """You're not allowed to
move entire special folders like %s shared folders!"""
                     % configuration.site_vgrid_label})
                status = returnvalues.CLIENT_ERROR
                continue
            # Additionally refuse operations on inherited subvgrid share roots
            elif in_vgrid_share(configuration, abs_path) == relative_path:
                output_objects.append(
                    {'object_type': 'warning', 'text': """You're not allowed to
move entire %s shared folders!""" % configuration.site_vgrid_label})
                status = returnvalues.CLIENT_ERROR
                continue
            elif os.path.realpath(abs_path) == os.path.realpath(base_dir):
                logger.error("%s: refusing move home dir: %s" % (op_name,
                                                                 abs_path))
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     "You're not allowed to move your entire home directory!"
                     })
                status = returnvalues.CLIENT_ERROR
                continue

            if not check_write_access(abs_path):
                logger.warning('%s called without write access: %s'
                               % (op_name, abs_path))
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'cannot move "%s": inside a read-only location!'
                     % pattern})
                status = returnvalues.CLIENT_ERROR
                continue

            # If destination is a directory the src should be moved in there
            # Move with existing directory as target replaces the directory!

            abs_target = abs_dest
            if os.path.isdir(abs_target):
                if os.path.samefile(abs_target, abs_path):
                    output_objects.append(
                        {'object_type': 'warning',
                         'text': "Cannot move '%s' to a subdirectory of itself!"
                         % relative_path
                         })
                    status = returnvalues.CLIENT_ERROR
                    continue
                abs_target = os.path.join(abs_target,
                                          os.path.basename(abs_path))

            try:
                gdp_iolog(configuration,
                          client_id,
                          environ['REMOTE_ADDR'],
                          'moved',
                          [relative_path, relative_dest])
                shutil.move(abs_path, abs_target)
                logger.info('%s %s %s done' % (op_name, abs_path, abs_target))
            except Exception, exc:
                if not isinstance(exc, GDPIOLogError):
                    gdp_iolog(configuration,
                              client_id,
                              environ['REMOTE_ADDR'],
                              'moved',
                              [relative_path, relative_dest],
                              failed=True,
                              details=exc)
                output_objects.append({'object_type': 'error_text',
                                       'text': "%s: '%s': %s"
                                       % (op_name, relative_path, exc)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                                                         relative_path, exc))

                status = returnvalues.SYSTEM_ERROR
                continue

    return (output_objects, status)
