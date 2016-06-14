#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# handlers - back.end handler helpers
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

import os
import urllib

from shared.base import client_id_dir
from shared.findtype import is_user, is_server
from shared.pwhash import make_csrf_token

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

def csrf_needed(configuration, environ=None):
    """Detect if client is a browser so that CSRF should be enabled or e.g. a 
    command line client like cURL or XMLRPC where it doesn't make sense.
    """

    if environ is None:
        environ = os.environ
    agent = environ.get('HTTP_USER_AGENT', 'UNKNOWN')
    if agent.startswith('curl'):
        return False
    # TODO: add XMLRPC detection here
    else:
        return True

def safe_handler(configuration, method, operation, client_id, limit,
                 accepted_dict, environ=None):
    """Verify that the method is correct for operation and that the csrf_token
    from accepted_dict fits operation from client_id with salt from
    configuration and limit from back-end handler.
    The limit argument can be used to e.g. limit the validity of a csrf token
    to a certain time-frame.
    """
    if not correct_handler(method, environ):
        return False
    # NOTE: CSRF checks are automatically disabled for e.g. cURL clients here
    elif not csrf_needed(configuration, environ):
        return True
    csrf_token = accepted_dict.get('_csrf', [''])[-1]
    csrf_required = make_csrf_token(configuration, method, operation,
                                    client_id, limit)
    configuration.logger.debug("CSRF check: %s vs %s" % (csrf_required,
                                                         csrf_token))
    if csrf_required != csrf_token:
        configuration.logger.warning("CSRF check failed: %s vs %s" % \
                                     (csrf_required, csrf_token))
        return False
    else:
        return True


def get_path():
    """Extract supplied path from environment:
    urllib.unquote(string): Replaces url encoded chars '%xx' by their
    single-character equivalents.
    """

    path_translated = os.getenv('PATH_TRANSLATED')
    if not path_translated:
        raise Exception('No path provided!')
    root = str(os.getenv('DOCUMENT_ROOT'))

    # Remove only leftmost root occurence of root

    path = urllib.unquote(path_translated.replace(root, '', 1))
    return path


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


