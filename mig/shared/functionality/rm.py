#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rm - backend to remove files/directories in user home
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Module that enables a user to delete files and directories
in his home directory.
It is possible to supply a recursive flag to enable recursive deletes.
"""

import os
import glob

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import trash_linkname
from shared.fileio import check_write_access
from shared.functional import validate_input, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables, find_entry
from shared.parseflags import verbose, recursive, force
from shared.sharelinks import extract_mode_id
from shared.userio import remove_path, delete_path, get_trash_location
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {
        'flags': [''],
        'iosessionid': [''],
        'path': REJECT_UNSET,
        'delete': [''],
        'allbox': [''],
        'share_id': [''],
        }
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flags = ''.join(accepted['flags'])
    pattern_list = accepted['path']
    iosessionid = accepted['iosessionid'][-1]
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
        page_title = 'Remove User File'
        if force(flags):
            rm_helper = delete_path
        else:
            rm_helper = remove_path
        userstyle = True
        widgets = True
    elif share_id:
        (share_mode, _) = extract_mode_id(configuration, share_id)
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
        page_title = 'Remove Shared File'
        rm_helper = delete_path
        userstyle = False
        widgets = False
    elif iosessionid.strip() and iosessionid.isalnum():
        user_id = iosessionid
        base_dir = configuration.webserver_home
        target_dir = iosessionid
        page_title = 'Remove Session File'
        rm_helper = delete_path
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

    logger.debug("%s: with paths: %s" % (op_name, pattern_list))

    # Input validation assures target_dir can't escape base_dir
    if not os.path.isdir(base_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid client/sharelink/session id!'})
        logger.warning('%s used %s with invalid base dir: %s' % \
                       (user_id, op_name, base_dir))
        return (output_objects, returnvalues.CLIENT_ERROR)

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text', 'text'
                                  : '%s using flag: %s' % (op_name,
                                  flag)})

    for pattern in pattern_list:
        
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

                logger.warning('%s tried to %s restricted path %s ! ( %s)'
                               % (client_id, op_name, abs_path, pattern))
                continue
            match.append(abs_path)

        # Now actually treat list of allowed matchings and notify if no
        # (allowed) match

        if not match:
            logger.warning("%s: no matching paths: %s" % (op_name,
                                                          pattern_list))
            output_objects.append({'object_type': 'file_not_found',
                                  'name': pattern})
            status = returnvalues.FILE_NOT_FOUND

        for abs_path in match:
            real_path = os.path.realpath(abs_path)
            relative_path = abs_path.replace(base_dir, '')
            if verbose(flags):
                output_objects.append({'object_type': 'file', 'name'
                        : relative_path})

            # Make it harder to accidentially delete too much - e.g. do not
            # deleteVGrid files without explicit selection of subdir contents

            if abs_path == os.path.abspath(base_dir):
                logger.error("%s: refusing rm home dir: %s" % (op_name,
                                                               abs_path))
                output_objects.append(
                    {'object_type': 'warning', 'text':
                     "You're not allowed to delete your entire home directory!"
                     })
                status = returnvalues.CLIENT_ERROR
                continue
            if os.path.islink(abs_path):
                logger.error("%s: refusing rm link: %s" % (op_name, abs_path))
                output_objects.append({'object_type': 'warning', 'text': """
You're not allowed to delete entire special folders like %s shares and %s
""" % (configuration.site_vgrid_label, trash_linkname)
                        })
                status = returnvalues.CLIENT_ERROR
                continue
            if os.path.isdir(abs_path) and not recursive(flags):
                logger.error("%s: non-recursive call on dir '%s'" % (op_name,
                                                                     abs_path))
                output_objects.append({'object_type': 'error_text', 'text':
                                        "cannot remove '%s': is a direcory" \
                                       % relative_path})
                status = returnvalues.CLIENT_ERROR
                continue
            trash_base = get_trash_location(configuration, abs_path)
            if not trash_base and not force(flags):
                logger.error("%s: no trash for dir '%s'" % (op_name, abs_path))
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     "No trash enabled for '%s' - read-only?" % relative_path})
                status = returnvalues.CLIENT_ERROR
                continue
            try:
                if rm_helper == remove_path and \
                       os.path.commonprefix([real_path, trash_base]) == trash_base:
                    logger.warning("%s: already in trash: '%s'" % (op_name,
                                                               real_path))
                    output_objects.append({'object_type': 'error_text', 'text': """
'%s' is already in trash - no action: use force flag to permanently delete""" \
                                       % relative_path})
                    status = returnvalues.CLIENT_ERROR
                    continue
            except Exception, err:
                logger.error("%s: check trash failed: %s" % (op_name, err))
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
        
            # TODO: limit delete in vgrid share trash to vgrid owners / conf?
            #       ... malicious members can still e.g. truncate all files.
            #       we could consider removing write bit on move to trash.
            # TODO: user setting to switch on/off trash?
            # TODO: add direct delete checkbox in fileman move to trash dialog?
            # TODO: add empty trash option for Trash?
            # TODO: user settings to define read-only and auto-expire in trash?
            # TODO: add trash support for sftp/ftps/webdavs?

            (rm_status, rm_err) = rm_helper(configuration, abs_path)
            if not rm_status:
                logger.error("%s: failed on '%s': %s" % \
                             (op_name, abs_path, ', '.join(rm_err)))
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     "remove '%s' failed: %s" % (relative_path,
                                                 '. '.join(rm_err))})
                status = returnvalues.SYSTEM_ERROR
                continue
            logger.info("%s: successfully (re)moved %s" % (op_name, abs_path))
            output_objects.append({'object_type': 'text',
                        'text': "removed %s" % (relative_path)})

    output_objects.append({'object_type': 'link',
                           'destination': 'ls.py%s' % id_query,
                           'text': 'Return to files overview'})
    return (output_objects, status)
