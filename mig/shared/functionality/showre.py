#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showre - Display a runtime environment
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Get info about a runtime environtment"""

import time
import base64

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables, find_entry
from shared.refunctions import is_runtime_environment, get_re_dict
from shared.validstring import valid_dir_input


def signature():
    """Signature of the main function"""

    defaults = {'re_name': REJECT_UNSET}
    return ['runtimeenvironment', defaults]


def build_reitem_object(re_dict):
    """Build a runtimeenvironment object based on input re_dict"""

    software_list = []
    soft = re_dict['SOFTWARE']
    if len(soft) > 0:
        for software_item in soft:
            if software_item['url'].find('://') < 0:
                software_item['url'] = 'http://%(url)s' % software_item
            software_list.append({
                'object_type': 'software',
                'name': software_item['name'],
                'icon': software_item['icon'],
                'url': software_item['url'],
                'description': software_item['description'],
                'version': software_item['version'],
                })

    # anything specified?

    testprocedure = ''
    if len(re_dict['TESTPROCEDURE']) > 0:
        base64string = ''
        for stringpart in re_dict['TESTPROCEDURE']:
            base64string += stringpart
        testprocedure = base64.decodestring(base64string)

    verifystdout = ''
    if len(re_dict['VERIFYSTDOUT']) > 0:
        for string in re_dict['VERIFYSTDOUT']:
            verifystdout += string

    verifystderr = ''
    if len(re_dict['VERIFYSTDERR']) > 0:
        for string in re_dict['VERIFYSTDERR']:
            verifystderr += string

    verifystatus = ''
    if len(re_dict['VERIFYSTATUS']) > 0:
        for string in re_dict['VERIFYSTATUS']:
            verifystatus += string

    environments = []
    env = re_dict['ENVIRONMENTVARIABLE']
    if len(env) > 0:
        for environment_item in env:
            environments.append({
                'object_type': 'environment',
                'name': environment_item['name'],
                'example': environment_item['example'],
                'description': environment_item['description'],
                })

    return {
        'object_type': 'runtimeenvironment',
        'name': re_dict['RENAME'],
        'description': re_dict['DESCRIPTION'],
        'creator': re_dict['CREATOR'],
        'created': time.asctime(re_dict['CREATED_TIMESTAMP'
                                ].timetuple()),
        'job_count': '(not implemented yet)',
        'resource_count': '(not implemented yet)',
        'testprocedure': testprocedure,
        'verifystdout': verifystdout,
        'verifystderr': verifystderr,
        'verifystatus': verifystatus,
        'environments': environments,
        'software': software_list,
        }


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
    re_name = accepted['re_name'][-1]

    if not valid_dir_input(configuration.re_home, re_name):
        logger.warning(
            "possible illegal directory traversal attempt re_name '%s'"
            % re_name)
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Illegal runtime environment name: "%s"'
                               % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not is_runtime_environment(re_name, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                               : "'%s' is not an existing runtime environment!"
                               % re_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Runtime environment details'
    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-1.7.2.custom.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery-1.3.2.min.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui-1.7.2.custom.min.js"></script>

<script type="text/javascript" >
var runConfirmDialog = function(text, link, textFieldName) {

    if (link == undefined) {
        link = "#";
    }
    if (text == undefined) {
        text = "Are you sure?";
    }
    $("#confirm_text").html(text);

    var addField = function() { /* doing nothing... */ };
    if (textFieldName != undefined) {
        $("#confirm_input").show();
        addField = function() {
            link += textFieldName + "=" + $("#confirm_input")[0].value;
        }
    }

    $("#confirm_dialog").dialog("option", "buttons", {
              "No": function() { $("#confirm_input").hide();
                                 $("#confirm_text").html("");
                                 $("#confirm_dialog").dialog("close");
                               },
              "Yes": function() { addField();
                                  window.location = link;
                                }
            });
    $("#confirm_dialog").dialog("open");
}

$(document).ready(function() {

          // init confirmation dialog
          $("#confirm_dialog").dialog(
              // see http://jqueryui.com/docs/dialog/ for options
              { autoOpen: false,
                modal: true, closeOnEscape: true,
                width: 500,
                buttons: {
                   "Cancel": function() { $("#" + name).dialog("close"); }
	        }
              });
     }
);
</script>
'''
    output_objects.append({'object_type': 'header', 'text'
                          : 'Show runtime environment details'})
    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="40" rows="4" id="confirm_input" style="display:none;"/></textarea>
 </div>
'''
                           })

    (re_dict, msg) = get_re_dict(re_name, configuration)
    if not re_dict:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Could not read details for "%s"' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append(build_reitem_object(re_dict))

    if client_id ==  re_dict['CREATOR']:
        
        output_objects.append({'object_type': 'link',
                               'destination':
                               "javascript:runConfirmDialog('%s','%s');" % \
                               ("Really delete runtime environment %s?"
                                % re_name, 
                                'deletere.py?re_name=%s'\
                                % (re_name)),
                               'class': 'removelink',
                               'title': 'Delete runtime environment %s'
                               % re_name,
                               'text': 'Delete %s' % re_name})
    
    return (output_objects, returnvalues.OK) 
