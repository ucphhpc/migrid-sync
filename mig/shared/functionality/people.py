#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# people - view and communicate with other users
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""View and communicate with other users that allow it"""

from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.defaults import default_pager_entries
from shared.functional import validate_input_and_cert
from shared.functionality.showuser import build_useritem_object
from shared.html import html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.user import anon_to_real_user_map, get_user_dict


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['users', defaults]


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
    title_entry['text'] = 'People'

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

          // table initially sorted by col. 1 (view), then 0 (name)
          var sortOrder = [[2,1],[0,0]];

          // use image path for sorting if there is any inside
          var imgTitle = function(contents) {
              var key = $(contents).find("a").attr("class");
              if (key == null) {
                  key = $(contents).html();
              }
              return key;
          }

          $("#usertable").tablesorter({widgets: ["zebra"],
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

    output_objects.append({'object_type': 'header', 'text'
                          : 'People'})

    output_objects.append(
        {'object_type': 'text', 'text' :
         'View and communicate with other users.'
         })

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'All users'})

    user_map = anon_to_real_user_map(configuration.user_home)
    if not user_map:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'no users found!'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    users = []
    for (anon_user, real_user) in user_map.items():
        user_dict) = get_user_dict(real_user, configuration)
        if not user_dict:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'failed to load user settings for %s' % \
                                   anon_user})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        user_item = build_useritem_object(configuration, user_dict)
        user_id = anon_user
        
        user_item['viewuserlink'] = {'object_type': 'link',
                                         'destination': "showuser.py?user_id=%s" % user_id,
                                         'class': 'infolink',
                                         'title': 'View %s user' % user_id, 
                                         'text': ''}
        if user_item['email']:
            js_name = 'sendemail%s' % hexlify(user_id)
            helper = html_post_helper(js_name, 'accessrequestaction.py',
                                      {'user_id': user_id})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            re_item['sendemaillink'] = {'object_type': 'link',
                                    'destination':
                                    "javascript: confirmDialog(%s, '%s');"\
                                    % (js_name, 'Really send email to %s?' % \
                                       user_id),
                                    'class': 'sendemaillink',
                                    'title': 'Send email to %s' % user_id, 
                                    'text': ''}
        users.append(user_item)

    output_objects.append({'object_type': 'table_pager', 'entry_name': 'people',
                           'default_entries': default_pager_entries})
    output_objects.append({'object_type': 'users',
                          'users': users})

    return (output_objects, returnvalues.OK)


