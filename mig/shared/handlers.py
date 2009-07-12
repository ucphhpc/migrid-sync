#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# handlers - [insert a few words of module description on this line]
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

"""This module contains general functions used by the HTTP
handlers.
"""

import os
import urllib

from shared.findtype import is_user, is_server
from shared.useradm import client_id_dir


def correct_handler(name):
    """Verify that the handler name matches handler method"""

    return os.getenv('REQUEST_METHOD') == name


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
    elif is_user(client_id, configuration.user_home):
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
        raise Exception('Invalid credentials %s: no such MiG user or server'
                         % client_id)

    target_path = target_dir + '/' + target_file
    return target_path


