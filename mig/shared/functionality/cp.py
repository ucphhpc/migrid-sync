#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cp - copy file between user home locations
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
from shared.fileio import check_write_access, check_empty_dir, makedirs_rec
from shared.freezefunctions import is_frozen_archive
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables
from shared.parseflags import verbose, recursive, force
from shared.sharelinks import extract_mode_id
from shared.userio import GDPIOLogError, gdp_iolog
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {
        'flags': [''],
        'src': REJECT_UNSET,
        'dst': REJECT_UNSET,
        'iosessionid': [''],
        'share_id': [''],
        'freeze_id': [''],
    }
    return ['', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
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
    src_list = accepted['src']
    dst = accepted['dst'][-1]
    iosessionid = accepted['iosessionid'][-1]
    share_id = accepted['share_id'][-1]
    freeze_id = accepted['freeze_id'][-1]

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

    # Special handling if used from a job (no client_id but iosessionid)
    if not client_id and iosessionid:
        base_dir = os.path.realpath(configuration.webserver_home
                                    + os.sep + iosessionid) + os.sep

    # Use selected base as source and destination dir by default
    src_base = dst_base = base_dir

    # Sharelink import if share_id is given - change to sharelink as src base
    if share_id:
        try:
            (share_mode, _) = extract_mode_id(configuration, share_id)
        except ValueError, err:
            logger.error('%s called with invalid share_id %s: %s' %
                         (op_name, share_id, err))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Invalid sharelink ID: %s' % share_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        # TODO: load and check sharelink pickle (currently requires client_id)
        if share_mode == 'write-only':
            logger.error('%s called import from write-only sharelink: %s'
                         % (op_name, accepted))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Sharelink %s is write-only!' % share_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        target_dir = os.path.join(share_mode, share_id)
        src_base = os.path.abspath(os.path.join(configuration.sharelink_home,
                                                target_dir)) + os.sep
        if os.path.isfile(os.path.realpath(src_base)):
            logger.error('%s called import on single file sharelink: %s'
                         % (op_name, share_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': """Import is only
supported for directory sharelinks!"""})
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif not os.path.isdir(src_base):
            logger.error('%s called import with non-existant sharelink: %s'
                         % (client_id, share_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': 'No such sharelink: %s'
                 % share_id})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Archive import if freeze_id is given - change to archive as src base
    if freeze_id:
        if not is_frozen_archive(client_id, freeze_id, configuration):
            logger.error('%s called with invalid freeze_id: %s' %
                         (op_name, freeze_id))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Invalid archive ID: %s' % freeze_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        target_dir = os.path.join(client_dir, freeze_id)
        src_base = os.path.abspath(os.path.join(configuration.freeze_home,
                                                target_dir)) + os.sep
        if not os.path.isdir(src_base):
            logger.error('%s called import with non-existant archive: %s'
                         % (client_id, freeze_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': 'No such archive: %s'
                 % freeze_id})
            return (output_objects, returnvalues.CLIENT_ERROR)

    status = returnvalues.OK

    abs_dest = dst_base + dst
    dst_list = glob.glob(abs_dest)
    if not dst_list:

        # New destination?

        if not glob.glob(os.path.dirname(abs_dest)):
            logger.error('%s called with illegal dst: %s'
                         % (op_name, dst))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Illegal dst path provided!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
        else:
            dst_list = [abs_dest]

    # Use last match in case of multiple matches

    dest = dst_list[-1]
    if len(dst_list) > 1:
        output_objects.append(
            {'object_type': 'warning', 'text':
             'dst (%s) matches multiple targets - using last: %s'
             % (dst, dest)})

    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_dest = os.path.abspath(dest)

    # Don't use abs_path in output as it may expose underlying
    # fs layout.

    relative_dest = abs_dest.replace(dst_base, '')
    if not valid_user_path(configuration, abs_dest, dst_base, True):
        logger.warning('%s tried to %s restricted path %s ! (%s)'
                       % (client_id, op_name, abs_dest, dst))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "Invalid destination (%s expands to an illegal path)" % dst})
        return (output_objects, returnvalues.CLIENT_ERROR)
    # We must make sure target dir exists if called in import X mode
    if (share_id or freeze_id) and not makedirs_rec(abs_dest, configuration):
        logger.error('could not create import destination dir: %s' % abs_dest)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'cannot import to "%s" : file in the way?' % relative_dest})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    if not check_write_access(abs_dest, parent_dir=True):
        logger.warning('%s called without write access: %s'
                       % (op_name, abs_dest))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'cannot copy to "%s": inside a read-only location!'
             % relative_dest})
        return (output_objects, returnvalues.CLIENT_ERROR)
    if share_id and not force(flags) and not check_empty_dir(abs_dest):
        logger.warning('%s called %s sharelink import with non-empty dst: %s'
                       % (op_name, share_id, abs_dest))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             """Importing a sharelink like '%s' into the non-empty '%s' folder
will potentially overwrite existing files with the sharelink version. If you
really want that, please try import again and select the overwrite box to
confirm it. You may want to back up any important data from %s first, however.
""" % (share_id, relative_dest, relative_dest)})
        return (output_objects, returnvalues.CLIENT_ERROR)
    if freeze_id and not force(flags) and not check_empty_dir(abs_dest):
        logger.warning('%s called %s archive import with non-empty dst: %s'
                       % (op_name, freeze_id, abs_dest))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             """Importing an archive like '%s' into the non-empty '%s' folder
will potentially overwrite existing files with the archive version. If you
really want that, please try import again and select the overwrite box to
confirm it. You may want to back up any important data from %s first, however.
""" % (freeze_id, relative_dest, relative_dest)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    for pattern in src_list:
        unfiltered_match = glob.glob(src_base + pattern)
        match = []
        for server_path in unfiltered_match:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, src_base, True):
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
            relative_path = abs_path.replace(src_base, '')
            if verbose(flags):
                output_objects.append(
                    {'object_type': 'file', 'name': relative_path})

            # Prevent vgrid share copy which would create read-only dot dirs

            if os.path.islink(abs_path):
                output_objects.append(
                    {'object_type': 'warning', 'text': """You're not allowed to
copy entire special folders like %s shared folders!"""
                     % configuration.site_vgrid_label})
                status = returnvalues.CLIENT_ERROR
                continue
            elif os.path.realpath(abs_path) == os.path.realpath(base_dir):
                logger.error("%s: refusing copy home dir: %s" % (op_name,
                                                                 abs_path))
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     "You're not allowed to copy your entire home directory!"
                     })
                status = returnvalues.CLIENT_ERROR
                continue

            # src must be a file unless recursive is specified

            if not recursive(flags) and os.path.isdir(abs_path):
                logger.warning('skipping directory source %s' % abs_path)
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     'skipping directory src %s!' % relative_path})
                continue

            # If destination is a directory the src should be copied there

            abs_target = abs_dest
            if os.path.isdir(abs_target):
                abs_target = os.path.join(abs_target,
                                          os.path.basename(abs_path))

            if os.path.abspath(abs_path) == os.path.abspath(abs_target):
                logger.warning('%s tried to %s %s to itself! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     "Cannot copy '%s' to self!" % relative_path})
                status = returnvalues.CLIENT_ERROR
                continue
            if os.path.isdir(abs_path) and \
                    abs_target.startswith(abs_path + os.sep):
                logger.warning('%s tried to %s %s to itself! (%s)'
                               % (client_id, op_name, abs_path, pattern))
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     "Cannot copy '%s' to (sub) self!" % relative_path})
                status = returnvalues.CLIENT_ERROR
                continue

            try:
                gdp_iolog(configuration,
                          client_id,
                          environ['REMOTE_ADDR'],
                          'copied',
                          [relative_path,
                           relative_dest
                           + "/" + os.path.basename(relative_path)])
                if os.path.isdir(abs_path):
                    shutil.copytree(abs_path, abs_target)
                else:
                    shutil.copy(abs_path, abs_target)
                logger.info('%s %s %s done' % (op_name, abs_path, abs_target))
            except Exception, exc:
                if not isinstance(exc, GDPIOLogError):
                    gdp_iolog(configuration,
                              client_id,
                              environ['REMOTE_ADDR'],
                              'copied',
                              [relative_path,
                               relative_dest
                               + "/" + os.path.basename(relative_path)],
                              failed=True,
                              details=exc)
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': "%s: failed on '%s' to '%s'"
                     % (op_name, relative_path, relative_dest)})
                logger.error("%s: failed on '%s': %s" % (op_name,
                                                         relative_path, exc))
                status = returnvalues.SYSTEM_ERROR

    return (output_objects, status)
