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

"""List owners, members, resources and triggers for vgrid and show html
controls to administrate them.
"""

from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.defaults import keyword_all, keyword_auto, valid_trigger_changes, \
     valid_trigger_actions
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.html import html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.vgrid import vgrid_list, vgrid_is_owner


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['html_form', defaults]


def vgrid_add_remove_table(client_id,
                           vgrid_name, 
                           item_string, 
                           script_suffix, 
                           configuration,
                           extra_fields=[]):
    """Create a table of owners/members/resources/triggers (item_string),
    allowing to remove one item by selecting (radio button) and calling a
    script, and a form to add a new entry.
    Used from separate workflows page, too.
    
    Arguments: vgrid_name, the vgrid to operate on
               item_string, one of owner, member, resource, trigger
               script_suffix, will be prepended with "add" and "rm" for forms
               configuration, for loading the list of current items 
               
    Returns: (Bool, list of output_objects)
    """

    out = []

    if not item_string in ['owner', 'member', 'resource', 'trigger']:
        out.append({'object_type': 'error_text', 'text': 
                    'Internal error: Unknown item type %s.' % item_string
                    })
        return (False, out)

    optional = False
    
    if item_string == 'resource':
        id_field = 'unique_resource_name'
    elif item_string == 'trigger':
        id_field = 'rule_id'
        optional = True
    else:
        id_field = 'cert_id'

    # read list of current items and create form to remove one

    (status, inherit) = vgrid_list(vgrid_name, '%ss' % item_string,
                                   configuration, recursive=True,
                                   allow_missing=optional)
    if not status:
        out.append({'object_type': 'error_text',
                    'text': inherit })
        return (False, out)
    (status, direct) = vgrid_list(vgrid_name, '%ss' % item_string,
                                  configuration, recursive=False,
                                  allow_missing=optional)
    if not status:
        out.append({'object_type': 'error_text',
                    'text': direct })
        return (False, out)

    extra_titles_html = ''
    for (field, _) in extra_fields:
        extra_titles_html += '<th>%s</th>' % field.replace('_', ' ').title()

    # success, so direct and inherit are lists of unique user/res/trigger IDs
    extras = [i for i in inherit if not i in direct]
    if extras:
        table = '''
        <br />
        Inherited %(item)ss of %(vgrid)s:
        <table class="vgrid%(item)s">
          <thead><tr><th></th><th>%(item)s</th>%(extra_titles)s</thead>
          <tbody>
''' % {'item': item_string,
       'vgrid': vgrid_name,
       'extra_titles': extra_titles_html}

        for elem in extras:
            extra_fields_html = ''
            if isinstance(elem, dict) and elem.has_key(id_field):
                for (field, _) in extra_fields:
                    val = elem[field]
                    if not isinstance(val, basestring):
                        val = ' '.join(val)
                    extra_fields_html += '<td>%s</td>' % val
                table += \
"""          <tr><td></td><td>%s</td>%s</tr>""" % (elem[id_field],
                                                   extra_fields_html)
            elif elem:
                table += \
"          <tr><td></td><td>%s</td></tr>"\
                     % elem
        table += '''
        </tbody></table>
'''
        out.append({'object_type': 'html_form', 'text': table})
    if direct:
        form = '''
      <form method="post" action="rm%(scriptname)s.py">
        <input type="hidden" name="vgrid_name" value="%(vgrid)s" />
        Current %(item)ss of %(vgrid)s:
        <table class="vgrid%(item)s">
          <thead><tr><th>Remove</th><th>%(item)s</th>%(extra_titles)s</thead>
          <tbody>
''' % {'item': item_string,
       'scriptname': script_suffix,
       'vgrid': vgrid_name,
       'extra_titles': extra_titles_html}

        for elem in direct:
            extra_fields_html = ''
            if isinstance(elem, dict) and elem.has_key(id_field):
                for (field, _) in extra_fields:
                    val = elem[field]
                    if not isinstance(val, basestring):
                        val = ' '.join(val)
                    extra_fields_html += '<td>%s</td>' % val
                form += \
"""          <tr><td><input type=radio name='%s' value='%s' /></td>
                 <td>%s</td>%s</tr>""" % (id_field, elem[id_field],
                 elem[id_field], extra_fields_html)
            elif elem:
                form += \
"""          <tr><td><input type=radio name='%s' value='%s' /></td>
                 <td>%s</td></tr>""" % (id_field, elem, elem)
        form += '''
        </tbody></table>
        <input type="submit" value="Remove %s" />
      </form>
''' % item_string
                    
        out.append({'object_type': 'html_form', 'text': form})

    # form to add a new item

    extra_fields_html = ''
    for (field, limit) in extra_fields:
        extra_fields_html += '<tr><td>%s</td><td>' % \
                             field.replace('_', ' ').title()
        if isinstance(limit, basestring):
            add_html = '%s' % limit
        elif limit == None:
            add_html = '<input type="text" size=70 name="%s" />' % field
        else:
            multiple = ''
            if keyword_all in limit:
                multiple = 'multiple'
            add_html = '<select %s name="%s">' % (multiple, field)
            for val in limit:
                add_html += '<option value="%s">%s</option>' % (val, val)
            add_html += '</select>'
        extra_fields_html += add_html + '</td></tr>'
    out.append({'object_type': 'html_form',
                'text': '''
      <form method="post" action="add%(script)s.py">
      <fieldset>
      <legend>Add vgrid %(item)s</legend>
      <input type="hidden" name="vgrid_name" value="%(vgrid)s" />
      <table>
      <tr>
      <td>ID</td><td><input type="text" size=70 name="%(id_field)s" /></td>
      </tr>
      %(extra_fields)s
      <tr>
      <td colspan="2"><input type="submit" value="Add %(item)s" /></td>
      </tr>
      </table>
      </fieldset>
      </form>
''' % {'vgrid': vgrid_name, 'item': item_string, 
       'script': script_suffix, 'id_field': id_field,
       'extra_fields': extra_fields_html }
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

    title_entry['style'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.custom.css" media="screen"/>
'''
    title_entry['javascript'] = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>

<script type="text/javascript" >

    var toggleHidden = function(classname) {
        // classname supposed to have a leading dot 
        $(classname).toggleClass('hidden');
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
   <textarea cols="40" rows="4" id="confirm_input" style="display:none;"></textarea>
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
        output_objects.append(
            {'object_type': 'link',
             'destination':
             "javascript: confirmDialog(%s, '%s', '%s');"\
             % (js_name, "Request ownership of " + \
                vgrid_name + ":<br/>" + \
                "\nPlease write a message to the owners below.",
                'request_text'),
             'class': 'addadminlink',
             'title': 'Request ownership of %s' % vgrid_name,
             'text': 'Apply to become an owner'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    for (item, scr) in zip(['owner', 'member', 'resource'],
                        ['vgridowner', 'vgridmember', 'vgridres']):
        output_objects.append({'object_type': 'sectionheader',
                               'text': "%ss" % item.title()
                               })
        if item == 'trigger':
            # Always run as rule creator to avoid users being able to act on
            # behalf of ANY other user using triggers (=exploit)
            extra_fields = [('path', None),
                            ('changes', [keyword_all] + valid_trigger_changes),
                            ('run_as', client_id),
                            ('action', [keyword_auto] + valid_trigger_actions),
                            ('arguments', None)]
        else:
            extra_fields = []

        (status, oobjs) = vgrid_add_remove_table(client_id, vgrid_name, item, 
                                                 scr, configuration,
                                                 extra_fields)
        if not status:
            output_objects.extend(oobjs)
            return (output_objects, returnvalues.SYSTEM_ERROR)
        else:
            output_objects.append({'object_type': 'html_form', 
                                   'text': '<div class="div-%s">' % item })
            output_objects.append(
                {'object_type': 'link', 
                 'destination': 
                 "javascript:toggleHidden('.div-%s');" % item,
                 'class': 'removeitemlink',
                 'title': 'Toggle view',
                 'text': 'Hide %ss' % item.title() })
            output_objects.extend(oobjs)
            output_objects.append(
                {'object_type': 'html_form', 
                 'text': '</div><div class="hidden div-%s">' % item})
            output_objects.append(
                {'object_type': 'link', 
                 'destination': 
                 "javascript:toggleHidden('.div-%s');" % item,
                 'class': 'additemlink',
                 'title': 'Toggle view',
                 'text': 'Show %ss' % item.title() })
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
