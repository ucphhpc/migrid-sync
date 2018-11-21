#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# auth - shared helpers for authentication in init functionality backends
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

"""Athentication helper functions"""

import Cookie
import os
import time

# Only needed for 2FA so ignore import error and only fail on use
try:
    import pyotp
except ImportError:
    pyotp = None

from shared.base import client_id_dir, extract_field, force_utf8
from shared.defaults import twofactor_key_name, twofactor_key_bytes, \
    twofactor_cookie_ttl
from shared.fileio import read_file, delete_file, delete_symlink
from shared.pwhash import scramble_password, unscramble_password


def twofactor_available(configuration):
    """Get current twofactor taken for base32 key"""
    _logger = configuration.logger
    if pyotp is None:
        _logger.error("The pyotp module is missing and required for 2FA!")
        return False
    return True


def reset_twofactor_key(client_id, configuration):
    """Reset 2FA secret key and write to user settings file in scrambled form.
    Return the new secret key on unscrambled base32 form.
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    key_path = os.path.join(configuration.user_settings, client_dir,
                            twofactor_key_name)
    try:
        if pyotp is None:
            raise Exception("The pyotp module is missing and required for 2FA")
        b32_key = pyotp.random_base32(length=twofactor_key_bytes)
        # NOTE: pyotp.random_base32 returns unicode
        #       which causes trouble with WSGI
        b32_key = force_utf8(b32_key)
        scrambled = scramble_password(configuration.site_password_salt,
                                      b32_key)
        key_fd = open(key_path, 'w')
        key_fd.write(scrambled)
        key_fd.close()
    except Exception, exc:
        _logger.error("failed in reset 2FA key: %s" % exc)
        return False

    return b32_key


def load_twofactor_key(client_id, configuration, allow_missing=True):
    """Load 2FA secret key on scrambled form from user settings file and
    return the unscrambled form.
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    key_path = os.path.join(configuration.user_settings, client_dir,
                            twofactor_key_name)
    b32_key = None
    try:
        pw_fd = open(key_path)
        scrambled = pw_fd.read().strip()
        pw_fd.close()
        b32_key = unscramble_password(configuration.site_password_salt,
                                      scrambled)
    except Exception, exc:
        if not allow_missing:
            _logger.error("load 2FA key failed: %s" % exc)
    return b32_key


def get_twofactor_secrets(configuration, client_id):
    """Load twofactor base32 key and OTP uri for QR code. Generates secret for
    user if not already done. Actual twofactor login requirement is not
    enabled here, however.
    """
    _logger = configuration.logger
    if pyotp is None:
        raise Exception("The pyotp module is missing and required for 2FA")

    # NOTE: 2FA secret key is a standalone file in user settings dir
    #       Try to load existing and generate new one if not there.
    #       We need the base32-encoded form as returned here.
    b32_key = load_twofactor_key(client_id, configuration)
    if not b32_key:
        b32_key = reset_twofactor_key(client_id, configuration)

    # URI-format for otp auth is
    # otpauth://<otptype>/(<issuer>:)<accountnospaces>?
    #         secret=<secret>(&issuer=<issuer>)(&image=<imageuri>)
    # which we pull out of pyotp directly.
    # We could display with Google Charts helper like this example
    # https://www.google.com/chart?chs=200x200&chld=M|0&cht=qr&
    #       chl=otpauth://totp/Example:alice@google.com?
    #       secret=JBSWY3DPEHPK3PXP&issuer=Example
    # but we prefer to use the QRious JS library to keep it local.
    if configuration.user_openid_alias:
        username = extract_field(
            client_id, configuration.user_openid_alias)
    else:
        username = client_id
    otp_uri = pyotp.totp.TOTP(b32_key).provisioning_uri(
        username, issuer_name=configuration.short_title)
    # IMPORTANT: pyotp unicode breaks wsgi when inserted - force utf8!
    otp_uri = force_utf8(otp_uri)

    # Google img examle
    # img_url = 'https://www.google.com/chart?'
    # img_url += urllib.urlencode([('cht', 'qr'), ('chld', 'M|0'),
    #                             ('chs', '200x200'), ('chl', otp_uri)])
    # otp_img = '<img src="%s" />' % img_url

    return (b32_key, otp_uri)


def get_twofactor_token(configuration, client_id, b32_key):
    """Get current twofactor taken for base32 key"""
    _logger = configuration.logger
    if pyotp is None:
        raise Exception("The pyotp module is missing and required for 2FA")
    # IMPORTANT: pyotp unicode breaks when used in our strings - force utf8!
    token = pyotp.TOTP(b32_key).now()
    token = force_utf8(token)
    return token


def verify_twofactor_token(configuration, client_id, b32_key, token):
    """Verify that supplied token matches the current token for base32 key"""
    _logger = configuration.logger
    if pyotp is None:
        raise Exception("The pyotp module is missing and required for 2FA")
    return pyotp.TOTP(b32_key).verify(token)


def client_twofactor_session(configuration,
                             client_id,
                             environ):
    """Extract any active twofactor session ID from client cookie"""
    _logger = configuration.logger
    session_cookie = Cookie.SimpleCookie()
    session_cookie.load(environ.get('HTTP_COOKIE', None))
    session_cookie = session_cookie.get('2FA_Auth', None)
    if session_cookie is None:
        return None
    return session_cookie.value


def check_twofactor_session(configuration,
                            client_id,
                            environ):
    """Check active twofactor session for user with identity. Looks up any
    corresponding session cookies and extracts the session_id. In case a
    matching session_id state file exists it is read and verified to belong to
    the user and still not be expired.
    """
    _logger = configuration.logger
    session_id = client_twofactor_session(configuration, client_id, environ)
    if not session_id:
        _logger.warning("no 2FA session found for %s" % client_id)
        return False
    session_path = os.path.join(configuration.twofactor_home, session_id)
    session_data = read_file(session_path, _logger)
    session_expire = os.stat(session_path).st_ctime + twofactor_cookie_ttl
    now = time.time()
    if session_data is None:
        return False
    elif session_data.find(client_id) == -1:
        _logger.error("2FA session %s does not belong to %s - ignoring! (%s)" %
                      (session_id, client_id, session_data))
        return False
    elif session_expire < now:
        _logger.info("2FA session %s for %s expired (%s)" %
                     (session_id, client_id, session_expire))
        return False
    else:
        _logger.debug("2FA session %s for %s is valid (%s)" %
                      (session_id, client_id, session_expire))
        return True


def expire_twofactor_session(configuration,
                             client_id,
                             environ,
                             allow_missing=False):
    """Expire active twofactor session for user with identity. Looks up any
    corresponding session cookies and extracts the session_id. In case a
    matching session_id state file exists it is deleted after checking that it
    does indeed originate from the client_id.
    """
    _logger = configuration.logger
    session_id = client_twofactor_session(configuration, client_id, environ)
    if not session_id:
        _logger.warning("no valid 2FA session found for %s" % client_id)
        if allow_missing:
            return True
        return False
    session_path = os.path.join(configuration.twofactor_home, session_id)
    session_data = read_file(session_path, _logger)
    if session_data is None:
        if allow_missing:
            _logger.info("2FA session empty: %s" % session_path)
            return True
        _logger.error("no 2FA session to expire: %s" % session_path)
        expired = False
    elif session_data.find(client_id) == -1:
        _logger.error("2FA session %s does not belong to %s - ignoring! (%s)" %
                      (session_id, client_id, session_data))
        expired = False
    else:
        delete_status = True
        if delete_file(session_path, _logger, allow_missing=allow_missing):
            _logger.info("expired 2FA session %s for %s" %
                         (session_id, client_id))
            client_dir = client_id_dir(client_id)
            client_link_path = os.path.join(configuration.twofactor_home,
                                            client_dir)
            if not delete_symlink(client_link_path, _logger):
                _logger.warning(
                    "failed to delete 2FA session symlink %s for %s"
                    % (client_link_path, client_id))
            expired = True
        else:
            _logger.error("failed to delete 2FA session file %s for %s!" %
                          (session_path, client_id))
            expired = False

    return expired
