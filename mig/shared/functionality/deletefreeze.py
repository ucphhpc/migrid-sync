#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#

# deletefreeze - delete a frozen archive
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

"""Deletion of frozen archives"""

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.init import initialize_main_variables, find_entry
from shared.freezefunctions import is_frozen_archive, \
     get_frozen_archive, delete_frozen_archive


def signature():
    """Signature of the main function"""

    defaults = {'freeze_id': REJECT_UNSET}
    return ['frozenarchive', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Delete frozen archive'
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                           : 'Delete frozen archive'})
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
    
    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                           '''Freezing archives is not enabled on this site.
    Please contact the Grid admins if you think it should be.'''})
        return (output_objects, returnvalues.OK)

    freeze_id = accepted['freeze_id'][-1]

    # NB: the restrictions on freeze_id prevents illegal directory traversal

    if not is_frozen_archive(freeze_id, configuration):
        logger.error("%s: invalid freeze '%s': %s" % (op_name,
                                                      client_id, freeze_id))
        output_objects.append({'object_type': 'error_text',
                               'text': "No such frozen archive: '%s'"
                               % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)
    
    (load_status, freeze_dict) = get_frozen_archive(freeze_id, configuration)
    if not load_status:
        logger.error("%s: load failed for '%s': %s" % \
                     (op_name, freeze_id, freeze_dict))
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'Could not read frozen archive details for %s'
             % freeze_id})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Make sure the frozen archive belongs to the user trying to delete it
    if client_id != freeze_dict['CREATOR']:
        logger.error("%s: illegal access attempt for '%s': %s" % \
                         (op_name, freeze_id, client_id))
        output_objects.append({'object_type': 'error_text', 'text': \
        'You are not the owner of frozen archive "%s"' % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Prevent easy delete if the frozen archive if configuration forbids it
    if configuration.site_permanent_freeze:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "Can't delete frozen archive '%s' yourself due to site policy"
             % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Delete the frozen archive
    (status, msg) = delete_frozen_archive(freeze_id, configuration)
    
    # If something goes wrong when trying to delete frozen archive
    # freeze_id, an error is displayed.
    if not status:
        logger.error("%s: failed for '%s': %s" % (op_name,
                                                  freeze_id, msg))
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Could not remove %s frozen archive: %s'
                               % (freeze_id, msg)})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # If deletion of frozen archive freeze_id is successful, we just
    # return OK
    else:
        logger.info("%s: successful for '%s': %s" % (op_name,
                                                      freeze_id, client_id))
        output_objects.append(
            {'object_type': 'text', 'text'
             : 'Successfully deleted frozen archive: "%s"' % freeze_id})
        output_objects.append({'object_type': 'link', 'destination':
                               'freezedb.py',
                               'class': 'infolink',
                               'title': 'Show frozen archives',
                               'text': 'Show frozen archives'})
        return (output_objects, returnvalues.OK) 
