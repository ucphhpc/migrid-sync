#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showfreeze - back end to request freeze files in write-once fashion
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

"""Show summary contents of frozen archive"""

import os

import shared.returnvalues as returnvalues
from shared.defaults import default_pager_entries
from shared.freezefunctions import is_frozen_archive, get_frozen_archive, \
     build_freezeitem_object, freeze_flavors
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.html import jquery_ui_js, man_base_js, man_base_html, themed_styles
from shared.init import initialize_main_variables, find_entry

list_operations = ['showlist', 'list']
show_operations = ['show', 'showlist']
allowed_operations = list(set(list_operations + show_operations))

def signature():
    """Signature of the main function"""

    defaults = {
        'freeze_id': REJECT_UNSET,
        'flavor': ['freeze'],
        'checksum': [''],
        'operation': ['show']}
    return ['html_form', defaults]

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = "Show freeze"
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

    freeze_id = accepted['freeze_id'][-1]
    flavor = accepted['flavor'][-1]
    checksum = accepted['checksum'][-1]
    operation = accepted['operation'][-1]

    if not flavor in freeze_flavors.keys():
        output_objects.append({'object_type': 'error_text', 'text':
                           'Invalid freeze flavor: %s' % flavor})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title = freeze_flavors[flavor]['showfreeze_title']
    title_entry['text'] = title
    output_objects.append({'object_type': 'header', 'text': title})

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Freezing archives is disabled on this site.
Please contact the Grid admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    if not operation in allowed_operations:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Operation must be one of %s.''' % \
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    if operation in show_operations:

        # jquery support for tablesorter (and unused confirmation dialog)
        # table initially sorted by col. 0 (filename)

        refresh_call = 'ajax_showfreeze("%s", "%s")' % (freeze_id, checksum)
        table_spec = {'table_id': 'frozenfilestable', 'sort_order': '[[0,0]]',
                      'refresh_call': refresh_call}
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec])
        if operation == "show":
            add_ready += refresh_call
        title_entry['style'] = themed_styles(configuration)
        title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                                 add_init, add_ready)
        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})
        output_objects.append({'object_type': 'table_pager', 'entry_name':
                               'frozen files', 'default_entries':
                               default_pager_entries, 'refresh_button': False})

    # NB: the restrictions on freeze_id prevents illegal directory traversal
    
    if not is_frozen_archive(freeze_id, configuration):
        logger.error("%s: invalid freeze '%s': %s" % (op_name,
                                                      client_id, freeze_id))
        output_objects.append({'object_type': 'error_text', 'text'
                               : "'%s' is not an existing frozen archive!"
                               % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)



    if operation in list_operations:
        (load_status, freeze_dict) = get_frozen_archive(freeze_id, configuration,
                                                        checksum)
        if not load_status:
            logger.error("%s: load failed for '%s': %s" % \
                         (op_name, freeze_id, freeze_dict))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Could not read details for "%s"' % \
                                   freeze_id})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        if freeze_dict.get('FLAVOR', 'freeze') != flavor:
            logger.error("%s: flavor mismatch for '%s': %s vs %s" % \
                         (op_name, freeze_id, flavor, freeze_dict))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'No such %s archive "%s"' % (flavor,
                                                                  freeze_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)

        output_objects.append(build_freezeitem_object(configuration, freeze_dict))

    if operation == "show":
        # insert dummy placeholder to build table
        output_objects.append({'object_type': 'frozenarchive',
                               'id': freeze_id, 'creator': client_id,
                               'flavor': 'freeze',  'frozenfiles': [],
                               'name': 'loading ...',
                               'description': 'loading ...',
                               'created': 'loading ...'})
    if operation in show_operations:
        output_objects.append({'object_type': 'html_form', 'text': '<p>'})
        output_objects.append({
                'object_type': 'link',
                'destination': "showfreeze.py?freeze_id=%s;flavor=%s;checksum=%s" \
            % (freeze_id, flavor, 'md5'),
                'class': 'infolink iconspace', 
                'title': 'View archive with MD5 sums', 
                'text': 'Show with MD5 checksums - may take long'})
        # TODO: we hide sha1 column and link for now
        output_objects.append({'object_type': 'html_form', 'text': '</p><p class="hidden">'})
        output_objects.append({
                'object_type': 'link',
                'destination': "showfreeze.py?freeze_id=%s;flavor=%s;checksum=%s" \
            % (freeze_id, flavor, 'sha1'),
                'class': 'infolink iconspace', 
                'title': 'View archive with SHA1 sums', 
                'text': 'Show with SHA1 checksums - may take long'})
        output_objects.append({'object_type': 'html_form', 'text': '</p>'})

    return (output_objects, returnvalues.OK) 
