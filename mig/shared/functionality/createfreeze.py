#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createfreeze - back end for freezing archives
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Creation of frozen archives fo write-once files"""

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import max_freeze_files, upload_tmp_dir
from shared.fileio import strip_dir
from shared.freezefunctions import create_frozen_archive
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.safeinput import valid_path
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {
        'freeze_name': REJECT_UNSET,
        'freeze_description': REJECT_UNSET,
        }
    return ['text', defaults]

def _parse_form_xfer(xfer, user_args, client_id, configuration):
    """Parse xfer (i.e. copy or move) file/dir entries from user_args"""
    files, rejected = [], []
    i = 0
    client_dir = client_id_dir(client_id)
    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep
    xfer_pattern = 'freeze_%s_%%d' % xfer 
    for i in xrange(max_freeze_files):
        if user_args.has_key(xfer_pattern % i):
            source_path = user_args[xfer_pattern % i][-1].strip()
            configuration.logger.info('found %s entry: %s' % (xfer,
                                                              source_path))
            if not source_path:
                continue
            try:
                valid_path(source_path)
            except Exception, exc:
                rejected.append('invalid path: %s (%s)' % (source_path,
                                                           exc))
                continue
            source_path = os.path.normpath(source_path).lstrip(os.sep)
            real_path = os.path.abspath(os.path.join(base_dir, source_path))
            if not valid_user_path(real_path, base_dir, True):
                rejected.append('invalid path: %s (%s)' % \
                                (source_path, 'illegal path!'))
                continue
            files.append((real_path, source_path))
    return (files, rejected)

def parse_form_copy(user_args, client_id, configuration):
    """Parse copy file/dir entries from user_args"""
    return _parse_form_xfer("copy", user_args, client_id, configuration)

def parse_form_move(user_args, client_id, configuration):
    """Parse move file/dir entries from user_args"""
    return _parse_form_xfer("move", user_args, client_id, configuration)

def parse_form_upload(user_args, client_id, configuration):
    """Parse upload file entries from user_args"""
    files, rejected = [], []
    i = 0
    client_dir = client_id_dir(client_id)
    for i in xrange(max_freeze_files):
        if user_args.has_key('freeze_upload_%d' % i):
            file_item = user_args['freeze_upload_%d' % i]
            filename = user_args.get('freeze_upload_%dfilename' % i,
                                     '')
            if not filename.strip():
                continue
            filename = strip_dir(filename)
            try:
                valid_path(filename)
            except Exception, exc:
                rejected.append('invalid filename: %s (%s)' % (filename, exc))
                continue
            files.append((filename, file_item[0]))
    return (files, rejected)

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Create frozen archive'})
    # All non-file fields must be validated
    validate_args = dict([(key, user_arguments_dict.get(key, val)) for \
                         (key, val) in defaults.items()])
    (validate_status, accepted) = validate_input_and_cert(
        validate_args,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended use'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                           '''Freezing archives is not enabled on this site.
    Please contact the Grid admins if you think it should be.'''})
        return (output_objects, returnvalues.OK)

    freeze_name = accepted['freeze_name'][-1].strip()
    freeze_description = accepted['freeze_description'][-1].strip()
    if not freeze_name:
        output_objects.append({'object_type': 'error_text', 'text':
                               'You must provide a name for the freeze!'})
        return (output_objects, returnvalues.OK)

    # Now parse and validate files to archive

    for name in defaults.keys():
        if user_arguments_dict.has_key(name):
            del user_arguments_dict[name]

    (copy_files, copy_rejected) = parse_form_copy(user_arguments_dict,
                                                  client_id, configuration)
    (move_files, move_rejected) = parse_form_move(user_arguments_dict,
                                                  client_id, configuration)
    (upload_files, upload_rejected) = parse_form_upload(user_arguments_dict,
                                                        client_id,
                                                        configuration)
    if copy_rejected + move_rejected + upload_rejected:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Errors parsing freeze files: %s' % \
                               '\n '.join(copy_rejected + move_rejected + \
                                          upload_rejected)})
        return (output_objects, returnvalues.CLIENT_ERROR)
    if not (copy_files + move_files + upload_files):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'No files included to freeze!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    freeze_entries = len(copy_files + move_files + upload_files)
    if freeze_entries > max_freeze_files:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Too many freeze files (%s), max %s'
                               % (freeze_entries,
                              max_freeze_files)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    (retval, retmsg) = create_frozen_archive(freeze_name, freeze_description,
                                             copy_files, move_files,
                                             upload_files, client_id,
                                             configuration)
    if not retval:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error creating new frozen archive: %s'
                               % retmsg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    freeze_id = retmsg
    logger.info("%s: successful for '%s': %s" % (op_name,
                                                 freeze_id, client_id))
    output_objects.append({'object_type': 'text', 'text'
                           : 'Created frozen archive with ID %s successfuly!'
                           % freeze_id})
    output_objects.append({'object_type': 'link',
                           'destination': 'showfreeze.py?freeze_id=%s' % \
                           freeze_id,
                           'class': 'viewlink',
                           'title': 'View your frozen archive',
                           'text': 'View new %s frozen archive'
                           % freeze_id,
                           })
    return (output_objects, returnvalues.OK)
