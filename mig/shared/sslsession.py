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

import binascii

# NOTE: We avoid import failure to support modules where SSL is optional
try:
    import _sslsession
except ImportError, ierr:
    _sslsession = None

def get_ssl_master_key(configuration, ssl_sock):
    """Extract SSL session master key from SSL socket"""
    logger = configuration.logger
    master_key = None
    if _ssl_session is None:
        logger.error("The MiG python _sslsession.so library is required!")
        return master_key
    try:
        ssl_obj = ssl_sock._sslobj
        master_key_bin = _sslsession.master_key(ssl_obj)
        master_key = binascii.hexlify(master_key_bin)
    except Exception, exc:
        master_key = None
        logger.error(exc)

    return master_key


def get_ssl_session_id(configuration, ssl_sock):
    """Extract SSL session id from SSL socket"""
    logger = configuration.logger
    session_id = None
    if _ssl_session is None:
        logger.error("The MiG python _sslsession.so library is required!")
        return session_id
    try:
        ssl_obj = ssl_sock._sslobj
        session_id_bin = _sslsession.session_id(ssl_obj)
        session_id = binascii.hexlify(session_id_bin)
    except Exception, exc:
        session_id = None
        logger.error(exc)

    return session_id
