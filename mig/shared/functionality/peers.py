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
from shared.base import pretty_format_user, fill_distinguished_name, \
    client_id_dir
from shared.defaults import csrf_field, peers_filename
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import man_base_js, man_base_html, html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.serial import load

valid_kinds = ['course', 'project', 'collaboration']
user_fields = ['full_name', 'organization', 'country', 'email']
sample_users = [['Jane Doe', 'University of Aarhus, Dept. of Physics',
                 'DK', 'jane.doe@phys.au.dk'],
                ['John Doe', 'DTU', 'DK', 'john.doe@dtu.dk']]


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
    '''
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    output_objects.append({'object_type': 'header', 'text': 'Peers'})

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'peersaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers = {
        'site': configuration.short_title, 'form_method': form_method,
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
    <input type="text" size=40 name="peers_label" value=""
      placeholder="Peer label of your choice ..." /><br/>
<select class="styled-select html-select" name="peers_kind">
'''
    expire = datetime.datetime.now()
    expire += datetime.timedelta(days=30)
    for name in valid_kinds:
        shared_peer_html += '''
<option value="%s">%s
''' % (name, name.capitalize())
    shared_peer_html += '''
</select><br/>
<input class="styled-select html-select" type="date" name="peers_expire" value="%s"
  title="Access expiry date" /><br/>
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
<li><a href="#upload-tab">Peers File</a></li>
<!-- TODO: enable these additional methods when ready -->
<li class="hidden"><a href="#fields-tab">Enter Peers</a></li>
<li class="hidden"><a href="#urlfetch-tab">Fetch Peers From URL</a></li>
</ul>

<div id="show-tab">
<p>
This is a list of your registered peers, that is, people that you vouch for to
get an %(site)s account because they need it for a particular
course/workshop, a particular research project or for general long term
collaboration with you.
</p>
<div class="peer_entries">
'''
    for (label, entry) in peers_dict.items():
        tabs_html += '''<h3>%s</h3>
<p>
Kind: %s
</p>
<p>
Expire: %s
</p>
''' % (label, entry.get('kind', 'UNKNOWN'), entry.get('expire', 'UNKNOWN'))
        for user in entry.get('peers', []):
            if not user:
                continue
            fill_distinguished_name(user)
            logger.debug("show peer: %s" % user)
            tabs_html += '''
<p>
<pre class="peer_user">%s</pre>
</p>
''' % pretty_format_user(user['distinguished_name'], False)

    if not peers_dict:
        tabs_html += '''
<pre class="grey">No peers registered yet ...</pre>
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
'''
    for field in user_fields:
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
</div >
<div id = "upload-tab" >
<p>You can paste or upload a CSV file with multiple peers. The file must start
with a single header line to define the field order in the following individual
user lines like shown below:
</p>'''
    tabs_html += '''
<p>
<pre class="verbatim grey">
%s
%s
...
%s
</pre>
</p>
''' % (';'.join(user_fields), ';'.join(sample_users[0]), ';'.join(sample_users[-1]))
    tabs_html += '''
%(form_prefix_html)s
%(shared_peer_html)s
<textarea class="fillwidth" name="peers_form" rows=20
    placeholder="Paste or enter CSV-formatted list of peers ..."></textarea>
<br/>
%(form_suffix_html)s
'''
    tabs_html += '''
</div >
<div id = "urlfetch-tab" >
<p>
In case you have a general project participation list online you can specify the URL here to fetch and parse the list into a peers list. Please note that this memberlist should still be on the machine readbale format described on the upload tab.
</p>
%(form_prefix_html)s
%(shared_peer_html)s
<br/>
<input class="fillwidth" type="text" name="peers_url" value=""
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
