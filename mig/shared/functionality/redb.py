#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# redb - manage runtime environments
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

"""Manage all available runtime environments"""

from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.defaults import default_pager_entries
from shared.functional import validate_input_and_cert
from shared.refunctions import build_reitem_object
from shared.html import jquery_ui_js, man_base_js, man_base_html, \
     html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.refunctions import list_runtime_environments, get_re_dict
from shared.vgridaccess import resources_using_re

list_operations = ['showlist', 'list']
show_operations = ['show', 'showlist']
allowed_operations = list(set(list_operations + show_operations))

def signature():
    """Signature of the main function"""

    defaults = {'operation': ['show']}
    return ['runtimeenvironments', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Runtime Environments'
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
    
    if not operation in allowed_operations:
        output_objects.append({'object_type': 'text', 'text':
                               '''Operation must be one of %s.''' % \
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    logger.info("%s %s begin for %s" % (op_name, operation, client_id))
    if operation in show_operations:

        # jquery support for tablesorter and confirmation on delete
        # table initially sorted by col. 2 (admin), then 0 (name)

        refresh_call = 'ajax_redb()'
        table_spec = {'table_id': 'runtimeenvtable', 'sort_order':
                      '[[2,1],[0,0]]', 'refresh_call': refresh_call}
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec])
        if operation == "show":
            add_ready += refresh_call
        title_entry['style'] = themed_styles(configuration)
        title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                                 add_init, add_ready)
        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})

        output_objects.append({'object_type': 'header', 'text'
                              : 'Runtime Environments'})

        output_objects.append(
            {'object_type': 'text', 'text' :
             'Runtime environments specify software/data available on resources.'
             })
        output_objects.append(
            {'object_type': 'link',
             'destination': 'docs.py?show=Runtime+Environments',
             'class': 'infolink iconspace',
             'title': 'Show information about runtime environment',
             'text': 'Documentation on runtime environments'})

        output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Existing runtime environments'})
        output_objects.append({'object_type': 'table_pager', 'entry_name': 'runtime envs',
                               'default_entries': default_pager_entries})

    runtimeenvironments = []
    if operation in list_operations:
        (status, ret) = list_runtime_environments(configuration)
        if not status:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : ret})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        for single_re in ret:
            (re_dict, msg) = get_re_dict(single_re, configuration)
            if not re_dict:
                output_objects.append({'object_type': 'error_text', 'text'
                                      : msg})
                return (output_objects, returnvalues.SYSTEM_ERROR)
            # Set providers explicitly after build_reitem_object to avoid import loop
            re_item = build_reitem_object(configuration, re_dict)
            re_name = re_item['name']
            re_item['providers'] = resources_using_re(configuration, re_name)
            re_item['resource_count'] = len(re_item['providers'])

            re_item['viewruntimeenvlink'] = {'object_type': 'link',
                                             'destination': "showre.py?re_name=%s" % re_name,
                                             'class': 'infolink iconspace',
                                             'title': 'View %s runtime environment' % re_name, 
                                             'text': ''}
            if client_id == re_item['creator']:
                js_name = 'delete%s' % hexlify(re_name)
                helper = html_post_helper(js_name, 'deletere.py',
                                          {'re_name': re_name})
                output_objects.append({'object_type': 'html_form', 'text': helper})
                re_item['ownerlink'] = {'object_type': 'link',
                                        'destination':
                                        "javascript: confirmDialog(%s, '%s');"\
                                        % (js_name, 'Really delete %s?' % re_name),
                                        'class': 'removelink iconspace',
                                        'title': 'Delete %s runtime environment' % re_name, 
                                        'text': ''}
            runtimeenvironments.append(re_item)

    output_objects.append({'object_type': 'runtimeenvironments',
                          'runtimeenvironments': runtimeenvironments})

    if operation in show_operations:
        if configuration.site_swrepo_url:
            output_objects.append({'object_type': 'sectionheader', 'text': 'Software Packages'})
            output_objects.append({'object_type': 'link',
                                   'destination': configuration.site_swrepo_url,
                                   'class': 'swrepolink iconspace',
                                   'title': 'Browse available software packages',
                                   'text': 'Open software catalogue for %s' % \
                                   configuration.short_title,
                                   })

        output_objects.append({'object_type': 'sectionheader', 'text': 'Additional Runtime Environments'})
        output_objects.append({'object_type': 'link',
                               'destination': 'adminre.py',
                               'class': 'addlink iconspace',
                               'title': 'Specify a new runtime environment', 
                               'text': 'Create a new runtime environment'})

    logger.info("%s %s end for %s" % (op_name, operation, client_id))
    return (output_objects, returnvalues.OK)
