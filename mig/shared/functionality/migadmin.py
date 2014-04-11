#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migadmin - admin control panel with daemon status monitor
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""MiG administrators page with daemon status and configuration"""

import os
import subprocess

import shared.returnvalues as returnvalues
from shared.fileio import send_message_to_grid_script
from shared.findtype import is_admin
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry

grid_actions = {'reloadconfig': 'RELOADCONFIG',
                'showqueued': 'JOBQUEUEINFO',
                'showexecuting': 'EXECUTINGQUEUEINFO',
                'showdone': 'DONEQUEUEINFO',
                'dropqueued': 'DROPQUEUED',
                'dropexecuting': 'DROPEXECUTING',
                'dropdone': 'DROPDONE',
                }

def signature():
    """Signature of the main function"""

    defaults = {'action': [''], 'job_id': [], 'lines': [20]}
    return ['html_form', defaults]


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
    action = accepted['action'][-1]
    job_list = accepted['job_id']
    lines = int(accepted['lines'][-1])

    meta = '''<meta http-equiv="refresh" content="%s" />
''' % configuration.sleep_secs
    style = '''    
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
'''
    script = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>

<script type="text/javascript" >

$(document).ready(function() {
);
</script>
'''

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s administration panel' % configuration.short_title
    title_entry['meta'] = meta
    title_entry['style'] = style
    title_entry['javascript'] = script

    if not is_admin(client_id, configuration, logger):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'You must be an admin to access this control panel.'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    html = ''
    if action and not action in grid_actions:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid action: %s' % action})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    if action:
        msg = "%s" % grid_actions[action]
        if job_list:
            msg += ' %s' % ' '.join(job_list)
        msg += '\n'
        if not send_message_to_grid_script(msg, logger, configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : '''Error sending %s message to grid_script.''' % action
                 })
            status = returnvalues.SYSTEM_ERROR

    show, drop = '', ''
    general = """
<h1>Server Status</h1>
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
    daemon_names = ['grid_script.py', 'grid_monitor.py', 'ssh_multiplex.py']
    # No need to run im_notify unless any im notify protocols are enabled
    if [i for i in configuration.notify_protocols if i != 'email']:
        daemon_names.append('im_notify.py')
    if configuration.site_enable_sftp:
        daemon_names.append('grid_sftp.py')
    if configuration.site_enable_davs:
        daemon_names.append('grid_davs.py')
    if configuration.site_enable_ftps:
        daemon_names.append('grid_ftps.py')
    if configuration.site_enable_openid:
        daemon_names.append('grid_openid.py')
    for proc in daemon_names:
        pgrep_proc = subprocess.Popen(['pgrep', '-f', proc],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)
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
        for name in ['server', 'cgi-bin', 'cgi-sid']:
            log_path_list.append(os.path.join(configuration.mig_code_base,
                                              name, configuration.logfile))
    for log_path in log_path_list:
        html += '''
<h1>%s</h1>
<textarea rows=%s cols=200 readonly="readonly">
''' % (log_path, lines)
        try:
            logger.debug("loading %d lines from %s" % (lines, log_path))
            log_fd = open(log_path, 'r')
            log_fd.seek(0, os.SEEK_END)
            size = log_fd.tell()
            pos = log_fd.tell()
            log_lines = []
            step_size = 100
            # locate last X lines 
            while pos > 0 and len(log_lines) < lines:
                offset = min(lines * step_size, size)
                logger.debug("seek to offset %d from end of %s" % (offset,
                                                                  log_path))
                log_fd.seek(-offset, os.SEEK_END)
                pos = log_fd.tell()
                log_lines = log_fd.readlines()
                step_size *= 2
            logger.debug("reading %d lines from %s" % (lines, log_path))
            html += ''.join(log_lines[-lines:])
            log_fd.close()
        except Exception, exc:
            logger.error("reading %d lines from %s: %s" % (lines, log_path,
                                                           exc))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Error reading log (%s)' % exc})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        html += '''</textarea>
'''

    output_objects.append({'object_type': 'html_form', 'text'
                              : html})
    return (output_objects, returnvalues.OK)


