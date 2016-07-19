#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminvgrid - administrate a vgrid
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

import os
from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.defaults import default_pager_entries, keyword_all, keyword_auto, \
     valid_trigger_changes, valid_trigger_actions, keyword_owners, \
     keyword_members
from shared.accessrequests import list_access_requests, load_access_request, \
     build_accessrequestitem_object
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.html import jquery_ui_js, man_base_js, man_base_html, \
     html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.sharelinks import build_sharelinkitem_object
from shared.vgrid import vgrid_list, vgrid_is_owner, vgrid_settings, \
     vgrid_sharelinks, vgrid_list_parents

_valid_sharelink = [("owners", keyword_owners), ("members", keyword_members)]
_valid_visible = _valid_sharelink + [("everyone", keyword_all)]
_valid_bool = [("yes", True), ("no", False)]

def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['html_form', defaults]


def vgrid_add_remove_table(client_id,
                           vgrid_name, 
                           item_string, 
                           script_suffix, 
                           configuration,
                           extra_fields=[],
                           optional_fields=[]):
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
        optional = True
    elif item_string == 'trigger':
        id_field = 'rule_id'
        optional = True
    else:
        id_field = 'cert_id'

    id_note = ""
    if item_string in ['owner', 'member']:
        openid_add = ""
        if configuration.user_openid_providers:
            openid_add = "either the OpenID alias or "    
        id_note = """
      <tr>
      <td colspan='2'>
Note: %ss are specified with %s the Distinguished Name (DN) of the user. If in
doubt, just let the user request access and accept it with the
<span class='addlink'></span>-icon in the Pending Requests table below.
      </td>
      </tr>
""" % (item_string, openid_add)

    # read list of current items and create form to remove one

    (list_status, inherit) = vgrid_list(vgrid_name, '%ss' % item_string,
                                   configuration, recursive=True,
                                   allow_missing=optional)
    if not list_status:
        out.append({'object_type': 'error_text', 'text': inherit})
        return (False, out)
    (list_status, direct) = vgrid_list(vgrid_name, '%ss' % item_string,
                                  configuration, recursive=False,
                                  allow_missing=optional)
    if not list_status:
        out.append({'object_type': 'error_text', 'text': direct})
        return (False, out)

    extra_titles_html = ''
    for (field, _) in extra_fields + optional_fields:
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
                for (field, _) in extra_fields + optional_fields:
                    val = elem.get(field, '')
                    if isinstance(val, bool):
                        val = str(val)
                    elif not isinstance(val, basestring):
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

    # TODO: add remove vgrid button if only inherited owners
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
                for (field, _) in extra_fields + optional_fields:
                    val = elem.get(field, '')
                    if isinstance(val, bool):
                        val = str(val)
                    elif not isinstance(val, basestring):
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
    for (field, limit) in extra_fields + optional_fields:
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
      <legend>Add %(_label)s %(item)s</legend>
      <input type="hidden" name="vgrid_name" value="%(vgrid)s" />
      %(id_note)s<br />
      <div id="dyn%(item)sspares">
          <!-- placeholder for dynamic add %(item)s fields -->
      </div>
      %(extra_fields)s<br />
      <input type="submit" value="Add %(item)s" />
      </fieldset>
      </form>
''' % {'vgrid': vgrid_name, 'item': item_string, 'id_note': id_note,
       'script': script_suffix, 'id_field': id_field,
       'extra_fields': extra_fields_html,
       '_label': configuration.site_vgrid_label}
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

    # prepare for confirm dialog, tablesort and toggling the views (css/js)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = "Administrate %s: %s" % \
                          (configuration.site_vgrid_label, vgrid_name)

    # jquery support for tablesorter and confirmation on request and leave
    # requests table initially sorted by 0, 4, 3 (type first, then date and
    # with alphabetical client ID last)
    # sharelinks table initially sorted by 5, 4 reversed (active first and
    # in growing age)
    
    table_specs = [{'table_id': 'accessrequeststable', 'pager_id':
                    'accessrequests_pager', 'sort_order':
                    '[[0,0],[4,0],[3,0]]'},
                   {'table_id': 'sharelinkstable', 'pager_id':
                    'sharelinks_pager', 'sort_order': '[[5,1],[4,1]]'}]
    (add_import, add_init, add_ready) = man_base_js(configuration, 
                                                    table_specs,
                                                    {'width': 600})
    add_init += '''
        var toggleHidden = function(classname) {
            // classname supposed to have a leading dot 
            $(classname).toggleClass("hidden");
        };
        /* helpers for dynamic form input fields */
        function onOwnerInputChange() {
            makeSpareFields("#dynownerspares", "cert_id");
        }
        function onMemberInputChange() {
            makeSpareFields("#dynmemberspares", "cert_id");
        }
        function onResourceInputChange() {
            makeSpareFields("#dynresourcespares", "unique_resource_name");
        }
    '''
    add_ready += '''
    /* init add owners/member/resource forms with dynamic input fields */
    onOwnerInputChange();
    $("#dynownerspares").on("blur", "input[name=cert_id]",
        function(event) {
            //console.debug("in add owner blur handler");
            onOwnerInputChange();
        }
    );
    onMemberInputChange();
    $("#dynmemberspares").on("blur", "input[name=cert_id]",
        function(event) {
            //console.debug("in add member blur handler");
            onMemberInputChange();
        }
    );
    onResourceInputChange();
    $("#dynresourcespares").on("blur", "input[name=unique_resource_name]",
        function(event) {
            console.debug("in resource blur handler");
            onResourceInputChange();
        }
    );
    '''
    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                             add_init, add_ready)
    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})
    
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
             'class': 'addadminlink iconspace',
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

        (init_status, oobjs) = vgrid_add_remove_table(client_id, vgrid_name, item, 
                                                 scr, configuration,
                                                 extra_fields)
        if not init_status:
            output_objects.extend(oobjs)
            return (output_objects, returnvalues.SYSTEM_ERROR)
        else:
            output_objects.append({'object_type': 'html_form', 
                                   'text': '<div class="div-%s">' % item })
            output_objects.append(
                {'object_type': 'link', 
                 'destination': 
                 "javascript:toggleHidden('.div-%s');" % item,
                 'class': 'removeitemlink iconspace',
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
                 'class': 'additemlink iconspace',
                 'title': 'Toggle view',
                 'text': 'Show %ss' % item.title() })
            output_objects.append({'object_type': 'html_form', 
                                   'text': '</div>' })

    # Pending requests

    helper = html_post_helper("acceptvgridownerreq", "addvgridowner.py",
                              {'vgrid_name': vgrid_name,
                               'cert_id': '__DYNAMIC__',
                               'request_name': '__DYNAMIC__'
                               })
    output_objects.append({'object_type': 'html_form', 'text': helper})
    helper = html_post_helper("acceptvgridmemberreq", "addvgridmember.py",
                              {'vgrid_name': vgrid_name,
                               'cert_id': '__DYNAMIC__',
                               'request_name': '__DYNAMIC__'
                               })
    output_objects.append({'object_type': 'html_form', 'text': helper})
    helper = html_post_helper("acceptvgridresourcereq", "addvgridres.py",
                              {'vgrid_name': vgrid_name,
                               'unique_resource_name': '__DYNAMIC__',
                               'request_name': '__DYNAMIC__'
                               })
    output_objects.append({'object_type': 'html_form', 'text': helper})
    helper = html_post_helper("rejectvgridreq", "rejectvgridreq.py",
                              {'vgrid_name': vgrid_name,
                               'request_name': '__DYNAMIC__'
                               })
    output_objects.append({'object_type': 'html_form', 'text': helper})

    request_dir = os.path.join(configuration.vgrid_home, vgrid_name)
    request_list = []
    for req_name in list_access_requests(configuration, request_dir):
        req = load_access_request(configuration, request_dir, req_name)
        if not req:
            continue
        if not req.get('request_type', None) in ["vgridowner", "vgridmember",
                                                 "vgridresource"]:
            logger.error("unexpected request_type %(request_type)s" % req)
            continue
        request_item = build_accessrequestitem_object(configuration, req)
        # Convert filename with exotic chars into url-friendly pure hex version
        shared_args = {"request_name": hexlify(req["request_name"])}
        accept_args, reject_args = {}, {}
        accept_args.update(shared_args)
        reject_args.update(shared_args)
        if req['request_type'] == "vgridresource":
            accept_args["unique_resource_name"] = req["entity"]
        else:
            accept_args["cert_id"] = req["entity"]

        request_item['acceptrequestlink'] = {
            'object_type': 'link',
            'destination':
             "javascript: confirmDialog(%s, '%s', %s, %s);" % \
            ("accept%(request_type)sreq" % req,
             "Accept %(target)s %(request_type)s request from %(entity)s" % req,
             'undefined', "{%s}" % ', '.join(["'%s': '%s'" % pair for pair in accept_args.items()])),
            'class': 'addlink iconspace', 'title':
            'Accept %(target)s %(request_type)s request from %(entity)s' % req,
            'text': ''}
        request_item['rejectrequestlink'] = {
            'object_type': 'link',
            'destination':
             "javascript: confirmDialog(%s, '%s', %s, %s);" % \
            ("rejectvgridreq",
             "Reject %(target)s %(request_type)s request from %(entity)s" % req,
             'undefined', "%s" % reject_args),
            'class': 'removelink iconspace', 'title':
            'Reject %(target)s %(request_type)s request from %(entity)s' % req,
            'text': ''}

        request_list.append(request_item)

    output_objects.append({'object_type': 'sectionheader',
                           'text': "Pending Requests"})
    output_objects.append({'object_type': 'table_pager', 'id_prefix':
                           'accessrequests_', 'entry_name': 'access requests',
                           'default_entries': default_pager_entries})
    output_objects.append({'object_type': 'accessrequests',
                           'accessrequests': request_list})
    
    # VGrid Share links

    # Table columns to skip
    skip_list = ['editsharelink', 'delsharelink', 'invites', 'expire',
                 'single_file']
    
    # NOTE: Inheritance is a bit tricky for sharelinks because parent shares
    # only have relevance if they actually share a path that is a prefix of
    # vgrid_name.
    
    (share_status, share_list) = vgrid_sharelinks(vgrid_name, configuration)
    sharelinks = []
    if share_status:
        for share_dict in share_list:
            rel_path = share_dict['path'].strip(os.sep)
            parent_vgrids = vgrid_list_parents(vgrid_name, configuration)
            include_share = False
            # Direct sharelinks (careful not to greedy match A/B with A/BCD)
            if rel_path == vgrid_name or \
                   rel_path.startswith(vgrid_name+os.sep):
                include_share = True
            # Parent vgrid sharelinks that in effect also give access here
            for parent in parent_vgrids:
                if rel_path == parent: 
                    include_share = True
            if include_share:
                share_item = build_sharelinkitem_object(configuration, share_dict)
                sharelinks.append(share_item)

    output_objects.append({'object_type': 'sectionheader',
                           'text': "Share Links"})
    output_objects.append({'object_type': 'html_form', 
                 'text': '<p>Current share links in %s shared folder</p>' % \
                           vgrid_name})
    output_objects.append({'object_type': 'table_pager', 'id_prefix':
                           'sharelinks_', 'entry_name': 'share links',
                           'default_entries': default_pager_entries})
    output_objects.append({'object_type': 'sharelinks',
                           'sharelinks': sharelinks,
                           'skip_list': skip_list})

    # VGrid settings
    
    output_objects.append({'object_type': 'sectionheader',
                           'text': "Settings"})

    (settings_status, settings_dict) = vgrid_settings(vgrid_name, configuration,
                                                 as_dict=True)
    if not settings_status or not settings_dict:
        settings_dict = {'vgrid_name': vgrid_name}
    settings_dict.update({
        'vgrid_label': configuration.site_vgrid_label,
        'owners': keyword_owners,
        'members': keyword_members,
        'all': keyword_all,
        })

    settings_form = '''
    <form method="post" action="vgridsettings.py">
        <fieldset>
            <legend>%(vgrid_label)s configuration</legend>
                <input type="hidden" name="vgrid_name" value="%(vgrid_name)s" />
'''
    description = settings_dict.get('description', '')
    settings_form += '''
            <h4>Public description</h4>
                <textarea class="fillwidth padspace" name="description" rows=10
                    >%s</textarea>
''' % description
    settings_form += '<br/>'

    settings_form += '''<p>All visibility options below can be set to owners,
members or everyone and by default only owners can see participation. In effect
setting visibility to <em>members</em> means that owners and members can see
the corresponding participants. Similarly setting a visibility flag to
<em>everyone</em> means that all %s users can see the participants.</p>
''' % configuration.short_title
    visibility_options = [("Owners are visible to", "visible_owners"),
                          ("Members are visible to", "visible_members"),
                          ("Resources are visible to", "visible_resources")]
    for (title, field) in visibility_options:
        settings_form += '<h4>%s</h4>' % title
        for (key, val) in _valid_visible: 
            checked = ''
            if settings_dict.get(field, keyword_owners) == val:
                checked = "checked"
            settings_form += '''
            <input type="radio" name="%s" value="%s" %s/> %s
''' % (field, val, checked, key)
        settings_form += '<br/>'
    sharelink_options = [("Limit sharelink creation to", "create_sharelink")]
    for (title, field) in sharelink_options:
        settings_form += '<h4>%s</h4>' % title
        for (key, val) in _valid_sharelink: 
            checked = ''
            if settings_dict.get(field, keyword_owners) == val:
                checked = "checked"
            settings_form += '''
            <input type="radio" name="%s" value="%s" %s/> %s
''' % (field, val, checked, key)
        settings_form += '<br/>'

    request_recipients = settings_dict.get('request_recipients', 42)
    settings_form += '''
            <h4>Request Recipients</h4> 
            Notify only first
            <input type="number" name="request_recipients" min=1 max=100 value=%d />
            owners about access requests.
''' % request_recipients
    settings_form += '<br/>'

    # TODO: implement and enable read-only support.
    #       Maybe just recursively remove write bit on share?
    #       Careful with .vgridX dirs when reverting to writable if so.
    bool_options = [("Hidden", "hidden"),
                    #("Read Only", "read_only"),
                    ]
    for (title, field) in bool_options:
        settings_form += '<h4>%s</h4>' % title
        for (key, val) in _valid_bool: 
            checked = ''
            if settings_dict.get(field, False) == val:
                checked = "checked"
            settings_form += '''
            <input type="radio" name="%s" value="%s" %s/> %s
''' % (field, val, checked, key)
        settings_form += '<br/>'
    settings_form += '<br/>'

    settings_form += '''
            <input type="submit" value="Save settings" />
        </fieldset>
    </form>
'''
    output_objects.append({'object_type': 'html_form',
                           'text': settings_form % settings_dict})

    # Checking/fixing of missing components

    output_objects.append({'object_type': 'sectionheader',
                           'text': "Repair/Add Components"})
    output_objects.append({'object_type': 'html_form',
                           'text': '''
      <form method="post" action="updatevgrid.py">
          <input type="hidden" name="vgrid_name" value="%(vgrid_name)s" />
          <input type="submit" value="Repair components" />
      </form>
''' % settings_dict})

    output_objects.append({'object_type': 'sectionheader',
                           'text': "Delete %s " % vgrid_name})
    output_objects.append({'object_type': 'html_form',
                           'text': '''
To delete <b>%(vgrid)s</b> remove all members and owners ending with yourself.
''' % {'vgrid': vgrid_name}})

    return (output_objects, returnvalues.OK)
