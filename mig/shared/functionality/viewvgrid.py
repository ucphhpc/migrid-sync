#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# viewvgrid - Display public details about a vgrid
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

"""Get info about a VGrid"""

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.vgrid import vgrid_owners, vgrid_members, vgrid_resources, \
     vgrid_settings
from shared.vgridaccess import user_allowed_vgrids


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['vgrid_info', defaults]


def build_vgriditem_object_from_vgrid_dict(configuration, vgrid_name,
                                       vgrid_dict, allow_vgrids):
    """Build a vgrid object based on input vgrid_dict"""

    vgrid_item = {
        'object_type': 'vgrid_info',
        'vgrid_name': vgrid_name,
        'fields': [],
        }
    description = vgrid_dict.get('description', 'No description available')
    owners = vgrid_dict.get('owners', ['Owners hidden'])
    members = vgrid_dict.get('members', ['Members hidden'])
    resources = vgrid_dict.get('resources', ['Resources hidden'])
    read_only = vgrid_dict.get('read_only', False)
    vgrid_item['fields'].append(('Description', description))
    vgrid_item['fields'].append(('Owners', ', '.join(owners)))
    vgrid_item['fields'].append(('Members', ', '.join(members)))
    vgrid_item['fields'].append(('Resources', ', '.join(resources)))
    vgrid_item['fields'].append(('Read-only', read_only)),
    return vgrid_item


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource details'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Show %s details' % configuration.site_vgrid_label})

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
    vgrid_list = accepted['vgrid_name']
    status = returnvalues.OK
    allowed_vgrids = user_allowed_vgrids(configuration, client_id)

    for vgrid_name in vgrid_list:
        vgrid_dict = {'vgrid_name': vgrid_name}
        (settings_status, settings) = vgrid_settings(vgrid_name, configuration)
        if settings_status:
            settings_dict = dict(settings)
        else:
            settings_dict = {}
        if settings_dict.get('visible_owners'):
            (owners_status, owners) = vgrid_owners(vgrid_name, configuration)
            if owners_status:
                vgrid_dict['owners'] = owners
        if settings_dict.get('visible_members'):
            (members_status, members) = vgrid_members(vgrid_name, configuration)
            if members_status:
                vgrid_dict['members'] = members
        if settings_dict.get('visible_resources'):
            (res_status, resources) = vgrid_resources(vgrid_name, configuration)
            if res_status:
                vgrid_dict['resources'] = resources            
        vgrid_item = build_vgriditem_object_from_vgrid_dict(configuration,
                                                            vgrid_name,
                                                            vgrid_dict,
                                                            allowed_vgrids)
        output_objects.append(vgrid_item)
    
        if client_id in vgrid_dict.get('owners', []):
            output_objects.append({'object_type': 'sectionheader',
                                   'text': 'Administrate'})
            output_objects.append({'object_type': 'link',
                                     'destination':
                                     'vgridadmin.py?vgrid_name=%s'\
                                     % vgrid_name,
                                     'class': 'adminlink',
                                     'title': 'Administrate %s' % vgrid_name, 
                                     'text': 'Administrate %s' % vgrid_name,
                                   })

        
    return (output_objects, status)
