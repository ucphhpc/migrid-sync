#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminre - set up a runtime environment
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

"""Create runtime environment"""

from __future__ import absolute_import

import base64

from mig.shared import returnvalues
from mig.shared.defaults import max_software_entries, max_environment_entries, \
    csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables
from mig.shared.refunctions import is_runtime_environment, \
    list_runtime_environments, get_re_dict
from mig.shared.rekeywords import get_keywords_dict


def signature():
    """Signature of the main function"""

    defaults = {
        're_template': [''],
        'software_entries': [-1],
        'environment_entries': [-1],
        'testprocedure_entry': [-1],
    }
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    output_objects.append(
        {'object_type': 'header', 'text': 'Create runtime environment'})
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
    re_template = accepted['re_template'][-1].upper().strip()
    software_entries = int(accepted['software_entries'][-1])
    environment_entries = int(accepted['environment_entries'][-1])
    testprocedure_entry = int(accepted['testprocedure_entry'][-1])

    template = {}
    if re_template:
        if not is_runtime_environment(re_template, configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "re_template ('%s') is not a valid existing runtime env!"
                 % re_template})
            return (output_objects, returnvalues.CLIENT_ERROR)

        (template, msg) = get_re_dict(re_template, configuration)
        if not template:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not read re_template %s. %s'
                                   % (re_template, msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # Override template fields if user loaded a template and modified the
    # required entries and chose update.
    # Use default of 1 sw, 1 env and 0 test or template setting otherwise
    if software_entries < 0:
        software_entries = len(template.get('SOFTWARE', [None]))
    if environment_entries < 0:
        environment_entries = len(template.get('ENVIRONMENTVARIABLE', [None]))
    if testprocedure_entry < 0:
        testprocedure_entry = len(template.get('TESTPROCEDURE', []))
    if 'SOFTWARE' in template:
        new_sw = template['SOFTWARE'][:software_entries]
        template['SOFTWARE'] = new_sw
    if 'ENVIRONMENTVARIABLE' in template:
        new_env = template['ENVIRONMENTVARIABLE'][:environment_entries]
        template['ENVIRONMENTVARIABLE'] = new_env
    if 'TESTPROCEDURE' in template:
        new_test = template['TESTPROCEDURE'][:testprocedure_entry]
        template['TESTPROCEDURE'] = new_test

    # Avoid DoS, limit number of software_entries

    if software_entries > max_software_entries:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Maximum number of software_entries %s exceeded (%s)' %
             (max_software_entries, software_entries)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Avoid DoS, limit number of environment_entries

    if environment_entries > max_environment_entries:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Maximum number of environment_entries %s exceeded (%s)' %
             (max_environment_entries, environment_entries)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    rekeywords_dict = get_keywords_dict()
    (list_status, ret) = list_runtime_environments(configuration)
    if not list_status:
        output_objects.append({'object_type': 'error_text', 'text': ret})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append(
        {'object_type': 'text', 'text':
         'Use existing Runtime Environment as template'})

    html_form = \
        """<form method='get' action='adminre.py'>
    <select name='re_template'>
    <option value=''>None</option>
"""
    for existing_re in ret:
        html_form += "    <option value='%s'>%s</option>\n" % \
                     (existing_re, existing_re)
    html_form += """
    </select>
    <input type='submit' value='Get' />
</form>"""
    output_objects.append({'object_type': 'html_form', 'text': html_form})

    output_objects.append(
        {'object_type': 'text', 'text':
         '''Note that a runtime environment can not be changed after creation
and it can only be removed if not in use by any resources, so please be careful
when filling in the details'''
         })
    output_objects.append(
        {'object_type': 'text', 'text':
         '''Changing the number of software and environment entries removes
all data in the form, so please enter the correct values before entering any
information.'''
         })

    html_form = \
        """<form method='get' action='adminre.py'>
    <table>
"""
    html_form += """
<tr>
    <td>Number of needed software entries</td>
    <td><input type='number' name='software_entries' min=0 max=99
    minlength=1 maxlength=2 value='%s' required pattern='[0-9]{1,2}'
    title='number of software entries needed in runtime environment' /></td>
</tr>""" % software_entries
    html_form += """
<tr>
    <td>Number of environment entries</td>
    <td>
    <input type='number' name='environment_entries' min=0 max=99
    minlength=1 maxlength=2 value='%s' required pattern='[0-9]{1,2}'
    title='number of environment variables provided by runtime environment' />
    </td>
</tr>""" % environment_entries
    output_objects.append({'object_type': 'html_form', 'text': html_form})
    if testprocedure_entry == 0:
        select_string = """<option value='0' selected>No</option>
<option value=1>Yes</option>"""
    elif testprocedure_entry == 1:
        select_string = """<option value='0'>No</option>
<option value='1' selected>Yes</option>"""
    else:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'testprocedure_entry should be 0 or 1, you specified %s'
             % testprocedure_entry})
        return (output_objects, returnvalues.CLIENT_ERROR)

    html_form = """
<tr>
    <td>Runtime environment has a testprocedure</td>
    <td><select name='testprocedure_entry'>%s</select></td>
</tr>
<tr>
    <td colspan=2>
    <input type='hidden' name='re_template' value='%s' />
    <input type='submit' value='Update fields' />
    </td>
</tr>
</table>
</form><br />
""" % (select_string, re_template)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'short_title': configuration.short_title,
                    'form_method': form_method,
                    'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'createre'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    html_form += """
<form method='%(form_method)s' action='%(target_op)s.py'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<b>Runtime Environment Name</b><br />
<small>(eg. BASH-2.X-1, must be unique):</small><br />
<input class='p80width' type='text' name='re_name' required 
    pattern='[a-zA-Z0-9_.-]+'
    title='unique name of ASCII letters and digits separated only by underscores, periods and hyphens' />
<br />
<br /><b>Description:</b><br />
<textarea class='p80width' rows='4' name='redescription'>
"""
    if template:
        html_form += template['DESCRIPTION'].replace('<br />', '\n')
    html_form += '</textarea><br />'

    soft_list = []
    if software_entries > 0:
        html_form += '<br /><b>Needed Software:</b><br />'
    if template:
        if 'SOFTWARE' in template:
            soft_list = template['SOFTWARE']
            for soft in soft_list:
                html_form += """
<textarea class='p80width' rows='6' name='software'>"""
                for keyname in soft:
                    if keyname != '':
                        html_form += '%s=%s\n' % (keyname, soft[keyname])
                html_form += '</textarea><br />'

    # loop and create textareas for any missing software entries

    software = rekeywords_dict['SOFTWARE']
    sublevel_required = []
    sublevel_optional = []

    if 'Sublevel' in software and software['Sublevel']:
        sublevel_required = software['Sublevel_required']
        sublevel_optional = software['Sublevel_optional']

    for _ in range(len(soft_list), software_entries):
        html_form += """
<textarea class='p80width' rows='6' name='software'>"""
        for sub_req in sublevel_required:
            html_form += '%s=   # required\n' % sub_req
        for sub_opt in sublevel_optional:
            html_form += '%s=   # optional\n' % sub_opt
        html_form += '</textarea><br />'

    if template and testprocedure_entry == 1:
        if 'TESTPROCEDURE' in template:
            html_form += """
<br /><b>Testprocedure</b> (in mRSL format):<br />
<textarea class='p80width' rows='15' name='testprocedure'>"""

            base64string = ''
            for stringpart in template['TESTPROCEDURE']:
                base64string += stringpart
                decodedstring = base64.decodestring(base64string)
                html_form += decodedstring
            html_form += '</textarea>'
            output_objects.append(
                {'object_type': 'html_form', 'text': html_form})

            html_form = """
<br /><b>Expected .stdout file if testprocedure is executed</b><br />
<textarea class='p80width' rows='10' name='verifystdout'>"""

            if 'VERIFYSTDOUT' in template:
                for line in template['VERIFYSTDOUT']:
                    html_form += line
            html_form += '</textarea>'

            html_form += """
<br /><b>Expected .stderr file if testprocedure is executed</b><br />
<textarea cols='50' rows='10' name='verifystderr'>"""
            if 'VERIFYSTDERR' in template:
                for line in template['VERIFYSTDERR']:
                    html_form += line
            html_form += '</textarea>'

            html_form += """
<br /><b>Expected .status file if testprocedure is executed</b><br />
<textarea cols='50' rows='10' name='verifystatus'>"""
            if 'VERIFYSTATUS' in template:
                for line in template['VERIFYSTATUS']:
                    html_form += line
            html_form += '</textarea>'
    elif testprocedure_entry == 1:

        html_form += """
<br /><b>Testprocedure</b> (in mRSL format):<br />
<textarea class='p80width' rows='15' name='testprocedure'>"""

        html_form += \
            """::EXECUTE::
ls    
</textarea>
<br /><b>Expected .stdout file if testprocedure is executed</b><br />
<textarea class='p80width' rows='10' name='verifystdout'></textarea>
<br /><b>Expected .stderr file if testprocedure is executed</b><br />
<textarea class='p80width' rows='10' name='verifystderr'></textarea>
<br /><b>Expected .status file if testprocedure is executed</b><br />
<textarea class='p80width' rows='10' name='verifystatus'></textarea>
"""

    environmentvariable = rekeywords_dict['ENVIRONMENTVARIABLE']
    sublevel_required = []
    sublevel_optional = []

    if 'Sublevel' in environmentvariable\
            and environmentvariable['Sublevel']:
        sublevel_required = environmentvariable['Sublevel_required']
        sublevel_optional = environmentvariable['Sublevel_optional']

    env_list = []
    if environment_entries > 0:
        html_form += '<br /><b>Environments:</b><br />'
    if template:
        if 'ENVIRONMENTVARIABLE' in template:
            env_list = template['ENVIRONMENTVARIABLE']
            for env in env_list:
                html_form += """
<textarea class='p80width' rows='4' name='environment'>"""
                for keyname in env:
                    if keyname != '':
                        html_form += '%s=%s\n' % (keyname, env[keyname])
                html_form += '</textarea><br />'

    # loop and create textareas for any missing environment entries

    for _ in range(len(env_list), environment_entries):
        html_form += """
<textarea class='p80width' rows='4' name='environment'>"""
        for sub_req in sublevel_required:
            html_form += '%s=   # required\n' % sub_req
        for sub_opt in sublevel_optional:
            html_form += '%s=   # optional\n' % sub_opt
        html_form += '</textarea><br />'

    html_form += """<br /><br /><input type='submit' value='Create' />
    </form>
"""
    output_objects.append({'object_type': 'html_form', 'text':
                           html_form % fill_helpers})
    return (output_objects, returnvalues.OK)
