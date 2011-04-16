#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resman - manage resources
# Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter
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

"""Resource management back end functionality"""

from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.base import sandbox_resource
from shared.defaults import default_pager_entries
from shared.functional import validate_input_and_cert
from shared.html import html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.resource import anon_to_real_res_map
from shared.vgridaccess import user_visible_res_exes, get_resource_map, \
     OWNERS, CONF


def signature():
    """Signature of the main function"""

    defaults = {'show_sandboxes': ['false']}
    return ['resources', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    status = returnvalues.OK
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

    show_sandboxes = (accepted['show_sandboxes'][-1] != 'false')

    visible_exes = user_visible_res_exes(configuration, client_id)
    res_map = get_resource_map(configuration)
    anon_map = anon_to_real_res_map(configuration.resource_home)

    # Iterate through resources and show management for each one requested

    res_list = {'object_type': 'resource_list', 'resources': []}
    fields = ['PUBLICNAME', 'NODECOUNT', 'CPUCOUNT', 'MEMORY', 'DISK', 'ARCHITECTURE',
              'SANDBOX', 'RUNTIMEENVIRONMENT']
    # Leave the sorting to jquery tablesorter
    for visible_res_name in visible_exes.keys():
        unique_resource_name = visible_res_name
        if visible_res_name in anon_map.keys():
            unique_resource_name = anon_map[visible_res_name]

        if not show_sandboxes and sandbox_resource(unique_resource_name):
            continue
        res_obj = {'object_type': 'resource', 'name': visible_res_name}

        if client_id in res_map[unique_resource_name][OWNERS]:

            # Admin of resource when owner

            js_name = 'rmresowner%s' % hexlify(unique_resource_name)
            helper = html_post_helper(js_name, 'rmresowner.py',
                                      {'unique_resource_name':
                                       unique_resource_name,
                                       'cert_id': client_id})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            res_obj['resownerlink'] = \
                                    {'object_type': 'link',
                                     'destination':
                                     "javascript: confirmDialog(%s, '%s');"\
                                     % (js_name, 'Really leave %s owners?' % \
                                        unique_resource_name),
                                     'class': 'removelink',
                                     'title': 'Leave %s owners' % unique_resource_name, 
                                     'text': ''}
            res_obj['resdetailslink'] = \
                                    {'object_type': 'link',
                                     'destination':
                                     'resadmin.py?unique_resource_name=%s'\
                                     % unique_resource_name,
                                     'class': 'adminlink',
                                     'title': 'Administrate %s' % unique_resource_name, 
                                     'text': ''}
        else:

            # link to become owner

            js_name = 'reqresowner%s' % hexlify(unique_resource_name)
            helper = html_post_helper(js_name, 'sendrequestaction.py',
                                      {'unique_resource_name':
                                       visible_res_name,
                                       'request_type': 'resourceowner',
                                       'request_text': ''})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            res_obj['resownerlink'] = \
                                    {'object_type': 'link',
                                     'destination':
                                     "javascript: confirmDialog(%s, '%s', '%s');"\
                                     % (js_name, "Request ownership of " + \
                                        visible_res_name + ":<br/>" + \
                                        "\nPlease write a message to the owners (field below).",
                                        'request_text'),
                                     'class': 'addlink',
                                     'title': 'Request ownership of %s' % visible_res_name,
                                     'text': ''}
            
            res_obj['resdetailslink'] = \
                                    {'object_type': 'link',
                                     'destination':
                                     'viewres.py?unique_resource_name=%s'\
                                     % visible_res_name,
                                     'class': 'infolink',
                                     'title': 'View detailed %s specs' % \
                                     visible_res_name, 
                                     'text': ''}
            
        # fields for everyone: public status
        for name in fields:
            res_obj[name] = res_map[unique_resource_name][CONF].get(name, '')
        # Use runtimeenvironment names instead of actual definitions
        res_obj['RUNTIMEENVIRONMENT'] = [i[0] for i in res_obj['RUNTIMEENVIRONMENT']]
        res_list['resources'].append(res_obj)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource management'

    # jquery support for tablesorter and confirmation on "leave":

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>

<script type="text/javascript" >

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
          var sortOrder = [[1,0],[0,0]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }
          
          $("#resourcetable").tablesorter({widgets: ["zebra"],
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
   <textarea cols="40" rows="4" id="confirm_input" style="display:none;"/></textarea>
 </div>
'''                       })

    output_objects.append({'object_type': 'header', 'text': 'Available Resources'
                          })

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Resources available on this server'})
    output_objects.append({'object_type': 'text', 'text'
                          : '''
All available resources are listed below with overall hardware specifications. Any resources that you own will have a administration icon that you can click to open resource management.
'''
                       })

    output_objects.append({'object_type': 'table_pager', 'entry_name': 'resources',
                           'default_entries': default_pager_entries})
    output_objects.append(res_list)

    if configuration.site_enable_sandboxes:
        if show_sandboxes:
            output_objects.append({'object_type': 'link',
                                   'destination': '?show_sandboxes=false',
                                   'class': 'removeitemlink',
                                   'title': 'Hide sandbox resources', 
                                   'text': 'Exclude sandbox resources',
                                   })

        else:
            output_objects.append({'object_type': 'link',
                                   'destination': '?show_sandboxes=true',
                                   'class': 'additemlink',
                                   'title': 'Show sandbox resources', 
                                   'text': 'Include sandbox resources',
                                   })

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Resource Status'})
    output_objects.append({'object_type': 'text',
                           'text': '''
Live resource status is available in the resource monitor page with all VGrids/resources you can access
'''})
    output_objects.append({'object_type': 'link',
                           'destination': 'showvgridmonitor.py?vgrid_name=ALL',
                           'class': 'monitorlink',
                           'title': 'Show monitor with all resources you can access', 
                           'text': 'Global resource monitor',
                           })

    output_objects.append({'object_type': 'sectionheader', 'text': 'Additional Resources'
                          })
    output_objects.append({'object_type': 'text',
                           'text': 'You can sign up spare or dedicated resources to the grid below.'
                           })
    output_objects.append({'object_type': 'link',
                           'destination' : 'resedit.py',
                           'class': 'addlink',
                           'title': 'Show sandbox resources',                            
                           'text': 'Create a new %s resource' % \
                           configuration.short_title, 
                           })
    output_objects.append({'object_type': 'sectionheader', 'text': ''})

    if configuration.site_enable_sandboxes:
        output_objects.append({'object_type': 'link',
                               'destination': 'ssslogin.py',
                               'class': 'adminlink',
                               'title': 'Administrate and monitor your sandbox resources',
                               'text': 'Administrate %s sandbox resources' % \
                               configuration.short_title,
                               })
        output_objects.append({'object_type': 'sectionheader', 'text': ''})
        output_objects.append({'object_type': 'link',
                               'destination': 'oneclick.py',
                               'class': 'sandboxlink',
                               'title': 'Run a One-click resource in your browser', 
                               'text': 'Use this computer as One-click %s resource' % \
                               configuration.short_title,
                               })

    return (output_objects, status)
