#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resman - manage resources
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

"""Resource management back end functionality"""

import time

import shared.returnvalues as returnvalues
from shared.base import sandbox_resource
from shared.defaults import default_pager_entries, csrf_field
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import jquery_ui_js, man_base_js, man_base_html, \
     html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.resource import anon_to_real_res_map
from shared.vgridaccess import user_visible_res_confs, get_resource_map, \
     OWNERS, CONF

list_operations = ['showlist', 'list']
show_operations = ['show', 'showlist']
allowed_operations = list(set(list_operations + show_operations))

def signature():
    """Signature of the main function"""

    defaults = {'show_sandboxes': ['false'], 'operation': ['show']}
    return ['resources', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    status = returnvalues.OK
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource management'
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

    show_sandboxes = (accepted['show_sandboxes'][-1] != 'false')
    operation = accepted['operation'][-1]

    if not operation in allowed_operations:
        output_objects.append({'object_type': 'text', 'text':
                               '''Operation must be one of %s.''' % \
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    logger.info("%s %s begin for %s" % (op_name, operation, client_id))
    if operation in show_operations:

        # jquery support for tablesorter and confirmation on delete
        # table initially sorted by col. 1 (admin), then 0 (name)

        refresh_call = 'ajax_resman()'
        table_spec = {'table_id': 'resourcetable', 'sort_order':
                      '[[1,0],[0,0]]', 'refresh_call': refresh_call}
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec])
        if operation == "show":
            add_ready += refresh_call
        title_entry['style'] = themed_styles(configuration)
        title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                                 add_init, add_ready)
        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})

        output_objects.append({'object_type': 'header', 'text':
                               'Available Resources'})

        output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Resources available on this server'})
        output_objects.append({'object_type': 'text', 'text'
                              : '''
All available resources are listed below with overall hardware specifications.
Any resources that you own will have a administration icon that you can click
to open resource management.
'''
                           })

        # Helper forms for requests and removes

        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        target_op = 'sendrequestaction'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        helper = html_post_helper('reqresowner', '%s.py' % target_op,
                                  {'unique_resource_name': '__DYNAMIC__',
                                   'request_type': 'resourceowner',
                                   'request_text': '',
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        target_op = 'rmresowner'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        helper = html_post_helper('rmresowner', '%s.py' % target_op,
                                  {'unique_resource_name': '__DYNAMIC__',
                                   'cert_id': client_id,
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})

        output_objects.append({'object_type': 'table_pager', 'entry_name':
                               'resources', 'default_entries':
                               default_pager_entries})

    resources = []
    if operation in list_operations:
        # TODO: next 3 call are slow because we reload pickles and maps
        visible_res_confs = user_visible_res_confs(configuration, client_id)
        res_map = get_resource_map(configuration)
        anon_map = anon_to_real_res_map(configuration.resource_home)

        # Iterate through resources and show management for each one requested

        fields = ['PUBLICNAME', 'NODECOUNT', 'CPUCOUNT', 'MEMORY', 'DISK',
                  'ARCHITECTURE', 'SANDBOX', 'RUNTIMEENVIRONMENT']

        # NOTE: only resources that user is allowed to access are listed.
        #       Resource with neither exes nor stores are not shown to anyone
        #       but the owners. Similarly resources are not shown if all
        #       resource units solely participate in VGrids, which the user
        #       can't access.
        for visible_res_name in visible_res_confs.keys():
            unique_resource_name = visible_res_name
            if visible_res_name in anon_map.keys():
                unique_resource_name = anon_map[visible_res_name]

            if not show_sandboxes and sandbox_resource(unique_resource_name):
                continue
            res_obj = {'object_type': 'resource', 'name': visible_res_name}

            if client_id in res_map[unique_resource_name][OWNERS]:

                # Admin of resource when owner

                res_obj['resownerlink'] = {
                    'object_type': 'link',
                    'destination':
                    "javascript: confirmDialog(%s, '%s', %s, %s);"\
                    % ('rmresowner', 'Really leave %s owners?' % \
                                            unique_resource_name,
                       'undefined', "{unique_resource_name: '%s'}" % \
                       unique_resource_name),
                    'class': 'removelink iconspace',
                    'title': 'Leave %s owners' % unique_resource_name, 
                    'text': ''}
                res_obj['resdetailslink'] = {
                    'object_type': 'link',
                    'destination':
                    'resadmin.py?unique_resource_name=%s'\
                    % unique_resource_name,
                    'class': 'adminlink iconspace',
                    'title': 'Administrate %s' % unique_resource_name, 
                    'text': ''}
            else:

                # link to become owner

                res_obj['resownerlink'] = {
                    'object_type': 'link',
                    'destination':
                    "javascript: confirmDialog(%s, '%s', '%s', %s);" % \
                    ('reqresowner', "Request ownership of " + \
                     visible_res_name + ":<br/>" + \
                     "\nPlease write a message to the owners (field below).",
                     'request_text',
                     "{unique_resource_name: '%s'}" % visible_res_name),
                    'class': 'addlink iconspace',
                    'title': 'Request ownership of %s' % visible_res_name,
                    'text': ''}
                
                res_obj['resdetailslink'] = {
                    'object_type': 'link',
                    'destination':
                    'viewres.py?unique_resource_name=%s'\
                    % visible_res_name,
                    'class': 'infolink iconspace',
                    'title': 'View detailed %s specs' % \
                    visible_res_name, 
                    'text': ''}
                
            # fields for everyone: public status
            for name in fields:
                res_obj[name] = res_map[unique_resource_name][CONF].get(name,
                                                                        '')
            # Use runtimeenvironment names instead of actual definitions
            res_obj['RUNTIMEENVIRONMENT'] = [i[0] for i in \
                                             res_obj['RUNTIMEENVIRONMENT']]
            resources.append(res_obj)

    if operation == "show":
        # insert dummy placeholder to build table
        res_obj = {'object_type': 'resource', 'name': ''}
        resources.append(res_obj)
        
    output_objects.append({'object_type': 'resource_list', 'resources':
                           resources})

    if operation in show_operations:
        if configuration.site_enable_sandboxes:
            if show_sandboxes:
                output_objects.append({'object_type': 'link',
                                       'destination': '?show_sandboxes=false',
                                       'class': 'removeitemlink iconspace',
                                       'title': 'Hide sandbox resources', 
                                       'text': 'Exclude sandbox resources',
                                       })

            else:
                output_objects.append({'object_type': 'link',
                                       'destination': '?show_sandboxes=true',
                                       'class': 'additemlink iconspace',
                                       'title': 'Show sandbox resources', 
                                       'text': 'Include sandbox resources',
                                       })

        output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Resource Status'})
        output_objects.append({'object_type': 'text',
                               'text': '''
Live resource status is available in the resource monitor page with all
%s/resources you can access
''' % configuration.site_vgrid_label})
        output_objects.append({
            'object_type': 'link',
            'destination': 'showvgridmonitor.py?vgrid_name=ALL',
            'class': 'monitorlink iconspace',
            'title': 'Show monitor with all resources you can access', 
            'text': 'Global resource monitor',
            })

        output_objects.append({'object_type': 'sectionheader', 'text':
                               'Additional Resources'})
        output_objects.append({
            'object_type': 'text', 'text':
            'You can sign up spare or dedicated resources to the grid below.'
            })
        output_objects.append({'object_type': 'link',
                               'destination' : 'resedit.py',
                               'class': 'addlink iconspace',
                               'title': 'Show sandbox resources',                            
                               'text': 'Create a new %s resource' % \
                               configuration.short_title, 
                               })
        output_objects.append({'object_type': 'sectionheader', 'text': ''})

        if configuration.site_enable_sandboxes:
            output_objects.append({
                'object_type': 'link',
                'destination': 'ssslogin.py',
                'class': 'adminlink iconspace',
                'title': 'Administrate and monitor your sandbox resources',
                'text': 'Administrate %s sandbox resources' % \
                configuration.short_title})
            output_objects.append({'object_type': 'sectionheader', 'text': ''})
            output_objects.append({
                'object_type': 'link',
                'destination': 'oneclick.py',
                'class': 'sandboxlink iconspace',
                'title': 'Run a One-click resource in your browser', 
                'text': 'Use this computer as One-click %s resource' % \
                configuration.short_title})

    logger.info("%s %s end for %s" % (op_name, operation, client_id))
    return (output_objects, status)
