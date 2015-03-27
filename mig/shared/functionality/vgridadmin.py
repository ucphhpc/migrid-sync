#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridadmin - manage vgrids
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

"""VGrid administration back end functionality"""

from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.defaults import default_vgrid, all_vgrids, default_pager_entries
from shared.functional import validate_input_and_cert
from shared.html import html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.useradm import get_full_user_map
from shared.vgrid import vgrid_list_vgrids, vgrid_is_owner, \
    vgrid_is_member, vgrid_is_owner_or_member, vgrid_create_allowed


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

    (stat, vgrid_list) = vgrid_list_vgrids(configuration)
    if not stat:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of %s.' % \
                               configuration.site_vgrid_label})

    # Iterate through vgrids and print details for each

    member_list = {'object_type': 'vgrid_list', 'vgrids': []}
    if 'monitor' in configuration.site_vgrid_links:
        vgrid_list = [all_vgrids] + vgrid_list
    else:
        vgrid_list.remove(default_vgrid)
    for vgrid_name in vgrid_list:
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
                                       'title': 'Every user is member of the %s %s' \
                                       % (default_vgrid,
                                          configuration.site_vgrid_label),
                                       'text': ''}
            vgrid_obj['administratelink'] = {'object_type': 'link',
                                       'destination':'',
                                       'class': 'infolink',
                                       'title': 'Nobody owns the %s %s' \
                                       % (default_vgrid,
                                          configuration.site_vgrid_label),
                                       'text': ''}
            member_list['vgrids'].append(vgrid_obj)
            continue
        elif vgrid_name == all_vgrids:

            # Only show global monitor link for all_vgrids, Noone
            # can own it or leave it. Do not add any page links.

            vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                                               'destination': 'showvgridmonitor.py?vgrid_name=%s'\
                                               % vgrid_name,
                                               'class': 'monitorlink',
                                               'title': 'View global monitor', 
                                               'text': 'View'}
            vgrid_obj['memberlink'] = {'object_type': 'link',
                                       'destination':'',
                                       'class': 'infolink',
                                       'title': 'Not a real %s - only for global monitor' % \
                                       configuration.site_vgrid_label,
                                       'text': ''}
            vgrid_obj['administratelink'] = {'object_type': 'link',
                                       'destination':'',
                                       'class': 'infolink',
                                       'title': 'Not a real %s - only for global monitor' % \
                                             configuration.site_vgrid_label,
                                       'text': ''}
            member_list['vgrids'].append(vgrid_obj)
            continue

        # links for everyone: public pages and membership request

        vgrid_obj['publicscmlink'] = {'object_type': 'link',
                'destination': '%s/vgridpublicscm/%s'\
                                       % (configuration.migserver_http_url,
                                          vgrid_name),
                                       'class': 'scmlink public',
                                       'title': 'Open %s public SCM' % \
                                       vgrid_name,
                                       'text': 'Open'}
        vgrid_obj['publictrackerlink'] = {'object_type': 'link',
                'destination': '%s/vgridpublictracker/%s'\
                                       % (configuration.migserver_http_url,
                                          vgrid_name),
                                       'class': 'trackerlink public',
                                       'title': 'Open %s public tracker' % \
                                       vgrid_name,
                                       'text': 'Open'}
        vgrid_obj['enterpubliclink'] = {'object_type': 'link',
                                        'destination':
                                        '%s/vgrid/%s/path/index.html' % \
                                        (configuration.migserver_http_url,
                                         vgrid_name),
                                        'class': 'urllink member',
                                        'title': 'View public %s web page' % \
                                        vgrid_name,
                                        'text': 'View'}

        # link to become member: overwritten later for members

        js_name = 'reqvgridmember%s' % hexlify(vgrid_name)
        helper = html_post_helper(js_name, 'sendrequestaction.py',
                                  {'vgrid_name': vgrid_name,
                                   'request_type': 'vgridmember',
                                   'request_text': ''})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        vgrid_obj['memberlink'] = \
                                {'object_type': 'link',
                                 'destination':
                                 "javascript: confirmDialog(%s, '%s', '%s');"\
                                 % (js_name, "Request membership of " + \
                                    vgrid_name + ":<br/>" + \
                                    "\nPlease write a message to the owners (field below).",
                                    'request_text'),
                                 'class': 'addlink',
                                 'title': 'Request membership of %s' % \
                                 vgrid_name,
                                 'text': ''}

        # link to become owner: overwritten later for owners

        js_name = 'reqvgridowner%s' % hexlify(vgrid_name)
        helper = html_post_helper(js_name, 'sendrequestaction.py',
                                  {'vgrid_name': vgrid_name,
                                   'request_type': 'vgridowner',
                                   'request_text': ''})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        vgrid_obj['administratelink'] = \
                                      {'object_type': 'link',
                                       'destination':
                                       "javascript: confirmDialog(%s, '%s', '%s');"\
                                       % (js_name, "Request ownership of " + \
                                          vgrid_name + ":<br/>" + \
                                          "\nPlease write a message to the owners (field below).",
                                          'request_text'),
                                       'class': 'addadminlink',
                                       'title': 'Request ownership of %s' % \
                                       vgrid_name,
                                       'text': ''}

        # members/owners are allowed to view private pages and monitor

        if vgrid_is_owner_or_member(vgrid_name, client_id, configuration):
            vgrid_obj['enterprivatelink'] = {'object_type': 'link',
                                             'destination':
                                             '../vgrid/%s/path/index.html' % \
                                             vgrid_name,
                                             'class': 'urllink owner',
                                             'title':
                                             'View private %s web page' % \
                                             vgrid_name, 
                                             'text': 'View'}
            vgrid_obj['sharedfolderlink'] = {'object_type': 'link',
                                             'destination':
                                             'fileman.py?path=%s/' % vgrid_name,
                                             'class': 'sharedfolderlink',
                                             'title': 'Open shared %s folder' \
                                             % vgrid_name, 
                                             'text': 'Open'}
            vgrid_obj['memberscmlink'] = {'object_type': 'link',
                                          'destination': '/vgridscm/%s' % \
                                          vgrid_name,
                                          'class': 'scmlink member',
                                          'title': 'View %s members scm' % \
                                          vgrid_name,
                                          'text': 'View'}
            vgrid_obj['membertrackerlink'] = {'object_type': 'link',
                                          'destination': '/vgridtracker/%s' % \
                                          vgrid_name,
                                          'class': 'trackerlink member',
                                          'title': 'View %s members tracker' % \
                                          vgrid_name,
                                          'text': 'View'}
            vgrid_obj['privateforumlink'] = {'object_type': 'link',
                                             'destination':
                                             'vgridforum.py?vgrid_name=%s' % \
                                             vgrid_name,
                                             'class': 'forumlink',
                                             'title': 'Open %s private forum' \
                                             % vgrid_name, 
                                               'text': 'Open'}
            vgrid_obj['privateworkflowslink'] = {'object_type': 'link',
                                             'destination':
                                             'vgridworkflows.py?vgrid_name=%s' % \
                                             vgrid_name,
                                             'class': 'workflowslink',
                                             'title': 'Open %s private workflows' \
                                             % vgrid_name, 
                                               'text': 'Open'}
            vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                                               'destination':
                                               'showvgridmonitor.py?vgrid_name=%s'\
                                               % vgrid_name,
                                               'class': 'monitorlink',
                                               'title': 'View %s monitor' % \
                                               vgrid_name, 
                                               'text': 'View'}

            # to leave this VGrid (remove ourselves). Note that we are
            # going to overwrite the link later for owners.

            js_name = 'rmvgridmember%s' % hexlify(vgrid_name)
            helper = html_post_helper(js_name, 'rmvgridmember.py',
                                      {'vgrid_name': vgrid_name,
                                       'cert_id': client_id})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            vgrid_obj['memberlink'] = \
                                    {'object_type': 'link',
                                     'destination':
                                     "javascript: confirmDialog(%s, '%s');"\
                                     % (js_name, "Really leave " + vgrid_name + "?"),
                                     'class': 'removelink',
                                     'title': 'Leave %s members' % vgrid_name, 
                                     'text': ''}
            
        # owners are allowed to edit pages and administrate

        if vgrid_is_owner(vgrid_name, client_id, configuration):
            vgrid_obj['ownerscmlink'] = {'object_type': 'link',
                                         'destination': '/vgridownerscm/%s' % \
                                         vgrid_name,
                                         'class': 'scmlink owner',
                                         'title': 'View %s owners scm' % \
                                         vgrid_name,
                                         'text': 'View'}
            vgrid_obj['ownertrackerlink'] = {'object_type': 'link',
                                         'destination': '/vgridownertracker/%s' % \
                                         vgrid_name,
                                         'class': 'trackerlink owner',
                                         'title': 'View %s owners tracker' % \
                                         vgrid_name,
                                         'text': 'View'}

            # correct the link to leave the VGrid

            js_name = 'rmvgridowner%s' % hexlify(vgrid_name)
            helper = html_post_helper(js_name, 'rmvgridowner.py',
                                      {'vgrid_name': vgrid_name,
                                       'cert_id': client_id})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            vgrid_obj['memberlink']['destination'] = \
                      "javascript: confirmDialog(%s,'%s');" % \
                      (js_name, "Really leave " + vgrid_name + "?")
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
                                            'destination': 'fileman.py?path=private_base/%s/'\
                                            % vgrid_name,
                                            'class': 'editlink owner',
                                            'title': 'Edit private %s web page' % vgrid_name,
                                            'text': 'Edit'}
            vgrid_obj['editpubliclink'] = {'object_type': 'link',
                                           'destination': 'fileman.py?path=public_base/%s/'\
                                           % vgrid_name,
                                           'class': 'editlink member',
                                           'title': 'Edit public %s web page' % vgrid_name,
                                           'text': 'Edit'}


        member_list['vgrids'].append(vgrid_obj)

    title_entry = find_entry(output_objects, 'title')
    label = "%ss" % configuration.site_vgrid_label
    # Append VGrid note if custom
    if label != 'VGrid':
        label += ' (i.e. VGrids)'
    title_entry['text'] = '%s administration' % label

    # jquery support for tablesorter and confirmation on "leave":

    title_entry['style'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.custom.css" media="screen"/>
'''
    title_entry['javascript'] = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
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

          // table initially sorted by col. 1 (admin), then 2 (member), then 0 (name)
          var sortOrder = [[1,1],[2,1],[0,0]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }

          $("#vgridtable").tablesorter({widgets: ["zebra", "saveSort"],
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
   <textarea cols="40" rows="4" id="confirm_input" style="display:none;"></textarea>
 </div>
'''                       })

    output_objects.append({'object_type': 'header', 'text': label})
    output_objects.append({'object_type': 'text', 'text'
                          : '''
%ss share files, a number of collaboration tools and resources. Members can access web pages, files, tools and resources. Owners can additionally edit pages, as well as add and remove members or resources.
''' % configuration.site_vgrid_label
                       })

    if configuration.site_vgrid_label != 'VGrid':
        output_objects.append({'object_type': 'text', 'text'
                          : """Please note that for historical reasons %ss are
also referred to as VGrids in some contexts.""" % \
                               configuration.site_vgrid_label})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : '%ss managed on this server' % \
                           configuration.site_vgrid_label})
    output_objects.append({'object_type': 'table_pager', 'entry_name': '%ss' % \
                           configuration.site_vgrid_label,
                           'default_entries': default_pager_entries})
    output_objects.append(member_list)

    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    # Optional limitation of create vgrid permission
    if user_dict and vgrid_create_allowed(configuration, user_dict):
        output_objects.append({'object_type': 'sectionheader', 'text'
                               : 'Additional %ss' % \
                               configuration.site_vgrid_label})

        output_objects.append(
            {'object_type': 'text', 'text':
             '''Please enter a name for the new %(label)s to add, using slashes to
 specify nesting. I.e. if you own a %(label)s called ABC, you can create a
 sub-%(label)s called DEF by entering ABC/DEF below.''' % \
             {'label': configuration.site_vgrid_label}})
        output_objects.append({'object_type': 'html_form', 'text':
                                '''<form method="post" action="createvgrid.py">
    <input type="text" size=40 name="vgrid_name" />
    <input type="hidden" name="output_format" value="html" />
    <input type="submit" value="Create %s" />
    </form>
 ''' % configuration.site_vgrid_label})

    return (output_objects, status)
