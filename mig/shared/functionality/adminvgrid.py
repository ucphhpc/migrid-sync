#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminvgrid - administrate a vgrid
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""List owners, members, res's and show html controls to administrate a vgrid"""

from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.html import html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.vgrid import vgrid_list, vgrid_is_owner


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['html_form', defaults]


def vgrid_add_remove_table(vgrid_name, 
                           item_string, 
                           script_suffix, 
                           configuration):
    """Create a table of owners/members/resources (item_string), allowing to
    remove one item by selecting (radio button) and calling a script, and
    a form to add a new entry. 
    
    Arguments: vgrid_name, the vgrid to operate on
               item_string, one of owner, member, resource
               script_suffix, will be prepended with "add" and "rm" for forms
               configuration, for loading the list of current items 
               
    Returns: (Bool, list of output_objects)
    """

    out = []

    if not item_string in ['owner', 'member', 'resource']:
        out.append({'object_type': 'error_text', 'text': 
                    'Internal error: Unknown item type %s.' % item_string
                    })
        return (False, out)

    if item_string == 'resource':
        qu_string = 'unique_resource_name'
    else:
        qu_string = 'cert_id'

    # read list of current items and create form to remove one

    (status, msg) = vgrid_list(vgrid_name, '%ss' % item_string, configuration)
    if not status:
        out.append({'object_type': 'error_text',
                    'text': msg })
        return (False, out)

    # success, so msg is a list of user names (DNs) or unique resource ids
    if len(msg) <= 0:
        out.append({'object_type': 'text', 
                    'text': 'No %ss found!' % str.title(item_string)
                    })
    else:
        form = '''
      <form method="post" action="rm%(scriptname)s.py">
        <input type="hidden" name="vgrid_name" value="%(vgrid)s" />
        Current %(item)ss of %(vgrid)s:
        <table class="vgrid%(item)s">
          <thead><tr><th>Remove</th><th>%(item)s</th></thead>
          <tbody>
''' % { 'item': item_string,
        'scriptname': script_suffix,
        'vgrid': vgrid_name }

        for elem in msg:
            if elem:
                form += \
"          <tr><td><input type=radio name='%s' value='%s' /></td><td>%s</td></tr>"\
                     % (qu_string, elem, elem)
        form += '              </tbody></table>'
        form += '''
        <input type="submit" value="Remove %s" />
      </form>
''' % item_string
                    
        out.append({'object_type': 'html_form', 'text': form })

    # form to add a new item

    out.append({'object_type': 'html_form',
                'text': '''
      <form method="post" action="add%(script)s.py">
          <input type="hidden" name="vgrid_name" value="%(vgrid)s" />
          <input type="text" size=70 name="%(qu_string)s" />
          <input type="submit" value="Add vgrid %(item)s" />
      </form>
''' % {'vgrid': vgrid_name, 'item': item_string, 
       'script': script_suffix, 'qu_string': qu_string }
               })
    
    return (True, out)

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

    # prepare support for confirm dialog and toggling the views (by css/jquery)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = "Administrate VGrid: %s" % vgrid_name

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.custom.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>

<script type="text/javascript" >

    var toggleHidden = function( classname ) {
        // classname supposed to have a leading dot 
        $( classname ).toggleClass('hidden');
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
                          : "Administrate '%s'" % vgrid_name })

    if not vgrid_is_owner(vgrid_name, client_id, configuration):

        output_objects.append({'object_type': 'error_text', 'text': 
                    'Only owners of %s can administrate it.' % vgrid_name })

        js_name = 'reqvgridowner%s' % hexlify(vgrid_name)
        helper = html_post_helper(js_name, 'sendrequestaction.py',
                                  {'vgrid_name': vgrid_name,
                                   'request_type': 'vgridowner',
                                   'request_text': ''})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        output_objects.append({'object_type': 'link',
                               'destination':
                               "javascript: confirmDialog(%s, '%s', '%s');"\
                               % (js_name, "Request ownership of " + \
                                  vgrid_name + ":<br/>" + \
                                  "\nPlease write a message to the owners (field below).",
                                  'request_text'),
                               'class': 'addadminlink',
                               'title': 'Request ownership of %s' % vgrid_name,
                               'text': 'Apply to become an owner'})

        return (output_objects, returnvalues.SYSTEM_ERROR)

#    (ret, msg) = create_html(vgrid_name, configuration)

#def vgrid_add_remove_table(vgrid_name,item_string,script_suffix, configuration):

    for (item, scr) in zip(['owner','member','resource'],
                        ['vgridowner','vgridmember', 'vgridres']):
        
        # section header == title(item_string)

        output_objects.append({'object_type': 'sectionheader',
                               'text': "%ss" % str.title(item)
                               })

        (status, oobjs) = vgrid_add_remove_table(vgrid_name, item, 
                                                 scr, configuration)
        if not status:

            output_objects.extend(oobjs)
            return (output_objects, returnvalues.SYSTEM_ERROR)

        else:

            output_objects.append({'object_type': 'html_form', 
                                   'text': '<div class="div-%s">' % item })
            output_objects.append({'object_type': 'link', 
                                   'destination': 
                                   "javascript:toggleHidden('.div-%s');" % item,
                                   'class': 'removeitemlink',
                                   'title': 'Toggle view',
                                   'text': 'Hide %ss' % str.title(item) })
            output_objects.extend(oobjs)
            output_objects.append({'object_type': 'html_form', 
                                   'text': '</div><div class="hidden div-%s">' % item})
            output_objects.append({'object_type': 'link', 
                                   'destination': 
                                   "javascript:toggleHidden('.div-%s');" % item,
                                   'class': 'additemlink',
                                   'title': 'Toggle view',
                                   'text': 'Show %ss' % str.title(item) })
            output_objects.append({'object_type': 'html_form', 
                                   'text': '</div>' })

    # Checking/fixing of missing components

    output_objects.append({'object_type': 'sectionheader',
                           'text': "Repair/Add Components"})
    output_objects.append({'object_type': 'html_form',
                           'text': '''
      <form method="post" action="updatevgrid.py">
          <input type="hidden" name="vgrid_name" value="%(vgrid)s" />
          <input type="submit" value="Repair components" />
      </form>
''' % {'vgrid': vgrid_name}})

    output_objects.append({'object_type': 'sectionheader',
                           'text': "Delete %s " % vgrid_name})
    output_objects.append({'object_type': 'html_form',
                           'text': '''
      To delete <b>%(vgrid)s</b> remove all members and owners ending with yourself.
''' % {'vgrid': vgrid_name}})


    return (output_objects, returnvalues.OK)
