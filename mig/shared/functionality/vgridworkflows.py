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

import shared.returnvalues as returnvalues
from shared.defaults import keyword_all, keyword_auto, valid_trigger_changes, \
     valid_trigger_actions, workflows_log_name, workflows_log_cnt
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
    for i in xrange(workflows_log_cnt-1, -1, -1):
        log_name = workflows_log_name
        if i > 0:
            log_name += '.%d' % i
        log_path = os.path.join(configuration.vgrid_home, vgrid_name, log_name)
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
        output_objects.append({'object_type': 'error_text', 'text':
                               '''You must be an owner or member of %s vgrid to
access the workflows.''' % vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s Workflows' % configuration.site_vgrid_label
    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] = '''
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
     }
);
</script>
''' % default_pager_entries

    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="72" rows="10" id="confirm_input" style="display:none;"></textarea>
 </div>
'''                       })
                          
    output_objects.append({'object_type': 'header', 'text'
                          : '%s Workflows for %s' % \
                           (configuration.site_vgrid_label, vgrid_name)})

    logger.info("vgridworkflows %s" % vgrid_name)

    # TODO: consider showing triggered job list?
    #job_list = []
    #output_objects.append({'object_type': 'sectionheader', 'text'
    #                      : 'Trigger Jobs'})
    #output_objects.append({'object_type': 'html_form', 'text'
    #                      : 'Job table here!'})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Trigger Log'})
    log_content = read_trigger_log(configuration, vgrid_name)
    output_objects.append({'object_type': 'html_form', 'text'
                          : '''
 <div class="form_container">
 <textarea id="logarea" rows=10 readonly="readonly">%s</textarea>
 </div>
 ''' % log_content})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Manage Triggers'})

    # Always run as rule creator to avoid users being able to act on behalf
    # of ANY other user using triggers (=exploit)
    extra_fields = [('path', None),
                    ('match_dirs', ['False', 'True']),                    
                    ('match_recursive', ['False', 'True']),                    
                    ('changes', [keyword_all] + valid_trigger_changes),
                    ('action', [keyword_auto] + valid_trigger_actions),
                    ('arguments', None),
                    ('run_as', client_id),
                    ]
    
    # NOTE: we do NOT show saved template contents - see addvgridtriggers
    
    optional_fields = [('rate_limit', None), ('settle_time', None), ]

    (status, oobjs) = vgrid_add_remove_table(client_id, vgrid_name, 'trigger',
                                             'vgridtrigger', configuration,
                                             extra_fields, optional_fields)
    output_objects.extend(oobjs)
    if not status:
        return (output_objects, returnvalues.SYSTEM_ERROR)
    
    return (output_objects, returnvalues.OK)
