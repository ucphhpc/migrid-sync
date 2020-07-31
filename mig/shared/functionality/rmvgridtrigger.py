#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmvgridtrigger - remove vgrid trigger
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

"""Remove a trigger from a given vgrid"""
from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
     vgrid_is_trigger, vgrid_remove_triggers


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'rule_id': REJECT_UNSET}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Remove %s Trigger" % label
    output_objects.append({'object_type': 'header', 'text'
                          : 'Remove %s Trigger' % label})
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
    rule_id = accepted['rule_id'][-1]

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    logger.info("rmvgridtrigger %s %s" % (vgrid_name, rule_id))

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id,
                                  rule_id, 'trigger',
                                  configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif msg:

        # In case of warnings, msg is non-empty while ret_val remains True

        output_objects.append({'object_type': 'warning', 'text': msg})

    # if we get here user is either vgrid owner or has rule ownership

    # can't remove if not a participant

    if not vgrid_is_trigger(vgrid_name, rule_id, configuration, recursive=False):
        output_objects.append({'object_type': 'error_text', 'text':
                               '%s is not a trigger in %s %s.' % \
                               (rule_id, vgrid_name, label)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # remove

    (rm_status, rm_msg) = vgrid_remove_triggers(configuration, vgrid_name,
                                                 [rule_id])
    if not rm_status:
        logger.error('%s failed to remove trigger: %s' % (client_id, rm_msg))
        output_objects.append({'object_type': 'error_text', 'text': rm_msg})
        output_objects.append({'object_type': 'error_text', 'text':
                               '''%(rule_id)s might be listed as a trigger of
this %(vgrid_label)s because it is a trigger of a parent %(vgrid_label)s.
Removal must be performed from the most significant %(vgrid_label)s
possible.''' % {'rule_id': rule_id, 'vgrid_label': label}})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.info('%s removed trigger: %s' % (client_id, rule_id))
    output_objects.append({'object_type': 'text', 'text':
                           'Trigger %s successfully removed from %s %s!'
                           % (rule_id, vgrid_name, label)})
    output_objects.append({'object_type': 'link', 'destination':
                           'vgridworkflows.py?vgrid_name=%s' % vgrid_name,
                           'text': 'Back to workflows for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


