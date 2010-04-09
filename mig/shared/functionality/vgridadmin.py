#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridadmin - [insert a few words of module description on this line]
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

"""VGrid administration back end functionality"""

import shared.returnvalues as returnvalues
from shared.defaults import default_vgrid
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
from shared.vgrid import vgrid_list_vgrids, vgrid_is_owner, \
    vgrid_is_member, vgrid_is_owner_or_member


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['vgrids', defaults]


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

    (stat, list) = vgrid_list_vgrids(configuration)
    if not stat:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of vgrids.'})

    # Iterate through vgrids and print details for each

    member_list = {'object_type': 'vgrid_list', 'vgrids': []}
    for vgrid_name in list:
        
        vgrid_obj = {'object_type': 'vgrid', 'name': vgrid_name}

        if vgrid_name == default_vgrid:

            # Everybody is member and allowed to see statistics, Noone
            # can own it or leave it. Do not add any page links.

            vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                                               'destination': 'showvgridmonitor.py?vgrid_name=%s'\
                                               % vgrid_name,
                                               'class': 'monitorlink',
                                               'title': 'View %s monitor' % vgrid_name, 
                                               'text': 'View'}

            vgrid_obj['memberlink'] = {'object_type': 'link',
                                       'destination':'',
                                       'class': 'infolink',
                                       'title': 'Every user is member of the %s VGrid' \
                                       % default_vgrid,
                                       'text': ''}
            vgrid_obj['administratelink'] = {'object_type': 'link',
                                       'destination':'',
                                       'class': 'infolink',
                                       'title': 'Nobody owns the %s VGrid' \
                                       % default_vgrid,
                                       'text': ''}

            member_list['vgrids'].append(vgrid_obj)
            continue

        # links for everyone: public pages and membership request

        vgrid_obj['publicwikilink'] = {'object_type': 'link',
                'destination': '%s/vgridpublicwiki/%s'\
                                       % (configuration.migserver_http_url, vgrid_name),
                                       'class': 'wikilink',
                                       'title': 'Open %s public wiki' % vgrid_name,
                                       'text': 'Open'}
        vgrid_obj['enterpubliclink'] = {'object_type': 'link',
                                        'destination': '%s/vgrid/%s/'\
                                        % (configuration.migserver_http_url, vgrid_name),
                                        'class': 'urllink',
                                        'title': 'View public %s web page' % vgrid_name,
                                        'text': 'View'}

        # link to become member. overwritten later for members

        vgrid_obj['memberlink'] = {'object_type': 'link',
          'destination':
          "javascript:runConfirmDialog('%s','%s','%s');" % \
            ("Request membership of " + vgrid_name + """:<br/>
Please write a message to the owners (field below).""",
             'vgridmemberrequestaction.py?vgrid_name=%s&request_type=member&'\
             % vgrid_name,
             "request_text"),
          'class': 'addlink',
          'title': 'Request membership of %s' % vgrid_name,
          'text': ''}
        # link to become owner. overwritten later for owners

        vgrid_obj['administratelink'] = {'object_type': 'link',
          'destination':
          "javascript:runConfirmDialog('%s','%s','%s');" % \
            ("Request ownership of " + vgrid_name + """:<br/>
Please write a message to the owners (field below).""",
             'vgridmemberrequestaction.py?vgrid_name=%s&request_type=owner&'\
             % vgrid_name,
             "request_text"),
                                         'class': 'addadminlink',
                                         'title': 'Request ownership of %s' % vgrid_name, 
                                         'text': ''}

        # members/owners are allowed to view private pages and monitor

        if vgrid_is_owner_or_member(vgrid_name, client_id, configuration):
            vgrid_obj['enterprivatelink'] = {'object_type': 'link',
                                             'destination': '../vgrid/%s/' % vgrid_name,
                                             'class': 'urllink',
                                             'title': 'View private %s web page' % vgrid_name, 
                                             'text': 'View'}
            vgrid_obj['memberwikilink'] = {'object_type': 'link',
                                           'destination': '/vgridwiki/%s' % vgrid_name,
                                           'class': 'wikilink',
                                           'title': 'Open %s members wiki' % vgrid_name,
                                           'text': 'Open'}
            vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                                               'destination': 'showvgridmonitor.py?vgrid_name=%s'\
                                               % vgrid_name,
                                               'class': 'monitorlink',
                                               'title': 'View %s monitor' % vgrid_name, 
                                               'text': 'View'}

            # to leave this VGrid (remove ourselves). Note that we are
            # going to overwrite the link later for owners.

            vgrid_obj['memberlink'] = {'object_type': 'link',
                                       'destination':
                                       "javascript:runConfirmDialog('%s','%s');" % \
                                       ("Really leave " + vgrid_name + "?", 
                                        'rmvgridmember.py?vgrid_name=%s&cert_id=%s'\
                                        % (vgrid_name, client_id)),
                                       'class': 'removelink',
                                       'title': 'Leave %s members' % vgrid_name, 
                                       'text': ''}
            
        # owners are allowed to edit pages and administrate

        if vgrid_is_owner(vgrid_name, client_id, configuration):
            vgrid_obj['ownerwikilink'] = {'object_type': 'link',
                                          'destination': '/vgridownerwiki/%s' % vgrid_name,
                                          'class': 'wikilink',
                                          'title': 'Open %s owners wiki' % vgrid_name,
                                          'text': 'Open'}

            # correct the link to leave the VGrid

            vgrid_obj['memberlink']['destination'] = \
                      "javascript:runConfirmDialog('%s','%s');" % \
                      ("Really leave " + vgrid_name + "?", 
                       'rmvgridowner.py?vgrid_name=%s&cert_id=%s'\
                       % (vgrid_name, client_id))
            vgrid_obj['memberlink']['class'] = 'removeadminlink'
            vgrid_obj['memberlink']['title'] = 'Leave %s owners' % vgrid_name

            # add more links: administrate and edit pages

            vgrid_obj['administratelink'] = {'object_type': 'link',
                                             'destination': 'adminvgrid.py?vgrid_name=%s'\
                                             % vgrid_name,
                                             'class': 'adminlink',
                                             'title': 'Administrate %s' % vgrid_name,
                                             'text': ''}
            vgrid_obj['editprivatelink'] = {'object_type': 'link',
                                            'destination': 'editor.py?path=private_base/%s/index.html'\
                                            % vgrid_name,
                                            'class': 'editlink',
                                            'title': 'Edit private %s web page' % vgrid_name,
                                            'text': 'Edit'}
            vgrid_obj['editpubliclink'] = {'object_type': 'link',
                                           'destination': 'editor.py?path=public_base/%s/index.html'\
                                           % vgrid_name,
                                           'class': 'editlink',
                                           'title': 'Edit public %s web page' % vgrid_name,
                                           'text': 'Edit'}

        member_list['vgrids'].append(vgrid_obj)


    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'VGrid administration'

    # jquery support for tablesorter and confirmation on "leave":

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-1.7.2.custom.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery-1.3.2.min.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui-1.7.2.custom.min.js"></script>

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

          // table initially sorted by col. 2 (admin), then 1 (member), then 0
          var sortOrder = [[2,1],[1,1],[0,0]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }

          $("#vgridtable").tablesorter({widgets: ["zebra"],
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

    output_objects.append({'object_type': 'header', 'text': 'VGrids'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : '''
VGrids share files and resources. Members can access web pages, files and resources, owners can also edit pages, as well as add and remove members or resources.
'''
                       })

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'VGrids managed on this server'})
    output_objects.append(member_list)

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'VGrid Totals'})
    output_objects.append({'object_type': 'link', 'text'
                           : 'View a monitor page with all VGrids/resources you can access'
                           , 'destination'
                           : 'showvgridmonitor.py?vgrid_name=ALL',
                           'class': 'monitorlink',
                           'title': 'View global monitor',                           
                           })

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Create a new VGrid'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : '''<form method="get" action="createvgrid.py">
    <input type="text" size=40 name="vgrid_name" />
    <input type="hidden" name="output_format" value="html" />
    <input type="submit" value="Create VGrid" />
    </form>
    <br />
    '''})

    # print "DEBUG: %s" % output_objects

    return (output_objects, status)
