#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminvgrid - administrate a vgrid
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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
from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import hexlify
from mig.shared.defaults import default_pager_entries, keyword_all, keyword_auto, \
    valid_trigger_changes, valid_trigger_actions, keyword_owners, \
    keyword_members, keyword_none, csrf_field, default_vgrid_settings_limit
from mig.shared.accessrequests import list_access_requests, load_access_request, \
    build_accessrequestitem_object
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.htmlgen import man_base_js, man_base_html, html_post_helper
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.sharelinks import build_sharelinkitem_object
from mig.shared.vgrid import vgrid_add_remove_table, vgrid_list, vgrid_is_owner, \
    vgrid_settings, vgrid_sharelinks, vgrid_list_parents, vgrid_owners, \
    vgrid_members, vgrid_resources, vgrid_restrict_write_support

_user_choice = [("owners", keyword_owners), ("members", keyword_members)]
_all_choice = [("everyone", keyword_all)]
_none_choice = [("none", keyword_none)]
_bool_choice = [("yes", True), ("no", False)]
_keep_choice = [("keep using inherited or default value", keyword_auto)]
_reset_choice = [("reset to inherited or default value", keyword_auto)]
_keep_note = '(enter 0 to keep using inherited or default value)'
_reset_note = '(enter 0 to reset to inherited or default value)'
_valid_sharelink = _user_choice
_valid_write_access = _none_choice + _user_choice
_valid_visible = _user_choice + _all_choice
_valid_bool = _bool_choice


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Administrate %s" % label
    # NOTE: Delay header entry here to include vgrid name
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
    $("#dynownerspares").on("focus", "input[name=cert_id]",
        function(event) {
            //console.debug("in add owner focus handler");
            onOwnerInputChange();
        }
    );
    onMemberInputChange();
    $("#dynmemberspares").on("focus", "input[name=cert_id]",
        function(event) {
            //console.debug("in add member focus handler");
            onMemberInputChange();
        }
    );'''
    if configuration.site_enable_resources:
        add_ready += '''
    onResourceInputChange();
    $("#dynresourcespares").on("focus", "input[name=unique_resource_name]",
        function(event) {
            console.debug("in resource focus handler");
            onResourceInputChange();
        }
    );
    '''
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'short_title': configuration.short_title,
                    'vgrid_label': label,
                    'form_method': form_method,
                    'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}

    output_objects.append(
        {'object_type': 'header', 'text': "Administrate '%s'" % vgrid_name})

    if not vgrid_is_owner(vgrid_name, client_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text':
                               'Only owners of %s can administrate it.' %
                               vgrid_name})
        target_op = "sendrequestaction"
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        js_name = 'reqvgridowner%s' % hexlify(vgrid_name)
        helper = html_post_helper(js_name, '%s.py' % target_op,
                                  {'vgrid_name': vgrid_name,
                                   'request_type': 'vgridowner',
                                   'request_text': '',
                                   csrf_field: csrf_token
                                   })
        output_objects.append({'object_type': 'html_form', 'text': helper})
        output_objects.append(
            {'object_type': 'link',
             'destination':
             "javascript: confirmDialog(%s, '%s', '%s');"
             % (js_name, "Request ownership of " +
                vgrid_name + ":<br/>" +
                "\nPlease write a message to the owners below.",
                'request_text'),
             'class': 'addadminlink iconspace',
             'title': 'Request ownership of %s' % vgrid_name,
             'text': 'Apply to become an owner'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    for (item, scr) in zip(['owner', 'member', 'resource'],
                           ['vgridowner', 'vgridmember', 'vgridres']):
        if item == 'resource' and not configuration.site_enable_resources:
            continue
        output_objects.append({'object_type': 'sectionheader',
                               'text': "%ss" % item.title()
                               })
        (init_status, oobjs) = vgrid_add_remove_table(client_id, vgrid_name,
                                                      item, scr, configuration)
        if not init_status:
            output_objects.extend(oobjs)
            return (output_objects, returnvalues.SYSTEM_ERROR)
        else:
            output_objects.append({'object_type': 'html_form',
                                   'text': '<div class="div-%s">' % item})
            output_objects.append(
                {'object_type': 'link',
                 'destination':
                 "javascript:toggleHidden('.div-%s');" % item,
                 'class': 'removeitemlink iconspace',
                 'title': 'Toggle view',
                 'text': 'Hide %ss' % item.title()})
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
                 'text': 'Show %ss' % item.title()})
            output_objects.append({'object_type': 'html_form',
                                   'text': '</div>'})

    # Pending requests

    target_op = "addvgridowner"
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    helper = html_post_helper("acceptvgridownerreq", "%s.py" % target_op,
                              {'vgrid_name': vgrid_name,
                               'cert_id': '__DYNAMIC__',
                               'request_name': '__DYNAMIC__',
                               csrf_field: csrf_token
                               })
    output_objects.append({'object_type': 'html_form', 'text': helper})
    target_op = "addvgridmember"
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    helper = html_post_helper("acceptvgridmemberreq", "%s.py" % target_op,
                              {'vgrid_name': vgrid_name,
                               'cert_id': '__DYNAMIC__',
                               'request_name': '__DYNAMIC__',
                               csrf_field: csrf_token
                               })
    output_objects.append({'object_type': 'html_form', 'text': helper})
    target_op = "addvgridres"
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    helper = html_post_helper("acceptvgridresourcereq", "%s.py" % target_op,
                              {'vgrid_name': vgrid_name,
                               'unique_resource_name': '__DYNAMIC__',
                               'request_name': '__DYNAMIC__',
                               csrf_field: csrf_token
                               })
    output_objects.append({'object_type': 'html_form', 'text': helper})
    target_op = "rejectvgridreq"
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    helper = html_post_helper("rejectvgridreq", "%s.py" % target_op,
                              {'vgrid_name': vgrid_name,
                               'request_name': '__DYNAMIC__',
                               csrf_field: csrf_token
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
            "javascript: confirmDialog(%s, '%s', %s, %s);" %
            ("accept%(request_type)sreq" % req,
             "Accept %(target)s %(request_type)s request from %(entity)s" % req,
             'undefined', "{%s}" % ', '.join(["'%s': '%s'" % pair for pair in accept_args.items()])),
            'class': 'addlink iconspace', 'title':
            'Accept %(target)s %(request_type)s request from %(entity)s' % req,
            'text': ''}
        request_item['rejectrequestlink'] = {
            'object_type': 'link',
            'destination':
            "javascript: confirmDialog(%s, '%s', %s, %s);" %
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
                share_item = build_sharelinkitem_object(
                    configuration, share_dict)
                sharelinks.append(share_item)
    else:
        logger.warning("failed to load vgrid sharelinks for %s: %s" %
                       (vgrid_name, share_list))

    output_objects.append({'object_type': 'sectionheader',
                           'text': "Share Links"})
    output_objects.append({'object_type': 'html_form',
                           'text': '<p>Current share links in %s shared folder</p>' %
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

    (direct_status, direct_dict) = vgrid_settings(vgrid_name, configuration,
                                                  recursive=False,
                                                  as_dict=True)
    if not direct_status or not direct_dict:
        direct_dict = {}
    (settings_status, settings_dict) = vgrid_settings(vgrid_name,
                                                      configuration,
                                                      recursive=True,
                                                      as_dict=True)
    if not settings_status or not settings_dict:
        settings_dict = {}
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    # Always set these values
    settings_dict.update({
        'vgrid_name': vgrid_name,
        'vgrid_label': label,
        'owners': keyword_owners,
        'members': keyword_members,
        'all': keyword_all,
        'form_method': form_method,
        'csrf_field': csrf_field,
        'csrf_limit': csrf_limit
    })
    target_op = 'vgridsettings'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    settings_dict.update({'target_op': target_op, 'csrf_token': csrf_token})

    settings_form = '''
    <form method="%(form_method)s" action="%(target_op)s.py">
        <fieldset>
            <legend>%(vgrid_label)s configuration</legend>
                <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
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
        if direct_dict.get(field, False):
            choices = _valid_visible + _reset_choice
        else:
            choices = _valid_visible + _keep_choice
        for (key, val) in choices:
            checked = ''
            if settings_dict.get(field, keyword_owners) == val:
                checked = "checked"
            settings_form += '''
            <input type="radio" name="%s" value="%s" %s/> %s
''' % (field, val, checked, key)
        settings_form += '<br/>'
    field = 'restrict_settings_adm'
    restrict_settings_adm = settings_dict.get(field,
                                              default_vgrid_settings_limit)
    if direct_dict.get(field, False):
        direct_note = _reset_note
    else:
        direct_note = _keep_note
    settings_form += '''
            <h4>Restrict Settings</h4>
            Restrict changing of these settings to only the first
            <input type="number" name="restrict_settings_adm" min=0 max=999
            minlength=1 maxlength=3 value=%d required />
            owners %s.
''' % (restrict_settings_adm, direct_note)
    settings_form += '<br/>'
    field = 'restrict_owners_adm'
    restrict_owners_adm = settings_dict.get(field,
                                            default_vgrid_settings_limit)
    if direct_dict.get(field, False):
        direct_note = _reset_note
    else:
        direct_note = _keep_note
    settings_form += '''
            <h4>Restrict Owner Administration</h4>
            Restrict administration of owners to only the first
            <input type="number" name="restrict_owners_adm" min=0 max=999
            minlength=1 maxlength=3 value=%d required />
            owners %s.
''' % (restrict_owners_adm, direct_note)
    settings_form += '<br/>'
    field = 'restrict_members_adm'
    restrict_members_adm = settings_dict.get(field,
                                             default_vgrid_settings_limit)
    if direct_dict.get(field, False):
        direct_note = _reset_note
    else:
        direct_note = _keep_note
    settings_form += '''
            <h4>Restrict Member Administration</h4>
            Restrict administration of members to only the first
            <input type="number" name="restrict_members_adm" min=0 max=999
            minlength=1 maxlength=3 value=%d required />
            owners %s.
''' % (restrict_members_adm, direct_note)
    settings_form += '<br/>'
    field = 'restrict_resources_adm'
    restrict_resources_adm = settings_dict.get(field,
                                               default_vgrid_settings_limit)
    if direct_dict.get(field, False):
        direct_note = _reset_note
    else:
        direct_note = _keep_note
    settings_form += '''
            <h4>Restrict Resource Administration</h4>
            Restrict administration of resources to only the first
            <input type="number" name="restrict_resources_adm" min=0 max=999
            minlength=1 maxlength=3 value=%d required />
            owners %s.
''' % (restrict_resources_adm, direct_note)
    settings_form += '<br/>'
    if vgrid_restrict_write_support(configuration):
        settings_form += '''<p>All write access options below can be set to
owners, members or none. By default only owners can write web pages while
owners and members can edit data in the shared folders. In effect setting write
access to <em>members</em> means that owners and members have full access.
Similarly setting a write access flag to <em>owners</em> means that only owners
can modify the data, while members can only read and use it. Finally setting a
write access flag to <em>none</em> means that neither owners nor members can
modify the data there, effectively making it read-only. Some options are not
yet supported and thus are disabled below.
</p>
'''
        writable_options = [("Shared files write access", "write_shared_files",
                             keyword_members),
                            ("Private web page write access", "write_priv_web",
                             keyword_owners),
                            ("Public web page write access", "write_pub_web",
                             keyword_owners),
                            ]
    else:
        writable_options = []
    for (title, field, default) in writable_options:
        settings_form += '<h4>%s</h4>' % title
        if direct_dict.get(field, False):
            choices = _valid_write_access + _reset_choice
        else:
            choices = _valid_write_access + _keep_choice
        for (key, val) in choices:
            disabled = ''
            # TODO: remove these artifical limits once we support changing
            # TODO: also add check for vgrid web reshare in sharelink then
            if field == 'write_shared_files' and val == keyword_owners:
                disabled = 'disabled'
            elif field == 'write_priv_web' and val in [keyword_members,
                                                       keyword_none]:
                disabled = 'disabled'
            elif field == 'write_pub_web' and val in [keyword_members,
                                                      keyword_none]:
                disabled = 'disabled'
            checked = ''
            if settings_dict.get(field, default) == val:
                checked = "checked"
            settings_form += '''
            <input type="radio" name="%s" value="%s" %s %s /> %s
''' % (field, val, checked, disabled, key)
        settings_form += '<br/>'
    sharelink_options = [("Limit sharelink creation to", "create_sharelink")]
    for (title, field) in sharelink_options:
        settings_form += '<h4>%s</h4>' % title
        if direct_dict.get(field, False):
            choices = _valid_sharelink + _reset_choice
        else:
            choices = _valid_sharelink + _keep_choice
        for (key, val) in choices:
            checked = ''
            if settings_dict.get(field, keyword_owners) == val:
                checked = "checked"
            settings_form += '''
            <input type="radio" name="%s" value="%s" %s/> %s
''' % (field, val, checked, key)
        settings_form += '<br/>'
    field = 'request_recipients'
    request_recipients = settings_dict.get(field,
                                           default_vgrid_settings_limit)
    if direct_dict.get(field, False):
        direct_note = _reset_note
    else:
        direct_note = _keep_note
    settings_form += '''
            <h4>Request Recipients</h4>
            Notify only first
            <input type="number" name="request_recipients" min=0 max=999
            minlength=1 maxlength=3 value=%d required />
            owners about access requests %s.
''' % (request_recipients, direct_note)
    settings_form += '<br/>'

    bool_options = [("Hidden", "hidden"), ]
    for (title, field) in bool_options:
        settings_form += '<h4>%s</h4>' % title
        if direct_dict.get(field, False):
            choices = _valid_bool + _reset_choice
        else:
            choices = _valid_bool + _keep_choice
        for (key, val) in choices:
            checked, inherit_note = '', ''
            if settings_dict.get(field, False) == val:
                checked = "checked"
            if direct_dict.get(field, False) != \
                    settings_dict.get(field, False):
                inherit_note = '''&nbsp;<span class="warningtext iconspace">
Forced by a parent %(vgrid_label)s. Please disable there first if you want to
change the value here.</span>''' % settings_dict
            settings_form += '''
            <input type="radio" name="%s" value="%s" %s /> %s
''' % (field, val, checked, key)
        settings_form += '%s<br/>' % inherit_note
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
    target_op = 'updatevgrid'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    settings_dict.update({'target_op': target_op, 'csrf_token': csrf_token})
    output_objects.append({'object_type': 'html_form',
                           'text': '''
      <form method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
          <input type="hidden" name="vgrid_name" value="%(vgrid_name)s" />
          <input type="submit" value="Repair components" />
      </form>
''' % settings_dict})

    (owners_status, owners_direct) = vgrid_owners(vgrid_name, configuration,
                                                  False)
    if not owners_status:
        logger.error("failed to load owners for %s: %s" % (vgrid_name,
                                                           owners_direct))
        return (output_objects, returnvalues.SYSTEM_ERROR)
    (members_status, members_direct) = vgrid_members(vgrid_name, configuration,
                                                     False)
    if not members_status:
        logger.error("failed to load members for %s: %s" % (vgrid_name,
                                                            members_direct))
        return (output_objects, returnvalues.SYSTEM_ERROR)
    (resources_status, resources_direct) = vgrid_resources(vgrid_name,
                                                           configuration,
                                                           False)
    if not resources_status:
        logger.error("failed to load resources for %s: %s" %
                     (vgrid_name, resources_direct))
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'sectionheader',
                           'text': "Delete %s " % vgrid_name})
    if len(owners_direct) > 1 or members_direct or resources_direct:
        output_objects.append({'object_type': 'html_form', 'text': '''
To delete <b>%(vgrid)s</b> first remove all resources, members and owners
ending with yourself.
''' % {'vgrid': vgrid_name}})
    else:
        output_objects.append({'object_type': 'html_form', 'text': '''
<p>As the last owner you can leave and delete <b>%(vgrid)s</b> including all
associated shared files and components.<br/>
</p>
<p class="warningtext">
You cannot undo such delete operations, so please use with great care!
</p>
''' % {'vgrid': vgrid_name}})
        target_op = "rmvgridowner"
        csrf_token = make_csrf_token(configuration, form_method,
                                     target_op, client_id, csrf_limit)
        js_name = 'rmlastvgridowner'
        helper = html_post_helper(js_name, '%s.py' % target_op,
                                  {'vgrid_name': vgrid_name,
                                   'cert_id': client_id,
                                   'flags': 'f',
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        output_objects.append(
            {'object_type': 'link', 'destination':
             "javascript: confirmDialog(%s, '%s');" %
             (js_name, 'Really leave and delete %s?' %
              vgrid_name),
             'class': 'removelink iconspace',
             'title': 'Leave and delete %s' % vgrid_name,
             'text': 'Leave and delete %s' % vgrid_name}
        )

    # Spacing
    output_objects.append({'object_type': 'html_form', 'text': '''
            <div class="vertical-spacer"></div>
    '''})

    return (output_objects, returnvalues.OK)
