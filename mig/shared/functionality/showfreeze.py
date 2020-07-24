#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showfreeze - back end to request freeze files in write-once fashion
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

"""Show summary contents of frozen archive"""

import os

from shared import returnvalues
from shared.defaults import default_pager_entries, freeze_flavors, \
    csrf_field, keyword_updating, keyword_final
from shared.freezefunctions import is_frozen_archive, get_frozen_archive, \
    build_freezeitem_object, brief_freeze, supported_hash_algos, TARGET_PATH
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from shared.html import man_base_js, man_base_html, html_post_helper
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
    checksum_list = [i for i in accepted['checksum'] if i]
    operation = accepted['operation'][-1]

    if not flavor in freeze_flavors.keys():
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid freeze flavor: %s' % flavor})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title = freeze_flavors[flavor]['showfreeze_title']
    title_entry['text'] = title
    output_objects.append({'object_type': 'header', 'text': title})

    sorted_algos = supported_hash_algos()
    sorted_algos.sort()
    for checksum in checksum_list:
        if not checksum in sorted_algos:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Invalid checksum algo(s): %s' % checksum})
            return (output_objects, returnvalues.CLIENT_ERROR)

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Freezing archives is disabled on this site.
Please contact the site admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    if not operation in allowed_operations:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Operation must be one of %s.''' %
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    # We don't generally know checksum and edit status until AJAX returns
    hide_elems = {'edit': 'hidden', 'update': 'hidden', 'register': 'hidden'}
    for algo in sorted_algos:
        hide_elems['%ssum' % algo] = 'hidden'

    if operation in show_operations:

        # jquery support for tablesorter and confirmation dialog
        # table initially sorted by col. 0 (filename)

        refresh_call = 'ajax_showfreeze("%s", "%s", %s, "%s", "%s", "%s", "%s")' % \
                       (freeze_id, flavor, checksum_list, keyword_updating,
                        keyword_final, configuration.site_freeze_doi_url,
                        configuration.site_freeze_doi_url_field)
        table_spec = {'table_id': 'frozenfilestable', 'sort_order': '[[0,0]]',
                      'refresh_call': refresh_call}
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec])
        if operation == "show":
            add_ready += '%s;' % refresh_call

        # Only show requested checksums
        for algo in sorted_algos:
            if algo in checksum_list:
                add_ready += """
        $('.%ssum').show();
""" % checksum
            else:
                add_ready += """
        $('.%ssum').hide();
        """ % algo

        title_entry['script']['advanced'] += add_import
        title_entry['script']['init'] += add_init
        title_entry['script']['ready'] += add_ready
        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})
        output_objects.append({'object_type': 'table_pager', 'entry_name':
                               'frozen files', 'default_entries':
                               default_pager_entries, 'refresh_button': False})

        # Helper form for removes

        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        target_op = 'deletefreeze'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        helper = html_post_helper('delfreeze', '%s.py' % target_op,
                                  {'freeze_id': '__DYNAMIC__',
                                   'flavor': '__DYNAMIC__',
                                   'path': '__DYNAMIC__',
                                   'target': TARGET_PATH,
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})

    # NB: the restrictions on freeze_id prevents illegal directory traversal

    if not is_frozen_archive(client_id, freeze_id, configuration):
        logger.error("%s: invalid freeze '%s': %s" % (op_name,
                                                      client_id, freeze_id))
        output_objects.append(
            {'object_type': 'error_text',
             'text': "'%s' is not an existing frozen archive!" % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if operation in list_operations:
        (load_status, freeze_dict) = get_frozen_archive(client_id, freeze_id,
                                                        configuration,
                                                        checksum_list)
        if not load_status:
            logger.error("%s: load failed for '%s': %s" %
                         (op_name, freeze_id, freeze_dict))
            output_objects.append(
                {'object_type': 'error_text',
                 'text': 'Could not read details for "%s"' % freeze_id})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        if freeze_dict.get('FLAVOR', 'freeze') != flavor:
            logger.error("%s: flavor mismatch for '%s': %s vs %s" %
                         (op_name, freeze_id, flavor, freeze_dict))
            output_objects.append(
                {'object_type': 'error_text',
                 'text': 'No such %s archive "%s"' % (flavor, freeze_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # Allow edit if not in updating/final state and allow request DOI if
        # finalized and not a backup archive.
        freeze_state = freeze_dict.get('STATE', keyword_final)
        if freeze_state == keyword_updating:
            hide_elems['update'] = ''
        elif freeze_state != keyword_final:
            hide_elems['edit'] = ''
        elif flavor != 'backup' and configuration.site_freeze_doi_url and \
                freeze_dict.get('PUBLISH_URL', ''):
            hide_elems['register'] = ''

        logger.debug("%s: build obj for '%s': %s" %
                     (op_name, freeze_id, brief_freeze(freeze_dict)))
        output_objects.append(
            build_freezeitem_object(configuration, freeze_dict))

    if operation == "show":
        # insert dummy placeholder to build table
        output_objects.append({'object_type': 'frozenarchive',
                               'id': freeze_id, 'creator': client_id,
                               'flavor': flavor,  'frozenfiles': [],
                               'name': 'loading ...',
                               'description': 'loading ...',
                               'created': 'loading ...',
                               'state': 'loading ...'})
    if operation in show_operations:
        output_objects.append({'object_type': 'html_form', 'text': """<p>
Show archive with file checksums - might take quite a while to calculate:
</p>"""})
        for algo in sorted_algos:
            output_objects.append({'object_type': 'html_form', 'text': '<p>'})
            output_objects.append({
                'object_type': 'link',
                'destination': "showfreeze.py?freeze_id=%s;flavor=%s;checksum=%s"
                % (freeze_id, flavor, algo),
                'class': 'infolink iconspace genericbutton',
                'title': 'View archive with %s checksums' % algo.upper(),
                'text': 'Show with %s checksums' % algo.upper()
            })
            output_objects.append({'object_type': 'html_form', 'text': '</p>'})

        # We don't know state of archive in this case until AJAX returns
        # so we hide the section and let AJAX show it if relevant
        output_objects.append({'object_type': 'html_form', 'text': """
<div class='updatearchive %(update)s'>
<p class='warn_message'>
Archive is currently in the process of being updated. No further changes can be
applied until running archive operations are completed. 
</p>
</div>
<div class='editarchive %(edit)s'>
<p>
You can continue inspecting and changing your archive until you're satisfied,
then finalize it for actual persistent freezing.
</p>
<p>""" % hide_elems})
        output_objects.append({
            'object_type': 'link',
            'destination': "adminfreeze.py?freeze_id=%s;flavor=%s" %
            (freeze_id, flavor),
            'class': 'editarchivelink iconspace genericbutton',
            'title': 'Further modify your pending %s archive' % flavor,
            'text': 'Edit archive'
        })
        output_objects.append({'object_type': 'html_form', 'text': '</p>'})
        form_method = 'post'
        target_op = 'createfreeze'
        csrf_limit = get_csrf_limit(configuration)
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        helper = html_post_helper('createfreeze', '%s.py' % target_op,
                                  {'freeze_id': freeze_id,
                                   'flavor': flavor,
                                   'freeze_state': keyword_final,
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        output_objects.append({
            'object_type': 'link',
            'destination':
            "javascript: confirmDialog(%s, '%s');" %
            ('createfreeze', 'Really finalize %s?' % freeze_id),
            'class': 'finalizearchivelink iconspace genericbutton',
            'title': 'Finalize %s archive to prevent further changes' % flavor,
            'text': 'Finalize archive',
        })
        output_objects.append({'object_type': 'html_form', 'text': """
</div>
<div class='registerarchive %(register)s'>
<p>
You can register a <a href='http://www.doi.org/index.html'>Digital Object
Identifier (DOI)</a> for finalized archives. This may be useful in case you
want to reference the contents in a publication.
</p>
""" % hide_elems})
        form_method = 'post'
        target_op = 'registerfreeze'
        csrf_limit = get_csrf_limit(configuration)
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        helper = html_post_helper('registerfreeze',
                                  configuration.site_freeze_doi_url,
                                  {'freeze_id': freeze_id,
                                   'freeze_author': client_id,
                                   configuration.site_freeze_doi_url_field:
                                   '__DYNAMIC__',
                                   'callback_url': "%s.py" % target_op,
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        output_objects.append({'object_type': 'html_form', 'text':
                               configuration.site_freeze_doi_text})
        output_objects.append({
            'object_type': 'link',
            'destination':
            "javascript: confirmDialog(%s, '%s');" %
            ('registerfreeze', 'Really request DOI for %s?' % freeze_id),
            'class': 'registerarchivelink iconspace genericbutton',
            'title': 'Register a DOI for %s archive %s' % (flavor, freeze_id),
            'text': 'Request archive DOI',
        })
        output_objects.append({'object_type': 'html_form', 'text': """
</div>"""})

    output_objects.append({'object_type': 'html_form', 'text': """
    <div class='vertical-spacer'></div>"""})

    return (output_objects, returnvalues.OK)
