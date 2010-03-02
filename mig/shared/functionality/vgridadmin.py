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
        initialize_main_variables(op_header=False)
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
                 % vgrid_name, 'text': 'Private'}

            vgrid_obj['memberlink'] = {'object_type': 'link',
             'destination':'',
             'text': "<img src='/images/icons/information.png' title='Every user is member of the %s VGrid.'/>" % default_vgrid }

            member_list['vgrids'].append(vgrid_obj)
            continue

        # links for everyone: public pages and membership request

        vgrid_obj['publicwikilink'] = {'object_type': 'link',
                'destination': '%s/vgridpublicwiki/%s'\
                 % (configuration.migserver_http_url, vgrid_name),
                'text': 'Public Wiki'}
        vgrid_obj['enterpubliclink'] = {'object_type': 'link',
                'destination': '%s/vgrid/%s/'\
                 % (configuration.migserver_http_url, vgrid_name),
                'text': 'View page'}

        # link to become member. overwritten later for members

        vgrid_obj['memberlink'] = {'object_type': 'link',
             'destination':
              'vgridmemberrequestaction.py?vgrid_name=%s&request_type=member&request_text=no+text'\
              % vgrid_name,
             'text': "<img src='/images/icons/add.png' title='Become a member'/>"}
        # link to become owner. overwritten later for owners

        vgrid_obj['administratelink'] = {'object_type': 'link',
             'destination':
              'vgridmemberrequestaction.py?vgrid_name=%s&request_type=owner&request_text=no+text'\
              % vgrid_name,
             'text': "<img src='/images/icons/cog_add.png' title='Become an owner'/>"}

        # members/owners are allowed to view private pages and monitor

        if vgrid_is_owner_or_member(vgrid_name, client_id, configuration):
            vgrid_obj['enterprivatelink'] = {'object_type': 'link',
                'destination': '../vgrid/%s/' % vgrid_name,
                'text': 'Enter'}
            vgrid_obj['privatewikilink'] = {'object_type': 'link',
                'destination': '/vgridwiki/%s' % vgrid_name,
                'text': 'Private Wiki'}
            vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                'destination': 'showvgridmonitor.py?vgrid_name=%s'\
                 % vgrid_name, 'text': 'Private'}

            # to leave this VGrid (remove ourselves). Note that we are
            # going to overwrite the link later for owners.

            vgrid_obj['memberlink'] = {'object_type': 'link',
                'destination':
                "javascript:confirmLeave('%s','%s');" % \
                  (vgrid_name, 
                   'rmvgridmember.py?vgrid_name=%s&cert_id=%s'\
                   % (vgrid_name, client_id)),
                'text': "<img src='/images/icons/cancel.png' title='Leave this VGrid'/>"}

        # owners are allowed to edit pages and administrate

        if vgrid_is_owner(vgrid_name, client_id, configuration):

            # correct the link to leave the VGrid

            vgrid_obj['memberlink']['destination'] = \
                "javascript:confirmLeave('%s','%s');" % \
                  (vgrid_name, 
                   'rmvgridowner.py?vgrid_name=%s&cert_id=%s'\
                 % (vgrid_name, client_id))

            # add more links: administrate and edit pages

            vgrid_obj['administratelink'] = {'object_type': 'link',
                    'destination': 'adminvgrid.py?vgrid_name=%s'\
                     % vgrid_name,
                    'text': "<img src='/images/icons/wrench.png' title='Administrate'/>"}
            vgrid_obj['editprivatelink'] = {'object_type': 'link',
                    'destination': 'editor.py?path=private_base/%s/index.html'\
                     % vgrid_name, 'text': 'Edit'}
            vgrid_obj['editpubliclink'] = {'object_type': 'link',
                    'destination': 'editor.py?path=public_base/%s/index.html'\
                     % vgrid_name, 'text': 'Edit'}

        member_list['vgrids'].append(vgrid_obj)


    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'VGrid administration'

    # jquery support for tablesorter and confirmation on "leave":

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery-1.3.2.min.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>

<script type="text/javascript" >

var confirmLeave = function(name, link) {
    var yes = confirm("Really leave the VGrid " + name + " ?");
    if (yes) {
         window.location=link;
    }
}

$(document).ready(function() {

          // table initially sorted by col. 2 (admin), then 1 (member), then 0
          var sortOrder = [[2,0],[1,1],[0,0]];

          // use an image title for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("img").attr("title");
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
                          : 'showvgridmonitor.py?vgrid_name=ALL'})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'VGrid request'})
    output_objects.append({'object_type': 'link', 'text'
                          : 'Request ownership or membership of an existing VGrid'
                          , 'destination': 'vgridmemberrequest.py'})

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
