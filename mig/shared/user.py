#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# user - helper functions for user related tasks
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

"""User related functions - especially for People interface"""

from __future__ import print_function
from __future__ import absolute_import

import base64
import os

# TODO: move to os.scandir with py3
# NOTE: Use faster scandir if available
try:
    from distutils.version import StrictVersion
    from scandir import scandir, __version__ as scandir_version
    if StrictVersion(scandir_version) < StrictVersion("1.3"):
        # Important os.scandir compatibility utf8 fixes were not added until
        # 1.3
        raise ImportError(
            "scandir version is too old: fall back to os.listdir")
except ImportError:
    scandir = None

from mig.shared.base import client_dir_id, client_id_dir, get_site_base_url
from mig.shared.defaults import litmus_id
from mig.shared.fileio import read_file
from mig.shared.pwcrypto import make_simple_hash
from mig.shared.settings import load_settings, load_profile
from mig.shared.url import urlencode


def anon_user_id(user_id):
    """Generates an anonymous but (practically) unique user ID for user with
    provided unique user_id. The anonymous ID is just a md5 hash of the
    user_id to keep ID relatively short.
    """
    anon_id = make_simple_hash(user_id)
    return anon_id


def list_users(configuration):
    """Return a list of all users by listing the user homes in user_home.
    Uses scandir for efficiency when available.
    """
    users = []
    if scandir:
        children = scandir(configuration.user_home)
    else:
        children = os.listdir(configuration.user_home)
    for entry in children:
        # skip all files and dot dirs - they are NOT users
        if scandir:
            name = entry.name
            path = entry.path
            if entry.is_symlink() or not entry.is_dir():
                continue
        else:
            name = entry
            path = os.path.join(configuration.user_home, name)
            if os.path.islink(path) or not os.path.isdir(path):
                continue

        if name.startswith('.'):
            continue
        # We assume user IDs on the form /A=bla/B=bla/... here
        if not '=' in name:
            continue
        if name in [configuration.empty_job_name, litmus_id]:
            continue
        users.append(client_dir_id(name))
    return users


def anon_to_real_user_map(configuration):
    """Return a mapping from anonymous user names to real names"""
    _logger = configuration.logger
    anon_map = {}
    for name in list_users(configuration):
        _logger.debug("de-mask anon user: %s" % [name])
        anon_map[anon_user_id(name)] = name
    return anon_map


def real_to_anon_user_map(configuration):
    """Return a mapping from real user names to anonymous names"""
    user_map = {}
    for name in list_users(configuration):
        user_map[name] = anon_user_id(name)
    return user_map


def get_user_conf(user_id, configuration, include_meta=False):
    """Return user profile and settings"""
    conf = {}
    profile = load_profile(user_id, configuration, include_meta)
    if profile:
        conf.update(profile)
    settings = load_settings(user_id, configuration, include_meta)
    if settings:
        conf.update(settings)
    return conf


def user_gravatar_url(configuration, email, size, anon_img="/images/anonymous.png"):
    """Helper to provide URL to user porfile picture"""
    configuration.logger.info("build gravatar for %s" % email)
    prefer_url_base = get_site_base_url(configuration)
    anon_png_url = '%s/%s' % (prefer_url_base, anon_img)
    gravatar_query = {'s': size, 'd': anon_png_url}
    gravatar_url = 'https://www.gravatar.com/avatar/'
    gravatar_url += make_simple_hash(email.strip().lower())
    gravatar_url += '?%s' % urlencode(gravatar_query)
    return gravatar_url


def inline_image(configuration, path):
    """Create inline image base64 string from file in path"""
    _logger = configuration.logger
    mime_type = os.path.splitext(path)[1].strip('.')
    data = 'data:image/%s;base64,' % mime_type
    img_data = read_file(path, _logger, 'rb')
    if img_data is None:
        _logger.error("no such image %r to display inline" % path)
        img_data = ''
    data += base64.b64encode(img_data)
    return data


if __name__ == "__main__":
    print("= Unit Testing =")
    from mig.shared.conf import get_configuration_object
    conf = get_configuration_object()
    print("== List Users =")
    all_users = list_users(conf)
    print("All users:\n%s" % '\n'.join(all_users))
    real_map = real_to_anon_user_map(conf)
    print("Real to anon user map:\n%s" % '\n'.join(["%s -> %s" % pair for pair
                                                    in real_map.items()]))
