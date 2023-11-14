#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmcrontab - remove scheduled cron/at user tasks back end
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Let users remove individual cron/at jobs from their scheduled tasks. A
convenient alternative to the full crontab back end, which expects a complete
crontab or atjobs textarea and therefore is a bit cumbersome to use from e.g.
xmlrpc/jsonrpc.
"""

from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.events import load_crontab, load_atjobs, \
    parse_and_save_crontab, parse_and_save_atjobs
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {'crontab': [''],
                'atjobs': ['']}
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

    atjobs = accepted['atjobs']
    cronjobs = accepted['crontab']

    output_status = returnvalues.OK
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Add Scheduled Tasks'

    header_entry = {'object_type': 'header',
                    'text': 'Schedule Tasks'}
    output_objects.append(header_entry)

    if not configuration.site_enable_crontab:
        output_objects.append({'object_type': 'text', 'text':
                               """Scheduling tasks is disabled on this site.
Please contact the %s site support (%s) if you think it should be enabled.
""" % (configuration.short_title, configuration.support_email)})
        return (output_objects, returnvalues.OK)

    logger.info('%s from %s' % (op_name, client_id))
    #logger.debug('%s from %s: %s' % (op_name, client_id, accepted))

    if not atjobs and not cronjobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               'No cron/at jobs provided!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if cronjobs:
        crontab_contents = load_crontab(client_id, configuration)
        updated_lines = []
        for line in crontab_contents.split('\n'):
            if line.strip() not in cronjobs:
                updated_lines.append(line)
        crontab_contents = '\n'.join(updated_lines)
        (parse_status, parse_msg) = \
            parse_and_save_crontab(crontab_contents, client_id,
                                   configuration)
        if not parse_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Error parsing and saving crontab: %s' %
                                   parse_msg})
            output_status = returnvalues.CLIENT_ERROR
        else:
            if parse_msg:
                output_objects.append({'object_type': 'html_form', 'text':
                                       '<p class="warningtext">%s</p>' %
                                       parse_msg})
            else:
                output_objects.append({'object_type': 'text', 'text':
                                       'Removed repeating task schedule(s)'})

    if atjobs:
        atjobs_contents = load_atjobs(client_id, configuration)
        updated_lines = []
        for line in atjobs_contents.split('\n'):
            if line.strip() not in atjobs:
                updated_lines.append(line)
        atjobs_contents = '\n'.join(updated_lines)
        (parse_status, parse_msg) = parse_and_save_atjobs(atjobs_contents,
                                                          client_id,
                                                          configuration)
        if not parse_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Error parsing and saving atjobs: %s' %
                                   parse_msg})
            output_status = returnvalues.CLIENT_ERROR
        else:
            if parse_msg:
                output_objects.append({'object_type': 'html_form', 'text':
                                       '<p class="warningtext">%s</p>' %
                                       parse_msg})
            else:
                output_objects.append({'object_type': 'text', 'text':
                                       'Removed one-time task schedule(s)'})

    output_objects.append({'object_type': 'link',
                           'destination': 'crontab.py',
                           'text': 'Schedule task overview'})

    return (output_objects, output_status)
