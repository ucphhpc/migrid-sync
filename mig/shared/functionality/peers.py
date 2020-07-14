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

import datetime
import os

import shared.returnvalues as returnvalues
from shared.accountreq import peers_permit_allowed
from shared.base import pretty_format_user, fill_distinguished_name, \
    client_id_dir
from shared.defaults import csrf_field, peers_filename, peers_fields, \
    peer_kinds
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import man_base_js, man_base_html, html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.serial import load
from shared.useradm import get_full_user_map


sample_users = [{'full_name': 'Jane Doe', 'country': 'DK', 'email':
                 'jane.doe@phys.au.dk', 'organization':
                 'University of Aarhus, Dept. of Physics',
                 },
                {'full_name': 'John Doe', 'organization': 'DTU', 'country':
                 'DK', 'email': 'john.doe@dtu.dk'}]


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

    # jquery support for confirmation on "edit"
    (add_import, add_init, add_ready) = man_base_js(configuration, [])
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
                    'target_op': target_op, 'csrf_token': csrf_token}
    form_prefix_html = '''
<form class="save_peers save_general" method="%(form_method)s"
action="%(target_op)s.py">
'''
    form_suffix_html = '''
<input type="submit" value="Save Peers" /><br/>
</form>
'''
    shared_peer_html = '''
    <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
    <div class="form-row">
      <div class="col-md-4 mb-3 form-cell">
          <label for="peers_label">Name</label>
          <input class="form-control" type="text" size=30 name="peers_label" value="" required
            pattern="[^ ]+" title="Name for peers" placeholder="Peers name or label" />
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
          <input class="form-control themed-select html-select" type="date"
            name="peers_expire" value="%s" required pattern="[0-9/-]+"
            title="Access expiry date" />
      </div>
    </div>
''' % expire.date()
    fill_helpers['form_prefix_html'] = form_prefix_html % fill_helpers
    fill_helpers['form_suffix_html'] = form_suffix_html % fill_helpers
    fill_helpers['shared_peer_html'] = shared_peer_html % fill_helpers

    peers_path = os.path.join(configuration.user_settings, client_dir,
                              peers_filename)
    try:
        peers_dict = load(peers_path)
    except Exception, exc:
        logger.warning("could not load peers from: %s" % exc)
        peers_dict = {}

    tabs_html = '''
<div id="wrap-tabs" class="peers-tabs">
<ul>
<li><a href="#show-tab">Show Peers</a></li>
<li class="%(peers_permit_class)s"><a href="#import-tab">Import Peers</a></li>
<!-- TODO: enable these additional methods when ready -->
<li class="%(peers_permit_class)s hidden"><a href="#fields-tab">Enter Peers</a></li>
<li class="%(peers_permit_class)s hidden"><a href="#urlfetch-tab">Fetch Peers From URL</a></li>
</ul>

<div id="show-tab">
<p>
%(peers_notice)s
This is an overview of your registered peers. That is, people that you have
vouched for to get an account on %(site)s because they need it for a particular
course/workshop, research project or for general long term collaboration with
you. The site admins will use this information to accept account requests and
extensions from any peers until the given time of expiry.
</p>
<div class="peer_entries">
'''
    csv_sep = ';'
    for (label, entry) in peers_dict.items():
        tabs_html += '''<h3>%s</h3>
<h4>Kind</h4>
%s
<h4>Expire</h4>
%s
<h4>Peers</h4>
''' % (label, entry.get('kind', 'UNKNOWN'), entry.get('expire', 'UNKNOWN'))
        user_lines = []
        export_lines = [csv_sep.join(peers_fields)]
        for user in entry.get('peers', []):
            if not user:
                continue
            export_lines.append(csv_sep.join(
                [user.get(i, '') for i in peers_fields]))
            fill_distinguished_name(user)
            user_lines.append(pretty_format_user(
                user['distinguished_name'], False))
        tabs_html += '''
<div class="peers_export init-expanded accordion invert-theme">
<h4>View Peers</h4>
<p class="verbatim">%s
</p>
<h4>Exportable Peers</h4>
<p class="verbatim">%s
</p>
</div>''' % ('\n'.join(user_lines), '\n'.join(export_lines))

    if not peers_dict:
        tabs_html += '''<div class="displaybox verbatim">
No peers registered yet ...
</div>
'''
    tabs_html += '''
</div>
</div>

<div id="fields-tab">
<p>
Please enter your peers in the form below and assign a kind and account expiry
time.
</p>
%(form_prefix_html)s
%(shared_peer_html)s
<input type="hidden" name="peers_format" value="fields" />
'''
    for field in peers_fields:
        field_extras = 'type="text"'
        if field.lower() == 'email':
            field_extras = 'type="email"'
        elif field.lower() == 'country':
            field_extras += ' minlen=2 maxlen=2'
        # TODO: country drop-down?
        tabs_html += '''
<input %s placeholder="%s" name="%s" />
''' % (field_extras, field.replace('_', ' ').capitalize(), field)
    tabs_html += '''
<button class="add_entry fas fas-plus" onClick="addEntry(); return false;">
Add</button>
<button class="clean_entry fas fas-clear" onClick="clearEntry(); return false;">
Clear</button>
<br/>
'''
    tabs_html += '''
%(form_suffix_html)s
</div>

<div id="import-tab" >
<p>
You can paste or enter a CSV-formatted list below to create or update an
existing group of peers. The contents must start with a single header line to
define the field order in the following individual user lines as shown in the
example at the bottom.
</p>
'''
    tabs_html += '''
<div id="peers-grid" class="import-form form_container">
<h2>Import/Update Peers</h2>
%(form_prefix_html)s
%(shared_peer_html)s
<input type="hidden" name="peers_format" value="csvform" />
<textarea class="fillwidth" name="peers_content" rows=10 title="CSV list of peers"
  placeholder="Paste or enter CSV-formatted list of peers ..."></textarea>
<br/>
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
''' % (';'.join(peers_fields),
       ';'.join([sample_users[0].get(i, '') for i in peers_fields]),
       ';'.join([sample_users[-1].get(i, '') for i in peers_fields]))

    tabs_html += '''
<div id="urlfetch-tab" >
<p>
In case you have a general project participation list online you can specify the URL here to fetch and parse the list into a peers list. Please note that this memberlist should still be on the machine readbale format described on the upload tab.
</p>
%(form_prefix_html)s
%(shared_peer_html)s
<br/>
<input type="hidden" name="peers_format" value="csvurl" />
<input class="fillwidth" type="text" name="peers_content" value=""
    placeholder="URL to fetch CSV-formatted list of peers from ..." /><br/>
%(form_suffix_html)s
</div >
</div >
'''
    output_objects.append(
        {'object_type': 'html_form', 'text': tabs_html % fill_helpers})

    # Helper form for post

    helper = html_post_helper('savepeers', '%s.py' % target_op,
                              {'kind': '__DYNAMIC__', 'peers': '__DYNAMIC__',
                               csrf_field: csrf_token})
    output_objects.append({'object_type': 'html_form', 'text':
                           helper})

    logger.info("%s end for %s" % (op_name, client_id))
    return (output_objects, returnvalues.OK)
