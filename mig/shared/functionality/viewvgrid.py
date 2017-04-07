#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# viewvgrid - Display public details about a vgrid
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

"""Get info about a VGrid"""

import shared.returnvalues as returnvalues
from shared.defaults import keyword_owners, keyword_members, keyword_none, \
     keyword_all
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.vgrid import vgrid_owners, vgrid_members, vgrid_resources, \
     vgrid_settings, vgrid_is_owner, vgrid_is_owner_or_member
from shared.vgridaccess import user_vgrid_access

_valid_bool = [("yes", True), ("no", False)]


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
    bool_map = {True: "Yes", False: "No"}
    keyword_map = {keyword_owners: 'Owners',
                   keyword_members: 'Owners and members',
                   keyword_all: 'Public', keyword_none: 'No one'}
    description = vgrid_dict.get('description', 'No description available')
    owners = vgrid_dict.get('owners', ['*** Owners hidden ***'])
    members = vgrid_dict.get('members', ['*** Members hidden ***'])
    resources = vgrid_dict.get('resources', ['*** Resources hidden ***'])
    visible_owners = vgrid_dict.get('visible_owners', keyword_owners)
    owner_visibility = keyword_map[visible_owners]
    visible_members = vgrid_dict.get('visible_members', keyword_owners)
    member_visibility = keyword_map[visible_members]
    visible_resources = vgrid_dict.get('visible_resources', keyword_owners)
    resource_visibility = keyword_map[visible_resources]
    create_sharelink = vgrid_dict.get('create_sharelink', keyword_owners)
    sharelink_access = keyword_map[create_sharelink]
    write_shared_files = keyword_map[vgrid_dict.get('write_shared_files',
                                                    keyword_members)]
    write_priv_web = keyword_map[vgrid_dict.get('write_priv_web',
                                                keyword_owners)]
    write_pub_web = keyword_map[vgrid_dict.get('write_pub_web',
                                                keyword_owners)]
    hidden = bool_map[vgrid_dict.get('hidden', False)]
    vgrid_item['fields'].append(('Description', description))
    vgrid_item['fields'].append(('Owners', '\n'.join(owners)))
    vgrid_item['fields'].append(('Members', '\n'.join(members)))
    vgrid_item['fields'].append(('Resources', ', '.join(resources)))
    vgrid_item['fields'].append(('Owner visibility', owner_visibility))
    vgrid_item['fields'].append(('Member visibility', member_visibility))
    vgrid_item['fields'].append(('Resource visibility', resource_visibility))
    vgrid_item['fields'].append(('Sharelink creation', sharelink_access))
    vgrid_item['fields'].append(('Write Shared Files', write_shared_files))
    vgrid_item['fields'].append(('Write Private Web Pages', write_priv_web))
    vgrid_item['fields'].append(('Write Public Web Pages', write_pub_web))
    vgrid_item['fields'].append(('Hidden', hidden))
    return vgrid_item

def user_view_access(configuration, vgrid_name, client_id, settings_dict,
                     field):
    """Check if client_id has access to view field participation for
    vgrid_name based on saved settings_dict.
    """
    required = settings_dict.get(field, keyword_owners)

    if required == keyword_owners:
        access = vgrid_is_owner(vgrid_name, client_id, configuration)
    elif required == keyword_members:
        access = vgrid_is_owner_or_member(vgrid_name, client_id, configuration)
    elif required == keyword_all:
        access = True
    else:
        access = False
    return access

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "%s Details" % label
    output_objects.append({'object_type': 'header', 'text':
                           'Show %s Details' % label})
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
    vgrid_access = user_vgrid_access(configuration, client_id)

    for vgrid_name in vgrid_list:
        vgrid_dict = {'vgrid_name': vgrid_name}
        (settings_status, settings_dict) = vgrid_settings(vgrid_name,
                                                          configuration,
                                                          recursive=True,
                                                          as_dict=True)
        if not settings_status:
            settings_dict = {}
        logger.info("loaded vgrid %s settings: %s" % (vgrid_name, settings_dict))
        vgrid_dict.update(settings_dict)
        if user_view_access(configuration, vgrid_name, client_id, settings_dict,
                            'visible_owners'):
            (owners_status, owners) = vgrid_owners(vgrid_name, configuration)
            if owners_status:
                vgrid_dict['owners'] = owners
        if user_view_access(configuration, vgrid_name, client_id, settings_dict,
                            'visible_members'):
            (members_status, members) = vgrid_members(vgrid_name, configuration)
            if members_status:
                vgrid_dict['members'] = members
        if user_view_access(configuration, vgrid_name, client_id, settings_dict,
                            'visible_resources'):
            (res_status, resources) = vgrid_resources(vgrid_name, configuration)
            if res_status:
                vgrid_dict['resources'] = resources            

        if user_view_access(configuration, vgrid_name, client_id, settings_dict,
                            'create_sharelink'):
                vgrid_dict['sharelink'] = settings_dict.get('create_sharelink',
                                                            keyword_owners)

        # Report no such vgrid if hidden
        
        if settings_dict.get('hidden', False) and \
               not client_id in vgrid_dict.get('owners', []):
            output_objects.append({'object_type': 'error_text', 'text':
                                   'No such %s: %s' % (label, vgrid_name)})
            status = returnvalues.CLIENT_ERROR
            continue

        # Show vgrid details based on participation and visibility settings
        
        vgrid_item = build_vgriditem_object_from_vgrid_dict(configuration,
                                                            vgrid_name,
                                                            vgrid_dict,
                                                            vgrid_access)
        output_objects.append(vgrid_item)
    
        if client_id in vgrid_dict.get('owners', []):
            output_objects.append({'object_type': 'sectionheader',
                                   'text': 'Administrate'})
            output_objects.append({'object_type': 'link',
                                     'destination':
                                     'adminvgrid.py?vgrid_name=%s'\
                                     % vgrid_name,
                                     'class': 'adminlink iconspace',
                                     'title': 'Administrate %s' % vgrid_name, 
                                     'text': 'Administrate %s' % vgrid_name,
                                   })

        
    return (output_objects, status)
