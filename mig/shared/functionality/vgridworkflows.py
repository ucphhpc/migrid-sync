#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# vgridforum - Access VGrid private forum for owners and members
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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
import time

from shared.base import client_id_dir
import shared.returnvalues as returnvalues
from shared.defaults import keyword_all, keyword_auto, \
    valid_trigger_changes, valid_trigger_actions, workflows_log_name, \
    workflows_log_cnt, pending_states, final_states
from shared.events import get_expand_map, get_command_map
from shared.fileio import unpickle, makedirs_rec, move_file
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.functionality.adminvgrid import vgrid_add_remove_table
from shared.html import themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.vgrid import vgrid_is_owner_or_member, vgrid_triggers, \
    vgrid_set_triggers

default_pager_entries = 20


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['html_form', defaults]


def read_trigger_log(configuration, vgrid_name):
    """Read in saved trigger logs for vgrid workflows page. We read in all
    rotated logs.
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
            configuration.logger.debug('read\n%s' % log_content)
            log_fd.close()
        except IOError:
            pass
    return log_content


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
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

    vgrid_name = accepted['vgrid_name'][-1]

    if not vgrid_is_owner_or_member(vgrid_name, client_id,
                                    configuration):
        output_objects.append({'object_type': 'error_text',
                              'text': '''You must be an owner or member of %s vgrid to
access the workflows.'''
                               % vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s Workflows' \
        % configuration.site_vgrid_label
    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] = \
        '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>

<script type="text/javascript">
$(document).ready(function() {

          $("#logarea").scrollTop($("#logarea")[0].scrollHeight);

          // table initially sorted by 0 (last update / date) 
          var sortOrder = [[0,1]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }

          $("#workflowstable").tablesorter({widgets: ["zebra", "saveSort"],
                                        sortList:sortOrder,
                                        textExtraction: imgTitle
                                        })
                               .tablesorterPager({ container: $("#pager"),
                                        size: %s
                                        });

        /* Init variables helper as foldable but closed and with individual heights */
        $(".variables-accordion").accordion({
                                       collapsible: true,
                                       active: false,
                                       heightStyle: "content"
                                      });
        /* fix and reduce accordion spacing */
        $(".ui-accordion-header").css("padding-top", 0).css("padding-bottom", 0).css("margin", 0);
     }
);
</script>
''' \
        % default_pager_entries

    output_objects.append({'object_type': 'html_form',
                          'text': '''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="72" rows="10" id="confirm_input" style="display:none;"></textarea>
 </div>
'''})

    output_objects.append({'object_type': 'header',
                          'text': '%s Workflows for %s'
                          % (configuration.site_vgrid_label,
                          vgrid_name)})

    logger.info('vgridworkflows %s' % vgrid_name)

    # Display active trigger jobs for this vgrid

    output_objects.append({'object_type': 'sectionheader',
                          'text': 'Active Trigger Jobs'})
    html = '<table><thead><tr>'
    html += '<th>Job ID</th>'
    html += '<th>Rule</th>'
    html += '<th>Path</th>'
    html += '<th>Change</th>'
    html += '<th>Time</th>'
    html += '<th>Status</th>'
    html += '</tr></thead>'
    html += '<tbody>'

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
                    html += \
                        '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></td><td>%s</td>' \
                        % (trigger_job['jobid'], trigger_rule['rule_id'
                           ], trigger_path, trigger_action, trigger_time,
                           serverjob['STATUS'])
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
    html += '</tbody>'
    html += '</table>'
    output_objects.append({'object_type': 'html_form', 'text': html})

    # Display active trigger jobs for this vgrid

    output_objects.append({'object_type': 'sectionheader',
                          'text': 'Trigger Log'})
    log_content = read_trigger_log(configuration, vgrid_name)
    output_objects.append({'object_type': 'html_form',
                          'text': '''
 <div class="form_container">
 <textarea id="logarea" rows=10 readonly="readonly">%s</textarea>
 </div>
 '''
                          % log_content})

    output_objects.append({'object_type': 'sectionheader',
                          'text': 'Manage Triggers'})

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

    (status, oobjs) = vgrid_add_remove_table(
        client_id,
        vgrid_name,
        'trigger',
        'vgridtrigger',
        configuration,
        extra_fields,
        optional_fields,
        )
    output_objects.extend(oobjs)

    if not status:
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Generate variable helper values for a few concrete samples for help text 
    vars_html = ''
    dummy_rule = {'run_as': client_id, 'vgrid_name': vgrid_name}
    samples = [('input.txt', 'modified'), ('input/image42.raw', 'changed')]
    for (path, change) in samples:
        vars_html += "<b>Expanded variables when %s is %s:</b><br/>" % \
                        (path, change)
        expanded = get_expand_map(path, dummy_rule, change)
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
side effect you could manually do on the grid. I.e. like submitting/cancelling
a job, creating/moving/deleting a file or directory and so on. When you select
'command' as the action for a trigger rule, you have the following commands at
your disposal:<br/>
%s
</p>
""" % (configuration.site_vgrid_label, vars_html, commands_html)
    output_objects.append({'object_type': 'html_form', 'text': helper_html})

    return (output_objects, returnvalues.OK)


