#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migadmin - admin control panel with daemon status monitor
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

"""MiG administrators page with basic user management, daemon status, site
status and configuration view.
"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.accountreq import build_accountreqitem_object, \
    list_account_reqs, get_account_req, accept_account_req, \
    peer_account_req, reject_account_req
from mig.shared.base import force_utf8_rec
from mig.shared.defaults import default_pager_entries, csrf_field, \
    keyword_any, keyword_auto, AUTH_CERTIFICATE, AUTH_OPENID_V2, \
    AUTH_OPENID_CONNECT
from mig.shared.fileio import send_message_to_grid_script, read_tail, listdir
from mig.shared.findtype import is_admin
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.html import man_base_js, man_base_html, html_post_helper
from mig.shared.httpsclient import detect_client_auth
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.safeeval import subprocess_popen, subprocess_pipe, \
    subprocess_stdout
from mig.shared.serial import load

grid_actions = {'reloadconfig': 'RELOADCONFIG',
                'showqueued': 'JOBQUEUEINFO',
                'showexecuting': 'EXECUTINGQUEUEINFO',
                'showdone': 'DONEQUEUEINFO',
                'dropqueued': 'DROPQUEUED',
                'dropexecuting': 'DROPEXECUTING',
                'dropdone': 'DROPDONE',
                }
accountreq_actions = ['createaccountreq', 'peeraccountreq', 'rejectaccountreq',
                      'reloadaccountreq']

all_actions = list(grid_actions) + accountreq_actions
view_ops, act_ops = [''], []
for entry in all_actions:
    if entry.startswith('show'):
        view_ops.append(entry)
    else:
        act_ops.append(entry)


def signature():
    """Signature of the main function"""

    defaults = {'action': [''], 'request_text': [''], 'req_id': [], 'job_id': [],
                'lines': [20]}
    return ['html_form', defaults]


def format_stats(filename, stats):
    """Helper to format stats dict for human display"""
    # TODO: handle all dict contents and polish display
    html = ''
    html += '''<h3>Saved %s</h3>
<h4>Disk Use</h4>
''' % filename
    for parts in stats['disk']['use']:
        html += '''<p>
'''
        html += ' '.join(parts)
        html += '''
</p>
'''
    html += '''
<h4>Total</h4>
'''
    for (key, val) in stats['totals'].items():
        html += '''<p>
%s: %s
</p>
''' % (key, val)
    html += '''
<h4>Weekly</h4>
'''
    for (key, val) in stats['weekly'].items():
        html += '''<p>
%s: %s
</p>
''' % (key, val)
    return html


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
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
    action = accepted['action'][-1].strip()
    request_text = accepted['request_text'][-1]
    req_list = accepted['req_id']
    job_list = accepted['job_id']
    lines = int(accepted['lines'][-1])

    meta = '''<meta http-equiv="refresh" content="%s" />
''' % configuration.sleep_secs
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s administration panel' % configuration.short_title
    title_entry['container_class'] = 'fillwidth',
    title_entry['meta'] = meta

    # jquery support for tablesorter and confirmation on "remove"
    # table initially sorted by col. 9 (created)
    # Hard-wire pager reload button to reloadaccountreq action for now
    # TODO: switch to AJAX actions in general, including table reload

    table_spec = {'table_id': 'accountreqtable', 'sort_order': '[[9,0]]',
                  'refresh_call': 'document.location="?action=reloadaccountreq"'}
    (add_import, add_init, add_ready) = man_base_js(configuration,
                                                    [table_spec])
    show_tab_index = 0
    if action in accountreq_actions:
        # NOTE: show Account Requests tab and disable reload
        show_tab_index = 1
        title_entry['meta'] = ''
    add_ready += '''
            var preselected_tab = %d;
            $(".migadmin-tabs").tabs({
                active: preselected_tab
                });
''' % show_tab_index
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    if not configuration.site_enable_migadmin:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Site administration not enabled for this site!'})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif not is_admin(client_id, configuration, logger):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'You MUST be a site admin to access this control panel.'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
    # TODO: Support OpenID with 2FA requirement as well
    view_auth, act_auth = [], []
    auth_map = {'cert': AUTH_CERTIFICATE, 'oid': AUTH_OPENID_V2,
                'oidc': AUTH_OPENID_CONNECT}
    for (auth_name, auth_code) in auth_map.items():
        if auth_name in configuration.site_migadmin_view_access or \
                keyword_any in configuration.site_migadmin_view_access:
            view_auth.append(auth_code)
        if auth_name in configuration.site_migadmin_act_access or \
                keyword_any in configuration.site_migadmin_act_access:
            act_auth.append(auth_code)
    if (not action or action in view_ops) and auth_type not in view_auth:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Admin view access requires %s auth on this site.' %
             ' or '.join(view_auth)})
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif action in act_ops and auth_type not in act_auth:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Admin act access requires %s auth on this site.' %
             ' or '.join(act_auth)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    html = ''
    if action and not action in list(grid_actions) + accountreq_actions:
        output_objects.append(
            {'object_type': 'error_text', 'text': 'Invalid action: %s' % action})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Handle action and set response in action_msg or action_err for inline use
    action_msg, action_err = '', ''
    if action in grid_actions:
        msg = "%s" % grid_actions[action]
        if job_list:
            msg += ' %s' % ' '.join(job_list)
        msg += '\n'
        if not send_message_to_grid_script(msg, logger, configuration):
            action_err = '''Error sending %s message to grid_script.''' % action
            status = returnvalues.SYSTEM_ERROR
    elif action in accountreq_actions:
        if action == "reloadaccountreq":
            action_msg = 'Reloaded account requests'
        elif action == "createaccountreq":
            peer_id = request_text
            for req_id in req_list:
                (success, err) = accept_account_req(req_id, configuration,
                                                    peer_id,
                                                    default_renew=True)
                if success:
                    action_msg = 'Accepted account request %s' % req_id
                else:
                    action_err = 'Accept account request %s failed: %s' % \
                                 (req_id, err)
                    status = returnvalues.SYSTEM_ERROR
        elif action == "peeraccountreq":
            peer_id = request_text
            for req_id in req_list:
                (success, err) = peer_account_req(req_id, configuration,
                                                  peer_id)
                if success:
                    action_msg = 'Made Peer account request for %s' % req_id
                else:
                    action_err = 'Peer account request failed for %s: %s' % \
                                 (req_id, err)
                    status = returnvalues.SYSTEM_ERROR
        elif action == "rejectaccountreq":
            reject_msg = request_text
            for req_id in req_list:
                (success, err) = reject_account_req(req_id, configuration,
                                                    reject_msg)
                if success:
                    action_msg = 'Rejected account request %s' % req_id
                else:
                    action_err = 'Reject account request %s failed: %s' % \
                                 (req_id, err)
                    status = returnvalues.SYSTEM_ERROR
        else:
            action_err = 'Unsupported account request action: %s' % action
            logger.error(action_err)
            status = returnvalues.SYSTEM_ERROR

    show, drop = '', ''
    general = """
<h2>Server Status</h2>
<p class='importanttext'>
This page automatically refreshes every %s seconds.
</p>
<p>
You can see the current grid daemon status and server logs below. The buttons
provide access to e.g. managing the grid job queues.
</p>
<form method='get' action='migadmin.py'>
    <input type='hidden' name='action' value='' />
    <input type='submit' value='Show last log lines' />
    <input type='text' size='2' name='lines' value='%s' />
</form>
<br />
<form method='get' action='migadmin.py'>
    <input type='hidden' name='lines' value='%s' />
    <input type='hidden' name='action' value='reloadconfig' />
    <input type='submit' value='Reload Configuration' />
</form>
<br />
""" % (configuration.sleep_secs, lines, lines)
    show += """
<form method='get' action='migadmin.py'>
    <input type='hidden' name='lines' value='%s' />
    <input type='submit' value='Log Jobs' />
    <select name='action'>
""" % lines
    drop += """
<form method='get' action='migadmin.py'>
    <input type='hidden' name='lines' value='%s' />
    <input type='submit' value='Drop Job' />
    <select name='action'>
""" % lines
    for queue in ['queued', 'executing', 'done']:
        selected = ''
        if action.find(queue) != -1:
            selected = 'selected'
        show += "<option %s value='show%s'>%s</option>" % (selected, queue,
                                                           queue)
        drop += "<option %s value='drop%s'>%s</option>" % (selected, queue,
                                                           queue)
    show += """
    </select>
</form>
<br />
"""
    drop += """
    </select>
    <input type='text' size='20' name='job_id' value='' />
</form>
<br />
"""

    html += general
    html += show
    html += drop

    daemons = """
<div id='daemonstatus'>
"""
    daemon_names = []
    if configuration.site_enable_jobs:
        daemon_names += ['grid_script.py', 'grid_monitor.py', 'grid_sshmux.py']
    if configuration.site_enable_events:
        daemon_names.append('grid_events.py')
    # No need to run im_notify unless any im notify protocols are enabled
    if configuration.site_enable_imnotify and \
            [i for i in configuration.notify_protocols if i != 'email']:
        daemon_names.append('grid_imnotify.py')
    if configuration.site_enable_sftp:
        daemon_names.append('grid_sftp.py')
    if configuration.site_enable_davs:
        daemon_names.append('grid_webdavs.py')
    if configuration.site_enable_ftps:
        daemon_names.append('grid_ftps.py')
    if configuration.site_enable_openid:
        daemon_names.append('grid_openid.py')
    if configuration.site_enable_transfers:
        daemon_names.append('grid_transfers.py')
    if configuration.site_enable_crontab:
        daemon_names.append('grid_cron.py')
    if configuration.site_enable_seafile and \
            configuration.user_seafile_local_instance:
        daemon_names += ['seafile-controller', 'seaf-server', 'ccnet-server',
                         'seahub']
        if configuration.seafile_mount and configuration.user_seafile_ro_access:
            daemon_names.append('seaf-fuse')
    if configuration.site_enable_sftp_subsys:
        daemon_names.append(
            '/sbin/sshd -f /etc/ssh/sshd_config-MiG-sftp-subsys')
    for proc in daemon_names:
        # NOTE: we use command list here to avoid shell requirement
        pgrep_proc = subprocess_popen(['pgrep', '-f', proc],
                                      stdout=subprocess_pipe,
                                      stderr=subprocess_stdout)
        pgrep_proc.wait()
        ps_out = pgrep_proc.stdout.read().strip()
        if pgrep_proc.returncode == 0:
            daemons += "<div class='status_online'>%s running (pid %s)</div>" \
                       % (proc, ps_out)
        else:
            daemons += "<div class='status_offline'>%s not running!</div>" % \
                       proc
    daemons += """</div>
<br />
"""
    html += daemons

    log_path_list = []
    if os.path.isabs(configuration.logfile):
        log_path_list.append(configuration.logfile)
    else:
        log_path_list.append(os.path.join(configuration.log_dir,
                                          configuration.logfile))
    for log_path in log_path_list:
        html += '''
<h2>%s</h2>
<textarea class="fillwidth padspace" rows=%s readonly="readonly">
''' % (log_path, lines)
        log_lines = read_tail(log_path, lines, logger)
        html += ''.join(log_lines[-lines:])
        html += '''</textarea>
'''

    if action_err:
        status_frame = """
<div id='action_status' class='status_box'>
    <span class='error errortext iconleftpad iconspace'>%s</span>
</div>
""" % action_err
    elif action_msg:
        status_frame = """
<div id='action_status' class='status_box'>
    <span class='ok iconleftpad iconspace'>%s</span>
</div>
""" % action_msg
    else:
        status_frame = ""

    if status_frame:
        output_objects.append({'object_type': 'html_form', 'text':
                               status_frame})

    output_objects.append({'object_type': 'html_form', 'text': """
<div id='wrap-tabs' class='migadmin-tabs'>
<ul>
<li><a href='#serverstatus-tab'>Server Status</a></li>
<li><a href='#accountreqs-tab'>Account Requests</a></li>
<li><a href='#sitestats-tab'>Site Stats</a></li>
</ul>
"""})

    output_objects.append({'object_type': 'html_form', 'text':  '''
<div id="serverstatus-tab">
'''})
    output_objects.append({'object_type': 'html_form', 'text': html})
    output_objects.append({'object_type': 'html_form', 'text':  '''
    </div>
'''})

    html = ''
    output_objects.append({'object_type': 'html_form', 'text':  '''
<div id="accountreqs-tab">
'''})
    output_objects.append(
        {'object_type': 'header', 'text': 'Pending Account Requests'})

    (list_status, ret) = list_account_reqs(configuration)
    if not list_status:
        logger.error("%s: failed for '%s': %s" % (op_name,
                                                  client_id, ret))
        output_objects.append({'object_type': 'error_text', 'text': ret})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'migadmin'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    accountreqs = []
    for req_id in ret:
        (load_status, req_dict) = get_account_req(req_id, configuration)
        if not load_status:
            logger.error("%s: load failed for '%s': %s" %
                         (op_name, req_id, req_dict))
            output_objects.append({'object_type': 'error_text', 'text': 'Could not read details for "%s"' %
                                   req_id})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        req_item = build_accountreqitem_object(configuration, req_dict)

        # TODO: support optional peer requirement and allow renew checkbox
        # TODO: support checkboxes with notify user and perhaps admin copy
        js_name = 'create%s' % req_id
        helper = html_post_helper(js_name, '%s.py' % target_op,
                                  {'action': 'createaccountreq', 'req_id': req_id,
                                   'request_text': keyword_auto,
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        dialog_help = "Really accept account request %s? Optionally provide a specific user as Peer below or %s to auto-extract from request." % (
            req_id, keyword_auto)
        req_item['createaccountreqlink'] = {
            'object_type': 'link', 'destination':
            "javascript: confirmDialog(%s, '%s', '%s', '', '%s');" %
            (js_name, dialog_help, 'request_text', keyword_auto),
            'class': 'addlink iconspace', 'title': 'Accept request %s' %
            req_id, 'text': ''}
        # TODO: support checkboxes with notify user and perhaps admin copy
        js_name = 'peer%s' % req_id
        helper = html_post_helper(js_name, '%s.py' % target_op,
                                  {'action': 'peeraccountreq', 'req_id': req_id,
                                   'request_text': keyword_auto,
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        dialog_help = "Really trigger Peer accept for account request %s? Optionally provide a specific user as Peer below or %s to auto-extract from request." % (
            req_id, keyword_auto)
        req_item['peeraccountreqlink'] = {
            'object_type': 'link', 'destination':
            "javascript: confirmDialog(%s, '%s', '%s', '', '%s');" %
            (js_name, dialog_help, 'request_text', keyword_auto),
            'class': 'peerlink iconspace', 'title': 'Request Peer for %s' %
            req_id, 'text': ''}
        # TODO: support checkboxes with notify user and perhaps admin copy
        js_name = 'reject%s' % req_id
        helper = html_post_helper(js_name, '%s.py' % target_op,
                                  {'action': 'rejectaccountreq', 'req_id': req_id,
                                   'request_text': '', csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})
        dialog_help = "Really reject account request %s? Enter reason below." % req_id
        req_item['rejectaccountreqlink'] = {
            'object_type': 'link', 'destination':
            "javascript: confirmDialog(%s, '%s', '%s', '', '%s');" %
            (js_name, dialog_help, 'request_text', keyword_auto),
            'class': 'rejectlink iconspace', 'title': 'Reject request %s' % req_id,
            'text': ''}

        # Insert created request item
        accountreqs.append(req_item)

    output_objects.append({'object_type': 'table_pager', 'entry_name':
                           'pending certificate/OpenID account requests',
                           'default_entries': default_pager_entries})
    output_objects.append({'object_type': 'accountreqs',
                           'accountreqs': accountreqs})

    output_objects.append({'object_type': 'html_form', 'text': html})
    output_objects.append({'object_type': 'html_form', 'text':  '''
    </div>
'''})
    output_objects.append({'object_type': 'html_form', 'text':  '''
    <div id="sitestats-tab">
'''})
    html = ''
    html += """
<h2>Site Statistics</h2>
"""
    sitestats_home = configuration.sitestats_home
    if sitestats_home and os.path.isdir(sitestats_home):
        html += '''
        <div id=""all-stats">
'''
        all_stats = {}
        # Grab first available format for each stats file
        for filename in listdir(sitestats_home):
            prefix, ext = os.path.splitext(filename)
            file_format = ext.lstrip('.')
            if not file_format in ['pickle', 'json', 'yaml']:
                continue
            path = os.path.join(sitestats_home, filename)
            stats = all_stats[prefix] = all_stats.get(prefix, {})
            if not stats:
                stats = load(path, serializer=file_format)
                all_stats[prefix].update(force_utf8_rec(stats))

        sorted_stats = list(all_stats.items())
        sorted_stats.sort()
        for (name, stats) in sorted_stats:
            html += format_stats(name, stats)
        html += '''
        </div>
'''

    else:
        html += '<span class="warningtext">Site stats not available</span>'

    output_objects.append({'object_type': 'html_form', 'text': html})
    output_objects.append({'object_type': 'html_form', 'text':  '''
    </div>
'''})

    # Finish tabs wrap
    output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})

    return (output_objects, returnvalues.OK)
