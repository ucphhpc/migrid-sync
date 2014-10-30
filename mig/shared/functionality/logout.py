#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# logout - force-expire local login session
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

"""Simple back end to force login session expiry"""

import os

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert
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

    output_objects.append({'object_type': 'header', 'text'
                          : 'Logout'})
    identity = extract_client_openid(configuration, environ, lookup_dn=False)
    logger.info("%s from %s with identity %s" % (op_name, client_id, identity))
    if client_id and client_id == identity:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             """You're accessing %s with a user certificate so to completely
logout you need to make sure it is protected by a password and then close the
browser. Please refer to your browser and system documentation for details.
""" % configuration.short_title})
        return (output_objects, status)

    # OpenID requires logout on provider and in local mod-auth-openid database.
    # IMPORTANT: some browsers like Firefox may inadvertently renew the local
    # OpenID session while loading the components for this page (in parallel)
    # so we keep the local logout step explicit and using plain text mode to
    # avoid loading other resources.

    # TODO: switch to ajax logout buttons and just show results in an overlay

    if do_logout:
        #logger.info("checking active sessions for %s" % identity)
        #(found, before) = find_oid_sessions(configuration, identity)
        #logger.info("expiring active sessions for %s" % identity)
        (success, _) = expire_oid_sessions(configuration, identity)
        logger.info("verifying no active sessions for %s" % identity)
        (found, remaining) = find_oid_sessions(configuration, identity)
        if success and found and not remaining:
            output_objects.append(
                {'object_type': 'text', 'text': """You are now logged out of %s
locally - you may want to close your web browser to finish""" % \
                 configuration.short_title})
        else:
            logger.error("remaining active sessions for %s: %s" % (identity,
                         remaining))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : "Could not log you out of %s!" % \
                                   configuration.short_title})
            status = returnvalues.CLIENT_ERROR
    else:
        oid_logout = os.path.join(os.path.dirname(os.path.dirname(identity)),
                                  'logout')
        local_logout = '?logout=true;output_format=text'
        output_objects.append(
            {'object_type': 'text', 'text':
             """You're accessing %s with an OpenID login, so to completely
logout you need to first""" % configuration.short_title})
        # Remove /id/username from identity and append logout
        output_objects.append(        
            {'object_type': 'link', 'destination': oid_logout,
             'target': '_blank', 'text': "Logout from your OpenID provider"})
        output_objects.append({'object_type': 'text', 'text': " and then "})
        output_objects.append(
            {'object_type': 'link', 'destination': local_logout,
             'text': "Stop your %s session" % configuration.short_title})
    return (output_objects, status)
