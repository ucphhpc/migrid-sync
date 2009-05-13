#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# submitjob - [insert a few words of module description on this line]
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

"""Simple front end to job and file uploads"""

import os
import sys

import shared.returnvalues as returnvalues
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.settings import mrsl_template, get_default_mrsl


def signature():
    """Signature of the main function"""
    defaults = {}
    return ['', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)

    status = returnvalues.OK
    defaults = signature()[1]
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

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(configuration.user_home + os.sep
                                + cert_name_no_spaces) + os.sep

    template_path = os.path.join(base_dir, mrsl_template)

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Submit Job'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Submit Job'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<div class='smallcontent'>
Job descriptions can use a wide range of keywords to specify job requirements and actions.<br>
Each keyword accepts one or more values of a particular type.<br>
The full list of keywords with their default values and format is available in the on-demand <a href='/cgi-bin/docs.py?show=job'>mRSL Documentation</a>.
<p>
Actual examples for inspiration:
<a href=/cpuinfo.mRSL>CPU Info</a>,
<a href=/basic-io.mRSL>Basic I/O</a>,
<a href=/notification.mRSL>Job Notification</a>,
<a href=/povray.mRSL>Povray</a> and
<a href=/vcr.mRSL>VCR</a>
</div>
    """})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Please enter your mRSL job description below:'
                          })
    default_mrsl = get_default_mrsl(template_path)
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<!-- 
Please note that textarea.py chokes if no nonempty KEYWORD_X_Y_Z fields 
are supplied: thus we simply send a bogus jobname which does nothing
-->
<table class="submitjob">
<tr><td class=centertext>
<form method="post" action="/cgi-bin/textarea.py" id="miginput">
<input type=hidden name=jobname_0_0_0 value=" ">
<textarea cols="82" rows="25" name="mrsltextarea_0">
%(default_mrsl)s
</textarea>
</td></tr>
<tr><td>
<center><input type="submit" value="Submit Job"></center>
</form>
</td></tr>
</table>
<br>
<table class='files'>
<tr class=title><td class=centertext colspan=4>
Upload file
</td></tr>
<tr><td colspan=4>
Upload file to current directory (%(dest_dir)s)
</td></tr>
<tr><td colspan=2>
<form enctype='multipart/form-data' action='/cgi-bin/textarea.py' method='post'>
Extract package files (.zip, .tar.gz, .tar.bz2)
</td><td colspan=2>
<input type=checkbox name='extract_0'>
</td></tr>
<tr><td colspan=2>
Submit mRSL files (also .mRSL files included in packages)
</td><td colspan=2>
<input type=checkbox name='submitmrsl_0' CHECKED>
</td></tr>
<tr><td>    
File to upload
</td><td class=righttext colspan=3>
<input name='fileupload_0_0_0' type='file' size='50'/>
</td></tr>
<tr><td>
Optional remote filename (extra useful in windows)
</td><td class=righttext colspan=3>
<input name='default_remotefilename_0' type='hidden' value='%(dest_dir)s'/>
<input name='remotefilename_0' type='input' size='50' value='%(dest_dir)s'/>
<input type='submit' value='Upload' name='sendfile'/>
</form>
</td></tr>
</table>
""" % {'default_mrsl':default_mrsl, 'dest_dir':('.' + os.sep)}})

    return (output_objects, status)


