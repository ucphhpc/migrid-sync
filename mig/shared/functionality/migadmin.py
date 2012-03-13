#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migadmin - admin control panel with daemon status monitor
# Copyright (C) 2003-2012  The MiG Project lead by Brian Vinter
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

import shared.returnvalues as returnvalues
from shared.fileio import send_message_to_grid_script
from shared.findtype import is_admin
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {'action': [], 'job_id': [], 'lines': [20]}
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

    script = '''<meta http-equiv="refresh" content="%s" />
    
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>

<script type="text/javascript" >

$(document).ready(function() {
);
</script>
''' % configuration.sleep_secs

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s administration panel' % configuration.short_title
    title_entry['javascript'] = script

    if not is_admin(client_id, configuration, logger):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'You must be an admin to access this control panel.'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    html = ''
    grid_actions = {'reloadconfig': 'RELOADCONFIG',
                    'showqueued': 'JOBQUEUEINFO',
                    'showexecuting': 'EXECUTINGQUEUEINFO',
                    'showdone': 'DONEQUEUEINFO',
                    'dropqueud': 'DROPQUEUED',
                    'dropexecuting': 'DROPEXECUTING',
                    'dropdone': 'DROPDONE',
                    }
    if action and not action in grid_actions:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Invalid action: %s)' % action})
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
    else:
        show, drop = '', '', ''
        general = """
<p>
<form method='get' action='migadmin.py'>
    <input type='hidden' name='action' value='' />
    <input type='text' size='2' name='lines' value='%s' />
    <input type='submit' value='last log lines' />
</form>
</p>
<p>
<form method='get' action='migadmin.py'>
    <input type='hidden' name='action' value='reloadconfig' />
    <input type='submit' value='reload configuration' />
</form>
</p>
""" % lines
        for queue in ['queued', 'executing', 'done']:
            show += """
<p>
<form method='get' action='migadmin.py'>
    <input type='hidden' name='action' value='show%s' />
    <input type='submit' value='show %s jobs' />
</form>
</p>
""" % queue
            drop += """
<p>
<form method='get' action='migadmin.py'>
    <input type='text' size='20' name='job_id' value='' />
    <input type='hidden' name='action' value='drop%s' />
    <input type='submit' value='drop %s job' />
</form>
</p>
""" % (queue, queue)
        html += general
        html += show
        html += drop

    log_path_list = []
    if os.path.isabs(configuration.logfile):
        log_path_list.append(configuration.logfile)
    else:
        for name in ['server', 'cgi-bin', 'cgi-sid']:
            log_path_list.append(os.path.join(configuration.mig_code_base,
                                              name, configuration.logfile))
    for log_path in log_path_list:
        html += '<p>'
        try:
            log_fd = open(log_path, 'r')
            for line in log_fd[-lines:]:
                html += str(line)
            log_fd.close()
        except Exception, exc:
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Error reading log (%s)' % exc})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        html += '</p>'

    output_objects.append({'object_type': 'html_form', 'text'
                              : html})
    return (output_objects, returnvalues.OK)


