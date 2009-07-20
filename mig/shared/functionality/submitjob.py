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
from shared.fileio import unpickle
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.mrslkeywords import get_job_specs
from shared.refunctions import list_runtime_environments
from shared.settings import load_settings
from shared.useradm import mrsl_template, get_default_mrsl, client_id_dir
from shared.vgrid import user_allowed_vgrids, default_vgrid


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def available_choices(configuration, client_id, field, spec):
    """Find the available choices for the selectable field.
    Tries to lookup all valid choices from configuration if field is
    specified to be a string variable.
    """
    if 'boolean' == spec['Type']:
        choices = [True, False]
    elif 'string' == spec['Type']:
        try:
            choices = getattr(configuration, '%ss' % field.lower())
        except AttributeError, exc:
            print exc
            choices = []
    else:
        choices = []
    default = spec['Value']
    if default in choices:
        choices = [default] + [i for i in choices if not default == i]
    return choices


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)
    client_dir = client_id_dir(client_id)
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

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

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
The full list of keywords with their default values and format is available in the on-demand <a href='docs.py?show=job'>mRSL Documentation</a>.
<p>
Actual examples for inspiration:
<a href=/cpuinfo.mRSL>CPU Info</a>,
<a href=/basic-io.mRSL>Basic I/O</a>,
<a href=/notification.mRSL>Job Notification</a>,
<a href=/povray.mRSL>Povray</a> and
<a href=/vcr.mRSL>VCR</a>
</div>
    """})
    default_mrsl = get_default_mrsl(template_path)
    settings_dict = load_settings(client_id, configuration)
    if not settings_dict or not settings_dict.has_key('SUBMITUI'):
        logger.info('Settings dict does not have SUBMITUI key - using default'
                    )
        submit_style = configuration.submitui[0]
    else:
        submit_style = settings_dict['SUBMITUI']

    if 'fields' == submit_style:
        output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Please fill in your job description in the fields below:'
                              })
        output_objects.append({'object_type': 'html_form', 'text'
                              : """
<table class="submitjob">
<form method="post" action="jobobjsubmit.py" id="miginput">
"""
                              })
        show_fields = get_job_specs(configuration)
        allowed_vgrids = user_allowed_vgrids(configuration, client_id) + ['ANY']
        allowed_vgrids.sort()
        (re_status, allowed_run_envs) = list_runtime_environments(configuration)
        allowed_run_envs.sort()
        extra_selects = 3
        field_size = 30
        area_cols = 80
        area_rows = 5
        for (field, spec) in show_fields:
            title = spec['Title']
            field_type = spec['Type']
            default = spec['Value']
            # TODO: override with default_mrsl
            if 'invisible' == spec['Editor']:
                continue
            if 'custom' == spec['Editor']:
                continue
            output_objects.append({'object_type': 'html_form', 'text'
                                       : """<br>
<b>%s:</b>&nbsp;<a href='docs.py?show=job#%s'>help</a><br>""" % (title, field)
                                   })
            if 'input' == spec['Editor']:
                if field_type.startswith('multiple'):
                    output_objects.append({'object_type': 'html_form', 'text'
                                           : """
<textarea name='%s' cols='%d' rows='%d'></textarea>
""" % (field, area_cols, area_rows)
                                   })
                else:
                    output_objects.append({'object_type': 'html_form', 'text'
                                           : """
<input type='text' name='%s' size='%d' value='%s'>
""" % (field, field_size, default)
                                   })
            elif 'select' == spec['Editor']:
                choices = available_choices(configuration, client_id,
                                            field, spec)
                res_value = default
                value_select = ''
                value_select += "<select name='%s'>\n" % field
                for name in choices:
                    selected = ''
                    if res_value == name:
                        selected = 'selected'
                    value_select += """<option %s value='%s'>%s</option>\n""" % (selected, name, name)
                value_select += """</select><br>\n"""    
                output_objects.append({'object_type': 'html_form', 'text'
                                       : value_select
                                       })
            output_objects.append({'object_type': 'html_form', 'text'
                                       : """<br><br>"""
                                   })

        # Not all resource fields here map directly to keywords/specs input field
    
        (title, field) = ('VGrid Participation', 'vgrid')
        exe_vgrids = []
        show = exe_vgrids + ['' for i in range(extra_selects)]
        vgrid_select = ''
        for active in show:
            vgrid_select += "<select name='exe-vgrid'>\n"
            for name in allowed_vgrids + ['']:
                selected = ''
                if active == name:
                    selected = 'selected'
                vgrid_select += """<option %s value='%s'>%s</option>\n""" % (selected, name, name)
            vgrid_select += """</select><br>\n"""    
        output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='docs.py?show=job#%s'>help</a><br>
%s
<br>""" % (title, field, vgrid_select)
                           })
        
        (title, field) = ('Runtime Environments', 'RUNTIMEENVIRONMENT')
        re_list = []
        show = re_list + [('', []) for i in range(extra_selects)]
        re_select = "<input type='hidden' name='runtime_env_fields' value='%s'>\n" % len(show)
        i = 0
        for active in show:
            re_select += "<select name='runtimeenvironment%d'>\n" % i
            for name in allowed_run_envs + ['']:
                selected = ''
                if active[0] == name:
                    selected = 'selected'
                re_select += """<option %s value='%s'>%s</option>\n""" % (selected, name, name)
            re_select += """</select><br>\n"""
            values = '\n'.join(['%s=%s' % pair for pair in active[1]])
            re_select += "<textarea cols='%d' rows='%d' name='re_values%d'>%s</textarea><br>\n" % \
                         (area_cols, area_rows, i, values)
            i += 1

        output_objects.append({'object_type': 'html_form', 'text'
                               : """<br>
<b>%s:</b>&nbsp;<a href='docs.py?show=job#%s'>help</a><br>
Please enter any required environment variable settings on the form NAME=VALUE in the box below
each selected runtimeenvironment.<br>
%s
<br>""" % (title, field, re_select)
                           })

        output_objects.append({'object_type': 'html_form', 'text'
                              : """
<tr>
<td><br></td>
<td class=centertext>
<input type="submit" value="Submit Job">
</td>
<td><br></td>
</tr>
</form>
</table>
"""
                               })
    else:
        output_objects.append({'object_type': 'sectionheader', 'text'
                              : 'Please enter your mRSL job description below:'
                              })
        output_objects.append({'object_type': 'html_form', 'text'
                              : """
<!-- 
Please note that textarea.py chokes if no nonempty KEYWORD_X_Y_Z fields 
are supplied: thus we simply send a bogus jobname which does nothing
-->
<table class="submitjob">
<tr><td class=centertext>
<form method="post" action="textarea.py" id="miginput">
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
"""
                               % {'default_mrsl': default_mrsl}})

    # Upload form

    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<br>
<table class='files'>
<tr class=title><td class=centertext colspan=4>
Upload file
</td></tr>
<tr><td colspan=4>
Upload file to current directory (%(dest_dir)s)
</td></tr>
<tr><td colspan=2>
<form enctype='multipart/form-data' action='textarea.py' method='post'>
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
"""
                           % {'dest_dir': '.' + os.sep}})

    return (output_objects, status)


