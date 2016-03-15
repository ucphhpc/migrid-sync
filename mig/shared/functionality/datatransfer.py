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
post_actions = ['put', 'get', 'move']
valid_actions = get_actions + post_actions

def signature():
    """Signature of the main function"""

    defaults = {'protocol': [], 'action': ['show'], 'src':[],
                'dst': [''], 'username': [''], 'password': [''],
                'key': ['']}
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
    src = accepted['src']
    dst = accepted['dst'][-1]
    username = accepted['username'][-1]
    password = accepted['password'][-1]
    key = accepted['key'][-1]
    
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s data import/export' % configuration.short_title
    output_objects.append({'object_type': 'header', 'text'
                           : 'Manage background data transfers'})

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid action "%s" (supported: %s)' % \
                               (action, ', '.join(valid_actions))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action in post_actions and not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
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
Action:<br />
<input type=radio name=action checked value="import" />import data
<input type=radio name=action value="export" />export data
<input type=radio name=action value="move" />move data
</td></tr>
<tr><td>
Protocol:<br />
<select name=protocol>
<option value="https" />
<option value="http" />
<option value="sftp" />
<option value="ftps" />
</select>
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

    output_objects.append({'object_type': 'text', 'text'
                          : 'Requesting data transfer in the background'
                           })

    if not src or not dst:
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'src and dst parameters required for all data transfer'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_transfers,
                                            client_dir)) + os.sep

    # TODO: improve to make ID unique
    transfer_id = '%d.req' % time.time
    transfer_request = os.path.join(base_dir, transfer_id)
    transfer_dict = {}
    if os.path.isfile(transfer_request):
        output_objects.append({'object_type': 'error_text',
                               'text': 'Request already exists!!'})
        return (output_objects, returnvalues.CLIENT_ERROR)
    pickle_ret = pickle(transfer_dict, transfer_request, logger)
    if not pickle_ret:
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Error saving data transfer request!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    return (output_objects, returnvalues.OK)
