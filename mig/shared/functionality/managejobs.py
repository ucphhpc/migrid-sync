#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# managejobs - simple job management interface
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

"""Simple front end to job management"""

from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.defaults import csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    status = returnvalues.OK
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

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Job execution is not enabled on this system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Manage jobs'
    output_objects.append({'object_type': 'header', 'text': 'Manage Jobs'})
    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'View status of all submitted jobs'})
    output_objects.append({'object_type': 'html_form', 'text': '''
<form method="get" action="jobstatus.py">
Sort by modification time: <input type="radio" name="flags" value="sv" />yes
<input type="radio" name="flags" checked="checked" value="vi" />no<br />
<input type="hidden" name="job_id" value="*" />
<input type="hidden" name="output_format" value="html" />
<input type="submit" value="Show All" />
</form>
    '''})
    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'View status of individual jobs'})
    output_objects.append({'object_type': 'html_form', 'text': '''
Filter job IDs (* and ? wildcards are supported)<br />
<form method="get" action="jobstatus.py">
Job ID: <input type="text" name="job_id" value="*" size="30" /><br />
Show only <input type="text" name="max_jobs" size="6" value=5 /> first matching jobs<br />
Sort by modification time: <input type="radio" name="flags" checked="checked" value="vsi" />yes
<input type="radio" name="flags" value="vi" />no<br />
<input type="hidden" name="output_format" value="html" />
<input type="submit" value="Show" />
</form>
    '''})
    output_objects.append({'object_type': 'sectionheader', 'text':
                           'Resubmit job'})
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'short_title': configuration.short_title,
                    'form_method': form_method,
                    'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'resubmit'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    output_objects.append({'object_type': 'html_form', 'text': '''
<form method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
Job ID: <input type="text" name="job_id" size="30" /><br />
<input type="hidden" name="output_format" value="html" />
<input type="submit" value="Submit" />
</form>
    ''' % fill_helpers})
    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'Freeze pending job'})
    target_op = 'jobaction'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    output_objects.append({'object_type': 'html_form', 'text': '''
<form method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
Job ID: <input type="text" name="job_id" size="30" /><br />
<input type="hidden" name="action" value="freeze" />
<input type="hidden" name="output_format" value="html" />
<input type="submit" value="Freeze job" />
</form>
    ''' % fill_helpers})
    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'Thaw frozen job'})
    output_objects.append({'object_type': 'html_form', 'text': '''
<form method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
Job ID: <input type="text" name="job_id" size="30" /><br />
<input type="hidden" name="action" value="thaw" />
<input type="hidden" name="output_format" value="html" />
<input type="submit" value="Thaw job" />
</form>
    ''' % fill_helpers})
    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'Cancel pending or executing job'})
    output_objects.append({'object_type': 'html_form', 'text': '''
<form method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
Job ID: <input type="text" name="job_id" size="30" /><br />
<input type="hidden" name="action" value="cancel" />
<input type="hidden" name="output_format" value="html" />
<input type="submit" value="Cancel job" />
</form>
    ''' % fill_helpers})
    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'Request live I/O'})
    output_objects.append({'object_type': 'html_form', 'text': '''
<form method="get" action="liveio.py">
Job ID: <input type="text" name="job_id" size="30" /><br />
<input type="hidden" name="output_format" value="html" />
<input type="submit" value="Request" />
</form>
<br />
    '''})
    return (output_objects, status)
