#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# downloads - [insert a few words of module description on this line]
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

"""Simple front end to script generators"""

import os
import sys

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)

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

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Downloads'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Downloads'})
    output_objects.append({'object_type': 'text', 'text'
                          : """
<div class="migcontent">
This page provides access to on-demand downloads of the MiG user scripts in all available formats.<br>
Simply pick your flavor of choice to generate the latest user scripts in your MiG home directory and as a zip file for easy download.<p>
In order to use the scripts your need the interpreter of choice (bash or python at the moment) and the
<a href="http://curl.haxx.se">cURL</a> command line client.<br>
There's a tutorial with examples of all the commands available on the MiG page. The python version of the user scripts additionally include a miglib python module, which may be used to incorporate MiG commands in your python applications.
</div>
"""})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'MiG User Scripts'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<div class="migcontent">
Generate MiG user scripts to manage jobs and files:<br/>
<div class="container">
<table class="downloads">
<tr>
<td>
<form method='get' action='scripts.py'>
<input type='hidden' name='output_format' value='html'>
<input type='hidden' name='lang' value='python'>
<input type='submit' value='python version'>
</form>
</td>
<td>
<form method='get' action='scripts.py'>
<input type='hidden' name='output_format' value='html'>
<input type='hidden' name='lang' value='sh'>
<input type='submit' value='sh version'>
</form>
</td>
<td>
<form method='get' action='scripts.py'>
<input type='hidden' name='output_format' value='html'>
<input type='submit' value='all versions'>
</form>
</td>
</tr>
</table>
</div>
</div>
<br>
    """})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'MiG Resource Scripts'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<div class="migcontent">
Generate MiG scripts to administrate resources and vgrids:<br/>
<div class="container">
<table class="downloads">
<tr>
<td>
<form method='get' action='scripts.py'>
<input type='hidden' name='output_format' value='html'>
<input type='hidden' name='lang' value='python'>

<input type='hidden' name='flavor' value='resource'>
<input type='submit' value='python version'>
</form>
</td>
<td>
<form method='get' action='scripts.py'>
<input type='hidden' name='output_format' value='html'>
<input type='hidden' name='lang' value='sh'>
<input type='hidden' name='flavor' value='resource'>
<input type='submit' value='sh version'>
</form>
</td>
<td>
<form method='get' action='scripts.py'>
<input type='hidden' name='output_format' value='html'>
<input type='hidden' name='flavor' value='resource'>
<input type='submit' value='all versions'>
</form>
</td>
</tr>
</table>
<br>
</div>
</div>
    """})
    return (output_objects, status)


