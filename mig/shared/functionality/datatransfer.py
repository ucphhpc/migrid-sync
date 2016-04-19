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

from binascii import hexlify
import glob
import os
import datetime
import socket
import time

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.conf import get_resource_exe
from shared.transferfunctions import build_transferitem_object, \
     build_keyitem_object, load_data_transfers, create_data_transfer, \
     delete_data_transfer, load_user_keys, generate_user_key, delete_user_key
from shared.defaults import all_jobs, job_output_dir, default_pager_entries, \
     transfers_log_name
from shared.fileio import read_tail
from shared.functional import validate_input_and_cert
from shared.handlers import correct_handler
from shared.html import html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.pwhash import make_digest
from shared.validstring import valid_user_path


get_actions = ['show', 'fillimport', 'fillexport']
transfer_actions = ['import', 'export', 'deltransfer', 'redotransfer']
# TODO: add these internal data shuffling targets on a separate tab without
#address and creds
#shuffling_actions = ['move', 'copy', 'unpack', 'pack', 'remove']
shuffling_actions = []
key_actions = ['generatekey', 'delkey']
post_actions = transfer_actions + shuffling_actions + key_actions
valid_actions = get_actions + post_actions
# TODO: implement scp in backend and enable here?
valid_proto = [("http", "HTTP"), ("https", "HTTPS"), ("ftp", "FTP"),
               ("ftps", "FTPS"), ("webdav", "WebDAV"), ("webdavs", "WebDAVS"),
               ("sftp", "SFTP"), ("rsyncssh", "RSYNC over SSH"),
               ("rsyncd", "RSYNC daemon")]
valid_proto_map = dict(valid_proto)
warn_anon = [i for (i, _) in valid_proto if not i in ('http', 'https', 'ftp',
                                                      'rsyncd')]
warn_key = [i for (i, _) in valid_proto if not i in ('sftp', 'rsyncssh')]

# TODO: consider adding a start time or cron-like field to transfers

def signature():
    """Signature of the main function"""

    defaults = {'action': ['show'], 'transfer_id': [''], 'protocol': [''],
                'fqdn':[''], 'port': [''], 'transfer_src':[''],
                'transfer_dst': [''], 'username': [''], 'password': [''],
                'key_id': [''], 'notify': [''], 'flags': ['']}
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
    transfer_id = accepted['transfer_id'][-1]
    protocol = accepted['protocol'][-1]
    fqdn = accepted['fqdn'][-1]
    port = accepted['port'][-1]
    src_list = accepted['transfer_src']
    dst = accepted['transfer_dst'][-1]
    username = accepted['username'][-1]
    password = accepted['password'][-1]
    key_id = accepted['key_id'][-1]
    notify = accepted['notify'][-1]
    flags = accepted['flags']

    anon_checked, pw_checked, key_checked = '', '', ''
    if username:
        if key_id:
            key_checked = 'checked'
            init_login = "key"
        else:
            pw_checked = 'checked'
            init_login = "password"
    else:
        anon_checked = 'checked'
        init_login = "anonymous"

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Background Data Transfers'

    # jquery support for tablesorter and confirmation on delete/redo:

    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] += '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>

<script type="text/javascript">
    var fields = 0;
    var max_fields = 20;
    var src_input = "<input id=\'src_FIELD\' type=text size=60 name=transfer_src value=\'\' />";
    src_input += "<input id=\'src_file_FIELD\' type=radio onclick=\'setSrcDir(FIELD, false);\' checked />Source file";
    src_input += "<input id=\'src_dir_FIELD\' type=radio onclick=\'setSrcDir(FIELD, true);\' />Source directory (recursive)";
    src_input += "<br />";
    function addSource() {
        if (fields < max_fields) {
            $("#srcfields").append(src_input.replace(/FIELD/g, fields));
            fields += 1;
        } else {
            alert("Maximum " + max_fields + " source fields allowed!");
        }
    }
    function setDir(target, field_no, is_dir) {
        var id_prefix = "#"+target+"_";
        var input_id = id_prefix+field_no;
        var file_id = id_prefix+"file_"+field_no;
        var dir_id = id_prefix+"dir_"+field_no;
        var value = $(input_id).val();
        $(file_id).removeAttr("checked");
        $(dir_id).removeAttr("checked");
        if (is_dir) {
            $(dir_id).prop("checked", "checked");
            if(value.substr(-1) != "/") {
                value += "/";
            }
        } else {
            $(file_id).prop("checked", "checked");
            if(value.substr(-1) == "/") {
                value = value.substr(0, value.length - 1);
            }
        }
        $(input_id).val(value);
        return false;
    }
    function setSrcDir(field_no, is_dir) {
        return setDir("src", field_no, is_dir);
    }
    function setDstDir(field_no, is_dir) {
        return setDir("dst", field_no, is_dir);
    }
    function refreshSrcDir(field_no) {
        var dir_id = "#src_dir_"+field_no;
        var is_dir = $(dir_id).prop("checked");
        return setSrcDir(field_no, is_dir);
    }
    function refreshDstDir(field_no) {
        var dir_id = "#dst_dir_"+field_no;
        var is_dir = $(dir_id).prop("checked");
        return setDstDir(field_no, is_dir);
    }
    function setDefaultPort() {
        port_map = {"http": 80, "https": 443, "sftp": 22, "scp": 22, "ftp": 21,
                    "ftps": 21, "webdav": 80, "webdavs": 443, "rsyncssh": 22,
                    "rsyncd": 873};
        var protocol = $("#protocol_select").val();
        var port = port_map[protocol]; 
        if (port != undefined) {
            $("#port_input").val(port);
        } else {
            alert("no default port provided for "+protocol);
        }
    }
    function beforeSubmit() {
        for(var i=0; i < fields; i++) {
            refreshSrcDir(i);
        }
        refreshDstDir(0);
        // Proceed with submit
        return true;
    }
    function enableLogin(method) {
        $("#anonymous_choice").removeAttr("checked");
        $("#userpassword_choice").removeAttr("checked");
        $("#userkey_choice").removeAttr("checked");
        $("#username").prop("disabled", false);
        $("#password").prop("disabled", true);
        $("#key").prop("disabled", true);
        $("#login_fields").show();
        $("#password_entry").hide();
        $("#key_entry").hide();
        
        if (method == "password") {
            $("#userpassword_choice").prop("checked", "checked");
            $("#password").prop("disabled", false);
            $("#password_entry").show();
        } else if (method == "key") {
            $("#userkey_choice").prop("checked", "checked");
            $("#key").prop("disabled", false);
            $("#key_entry").show();
        } else {
            $("#anonymous_choice").prop("checked", "checked");
            $("#username").prop("disabled", true);
            $("#login_fields").hide();
        }
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

        /* init create dialog */
        enableLogin("%s");

        addSource();

        /* setup table with tablesorter initially sorted by 0 (id) */
        var sortOrder = [[0,0]];
        $("#datatransferstable").tablesorter({widgets: ["zebra", "saveSort"],
                                        sortList:sortOrder
                                        })
                               .tablesorterPager({ container: $("#datatransfers_pager"),
                                        size: %s
                                        });

        /* setup table with tablesorter initially sorted by 0 (id) */
        var sortOrder = [[0,0]];
        $("#transferkeystable").tablesorter({widgets: ["zebra", "saveSort"],
                                        sortList:sortOrder
                                        })
                               .tablesorterPager({ container: $("#transferkeys_pager"),
                                        size: %s
                                        });

          $(".datatransfer-tabs").tabs();
          $("#logarea").scrollTop($("#logarea")[0].scrollHeight);
          $("#datatransfers_pagerrefresh").click(function() { location.reload(); });
          $("#transferkeys_pagerrefresh").click(function() { location.reload(); });
    });
</script>
''' % (init_login, default_pager_entries, default_pager_entries)
    output_objects.append({'object_type': 'header', 'text'
                           : 'Manage background data transfers'})

    if not configuration.site_enable_transfers:
        output_objects.append({'object_type': 'text', 'text':
                               '''Backgroung data transfers are disabled on
this site.
Please contact the Grid admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="40" rows="4" id="confirm_input"
       style="display:none;"></textarea>
 </div>
'''                       })

    logger.info('datatransfer %s from %s' % (action, client_id))

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

    (load_status, transfer_map) = load_data_transfers(configuration, client_id)
    if not load_status:
        transfer_map = {}

    restrict_list = []
    for from_fqdn in configuration.site_transfers_from:
        restrict_list += [from_fqdn, socket.gethostbyname(from_fqdn)]
    restrict_str = 'from="%s",no-pty,' % ','.join(restrict_list)
    restrict_str += 'no-port-forwarding,no-agent-forwarding,no-X11-forwarding'
    restrict_template = '''
As usual it is a good security measure to prepend a <em>from</em> restriction
when you know the key will only be used from a single location.<br/>
In this case the keys will only ever be used from %s and will not need much
else, so the public key can inserted in authorized_keys as:<br/>
<p>
<textarea class="publickey" rows="5" readonly="readonly">%s %%s</textarea>
</p>
''' % (configuration.short_title, restrict_str)

    if action in get_actions:
        datatransfers = []
        for (saved_id, transfer_dict) in transfer_map.items():
            transfer_item = build_transferitem_object(configuration,
                                                      transfer_dict)
            transfer_item['status'] = transfer_item.get('status', 'NEW')            
            transfer_item['viewtransferlink'] = {
                'object_type': 'link',
                'destination': "fileman.py?path=transfer_output/%s/" % \
                saved_id,
                'class': 'infolink', 
                'title': 'View data transfer %s status files' % saved_id,
                'text': ''}
            js_name = 'delete%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, 'datatransfer.py',
                                      {'transfer_id': saved_id,
                                       'action': 'deltransfer'})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            transfer_item['deltransferlink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" % \
                (js_name, 'Really remove %s?' % saved_id),
                'class': 'removelink', 'title': 'Remove %s' % \
                saved_id, 'text': ''}
            js_name = 'redo%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, 'datatransfer.py',
                                      {'transfer_id': saved_id,
                                       'action': 'redotransfer'})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            transfer_item['redotransferlink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" % \
                (js_name, 'Really reschedule %s?' % saved_id),
                'class': 'refreshlink', 'title': 'Reschedule %s' % \
                saved_id, 'text': ''}
            datatransfers.append(transfer_item)
        #logger.debug("found datatransfers: %s" % datatransfers)
        log_path = os.path.join(configuration.user_home, client_id_dir(client_id),
                                "transfer_output", transfers_log_name)
        show_lines = 40
        log_lines = read_tail(log_path, show_lines, logger)
        available_keys = load_user_keys(configuration, client_id)
        if available_keys:
            key_note = ''
        else:
            key_note = '''No keys available - you can add a key for use in
transfers below.'''

        import_checked, export_checked, scroll_to_create = '', '', ''
        if action in ['fillimport', 'fillexport']:
            scroll_to_create = '''
<script>
 $("html, body").animate({
  scrollTop: $("#createtransfer").offset().top
   }, 2000);
</script>
            '''
            if action == 'fillimport':
                import_checked = 'checked'
            elif action == 'fillexport':
                export_checked = 'checked'
                
        fill_helper= {'import_checked': import_checked, 'export_checked':
                      export_checked, 'anon_checked': anon_checked,
                      'pw_checked': pw_checked, 'key_checked': key_checked,
                      'transfer_id': transfer_id, 'protocol': protocol,
                      'fqdn': fqdn, 'port': port, 'username': username,
                      'password': password, 'key_id': key_id, 
                      'transfer_src': src_list, 'transfer_dst': dst,
                      'notify': notify, 'scroll_to_create': scroll_to_create}
        
        # Make page with manage transfers tab and manage keys tab

        output_objects.append({'object_type': 'html_form', 'text':  '''
    <div id="wrap-tabs" class="datatransfer-tabs">
<ul>
<li><a href="#transfer-tab">Manage Data Transfers</a></li>
<li><a href="#keys-tab">Manage Transfer Keys</a></li>
</ul>
'''})

        # Display external transfers, log and form to add new ones
    
        output_objects.append({'object_type': 'html_form', 'text':  '''
<div id="transfer-tab">
'''})

        output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'External Data Transfers'})
        output_objects.append({'object_type': 'table_pager',
                               'id_prefix': 'datatransfers_',
                               'entry_name': 'transfers',
                               'default_entries': default_pager_entries})
        output_objects.append({'object_type': 'datatransfers', 'datatransfers'
                              : datatransfers})
        output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Latest Transfer Results'})
        output_objects.append({'object_type': 'html_form', 'text': '''
<textarea id="logarea" rows=5 cols=200  readonly="readonly">%s</textarea>''' \
                               % (''.join(log_lines))})
        output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Create External Data Transfer'})
        transfer_html = '''
<table class="addexttransfer">
<tr><td>
Fill in the import/export data transfer details below to request a new
background data transfer task.<br/>  
Source must be a path without wildcard characters and it must be specifically
pointed out if the src is a directory. In that case recursive transfer will
automatically be used and otherwise the src is considered a single file, so it
will fail if that is not the case.<br/>  
Destination is a single location directory to transfer the data to. It is
considered in relation to your user home for <em>import</em> requests. Source
is similarly considered in relation to your user home in <em>export</em>
requests.<br/>
Destination is a always handled as a directory path to transfer source files
into.<br/>
<form method="post" action="datatransfer.py" onSubmit="return beforeSubmit();">
<table id="createtransfer" class="addexttransfer">
<tr><td>
<input type=radio name=action %(import_checked)s value="import" />import data
<input type=radio name=action %(export_checked)s value="export" />export data
</td></tr>
<tr><td>
Transfer ID:<br />
<input type=text size=60 name=transfer_id value="%(transfer_id)s" />
</td></tr>
<tr><td>
<select id="protocol_select" name="protocol" onblur="setDefaultPort();">
'''
        # select requested protocol
        for (key, val) in valid_proto:
            if protocol == key:
                selected = 'selected'
            else:
                selected = ''
            transfer_html += '<option %s value="%s">%s</option>' % \
                             (selected, key, val)
        transfer_html += '''
</select>
Host:
<input type=text size=30 name=fqdn value="%(fqdn)s" />
Port:
<input id="port_input" type=text size=4 name=port value="%(port)s" />
</td></tr>
<tr><td>
<input id="anonymous_choice" type=radio %(anon_checked)s
    onclick="enableLogin(\'anonymous\');" />
anonymous access
<input id="userpassword_choice" type=radio %(pw_checked)s
    onclick="enableLogin(\'password\');" />
login with password
<input id="userkey_choice" type=radio %(key_checked)s
    onclick="enableLogin(\'key\');" />
login with key
</td></tr>
<tr id="login_fields" style="display: none;"><td>
Username:<br />
<input id="username" type=text size=60 name=username value="%(username)s" />
<br/>
<span id="password_entry">
Password:<br />
<input id="password" type=password size=60 name=password value="" />
</span>
<span id="key_entry">
Key:<br />
<select id="key" name=key_id />
'''
        # select requested key
        for key_dict in available_keys:
            if key_dict['key_id'] == key_id:
                selected = 'selected'
            else:
                selected = ''
            transfer_html += '<option %s value="%s">%s</option>' % \
                             (selected, key_dict['key_id'], key_dict['key_id'])
            selected = ''
        transfer_html += '''
</select> %s
''' % key_note
        transfer_html += '''
</span>
</td></tr>
<tr><td>
Source path(s):<br />
<div id="srcfields">
<!-- NOTE: automatically filled by addSource function -->
</div>
<input id="addsrcbutton" type="button" onclick="addSource(); return false;"
    value="Add another source field" />
</td></tr>
<tr><td>
Destination path:<br />
<input id=\'dst_0\' type=text size=60 name=transfer_dst value="%(transfer_dst)s" />
<input id=\'dst_dir_0\' type=radio checked />Destination directory
<input id=\'dst_file_0\' type=radio disabled />Destination file<br />
</td></tr>
<tr><td>
Notify on completion (e.g. email address):<br />
<input type=text size=60 name=notify value=\'%(notify)s\'>
</td></tr>
<tr><td>
<span>
<input type=submit value="Request transfer" />
<input type=reset value="Clear" />
</span>
</td></tr>
</table>
</form>
</td>
</tr>
</table>
%(scroll_to_create)s
'''
        output_objects.append({'object_type': 'html_form', 'text'
                              : transfer_html % fill_helper})
        output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})

        # Display key management

        output_objects.append({'object_type': 'html_form', 'text':  '''
<div id="keys-tab">
'''})
        output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Manage Data Transfer Keys'})
        key_html = '''
<form method="post" action="datatransfer.py">
<table class="managetransferkeys">
<tr><td>
'''
        transferkeys = []
        for key_dict in available_keys:
            key_item = build_keyitem_object(configuration, key_dict)
            saved_id = key_item['key_id']
            js_name = 'delete%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, 'datatransfer.py',
                                      {'key_id': saved_id,
                                    'action': 'delkey'})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            key_item['delkeylink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" % \
                (js_name, 'Really remove %s?' % saved_id),
                'class': 'removelink', 'title': 'Remove %s' % \
                saved_id, 'text': ''}
            transferkeys.append(key_item)

        output_objects.append({'object_type': 'table_pager',
                               'id_prefix': 'transferkeys_',
                               'entry_name': 'keys', 
                               'default_entries': default_pager_entries})
        output_objects.append({'object_type': 'transferkeys', 'transferkeys'
                               : transferkeys})
        
        key_html += '''
Please copy the public key to your ~/.ssh/authorized_keys file on systems where
you want to login with the corresponding key.<br/>
%s
</td></tr>
<tr><td>
Select a name below to create a new key for use in future transfers. The key is
generated and stored in a private storage area on %s, so that only the transfer
service can access and use it for your transfers.
</td></tr>
<tr><td>
<input type=hidden name=action value="generatekey" />
Key name:<br/>
<input type=text size=60 name=key_id value="" />
<br/>
<input type=submit value="Generate key" />
</td></tr>
</table>
</form>
''' % (restrict_template % 'ssh-rsa AAAAB3NzaC...', configuration.short_title)
        output_objects.append({'object_type': 'html_form', 'text'
                              : key_html})
        output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})
    
        output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})
        return (output_objects, returnvalues.OK)
    elif action in transfer_actions:
        transfer_dict = transfer_map.get(transfer_id, {})
        if action == 'deltransfer':
            if transfer_dict is None:
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': 'existing transfer_id is required for delete'})
                return (output_objects, returnvalues.CLIENT_ERROR)
            (save_status, _) = delete_data_transfer(transfer_id, client_id,
                                                    configuration,
                                                    transfer_map)
            desc = "delete"
        elif action == 'redotransfer':
            if transfer_dict is None:
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': 'existing transfer_id is required for reschedule'
                     })
                return (output_objects, returnvalues.CLIENT_ERROR)
            transfer_dict['status'] = 'NEW'
            (save_status, _) = create_data_transfer(transfer_dict, client_id,
                                                    configuration,
                                                    transfer_map)
            desc = "reschedule"
        else:
            if not fqdn:
                output_objects.append(
                    {'object_type': 'error_text', 'text'
                     : 'No host address provided!'})
                return (output_objects, returnvalues.CLIENT_ERROR)
            if not [src for src in src_list if src] or not dst:
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': 'transfer_src and transfer_dst parameters required for all'
                     'data transfers!'})
                return (output_objects, returnvalues.CLIENT_ERROR)
            if protocol == "rsyncssh" and not key_id:
                output_objects.append(
                    {'object_type': 'error_text', 'text'
                     : 'RSYNC over SSH is only supported with key!'})
                return (output_objects, returnvalues.CLIENT_ERROR)
            if not password and not key_id and protocol in warn_anon:
                output_objects.append(
                    {'object_type': 'warning', 'text': '''
%s transfers usually require explicit authentication with your credentials.
Proceeding as requested with anonymous login, but the transfer is likely to
fail.''' % valid_proto_map[protocol]})
            if key_id and protocol in warn_key:
                output_objects.append(
                    {'object_type': 'warning', 'text': '''
%s transfers usually only support authentication with username and password
rather than key. Proceeding as requested, but the transfer is likely to
fail if it really requires login.''' % valid_proto_map[protocol]})

            # Make pseudo-unique ID based on msec time since epoch if not given
            if not transfer_id:
                transfer_id = "transfer-%d" % (time.time() * 1000)
            if transfer_dict:
                desc = "update"
            else:
                desc = "create"

            if password:
                # We don't want to store password in plain text on disk
                password_digest = make_digest('datatransfer', client_id,
                                              password,
                                              configuration.site_digest_salt)
            else:
                password_digest = ''
            transfer_dict.update(
                {'transfer_id': transfer_id, 'action': action,
                 'protocol': protocol, 'fqdn': fqdn, 'port': port, 
                 'username': username, 'password_digest': password_digest,
                 'key': key_id, 'src': src_list, 'dst': dst, 'notify': notify,
                 'status': 'NEW'})
            (save_status, _) = create_data_transfer(transfer_dict, client_id,
                                                    configuration,
                                                    transfer_map)
        if not save_status:
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : 'Error in %s data transfer %s: '% (desc, transfer_id) + \
                 'save updated transfers failed!'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        output_objects.append({'object_type': 'text', 'text'
                               : '%sd transfer request %s.' % (desc.title(),
                                                           transfer_id)
                               })
        if action != 'deltransfer':
            output_objects.append({
                'object_type': 'link',
                'destination': "fileman.py?path=transfer_output/%s/" % transfer_id,
                'title': 'Transfer status and output',
                'text': 'Transfer status and output folder'})
            output_objects.append({'object_type': 'text', 'text': '''
Please note that the status files only appear after the transfer starts, so it
may be empty now.
'''})
    elif action in key_actions:
        if action == 'generatekey':
            (gen_status, pub) = generate_user_key(configuration, client_id, key_id)
            if gen_status:
                output_objects.append({'object_type': 'html_form', 'text': '''
Generated new key with name %s and associated public key:<br/>
<textarea class="publickey" rows="5" readonly="readonly">%s</textarea>
<p>
Please copy it to your ~/.ssh/authorized_keys file on the host(s) where you
want to use this key for background transfer login.<br/>
%s
</p>
''' % (key_id, pub, restrict_template % pub)})
            else:
                output_objects.append({'object_type': 'error_text', 'text': '''
Key generation for name %s failed with error: %s''' % (key_id, pub)})
                return (output_objects, returnvalues.CLIENT_ERROR)
        elif action == 'delkey':
            pubkey = '[unknown]'
            available_keys = load_user_keys(configuration, client_id)
            for key_dict in available_keys:
                if key_dict['key_id'] == key_id:
                    pubkey = key_dict.get('public_key', pubkey)
            (del_status, msg) = delete_user_key(configuration, client_id, key_id)
            if del_status:
                output_objects.append({'object_type': 'html_form', 'text': '''
<p>
Deleted the key "%s" and the associated public key:<br/>
</p>
<textarea class="publickey" rows="5" readonly="readonly">%s</textarea>
<p>
You will no longer be able to use it in your data transfers and can safely
remove the public key from your ~/.ssh/authorized_keys file on any hosts where
you may have previously added it.
</p>
''' % (key_id, pubkey)})
            else:
                output_objects.append({'object_type': 'error_text', 'text': '''
Key removal for name %s failed with error: %s''' % (key_id, msg)})
                return (output_objects, returnvalues.CLIENT_ERROR)
    else:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Invalid data transfer action: %s' % action})
        return (output_objects, returnvalues.CLIENT_ERROR)
                
    output_objects.append({'object_type': 'link',
                           'destination': 'datatransfer.py',
                           'text': 'Return to data transfers overview'})
    return (output_objects, returnvalues.OK)

