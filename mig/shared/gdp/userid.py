#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# userid - gdp userid helper functions related to GDP actions
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""GDP userid specific helper functions"""

import base64
import hashlib
from shared.base import expand_openid_alias, get_short_id
from shared.defaults import gdp_distinguished_field

client_id_project_postfix = '/%s=' % gdp_distinguished_field


def __validate_user_id(configuration, user_id):
    """Return valid user id, decode possible user alias"""

    _logger = configuration.logger
    # _logger.debug('user_id: %s' % user_id)

    result = None
    if user_id.find("@") == -1 and user_id.find('/') == -1:
        try:
            result = base64.b64decode(user_id.replace('_', '='))
        except Exception, exc:
            result = None
    else:
        result = user_id

    if result is None \
            or result.find("@") == -1 and result.find('/') == -1:
        _logger.error("Invalid user_id: %s" % result)
        result = None

    return result


def __client_id_from_project_client_id(configuration,
                                       project_client_id):
    """Extract client_id from *project_client_id"""

    _logger = configuration.logger
    # _logger.debug('project_client_id: %s' % project_client_id)

    result = None
    try:
        if project_client_id.find(client_id_project_postfix) > -1:
            result = \
                project_client_id.split(client_id_project_postfix)[0]
        # else:
        #     _logger.debug(
        #         "%r is NOT a GDP project client id" % project_client_id)
    except Exception, exc:
        _logger.error(
            "GDP:__client_id_from_project_client_id failed:"
            + "%r, error: %s" % (project_client_id, exc))

    return result


def __project_name_from_project_client_id(configuration,
                                          project_client_id):
    """Extract project name from *project_client_id*"""

    _logger = configuration.logger
    # _logger.debug('project_client_id: %s' % project_client_id)

    result = None
    try:
        if project_client_id \
                and project_client_id.find(client_id_project_postfix) > -1:
            result = \
                project_client_id.split(
                    client_id_project_postfix)[1].split('/')[0]
        else:
            _logger.warning("%r is NOT a GDP project client id"
                            % project_client_id)
    except Exception, exc:
        _logger.error("GDP:__project_name_from_project_client_id failed:"
                      + "%r, error: %s" % (project_client_id, exc))

    return result


def __short_id_from_client_id(configuration, client_id):
    """Extract login handle (email address) from *client_id*"""

    _logger = configuration.logger
    # _logger.debug('client_id: %s' % client_id)

    user_alias = configuration.user_openid_alias
    result = get_short_id(configuration, client_id, user_alias)

    return result


def __project_short_id_from_project_client_id(configuration,
                                              project_client_id):
    """Extract project short id (email@projectname)
    from *project_client_id*"""

    _logger = configuration.logger
    # _logger.debug('project_client_id: %s' % project_client_id)

    user_alias = configuration.user_openid_alias
    result = get_short_id(configuration, project_client_id, user_alias)

    return result


def __client_id_project_short_id(configuration, project_short_id):
    """Extract client_id from *project_short_id*"""

    _logger = configuration.logger
    # _logger.debug('project_short_id: %s' % project_short_id)

    result = None
    user_id_array = project_short_id.split('@')
    user_id = "@".join(user_id_array[:-1])
    client_id = expand_openid_alias(user_id, configuration)
    home_path = os.path.join(configuration.user_home, client_id)
    if os.path.exists(home_path):
        result = client_id
    else:
        _logger.error("GDP:__client_id_from_project_short_id failed:"
                      + " no home path user: %r" % project_short_id)

    return result


def __client_id_from_user_id(configuration, user_id):
    """Extract client_id from *user_id*
    *user_id* is either a client_id, project_client_id, short_id
    or project_user_id"""

    _logger = configuration.logger
    # _logger.debug('user_id: %s' % user_id)

    result = None

    # Extract client_id from user_id

    client_id = expand_openid_alias(user_id, configuration)
    possible_client_id = __client_id_from_project_client_id(
        configuration, client_id)

    if possible_client_id is None:
        result = client_id
    else:
        result = possible_client_id

    return result


def __project_client_id_from_user_id(configuration, user_id):
    """Extract project_client_id from *user_id*
    *user_id* is either a project_client_id or project_short_id"""

    _logger = configuration.logger
    # _logger.debug('user_id: %s' % user_id)

    result = None

    # Extract client_id from user_id

    client_id = expand_openid_alias(user_id, configuration)
    if client_id and client_id.find(client_id_project_postfix) > -1:
        result = client_id

    return result


def __project_name_from_user_id(configuration, user_id):
    """Extract project name *user_id*
    *user_id* is either a project_client_id or project_short_id"""

    result = None

    project_client_id = __project_client_id_from_user_id(
        configuration, user_id)
    if project_client_id is not None:
        result = __project_name_from_project_client_id(configuration,
                                                       project_client_id)

    return result


def __project_short_id_from_user_id(configuration, user_id):
    """Extract project_short_id from *user_id*
    *user_id* is either a project_client_id or project_short_id"""

    _logger = configuration.logger
    # _logger.debug("user_id: %s" % user_id)

    result = __project_short_id_from_project_client_id(
        configuration,
        user_id)
    if result is None:
        result = user_id

    return result


def __scamble_user_id(configuration, user_id):
    """Scamble user_id"""
    _logger = configuration.logger

    result = None
    try:
        result = hashlib.sha256(user_id).hexdigest()
    except Exception, exc:
        _logger.error("GDP: __scamble_user_id failed for user: %r: %s"
                      % (user_id, exc))
        result = None

    return result



def get_project_client_id(client_id, project_name):
    """Generate project client id from *client_id* and *project_name*"""

    return '%s%s%s' % (client_id, client_id_project_postfix,
                       project_name)


def get_base_client_id(configuration, user_id, expand_oid_alias=True):
    """Returns real user client_id from *user_id* which might
    Set *expand_oid_alias* to False for performance
    if user_id is a project_client_id or client_id"""

    if expand_oid_alias:
        possible_project_client_id = expand_openid_alias(
            user_id, configuration)
    else:
        possible_project_client_id = user_id

    possible_client_id = __client_id_from_project_client_id(
        configuration, possible_project_client_id)
    if possible_client_id is not None:
        client_id = possible_client_id
    else:
        client_id = possible_project_client_id

    return client_id


def get_client_id_from_project_client_id(configuration, project_client_id):
    """Returns base client_id from *project_client_id*"""

    return __client_id_from_project_client_id(configuration, project_client_id)


def get_project_from_client_id(configuration, project_client_id):
    """Returns project name from *project_client_id*"""

    return __project_name_from_project_client_id(configuration,
                                                 project_client_id)


def get_project_from_short_id(configuration, project_short_id):
    """Returns project name from *project_short_id*"""

    _logger = configuration.logger
    # _logger.debug("project_short_id: %s" % project_short_id)
    result = None
    try:
        result = project_short_id.split('@')[2]
    except Exception:
        _logger.error(
            "GDP: get_project_from_short_id failed:"
            + "%r is NOT a project short id" % project_short_id)

    return result


def get_project_from_user_id(configuration, user_id):
    """Returns project name from *user_id*"""

    project_name = None
    user_id = __validate_user_id(configuration, user_id)
    if user_id is not None:
        project_name = __project_name_from_user_id(configuration, user_id)

    return project_name


def get_short_id_from_user_id(configuration, user_id):
    """Extract project short id (email) from *user_id*.
    *user_id* is either a client_id, project_client_id, short_id
    or project_user_id"""

    result = None
    user_id = __validate_user_id(configuration, user_id)
    if user_id is not None:
        client_id = __client_id_from_user_id(configuration, user_id)
        result = __short_id_from_client_id(configuration, client_id)

    return result
