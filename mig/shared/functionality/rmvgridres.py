#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmvgridres - remove vgrid resource
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

"""Remove a resource from a given vgrid"""

from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.useradm import get_full_user_map
from mig.shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
    vgrid_is_resource, vgrid_remove_resources, allow_resources_adm, \
    vgrid_manage_allowed


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'unique_resource_name': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Remove %s Resource" % label
    output_objects.append({'object_type': 'header', 'text':
                           'Remove %s Resource' % label})
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

    vgrid_name = accepted['vgrid_name'][-1]
    unique_resource_name = accepted['unique_resource_name'][-1].lower()

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    # Optional site-wide limitation of manage vgrid permission
    if not user_dict or \
            not vgrid_manage_allowed(configuration, user_dict):
        logger.warning("user %s is not allowed to manage vgrids!" % client_id)
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Only privileged users can manage %ss' % label})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # make sure vgrid settings allow this owner to edit resources

    (allow_status, allow_msg) = allow_resources_adm(configuration, vgrid_name,
                                                    client_id)
    if not allow_status:
        output_objects.append({'object_type': 'error_text', 'text': allow_msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id,
                                  unique_resource_name, 'resource',
                                  configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif msg:

        # In case of warnings, msg is non-empty while ret_val remains True

        output_objects.append({'object_type': 'warning', 'text': msg})

    if not vgrid_is_owner(vgrid_name, client_id, configuration):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             '''You must be an owner of the %s to remove a resource!''' %
             label})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't remove if not a participant

    if not vgrid_is_resource(vgrid_name, unique_resource_name, configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               '%s is not a resource in %s or a parent %s.'
                               % (unique_resource_name, vgrid_name, label)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # remove

    (rm_status, rm_msg) = vgrid_remove_resources(configuration, vgrid_name,
                                                 [unique_resource_name])
    if not rm_status:
        output_objects.append({'object_type': 'error_text', 'text': rm_msg})
        output_objects.append({'object_type': 'error_text', 'text':
                               '''%(res_name)s might be listed as a resource
of this %(vgrid_label)s because it is a resource of a parent %(vgrid_label)s.
Removal must be performed from the most significant %(vgrid_label)s possible.
''' % {'res_name': unique_resource_name, 'vgrid_label': label}})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text':
                           'Resource %s successfully removed from %s %s!' %
                           (unique_resource_name, vgrid_name, label)})
    output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)
