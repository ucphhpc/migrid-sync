#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminfreeze - back end to request freeze files in write-once fashion
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

"""Request freeze of one or more files into a write-once archive"""

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append({'object_type': 'header', 'text'
                          : 'Make frozen archive'})
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

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Freeze Archive'

    # jquery support for dynamic addition of upload fields

    title_entry['javascript'] = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>

<script type="text/javascript" >

var upload_fields = 0;

function add_uploads(div_id) {
    // How many upload fields to add each time add more is requested
    var add_count = 3;
    var i;
    for (i = 0; i < add_count; i++) {
        upload_entry = "<input type=\'file\' name=\'freeze_file_"+upload_fields;
        upload_entry += "\' size=50 /><br / >";
        $(div_id).append(upload_entry);
        upload_fields += 1;
    }
}

$(document).ready(function() {
         // Add upload fields
         add_uploads("#freezefiles");
     }
);
</script>
'''

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                           '''Freezing archives is not enabled on this site.
    Please contact the Grid admins if you think it should be.'''})
        return (output_objects, returnvalues.OK)

    output_objects.append(
        {'object_type': 'text', 'text'
         : '''Note that a frozen archive can not be changed after creation
and it can only be manually removed by the management, so please be careful
when filling in the details.'''
         })

    html_form = """
<form enctype='multipart/form-data' method='post' action='createfreeze.py'>
<br /><b>Name:</b><br />
<input type='text' name='freeze_name' size=30 />
<br /><b>Description:</b><br />
<textarea cols='80' rows='20' wrap='off' name='freeze_description'></textarea>
<br />
<div id='freezefiles'>
<b>Freeze Archive Files:</b> <input type='button' value='Add more uploads'
onClick='add_uploads(\"#freezefiles\");'/>
<br />
</div><br />
<input type='submit' value='Create Archive' />
</form>
"""
    output_objects.append({'object_type': 'html_form', 'text'
                          : html_form})

    return (output_objects, returnvalues.OK)


