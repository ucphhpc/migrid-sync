#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# redb - [insert a few words of module description on this line]
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

"""Show all available runtime environments"""

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert
from shared.functionality.showre import build_reitem_object
from shared.init import initialize_main_variables, find_entry
from shared.refunctions import list_runtime_environments, get_re_dict


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['runtimeenvironments', defaults]


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

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Runtime Environments'

    # jquery support for tablesorter and confirmation on "leave":

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>

<script type="text/javascript" >

var runConfirmDialog = function(text, link, textFieldName) {

    if (link == undefined) {
        link = "#";
    }
    if (text == undefined) {
        text = "Are you sure?";
    }
    $( "#confirm_text").html(text);

    var addField = function() { /* doing nothing... */ };
    if (textFieldName != undefined) {
        $("#confirm_input").show();
        addField = function() {
            link += textFieldName + "=" + $("#confirm_input")[0].value;
        }
    }

    $( "#confirm_dialog").dialog("option", "buttons", {
              "No": function() { $("#confirm_input").hide();
                                 $("#confirm_text").html("");
                                 $("#confirm_dialog").dialog("close");
                               },
              "Yes": function() { addField();
                                  window.location = link;
                                }
            });
    $( "#confirm_dialog").dialog("open");
}

$(document).ready(function() {

          // init confirmation dialog
          $( "#confirm_dialog" ).dialog(
              // see http://jqueryui.com/docs/dialog/ for options
              { autoOpen: false,
                modal: true, closeOnEscape: true,
                width: 500,
                buttons: {
                   "Cancel": function() { $( "#" + name ).dialog("close"); }
	        }
              });

          // table initially sorted by col. 1 (admin), then 0 (name)
          var sortOrder = [[2,1],[0,0]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }

          $("#runtimeenvtable").tablesorter({widgets: ["zebra"],
                                        sortList:sortOrder,
                                        textExtraction: imgTitle
                                       });
     }
);
</script>
'''

    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="40" rows="4" id="confirm_input" style="display:none;"/></textarea>
 </div>
'''                       })

    output_objects.append({'object_type': 'header', 'text'
                          : 'Runtime Environments'})

    output_objects.append(
        {'object_type': 'text', 'text' :
         'Runtime environments specify software/data available on resources.'
         })
    output_objects.append(
        {'object_type': 'link',
         'destination': 'docs.py?show=Runtime+Environments',
         'class': 'infolink',
         'title': 'Show information about runtime environment',
         'text': 'Documentation on runtime environments'})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Existing runtime environments'})

    (status, ret) = list_runtime_environments(configuration)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : ret})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    runtimeenvironments = []
    for single_re in ret:
        (re_dict, msg) = get_re_dict(single_re, configuration)
        if not re_dict:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : msg})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        re_item = build_reitem_object(re_dict)
        re_name = re_item['name']
        
        re_item['viewruntimeenvlink'] = {'object_type': 'link',
                                         'destination': "showre.py?re_name=%s" % re_name,
                                         'class': 'infolink',
                                         'title': 'View %s runtime environment' % re_name, 
                                         'text': ''}
        if client_id == re_item['creator']:
            re_item['ownerlink'] = {'object_type': 'link',
                                    'destination':
                                    "javascript:runConfirmDialog('%s','%s');" % \
                                    ("Really delete " + re_name + "?", 
                                     'deletere.py?re_name=%s' % re_name),
                                    'class': 'removelink',
                                    'title': 'Delete %s runtime environment' % re_name, 
                                    'text': ''}
        runtimeenvironments.append(re_item)

    output_objects.append({'object_type': 'runtimeenvironments',
                          'runtimeenvironments': runtimeenvironments})

    if configuration.site_swrepo_url:
        output_objects.append({'object_type': 'sectionheader', 'text': 'Software Packages'})
        output_objects.append({'object_type': 'link',
                               'destination': configuration.site_swrepo_url,
                               'class': 'swrepolink',
                               'title': 'Browse available software packages',
                               'text': 'Open software catalogue for %s' % \
                               configuration.short_title,
                               })

    output_objects.append({'object_type': 'sectionheader', 'text': 'Additional Runtime Environments'})
    output_objects.append({'object_type': 'link',
                           'destination': 'adminre.py',
                           'class': 'addlink',
                           'title': 'Specify a new runtime environment', 
                           'text': 'Create a new runtime environment'})

    return (output_objects, returnvalues.OK)


