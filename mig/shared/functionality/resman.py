#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resman - [insert a few words of module description on this line]
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

"""Resource management back end functionality"""

import shared.returnvalues as returnvalues
from shared.findtype import is_owner
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
from shared.vgridaccess import user_allowed_resources


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['resources', defaults]


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

    allowed = user_allowed_resources(configuration, client_id)
    # Iterate through resources and print details for each

    res_list = {'object_type': 'resource_list', 'resources': []}
    sorted_names = allowed.keys()
    sorted_names.sort()
    for unique_resource_name in sorted_names:
        
        res_obj = {'object_type': 'resource', 'name': unique_resource_name}

        if is_owner(client_id, unique_resource_name,
                    configuration.resource_home, logger):

            # Allow admin of resource

            res_obj['resadminlink'] = \
                                    {'object_type': 'link',
                                     'destination':
                                     'resadmin.py?unique_resource_name=%s'\
                                     % unique_resource_name,
                                     'text': "<img src='/images/icons/wrench.png' title='Administrate'>"}

        # TODO: add more fields
        # fields for everyone: public status

        res_obj['nodes'] = len(allowed[unique_resource_name])
        res_obj['status'] = 'unknown'
        res_list['resources'].append(res_obj)


    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource management'

    # jquery support for tablesorter and confirmation on "leave":

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery-1.3.2.min.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>

<script type="text/javascript" >

var confirmDelete = function(name, link) {
    var yes = confirm("Really delete the resource " + name + " ?");
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

          $("#resourcetable").tablesorter({widgets: ["zebra"],
                                        sortList:sortOrder,
                                        textExtraction: imgTitle
                                       });
     }
);
</script>
'''

    output_objects.append({'object_type': 'header', 'text': 'Resources'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : '''
Resources can execute jobs for you and you can manage any resources that you own.
'''
                       })

    output_objects.append({'object_type': 'link', 'text'
                          : 'Create a new %s resource' % \
                            configuration.short_title, 
                           'destination' : 'resedit.py'})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Resources available on this server'})
    output_objects.append(res_list)

    # print "DEBUG: %s" % output_objects

    return (output_objects, status)
