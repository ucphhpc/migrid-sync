#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createfreeze - back end for freezing archives
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

"""Creation of frozen archives for write-once files"""

import datetime
import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import max_freeze_files, csrf_field, freeze_flavors
from shared.fileio import strip_dir
from shared.freezefunctions import create_frozen_archive, published_url
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import initialize_main_variables, find_entry
from shared.safeinput import valid_path
from shared.validstring import valid_user_path
from shared.vgrid import in_vgrid_share


def signature():
    """Signature of the main function"""

    defaults = {
        'flavor': ['freeze'],
        'freeze_name': REJECT_UNSET,
        'freeze_description': [''],
        'freeze_publish': ['False'],
        'freeze_author': [''],
        'freeze_department': [''],
        'freeze_organization': [''],
        }
    return ['text', defaults]

def _parse_form_xfer(xfer, user_args, client_id, configuration):
    """Parse xfer request (i.e. copy, move or upload) file/dir entries from
    user_args.
    """
    _logger = configuration.logger
    files, rejected = [], []
    i = 0
    client_dir = client_id_dir(client_id)
    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep
    xfer_pattern = 'freeze_%s_%%d' % xfer 
    for i in xrange(max_freeze_files):
        if user_args.has_key(xfer_pattern % i):
            source_path = user_args[xfer_pattern % i][-1].strip()
            source_path = os.path.normpath(source_path).lstrip(os.sep)
            _logger.debug('found %s entry: %s' % (xfer, source_path))
            if not source_path:
                continue
            try:
                valid_path(source_path)
            except Exception, exc:
                rejected.append('invalid path: %s (%s)' % (source_path,
                                                           exc))
                continue
            abs_path = os.path.abspath(
                os.path.join(base_dir, source_path))
            # Prevent out-of-bounds, and restrict some greedy targets
            if not valid_user_path(abs_path, base_dir, True):
                _logger.error('found illegal directory traversal %s entry: %s' \
                              % (xfer, source_path))
                rejected.append('invalid path: %s (%s)' % \
                                (source_path, 'illegal path!'))
                continue
            elif os.path.exists(abs_path) and os.path.samefile(abs_path,
                                                               base_dir):
                _logger.warning('refusing archival of entire user home %s: %s' \
                                % (xfer, source_path))
                rejected.append('invalid path: %s (%s)' % \
                                (source_path, 'entire home not allowed!'))
                continue
            elif in_vgrid_share(configuration, abs_path) == source_path:
                _logger.warning(
                    'refusing archival of entire vgrid shared folder %s: %s' % \
                    (xfer, source_path))
                rejected.append('invalid path: %s (%s)' % \
                                (source_path, 'entire %s share not allowed!' \
                                 % configuration.site_vgrid_label))
                continue

            # expand any dirs recursively
            if os.path.isdir(abs_path):
                for (root, dirnames, filenames) in os.walk(abs_path):
                    for subname in filenames:
                        abs_sub = os.path.join(root, subname)
                        sub_base = root.replace(abs_path, source_path)
                        sub_path = os.path.join(sub_base, subname)
                        files.append((abs_sub, sub_path.lstrip(os.sep)))
            else:
                files.append((abs_path, source_path.lstrip(os.sep)))
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
    title_entry = find_entry(output_objects, 'title') 
    label = "%s" % configuration.site_vgrid_label   
    title_entry['text'] = "Create Archive"
    # NOTE: Delay header entry here to include vgrid_name
    # All non-file fields must be validated
    validate_args = dict([(key, user_arguments_dict.get(key, val)) for \
                          (key, val) in defaults.items()])
    # IMPORTANT: we must explicitly inlude CSRF token
    validate_args[csrf_field] = user_arguments_dict.get(csrf_field, ['allowme'])
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

    flavor = accepted['flavor'][-1].strip()

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not flavor in freeze_flavors.keys():
        output_objects.append({'object_type': 'error_text', 'text':
                           'Invalid freeze flavor: %s' % flavor})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title = freeze_flavors[flavor]['createfreeze_title']
    output_objects.append({'object_type': 'header', 'text': title})

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                               '''Freezing archives is disabled on this site.
Please contact the Grid admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    freeze_name = accepted['freeze_name'][-1].strip()
    freeze_description = accepted['freeze_description'][-1].strip()
    freeze_author = accepted['freeze_author'][-1].strip()
    freeze_department = accepted['freeze_department'][-1].strip()
    freeze_organization = accepted['freeze_organization'][-1].strip()
    freeze_publish = (accepted['freeze_publish'][-1].strip() != 'False')
    if not freeze_name:
        if flavor == 'backup':
            freeze_name = 'backup-%s' % datetime.datetime.now()
        else:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'You must provide a name for the archive!'})
            return (output_objects, returnvalues.CLIENT_ERROR)
    if not freeze_description:
        if flavor == 'backup':
            freeze_description = 'manual backup archive created on %s' % \
                                 datetime.datetime.now()
        else:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'You must provide a description for the archive!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

    freeze_meta = {'NAME': freeze_name, 'DESCRIPTION': freeze_description,
                   'FLAVOR': flavor, 'AUTHOR': freeze_author, 'DEPARTMENT':
                   freeze_department, 'ORGANIZATION': freeze_organization,
                   'PUBLISH': freeze_publish}

    if flavor == 'phd' and (not freeze_author or not freeze_department):
        output_objects.append({'object_type': 'error_text', 'text':
                               'You must provide author and department for '
                               'the thesis!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

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

    (retval, retmsg) = create_frozen_archive(freeze_meta, copy_files,
                                             move_files, upload_files,
                                             client_id, configuration)
    if not retval:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error creating new frozen archive: %s'
                               % retmsg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    freeze_id = freeze_meta['ID'] = retmsg
    logger.info("%s: successful for '%s': %s" % (op_name,
                                                 freeze_id, client_id))
    output_objects.append({'object_type': 'text', 'text'
                           : 'Successfully created %s archive with ID %s .'
                           % (flavor, freeze_id)})
    output_objects.append({
        'object_type': 'link',
        'destination': 'showfreeze.py?freeze_id=%s;flavor=%s' % (freeze_id,
                                                                 flavor),
        'class': 'viewlink iconspace',
        'title': 'View your %s archive' % flavor,
        'text': 'View %s' % freeze_id,
        })
    if freeze_publish:
        public_url = published_url(freeze_meta, configuration)
        output_objects.append({'object_type': 'text', 'text'
                           : 'The archive is publicly available at:'})
        output_objects.append({
            'object_type': 'link',
            'destination': public_url,
            'class': 'viewlink iconspace',
            'title': 'View published archive',
            'text': public_url,
        })

    return (output_objects, returnvalues.OK)
