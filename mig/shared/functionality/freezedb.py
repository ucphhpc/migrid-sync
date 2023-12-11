#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# freezedb - manage frozen archives
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Manage all owned frozen archives"""
from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.defaults import default_pager_entries, csrf_field, keyword_final
from mig.shared.freezefunctions import build_freezeitem_object, \
    list_frozen_archives, get_frozen_meta, get_frozen_archive, \
    pending_archives_update, TARGET_ARCHIVE
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.html import man_base_js, man_base_html, html_post_helper
from mig.shared.init import initialize_main_variables, find_entry

list_operations = ['showlist', 'list']
show_operations = ['show', 'showlist']
allowed_operations = list(set(list_operations + show_operations))


def signature():
    """Signature of the main function"""

    defaults = {'operation': ['show'],
                'caching': ['false']}
    return ['frozenarchives', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Frozen Archives'
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

    operation = accepted['operation'][-1]
    caching = (accepted['caching'][-1].lower() in ('true', 'yes'))

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                               """Freezing archives is disabled on this site.
Please contact the %s site support (%s) if you think it should be enabled.
""" % (configuration.short_title, configuration.support_email)})
        return (output_objects, returnvalues.OK)

    if not operation in allowed_operations:
        output_objects.append({'object_type': 'text', 'text':
                               '''Operation must be one of %s.''' %
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    logger.info("%s %s begin for %s" % (op_name, operation, client_id))
    if operation in show_operations:

        # jquery support for tablesorter and confirmation on delete
        # table initially sorted by col. 5 (State), 3 (Created date), 2 (name)

        if client_id in configuration.site_freeze_admins:
            permanent_flavors = []
        else:
            permanent_flavors = configuration.site_permanent_freeze

        # NOTE: We distinguish between caching on page load and forced refresh
        refresh_helper = 'ajax_freezedb(%s, "%s", %%s)'
        # NOTE: must insert permanent_flavors list as string here
        refresh_call = refresh_helper % (
            "%s" % permanent_flavors, keyword_final)
        table_spec = {'table_id': 'frozenarchivetable', 'sort_order':
                      '[[5,1],[3,1],[2,0]]',
                      'refresh_call': refresh_call % 'false'}
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec])
        if operation == "show":
            add_ready += '%s;' % (refresh_call % 'true')
        title_entry['script']['advanced'] += add_import
        title_entry['script']['init'] += add_init
        title_entry['script']['ready'] += add_ready
        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})

        output_objects.append(
            {'object_type': 'header', 'text': 'Frozen Archives'})

        output_objects.append(
            {'object_type': 'text', 'text':
             '''Frozen archives are write-once collections of files used e.g.
in relation to conference paper submissions. Please note that local policies
may prevent users from deleting frozen archives without explicit acceptance
from the management.
        '''})

        output_objects.append(
            {'object_type': 'sectionheader', 'text': 'Existing frozen archives'})

        # Helper form for removes

        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        target_op = 'deletefreeze'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        helper = html_post_helper('delfreeze', '%s.py' % target_op,
                                  {'freeze_id': '__DYNAMIC__',
                                   'flavor': '__DYNAMIC__',
                                   'target': TARGET_ARCHIVE,
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})

        output_objects.append({'object_type': 'table_pager', 'entry_name':
                               'frozen archives',
                               'default_entries': default_pager_entries})

    frozenarchives, pending_updates = [], False
    if operation in list_operations:

        logger.info("list frozen archives with caching %s" % caching)
        # NOTE: we do NOT enforce creator match here as edituser can't update
        #       without breaking any published archives
        (list_status, ret) = list_frozen_archives(configuration, client_id,
                                                  strict_owner=False,
                                                  caching=caching)
        if not list_status:
            logger.error("%s: failed for '%s': %s" % (op_name,
                                                      client_id, ret))
            output_objects.append({'object_type': 'error_text', 'text': ret})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # NOTE: use simple pending check if caching to avoid lock during update
        if caching:
            pending_updates = pending_archives_update(configuration, client_id)
        else:
            pending_updates = False
        if pending_updates:
            logger.debug("found pending cache updates: %s" % pending_updates)
        else:
            logger.debug("no pending cache updates")

        logger.debug("%s %s: building list of archives" % (op_name, operation))
        for freeze_id in ret:
            # TODO: add file count to meta and switch here
            # (load_status, freeze_dict) = get_frozen_meta(client_id, freeze_id,
            #                                             configuration)
            (load_status, freeze_dict) = get_frozen_archive(client_id,
                                                            freeze_id,
                                                            configuration,
                                                            checksum_list=[],
                                                            caching=caching)
            if not load_status:
                logger.error("%s: load failed for '%s': %s" %
                             (op_name, freeze_id, freeze_dict))
                output_objects.append({'object_type': 'error_text', 'text':
                                       'Could not read details for %r' %
                                       freeze_id})
                return (output_objects, returnvalues.SYSTEM_ERROR)
            freeze_item = build_freezeitem_object(configuration, freeze_dict,
                                                  summary=True)
            freeze_id = freeze_item['id']
            flavor = freeze_item.get('flavor', 'freeze')

            # Users may view all their archives
            freeze_item['viewfreezelink'] = {
                'object_type': 'link',
                'destination': "showfreeze.py?freeze_id=%s&flavor=%s" %
                (freeze_id, flavor),
                'class': 'infolink iconspace',
                'title': 'View frozen archive %s' % freeze_id,
                'text': ''}
            # Users may edit pending or non-permanent archives
            # Freeze admins may edit all their own archives.
            if freeze_item['state'] != keyword_final or \
                    flavor not in configuration.site_permanent_freeze or \
                    client_id in configuration.site_freeze_admins:
                freeze_item['editfreezelink'] = {
                    'object_type': 'link',
                    'destination': "adminfreeze.py?freeze_id=%s" % freeze_id,
                    'class': 'adminlink iconspace',
                    'title': 'Edit archive %s' % freeze_id,
                    'text': ''}
            # Users may delete pending or non-permanent archives.
            # Freeze admins may delete all their own archives.
            if freeze_item['state'] != keyword_final or \
                    flavor not in configuration.site_permanent_freeze or \
                    client_id in configuration.site_freeze_admins:
                freeze_item['delfreezelink'] = {
                    'object_type': 'link', 'destination':
                    "javascript: confirmDialog(%s, '%s', %s, %s);" %
                    ('delfreeze', 'Really remove %s?' % freeze_id, 'undefined',
                     "{freeze_id: '%s', flavor: '%s'}" % (freeze_id, flavor)),
                    'class': 'removelink iconspace', 'title': 'Remove %s' %
                    freeze_id, 'text': ''}

            frozenarchives.append(freeze_item)
        logger.debug("%s %s: inserting list of %d archives" %
                     (op_name, operation, len(frozenarchives)))

    output_objects.append({'object_type': 'frozenarchives',
                           'frozenarchives': frozenarchives,
                           'pending_updates': pending_updates})

    if operation in show_operations:
        output_objects.append({'object_type': 'sectionheader', 'text':
                               'Additional Frozen Archives'})
        output_objects.append({'object_type': 'text', 'text': """
You can create frozen snapshots/archives of particular subsets of your data in
order to make sure a verbatim copy is preserved. The freeze archive method
includes support for persistent publishing, so that you can e.g. reference your
data in publications. Backup archives can be used as a basic backup mechanism,
so that you can manually recover from any erroneous file removals."""})

        output_objects.append({'object_type': 'html_form', 'text': """<p>
Choose one of the archive methods below to make a manual archive:
</p>
<p>"""})
        output_objects.append({'object_type': 'link',
                               'destination': 'adminfreeze.py?flavor=freeze',
                               'class': 'addlink iconspace',
                               'title': 'Make a new freeze archive of e.g. '
                               'research data to be published',
                               'text': 'Create a new freeze archive'})
        output_objects.append({'object_type': 'html_form', 'text': '</p><p>'})
        output_objects.append({'object_type': 'link',
                               'destination': 'adminfreeze.py?flavor=backup',
                               'class': 'addlink iconspace',
                               'title': 'Make a new backup archive of %s data'
                               % configuration.short_title,
                               'text': 'Create a new backup archive'})
        output_objects.append(
            {'object_type': 'html_form', 'text': "<br/><br/></p>"})

        if configuration.site_enable_duplicati:
            output_objects.append({'object_type': 'text', 'text': '''
Alternatively you can use Duplicati for traditional incremental backup/restore
with optional encryption of all your backup contents.'''})
            output_objects.append({'object_type': 'html_form', 'text': """
<p>For further details please refer to the """})
            output_objects.append({'object_type': 'link',
                                   'destination': 'setup.py?topic=duplicati',
                                   'class': '',
                                   'title': 'Open Duplicati settings',
                                   'text': 'Duplicati Settings'})
            output_objects.append({'object_type': 'html_form', 'text':
                                   """ and the %s documentation.<br/><br/></p>""" %
                                   configuration.short_title})

        if configuration.site_enable_seafile:
            output_objects.append({'object_type': 'text', 'text': '''
We recommend our Seafile sync solution for any small or medium sized data sets,
for which you want automatic file versioning and easy roll-back support.'''})
            output_objects.append({'object_type': 'html_form', 'text': """
<p>For further details please refer to the """})
            output_objects.append({'object_type': 'link',
                                   'destination': 'setup.py?topic=seafile',
                                   'class': '',
                                   'title': 'Open Seafile settings',
                                   'text': 'Seafile Settings'})
            output_objects.append({'object_type': 'html_form', 'text':
                                   """ and the %s documentation.</p>""" %
                                   configuration.short_title})
    logger.info("%s %s end for %s" % (op_name, operation, client_id))
    return (output_objects, returnvalues.OK)
