#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# logout - force-expire local login session(s)
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

"""Simple backend to force login session expiry"""

import os

import shared.returnvalues as returnvalues
from shared.auth import expire_twofactor_session
from shared.functional import validate_input_and_cert
from shared.gdp import project_logout, get_client_id_from_project_client_id
from shared.httpsclient import extract_client_openid
from shared.init import initialize_main_variables
from shared.useradm import expire_oid_sessions, find_oid_sessions


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

    output_objects.append({'object_type': 'header', 'text': 'Logout'})
    (oid_db, identity) = extract_client_openid(configuration, environ,
                                               lookup_dn=False)
    logger.info("%s from %s with identity %s" % (op_name, client_id, identity))
    if client_id and client_id == identity:
        output_objects.append(
            {'object_type': 'warning', 'text':
             """You're accessing %s with a user certificate so to completely
logout you need to make sure it is protected by a password and then close the
browser. Please refer to your browser and system documentation for details.
""" % configuration.short_title})
        return (output_objects, status)

    # OpenID requires logout on provider and in local mod-auth-openid database.
    # IMPORTANT: some browsers like Firefox may inadvertently renew the local
    # OpenID session while loading the resources for this page (in parallel).
    # User clicks logout at OpenID provider, which sends her back here to
    # finish the local logout.

    if do_logout:
        if configuration.site_enable_twofactor:
            real_user = client_id
            # GDP logout is for project user so we strip project to force
            # repeat 2FA login on project logout / switch
            if configuration.site_enable_gdp:
                real_user = get_client_id_from_project_client_id(configuration,
                                                                 client_id)
            if real_user and not expire_twofactor_session(configuration,
                                                          real_user, environ,
                                                          allow_missing=True):
                logger.warning("expire twofactor session failed for %s" %
                               client_id)
                output_objects.append(
                    {'object_type': 'html_form', 'text':
                     """<p class='warningtext'>
There was a potential problem with 2-factor session termination. Please contact
the %s Admins if it happens repeatedly.
</p>""" % configuration.short_title
                     })
        logger.info("expiring active sessions for %s in %s" % (identity,
                                                               oid_db))
        (success, _) = expire_oid_sessions(configuration, oid_db, identity)
        logger.info("verifying no active sessions left for %s" % identity)
        (found, remaining) = find_oid_sessions(configuration, oid_db, identity)
        if success and found and not remaining:
            if configuration.site_enable_gdp:
                reentry_page = "https://%s" % configuration.server_fqdn
                if configuration.user_mig_oid_provider and \
                        identity.startswith(
                            configuration.user_mig_oid_provider):
                    reentry_page = configuration.migserver_https_mig_oid_url
                elif configuration.user_ext_oid_provider and \
                        identity.startswith(
                            configuration.user_ext_oid_provider):
                    reentry_page = configuration.migserver_https_ext_oid_url
                project_logout(
                    configuration, 'https', environ['REMOTE_ADDR'], client_id)
                html = '''
                <a id='gdp_logout' href='%s'></a>
                <script type='text/javascript'>
                    document.getElementById('gdp_logout').click();
                </script>''' % reentry_page
                output_objects.append(
                    {'object_type': 'html_form', 'text': html})
            else:
                output_objects.append(
                    {'object_type': 'text', 'text': """You are now logged out of %s
    locally - you may want to close your web browser to finish"""
                     % configuration.short_title})
        else:
            logger.error("remaining active sessions for %s: %s" % (identity,
                                                                   remaining))
            output_objects.append({'object_type': 'error_text',
                                   'text': "Could not log you out of %s!"
                                   % configuration.short_title})
            status = returnvalues.CLIENT_ERROR
    else:
        local_logout = '?logout=true'
        oid_logout = os.path.join(os.path.dirname(os.path.dirname(identity)),
                                  'logout?return_to=%(SCRIPT_URI)s' % environ)
        oid_logout += local_logout
        output_objects.append(
            {'object_type': 'text', 'text': """Are you sure you want to
log out of %s?""" % configuration.short_title})
        output_objects.append(
            {'object_type': 'link', 'destination': oid_logout,
             'class': 'genericbutton', 'text': "Yes"})
        output_objects.append(
            {'object_type': 'link',
             'destination': 'javascript:history.back();',
             'class': 'genericbutton', 'text': "No, go back"})
    return (output_objects, status)
