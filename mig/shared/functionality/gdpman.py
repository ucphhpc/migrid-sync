#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# gdpman - Sensitive Information Facility management
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

# TODO: this backend is horribly KU/UCPH-specific, should move that to conf

"""Management of Sensitive Information Facility"""

import os
import tempfile

from shared.auth import expire_twofactor_session, get_twofactor_secrets
import shared.returnvalues as returnvalues
from shared.base import get_xgi_bin
from shared.defaults import csrf_field
from shared.functional import validate_input_and_cert
from shared.gdp import ensure_user, get_projects, get_users, \
    project_accept, project_create, project_invite, project_login, \
    project_logout, project_remove_user, validate_user
from shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from shared.html import themed_styles, jquery_ui_js, twofactor_wizard_html, \
    twofactor_wizard_js
from shared.httpsclient import extract_client_openid
from shared.init import initialize_main_variables, find_entry
from shared.settings import load_twofactor, parse_and_save_twofactor
from shared.useradm import get_full_user_map
from shared.url import openid_autologout_url
from shared.vgrid import vgrid_create_allowed
from shared.twofactorkeywords import get_keywords_dict as twofactor_keywords


def signature():
    """Signature of the main function"""

    defaults = {
        'action': [''],
        'base_vgrid_name': [''],
        'gdp_workzone_id': [''],
        'username': [''],
        'status_msg': [''],
    }
    return ['text', defaults]


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
    fill_entries['workzone_help_icon'] = "%s/icons/help.png" \
        % configuration.site_images
    fill_entries['workzone_help_txt'] = \
        "The workzone nummer is the Journal number from the acceptance of processing personal data." \
        + " Use 000000 as the workzone number if your project does not require a workzone registration."

    twofactor_enabled = False
    create_projects = False
    accepted_projects = False
    invited_projects = False
    invite_projects = False
    remove_projects = False

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
        accepted_projects = get_projects(configuration, client_id,
                                         'accepted')
        invited_projects = get_projects(configuration, client_id, 'invited')
        invite_projects = get_projects(
            configuration, client_id, 'accepted', owner_only=True)
        remove_projects = get_projects(
            configuration, client_id, 'accepted', owner_only=True)

    # Generate html

    html = \
        """
        <form id='gm_project_submit_form' action='gdpman.py', method='post'>
        <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
        <input type='hidden' name='action' value='' />
        <input type='hidden' name='base_vgrid_name' value='' />
        <input type='hidden' name='username' value='' />
        <input type='hidden' name='gdp_workzone_id' value='' />
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
        html += """<li><a href='#access'>Access project</a></li>"""
        tab_count += 1
    if create_projects:
        html += """<li><a href='#create'>Create project</a></li>"""
        if action == 'create':
            preselected_tab = tab_count
        tab_count += 1
    if invite_projects:
        html += """<li><a href='#invite'>Invite participant</a></li>"""
        if action == 'invite':
            preselected_tab = tab_count
        tab_count += 1
    if invited_projects:
        html += """<li><a href='#accept'>Accept invitation</a></li>"""
        if action == 'accept_invite':
            preselected_tab = tab_count
        tab_count += 1
    if remove_projects:
        html += """<li><a href='#remove'>Remove participant</a></li>"""
        if action == 'remove':
            preselected_tab = tab_count
        tab_count += 1
    if configuration.site_enable_twofactor:
        html += """<li><a href='#twofactor'>Two-Factor Auth</a></li>"""
        if action == 'twofactor':
            preselected_tab = tab_count
        tab_count += 1

    html += """</ul>"""
    html += """
        <script type='text/javascript'>
            var preselected_tab = %s;
        </script>""" % preselected_tab

    if status_msg:
        status_html = \
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
        for project in sorted(accepted_projects):
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
        </form>
        </div>"""

    # Show project invitations selectbox

    if invited_projects:
        html += \
            """
        <div id='accept'>"""
        html += status_html
        html +=  \
            """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>Accept invite:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>
                <div class='styled-select gm_select semi-square'>
                <select name='accept_invite_base_vgrid_name'>
                <option value=''>Choose project</option>
                <option value=''>───────</option>"""
        for project in sorted(invited_projects):
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
                <a class='ui-button' id='accept_invite' href='#' onclick='submitform(\"accept_invite\"); return false;'>Accept</a>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </form>
        </div>"""

    # Show project invite selectbox

    if invite_projects:
        html += \
            """
        <div id='invite'>"""
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
                <select name='invite_base_vgrid_name'>
                <option value=''>Choose project</option>
                <option value=''>───────</option>"""
        for project in sorted(invite_projects):
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
                <input name='invite_user_id' type='text' size='30'/>
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
                <a class='ui-button' id='invite' href='#' onclick='submitform(\"invite\"); return false;'>Invite</a>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </form>
        </div>
        """

    # Show project remove selectbox

    if remove_projects:
        html += \
            """
        <div id='remove'>"""
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
                <select name='remove_base_vgrid_name'>
                <option value=''>Choose project</option>
                <option value=''>───────</option>"""
        for project in sorted(remove_projects):
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
                <input name='remove_user_id' type='text' size='30'/>
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
                <a class='ui-button' id='remove' href='#' onclick='submitform(\"remove\"); return false;'>Remove</a>
                <a class='ui-button' id='logout' href='#' onclick='submitform(\"logout\"); return false;'>Logout</a>
            </td></tr>
        </tbody>
        </table>
        </form>
        </div>
        """

    # Show project create selectbox

    if create_projects:
        html += \
            """
        <div id='create'>"""
        html += status_html
        html +=  \
            """
        <table class='gm_projects_table' style='border-spacing=0;'>
        <thead>
            <tr>
                <th>Create new project:</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>
                Workzone number: <a title='%(workzone_help_txt)s' href='#' onclick='return false;'><img align='top' src='%(workzone_help_icon)s' /></a>
                </td>
            </tr>
            <tr>
                <td>
                <input name='create_workzone_id' type='text' size='30'/>
                </td>
            </tr>
            <tr>
                <td>
                Name:
                </td>
            </tr>
            <tr>
                <td>
                <input name='create_base_vgrid_name' type='text' size='30'/>
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
        </form>
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
</script>
        """

    fill_helpers.update({
        'client_id': client_id,
    })

    fill_entries.update(fill_helpers)

    html += """
        </div>
        """

    # Tabs and form close tags

    html += \
        """
        </div>
        </form>"""
    html = html % fill_entries

    if preselected_tab > 0:
        html += \
            """
            <script type='text/javascript'>
                $(selector).tabs('option', 'active', %s);
            </script>
            """ % preselected_tab
    return html


def html_logout_tmpl(configuration, csrf_token):
    """HTML logout template for GDP manager"""

    fill_entries = {}
    fill_entries['csrf_field'] = csrf_field
    fill_entries['csrf_token'] = csrf_token

    html = \
        """
    <form id='gm_logout_form' action='gdpman.py', method='post'>
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


def css_tmpl(configuration):
    """Stylesheets to include in the page header
    Selectbox CSS from : https://codepen.io/ericrasch/pen/zjDBx
    TODO: Turn into MiG css ?
    """

    css = themed_styles(configuration)

    # TODO: move this custom css to style sheets where it belongs

    css['base'] += \
        """
<style>
    .gm_projects_table {
        padding-left: 25px;
        padding-top: 5px;
        padding-bottom: 5px;
    }
    .gm_projects_table th {
        padding-right: 50px;
        padding-top: 7px;
        padding-bottom: 7px;
        text-align: left;
    }
    .gm_projects_table td {
        padding-left: 10px;
        text-align: left;
    }

    /* -------------------- Select Box Styles: bavotasan.com Method (with special adaptations by ericrasch.com) */
    /* -------------------- Source: http://bavotasan.com/2011/style-select-box-using-only-css/ */

    .styled-select {
       background: url(/images/icons/select_arrow.png) no-repeat 96% 0;
       background-size: 25px 25px;
       height: 25px;
       overflow: hidden;
       width: 240px;
       max-width: 240px;
    }

    .styled-select select {
       background: transparent;
       border: none;
       font-size: 13px;
       height: 25px;
       overflow: hidden;
       padding: 3px; /* If you add too much padding here, the options won't show in IE */
       width: 268px;
       max-width: 268px;
    }

    .semi-square {
       -webkit-border-radius: 5px;
       -moz-border-radius: 5px;
       border-radius: 5px;
    }

    /* -------------------- Colors: Background */
    .gm_select {
        background-color: #679c5b;
    }

    /* -------------------- Colors: Text */
    .gm_select select {
        color: #fff;
    }

    /* Set the desired color for the focus state */
    .gm_select select:focus {
        background-color: #679c5b;
        color: #fff;
    }

    /* Make M$ IE and EDGE behave like other browsers */
    .gm_select select:focus::-ms-value {
        background: #679c5b;
        color:  #fff;
    }
}

</style>"""

    return css


def js_tmpl(configuration):
    """Javascript to include in the page header"""

    (tfa_import, tfa_init, tfa_ready) = twofactor_wizard_js(configuration)
    js_import = ''
    js_import += tfa_import
    js_init = """
    function submitform(project_action) {
        if (project_action == 'access') {
            if ($('#gm_project_form select[name=access_base_vgrid_name]').val() !== '') {
                $('#gm_project_submit_form input[name=action]').val(project_action);
                $('#gm_project_submit_form input[name=base_vgrid_name]').val(
                    $('#gm_project_form select[name=access_base_vgrid_name]').val());
                $('#gm_project_submit_form').submit();
            }
        }
        else if (project_action == 'accept_invite') {
            if ($('#gm_project_form select[name=accept_invite_base_vgrid_name]').val() !== '') {
                $('#gm_project_submit_form input[name=action]').val(project_action);
                $('#gm_project_submit_form input[name=base_vgrid_name]').val(
                    $('#gm_project_form select[name=accept_invite_base_vgrid_name]').val());
                $('#gm_project_submit_form').submit();
            }
        }
        else if (project_action == 'invite') {
            if ($('#gm_project_form select[name=base_vgrid_name]').val() !== '' &&
                    $('#gm_project_form input[name=invite_user_id]').val() !== '') {
                $('#gm_project_submit_form input[name=action]').val(project_action);
                $('#gm_project_submit_form input[name=base_vgrid_name]').val(
                    $('#gm_project_form select[name=invite_base_vgrid_name]').val());
                $('#gm_project_submit_form input[name=username]').val(
                    $('#gm_project_form input[name=invite_user_id]').val());
                $('#gm_project_submit_form').submit();
            }
        }
        else if (project_action == 'remove') {
            if ($('#gm_project_form select[name=remove_base_vgrid_name]').val() !== '' &&
                    $('#gm_project_form input[name=remove_user_id]').val() !== '') {
                $('#gm_project_submit_form input[name=action]').val(project_action);
                $('#gm_project_submit_form input[name=base_vgrid_name]').val(
                    $('#gm_project_form select[name=remove_base_vgrid_name]').val());
                $('#gm_project_submit_form input[name=username]').val(
                    $('#gm_project_form input[name=remove_user_id]').val());
                $('#gm_project_submit_form').submit();
            }
        }
        else if (project_action == 'create') {
            if ($('#gm_project_form input[name=create_base_vgrid_name]').val() !== '' &&
                    $('#gm_project_form input[name=create_workzone_id]').val() !== '') {
                $('#gm_project_submit_form input[name=action]').val(project_action);
                $('#gm_project_submit_form input[name=base_vgrid_name]').val(
                    $('#gm_project_form input[name=create_base_vgrid_name]').val());
                $('#gm_project_submit_form input[name=gdp_workzone_id]').val(
                    $('#gm_project_form input[name=create_workzone_id]').val());
                $('#gm_project_submit_form').submit();
            }
        }
        else if (project_action == 'logout') {
            $('#gm_project_submit_form input[name=action]').val(project_action);
            $('#gm_project_submit_form').submit();
        }
        else if (project_action == 'enable2fa') {
            $('#gm_project_submit_form input[name=action]').val(project_action);
            $('#gm_project_submit_form').submit();
        }
    }

%s
    """ % tfa_init
    js_ready = """
        $('#project-tabs').tabs({
            collapsible: false,
            active: preselected_tab
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
    workzone_id = accepted['gdp_workzone_id'][-1].strip()
    username = accepted['username'][-1].strip()

    # Generate header, title, css and js

    title_text = 'SIF Management'
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = title_text
    title_entry['style'] = css_tmpl(configuration)
    title_entry['javascript'] = js_tmpl(configuration, )

    output_objects.append({'object_type': 'header',
                           'class': 'gdpman-title', 'text': title_text})

    # Validate Access

    if not configuration.site_enable_gdp:
        output_objects.append({'object_type': 'error_text',
                               'text': """SIF disabled on this site.
Please contact the Grid admins %s if you think it should be enabled.
"""
                               % configuration.admin_email})
        return (output_objects, returnvalues.ERROR)
    if client_id and client_id == identity:
        output_objects.append({'object_type': 'error_text',
                               'text':
                               'CERT user credentials _NOT_ supported by this site.'})
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
            else:
                value = keywords_dict[keyword]['value']
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

        (parse_status, parse_msg) = \
            parse_and_save_twofactor(tmptopicfile, client_id,
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
            html = \
                """
            <a id='gdp_twofactorlogin' href='%s'></a>
            <script type='text/javascript'>
                document.getElementById('gdp_twofactorlogin').click();
            </script>""" \
                % environ['SCRIPT_URI']

        output_objects.append({'object_type': 'html_form',
                               'text': html})

        return (output_objects, returnvalues.OK)

    if not action and identity or action == 'logout':
        autologout = project_logout(configuration,
                                    'https',
                                    client_addr,
                                    client_id,
                                    autologout=True)

        if autologout or action == 'logout':
            return_url = req_url
            if action == 'logout':
                return_query_dict = None
            else:
                return_query_dict = user_arguments_dict

            html = \
                """
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

    ensure_user(configuration, client_addr, client_id)
    (validate_status, validate_msg) = validate_user(configuration,
                                                    client_id,
                                                    client_addr,
                                                    'https')
    if not validate_status:
        html = \
            """
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
            % validate_msg
        html += html_logout_tmpl(configuration, csrf_token)
        output_objects.append({'object_type': 'html_form',
                               'text': html})
    else:

        # Entry page

        status = True
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
                html = \
                    """
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
        elif action == 'accept_invite':

            # Project accept invitation

            (status, msg) = project_accept(configuration, client_addr,
                                           client_id, base_vgrid_name)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg

        elif action == 'invite':
            gdp_users = get_users(configuration)

            if not username in gdp_users.keys():
                status = False
                msg = "'%s' is _NOT_ a valid user id" % username
                _logger.error("gdpman: Invite user: %s" % msg)

            if status:

                # Project invitation

                invite_client_id = gdp_users[username]
                (status, msg) = project_invite(configuration,
                                               client_addr,
                                               client_id,
                                               invite_client_id,
                                               base_vgrid_name)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg

        elif action == 'remove':
            gdp_users = get_users(configuration)

            if not username in gdp_users.keys():
                status = False
                msg = "'%s' is _NOT_ a valid user id" % username
                _logger.error("gdpman: Remove user: %s" % msg)

            if status:

                # Project invitation

                remove_client_id = gdp_users[username]
                (status, msg) = project_remove_user(configuration,
                                                    client_addr,
                                                    client_id,
                                                    remove_client_id,
                                                    base_vgrid_name)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg

        elif action == 'create':

            # Project create

            logger.debug(": %s : creating project: '%s' : %s : from ip: %s'"
                         % (client_id,
                            base_vgrid_name,
                            workzone_id,
                            client_addr))

            # Check workzone_id

            create_workzone_id = ''
            if not workzone_id:
                status = False
                msg = "missing workzone number"

            elif workzone_id != '000000':
                workzone_id = create_workzone_id

            if status:
                (status, msg) = project_create(configuration,
                                               client_addr,
                                               client_id,
                                               base_vgrid_name,
                                               create_workzone_id)
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
        #html += html_logout_tmpl(configuration, csrf_token)
        output_objects.append({'object_type': 'html_form',
                               'text': html})

    return (output_objects, returnvalues.OK)
