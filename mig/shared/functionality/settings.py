#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settings - [insert a few words of module description on this line]
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

import os

import shared.returnvalues as returnvalues
from shared.fileio import unpickle
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables
from shared.settingskeywords import get_keywords_dict
from shared.useradm import client_id_dir, mrsl_template, css_template, \
    get_default_mrsl, get_default_css


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
    client_dir = client_id_dir(client_id)
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

    output_objects.append({'object_type': 'header', 'text'
                          : 'Settings'})

    # unpickle current settings

    current_settings_dict = \
        unpickle(os.path.join(configuration.user_home, client_dir,
                 '.settings'), logger)
    if not current_settings_dict:

        # no current settings found

        current_settings_dict = {}

    html = \
        """
        <div id=settings>
        <table class=settings>
        <tr class=title><td class=centertext>
        Select your MiG settings
        </td></tr>
        <tr><td>
        </td></tr>
        <tr><td>
        <form method='post' action='settingsaction.py'>
        Please note that if you want to set multiple values (e.g. addresses) in the same field, you must write each value on a separate line.
        </td></tr>
        <tr><td>
        </td></tr>
        """
    keywords_dict = get_keywords_dict()
    for (keyword, val) in keywords_dict.items():
        html += \
            """
        <tr class=title><td>
        %s
        </td></tr>
        <tr><td>
        %s
        </td></tr>
        <tr><td>
        """\
             % (keyword, val['Description'])
        if val['Type'] == 'multiplestrings':
            html += \
                """<textarea cols="40" rows="1" wrap="off" name="%s">"""\
                 % keyword
            if current_settings_dict.has_key(keyword):
                html += '<BR>'.join(current_settings_dict[keyword])
            html += '</textarea><BR>'
        elif val['Type'] == 'string':

            # get valid choices from conf

            valid_choices = eval('configuration.%s' % keyword.lower())
            current_choice = ''
            if current_settings_dict.has_key(keyword):
                current_choice = current_settings_dict[keyword]

            if len(valid_choices) > 0:
                html += '<select name=%s>' % keyword
                for choice in valid_choices:
                    selected = ''
                    if choice == current_choice:
                        selected = 'SELECTED'
                    html += '<option %s value=%s>%s</option>'\
                         % (selected, choice, choice)
                html += '</select><BR>'
        html += """
        </td></tr>
        """

    html += \
        """
    <tr><td>
    <input type="submit" value="Save">
    </form>
    </td></tr>
    </table>
    </div>
    """

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    mrsl_path = os.path.join(base_dir, mrsl_template)

    default_mrsl = get_default_mrsl(mrsl_path)
    css_path = os.path.join(base_dir, css_template)

    default_css = get_default_css(css_path)

    html += \
        '''
<div id=defaultmrsl>
<table class="defaultjob">
<tr class=title><td class=centertext>
Default job on submit page
</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you use the same fields and values in many of your jobs, you can save your preferred job description here to always start out with that description on your submit job page.
</td></tr>
<tr><td>
</td></tr>
<tr><td class=centertext>
<form method="post" action="editfile.py">
<input type="hidden" name="path" value="%(mrsl_template)s">
<input type="hidden" name="newline" value="unix">
<textarea cols="82" rows="25" wrap="off" name="editarea">
%(default_mrsl)s
</textarea>
</td></tr>
<tr><td>
<center>
<input type="submit" value="Save template">
<input type="reset" value="Forget changes">
<center>
</form>
</td></tr>
</table>
</div>
<div id=defaultcss>
<table class="defaultstyle">
<tr class=title><td class=centertext>
Default CSS (style) for all pages
</td></tr>
<tr><td>
</td></tr>
<tr><td>
If you want to customize the look and feel of the MiG web interfaces you can override default values here. If you leave the style file blank you will just use the default style.<br>
You can copy paste from the available style file links below if you want to override specific parts.<br>
Please note that you can not save an empty style file, but must at least leave a blank line to use defaults.
</td></tr>
<tr><td class=centertext>
<a href="/images/default.css">default</a> , <a href="/images/bluesky.css">bluesky</a>
</td></tr>
<tr><td>
</td></tr>
<tr><td class=centertext>
<form method="post" action="editfile.py">
<input type="hidden" name="path" value="%(css_template)s">
<input type="hidden" name="newline" value="unix">
<textarea cols="82" rows="25" wrap="off" min_len=1 name="editarea">
%(default_css)s
</textarea>
</td></tr>
<tr><td>
<center>
<input type="submit" value="Save style">
<input type="reset" value="Forget changes">
<center>
</form>
</td></tr>
</table>
</div>
'''\
         % {
        'default_mrsl': default_mrsl,
        'mrsl_template': mrsl_template,
        'default_css': default_css,
        'css_template': css_template,
        }

    output_objects.append({'object_type': 'html_form', 'text': html})

    return (output_objects, returnvalues.OK)


