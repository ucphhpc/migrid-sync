#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# datatransfer - import and export data in the backgroud
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

"""Manage data imports and exports"""

import glob
import os
import datetime
import time

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.conf import get_resource_exe
from shared.defaults import all_jobs, job_output_dir
from shared.fileio import unpickle, pickle
from shared.functional import validate_input_and_cert
from shared.handlers import correct_handler
from shared.init import initialize_main_variables, find_entry
from shared.ssh import copy_file_to_resource
from shared.validstring import valid_user_path


get_actions = ['show']
# TODO: add these internal targets
post_actions = ['import', 'export'] # + ['move', 'copy', 'unpack', 'pack']
valid_actions = get_actions + post_actions

def signature():
    """Signature of the main function"""

    defaults = {'action': ['show'], 'protocol': [''], 'fqdn':[''],
                'port': [''], 'src':[''], 'dst': [''], 'username': [''],
                'password': [''], 'key': [''], 'flags': ['']}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
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

    action = accepted['action'][-1]
    protocol = accepted['protocol'][-1]
    fqdn = accepted['fqdn'][-1]
    port = accepted['port'][-1]
    src_list = accepted['src']
    dst = accepted['dst'][-1]
    username = accepted['username'][-1]
    password = accepted['password'][-1]
    key = accepted['key'][-1]
    flags = accepted['flags']
    
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s data import/export' % configuration.short_title
    output_objects.append({'object_type': 'header', 'text'
                           : 'Manage background data transfers'})

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid action "%s" (supported: %s)' % \
                               (action, ', '.join(valid_actions))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action in post_actions:
        if not correct_handler('POST'):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'Only accepting POST requests to prevent unintended updates'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        if not fqdn:
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'No host address provided!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : '''
Fill in the data transfer details below to request a new background data
transfer task.
Source can be a path or a wild card pattern using "*" and "?" to match one
or more characters.
Destination is a single location to transfer the data to. It is considered in
relation to your user home for get and move requests. Source is similarly
considered in relation to your user home in move and put requests.
Destination is a always handled as a directory path to put source files into.
'''})
    if action in get_actions:
        html = '''
<table class="datatransfer">
<tr>
<td>
<form method="post" action="datatransfer.py">
<table class="datatransfer">
<tr><td class=centertext>
</td></tr>
<tr><td>
<span>
Action:
<input type=radio name=action checked value="import" />import data
<input type=radio name=action value="export" />export data
<input type=radio name=action value="move" />move data
</span>
<span>
Protocol:
<select name=protocol>
<option selected value="https">HTTPS</option>
<option value="http" />HTTP</option>
<option value="sftp" />SFTP</option>
<option value="scp" />SCP</option>
<option value="ssh+rsync" />SSH+RSYNC</option>
<option value="rsync" />RSYNC</option>
<option value="ftps" />FTPS</option>
<option value="ftp" />FTP</option>
</select>
</span>
<br/>
<br/>
Host:
<input type=text size=45 name=fqdn value="" />
Port:
<input type=text size=5 name=port value="" />
</td></tr>
<tr><td>
Username:<br />
<input type=text size=60 name=username value="" />
</td></tr>
<tr><td>
Password:<br />
<input type=password size=60 name=password value="" />
</td></tr>
<tr><td>
Key:<br />
<input type=key size=60 name=key value="" />
</td></tr>
<tr><td>
Source path(s):<br />
<div id="srcfields">
<input type=text size=60 name=src value="" /><br />
</div>
</td></tr>
<tr><td>
Destination path:<br />
<input type=text size=60 name=dst value="" />
</td></tr>
<tr><td>
Extra flags:<br />
<input type=text size=60 name=flags value="" />
</td></tr>
<tr><td>
<input type="submit" value="Request transfer" />
</td></tr>
</table>
</form>
</td>
<td>
<script type="text/javascript">
fields = 1;
max_fields = 64;
function addInput() {
    if (fields < max_fields) {
        document.getElementById("srcfields").innerHTML += "<input type=text size=60 name=src value='' /><br />";
        fields += 1;
    } else {
        alert("Maximum " + max_fields + " source fields allowed!");
        document.form.add.disabled=true;
    }
}
</script>
<form name="addsrcform">
<input type="button" onclick="addInput(); return false;" name="add" value="Add another source field" />
</form>
</td>
</tr>
</table>
'''
        output_objects.append({'object_type': 'html_form', 'text'
                              : html})
        return (output_objects, returnvalues.OK)
    elif action in post_actions:
        action = 'transfer'
    else:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Invalid data transfer action: %s' % action})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not [src for src in src_list if src] or not dst:
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'src and dst parameters required for all data transfer'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_settings,
                                            client_dir)) + os.sep

    # TODO: improve to make ID unique
    transfer_requests = os.path.join(base_dir, "transfers")
    transfer_map = unpickle(transfer_requests, logger)
    if transfer_map == False:
        transfer_map = {}
    transfer_id = 'transfer-%d' % time.time()
    transfer_dict = transfer_map.get(transfer_id, {})
    if transfer_dict:
        output_objects.append({'object_type': 'error_text',
                               'text': 'Request already exists!!'})
        return (output_objects, returnvalues.CLIENT_ERROR)
    transfer_dict = {'transfer_id': transfer_id, 'action': action,
                     'protocol': protocol, 'fqdn': fqdn, 'port': port, 
                     'flags': flags, 'username': username, 'password': password,
                     'key':key, 'src': src_list, 'dst': dst}
    transfer_map[transfer_id] = transfer_dict
    pickle_ret = pickle(transfer_map, transfer_requests, logger)
    if not pickle_ret:
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Error saving data transfer request!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : '''Accepted request %s to transfer data in the
background. You can monitor the progress on this page.''' % transfer_id
                           })

    # TODO: insert table with transfer status

    return (output_objects, returnvalues.OK)
