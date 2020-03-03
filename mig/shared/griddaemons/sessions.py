#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# griddaemons.sessions - grid daemon session tracker helper functions
# Copyright (C) 2010-2020  The MiG Project lead by Brian Vinter
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

"""MiG daemon session tracker functions"""

import threading
import time
from shared.defaults import io_session_timeout

_active_sessions = {}
_sessions_lock = threading.Lock()


def track_open_session(configuration,
                       proto,
                       client_id,
                       client_address,
                       client_port,
                       session_id=None,
                       authorized=False,
                       prelocked=False,
                       blocking=True):
    """Track that client_id opened a new session from
    client_address and client_port.
    If session_id is _NOT_ set then client_ip:client_port
    is used as session_id.
    Returns dictionary with new session"""

    logger = configuration.logger
    # msg = "track open session for %s" % client_id \
    #     + " from %s:%s with session_id: %s" % \
    #     (client_address, client_port, session_id)
    # logger.debug(msg)
    result = None
    if not session_id:
        session_id = "%s:%s" % (client_address, client_port)
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    try:
        _cached = _active_sessions.get(client_id, {})
        if not _cached:
            _active_sessions[client_id] = _cached
        _proto = _cached.get(proto, {})
        if not _proto:
            _cached[proto] = _proto
        _session = _proto.get(session_id, {})
        if not _session:
            _proto[session_id] = _session
        _session['session_id'] = session_id
        _session['client_id'] = client_id
        _session['ip_addr'] = client_address
        _session['tcp_port'] = client_port
        _session['authorized'] = authorized
        _session['timestamp'] = time.time()
        result = _session
    except Exception, exc:
        result = None
        logger.error("track open session failed: %s" % exc)

    if not prelocked:
        _sessions_lock.release()

    return result


def get_active_session(configuration,
                       proto,
                       client_id,
                       session_id,
                       prelocked=False,
                       blocking=True):
    """Returns active session if it exists
    for proto, client_id and session_id"""
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, session_id: %s," \
    #              % (proto, client_id) \
    #              + " prelocked: %s, blocking: %s" \
    #              % (prelocked, blocking))
    result = None
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = _active_sessions.get(client_id, {}).get(
        proto, {}).get(session_id, {})

    if not prelocked:
        _sessions_lock.release()

    return result


def get_open_sessions(configuration,
                      proto,
                      client_id=None,
                      prelocked=False,
                      blocking=True):
    """Returns dictionary {session_id: session}
    with open proto sessions for client_id"""
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, prelocked: %s, blocking: %s"
    #              % (proto, client_id, prelocked, blocking))
    result = None
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    # logger.debug("_active_sessions: %s" % _active_sessions)
    if client_id is not None:
        result = _active_sessions.get(client_id, {}).get(
            proto, {})
    else:
        result = {}
        for (_, open_sessions) in _active_sessions.iteritems():
            open_proto_session = open_sessions.get(proto, {})
            if open_proto_session:
                result.update(open_proto_session)

    if not prelocked:
        _sessions_lock.release()

    return result


def track_close_session(configuration,
                        proto,
                        client_id,
                        client_address,
                        client_port,
                        session_id=None,
                        prelocked=False,
                        blocking=True):
    """Track that proto session for client_id is closed,
    returns closed session dictionary"""
    logger = configuration.logger
    # msg = "track close session for proto: '%s'" % proto \
    #     + " from %s:%s with session_id: %s, client_id: %s, prelocked: %s" % \
    #     (client_address, client_port, session_id, client_id, prelocked)
    # logger.debug(msg)
    result = None
    if not session_id:
        session_id = "%s:%s" % (client_address, client_port)
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = {}
    open_sessions = get_open_sessions(
        configuration, proto, client_id=client_id, prelocked=True)
    # logger.debug("_sessions : %s" % _sessions)
    if open_sessions and open_sessions.has_key(session_id):
        try:
            result = open_sessions[session_id]
            del open_sessions[session_id]
        except Exception, exc:
            result = None
            msg = "track close session failed for client: %s" % client_id \
                + "with session id: %s" % session_id \
                + ", error: %s" % exc
            logger.error(msg)
    else:
        msg = "track close session: '%s' _NOT_ found for proto: '%s'" \
            % (session_id, proto) \
            + ", client: '%s'" % client_id
        logger.warning(msg)

    if not prelocked:
        _sessions_lock.release()

    return result


def track_close_expired_sessions(
        configuration,
        proto,
        client_id=None,
        prelocked=False,
        blocking=True):
    """Track expired sessions and close them.
    Returns dictionary of closed sessions {session_id: session}"""
    logger = configuration.logger
    # msg = "track close sessions for proto: '%s'" % proto \
    #     + " with client_id: %s, prelocked: %s, blocking: %s" % \
    #     (client_id, prelocked, blocking)
    # logger.debug(msg)
    result = None
    session_timeout = io_session_timeout.get(proto, 0)
    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    result = {}
    open_sessions = get_open_sessions(
        configuration, proto, client_id=client_id, prelocked=True)
    # logger.debug("open_sessions: %s" % open_sessions)
    current_timestamp = time.time()
    # logger.debug("current_timestamp: %s" % (current_timestamp))
    for open_session_id in open_sessions.keys():
        timestamp = open_sessions[open_session_id]['timestamp']
        # logger.debug("current_timestamp - timestamp: %s / %s"
        #              % (current_timestamp - timestamp, session_timeout))
        if current_timestamp - timestamp > session_timeout:
            cur_session = open_sessions[open_session_id]
            cur_session_id = cur_session['session_id']
            closed_session = \
                track_close_session(configuration,
                                    proto,
                                    cur_session['client_id'],
                                    cur_session['ip_addr'],
                                    cur_session['tcp_port'],
                                    session_id=cur_session_id,
                                    prelocked=True)
            if closed_session is not None:
                result[cur_session_id] = closed_session
    if not prelocked:
        _sessions_lock.release()

    return result


def active_sessions(configuration,
                    proto,
                    client_id,
                    prelocked=False,
                    blocking=True):
    """Look up how many active proto sessions client_id has running"""
    logger = configuration.logger
    result = None

    if not prelocked and not _sessions_lock.acquire(blocking):
        return result
    try:
        _cached = _active_sessions.get(client_id, {})
        _active = _cached.get(proto, {})
        result = len(_active.keys())
    except Exception, exc:
        result = None
        logger.error("active sessions failed: %s" % exc)

    if not prelocked:
        _sessions_lock.release()

    return result
