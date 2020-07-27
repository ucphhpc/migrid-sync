#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# addvgridtrigger - add vgrid trigger
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

"""Add a trigger to a given vgrid"""
from __future__ import absolute_import

import os
import shlex
import time

from .shared.base import client_id_dir
from .shared.defaults import any_state, keyword_auto, valid_trigger_actions, \
    valid_trigger_changes, keyword_all
from .shared.functional import validate_input_and_cert, REJECT_UNSET
from .shared.handlers import safe_handler, get_csrf_limit
from .shared.init import initialize_main_variables, find_entry
from .shared.validstring import valid_user_path
from .shared.vgrid import init_vgrid_script_add_rem, vgrid_is_trigger, \
    vgrid_is_trigger_owner, vgrid_list_subvgrids, vgrid_add_triggers, \
    vgrid_triggers
from .shared import returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'rule_id': [keyword_auto],
                'path': [''],
                'changes': [any_state],
                'action': [keyword_auto],
                'arguments': [''],
                'rate_limit': [''],
                'settle_time': [''],
                'match_files': ['True'],
                'match_dirs': ['False'],
                'match_recursive': ['False'],
                'rank': [''],
                }
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Add/Update %s Trigger" % label
    output_objects.append({'object_type': 'header', 'text':
                           'Add/Update %s Trigger' % label})
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

    # NOTE: strip leftmost slashes from all fields used in file paths to avoid
    # interference with os.path.join calls. Furthermore we strip and normalize
    # the path variable first to make sure it does not point outside the vgrid.
    # In practice any such directory traversal attempts will generally be moot
    # since the grid_events daemon only starts a listener for each top-level
    # vgrid and in there only reacts to events that match trigger rules from
    # that particular vgrid. Thus only subvgrid access to parent vgrids might
    # be a concern and still of limited consequence.
    # NOTE: merge multi args into one string and split again to get flat array
    rule_id = accepted['rule_id'][-1].strip()
    vgrid_name = accepted['vgrid_name'][-1].strip().lstrip(os.sep)
    path = os.path.normpath(accepted['path'][-1].strip()).lstrip(os.sep)
    changes = [i.strip() for i in ' '.join(accepted['changes']).split()]
    action = accepted['action'][-1].strip()
    arguments = [i.strip() for i in
                 shlex.split(' '.join(accepted['arguments']))]
    rate_limit = accepted['rate_limit'][-1].strip()
    settle_time = accepted['settle_time'][-1].strip()
    match_files = accepted['match_files'][-1].strip() == 'True'
    match_dirs = accepted['match_dirs'][-1].strip() == 'True'
    match_recursive = accepted['match_recursive'][-1].strip() == 'True'
    rank_str = accepted['rank'][-1]
    try:
        rank = int(rank_str)
    except ValueError:
        rank = None

    logger.debug("addvgridtrigger with args: %s" % user_arguments_dict)

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep

    # we just use a high res timestamp as automatic rule_id

    if rule_id == keyword_auto:
        rule_id = "%d" % (time.time() * 1E8)

    if action == keyword_auto:
        action = valid_trigger_actions[0]

    if any_state in changes:
        changes = valid_trigger_changes

    logger.info("addvgridtrigger %s" % vgrid_name)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id,
                                  rule_id, 'trigger',
                                  configuration)
    if not ret_val:
        output_objects.append(
            {'object_type': 'error_text', 'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif msg:

        # In case of warnings, msg is non-empty while ret_val remains True

        output_objects.append({'object_type': 'warning', 'text': msg})

    # if we get here user is either vgrid owner or allowed to add rule

    # don't add if already in vgrid or parent vgrid - but update if owner

    update_id = None
    if vgrid_is_trigger(vgrid_name, rule_id, configuration):
        if vgrid_is_trigger_owner(vgrid_name, rule_id, client_id,
                                  configuration):
            update_id = 'rule_id'
        else:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s is already a trigger owned by somebody else in the %s' %
                 (rule_id, label)})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # don't add if already in subvgrid

    (list_status, subvgrids) = vgrid_list_subvgrids(vgrid_name,
                                                    configuration)
    if not list_status:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Error getting list of sub%ss: %s' %
                               (label, subvgrids)})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    for subvgrid in subvgrids:
        if vgrid_is_trigger(subvgrid, rule_id, configuration, recursive=False):
            output_objects.append({'object_type': 'error_text', 'text':
                                   '''%(rule_id)s is already in a
sub-%(vgrid_label)s (%(subvgrid)s). Please remove the trigger from the
sub-%(vgrid_label)s and try again''' % {'rule_id': rule_id,
                                        'subvgrid': subvgrid,
                                        'vgrid_label': label}})
            return (output_objects, returnvalues.CLIENT_ERROR)

    if not action in valid_trigger_actions:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "invalid action value %s" % action})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if keyword_all in changes:
        changes = valid_trigger_changes
    for change in changes:
        if not change in valid_trigger_changes:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "found invalid change value %s" % change})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Check if we should load saved trigger for rank change or update

    rule_dict = None
    if rank is not None or update_id is not None:
        (load_status, all_triggers) = vgrid_triggers(vgrid_name, configuration)
        if not load_status:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'Failed to load triggers for %s: %s' %
                (vgrid_name, all_triggers)})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        for saved_dict in all_triggers:
            if saved_dict['rule_id'] == rule_id:
                rule_dict = saved_dict
                break
        if rule_dict is None:
            output_objects.append({
                'object_type': 'error_text', 'text':
                'No such trigger %s for %s: %s' % (rule_id, vgrid_name,
                                                   all_triggers)})
            return (output_objects, returnvalues.CLIENT_ERROR)
    elif not path:
        # New trigger with missing path
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Either path or rank must
be set.'''})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif action == "submit" and not arguments:
        # New submit trigger with missing mrsl arguments
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Submit triggers must give
a job description file path as argument.'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Handle create and update (i.e. new, update all or just refresh mRSL)

    if rank is None:

        # IMPORTANT: we save the job template contents to avoid potential abuse
        # Otherwise someone else in the VGrid could tamper with the template
        # and make the next trigger execute arbitrary code on behalf of the
        # rule owner.

        templates = []

        # Merge current and saved values

        req_dict = {'rule_id': rule_id,
                    'vgrid_name': vgrid_name,
                    'path': path,
                    'changes': changes,
                    'run_as': client_id,
                    'action': action,
                    'arguments': arguments,
                    'rate_limit': rate_limit,
                    'settle_time': settle_time,
                    'match_files': match_files,
                    'match_dirs': match_dirs,
                    'match_recursive': match_recursive,
                    'templates': templates
                    }
        if rule_dict is None:
            rule_dict = req_dict
        else:
            for field in user_arguments_dict:
                if field in req_dict:
                    rule_dict[field] = req_dict[field]

        # Now refresh template contents

        if rule_dict['action'] == "submit":
            for rel_path in rule_dict['arguments']:
                # IMPORTANT: path must be expanded to abs for proper chrooting
                abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
                try:
                    if not valid_user_path(configuration, abs_path, base_dir,
                                           True):
                        logger.warning(
                            '%s tried to %s restricted path %s ! (%s)'
                            % (client_id, op_name, abs_path, rel_path))
                        raise ValueError('invalid submit path argument: %s'
                                         % rel_path)
                    temp_fd = open(abs_path)
                    templates.append(temp_fd.read())
                    temp_fd.close()
                except Exception as err:
                    logger.error("read submit argument file failed: %s" % err)
                    output_objects.append(
                        {'object_type': 'error_text', 'text':
                         'failed to read submit argument file "%s"' % rel_path
                         })
                    return (output_objects, returnvalues.CLIENT_ERROR)

        # Save updated template contents here
        rule_dict['templates'] = templates

    # Add to list and pickle

    (add_status, add_msg) = vgrid_add_triggers(configuration, vgrid_name,
                                               [rule_dict], update_id, rank)
    if not add_status:
        logger.error('%s failed to add/update trigger: %s' % (client_id,
                                                              add_msg))
        output_objects.append({'object_type': 'error_text', 'text': '%s'
                               % add_msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if rank is not None:
        logger.info('%s moved trigger %s to %d' % (client_id, rule_id, rank))
        output_objects.append({'object_type': 'text', 'text':
                               'moved %s trigger %s to position %d' %
                               (vgrid_name, rule_id, rank)})
    elif update_id:
        logger.info('%s updated trigger: %s' % (client_id, rule_dict))
        output_objects.append(
            {'object_type': 'text', 'text':
             'Existing trigger %s successfully updated in %s %s!' %
             (rule_id, vgrid_name, label)})
    else:
        logger.info('%s added new trigger: %s' % (client_id, rule_dict))
        output_objects.append(
            {'object_type': 'text', 'text':
             'New trigger %s successfully added to %s %s!' %
             (rule_id, vgrid_name, label)})

    output_objects.append({'object_type': 'link', 'destination':
                           'vgridworkflows.py?vgrid_name=%s' % vgrid_name,
                           'text': 'Back to workflows for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)
