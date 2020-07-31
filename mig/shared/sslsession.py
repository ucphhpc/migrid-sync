#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sslsession - Shared functions for SSL session information
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

"""Functions for extracting SSL session information"""
from __future__ import absolute_import

import binascii

# NOTE: We avoid import failure to support modules where SSL is optional
try:
    import _sslsession
except ImportError as ierr:
    _sslsession = None

from mig.shared.pwhash import make_digest

SSL_SESSION_ID_LENGTH = 64
SSL_MASTER_KEY_LENGTH = 96


def ssl_master_key(configuration, ssl_sock):
    """Extract SSL session master key from SSL socket"""
    logger = configuration.logger
    master_key = None
    if _sslsession is None:
        logger.error("The MiG python _sslsession.so library is required!")
        return master_key
    try:
        ssl_obj = ssl_sock._sslobj
        master_key_bin = _sslsession.master_key(ssl_obj)
        master_key = binascii.hexlify(master_key_bin)
        if len(master_key) != SSL_MASTER_KEY_LENGTH \
                or master_key.isdigit() and int(master_key) == 0:
            raise TypeError("Invalid SSL master_key: %s" % master_key)
    except Exception as exc:
        master_key = None
        logger.error(exc)

    return master_key


def ssl_session_id(configuration, ssl_sock):
    """Extract SSL session id from SSL socket"""
    logger = configuration.logger
    session_id = None
    if _sslsession is None:
        logger.error("The MiG python _sslsession.so library is required!")
        return session_id
    try:
        ssl_obj = ssl_sock._sslobj
        session_id_bin = _sslsession.session_id(ssl_obj)
        session_id = binascii.hexlify(session_id_bin)
        if len(session_id) != SSL_SESSION_ID_LENGTH:
            raise TypeError("Invalid session_id: %s" % session_id)
        elif session_id.isdigit() and int(session_id) == 0:
            # session_id might be empty according to rfc5246:
            # https://tools.ietf.org/html/rfc5246
            logger.warning("Found empty SSL session_id: %s" % session_id)
            session_id = None
    except Exception as exc:
        session_id = None
        logger.error(exc)

    return session_id


def ssl_session_token(configuration, ssl_sock, realm):
    """Generate SSL session identifier token"""
    session_token = None
    (client_addr, _) = ssl_sock.getpeername()
    master_key = ssl_master_key(configuration, ssl_sock)
    if master_key is not None:
        session_token = make_digest(realm,
                                    client_addr,
                                    master_key,
                                    configuration.site_digest_salt)

    return session_token
