#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# handlers - back end handler helpers
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

"""This module contains general functions used by the HTTP
handlers.
"""

from __future__ import absolute_import

import os

from mig.shared.base import client_id_dir
from mig.shared.defaults import csrf_field, CSRF_MINIMAL, CSRF_WARN, CSRF_MEDIUM, \
    CSRF_FULL
from mig.shared.findtype import is_user, is_server
from mig.shared.pwhash import make_csrf_token, make_csrf_trust_token


def correct_handler(name, environ=None):
    """Verify that the handler name matches handler method using the provided
    environ. Fall back to os.environ if environ is left to None.
    """

    if environ is None:
        environ = os.environ
    return environ.get('REQUEST_METHOD', 'UNSET').upper() == name.upper()


def get_csrf_limit(configuration, environ=None):
    """Create a suitable limit argument for make_csrf_token. We just use None
    for now to disable limit. CSRF token is already impossible to predict
    without access to server salt or previous client session.
    We could add a limit to get forward-secrecy and prevent replay attacks.
    """
    # TODO: add time limit for full forward-secrecy?
    limit = None
    return limit


def check_enable_csrf(configuration, accepted_dict, environ=None):
    """Detect if client is a browser so that CSRF should be enabled or e.g. a 
    command line client like cURL or XMLRPC where it is partially supported
    except for legacy script versions. We should eventually disable the
    legacy support exception.
    """
    _logger = configuration.logger
    if environ is None:
        environ = os.environ
    if configuration.site_csrf_protection == CSRF_FULL:
        _logger.debug("configuration enforces full CSRF protection")
        return True
    elif configuration.site_csrf_protection == CSRF_WARN:
        _logger.debug("configuration enforces minimal CSRF protection, but " +
                      "with full warnings")
        return True
    elif configuration.site_csrf_protection == CSRF_MINIMAL:
        _logger.debug("configuration enforces minimal CSRF protection")
        return False
    # Fall back to CSRF_MEDIUM - enforce CSRF checks except for legacy clients
    # We look for curl and xmlrpc/jsonrpc first in user agent to match e.g.
    # * curl/7.38.0
    # * xmlrpclib.py/1.0.1 (by www.pythonware.com)
    # * jsonrpclib/0.1 (Python X.Y.Z)
    agent = environ.get('HTTP_USER_AGENT', 'UNKNOWN')
    if agent.lower().startswith('curl') or agent.lower().startswith('xmlrpc') \
            or agent.lower().startswith('python-xmlrpc') or \
            agent.lower().startswith('jsonrpc'):
        # No csrf_field input results in the defaults AllowMe string
        csrf_token = accepted_dict.get(csrf_field, ['AllowMe'])[-1]
        if csrf_token and csrf_token != 'AllowMe':
            _logger.debug("enable CSRF check for modern script (%s)" % agent)
            return True
        else:
            _logger.debug("disable CSRF check for legacy script (%s)" % agent)
            return False
    else:
        _logger.debug("enable CSRF check for client: %s" % agent)
        return True


def safe_handler(configuration, method, operation, client_id, limit,
                 accepted_dict, environ=None):
    """Verify that the method is correct for operation and that the csrf_token
    from accepted_dict fits operation from client_id with salt from
    configuration and limit from back-end handler.
    The limit argument can be used to e.g. limit the validity of a csrf token
    to a certain time-frame.
    """
    _logger = configuration.logger
    if not correct_handler(method, environ):
        return False
    # NOTE: CSRF checks are automatically disabled for e.g. cURL clients here
    elif not check_enable_csrf(configuration, accepted_dict, environ):
        return True
    # TODO: integrate token in user scripts and in xmlrpc/jsonrpc
    #       Remember that user scripts cannot hardcode token as long as it
    #       includes client_id (e.g. breaks deb package). Maybe add a get_token
    #       backend and use everywhere? or include a single shared token for
    #       scripts which is set/found in Settings and must be set copied to
    #       miguser.conf / Xrpc requests?
    csrf_token = accepted_dict.get(csrf_field, [''])[-1]
    # TODO: include any openid session ID headers from environ here?
    # _logger.debug("CSRF token for %s of %s from %s with %s" %
    #              (method, operation, client_id, limit))
    csrf_required = make_csrf_token(configuration, method, operation,
                                    client_id, limit)
    _logger.debug("CSRF check: %s vs %s" % (csrf_required, csrf_token))
    if csrf_required != csrf_token:
        msg = "CSRF check failed: %s vs %s" % (csrf_required, csrf_token)
        # In the transitional warn-mode we log CSRF errors, but let them pass.
        if configuration.site_csrf_protection != CSRF_WARN:
            _logger.error(msg)
            return False
        else:
            _logger.warning(msg)
            return True
    else:
        _logger.debug("CSRF check succeeded: %s vs %s" % (csrf_required,
                                                          csrf_token))
        return True


def trust_handler(configuration, method, operation, unpacked_args, client_id,
                  limit, environ=None):
    """Stricter version of safe_handler to verify that trust token in
    csrf_field matches all usual static parts in addition to unpacked_args.
    Only used in the special cases where we need to submit a form with values
    completely known up front, so that backend can verify that the values in
    unpacked_args are passed without tampering.
    """
    _logger = configuration.logger
    if not correct_handler(method, environ):
        return False
    csrf_token = unpacked_args.get(csrf_field, [''])[-1]
    csrf_required = make_csrf_trust_token(configuration, method, operation,
                                          unpacked_args, client_id, limit,
                                          skip_fields=[csrf_field])
    _logger.debug("CSRF trust check: %s vs %s" % (csrf_required, csrf_token))
    if csrf_required != csrf_token:
        _logger.error("CSRF trust check failed: %s vs %s" % (csrf_required,
                                                             csrf_token))
        return False
    _logger.debug("CSRF trust check succeeded: %s vs %s" % (csrf_required,
                                                            csrf_token))
    return True


def get_allowed_path(configuration, client_id, path):
    """Check certificate data and path for either a valid user/server
    or a resource using a valid session id. If the check succeeds, the
    real path to the file is returned.
    """

    client_dir = client_id_dir(client_id)

    # Check cert and decide if it is a user, resource or server

    if not client_id:
        path_slash_stripped = path.lstrip('/')
        sessionid = path_slash_stripped[:path_slash_stripped.find('/')]

        # check that the sessionid is ok (does symlink exist?)

        if not os.path.islink(configuration.webserver_home + sessionid):
            raise Exception('Invalid session id!')

        target_dir = configuration.webserver_home\
            + path_slash_stripped[:path_slash_stripped.rfind('/')]
        target_file = path_slash_stripped[path_slash_stripped.rfind('/')
                                          + 1:]
    elif is_user(client_id, configuration.mig_server_home):
        real_path = \
            os.path.normpath(os.path.join(configuration.user_home,
                                          client_dir, path))
        target_dir = os.path.dirname(real_path)
        target_file = os.path.basename(real_path)
    elif is_server(client_id, configuration.server_home):
        real_path = \
            os.path.normpath(os.path.join(configuration.server_home,
                                          client_dir, path))
        target_dir = os.path.dirname(real_path)
        target_file = os.path.basename(real_path)
    else:
        raise Exception('Invalid credentials %s: no such user or server'
                        % client_id)

    target_path = target_dir + '/' + target_file
    return target_path
