#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#

# deletefreeze - delete an entire frozen archive or files in one
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

"""Delete archive or only individual files inside one. Requires freeze to be
non-final.
"""
from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import freeze_flavors, keyword_updating, keyword_final, \
    keyword_all
from mig.shared.freezefunctions import is_frozen_archive, get_frozen_archive, \
    delete_frozen_archive, delete_archive_files, TARGET_ARCHIVE, TARGET_PATH
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.validstring import valid_user_path

valid_targets = [TARGET_ARCHIVE, TARGET_PATH]


def signature():
    """Signature of the main function"""

    defaults = {'freeze_id': REJECT_UNSET,
                'flavor': ['freeze'],
                'target': TARGET_ARCHIVE,
                'path': ['']}
    return ['frozenarchive', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Delete frozen archive'
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

    flavor = accepted['flavor'][-1]

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

    title = freeze_flavors[flavor]['deletefreeze_title']
    output_objects.append({'object_type': 'header', 'text': title})
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = title

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                               '''Freezing archives is disabled on this site.
Please contact the site admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    freeze_id = accepted['freeze_id'][-1]
    target = accepted['target'][-1]
    path_list = accepted['path']

    if not target in valid_targets:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid delete freeze target: %s' % target})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # NB: the restrictions on freeze_id prevents illegal directory traversal

    if not is_frozen_archive(client_id, freeze_id, configuration):
        logger.error("%s: invalid freeze '%s': %s" % (op_name,
                                                      client_id, freeze_id))
        output_objects.append({'object_type': 'error_text',
                               'text': "No such frozen archive: '%s'"
                               % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    (load_status, freeze_dict) = get_frozen_archive(client_id, freeze_id,
                                                    configuration,
                                                    checksum_list=[])
    if not load_status:
        logger.error("%s: load failed for '%s': %s" %
                     (op_name, freeze_id, freeze_dict))
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'Could not read frozen archive details for %s'
             % freeze_id})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Make sure the frozen archive belongs to the user trying to delete it
    if client_id != freeze_dict['CREATOR']:
        logger.error("%s: illegal access attempt for '%s': %s" %
                     (op_name, freeze_id, client_id))
        output_objects.append({'object_type': 'error_text', 'text':
                               'You are not the owner of frozen archive "%s"'
                               % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if freeze_dict.get('FLAVOR', 'freeze') != flavor:
        logger.error("%s: flavor mismatch for '%s': %s vs %s" %
                     (op_name, freeze_id, flavor, freeze_dict))
        output_objects.append({'object_type': 'error_text', 'text':
                               'No such %s archive "%s"' % (flavor, freeze_id)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Prevent user-delete of the frozen archive if configuration forbids it.
    # We exclude any archives in the pending intermediate freeze state.
    # Freeze admins are also excluded from the restrictions.
    state = freeze_dict.get('STATE', keyword_final)
    if state == keyword_updating:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "Can't change %s archive %s which is currently being updated" %
             (flavor, freeze_id)})
        output_objects.append({
            'object_type': 'link',
            'destination': 'showfreeze.py?freeze_id=%s;flavor=%s' %
            (freeze_id, flavor),
            'class': 'viewarchivelink iconspace genericbutton',
            'title': 'View details about your %s archive' % flavor,
            'text': 'View details',
        })
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif state == keyword_final and \
            flavor in configuration.site_permanent_freeze and \
            not client_id in configuration.site_freeze_admins:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "Can't change %s archives like '%s' yourself due to site policy"
             % (flavor, freeze_id)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)

    # Please note that base_dir must end in slash to avoid access to other
    # user archive dirs if own name is a prefix of another archive name

    base_dir = os.path.abspath(os.path.join(user_archives, freeze_id)) + os.sep

    if target == TARGET_ARCHIVE:
        # Delete the entire freeze archive
        (del_status, msg) = delete_frozen_archive(freeze_dict, client_id,
                                                  configuration)

        # If something goes wrong when trying to delete freeze archive
        # freeze_id, an error is displayed.
        if not del_status:
            logger.error("%s: failed for '%s': %s" % (op_name,
                                                      freeze_id, msg))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Could not remove entire %s archive %s: %s' %
                 (flavor, freeze_id, msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # If deletion of frozen archive freeze_id is successful, we just
        # return OK
        else:
            logger.info("%s: successful for '%s': %s" % (op_name,
                                                         freeze_id, client_id))
            output_objects.append(
                {'object_type': 'text', 'text':
                 'Successfully deleted %s archive: "%s"' % (flavor,
                                                            freeze_id)})
    elif target == TARGET_PATH:
        # Delete individual files in non-final archive
        del_paths = []
        for path in path_list:
            # IMPORTANT: path must be expanded to abs for proper chrooting
            server_path = os.path.join(base_dir, path)
            abs_path = os.path.abspath(server_path)
            if not valid_user_path(configuration, abs_path, base_dir, False):

                # Out of bounds!

                logger.warning('%s tried to %s del restricted path %s ! ( %s)'
                               % (client_id, op_name, abs_path, path))
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'Not allowed to delete %s - outside archive %s !' %
                     (path, freeze_id)})
                continue
            del_paths.append(path)

        (del_status, msg_list) = delete_archive_files(freeze_dict, client_id,
                                                      del_paths, configuration)

        # If something goes wrong when trying to delete files from archive
        # freeze_id, an error is displayed.
        if not del_status:
            logger.error("%s: delete archive file(s) failed for '%s':\n%s" %
                         (op_name, freeze_id, '\n'.join(msg_list)))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Could not remove file(s) from archive %s: %s'
                 % (freeze_id, '\n '.join(msg_list))})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # If deletion of files from archive freeze_id is successful, we just
        # return OK
        else:
            logger.info("%s: delete %d files successful for '%s': %s" %
                        (op_name, len(path_list), freeze_id, client_id))
            output_objects.append(
                {'object_type': 'text', 'text':
                 'Successfully deleted %d file(s) from archive: "%s"' %
                 (len(path_list), freeze_id)})

    # Success - show link to overview
    output_objects.append({'object_type': 'link', 'destination':
                           'freezedb.py',
                           'class': 'infolink iconspace',
                           'title': 'Show archives',
                           'text': 'Show archives'})
    return (output_objects, returnvalues.OK)
