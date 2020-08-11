#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# peers - manage external collaboration partners, etc.
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""Peers provides an optional facility to specify external collaboration
partners, course/workshop participants and similar users that one user needs
to offer site access for a time limited period.
"""
from __future__ import absolute_import

import datetime
import os

from mig.shared import returnvalues
from mig.shared.accountreq import peers_permit_allowed
from mig.shared.base import pretty_format_user, fill_distinguished_name, \
    client_id_dir
from mig.shared.defaults import csrf_field, peers_filename, \
    pending_peers_filename, peers_fields, peer_kinds, default_pager_entries
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.html import man_base_js, man_base_html, html_post_helper
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.serial import load
from mig.shared.useradm import get_full_user_map


sample_users = [{'full_name': 'Jane Doe', 'country': 'DK', 'email':
                 'jane.doe@phys.au.dk', 'organization':
                 'Dept. of Physics at University of Aarhus',
                 },
                {'full_name': 'John Doe', 'organization': 'DTU', 'country':
                 'DK', 'email': 'john.doe@dtu.dk'}]
csv_sep = ';'
edit_entries = 6


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['peers', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    client_dir = client_id_dir(client_id)
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Peers'
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

    logger.info("%s begin for %s" % (op_name, client_id))

    # jquery support for tablesorter and confirmation on delete
    # table initially sorted by col. 4 (kind), then 0 (name)
    refresh_call = 'ajax_peers()'
    table_spec = {'table_id': 'peers', 'sort_order':
                  '[[4,0],[0,0]]',
                  'refresh_call': refresh_call}
    (add_import, add_init, add_ready) = man_base_js(configuration,
                                                    [table_spec])

    add_init += '''
function transfer_id_fields() {
    //console.log("in transfer_id_fields");
    var peer_count = 0;
    var peer_id;
    $("#fields-tab .save_peers .field_group").each(function() {
        var group = $(this);
        peer_id = '';
        var full_name = $(group).find("input.entry-field.full_name").val();
        var organization = $(group).find("input.entry-field.organization").val();
        var email = $(group).find("input.entry-field.email").val();
        var country = $(group).find("input.entry-field.country").val();
        if (full_name && organization && email && country) {
            peer_id = "/C="+country+"/ST=NA/L=NA/O="+organization+"/OU=NA/CN="+full_name+"/emailAddress="+email;
            //console.debug("built peer_id: "+peer_id);
            peer_count += 1;
        }
        /* Always set peer_id to reset empty rows */
        $(group).find("input.id-collector").val(peer_id);
        console.log("set collected peer_id: "+$(group).find("input.id-collector").val());
    });
    if (peer_count > 0) {
        return true;
    } else {
        return false;
    }
}

    '''
    add_ready += '''
        $(".peers-tabs").tabs();
        $(".peers-tabs .accordion").accordion({
            collapsible: true,
            active: false,
            icons: {"header": "ui-icon-plus", "activeHeader": "ui-icon-minus"},
            heightStyle: "content"
            });
        /* fix and reduce accordion spacing */
        $(".peers-tabs .accordion .ui-accordion-header").css("padding-top", 0).css("padding-bottom", 0).css("margin", 0);
        $(".peers-tabs .init-expanded.accordion ").accordion("option", "active", 0);
        $("#fields-tab .save_peers").on("submit", transfer_id_fields);
    '''
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    output_objects.append({'object_type': 'header', 'text': 'Peers'})

    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    # Optional site-wide limitation of peers permission
    peers_permit_class = 'hidden'
    if user_dict and peers_permit_allowed(configuration, user_dict):
        peers_permit_class = ''

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'peersaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers = {'peers_notice': configuration.site_peers_notice,
                    'site': configuration.short_title,
                    'peers_permit_class': peers_permit_class,
                    'form_method': form_method,
                    'csrf_field': csrf_field, 'csrf_limit': csrf_limit,
                    'target_op': target_op, 'csrf_token': csrf_token,
                    'csv_header': csv_sep.join([i for i in peers_fields])}
    form_prefix_html = '''
<form class="save_peers save_general" method="%(form_method)s"
action="%(target_op)s.py">
'''
    form_suffix_html = '''
<input type="submit" value="Save Peers" /><br/>
</form>
'''
    form_accept_html = '''
<input type="submit" value="Apply" /><br/>
</form>
'''
    shared_peer_html = '''
    <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
    <div class="form-row three-col-grid">
      <div class="col-md-4 mb-3 form-cell">
          <label for="peers_label">Label</label>
          <input class="form-control fill-width" type="text" name="peers_label"
            value="" pattern="[^ ]*" title="Label for peers"
            placeholder="Peers name or label" />
      </div>
      <div class="col-md-4 mb-3 form-cell">
          <label for="peers_kind">Kind</label>
          <select class="form-control themed-select html-select" name="peers_kind">
'''
    expire = datetime.datetime.now()
    expire += datetime.timedelta(days=30)
    for name in peer_kinds:
        shared_peer_html += '''
              <option value="%s">%s
''' % (name, name.capitalize())
    shared_peer_html += '''
          </select>
      </div>
      <div class="col-md-4 mb-3 form-cell">
          <label for="peers_expire">Expire</label>
          <input class="form-control themed-select html-select fill-width"
            type="date" name="peers_expire" value="%s" required
            pattern="[0-9/-]+" title="Access expiry date" />
      </div>
    </div>
''' % expire.date()
    fill_helpers['form_prefix_html'] = form_prefix_html % fill_helpers
    fill_helpers['form_suffix_html'] = form_suffix_html % fill_helpers
    fill_helpers['form_accept_html'] = form_accept_html % fill_helpers
    fill_helpers['shared_peer_html'] = shared_peer_html % fill_helpers

    peers_path = os.path.join(configuration.user_settings, client_dir,
                              peers_filename)
    try:
        all_peers = load(peers_path)
    except Exception as exc:
        logger.warning("could not load peers from %s: %s" % (peers_path, exc))
        all_peers = {}

    pending_peers_path = os.path.join(configuration.user_settings, client_dir,
                                      pending_peers_filename)
    try:
        pending_peers = load(pending_peers_path)
    except Exception as exc:
        logger.warning("could not load pending peers from %s: %s" %
                       (pending_peers_path, exc))
        pending_peers = []

    tabs_html = '''
<div id="wrap-tabs" class="peers-tabs">
<ul>
<li><a href="#show-tab">Show Peers</a></li>
<li class="%(peers_permit_class)s"><a href="#requests-tab">Requested Peers</a></li>
<li class="%(peers_permit_class)s"><a href="#fields-tab">Enter Peers</a></li>
<li class="%(peers_permit_class)s"><a href="#import-tab">Import Peers</a></li>
<!-- TODO: enable additional methods when ready? -->
<li class="%(peers_permit_class)s hidden"><a href="#urlfetch-tab">Fetch Peers From URL</a></li>
</ul>

<div id="show-tab">
<p>
%(peers_notice)s
This is an overview of your registered peers. That is, people that you have
vouched for to get an account on %(site)s because they need it for a particular
course/workshop, research project or for general long term collaboration with
you. The site admins will use this information to accept account requests and
extensions from your peers until the given time of expiry.
</p>
<div class="peer_entries">
'''
    output_objects.append(
        {'object_type': 'html_form', 'text': tabs_html % fill_helpers})

    output_objects.append({'object_type': 'table_pager', 'entry_name': 'peers',
                           'default_entries': default_pager_entries})
    peers = []
    for (peer_id, entry) in all_peers.items():
        filled_entry = dict([(field, '') for field in
                             ('label', 'kind', 'expire')])
        fill_distinguished_name(entry)
        filled_entry.update(entry)
        filled_entry['object_type'] = 'peer'
        # TODO: create edit dialog to change expire?
        # filled_entry['editpeerlink'] = {
        #    'object_type': 'link',
        #    'destination':
        #    "javascript: confirmDialog(%s, '%s', %s, %s);" %
        #    ('peer_action', 'Update %(distinguished_name)s?' % filled_entry,
        #     'undefined',
        #     "{action: 'update', peers_label: '%(label)s', peers_kind: '%(kind)s', peers_expire:'%(expire)s', peers_content: '%(distinguished_name)s'}" % filled_entry),
        #    'class': 'editlink iconspace',
        #    'title': 'Update %(distinguished_name)s in peers' % filled_entry,
        #    'text': ''}
        filled_entry['invitepeerlink'] = {
            'object_type': 'link',
            'destination':
            "javascript: confirmDialog(%s, '%s', %s, %s);" %
            ('peer_action', 'Send invitation email to %(distinguished_name)s?' % filled_entry,
             'undefined',
             "{action: 'update', peers_label: '%(label)s', peers_kind: '%(kind)s', peers_expire:'%(expire)s', peers_content: '%(distinguished_name)s', peers_invite: true}" % filled_entry),
            'class': 'invitelink iconspace',
            'title': 'Invite %(distinguished_name)s as peer' % filled_entry,
            'text': ''}
        filled_entry['delpeerlink'] = {
            'object_type': 'link',
            'destination':
            "javascript: confirmDialog(%s, '%s', %s, %s);" %
            ('peer_action', 'Really remove %(distinguished_name)s?' % filled_entry,
             'undefined',
             "{action: 'remove', peers_label: '%(label)s', peers_kind: '%(kind)s', peers_expire:'%(expire)s', peers_content: '%(distinguished_name)s'}" % filled_entry),
            'class': 'removelink iconspace',
            'title': 'Remove %(distinguished_name)s from peers' % filled_entry,
            'text': ''}
        peers.append(filled_entry)
    output_objects.append({'object_type': 'peers',
                           'peers': peers})

    # NOTE: reset tabs_html here
    tabs_html = '''
</div>
</div>

<div id="fields-tab">
<p>
You may enter your individual peers in the form fields below and assign a
shared kind and account expiry time for all entries. Just leave the Action
field to <em>Add</em> unless you want to <em>Update</em> or <em>Remove</em>
existing peers. You are free to leave rows empty, but each field in a peer row
MUST be filled for the row to be treated.
</p>
<div class="enter-form form_container">
%(form_prefix_html)s
%(shared_peer_html)s
<input type="hidden" name="peers_format" value="userid" />
<div class="form-row one-col-grid">
    <div class="col-md-12 mb-1 form-cell">
    <label for="action">Action</label>
    <select class="form-control themed-select html-select fill-width" name="action">
        <option value="add">Add</option>
        <option value="update">Update</option>
        <option value="remove">Remove</option>
    </select>
    </div>
</div>
'''

    # TODO: switch to JS rows with automagic addition to always keep spare row?
    for index in range(edit_entries):
        # NOTE: we arrange each entry into a field_group_N div with a hidden
        #       user ID collector where the field values are merged on submit
        #       and the actual fields are not passed to the backend.
        tabs_html += '''
<div id="field_group_%s" class="field_group">
    <input class="id-collector" type="hidden" name="peers_content" value="" />
    <div class="form-row four-col-grid">
        ''' % index
        for field in peers_fields:
            title = ' '.join([i.capitalize() for i in field.split('_')])
            placeholder = title
            field_extras = 'type="text"'
            if field.lower() == 'full_name':
                field_extras = 'minlength=3'
            elif field.lower() == 'organization':
                field_extras = 'minlength=2'
            elif field.lower() == 'email':
                placeholder = "Email at organization"
                field_extras = 'type="email" minlength=5'
            elif field.lower() == 'country':
                # TODO: country drop-down instead?
                title = "Country (ISO 3166)"
                placeholder = "2-Letter country code"
                field_extras += ' minlength=2 maxlength=2'
            tabs_html += '''
      <div class="col-md-3 mb-3 form-cell">
          <label for="%(field)s">%(title)s</label><br/>
          <input class="form-control %(field)s entry-field fill-width" %(extras)s
            placeholder="%(placeholder)s" />
      </div>
''' % {'field': field, 'title': title, 'placeholder': placeholder,
                'extras': field_extras}

        tabs_html += '''
    </div>
</div>
'''

    tabs_html += '''
<span class="switch-label">Invite on email</span>
<label class="switch" for="peers_invite">
<input class="" type="checkbox" name="peers_invite">
<span class="slider round small" title="Optional email invitation"></span>
<br/>
</label>
%(form_suffix_html)s
</div>
</div>
'''
    tabs_html += '''
<div id="import-tab" >
<p>
You can paste or enter a CSV-formatted list below to create or update your
existing peers. The contents must start with a single header line to define
the field order in the following individual user lines as shown in the example
at the bottom.
</p>
<div class="import-form form_container">
<h2>Import/Update Peers</h2>
%(form_prefix_html)s
%(shared_peer_html)s
<input type="hidden" name="peers_format" value="csvform" />
<input type="hidden" name="action" value="import" />
<textarea class="fillwidth" name="peers_content" rows=10 title="CSV list of peers"
  placeholder="Paste or enter CSV-formatted list of peers ..."></textarea>
<br/>
<span class="switch-label">Invite on email</span>
<label class="switch" for="peers_invite">
<input class="" type="checkbox" name="peers_invite">
<span class="slider round small" title="Optional email invitation"></span>
<br/>
</label>
%(form_suffix_html)s
</div>
'''
    tabs_html += '''
<br/>
<div class="peers_export init-collapsed accordion invert-theme">
<h4>Example Peers</h4>
<p class="verbatim">%s
%s
...
%s
</p>
</div>
</div>
''' % (fill_helpers['csv_header'],
       csv_sep.join([sample_users[0].get(i, '') for i in peers_fields]),
       csv_sep.join([sample_users[-1].get(i, '') for i in peers_fields]))

    tabs_html += '''
<div id="requests-tab" >
<p>
If someone requests an external user account on %(site)s and explicitly
references you as sponsor or contact person the site admins will generally
forward the request, so that it shows up here for you to confirm. You can then
accept or reject the individual requests below to let the site admins proceed
with account creation or rejection.
</p>
'''

    pending_count = 0
    for (peer_id, user) in pending_peers:
        # TODO: consider still showing if expired?
        # Skip already accepted request
        if peer_id in all_peers:
            continue
        pending_count += 1
        tabs_html += '''
<div class="requests-form form_container">
%(form_prefix_html)s
%(shared_peer_html)s
<br/>
<input type="hidden" name="peers_format" value="userid" />
<div class="form-row five-col-grid">
    <div class="col-md-2 mb-5 form-cell">
    <label for="action">Action</label>
    <select class="form-control themed-select html-select fill-width" name="action">
        <option value="accept">Accept</option>
        <option value="reject">Reject</option>
    </select>
    </div>
'''
        tabs_html += '''
    <input type="hidden" name="peers_content" value="%(distinguished_name)s" />
''' % user
        for field in peers_fields:
            title = ' '.join([i.capitalize() for i in field.split('_')])
            tabs_html += '''
    <div class="col-md-2 mb-5 form-cell">
        <label for="%(field)s">%(title)s</label>
        <input class="form-control fill-width" type="text" value="%(value)s"
          readonly=readonly />
    </div>''' % {'field': field, 'title': title, 'value': user.get(field, '')}
        tabs_html += '''
</div>
%(form_accept_html)s
</div>
'''
    if pending_count < 1:
        tabs_html += '''
<p class="info icon iconpadding">
No pending requests ...
</p>
'''
    tabs_html += '''
</div>
'''

    tabs_html += '''
<div id="urlfetch-tab" >
<p>
In case you have a general project participation list online you can specify the URL here to fetch and parse the list into a peers list. Please note that this memberlist should still be on the machine readbale format described on the upload tab.
</p>
<div class="urlfetch-form form_container">
%(form_prefix_html)s
%(shared_peer_html)s
<br/>
<input type="hidden" name="action" value="import" />
<input type="hidden" name="peers_format" value="csvurl" />
<input class="fillwidth" type="text" name="peers_content" value=""
    placeholder="URL to fetch CSV-formatted list of peers from ..." /><br/>
%(form_suffix_html)s
</div>
</div>
'''

    # End wrap-tabs div
    tabs_html += '''
</div >
'''
    output_objects.append(
        {'object_type': 'html_form', 'text': tabs_html % fill_helpers})

    # Helper form for post

    helper = html_post_helper('peer_action', '%s.py' % target_op,
                              {'action': '__DYNAMIC__',
                               'peers_label': '__DYNAMIC__',
                               'peers_kind': '__DYNAMIC__',
                               'peers_expire': '__DYNAMIC__',
                               'peers_content': '__DYNAMIC__',
                               'peers_invite': '__DYNAMIC__',
                               'peers_format': 'userid',
                               csrf_field: csrf_token})
    output_objects.append({'object_type': 'html_form', 'text':
                           helper})

    logger.info("%s end for %s" % (op_name, client_id))
    return (output_objects, returnvalues.OK)
