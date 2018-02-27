#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridworkflows - data-driven workflows for owners and members
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Access to the VGrid workflows configured in a given vgrids vgrid_home dir.
Owners and members of a VGrid can configure triggers to react on file changes
anywhere in their VGrid shared directory.
Triggers are personal but the workflows page allows sharing of trigger job
status and so on to ease workflow collaboration.
"""

import os
import re
import time

from shared.base import client_id_dir
import shared.returnvalues as returnvalues
from shared.defaults import keyword_all, keyword_auto, \
    valid_trigger_changes, valid_trigger_actions, workflows_log_name, \
    workflows_log_cnt, pending_states, final_states, img_trigger_prefix
from shared.events import get_expand_map, get_command_map
from shared.fileio import unpickle, makedirs_rec, move_file
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.html import jquery_ui_js, man_base_js, man_base_html, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.parseflags import verbose
from shared.vgrid import vgrid_add_remove_table, vgrid_is_owner_or_member, \
     vgrid_triggers, vgrid_set_triggers

default_pager_entries = 20

# TODO: optimize (differential) log reload for big logs
# TODO: tablesorter does not kick in when tab is initially loaded while hidden

list_operations = ['showlist', 'list']
show_operations = ['show', 'showlist']
allowed_operations = list(set(list_operations + show_operations))

def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET,
                'operation': ['show'],
                'flags': ['']}
    return ['html_form', defaults]


def read_trigger_log(configuration, vgrid_name, flags):
    """Read-in saved trigger logs for vgrid workflows page. We read in all
    rotated logs. If flags don't include verbose we try to filter out all
    system trigger lines.
    """

    log_content = ''
    for i in xrange(workflows_log_cnt - 1, -1, -1):
        log_name = '%s.%s' % (configuration.vgrid_triggers,
                              workflows_log_name)
        if i > 0:
            log_name += '.%d' % i
        log_path = os.path.join(configuration.vgrid_home, vgrid_name,
                                log_name)
        configuration.logger.debug('read from %s' % log_path)
        try:
            log_fd = open(log_path)
            log_content += log_fd.read()
            configuration.logger.debug('read in log lines:\n%s' % log_content)
            log_fd.close()
        except IOError:
            pass

    if not verbose(flags):
        # Strip system trigger lines containing '.meta/EXT.last_modified'
        system_pattern = '[0-9 ,:-]* [A-Z]* .*/\.meta/.*\.last_modified.*\n'
        log_content = re.sub(system_pattern, '', log_content)

    return log_content


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = '%s Workflows' % label
    # NOTE: Delay header entry here to include vgrid_name
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
    operation = accepted['operation'][-1]
    flags = ''.join(accepted['flags'][-1])
    
    if not vgrid_is_owner_or_member(vgrid_name, client_id,
                                    configuration):
        output_objects.append({'object_type': 'error_text',
                              'text': '''You must be an owner or member of %s vgrid to
access the workflows.'''
                               % vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not operation in allowed_operations:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Operation must be one of %s.''' % \
                               ', '.join(allowed_operations)})
        return (output_objects, returnvalues.OK)

    if operation in show_operations:

        # jquery support for tablesorter (and unused confirmation dialog)
        # table initially sorted by 0 (last update / date) 

        refresh_call = 'ajax_workflowjobs("%s", "%s")' % (vgrid_name, flags)
        table_spec = {'table_id': 'workflowstable', 'sort_order': '[[0,1]]',
                      'refresh_call': refresh_call
                      }
        (add_import, add_init, add_ready) = man_base_js(configuration,
                                                        [table_spec])
        if operation == "show":
            add_ready += '%s;' % refresh_call
        add_ready += '''
              /* Init variables helper as foldable but closed and with individual
              heights */
              $(".variables-accordion").accordion({
                                           collapsible: true,
                                           active: false,
                                           heightStyle: "content"
                                          });
              /* fix and reduce accordion spacing */
              $(".ui-accordion-header").css("padding-top", 0)
                                       .css("padding-bottom", 0).css("margin", 0);
              /* NOTE: requires managers CSS fix for proper tab bar height */      
              $(".workflow-tabs").tabs();
              $("#logarea").scrollTop($("#logarea")[0].scrollHeight);
        '''
        title_entry['style'] = themed_styles(configuration)
        title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                                 add_init, add_ready)
        output_objects.append({'object_type': 'html_form',
                               'text': man_base_html(configuration)})

        output_objects.append({'object_type': 'header', 'text':
                               '%s Workflows for %s' % (label, vgrid_name)})

    logger.info('vgridworkflows %s %s' % (vgrid_name, operation))

    # Iterate through jobs and list details for each

    trigger_jobs = []
    log_content = ''

    if operation in list_operations:
        trigger_job_dir = os.path.join(configuration.vgrid_home,
                                       os.path.join(vgrid_name, '.%s.jobs'
                                       % configuration.vgrid_triggers))
        trigger_job_pending_dir = os.path.join(trigger_job_dir,
                'pending_states')
        trigger_job_final_dir = os.path.join(trigger_job_dir, 'final_states'
                )

        if makedirs_rec(trigger_job_pending_dir, logger) \
            and makedirs_rec(trigger_job_final_dir, logger):
            abs_vgrid_dir = '%s/' \
                % os.path.abspath(os.path.join(configuration.vgrid_files_home,
                                  vgrid_name))
            for filename in os.listdir(trigger_job_pending_dir):
                trigger_job_filepath = \
                    os.path.join(trigger_job_pending_dir, filename)
                trigger_job = unpickle(trigger_job_filepath, logger)
                serverjob_filepath = \
                    os.path.join(configuration.mrsl_files_dir,
                                 os.path.join(client_id_dir(trigger_job['owner'
                                 ]), '%s.mRSL' % trigger_job['jobid']))
                serverjob = unpickle(serverjob_filepath, logger)
                if serverjob:
                    if serverjob['STATUS'] in pending_states:
                        trigger_event = trigger_job['event']
                        trigger_rule = trigger_job['rule']
                        trigger_action = trigger_event['event_type']
                        trigger_time = time.ctime(trigger_event['time_stamp'
                                ])
                        trigger_path = '%s %s' % (trigger_event['src_path'
                                ].replace(abs_vgrid_dir, ''),
                                trigger_event['dest_path'
                                ].replace(abs_vgrid_dir, ''))
                        job = {'object_type': 'trigger_job', 'job_id':
                               trigger_job['jobid'], 'rule_id':
                               trigger_rule['rule_id'], 'path': trigger_path,
                               'action': trigger_action, 'time': trigger_time,
                               'status': serverjob['STATUS']}
                        if not job['rule_id'].startswith(img_trigger_prefix) \
                               or verbose(flags):
                            trigger_jobs.append(job)
                    elif serverjob['STATUS'] in final_states:
                        src_path = os.path.join(trigger_job_pending_dir,
                                filename)
                        dest_path = os.path.join(trigger_job_final_dir,
                                filename)
                        move_file(src_path, dest_path, configuration)
                    else:
                        logger.error('Trigger job: %s, unknown state: %s'
                                     % (trigger_job['jobid'],
                                     serverjob['STATUS']))

        log_content = read_trigger_log(configuration, vgrid_name, flags)

    if operation in show_operations:

        # Always run as rule creator to avoid users being able to act on behalf
        # of ANY other user using triggers (=exploit)

        extra_fields = [
            ('path', None),
            ('match_dirs', ['False', 'True']),
            ('match_recursive', ['False', 'True']),
            ('changes', [keyword_all] + valid_trigger_changes),
            ('action', [keyword_auto] + valid_trigger_actions),
            ('arguments', None),
            ('run_as', client_id),
            ]

        # NOTE: we do NOT show saved template contents - see addvgridtriggers

        optional_fields = [('rate_limit', None), ('settle_time', None)]

        # Only include system triggers in verbose mode
        if verbose(flags):
            system_filter = []
        else:
            system_filter = [('rule_id', '%s_.*' % img_trigger_prefix)]
        (init_status, oobjs) = vgrid_add_remove_table(
            client_id,
            vgrid_name,
            'trigger',
            'vgridtrigger',
            configuration,
            extra_fields + optional_fields,
            filter_items=system_filter
            )
        if not init_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'failed to load triggers: %s' % oobjs})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # Generate variable helper values for a few concrete samples for help text 
        vars_html = ''
        dummy_rule = {'run_as': client_id, 'vgrid_name': vgrid_name}
        samples = [('input.txt', 'modified'), ('input/image42.raw', 'changed')]
        for (path, change) in samples:
            vgrid_path = os.path.join(vgrid_name, path)
            vars_html += "<b>Expanded variables when %s is %s:</b><br/>" % \
                            (vgrid_path, change)
            expanded = get_expand_map(vgrid_path, dummy_rule, change)
            for (key, val) in expanded.items():
                vars_html += "    %s: %s<br/>" % (key, val)
        commands_html = ''
        commands = get_command_map(configuration)
        for (cmd, cmd_args) in commands.items():
            commands_html += "    %s %s<br/>" % (cmd, (' '.join(cmd_args)).upper())

        helper_html = """
<div class='variables-accordion'>
<h4>Help on available trigger variable names and values</h4>
<p>
Triggers can use a number of helper variables on the form +TRIGGERXYZ+ to
dynamically act on targets. Some of the values are bound to the rule owner the
%s while the remaining ones are automatically expanded for the particular
trigger target as shown in the following examples:<br/>
%s
</p>
<h4>Help on available trigger commands and arguments</h4>
<p>
It is possible to set up trigger rules that basically run any operation with a
side effect you could manually do on %s. I.e. like submitting/cancelling
a job, creating/moving/deleting a file or directory and so on. When you select
'command' as the action for a trigger rule, you have the following commands at
your disposal:<br/>
%s
</p>
</div>
""" % (label, vars_html, configuration.short_title, commands_html)

        # Make page with manage triggers tab and active jobs and log tab

        output_objects.append({'object_type': 'html_form', 'text':  '''
    <div id="wrap-tabs" class="workflow-tabs">
<ul>
<li><a href="#manage-tab">Manage Triggers</a></li>
<li><a href="#jobs-tab">Active Trigger Jobs</a></li>
</ul>
'''})

        # Display existing triggers and form to add new ones

        output_objects.append({'object_type': 'html_form', 'text':  '''
<div id="manage-tab">
'''})
    
        output_objects.append({'object_type': 'sectionheader',
                              'text': 'Manage Triggers'})
        output_objects.extend(oobjs)
        output_objects.append({'object_type': 'html_form', 'text': helper_html})

        if configuration.site_enable_crontab:
            output_objects.append({'object_type': 'html_form', 'text':  '''
<p>You can combine these workflows with the personal '''})
            output_objects.append({'object_type': 'link',
                                   'destination': 'crontab.py',
                                   'class': 'crontablink iconspace',
                                   'text': 'schedule task'})
            output_objects.append({'object_type': 'html_form', 'text':  '''
facilities in case you want to trigger flows at given times rather than only
in reaction to file system events.</p>
'''})
        output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})

        # Display active trigger jobs and recent logs for this vgrid

        output_objects.append({'object_type': 'html_form', 'text':  '''
    <div id="jobs-tab">
    '''})
        output_objects.append({'object_type': 'sectionheader',
                              'text': 'Active Trigger Jobs'})
        output_objects.append({'object_type': 'table_pager', 'entry_name': 'job',
                               'default_entries': default_pager_entries})

    output_objects.append({'object_type': 'trigger_job_list', 'trigger_jobs':
                           trigger_jobs})

    if operation in show_operations:
        output_objects.append({'object_type': 'sectionheader',
                               'text': 'Trigger Log'})

    output_objects.append({'object_type': 'trigger_log', 'log_content':
                           log_content})
    if operation in show_operations:
        output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})
    
        output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})
    return (output_objects, returnvalues.OK)


