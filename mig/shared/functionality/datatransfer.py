#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# datatransfer - import and export data in the backgroud
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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
from urllib import quote, urlencode

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.conf import get_resource_exe
from shared.defaults import all_jobs, job_output_dir, default_pager_entries, \
     csrf_field
from shared.fileio import read_tail
from shared.functional import validate_input_and_cert
from shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from shared.html import jquery_ui_js, man_base_js, man_base_html, \
     html_post_helper, themed_styles
from shared.init import initialize_main_variables, find_entry
from shared.parseflags import quiet
from shared.pwhash import make_digest
from shared.transferfunctions import build_transferitem_object, \
     build_keyitem_object, load_data_transfers, create_data_transfer, \
     update_data_transfer, delete_data_transfer, load_user_keys, \
     generate_user_key, delete_user_key


# Fields to fill on edit - note password is skipped on purpose for security!
edit_fields = ['transfer_id', 'protocol', 'fqdn', 'port', 'username',
               'compress', 'notify']
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

    # NOTE: we use transfer_pw rather than password to avoid interference with
    # user script curl password argument for the user key/cert
    defaults = {'action': ['show'], 'transfer_id': [''], 'protocol': [''],
                'fqdn':[''], 'port': [''], 'transfer_src': [''],
                'transfer_dst': [''], 'username': [''], 'transfer_pw': [''],
                'key_id': [''], 'exclude': [''], 'compress': [''],
                'notify': [''], 'flags': ['']}
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
    password = accepted['transfer_pw'][-1]
    key_id = accepted['key_id'][-1]
    exclude_list = accepted['exclude']
    notify = accepted['notify'][-1]
    compress = accepted['compress'][-1]
    flags = accepted['flags']

    logger.info('DEBUG: datatransfer %s from %s: %s' % (action, client_id,
                                                        accepted))

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
    use_compress = False
    if compress.lower() in ("true", "1", "yes", "on"):
        use_compress = True

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Background Data Transfers'

    # jquery support for tablesorter and confirmation on delete/redo:
    # datatransfer and key tables initially sorted by 0 (id) */
    
    datatransfer_spec = {'table_id': 'datatransferstable', 'pager_id':
                         'datatransfers_pager', 'sort_order': '[[0,0]]'}
    transferkey_spec = {'table_id': 'transferkeystable', 'pager_id':
                        'transferkeys_pager', 'sort_order': '[[0,0]]'}
    (add_import, add_init, add_ready) = man_base_js(configuration, 
                                                    [datatransfer_spec,
                                                     transferkey_spec])
    add_init += '''
    var fields = 0;
    var max_fields = 20;
    var src_input = "<label for=\'transfer_src\'>Source path(s)</label>";
    src_input += "<input id=\'src_FIELD\' type=text size=60 name=transfer_src value=\'PATH\' title=\'relative source path: local for exports and remote for imports\' />";
    src_input += "<input id=\'src_file_FIELD\' type=radio onclick=\'setSrcDir(FIELD, false);\' checked />Source file";
    src_input += "<input id=\'src_dir_FIELD\' type=radio onclick=\'setSrcDir(FIELD, true);\' />Source directory (recursive)";
    src_input += "<br />";
    var exclude_input = "<label for=\'exclude\'>Exclude path(s)</label>";
    exclude_input += "<input type=text size=60 name=exclude value=\'PATH\' title=\'relative path or regular expression to exclude\' />";
    exclude_input += "<br />";
    function addSource(path, is_dir) {
        if (path === undefined) {
            path = "";
        }
        if (is_dir === undefined) {
            is_dir = false;
        }
        if (fields < max_fields) {
            $("#srcfields").append(src_input.replace(/FIELD/g, fields).replace(/PATH/g, path));
            setSrcDir(fields, is_dir);
            fields += 1;
        } else {
            alert("Maximum " + max_fields + " source fields allowed!");
        }
    }
    function addExclude(path) {
        if (path === undefined) {
            path = "";
        }
        $("#excludefields").append(exclude_input.replace(/PATH/g, path));
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
    function doSubmit() {
        $("#submit-request-transfer").click();
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
    '''
    # Mangle ready handling to begin with dynamic init and end with tab init
    pre_ready = '''
        enableLogin("%s");
        ''' % init_login
    for src in src_list or ['']:
        pre_ready += '''
        addSource("%s", %s);
        ''' % (src, ("%s" % src.endswith('/')).lower())
    for exclude in exclude_list or ['']:
        pre_ready += '''
        addExclude("%s");
        ''' % exclude
    add_ready = '''
        %s
        %s
        /* NOTE: requires managers CSS fix for proper tab bar height */      
        $(".datatransfer-tabs").tabs();
        $("#logarea").scrollTop($("#logarea")[0].scrollHeight);
    ''' % (pre_ready, add_ready)
    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                             add_init, add_ready)
    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    output_objects.append({'object_type': 'header', 'text'
                           : 'Manage background data transfers'})

    if not configuration.site_enable_transfers:
        output_objects.append({'object_type': 'text', 'text':
                               '''Backgroung data transfers are disabled on
this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    logger.info('datatransfer %s from %s' % (action, client_id))

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid action "%s" (supported: %s)' % \
                               (action, ', '.join(valid_actions))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action in post_actions:
        if not safe_handler(configuration, 'post', op_name, client_id,
                            get_csrf_limit(configuration), accepted):
            output_objects.append(
                {'object_type': 'error_text', 'text': '''Only accepting
                CSRF-filtered POST requests to prevent unintended updates'''
                 })
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
else, so the public key can be inserted in your authorized_keys file as:
<br/>
<p>
<textarea class="publickey" rows="5" readonly="readonly">%s %%s</textarea>
</p>
''' % (configuration.short_title, restrict_str)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'datatransfer'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    if action in get_actions:
        datatransfers = []
        for (saved_id, transfer_dict) in transfer_map.items():
            transfer_item = build_transferitem_object(configuration,
                                                      transfer_dict)
            transfer_item['status'] = transfer_item.get('status', 'NEW')
            data_url = ''
            # NOTE: we need to urlencode any exotic chars in paths here
            if transfer_item['action'] == 'import':
                enc_path = quote(("%(dst)s" % transfer_item))
                data_url = "fileman.py?path=%s" % enc_path
            elif transfer_item['action'] == 'export':
                enc_paths = [quote(i) for i in transfer_item['src']]
                data_url = "fileman.py?path=" + ';path='.join(enc_paths)
            if data_url:
                transfer_item['viewdatalink'] = {
                    'object_type': 'link',
                    'destination': data_url,
                    'class': 'viewlink iconspace', 
                    'title': 'View local component of %s' % saved_id,
                    'text': ''}
            transfer_item['viewoutputlink'] = {
                'object_type': 'link',
                'destination': "fileman.py?path=transfer_output/%s/" % \
                saved_id,
                'class': 'infolink iconspace', 
                'title': 'View status files for %s' % saved_id,
                'text': ''}
            # Edit is just a call to self with fillimport set
            args = [('action', 'fill%(action)s' % transfer_dict),
                    ('key_id', '%(key)s' % transfer_dict),
                    ('transfer_dst', '%(dst)s' % transfer_dict)]
            for src in transfer_dict['src']:
                args.append(('transfer_src', src))
            for exclude in transfer_dict.get('exclude', []):
                args.append(('exclude', exclude))
            for field in edit_fields:
                val = transfer_dict.get(field, '')
                args.append((field, val))
            transfer_args = urlencode(args, True)
            transfer_item['edittransferlink'] = {
                'object_type': 'link',
                'destination': "%s.py?%s" % (target_op, transfer_args),
                'class': 'editlink iconspace', 
                'title': 'Edit or duplicate transfer %s' % saved_id,
                'text': ''}
            js_name = 'delete%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'transfer_id': saved_id,
                                       'action': 'deltransfer',
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            transfer_item['deltransferlink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" % \
                (js_name, 'Really remove %s?' % saved_id),
                'class': 'removelink iconspace', 'title': 'Remove %s' % \
                saved_id, 'text': ''}
            js_name = 'redo%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'transfer_id': saved_id,
                                       'action': 'redotransfer',
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            transfer_item['redotransferlink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" % \
                (js_name, 'Really reschedule %s?' % saved_id),
                'class': 'refreshlink iconspace', 'title': 'Reschedule %s' % \
                saved_id, 'text': ''}
            datatransfers.append(transfer_item)
        #logger.debug("found datatransfers: %s" % datatransfers)
        log_path = os.path.join(configuration.user_home, client_id_dir(client_id),
                                "transfer_output",
                                configuration.site_transfer_log)
        show_lines = 40
        log_lines = read_tail(log_path, show_lines, logger)
        available_keys = load_user_keys(configuration, client_id)
        if available_keys:
            key_note = ''
        else:
            key_note = '''No keys available - you can add a key for use in
transfers below.'''

        if action.endswith('import'):
            transfer_action = 'import'
        elif action.endswith('export'):
            transfer_action = 'export'
        else:
            transfer_action = 'unknown'

        import_checked, export_checked = 'checked', ''
        toggle_quiet, scroll_to_create = '', ''
        if action in ['fillimport', 'fillexport']:
            if quiet(flags):
                toggle_quiet = '''
<script>
 $("#wrap-tabs").hide();
 $("#quiet-mode-content").show();
</script>
'''
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
                import_checked = ''

        fill_helpers= {'import_checked': import_checked, 'export_checked':
                       export_checked, 'anon_checked': anon_checked,
                       'pw_checked': pw_checked, 'key_checked': key_checked,
                       'transfer_id': transfer_id, 'protocol': protocol,
                       'fqdn': fqdn, 'port': port, 'username': username,
                       'password': password, 'key_id': key_id, 
                       'transfer_src_string': ', '.join(src_list),
                       'transfer_src': src_list, 'transfer_dst': dst,
                       'exclude': exclude_list, 'compress': use_compress,
                       'notify': notify, 'toggle_quiet': toggle_quiet,
                       'scroll_to_create': scroll_to_create,
                       'transfer_action': transfer_action,
                       'form_method': form_method, 'csrf_field': csrf_field,
                       'csrf_limit': csrf_limit, 'target_op': target_op,
                       'csrf_token': csrf_token}

        # Make page with manage transfers tab and manage keys tab

        output_objects.append({'object_type': 'html_form', 'text':  '''
    <div id="quiet-mode-content" class="hidden">
        <p>
        Accept data %(transfer_action)s of %(transfer_src_string)s from
        %(protocol)s://%(fqdn)s:%(port)s/ into %(transfer_dst)s ?
        </p>
        <p>
            <input type=button onClick="doSubmit();"
            value="Accept %(transfer_action)s" />
        </p>
    </div>
    <div id="wrap-tabs" class="datatransfer-tabs">
<ul>
<li><a href="#transfer-tab">Manage Data Transfers</a></li>
<li><a href="#keys-tab">Manage Transfer Keys</a></li>
</ul>
''' % fill_helpers})

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
<textarea id="logarea" class="fillwidth" rows=5 readonly="readonly">%s</textarea>
''' % (''.join(log_lines))})
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
<form method="%(form_method)s" action="%(target_op)s.py"
    onSubmit="return beforeSubmit();">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<fieldset id="transferbox">
<table id="createtransfer" class="addexttransfer">
<tr><td>
<label for="action">Action</label>
<input type=radio name=action %(import_checked)s value="import" />import data
<input type=radio name=action %(export_checked)s value="export" />export data
</td></tr>
<tr><td>
<label for="transfer_id">Optional Transfer ID / Name </label>
<input type=text size=60 name=transfer_id value="%(transfer_id)s"
    pattern="[a-zA-Z0-9._-]*"
    title="Optional ID string containing only ASCII letters and digits possibly with separators like hyphen, underscore and period" />
</td></tr>
<tr><td>
<label for="protocol">Protocol</label>
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
</td></tr>
<tr><td>
<label for="fqdn">Host and port</label>
<input type=text size=37 name=fqdn value="%(fqdn)s" required
    pattern="[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)+"
    title="A fully qualified domain name or Internet IP address for the remote location"/>
<input id="port_input" type=number step=1 min=1 max=65535 name=port
    value="%(port)s" required />
</td></tr>
<tr><td>
<label for="">Login method</label>
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
<label for="username">Username</label>
<input id="username" type=text size=60 name=username value="%(username)s"
    pattern="[a-zA-Z0-9._-]*"
    title="Optional username used to login on the remote site, if required" />
<br/>
<span id="password_entry">
<label for="transfer_pw">Password</label>
<input id="password" type=password size=60 name=transfer_pw value="" />
</span>
<span id="key_entry">
<label for="key_id">Key</label>
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
<div id="srcfields">
<!-- NOTE: automatically filled by addSource function -->
</div>
<input id="addsrcbutton" type="button" onclick="addSource(); return false;"
    value="Add another source field" />
</td></tr>
<tr><td>
<label for="transfer_dst">Destination path</label>
<input id=\'dst_0\' type=text size=60 name=transfer_dst
    value="%(transfer_dst)s" required
    title="relative destination path: local for imports and remote for exports" />
<input id=\'dst_dir_0\' type=radio checked />Destination directory
<input id=\'dst_file_0\' type=radio disabled />Destination file<br />
</td></tr>
<tr><td>
<div id="excludefields">
<!-- NOTE: automatically filled by addExclude function -->
</div>
<input id="addexcludebutton" type="button" onclick="addExclude(); return false;"
    value="Add another exclude field" />
</td></tr>
<tr><td>
<label for="compress">Enable compression (leave unset except for <em>slow</em> sites)</label>
<input type=checkbox name=compress>
</td></tr>
<tr><td>
<label for="notify">Optional notify on completion (e.g. email address)</label>
<input type=text size=60 name=notify value=\'%(notify)s\'>
</td></tr>
<tr><td>
<span>
<input id="submit-request-transfer" type=submit value="Request transfer" />
<input type=reset value="Clear" />
</span>
</td></tr>
</table>
</fieldset>
</form>
</td>
</tr>
</table>
%(toggle_quiet)s
%(scroll_to_create)s
'''
        output_objects.append({'object_type': 'html_form', 'text'
                              : transfer_html % fill_helpers})
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
<form method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<table class="managetransferkeys">
<tr><td>
'''
        transferkeys = []
        for key_dict in available_keys:
            key_item = build_keyitem_object(configuration, key_dict)
            saved_id = key_item['key_id']
            js_name = 'delete%s' % hexlify(saved_id)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'key_id': saved_id,
                                       'action': 'delkey',
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            key_item['delkeylink'] = {
                'object_type': 'link', 'destination':
                "javascript: confirmDialog(%s, '%s');" % \
                (js_name, 'Really remove %s?' % saved_id),
                'class': 'removelink iconspace', 'title': 'Remove %s' % \
                saved_id, 'text': ''}
            transferkeys.append(key_item)

        output_objects.append({'object_type': 'table_pager',
                               'id_prefix': 'transferkeys_',
                               'entry_name': 'keys', 
                               'default_entries': default_pager_entries})
        output_objects.append({'object_type': 'transferkeys', 'transferkeys'
                               : transferkeys})
        
        key_html += '''
Please copy the public key to your ~/.ssh/authorized_keys or
~/.ssh/authorized_keys2 file on systems where you want to login with the
corresponding key.<br/>
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
<input type=text size=60 name=key_id value="" required pattern="[a-zA-Z0-9._-]+"
    title="internal name for the key when used in transfers. I.e. letters and digits separated only by underscores, periods and hyphens" />
<br/>
<input type=submit value="Generate key" />
</td></tr>
</table>
</form>
''' % (restrict_template % 'ssh-rsa AAAAB3NzaC...', configuration.short_title)
        output_objects.append({'object_type': 'html_form', 'text'
                              : key_html % fill_helpers})
        output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})
    
        output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})
        return (output_objects, returnvalues.OK)
    elif action in transfer_actions:
        # NOTE: all path validation is done at run-time in grid_transfers
        transfer_dict = transfer_map.get(transfer_id, {})
        if action == 'deltransfer':
            if transfer_dict is None:
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': 'existing transfer_id is required for delete'})
                return (output_objects, returnvalues.CLIENT_ERROR)
            (save_status, _) = delete_data_transfer(configuration, client_id,
                                                    transfer_id, transfer_map)
            desc = "delete"
        elif action == 'redotransfer':
            if transfer_dict is None:
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': 'existing transfer_id is required for reschedule'
                     })
                return (output_objects, returnvalues.CLIENT_ERROR)
            transfer_dict['status'] = 'NEW'
            (save_status, _) = update_data_transfer(configuration, client_id,
                                                    transfer_dict,
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
                     'text': 'transfer_src and transfer_dst parameters '
                     'required for all data transfers!'})
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
                 'key': key_id, 'src': src_list, 'dst': dst,
                 'exclude': exclude_list, 'compress': use_compress,
                 'notify': notify, 'status': 'NEW'})
            (save_status, _) = create_data_transfer(configuration, client_id,
                                                    transfer_dict,
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
        logger.debug('datatransfer %s from %s done: %s' % (action, client_id,
                                                          transfer_dict))
    elif action in key_actions:
        if action == 'generatekey':
            (gen_status, pub) = generate_user_key(configuration, client_id, key_id)
            if gen_status:
                output_objects.append({'object_type': 'html_form', 'text': '''
Generated new key with name %s and associated public key:<br/>
<textarea class="publickey" rows="5" readonly="readonly">%s</textarea>
<p>
Please copy it to your ~/.ssh/authorized_keys or ~/.ssh/authorized_keys2 file
on the host(s) where you want to use this key for background transfer login.
<br/>
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
remove the public key from your ~/.ssh/authorized_keys* files on any hosts
where you may have previously added it.
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
