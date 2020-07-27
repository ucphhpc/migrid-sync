#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# auth - shared helpers for authentication in init functionality backends
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

"""Authentication helper functions"""
from __future__ import absolute_import

import Cookie
import base64
import glob
import hashlib
import os
import re
import time
import urllib

# Only needed for 2FA so ignore import error and only fail on use
try:
    import pyotp
except ImportError:
    pyotp = None

from .shared.base import client_id_dir, extract_field, force_utf8
from .shared.defaults import twofactor_key_name, twofactor_interval_name, \
    twofactor_key_bytes, twofactor_cookie_bytes, twofactor_cookie_ttl
from .shared.fileio import read_file, delete_file, delete_symlink, \
    pickle, unpickle, make_symlink
from .shared.gdp.all import get_base_client_id
from .shared.pwhash import scramble_password, unscramble_password

valid_otp_window = 1


def get_totp(client_id,
             b32_key,
             configuration,
             force_default_interval=False):
    """Initialize and return pyotp object"""
    if pyotp is None:
        raise Exception("The pyotp module is missing and required for 2FA")
    interval = None
    if not force_default_interval:
        interval = load_twofactor_interval(client_id, configuration)
    if interval:
        result = pyotp.totp.TOTP(b32_key, interval=interval)
    else:
        result = pyotp.totp.TOTP(b32_key)
    result.custom_interval = interval

    return result


def twofactor_available(configuration):
    """Get current twofactor taken for base32 key"""
    _logger = configuration.logger
    if pyotp is None:
        _logger.error("The pyotp module is missing and required for 2FA!")
        return False
    return True


def load_twofactor_interval(client_id, configuration):
    """Load 2FA token interval"""
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    client_dir = client_id_dir(client_id)
    interval_path = os.path.join(configuration.user_settings, client_dir,
                                 twofactor_interval_name)
    result = None
    if os.path.isfile(interval_path):
        i_fd = open(interval_path)
        interval = i_fd.read().strip()
        i_fd.close()
        try:
            result = int(interval)
        except Exception as exc:
            result = None
            _logger.error("Failed to read twofactor interval: %s" % exc)

    return result


def reset_twofactor_key(client_id, configuration, seed=None, interval=None):
    """Reset 2FA secret key and write to user settings file in scrambled form.
    Return the new secret key on unscrambled base32 form.
    """
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    client_dir = client_id_dir(client_id)
    key_path = os.path.join(configuration.user_settings, client_dir,
                            twofactor_key_name)
    try:
        if pyotp is None:
            raise Exception("The pyotp module is missing and required for 2FA")
        if not seed:
            b32_key = pyotp.random_base32(length=twofactor_key_bytes)
        else:
            b32_key = seed
        # NOTE: pyotp.random_base32 returns unicode
        #       which causes trouble with WSGI
        b32_key = force_utf8(b32_key)
        scrambled = scramble_password(configuration.site_password_salt,
                                      b32_key)
        key_fd = open(key_path, 'w')
        key_fd.write(scrambled)
        key_fd.close()

        # Reset interval

        interval_path = os.path.join(configuration.user_settings,
                                     client_dir,
                                     twofactor_interval_name)
        delete_file(interval_path, _logger, allow_missing=True)
        if interval:
            i_fd = open(interval_path, 'w')
            i_fd.write("%d" % interval)
            i_fd.close()
    except Exception as exc:
        _logger.error("failed in reset 2FA key: %s" % exc)
        return False

    return b32_key


def load_twofactor_key(client_id, configuration, allow_missing=True):
    """Load 2FA secret key on scrambled form from user settings file and
    return the unscrambled form.
    """
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
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
    except Exception as exc:
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
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    # NOTE: 2FA secret key is a standalone file in user settings dir
    #       Try to load existing and generate new one if not there.
    #       We need the base32-encoded form as returned here.
    b32_key = load_twofactor_key(client_id, configuration)
    if not b32_key:
        b32_key = reset_twofactor_key(client_id, configuration)

    totp = get_totp(client_id,
                    b32_key,
                    configuration)

    # URI-format for otp auth is
    # otpauth://<otptype>/(<issuer>:)<accountnospaces>?
    #         secret=<secret>(&issuer=<issuer>)(&image=<imageuri>)
    # which we pull out of pyotp directly.
    # IMPORTANT: we use the QRious JS library to keep rendering local.
    if configuration.user_openid_alias:
        username = extract_field(
            client_id, configuration.user_openid_alias)
    else:
        username = client_id
    otp_uri = totp.provisioning_uri(
        username, issuer_name=configuration.short_title)
    # Some auth apps like FreeOTP support addition of logo with &image=PNG_URL
    # Testing is easy with https://freeotp.github.io/qrcode.html
    if configuration.site_logo_left.endswith('.png'):
        logo_url = configuration.site_logo_left
        # NOTE: image URL must a full URL and logo_url is abs or anchored path
        if not logo_url.startswith('http'):
            # Remove any leading slashes which would break join
            logo_url = os.path.join(configuration.migserver_https_sid_url,
                                    logo_url.lstrip('/'))
        # Clear 'safe' argument to also encode slashes in url
        otp_uri += '&image=%s' % urllib.quote(logo_url, '')

    # IMPORTANT: pyotp unicode breaks wsgi when inserted - force utf8!
    otp_uri = force_utf8(otp_uri)

    return (b32_key, totp.interval, otp_uri)


def generate_session_prefix(configuration, client_id):
    """Generate a session prefix with a hash of client_id"""
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    return hashlib.sha256(client_id).hexdigest()


def generate_session_key(configuration, client_id):
    """Generate a random session key with a hash of user id as prefix so that
    it is easy to locate all sessions belonging to a particular user.
    """
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    session_key = generate_session_prefix(configuration, client_id)
    random_key = os.urandom(twofactor_cookie_bytes)
    session_key += re.sub(r'[=+/]+', '', base64.b64encode(random_key))
    return session_key


def get_twofactor_token(configuration, client_id, b32_key):
    """Get current twofactor taken for base32 key"""
    _logger = configuration.logger
    if pyotp is None:
        raise Exception("The pyotp module is missing and required for 2FA")
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    # IMPORTANT: pyotp unicode breaks when used in our strings - force utf8!
    totp = get_totp(client_id,
                    b32_key,
                    configuration)
    token = totp.now()
    token = force_utf8(token)
    return token


def verify_twofactor_token(configuration, client_id, b32_key, token):
    """Verify that supplied token matches the current token for base32 key"""
    _logger = configuration.logger
    if pyotp is None:
        raise Exception("The pyotp module is missing and required for 2FA")
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    totp = get_totp(client_id,
                    b32_key,
                    configuration)
    valid_token = totp.verify(token, valid_window=valid_otp_window)
    if not valid_token \
            and hasattr(totp, 'custom_interval') \
            and totp.custom_interval:
        # Fall back to default interval,
        # some App's like Android Google Authenticator
        # does not support non-default intervals
        totp = get_totp(client_id,
                        b32_key,
                        configuration,
                        force_default_interval=True)
        valid_token = totp.verify(token, valid_window=valid_otp_window)

    return valid_token


def client_twofactor_session(configuration,
                             client_id,
                             environ):
    """Extract any active twofactor session ID from client cookie"""
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    session_cookie = Cookie.SimpleCookie()
    session_cookie.load(environ.get('HTTP_COOKIE', None))
    session_cookie = session_cookie.get('2FA_Auth', None)
    if session_cookie is None:
        return None
    return session_cookie.value


def load_twofactor_session(configuration, session_key):
    """Load given twofactor session"""
    _logger = configuration.logger
    session_path = os.path.join(configuration.twofactor_home, session_key)
    # Use session file timestamp as default session start
    try:
        session_expire = os.stat(session_path).st_ctime + twofactor_cookie_ttl
    except Exception as exc:
        _logger.warning("Could not stat session_path %s: %s" % (session_path,
                                                                exc))
        return {}
    # NOTE: try to load pickle but with fallback to legacy plain file
    session_data = unpickle(session_path, _logger)
    if session_data:
        # new pickle format contains explicit session_end
        session_expire = session_data.get('session_end', session_expire)
    else:
        legacy_session = read_file(session_path, _logger)
        session_lines = legacy_session.split('\n')
        session_data = {'user_agent': 'UNKNOWN', 'user_addr': 'UNKNOWN',
                        'client_id': 'UNKNOWN', 'session_end': session_expire,
                        'session_start': session_expire - twofactor_cookie_ttl}
        for (key, val) in zip(['user_agent', 'user_addr', 'client_id'],
                              session_lines):
            session_data[key] = val.strip()
    return session_data


def save_twofactor_session(configuration, client_id, session_key, user_addr,
                           user_agent, session_start, session_end=-1):
    """Save twofactor session dict for client_id"""
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    session_path = os.path.join(configuration.twofactor_home, session_key)
    if session_end < 0:
        session_end = session_start + twofactor_cookie_ttl
    session_data = {'client_id': client_id, 'session_key': session_key,
                    'user_addr': user_addr, 'user_agent': user_agent,
                    'session_start': session_start, 'session_end': session_end}
    status = pickle(session_data, session_path, configuration.logger)
    if status and configuration.site_twofactor_strict_address:
        session_path_link = os.path.join(configuration.twofactor_home,
                                         "%s_%s" % (user_addr, session_key))
        status = \
            make_symlink(session_key, session_path_link, _logger, force=False)
        if not status:
            delete_file(session_path, _logger)
    return status


def list_twofactor_sessions(configuration, client_id, user_addr=None):
    """List all twofactor sessions for client_id. Optionally filter with client
    source.
    """
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    sessions = {}
    client_prefix = generate_session_prefix(configuration, client_id)
    pattern = os.path.join(configuration.twofactor_home, client_prefix+'*')
    for session_path in glob.glob(pattern):
        session_key = os.path.basename(session_path)
        session_data = load_twofactor_session(configuration, session_key)
        if session_data.get('client_id', None) != client_id:
            _logger.debug("skip session %s without user match for %s" %
                          (session_data, client_id))
            continue
        elif user_addr and session_data.get('user_addr', None) != user_addr:
            _logger.debug("skip session %s without address match for %s (%s)" %
                          (session_data, client_id, user_addr))
            continue
        sessions[session_key] = session_data
    _logger.debug("found sessions for %s: %s" % (client_id, sessions.keys()))
    return sessions


def active_twofactor_session(configuration, client_id, user_addr=None):
    """Load (latest) active twofactor session dict for client_id if any.
    Optionally filter to only target sessions originating from user_addr.
    """
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    # _logger.debug("client_id: '%s', %s" % (client_id, user_addr))
    sessions = list_twofactor_sessions(configuration, client_id, user_addr)
    latest = None
    now = time.time()
    for session_data in sessions.values():
        # Already checked client_id and optional user_addr match in list
        if session_data.get('session_end', -1) < now:
            _logger.debug("skip expired session %s (%s)" %
                          (session_data, now))
            continue
        elif latest is None or latest.get('session_end', -1) < \
                session_data.get('session_end', -1):
            latest = session_data
    _logger.debug("latest session for %s is %s" % (client_id, latest))
    return latest


def check_twofactor_active(configuration,
                           client_id,
                           user_addr,
                           environ):
    """Check active twofactor session for user with identity. Looks up any
    corresponding session cookies and extracts the session_id. In case a
    matching session_id state file exists it is read and verified to belong to
    the user and still not be expired.
    The user_addr argument is used to make sure an active twofactor session
    exists from that particular address. It can be set to None to disable the
    address check and allow users to change network as long as they have an
    active 2FA session.
    """
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    session_id = client_twofactor_session(configuration, client_id, environ)
    if not session_id:
        _logger.warning("no 2FA session found for %s" % client_id)
        return False
    session_data = active_twofactor_session(configuration, client_id,
                                            user_addr)
    if session_data is None:
        _logger.debug("No active 2FA session for %s (%s)" % (client_id,
                                                             user_addr))
        return False
    else:
        _logger.debug("2FA session for %s (%s) is valid: %s" % (client_id,
                                                                user_addr,
                                                                session_data))
        return True


def expire_twofactor_session(configuration,
                             client_id,
                             environ,
                             allow_missing=False,
                             user_addr=None,
                             not_user_addr=None):
    """Expire active twofactor session for user with client_id. Looks up any
    corresponding session cookie and extracts the session_id. In case a
    matching session_id state file exists it is deleted after checking that it
    does indeed originate from the client_id.
    The optional user_addr argument is used to only expire the active session
    from a particular source address for client_id. Left to None in gdp mode to
    expire all sessions and make sure only one session is ever active at a time.
    The optional not_user_addr argument is used to expire all sessions NOT
    from a particular source address for client_id.
    """
    _logger = configuration.logger
    if configuration.site_enable_gdp:
        client_id = get_base_client_id(
            configuration, client_id, expand_oid_alias=False)
    session_id = client_twofactor_session(configuration, client_id, environ)
    if not session_id:
        _logger.warning("no valid 2FA session found for %s" % client_id)
        if allow_missing:
            return True
        return False
    # Expire all client_id session files matching user_addr
    sessions = list_twofactor_sessions(configuration, client_id, user_addr)
    if not sessions:
        if allow_missing:
            _logger.info("No active 2FA session for %s (%s)"
                         % (client_id, user_addr))
            return True
        else:
            _logger.error("no 2FA session to expire for %s (%s)"
                          % (client_id, user_addr))
            return False

    expired = True
    for (session_key, session_data) in sessions.items():
        if not_user_addr and session_data.get('user_addr', '') \
                == not_user_addr:
            continue
        session_path = os.path.join(configuration.twofactor_home, session_key)
        # Already checked client_id and optionally user_addr match
        delete_status = True
        if configuration.site_twofactor_strict_address:
            session_user_addr = session_data.get('user_addr', None)
            if session_user_addr is None:
                delete_status = False
            else:
                session_link_path = \
                    os.path.join(configuration.twofactor_home, "%s_%s"
                                 % (session_user_addr, session_key))
                delete_status = delete_symlink(
                    session_link_path, _logger, allow_missing=allow_missing)
        if delete_status:
            delete_status = delete_file(
                session_path, _logger, allow_missing=allow_missing)
        if delete_status:
            _logger.info("expired 2FA session %s for %s in %s" %
                         (session_data, client_id, session_path))
        else:
            _logger.error("failed to delete 2FA session file %s for %s in %s" %
                          (session_path, client_id, session_path))
            expired = False

    return expired
