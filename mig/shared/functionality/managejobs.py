#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# managejobs - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import os
import sys

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)

    status = returnvalues.OK
    defaults = {}
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        cert_name_no_spaces,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'title', 'text': 'MiG Jobs'})
    output_objects.append({'object_type': 'header', 'text': 'MiG Jobs'})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'View status of all submitted jobs'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<form method="post" action="/cgi-bin/jobstatus.py">
Sort by modification time: <input type="radio" name="flags" value="sv">yes
<input type="radio" name="flags" checked="checked" value="v">no<BR>
<input type="hidden" name="job_id" value="*">
<input type="hidden" name="output_format" value="html">
<input type="submit" value="Show All">
</form>
    """})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'View status of one or more jobs'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
Filter job IDs (* and ? wildcards are supported)<br>
<form method="post" action="/cgi-bin/jobstatus.py">
Job ID: <input type="text" name="job_id" value="*" size="30"><br>
Show only <input type="text" name="max_jobs" size="6" value=5> first matching jobs<br>
Sort by modification time: <input type="radio" name="flags" checked="checked" value="vs">yes
<input type="radio" name="flags" value="v">no<br>
<input type="hidden" name="output_format" value="html">
<input type="submit" value="Show">
</form>
    """})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Resubmit job'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<form method="post" action="/cgi-bin/resubmit.py">
Job ID: <input type="text" name="job_id" size="30"><br>
<input type="hidden" name="output_format" value="html">
<input type="submit" value="Submit">
</form>
    """})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Cancel pending or executing job'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<form method="post" action="/cgi-bin/canceljob.py">
Job ID: <input type="text" name="job_id" size="30"><br>
<input type="hidden" name="output_format" value="html">
<input type="submit" value="Cancel job">
</form>
    """})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Request live output'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<form method="post" action="/cgi-bin/liveoutput.py">
Job ID: <input type="text" name="job_id" size="30"><br>
<input type="hidden" name="output_format" value="html">
<input type="submit" value="Request">
</form>
    """})
    return (output_objects, status)


