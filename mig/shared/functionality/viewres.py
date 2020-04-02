#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# viewres - Display public details about a resource
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""Get info about a resource"""

import shared.returnvalues as returnvalues
from shared.conf import get_resource_configuration
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.resconfkeywords import get_resource_keywords, \
    get_exenode_keywords, get_storenode_keywords
from shared.resource import anon_to_real_res_map
from shared.vgridaccess import user_visible_res_confs, user_vgrid_access, \
    get_resource_map, OWNERS, CONF


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': REJECT_UNSET, 'caching': ['true']}
    return ['resource_info', defaults]


def build_resitem_object_from_res_dict(configuration, unique_resource_name,
                                       res_dict, vgrid_access):
    """Build a resource object based on input res_dict"""

    res_keywords = get_resource_keywords(configuration)
    exe_keywords = get_exenode_keywords(configuration)
    store_keywords = get_storenode_keywords(configuration)
    res_fields = ['PUBLICNAME', 'PUBLICINFO', 'CPUCOUNT', 'NODECOUNT', 'MEMORY', 'DISK',
                  'ARCHITECTURE', 'JOBTYPE', 'MAXUPLOADBANDWIDTH',
                  'MAXDOWNLOADBANDWIDTH', 'SANDBOX']
    exe_fields = ['cputime', 'nodecount']
    store_fields = ['storage_disk', 'storage_protocol']
    res_item = {
        'object_type': 'resource_info',
        'unique_resource_name': unique_resource_name,
        'fields': [],
        'exes': {},
        'stores': {},
    }
    for name in res_fields:
        res_item['fields'].append((res_keywords[name]['Title'],
                                   res_dict.get(name, 'UNKNOWN')))
    rte_spec = res_dict.get('RUNTIMEENVIRONMENT', [])
    res_item['fields'].append((res_keywords['RUNTIMEENVIRONMENT']['Title'],
                               ', '.join([name for (name, val) in rte_spec])))
    for exe in res_dict.get('EXECONFIG', []):
        exe_name = exe['name']
        if not exe_name:
            continue
        exe_spec = res_item['exes'][exe_name] = []
        for name in exe_fields:
            exe_spec.append((exe_keywords[name]['Title'],
                             exe.get(name, 'UNKNOWN')))
        exec_vgrids = exe.get('vgrid', [])
        visible_vgrids = [i for i in exec_vgrids if i in vgrid_access]
        if visible_vgrids != exec_vgrids:
            visible_vgrids.append('%d undisclosed' %
                                  (len(exec_vgrids) - len(visible_vgrids)))
        exe_spec.append((exe_keywords['vgrid']['Title'],
                         ', '.join(visible_vgrids)))
    for store in res_dict.get('STORECONFIG', []):
        store_name = store['name']
        if not store_name:
            continue
        store_spec = res_item['stores'][store_name] = []
        for name in store_fields:
            store_spec.append((store_keywords[name]['Title'],
                               store.get(name, 'UNKNOWN')))
        storage_vgrids = store.get('vgrid', [])
        visible_vgrids = [i for i in storage_vgrids if i in vgrid_access]
        if visible_vgrids != storage_vgrids:
            visible_vgrids.append('%d undisclosed' %
                                  (len(storage_vgrids) - len(visible_vgrids)))
        store_spec.append((store_keywords['vgrid']['Title'],
                           ', '.join(visible_vgrids)))
    return res_item


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource details'
    output_objects.append(
        {'object_type': 'header', 'text': 'Show resource details'})

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
    resource_list = accepted['unique_resource_name']
    caching = (accepted['caching'][-1].lower() in ('true', 'yes'))
    status = returnvalues.OK
    visible_res = user_visible_res_confs(
        configuration, client_id, caching=True)
    vgrid_access = user_vgrid_access(configuration, client_id, caching=caching)
    res_map = get_resource_map(configuration, caching=caching)
    anon_map = anon_to_real_res_map(configuration.resource_home)

    for visible_res_name in resource_list:
        unique_resource_name = visible_res_name
        if visible_res_name in anon_map.keys():
            unique_resource_name = anon_map[visible_res_name]
        if not visible_res_name in visible_res.keys():
            logger.warning('User %s not allowed to view %s (%s)' %
                           (client_id, visible_res_name, visible_res.keys()))
            output_objects.append({'object_type': 'error_text',
                                   'text': 'invalid resource %s' %
                                   visible_res_name})
            continue
        res_dict = visible_res[visible_res_name]
        res_item = build_resitem_object_from_res_dict(configuration,
                                                      visible_res_name,
                                                      res_dict,
                                                      vgrid_access)
        output_objects.append(res_item)

        if client_id in res_map[unique_resource_name][OWNERS]:
            output_objects.append({'object_type': 'sectionheader',
                                   'text': 'Administrate'})
            output_objects.append({'object_type': 'link',
                                   'destination':
                                   'resadmin.py?unique_resource_name=%s'
                                   % unique_resource_name,
                                   'class': 'adminlink iconspace',
                                   'title': 'Administrate %s' % unique_resource_name,
                                   'text': 'Administrate %s' % unique_resource_name,
                                   })

    return (output_objects, status)
