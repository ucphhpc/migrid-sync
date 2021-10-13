#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# crontab - user task scheduling back end
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Let users set up cron jobs to schedule tasks they would otherwise have to
do interactively. Restricted to the same backends that are otherwise exposed
and basically just runs those on behalf of the user.
"""

from __future__ import absolute_import

# NOTE: we use additional try/except wrapping here to prevent autopep8 mess up

try:
    from builtins import range
    from future import standard_library
    standard_library.install_aliases()
except Exception as exc:
    print("ERROR: failed to init py 2/3 compatibility")
    sys.exit(1)

import datetime
import os
import re
import time

from mig.shared.base import client_id_dir
from mig.shared.cmdapi import get_usage_map
from mig.shared.defaults import crontab_name, cron_log_cnt, cron_output_dir, \
    cron_log_name, csrf_field
from mig.shared import returnvalues
from mig.shared.editing import cm_css, cm_javascript, cm_options, wrap_edit_area
from mig.shared.events import get_time_expand_map, load_crontab, load_atjobs, \
    parse_and_save_crontab, parse_and_save_atjobs
from mig.shared.fileio import makedirs_rec
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from mig.shared.html import man_base_js, man_base_html
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.parseflags import verbose


get_actions = ['show']
post_actions = ['save']
valid_actions = get_actions + post_actions
enabled_strings = ('on', 'yes', 'true')

crontab_edit = cm_options.copy()
crontab_edit['mode'] = 'shell'
atjobs_edit = cm_options.copy()
atjobs_edit['mode'] = 'shell'


def signature():
    """Signature of the main function"""

    defaults = {'action': ['show'],
                'crontab': [''],
                'atjobs': [''],
                'flags': ['']}
    return ['html_form', defaults]


def read_cron_log(configuration, client_id, flags):
    """Read-in saved cron logs for crontab. We read in all rotated logs"""

    client_dir = client_id_dir(client_id)
    log_content = ''
    for i in range(cron_log_cnt - 1, -1, -1):
        log_name = cron_log_name
        if i > 0:
            log_name += '.%d' % i
        log_path = os.path.join(configuration.user_home, client_dir,
                                cron_output_dir, log_name)
        configuration.logger.debug('read from %s' % log_path)
        try:
            log_fd = open(log_path)
            log_content += log_fd.read()
            configuration.logger.debug('read in log lines:\n%s' % log_content)
            log_fd.close()
        except IOError:
            pass
    return log_content


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
    crontab = '\n'.join(accepted['crontab'])
    flags = ''.join(accepted['flags'][-1])

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Scheduled Tasks'

    # jquery support for tabs

    (add_import, add_init, add_ready) = man_base_js(configuration,
                                                    [],
                                                    {'width': 600})
    add_ready += '''
              /* Init variables helper as foldable but closed and with individual
              heights */
              $(".variables-accordion").accordion({
                                           collapsible: true,
                                           active: false,
                                           heightStyle: "content"
                                          });
              /* fix and reduce accordion spacing */
              $(".ui-accordion-header").css("padding-top", 0)
                                       .css("padding-bottom", 0).css("margin", 0);
              /* NOTE: requires managers CSS fix for proper tab bar height */
              $(".crontab-tabs").tabs();
              $("#logarea").scrollTop($("#logarea")[0].scrollHeight);
        '''
    title_entry['style']['advanced'] += '''
%s
''' % cm_css
    title_entry['script']['advanced'] += cm_javascript + "\n"
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})
    if not configuration.site_enable_crontab:
        output_objects.append({'object_type': 'text', 'text': '''
Scheduled tasks are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    logger.info('crontab %s from %s' % (action, client_id))
    logger.debug('crontab from %s: %s' % (client_id, accepted))

    if not action in valid_actions:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid action "%s" (supported: %s)' %
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

    crontab_contents = load_crontab(client_id, configuration)
    crontab_help = """### Cron Jobs: Regularly Running Tasks
# This is a standard crontab specification describing actions to run on your
# behalf at given times. Lines starting with a '#' are comments, only used for
# explaining things. All other lines represent a scheduled task.
#
# Each task to run has to be defined through a single line indicating with
# different fields when the task will be run and what command to run for the
# task.
#
# To define the time you can provide concrete values for minute (m), hour (h),
# day of month (dom), month (mon), and day of week (dow) or use '*' in these
# fields (for 'any').
#
# For example, if you have a Documents folder and want to create a backup of it
# at 5 a.m every week, you can do so by adding a rule like:
# 0 5 * * 1 pack Documents Documents-backup.zip
# somewhere below this help text. Just leave out the leading '# '.
#
# m h  dom mon dow   command
"""
    if not crontab_contents:
        crontab_contents += crontab_help

    atjobs_help = """### At Jobs: One-time Tasks
# This is a basic at schedule file. It is similar to the crontab only with
# time stamps leading the command line.
#
# It uses the ISO time format YYYY-MM-DD HH:MM:SS so to schedule a one-time
# backup like the cron job example and make it run on the 14th of May 2019
# 42 minutes past midnight one would enter something like:
# 2019-05-14 00:42:00 pack Documents Documents-backup.zip
# You can insert such commands below and just leave out the leading '#'.
#
# yyyy-mm-dd hh:mm:ss command
"""
    atjobs_contents = load_atjobs(client_id, configuration)
    if not atjobs_contents:
        atjobs_contents += atjobs_help

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = 'crontab'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers = {'site': configuration.short_title,
                    'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}

    # Shared header entry
    header_entry = {'object_type': 'header', 'text': 'Schedule Tasks'}
    output_objects.append(header_entry)
    if action in get_actions:
        if action == "show":
            log_content = read_cron_log(configuration, client_id, flags)

            # Make page with manage crontab and log tab

            output_objects.append({'object_type': 'html_form', 'text':  '''
    <div id="wrap-tabs" class="crontab-tabs">
<ul>
<li><a href="#manage-tab">Manage Tasks</a></li>
<li><a href="#log-tab">View Logs</a></li>
</ul>
'''})

            # Display existing crontab in form to edit

            output_objects.append({'object_type': 'html_form', 'text':  '''
<div id="manage-tab">
'''})

            output_objects.append({'object_type': 'sectionheader',
                                   'text': 'Manage Scheduled Tasks'})

            fill_helpers.update(
                {'target_op': target_op, 'csrf_token': csrf_token})
            html = '''
<form method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="action" value="save" />
<p>
You can schedule %(site)s commands to run on your behalf at given times. In
that way you can automate many of the routine tasks that you would in practice
be able to do manually, but which would be tedious and inconvenient to repeat
every time. This includes tasks like regular backup or archiving, which
typically makes most sense to run e.g. every night or once a week.
</p>
<p>Information about any scheduled actions you configure automatically gets
logged and you can use View Logs above to inspect them.
</p>
<p class="warningtext">Please note that for security reasons you can ONLY
schedule runs of a limited set of commands, namely a selection of the most
useful actions you would be able to interactively run.
</p>
<p>
The fold-outs at the bottom contain additional help on the available commands
and the format in use.
</p>
<h3>Cron Jobs: Repeating Command Schedule</h3>
Each line here follows the standard UN*X crontab format with five time fields
specifying when to run, followed by the command to run.
'''

            keyword_crontab = "crontabentries"
            crontab_area = '''
<textarea id="%(keyword_crontab)s" cols=82 rows=5
          name="crontab">%(current_crontab)s</textarea>
'''
            html += wrap_edit_area(keyword_crontab, crontab_area, crontab_edit,
                                   'BASIC')

            html += '''
            <h3>At Jobs: One-time Command Schedule</h3>
For one-time commands you can use the following field instead. Each line
consists of a time stamp in ISO format followed by the command to run at that
particular time.
'''
            keyword_atjobs = "atjobsentries"
            atjobs_area = '''
<textarea id="%(keyword_atjobs)s" cols=82 rows=5
          name="atjobs">%(current_atjobs)s</textarea>
'''
            html += wrap_edit_area(keyword_atjobs, atjobs_area, atjobs_edit,
                                   'BASIC')

            html += '''<br/>
<input type="submit" value="Save Cron/At Jobs Settings" />
</form>
'''

            vars_html = ''
            dummy_rule = {
                'run_as': client_id, 'command':
                ['touch', 'crontest-+SCHEDYEAR+-+SCHEDMONTH+-+SCHEDDAY+.txt']}
            now = datetime.datetime.now()
            now = now.replace(microsecond=0)
            cron_times = [now, datetime.datetime(now.year + 1, 12, 24, 12, 42),
                          datetime.datetime(now.year + 2, 1, 2, 9, 2, 42)]
            for timestamp in cron_times:
                vars_html += "<b>Expanded time %s variables:</b><br/>" % \
                             timestamp
                expanded = get_time_expand_map(timestamp, dummy_rule)
                for (key, val) in expanded.items():
                    vars_html += "    %s: %s<br/>" % (key, val)
                filled_command = dummy_rule['command'][:1]
                for argument in dummy_rule['command'][1:]:
                    filled_argument = argument
                    for (key, val) in expanded.items():
                        filled_argument = filled_argument.replace(key, val)
                    filled_command.append(filled_argument)
                vars_html += "Expanded command <tt>%s</tt> to: <tt>%s</tt>:<br/>" % \
                             (' '.join(dummy_rule['command']),
                              ' '.join(filled_command))
            commands_html = ''
            commands = get_usage_map(configuration)
            for usage in commands.values():
                commands_html += "    %s<br/>" % usage
            html += """
<br/>
<div class='variables-accordion'>
<h4>Help on available cron/at variable names and values</h4>
<p>
Scheduled tasks can use a number of helper variables on the form +SCHEDXYZ+ to
dynamically act on times. Most are automatically expanded for the particular
cron timestamp as shown in the following examples:<br/>
%s
</p>
<h4>Help on available commands and arguments</h4>
<p>
It is possible to schedule most operations you could manually do on %s.
I.e. like packing files/folders, creating/moving/deleting a file or directory
and so on. You have the following commands at your disposal:<br/>
%s
</p>
</div>
""" % (vars_html, configuration.short_title, commands_html)

            fill_helpers.update({
                'current_crontab': crontab_contents,
                'keyword_crontab': keyword_crontab,
                'current_atjobs': atjobs_contents,
                'keyword_atjobs': keyword_atjobs,
            })
            output_objects.append({'object_type': 'html_form', 'text':
                                   html % fill_helpers})

            output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
'''})

            # Display recent logs for this vgrid

            output_objects.append({'object_type': 'html_form', 'text':  '''
    <div id="log-tab">
'''})
            output_objects.append({'object_type': 'sectionheader',
                                   'text': 'Scheduled Tasks Log'})

            # TODO: switch to ajax and job monitor+refresh like in workflows

            output_objects.append({'object_type': 'crontab_log', 'log_content':
                                   log_content})
            output_objects.append({'object_type': 'html_form', 'text':  '''
</div>
</div>
<div class="col-lg-12" style="height: 100px;"></div>
'''})

    elif action in post_actions:
        if action == "save":
            header_entry['text'] = 'Save Scheduled Tasks'
            crontab = '\n'.join(accepted.get('crontab', ['']))
            (parse_status, parse_msg) = \
                parse_and_save_crontab(crontab, client_id,
                                       configuration)
            if not parse_status:
                output_objects.append({'object_type': 'error_text', 'text':
                                       'Error parsing and saving crontab: %s'
                                       % parse_msg})
                output_status = returnvalues.CLIENT_ERROR
            else:
                if parse_msg:
                    output_objects.append({'object_type': 'html_form', 'text':
                                           '<p class="warningtext">%s</p>' %
                                           parse_msg})
                else:
                    output_objects.append({'object_type': 'text', 'text':
                                           'Saved repeating task schedule'})

            atjobs = '\n'.join(accepted.get('atjobs', ['']))
            (parse_status, parse_msg) = \
                parse_and_save_atjobs(atjobs, client_id,
                                      configuration)
            if not parse_status:
                output_objects.append({'object_type': 'error_text', 'text':
                                       'Error parsing and saving atjobs: %s'
                                       % parse_msg})
                output_status = returnvalues.CLIENT_ERROR
            else:
                if parse_msg:
                    output_objects.append({'object_type': 'html_form', 'text':
                                           '<p class="warningtext">%s</p>' %
                                           parse_msg})
                else:
                    output_objects.append({'object_type': 'text', 'text':
                                           'Saved one-time task schedule'})
            output_objects.append({'object_type': 'link',
                                   'destination': 'crontab.py',
                                   'text': 'Return to schedule task overview'})

    return (output_objects, returnvalues.OK)
