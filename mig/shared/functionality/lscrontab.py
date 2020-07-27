#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# lscrontab - list scheduled cron/at user tasks back end
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Let users list cron/at jobs from their scheduled tasks. A convenient
alternative to the full crontab back end, which expects a complete crontab or
atjobs textarea and therefore is a bit cumbersome to use from e.g.
xmlrpc/jsonrpc.
"""
from __future__ import absolute_import

from .shared.defaults import keyword_all, csrf_field
from .shared import returnvalues
from .shared.events import load_crontab, load_atjobs
from .shared.functional import validate_input_and_cert
from .shared.handlers import get_csrf_limit, make_csrf_token
from .shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {'target': [keyword_all]}
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

    target_list = accepted['target']

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'List Scheduled Tasks'

    header_entry = {'object_type': 'header',
                    'text': 'Scheduled Tasks'}
    output_objects.append(header_entry)

    if not configuration.site_enable_crontab:
        output_objects.append({'object_type': 'text', 'text': '''
Scheduled tasks are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    logger.info('%s from %s' % (op_name, client_id))
    #logger.debug('%s from %s: %s' % (op_name, client_id, accepted))

    # Include handy CSRF helpers for use in subsequent client crontab changes
    csrf_helpers = {'csrf_field': csrf_field}
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    for target_op in ('addcrontab', 'rmcrontab', 'crontab'):
        csrf_helpers[target_op] = make_csrf_token(configuration, form_method,
                                                  target_op, client_id,
                                                  csrf_limit)
    crontab_listing = {'object_type': 'crontab_listing', 'crontab': [],
                       'atjobs': [], 'csrf_helpers': csrf_helpers}
    if not target_list:
        output_objects.append({'object_type': 'error_text', 'text':
                               'No at/cron target to list!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if keyword_all in target_list or 'crontab' in target_list:
        crontab_contents = load_crontab(client_id, configuration)
        cronjobs = []
        for line in crontab_contents.split('\n'):
            # Skip comments and blank lines
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            cronjobs.append(line)
        crontab_listing['crontab'] = cronjobs

    if keyword_all in target_list or 'atjobs' in target_list:
        atjobs_contents = load_atjobs(client_id, configuration)

        atjobs = []
        for line in atjobs_contents.split('\n'):
            # Skip comments and blank lines
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            atjobs.append(line)
        crontab_listing['atjobs'] = atjobs

    output_objects.append(crontab_listing)

    return (output_objects, returnvalues.OK)
