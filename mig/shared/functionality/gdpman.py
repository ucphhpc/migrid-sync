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

"""Management of Sensitive Information Facility
"""

import os

import shared.returnvalues as returnvalues
from shared.defaults import csrf_field
from shared.functional import validate_input_and_cert
from shared.gdp import ensure_user, get_projects, get_users, \
    project_accept, project_create, project_invite, project_login, \
    project_logout, validate_user
from shared.handlers import safe_handler, get_csrf_limit
from shared.html import themed_styles
from shared.httpsclient import extract_client_openid
from shared.init import initialize_main_variables, find_entry
from shared.pwhash import make_csrf_token
from shared.useradm import get_full_user_map
from shared.url import base32urldecode, base32urlencode, \
    openid_autologout_url
from shared.vgrid import vgrid_create_allowed


def signature():
    """Signature of the main function"""

    defaults = {
        'action': [''],
        'vgrid_name': [''],
        'invite_client_id': [''],
        'status_msg': [''],
        }
    return ['text', defaults]


def html_tmpl(
    configuration,
    client_id,
    csrf_token,
    status_msg,
    ):
    """HTML main template for GDP manager"""

    fill_entries = {}
    fill_entries['csrf_field'] = csrf_field
    fill_entries['csrf_token'] = csrf_token
    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)

    # Optional limitation of create vgrid permission

    create_projects = True
    if not user_dict or not vgrid_create_allowed(configuration,
            user_dict):
        create_projects = False
    accepted_projects = get_projects(configuration, client_id,
            'accepted')
    invited_projects = get_projects(configuration, client_id, 'invited')
    invite_projects = get_projects(configuration, client_id, 'invite')
    gdp_users = get_users(configuration)

    # Generate html

    html = ''
    if len(status_msg) > 0:
        html += \
            """
        <table class="gm_projects_table" style="border-spacing=0;">
        <thead>
            <tr>
                <th>Status:</th>
            </tr>
        </thead>
        <tbody>
        <tr><td>%s</td></tr>
        </tbody>
        </table>""" \
            % status_msg

    # Show login projects selectbox

    if accepted_projects:
        html += \
            """
        <form id="gm_access_project_form" action="gdpman.py", method="post">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="action" value="" />
        <table class="gm_projects_table" style="border-spacing=0;">
        <thead>
            <tr>
                <th colspan="2">Access project:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td width="250px">
                <div class="styled-select gm_select_color semi-square">
                <select name="vgrid_name">"""
        for project in accepted_projects:
            html += \
                """
                <option value="%s">%s</option>""" \
                % (project, project)
        html += \
            """
                </select>
                </div>
                </td><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='genericbutton' id='access' href='#' onclick='submitform(\"access\"); return false;'>Login</a>
            </td></tr>
        </tbody>
        </table>
        </form>"""

    # Show project invitations selectbox

    if invited_projects:
        html += \
            """
        <form id="gm_accept_invite_project_form" action="gdpman.py", method="post">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="action" value="" />
        <table class="gm_projects_table" style="border-spacing=0;">
        <thead>
            <tr>
                <th colspan="2">Accept invite to project:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td width="250px">
                <div class="styled-select gm_select_color semi-square">
                <select name="vgrid_name">"""
        for project in invited_projects:
            html += \
                """
                <option value="%s">%s</option>""" \
                % (project, project)
        html += \
            """
                </select>
                </div>
                </td><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='genericbutton' id='accept_invite' href='#' onclick='submitform(\"accept_invite\"); return false;'>Accept Invite</a>
            </td></tr>
        </tbody>
        </table>
        </form>"""

    # Show project invite selectbox

    if invite_projects:
        html += \
            """
        <form id="gm_invite_project_form" action="gdpman.py", method="post">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="action" value="" />
        <table class="gm_projects_table" style="border-spacing=0;">
        <thead>
            <tr>
                <th colspan="2">Invite user to project:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td colspan="2">
                <div class="styled-select gm_select_color semi-square">
                <select name="invite_client_id">"""
        for user in gdp_users:
            if user != client_id:
                login = user.split('emailAddress=')[1].split('/')[0]
                html += \
                    """
                    <option value="%s">%s</option>""" \
                    % (base32urlencode(configuration, user), login)
        html += \
            """
                </select>
                </div>
            </td></tr>
            <tr><td width="250px">
                <div class="styled-select gm_select_color semi-square">
                <select name="vgrid_name">"""
        for project in invite_projects:
            html += \
                """
                <option value="%s">%s</option>""" \
                % (project, project)
        html += \
            """
                </select>
                </div>
                </td><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='genericbutton' id='invite' href='#' onclick='submitform(\"invite\"); return false;'>Invite</a>
            </td></tr>
        </tbody>
        </table>
        </form>
        """

    # Show project create selectbox

    if create_projects:
        html += \
            """
        <form id="gm_create_project_form" action="gdpman.py", method="post">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="action" value="" />
        <table class="gm_projects_table" style="border-spacing=0;">
        <thead>
            <tr>
                <th colspan="2">Create new project:</th>
            </tr>
        </thead>
        <tbody>
            <tr><td width="250px">
                <input name="vgrid_name" type="text" size="30"/>
                </td><td>
                <!-- NOTE: must have href for correct cursor on mouse-over -->
                <a class='genericbutton' id='create' href='#' onclick='submitform(\"create\"); return false;'>Create</a>
            </td></tr>
        </tbody>
        </table>
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
    <form id="gm_logout_form" action="gdpman.py", method="post">
    <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
    <input type="hidden" name="action" value="" />
    <table class="gm_projects_table" style="border-spacing=0;">
    <thead>
        <tr>
            <th colspan="2"></th>
        </tr>
    </thead>
    <tbody>
        <tr><td colspan="2">
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
    TODO: Turn into MiG css ?"""

    css = themed_styles(configuration)

    # TODO: move this custom css to style sheets where it belongs

    css['base'] = \
        """
<style>
    .gm_projects_table {
        #border: solid green;
        padding-left: 25px;
        padding-top: 5px;
        padding-bottom: 5px;
    }
    .gm_projects_table th {
        padding-right: 50px;
        padding-top: 7px;
        padding-bottom: 7px;
    }
    .gm_projects_table td {
        padding-left: 10px;
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
    .gm_select_color { background-color: #679c5b; }
    /* -------------------- Colors: Text */
    .gm_select_color select   { color: #fff; }

</style>"""

    return css


def js_tmpl():
    """Javascript to include in the page header"""

    js = \
        """
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript">
    function submitform(project_action) {
        if (project_action == 'access') {
            $("#gm_access_project_form input[name=action]").val(project_action);
            $("#gm_access_project_form").submit();
        }
        else if (project_action == 'accept_invite') {
            $("#gm_accept_invite_project_form input[name=action]").val(project_action);
            $("#gm_accept_invite_project_form").submit();
        }
        else if (project_action == 'invite') {
            $("#gm_invite_project_form input[name=action]").val(project_action);
            $("#gm_invite_project_form").submit();
        }
        else if (project_action == 'create') {
            $("#gm_create_project_form input[name=action]").val(project_action);
            $("#gm_create_project_form").submit();
        }
        else if (project_action == 'logout') {
            $("#gm_logout_form input[name=action]").val(project_action);
            $("#gm_logout_form").submit();
        }
    }
</script>"""

    return js


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
    project_name = accepted['vgrid_name'][-1].strip()
    invite_client_id = accepted['invite_client_id'][-1].strip()
    if invite_client_id:
        (invite_client_id, _) = base32urldecode(configuration,
                invite_client_id)
    status_msg = accepted['status_msg'][-1].strip()
    if status_msg:
        (status_msg, _) = base32urldecode(configuration, status_msg)

    # Generate header, title, css and js

    title_text = 'SIF Management'
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = title_text
    title_entry['style'] = css_tmpl(configuration)
    title_entry['javascript'] = js_tmpl()

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
                              'text': 'CERT user credentials _NOT_ supported by this site.'
                              })
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
                              'text': 'action: %s' % action})
        output_objects.append({'object_type': 'error_text',
                              'text': """Only accepting
            CSRF-filtered POST accept_invites to prevent unintended updates"""
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not action and identity or action == 'logout':
        autologout = project_logout(configuration, client_addr,
                                    client_id, autologout=True)

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
                % openid_autologout_url(configuration, identity,
                    client_id, return_url, return_query_dict)
            output_objects.append({'object_type': 'html_form',
                                  'text': html})

    # Generate html

    ensure_user(configuration, client_addr, client_id)
    (validate_status, validate_msg) = validate_user(configuration,
            client_id, client_addr)
    if not validate_status:
        html = \
            """
            <table class="gm_projects_table" style="border-spacing=0;">
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

        action_msg = ''
        if not action:
            if not status_msg:
                status_msg = validate_msg
            html = html_tmpl(configuration, client_id, csrf_token,
                             status_msg)
            html += html_logout_tmpl(configuration, csrf_token)
            output_objects.append({'object_type': 'html_form',
                                  'text': html})
        elif action == 'access':

        # Project login

            project_client_id = project_login(configuration, client_addr,
                    client_id, project_name)
            if project_client_id:
                dest_op_name = 'fileman'
                base_url = environ.get('REQUEST_URI', '').split('?'
                        )[0].replace(op_name, dest_op_name)
                html = \
                    """
                <a id='gdp_login' href='%s'></a>
                <script type='text/javascript'>
                    document.getElementById('gdp_login').click();
                </script>""" \
                    % base_url
                output_objects.append({'object_type': 'html_form',
                        'text': html})
            else:
                action_msg = 'ERROR: Login to project: %s failed' \
                    % project_name
        elif action == 'accept_invite':

        # Project accept invitation

            (status, msg) = project_accept(configuration, client_addr,
                    client_id, project_name)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg
        elif action == 'invite':

        # Project invitation

            (status, msg) = project_invite(configuration, client_addr,
                    client_id, invite_client_id, project_name)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg
        elif action == 'create':

        # Project create

            logger.debug(": %s : creating project: '%s' : from ip: %s'"
                         % (client_id, project_name, client_addr))
            (status, msg) = project_create(configuration, client_addr,
                    client_id, project_name)
            if status:
                action_msg = 'OK: %s' % msg
            else:
                action_msg = 'ERROR: %s' % msg
        else:
            action_msg = 'ERROR: Unknown action: %s' % action

        # Go to entry page and show status message

        if action and action_msg:
            html = \
                """
            <form id='gdpman_status_form' method='post' action='%s'>""" \
                % req_url
            html += \
                """
                <input type='hidden' name='status_msg' value='%s'>""" \
                % base32urlencode(configuration, action_msg)
            html += \
                """
            </form>
            <script type='text/javascript'>
                document.getElementById('gdpman_status_form').submit();
            </script>"""
            output_objects.append({'object_type': 'html_form',
                                  'text': html})

    return (output_objects, returnvalues.OK)


