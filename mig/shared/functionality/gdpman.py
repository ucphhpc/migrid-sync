#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# gdpman - entry point with project access and management for GDP-enabled sites
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

"""Entry page with project access and management for GDP-enabled sites"""

import os
import tempfile

from shared.auth import expire_twofactor_session, get_twofactor_secrets
import shared.returnvalues as returnvalues
from shared.base import get_xgi_bin
from shared.defaults import csrf_field
from shared.functional import validate_input_and_cert
from shared.gdp import ensure_user, get_projects, get_users, \
    get_active_project_client_id, project_accept_user, project_create, \
    project_invite_user, project_login, project_logout, project_remove_user, \
    validate_user
from shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from shared.html import themed_styles, jquery_ui_js, twofactor_wizard_html, \
    twofactor_wizard_js, twofactor_token_html
from shared.httpsclient import extract_client_openid
from shared.init import initialize_main_variables, find_entry
from shared.settings import load_twofactor, parse_and_save_twofactor
from shared.useradm import get_full_user_map
from shared.url import openid_autologout_url
from shared.vgrid import vgrid_create_allowed, vgrid_manage_allowed
from shared.twofactorkeywords import get_keywords_dict as twofactor_keywords


def signature():
    """Signature of the main function"""

    defaults = {
        'action': [''],
        'base_vgrid_name': [''],
        'gdp_category_id': [''],
        'gdp_ref_id': [''],
        'gdp_ref_value': [''],
        'username': [''],
        'status_msg': [''],
    }
    return ['text', defaults]


def fill_category(configuration, category_id, action, ref_dict):
    """Fill a data category dict for *category_id* based on configuration
    categories for *action* and actual reference values in *ref_dict*.
    Raises ValueError if one or more required category reference fields are
    missing from ref_dict or if category doesn't exist in data categories.
    """
    _logger = configuration.logger
    _logger.debug('fill %s dict from %s %s values' % (category_id, action,
                                                      ref_dict))
    category_dict = {'category_id': category_id}
    # _logger.debug('build map to fill %s %s dict from: %s' %
    #              (category_id, action, configuration.gdp_data_categories))
    category_map = dict([(i['category_id'], i) for i in
                         configuration.gdp_data_categories])
    if not category_map.has_key(category_id):
        raise ValueError('no such data category: %s' % category_id)
    category_dict.update(category_map[category_id])
    # _logger.debug('fill %s dict %s with %s values' % (category_id,
    #                                                  category_dict,
    #                                                  ref_dict))
    for ref_fill in category_dict.get('references', {}).get(action, []):
        key = ref_fill['ref_id']
        if not ref_dict.has_key(key):
            raise ValueError('no %s value' % key)
        ref_fill['value'] = ref_dict[key]
    _logger.debug('filled %s dict: %s' % (category_id, category_dict))
    return category_dict


def html_category_fields(configuration, action):
    """Helper to generate dynamic form category fields for a *action* based on
    the configured and chosen project data categories. Uses a general form
    class layout to easily show/hide with javascript code based on project
    selection.
    """
    fields = "<!-- dynamic fields for %s -->" % action
    for category_entry in configuration.gdp_data_categories:
        # Make a local copy for filling
        specs = {}
        specs.update(category_entry)
        specs['hidden'] = 'hidden'
        for ref_dict in category_entry.get('references', {}).get(action, []):
            # Copy to avoid changing
            ref_fill = {'action': action}
            ref_fill.update(specs)
            ref_fill.update(ref_dict)
            # Default to anything as value if not set in ref_dict
            ref_fill['ref_pattern'] = ref_fill.get('ref_pattern', '.*')
            ref_fill['ref_name'] = ref_fill.get('ref_name', '')
            ref_fill['ref_text'] = ref_fill.get('ref_text', '')
            ref_fill['ref_help_html'] = ''
            if ref_fill.get('ref_help', ''):
                ref_fill['ref_help_icon'] = "%s/icons/help.png" % \
                    configuration.site_images
                ref_fill['ref_help_html'] = """
<span  class='fakelink'
    onclick='showHelp(\"%(ref_name)s Help\", \"%(ref_help)s\");'>
<img align='top' src='%(ref_help_icon)s' title='%(ref_help)s'>
</span>""" % ref_fill

            fields += """
        <tr class='%(action)s %(category_id)s_section category_section %(hidden)s'>
            <td>
            %(ref_name)s: %(ref_help_html)s<br/>
            </td>
        </tr>
        <tr class='%(action)s %(category_id)s_section category_section %(hidden)s'>
            <td>
            <div class='ref_field'>
            """ % ref_fill
            if ref_fill.get('ref_type', 'text') == "checkbox":
                fields += """
                <!-- NOTE: make a checkbox with ref_id and name --> 
                <input id='%(action)s_%(ref_id)s' class='%(category_id)s_ref category_ref'
                    name='%(action)s_%(ref_id)s' required title='%(ref_help)s'
                    type='checkbox' /> %(ref_text)s
                """ % ref_fill
            else:
                fields += """
            <!-- NOTE: keep a single field for ref with ref_id in name -->
            <input id='%(action)s_%(ref_id)s' class='%(category_id)s_ref category_ref'
                name='%(action)s_%(ref_id)s' required pattern='%(ref_pattern)s'
                placeholder='%(ref_name)s' title='%(ref_help)s'
                type='text' size='30' />
                """ % ref_fill
            fields += """
            </div>
            </td>
        </tr>
            """ % ref_fill
    return fields


def html_tmpl(
        configuration,
        action,
        client_id,
        csrf_token,
        status_msg):
    """HTML main template for GDP manager"""

    fill_entries = {}
    fill_entries['csrf_field'] = csrf_field
    fill_entries['csrf_token'] = csrf_token

    twofactor_enabled = False
    create_projects = False
    accepted_projects = False
    invited_projects = False
    invite_projects = False
    remove_projects = False
    await_projects = False

    if configuration.site_enable_twofactor:
        current_twofactor_dict = load_twofactor(client_id, configuration)
        if not current_twofactor_dict:
            # no current twofactor found
            current_twofactor_dict = {}
        if current_twofactor_dict:
            twofactor_enabled = True

    if not configuration.site_enable_twofactor \
            or (configuration.site_enable_twofactor and twofactor_enabled):
        user_map = get_full_user_map(configuration)
        user_dict = user_map.get(client_id, None)

        if user_dict and vgrid_create_allowed(configuration,
                                              user_dict):
            create_projects = True
        if user_dict and vgrid_manage_allowed(configuration,
                                              user_dict):
            invite_projects = get_projects(
                configuration, client_id, 'accepted', owner_only=True)
            remove_projects = get_projects(
                configuration, client_id, 'accepted', owner_only=True)
        accepted_projects = get_projects(configuration, client_id,
                                         'accepted')
        invited_projects = get_projects(configuration, client_id, 'invited')

    # Gather all projects known to user and use in await and category map
    known_projects = {}
    for entry in [invite_projects, remove_projects, accepted_projects,
                  invited_projects]:
        if entry and isinstance(entry, dict):
            known_projects.update(entry)
    await_projects = (not create_projects and not known_projects)

    # Generate html

    status_html = ""
    html = ""
    if configuration.site_enable_twofactor:
        html += """
<div id='help_dialog' class='centertext hidden'></div>
<div id='otp_verify_dialog' title='Verify Authenticator App Token'
   class='centertext hidden'>
"""
        # NOTE: wizard needs dialog with form outside the main settings form
        # because nested forms cause problems
        html += twofactor_token_html(configuration)
        html += """</div>
"""
    html += """
        <form id='gm_project_submit_form' action='gdpman.py' method='post'>
        <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
        <input type='hidden' name='action' value='' />
        <input type='hidden' name='base_vgrid_name' value='' />
        <input type='hidden' name='username' value='' />
        <input type='hidden' name='gdp_category_id' value='' />
        <div class='volatile_fields'><!-- dynamic JS ref fields --></div>
        </form>
        <form id='gm_project_form'>
        """

    # Show project tabs

    tab_count = 0
    preselected_tab = 0

    html += \
        """
        <div id='project-tabs'>
        <ul class='fillwidth padspace'>"""
    if accepted_projects:
        html += """<li><a href='#access'>Access Project</a></li>"""
        tab_count += 1
    if create_projects:
        html += """<li><a href='#create'>Create Project</a></li>"""
        if action == 'create':
            preselected_tab = tab_count
        tab_count += 1
    if invite_projects:
        html += """<li><a href='#invite_user'>Invite Participant</a></li>"""
        if action == 'invite_user':
            preselected_tab = tab_count
        tab_count += 1
    if invited_projects:
        html += """<li><a href='#accept_user'>Accept Invitation</a></li>"""
        if action == 'accept_user':
            preselected_tab = tab_count
        tab_count += 1
    if remove_projects:
        html += """<li><a href='#remove_user'>Remove Participant</a></li>"""
        if action == 'remove_user':
            preselected_tab = tab_count
        tab_count += 1
    if await_projects:
        html += """<li><a href='#await'>Await Invitation</a></li>"""
        if action == 'await':
            preselected_tab = tab_count
        tab_count += 1
    if configuration.site_enable_twofactor:
        html += """<li><a href='#twofactor'>Two-Factor Auth</a></li>"""
        if action == 'twofactor':
            preselected_tab = tab_count
        tab_count += 1

    html += """</ul>"""
    # Insert category map helper for all known projects
    category_map = dict([(key, val['category_meta']['category_id']) for (key, val) in
                         known_projects.items()])
    html += """
        <script type='text/javascript'>
            preselected_tab = %s;
            /* Initialize category_map */
            category_map = %s;
        </script>""" % (preselected_tab, category_map)

    if status_msg:
        status_html += \
            """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>Status:</th>
            </tr>
        </thead>
        <tbody>
        <tr><td id='status_msg'>%s</td></tr>
        </tbody>
        </table>""" % status_msg

    # Show login projects selectbox

    if accepted_projects:
        html += \
            """
        <div id='access'>"""
        html += status_html
        html += \
            """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>Access project:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <div class='styled-select gm_select semi-square'>
                <select name='access_base_vgrid_name'>
                <option value=''>Choose project</option>
                <option value=''>───────</option>"""
        for project in sorted(accepted_projects.keys()):
            html += \
                """
                <option value='%s'>%s</option>""" \
                % (project, project)
        html += \
            """
                <option value=''>───────</option>
                </select>
                </div>
            </td></tr>
        </tbody>
        </table>
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='ui-button' id='access' href='#' onclick='submitform(\"access\"); return false;'>Login</a>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </div>"""

    # Show project invitations selectbox

    if invited_projects:
        html += \
            """
        <div id='accept_user'>"""
        html += status_html
        html +=  \
            """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>Accept project invitation:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <div class='styled-select gm_select semi-square'>
                <select name='accept_user_base_vgrid_name' onChange='selectAcceptUserProject(value);'>
                <option value=''>Choose project</option>
                <option value=''>───────</option>"""
        for project in sorted(invited_projects.keys()):
            html += \
                """
                <option value='%s'>%s</option>""" \
                % (project, project)
        html += \
            """
                <option value=''>───────</option>
                </select>
                </div>
            </td></tr>
            """

        # Insert all category refs but show only the ones for chosen project
        html += html_category_fields(configuration, 'accept_user')
        html += """
        </tbody>
        </table>
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='ui-button' id='accept_user' href='#' onclick='submitform(\"accept_user\"); return false;'>Accept</a>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </div>"""

    # Show project invite selectbox

    if invite_projects:
        html += \
            """
        <div id='invite_user'>"""
        html += status_html
        html +=  \
            """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>Invite project participant:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <div class='styled-select gm_select semi-square'>
                <select name='invite_user_base_vgrid_name' onChange='selectInviteUserProject(value);'>
                <option value=''>Choose project</option>
                <option value=''>───────</option>"""
        for project in sorted(invite_projects.keys()):
            html += \
                """
                <option value='%s'>%s</option>""" % (project, project)
        html += \
            """
                <option value=''>───────</option>
                </select>
                </div>
                </td></tr>
            <tr>
                <td>
                User id:
                </td>
            </tr><tr>
                <td>
                <input name='invite_user_short_id' required placeholder='User ID'
                    title='Email of user to invite' type='email' size='30'/>
            </td></tr>
            """

        # Insert all category refs but show only the ones for chosen project
        html += html_category_fields(configuration, 'invite_user')
        html += """
        </tbody>
        </table>
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='ui-button' id='invite_user' href='#' onclick='submitform(\"invite_user\"); return false;'>Invite</a>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </div>
        """

    # Show project remove selectbox

    if remove_projects:
        html += \
            """
        <div id='remove_user'>"""
        html += status_html
        html +=  \
            """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>Remove project participant:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <div class='styled-select gm_select semi-square'>
                <select name='remove_user_base_vgrid_name' onChange='selectRemoveUserProject(value);'>
                <option value=''>Choose project</option>
                <option value=''>───────</option>"""
        for project in sorted(remove_projects.keys()):
            html += \
                """
                <option value='%s'>%s</option>""" \
                % (project, project)
        html += \
            """
                <option value=''>───────</option>
                </select>
                </div>
                </td></tr>
            <tr>
                <td>
                User id:
                </td>
            </tr><tr>
                <td>
                <input name='remove_user_short_id' required placeholder='User ID'
                    title='Email of user to remove' type='email' size='30'/>
            </td></tr>
            """

        # Insert all category refs but show only the ones for chosen project
        html += html_category_fields(configuration, 'remove_user')
        html += """
        </tbody>
        </table>
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='ui-button' id='remove_user' href='#' onclick='submitform(\"remove_user\"); return false;'>Remove</a>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </div>
        """

    # Show project create selectbox

    if create_projects:
        html += """
        <div id='create'>"""
        html += status_html
        html += """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>Create new project:</th>
            </tr>
        </thead>
        <tbody>
        """
        category_html, ref_html = "", ""
        default_category = False
        for category_entry in configuration.gdp_data_categories:
            # Make a local copy for filling
            specs = {}
            specs.update(category_entry)
            # Let first be selected and visible, then hide the rest
            if not default_category:
                default_category = category_entry['category_id']
                specs['hidden'] = ''
            else:
                specs['hidden'] = 'hidden'

            category_html += """
<input id='%(category_id)s_radio' name='create_category' type='radio'
    value='%(category_id)s' onClick='selectRef(\"create\", \"%(category_id)s\");'/>
    <span class='category_title'>%(category_title)s</span>
            """ % specs
            for ref_dict in category_entry.get('references', {}).get('create',
                                                                     []):
                # Copy to avoid changing
                ref_fill = {}
                ref_fill.update(specs)
                ref_fill.update(ref_dict)
                # Default to anything as value if not set in ref_dict
                ref_fill['ref_pattern'] = ref_fill.get('ref_pattern', '.*')
                ref_fill['ref_name'] = ref_fill.get('ref_name', '')
                ref_fill['ref_text'] = ref_fill.get('ref_text', '')
                ref_fill['ref_help_html'] = ''
                if ref_fill.get('ref_help', ''):
                    ref_fill['ref_help_icon'] = "%s/icons/help.png" % \
                        configuration.site_images
                    ref_fill['ref_help_html'] = """
    <span  class='fakelink'
        onclick='showHelp(\"%(ref_name)s Help\", \"%(ref_help)s\");'>
    <img align='top' src='%(ref_help_icon)s' title='%(ref_help)s'>
    </span>""" % ref_fill

                ref_html += """
            <tr class='create %(category_id)s_section category_section %(hidden)s'>
                <td>
                %(ref_name)s: %(ref_help_html)s<br/>
                </td>
            </tr>
            <tr class='create %(category_id)s_section category_section %(hidden)s'>
                <td>
                <div class='ref_field'>
                """ % ref_fill
                if ref_fill.get('ref_type', 'text') == "checkbox":
                    ref_html += """
                <!-- NOTE: make a checkbox with ref_id and name --> 
                <input id='create_%(ref_id)s' class='%(category_id)s_ref category_ref'
                    name='create_%(ref_id)s' required title='%(ref_help)s'
                    type='checkbox' /> %(ref_text)s
                """ % ref_fill
                else:
                    ref_html += """
                <!-- NOTE: keep a single field for ref with ref_id in name --> 
                <input id='create_%(ref_id)s' class='%(category_id)s_ref category_ref'
                    name='create_%(ref_id)s' required pattern='%(ref_pattern)s'
                    placeholder='%(ref_name)s' title='%(ref_help)s'
                    type='text' size='30' />
                """ % ref_fill
                ref_html += """
                </div>
                </td>
            </tr>
            """ % ref_fill
        if configuration.gdp_data_categories:
            html += """
            <tr>
                <td>
                Data Category:
                </td>
            </tr>
            <tr>
                <td>
                <div id='category_select'>
                %s
                </div>
                <script type='text/javascript'>
                    /* force click to override browser cache */
                    $('#%s_radio').click();
                </script>
                <br/>
            </td>
            </tr>
            """ % (category_html, default_category)
            html += ref_html
        html += """
            <tr>
                <td>
                Name:
                </td>
            </tr>
            <tr>
                <td>
                <input name='create_base_vgrid_name' type='text' size='30'
                required pattern='.+' placeholder='%s Name'
                title='A name for your project or data set'/>
            </td></tr>
        </tbody>
        </table>
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='ui-button' id='create' href='#' onclick='submitform(\"create\"); return false;'>Create</a>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </div>
        """ % configuration.site_vgrid_label

    # Show project await message

    if await_projects:
        html += \
            """
        <div id='await'>"""
        html += status_html
        html +=  \
            """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>No project access yet:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
            It appears you don't have permission to create projects, and you
            neither have projects to access nor pending project invitations to
            accept.
            </td></tr>
            <tr><td>
            Please contact you collaboration partner(s) and have them
            invite you to join their project for access.
            </td></tr>
            <tr><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </div>
        """

    # 2-FA

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'site': configuration.short_title,
                    'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    if configuration.site_enable_twofactor:

        html += \
            """
        <div id='twofactor'>
            """
        html += """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>2-Factor Authentication</th>
            </tr>
        </thead>
        <tbody>
        """
        b32_key, otp_uri = get_twofactor_secrets(configuration, client_id)
        # We limit key exposure by not showing it in clear and keeping it
        # out of backend dictionary with indirect generation only.

        # TODO: we might want to protect QR code with repeat basic login
        #       or a simple timeout since last login (cookie age).
        html += twofactor_wizard_html(configuration)
        check_url = '/%s/twofactor.py' % get_xgi_bin(configuration)
        if twofactor_enabled:
            enable_hint = 'enable it (as you already did)'
        else:
            enable_hint = 'enable it below'
        fill_helpers.update({'otp_uri': otp_uri, 'b32_key': b32_key,
                             'check_url': check_url, 'demand_twofactor':
                             'demand', 'enable_hint': enable_hint})

        html += """
        <tr class='otp_ready hidden'><td>
        </td></tr>
        """

        if not twofactor_enabled:
            html += """<tr class='otp_ready hidden'><td>
        Enable 2-factor authentication and<br/>
        <a class='ui-button' href='#' onclick='submitform(\"enable2fa\"); return false;'>Start Using %(site)s</a>
</td></tr>
"""

        html += """
        <tr><td>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
</tbody>
</table>
</div>
"""

    if configuration.site_enable_twofactor and \
        (current_twofactor_dict.get("MIG_OID_TWOFACTOR", False) or
         current_twofactor_dict.get("EXT_OID_TWOFACTOR", False)):
        html += """<script>
    setOTPProgress(['otp_intro', 'otp_install', 'otp_import', 'otp_verify',
                    'otp_ready']);
</script>"""

    fill_helpers.update({
        'client_id': client_id,
    })

    fill_entries.update(fill_helpers)

    html += """
</div>"""

    # Tabs and form close tags

    html += """
</form>
"""
    html = html % fill_entries

    return html


def html_logout_tmpl(configuration, csrf_token):
    """HTML logout template for GDP manager"""

    fill_entries = {}
    fill_entries['csrf_field'] = csrf_field
    fill_entries['csrf_token'] = csrf_token

    html = \
        """
    <form id='gm_logout_form' action='gdpman.py' method='post'>
    <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
    <input type='hidden' name='action' value='' />
    <table class='gm_projects_table' style='border-spacing=0;'>
    <thead>
        <tr>
            <th></th>
        </tr>
    </thead>
    <tbody>
        <tr><td>
            <!-- NOTE: must have href for correct cursor on mouse-over -->
            <a class='genericbutton' id='access' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
        </td></tr>
    </tbody>
    </table>
    </form>""" \
        % fill_entries
    return html


def js_tmpl(configuration):
    """Javascript to include in the page header"""

    (tfa_import, tfa_init, tfa_ready) = twofactor_wizard_js(configuration)
    js_import = ''
    js_import += tfa_import
    js_init = """
    var preselected_tab = 0;
    var category_map = {};

    function selectRef(project_action, category_id) {
        /* Hide and disable inactive input fields to avoid interference */
        $('.category_section.'+project_action).hide();
        $('.'+category_id+'_section.'+project_action).show();
        $('.'+category_id+'_section.'+project_action+' .category_ref').prop('disabled', true);
        $('.'+category_id+'_section.'+project_action+' .category_ref').prop('disabled', false);
    }
    function selectInviteUserProject(project_name) {
        /* Helper to switch category fields on project select in invite_user tab */
        var category_id = category_map[project_name];
        selectRef('invite_user', category_id);
    }
    function selectAcceptUserProject(project_name) {
        /* Helper to switch category fields on project select in accept_user tab */
        var category_id = category_map[project_name];
        selectRef('accept_user', category_id);
    }
    function selectRemoveUserProject(project_name) {
        /* Helper to switch category fields on project select in remove_user tab */
        var category_id = category_map[project_name];
        selectRef('remove_user', category_id);
    }
    function extractProject(project_action) {
        var project_name = '';
        var err_help = 'selected'
        if (project_action === 'create') {
            project_name = $('#gm_project_form input[name='+project_action+'_base_vgrid_name]').val();
            err_help = 'name provided';
        } else {
            project_name = $('#gm_project_form select[name='+project_action+'_base_vgrid_name]').val();
        }
        if (!project_name) {
            showError('Input Error', 'No project '+err_help+'!');
            return null;
        }
        return project_name;
    }
    function extractUser(project_action) {
        var user_name = $('#gm_project_form input[name='+project_action+'_short_id]').val();
        /* TODO: switch to select drop-down in remove user? */
        if (! $('#gm_project_form input[name='+project_action+'_short_id]')[0].checkValidity()) {
            console.error('user field is missing or not on required format!');
            //console.debug(project_action+'_short_id: '+user_name);
            showError('Value Error', 'User missing or not on required format!');
            return null;
        }
        return user_name;
    }
    function extractCategory(project_action, project_name) {
        var category_name = '';
        var err_help = 'found';
        if (!project_name) {
            /* No project selected (already handled elsewhere) */
            console.error('project_name unset - cannot extract category!');
            return null;
        } else if (project_action === 'create') {
            category_name = $('#gm_project_form input[name='+project_action+'_category]:checked').val();
            err_help = 'selected';
        } else {
            /* Extract category from category_map for project_name */
            if (project_name in category_map) {
                category_name = category_map[project_name];
            } else {
                console.error('project_name '+project_name+' not found in category_map');
            }
        }
        if (category_name === '') {
            showError('Input Error', 'No data category '+err_help+' for the \"'+project_name+'\" project.<br/>Please contact the site admins.');
            return null;
        }
        return category_name;
    }
    function handleStaticFields(project_action, project_name, user_name, category_name) {
        if (project_action === null || project_name === null || user_name === null || category_name === null) {
            console.error('one or more errors in static fields!');
            return false;
        }
        $('#gm_project_submit_form input[name=action]').val(project_action);
        $('#gm_project_submit_form input[name=base_vgrid_name]').val(project_name);
        $('#gm_project_submit_form input[name=username]').val(user_name);
        $('#gm_project_submit_form input[name=gdp_category_id]').val(category_name);
        return true;
    }
    function handleDynamicFields(project_action, category_name) {
        /* Check validity of dynamic fields */
        var valid_fields = true;
        $('#gm_project_form .'+category_name+'_section.'+project_action+' input:enabled').each(
                function() {
                    var ref_id = $(this).attr('id').replace(project_action+'_', '');
                    var ref_val = $(this).val();
                    //console.debug('checking: '+ref_id+': '+ref_val);
                    var valid_value = $(this)[0].checkValidity();
                    //console.debug(ref_id+' valid: '+valid_value);
                    if (!valid_value) {
                        showError('Value Error', 'Provided '+ref_id+' value is not on the required format!<p>'+$(this).attr('title')+'</p>');
                        console.error(ref_id+' value '+ref_val+' is invalid!');
                    }
                    valid_fields &= valid_value;
                });
        if (!valid_fields) {
            console.error('one or more form fields are missing or not on required format!');
            return false;
        }

        $('#gm_project_submit_form .volatile_fields').empty();
        //console.debug('cleared gdp helper form: '+ $('#gm_project_submit_form').html());
        /* Loop through any project_action references and transfer in turn */
        //console.debug('loop through refs and transfer values');
        /* pick active category input fields */
        $('#gm_project_form .'+category_name+'_section.'+project_action+' input:enabled').each(
            function() {
                var ref_id, ref_val, field;
                if ($(this).val() !== '') {
                    ref_id = $(this).attr('id').replace(project_action+'_', '');
                    ref_val = $(this).val();
                    //console.debug('set '+ref_id+': '+ref_val);
                    /* NOTE: add ref input fields dynamically */
                    //$('#gm_project_submit_form input[name=gdp_ref_id]').val(ref_id);
                    field = '<input name=\"gdp_ref_id\" type=hidden value=\"';
                    field += ref_id + '\">\\n';
                    $('#gm_project_submit_form .volatile_fields').append(field);
                    field = '<input name=\"gdp_ref_value\" type=hidden value=\"';
                    field += ref_val + '\">\\n';
                    $('#gm_project_submit_form .volatile_fields').append(field);
                }
            }
        );
        console.debug('ready to submit form: '+$('#gm_project_submit_form').html());
        return true;
    }
    function submitform(project_action) {
        /* Clear any stale data from previous form submits first */
        $('#gm_project_submit_form').trigger('reset');
        if (project_action == 'access') {
            var project_name = extractProject(project_action);
            if (!handleStaticFields(project_action, project_name, '', '')) return false;
            $('#gm_project_submit_form').submit();
        }
        else if (project_action == 'accept_user') {
            var project_name = extractProject(project_action);
            var category_name = extractCategory(project_action, project_name);
            if (!handleStaticFields(project_action, project_name, '', category_name)) return false;
            if (!handleDynamicFields(project_action, category_name)) return false;
            $('#gm_project_submit_form').submit();
        }
        else if (project_action == 'invite_user') {
            var project_name = extractProject(project_action);
            var user_name = extractUser(project_action);
            var category_name = extractCategory(project_action, project_name);
            if (!handleStaticFields(project_action, project_name, user_name, category_name)) return false;
            if (!handleDynamicFields(project_action, category_name)) return false;
            $('#gm_project_submit_form').submit();
        }
        else if (project_action == 'remove_user') {
            var project_name = extractProject(project_action);
            var user_name = extractUser(project_action);
            var category_name = extractCategory(project_action, project_name);
            if (!handleStaticFields(project_action, project_name, user_name, category_name)) return false;
            if (!handleDynamicFields(project_action, category_name)) return false;
            $('#gm_project_submit_form').submit();
        }
        else if (project_action == 'create') {
            var project_name = extractProject(project_action);
            var category_name = extractCategory(project_action, project_name);
            if (!handleStaticFields(project_action, project_name, '', category_name)) return false;
            if (!handleDynamicFields(project_action, category_name)) return false;
            $('#gm_project_submit_form').submit();
        }
        else if (project_action == 'logout') {
            if (!handleStaticFields(project_action, '', '', '')) return false;
            $('#gm_project_submit_form').submit();
        }
        else if (project_action == 'enable2fa') {
            if (!handleStaticFields(project_action, '', '', '')) return false;
            $('#gm_project_submit_form').submit();
        }
    }

   function showHelp(title, msg) {
        $('#help_dialog').dialog('option', 'title', title);
        $('#help_dialog').html('<p>'+msg+'</p>');
        $('#help_dialog').dialog('open');
    }
   function showError(title, msg) {
        console.error(msg);
        showHelp(title, '<span class=\"warningtext\">'+msg+'</span>');
    }

%s
    """ % tfa_init
    js_ready = """
        $('#project-tabs').tabs({
            collapsible: false,
            active: preselected_tab
        });

        $('#help_dialog').dialog(
              { autoOpen: false, width: 500, modal: true, closeOnEscape: true,
                buttons: { 'Ok': function() { $(this).dialog('close'); }}
              });

    %s
    """ % tfa_ready

    return jquery_ui_js(configuration, js_import, js_init, js_ready)


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=False)
    _logger = configuration.logger
    client_addr = environ.get('REMOTE_ADDR', None)
    base_url = configuration.migserver_https_ext_oid_url
    req_url = environ.get('SCRIPT_URI', None)
    csrf_limit = get_csrf_limit(configuration)
    csrf_token = make_csrf_token(configuration, 'post', op_name,
                                 client_id, csrf_limit)
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
    (_, identity) = extract_client_openid(configuration, environ,
                                          lookup_dn=False)
    _csrf = accepted['_csrf'][-1].strip()
    action = accepted['action'][-1].strip()
    base_vgrid_name = accepted['base_vgrid_name'][-1].strip()
    gdp_category_id = accepted['gdp_category_id'][-1].strip()
    gdp_ref_id_list = [i.strip() for i in accepted['gdp_ref_id']]
    gdp_ref_value_list = [i.strip() for i in accepted['gdp_ref_value']]
    gdp_ref_pairs = zip(gdp_ref_id_list, gdp_ref_value_list)
    username = accepted['username'][-1].strip()
    if action:
        log_msg = "GDP Manager: ip: '%s', action: '%s', base_vgrid_name: '%s'"
        log_msg += ", category_id %s, references: %s, username: '%s'"
        _logger.info(log_msg % (client_addr, action, base_vgrid_name,
                                gdp_category_id, gdp_ref_pairs, username))

    # Generate header, title, css and js

    title_text = '%s %s Management' % (configuration.short_title,
                                       configuration.site_vgrid_label)
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = title_text
    title_entry['style'] = themed_styles(configuration)
    title_entry['javascript'] = js_tmpl(configuration, )

    output_objects.append({'object_type': 'header',
                           'class': 'gdpman-title', 'text': title_text})

    # Validate Access

    if not configuration.site_enable_gdp:
        output_objects.append({'object_type': 'error_text',
                               'text': """%s Management disabled on this site.
Please contact the site admins %s if you think it should be enabled.
""" % configuration.admin_email})
        return (output_objects, returnvalues.ERROR)
    if client_id and client_id == identity:
        output_objects.append({'object_type': 'error_text',
                               'text':
                               'CERT user credentials NOT supported by this site.'})
        return (output_objects, returnvalues.ERROR)
    elif not identity:
        output_objects.append({'object_type': 'error_text',
                               'text': 'Missing user credentials'})
        return (output_objects, returnvalues.ERROR)

    if action and not safe_handler(
        configuration,
        'post',
        op_name,
        client_id,
        get_csrf_limit(configuration),
        accepted,
    ):
        output_objects.append({'object_type': 'error_text',
                               'text': """Only accepting
            CSRF-filtered POST to prevent unintended updates"""
                               })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if action == 'enable2fa':

        # Expire any exisiting 2FA sessions
        # Due to browser cookies outdated 2FA sessions may be re-initiated

        expire_twofactor_session(
            configuration, client_id, environ, allow_missing=False)

        keywords_dict = twofactor_keywords(configuration)
        topic_mrsl = ''
        for keyword in keywords_dict.keys():
            if keyword.endswith('_OID_TWOFACTOR'):
                value = True
            elif keyword == 'WEBDAVS_TWOFACTOR':
                value = True
            elif keyword == 'SFTP_PASSWORD_TWOFACTOR':
                value = True
            elif keyword == 'SFTP_KEY_TWOFACTOR':
                value = True
            else:
                value = keywords_dict[keyword]['Value']
            topic_mrsl += '''::%s::
%s

''' % (keyword.upper(), value)
        try:
            (filehandle, tmptopicfile) = tempfile.mkstemp(text=True)
            os.write(filehandle, topic_mrsl)
            os.close(filehandle)
        except Exception, exc:
            msg = 'Problem writing temporary topic file on server.'
            logger.error("%s : %s" % (msg, exc))
            output_objects.append(
                {'object_type': 'error_text', 'text': msg})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        (parse_status, parse_msg) = parse_and_save_twofactor(tmptopicfile, client_id,
                                                             configuration)

        try:
            os.remove(tmptopicfile)
        except Exception, exc:
            pass  # probably deleted by parser!

        status_msg = 'OK: 2-Factor Authentication enabled'
        if not parse_status:
            status_msg = 'ERROR: Failed to enable 2-Factor Authentication'
            logger.error("%s -> %s" % (status_msg, parse_msg))
            html = status_msg
        else:
            html = """
            <a id='gdp_twofactorlogin' href='%s'></a>
            <script type='text/javascript'>
                document.getElementById('gdp_twofactorlogin').click();
            </script>""" \
                % environ['SCRIPT_URI']

        output_objects.append({'object_type': 'html_form',
                               'text': html})

        return (output_objects, returnvalues.OK)

    # Make sure user exists in GDP user db

    (status, ensure_msg) = ensure_user(configuration, client_addr, client_id)

    if status and not action or action == 'logout':
        active_project_client_id = get_active_project_client_id(
            configuration, client_id, 'https')

        if active_project_client_id or action == 'logout':
            project_logout(configuration,
                           'https',
                           client_addr,
                           client_id,
                           autologout=True)
            return_url = req_url
            if action == 'logout':
                return_query_dict = None
            else:
                return_query_dict = user_arguments_dict

            html = """
            <a id='autologout' href='%s'></a>
            <script type='text/javascript'>
                document.getElementById('autologout').click();
            </script>""" \
                % openid_autologout_url(configuration,
                                        identity,
                                        client_id,
                                        return_url,
                                        return_query_dict)

            output_objects.append({'object_type': 'html_form',
                                   'text': html})

            return (output_objects, returnvalues.OK)

    # Generate html

    if status:
        (status, validate_msg) = validate_user(configuration,
                                               client_id,
                                               client_addr,
                                               'https')
    if not status:
        status_msg = ''
        if ensure_msg:
            status_msg = ensure_msg
        elif validate_msg:
            status_msg = validate_msg
        html = """
            <table class='gm_projects_table' style='border-spacing=0;'>
            <thead>
                <tr>
                    <th>Access Denied:</th>
                </tr>
            </thead>
            <tbody>
            <tbody>
                <tr><td>%s</td></tr>
            </tbody>
            </table>""" \
            % status_msg
        html += html_logout_tmpl(configuration, csrf_token)
        output_objects.append({'object_type': 'html_form',
                               'text': html})
    else:

        # Entry page

        action_msg = ''
        if action == 'access':

            # Project login

            project_client_id = project_login(configuration,
                                              'https',
                                              client_addr,
                                              client_id,
                                              base_vgrid_name)
            if project_client_id:
                dest_op_name = 'fileman'
                base_url = environ.get('REQUEST_URI',
                                       '').split('?')[0].replace(op_name,
                                                                 dest_op_name)
                html = """
                <a id='gdp_login' href='%s'></a>
                <script type='text/javascript'>
                    document.getElementById('gdp_login').click();
                </script>""" \
                    % base_url
                output_objects.append({'object_type': 'html_form',
                                       'text': html})

                return (output_objects, returnvalues.OK)

            else:
                action_msg = "ERROR: Login to project: '%s' failed" \
                    % base_vgrid_name
        elif action == 'accept_user':

            # Project accept user invitation

            logger.debug(": %s : accept user invitation to project: '%s' : %s : from ip: %s'"
                         % (client_id,
                            base_vgrid_name,
                            gdp_ref_pairs,
                            client_addr))

            # extract owned projects and saved data category
            invited_projects = get_projects(configuration, client_id,
                                            'invited')
            if not base_vgrid_name in invited_projects.keys():
                status = False
                msg = "'%s' is NOT a valid project id" % base_vgrid_name
                _logger.error("gdpman: accept user invitation: %s" % msg)
            else:
                project = invited_projects[base_vgrid_name]
                gdp_category_id = project['category_meta']['category_id']
                if not gdp_category_id:
                    status = False
                    msg = "%s does NOT have a data category" % base_vgrid_name
                    _logger.warning("gdpman: accept user invitation: %s" % msg)
                    gdp_category_id = 'UNKNOWN'

            if status:
                # Check and fill references

                try:
                    category_entry = fill_category(configuration,
                                                   gdp_category_id, action,
                                                   dict(gdp_ref_pairs))
                except ValueError, err:
                    status = False
                    msg = "missing reference: %s" % err

                (status, msg) = project_accept_user(configuration, client_addr,
                                                    client_id, base_vgrid_name,
                                                    category_entry)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg

        elif action == 'invite_user':

            # Project invitation

            logger.debug(": %s : invite user %s to project: '%s' : %s : from ip: %s'"
                         % (client_id,
                            username,
                            base_vgrid_name,
                            gdp_ref_pairs,
                            client_addr))

            gdp_users = get_users(configuration)

            if not username in gdp_users.keys():
                status = False
                msg = "'%s' is NOT a valid user id" % username
                _logger.error("gdpman: Invite user: %s" % msg)

            # extract owned projects and saved data category
            invite_projects = get_projects(configuration, client_id,
                                           'accepted', owner_only=True)
            if not base_vgrid_name in invite_projects.keys():
                status = False
                msg = "'%s' is NOT a valid project id" % base_vgrid_name
                _logger.error("gdpman: Invite user: %s" % msg)
            else:
                project = invite_projects[base_vgrid_name]
                gdp_category_id = project['category_meta']['category_id']
                if not gdp_category_id:
                    status = False
                    msg = " %s does NOT have a data category" % base_vgrid_name
                    _logger.warning("gdpman: invite user: %s" % msg)
                    gdp_category_id = 'UNKNOWN'

            if status:
                # Check and fill references

                try:
                    category_entry = fill_category(configuration,
                                                   gdp_category_id, action,
                                                   dict(gdp_ref_pairs))
                except ValueError, err:
                    status = False
                    msg = "missing reference: %s" % err

                invite_client_id = gdp_users[username]
                (status, msg) = project_invite_user(configuration,
                                                    client_addr,
                                                    client_id,
                                                    invite_client_id,
                                                    base_vgrid_name,
                                                    category_entry)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg

        elif action == 'remove_user':

            # Project remove user

            gdp_users = get_users(configuration)

            if not username in gdp_users.keys():
                status = False
                msg = "'%s' is NOT a valid user id" % username
                _logger.error("gdpman: Remove user: %s" % msg)

            # extract owned projects and saved data category
            remove_projects = get_projects(
                configuration, client_id, 'accepted', owner_only=True)
            if not base_vgrid_name in remove_projects.keys():
                status = False
                msg = "'%s' is NOT a valid project id" % base_vgrid_name
                _logger.error("gdpman: Remove user: %s" % msg)
            else:
                project = remove_projects[base_vgrid_name]
                gdp_category_id = project['category_meta']['category_id']
                if not gdp_category_id:
                    status = False
                    msg = "%s does NOT have a data category" % base_vgrid_name
                    _logger.warning("gdpman: remove user: %s" % msg)
                    gdp_category_id = 'UNKNOWN'

            if status:
                # Check and fill references

                try:
                    category_entry = fill_category(configuration,
                                                   gdp_category_id, action,
                                                   dict(gdp_ref_pairs))
                except ValueError, err:
                    status = False
                    msg = "missing reference: %s" % err

                remove_client_id = gdp_users[username]
                (status, msg) = project_remove_user(configuration,
                                                    client_addr,
                                                    client_id,
                                                    remove_client_id,
                                                    base_vgrid_name,
                                                    category_entry)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg

        elif action == 'create':

            # Project create

            logger.debug(": %s : creating project: '%s' : %s %s : from ip: %s'"
                         % (client_id,
                            base_vgrid_name,
                            gdp_category_id,
                            gdp_ref_pairs,
                            client_addr))

            # Check and fill references

            try:
                category_entry = fill_category(configuration, gdp_category_id,
                                               action, dict(gdp_ref_pairs))
            except ValueError, err:
                status = False
                msg = "missing reference: %s" % err

            if status:
                (status, msg) = project_create(configuration,
                                               client_addr,
                                               client_id,
                                               base_vgrid_name,
                                               category_entry)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg
        elif action:
            action_msg = 'ERROR: Unknown action: %s' % action

        if not action_msg:
            action_msg = validate_msg
        html = html_tmpl(configuration, action, client_id, csrf_token,
                         action_msg)
        # html += html_logout_tmpl(configuration, csrf_token)
        output_objects.append({'object_type': 'html_form',
                               'text': html})

    return (output_objects, returnvalues.OK)
