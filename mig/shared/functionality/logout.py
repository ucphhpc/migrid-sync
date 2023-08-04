#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# logout - force-expire local login session(s)
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Simple backend to force login session expiry"""

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.auth import expire_twofactor_session
from mig.shared.base import requested_backend
from mig.shared.defaults import AUTH_CERTIFICATE, AUTH_OPENID_V2, \
    AUTH_OPENID_CONNECT, AUTH_MIG_OID, AUTH_EXT_OID, AUTH_MIG_OIDC, \
    AUTH_EXT_OIDC
from mig.shared.functional import validate_input_and_cert
from mig.shared.gdp.all import project_logout, get_client_id_from_project_client_id
from mig.shared.httpsclient import extract_client_id, detect_client_auth, \
    require_twofactor_setup, build_logout_url, extract_client_openid
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.useradm import expire_oid_sessions, find_oid_sessions


def signature():
    """Signature of the main function"""

    defaults = {'logout': ['false']}
    return ['text', defaults]


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

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
    do_logout = accepted['logout'][-1].lower() in ('true', '1')

    # sub-container inside default IU container
    output_objects.append({'object_type': 'html_form', 'text': '''
        <div class="global-full-height row">
            <div class="col-12 align-self-center">
    '''})

    output_objects.append({'object_type': 'header', 'text': 'Logout'})
    (auth_type, auth_flavor) = detect_client_auth(configuration, environ)
    identity = extract_client_id(configuration, environ, lookup_dn=False)
    logger.info("%s from %s with identity %s" % (op_name, client_id, identity))
    if not client_id:
        output_objects.append(
            {'object_type': 'warning', 'text':
             """You're accessing %s on the address without authentication info,
so there's no session to logout. If you are in fact logged in you need to use
logout from the corresponding authenticated web pages.
""" % configuration.short_title})
        return (output_objects, status)
    elif auth_type == AUTH_CERTIFICATE:
        output_objects.append(
            {'object_type': 'warning', 'text':
             """You're accessing %s with a user certificate so to completely
logout you need to make sure it is protected by a password and then close the
browser. Please refer to your browser and system documentation for details.
""" % configuration.short_title})
        return (output_objects, status)

    title_entry = find_entry(output_objects, 'title')

    # Always rely on os.environ here as that's what we have
    environ = os.environ
    script_name = requested_backend(environ, strip_ext=False)
    # Check if twofactor is mandatory and not yet set up
    forced_twofactor = require_twofactor_setup(configuration, script_name,
                                               client_id, environ)
    if forced_twofactor:
        # Hide usual menu entries to only allow logout
        title_entry['base_menu'] = [i for i in title_entry['base_menu']
                                    if i in ['setup', 'logout']]
        title_entry['user_menu'] = []

    # OpenID requires logout on provider and in local mod-auth-openid database.
    # IMPORTANT: some browsers like Firefox may inadvertently renew the local
    # OpenID session while loading the resources for this page (in parallel).
    # User clicks logout at OpenID provider, which sends her back here to
    # finish the local logout.

    if do_logout:
        if configuration.site_enable_twofactor:
            real_user = client_id
            addr_filter = environ['REMOTE_ADDR']
            # GDP logout is for project user so we strip project to force
            # repeat 2FA login on project logout / switch
            if configuration.site_enable_gdp:
                real_user = get_client_id_from_project_client_id(configuration,
                                                                 client_id)
                addr_filter = None
            if real_user and not expire_twofactor_session(configuration,
                                                          real_user, environ,
                                                          allow_missing=True,
                                                          user_addr=addr_filter):
                logger.warning("expire twofactor session failed for %s" %
                               client_id)
                output_objects.append(
                    {'object_type': 'html_form', 'text':
                     """<p class='warningtext'>
There was a potential problem with 2-factor session termination. Please contact
the %s Admins if it happens repeatedly.
</p>""" % configuration.short_title
                     })
        if auth_type == AUTH_OPENID_V2:
            (oid_db, identity) = extract_client_openid(configuration, environ,
                                                       lookup_dn=False)
            logger.info("expiring active sessions for %s in %s" % (identity,
                                                                   oid_db))
            (success, _) = expire_oid_sessions(configuration, oid_db, identity)
            logger.info("verifying no active sessions left for %s" % identity)
            (found, remaining) = find_oid_sessions(
                configuration, oid_db, identity)
        elif auth_type == AUTH_OPENID_CONNECT:
            # NOTE: mod auth oidc handles local logout automatically
            logger.info("no manual cleanup needed for %s session of %s" %
                        (auth_type, identity))
            success, found, remaining = True, True, []
        else:
            logger.error("unexpected auth_type %r in logout for in %s" %
                         (auth_type, identity))
            output_objects.append(
                {'object_type': 'warning', 'text':
                 """You're accessing %s with %s credentials not covered by
logout, so to completely logout you need to make sure they are protected by a
password and then close the browser. Please refer to your browser and system
documentation for details.""" % (configuration.short_title, auth_type)})
            return (output_objects, status)

        if success and found and not remaining:
            if configuration.site_enable_gdp:
                reentry_page = "https://%s" % configuration.server_fqdn
                if auth_type == AUTH_OPENID_V2:
                    if auth_flavor == AUTH_MIG_OID:
                        reentry_page = configuration.migserver_https_mig_oid_url
                    elif auth_flavor == AUTH_EXT_OID:
                        reentry_page = configuration.migserver_https_ext_oid_url
                elif auth_type == AUTH_OPENID_CONNECT:
                    if auth_flavor == AUTH_MIG_OIDC:
                        reentry_page = configuration.migserver_https_mig_oidc_url
                    elif auth_flavor == AUTH_EXT_OIDC:
                        reentry_page = configuration.migserver_https_ext_oidc_url
                project_logout(
                    configuration, 'https', environ['REMOTE_ADDR'], client_id)
                html = """
                <a id='gdp_logout' href='%s'></a>
                <script type='text/javascript'>
                    document.getElementById('gdp_logout').click();
                </script>""" % reentry_page
                output_objects.append(
                    {'object_type': 'html_form', 'text': html})
            else:
                output_objects.append(
                    {'object_type': 'text', 'text':
                     """You are now logged out of %s locally - you may want to
close your web browser to finish""" % configuration.short_title})
                title_entry['skipmenu'] = True

        else:
            logger.error("remaining active sessions for %s: %s" % (identity,
                                                                   remaining))
            output_objects.append({'object_type': 'error_text', 'text':
                                   "Could not log you out of %s!"
                                   % configuration.short_title})
            status = returnvalues.CLIENT_ERROR
    else:
        logout_url = build_logout_url(configuration, environ)
        output_objects.append(
            {'object_type': 'text', 'text': """Are you sure you want to
log out of %s?""" % configuration.short_title})
        output_objects.append({'object_type': 'text', 'text': ""})
        output_objects.append(
            {'object_type': 'link', 'destination': logout_url,
             'class': 'genericbutton greenBtn', 'text': "Yes"})
        output_objects.append(
            {'object_type': 'link',
             'destination': 'javascript:history.back();',
             'class': 'genericbutton greenBtn', 'text': "No, go back"})
    # sub-container end
    output_objects.append({'object_type': 'html_form', 'text': '''
            </div>
        </div>
    '''})

    return (output_objects, status)
