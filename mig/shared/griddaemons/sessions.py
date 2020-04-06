#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sessions - grid daemon session tracker helper functions
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

import os
import time
from shared.defaults import io_session_timeout
from shared.fileio import pickle, unpickle, acquire_file_lock, \
    release_file_lock

_sessions_filename = "sessions.pck"


def _acquire_sessions_lock(configuration, proto, exclusive=True):
    """Acquire sessions lock for protocol proto"""
    flock_filepath = \
        os.path.join(configuration.mig_system_run,
                     "%s.%s.lock"
                     % (proto, _sessions_filename))
    flock = acquire_file_lock(flock_filepath, exclusive=exclusive)

    return flock


def _release_sessions_lock(flock):
    """Release sessions file lock"""
    return release_file_lock(flock)


def _load_sessions(configuration, proto, do_lock=True):
    """Load sessions dict"""
    logger = configuration.logger
    sessions_filepath = os.path.join(configuration.mig_system_run,
                                     "%s.%s"
                                     % (proto, _sessions_filename))
    sessions_lock = None
    if do_lock:
        sessions_lock = _acquire_sessions_lock(
            configuration, proto, exclusive=False)
    # NOTE: file is typically on tmpfs so it may or may not exist at this point
    result = unpickle(sessions_filepath, logger, allow_missing=True)
    if do_lock:
        _release_sessions_lock(sessions_lock)

    if not isinstance(result, dict):
        logger.warning("failed to retrieve active %s sessions from %s" %
                       (proto, sessions_filepath))
        result = {}

    return result


def _save_sessions(configuration,
                   proto,
                   sessions,
                   do_lock=True):
    """Save sessions dict"""
    logger = configuration.logger
    do_lock = None
    sessions_filepath = os.path.join(configuration.mig_system_run,
                                     "%s.%s"
                                     % (proto, _sessions_filename))
    if do_lock:
        sessions_lock = _acquire_sessions_lock(
            configuration, proto, exclusive=True)
    result = pickle(sessions, sessions_filepath, logger)
    if do_lock:
        _release_sessions_lock(sessions_lock)

    if not result:
        logger.error("failed to save active %s sessions to %s" %
                     (proto, sessions_filepath))

    return result


def clear_sessions(configuration,
                   proto,
                   do_lock=True):
    """Clear sessions"""
    logger = configuration.logger

    return _save_sessions(configuration,
                          proto,
                          {},
                          do_lock=do_lock)


def track_open_session(configuration,
                       proto,
                       client_id,
                       client_address,
                       client_port,
                       session_id=None,
                       authorized=False,
                       do_lock=True):
    """Track that client_id opened a new session from
    client_address and client_port.
    If session_id is _NOT_ set then client_ip:client_port
    is used as session_id.
    Returns dictionary with new session"""

    logger = configuration.logger
    # msg = "track open session for %s" % client_id \
    #      + " from %s:%s with session_id: %s" % \
    #      (client_address, client_port, session_id)
    # logger.debug(msg)
    result = None
    if not session_id:
        session_id = "%s:%s" % (client_address, client_port)
    if do_lock:
        sessions_lock = _acquire_sessions_lock(
            configuration, proto, exclusive=True)
    _active_sessions = _load_sessions(configuration, proto, do_lock=False)
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
        if not _save_sessions(configuration,
                              proto, _active_sessions, do_lock=False):
            raise IOError("%s save sessions failed for %s" %
                          (proto, client_id))
    except Exception, exc:
        result = None
        logger.error("track open session failed: %s" % exc)

    if do_lock:
        _release_sessions_lock(sessions_lock)

    return result


def get_active_session(configuration,
                       proto,
                       client_id,
                       session_id,
                       do_lock=True):
    """Returns active session if it exists
    for proto, client_id and session_id"""
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, session_id: %s," \
    #              % (proto, client_id, session_id) \
    #              + " do_lock: %s" % do_lock)
    result = None
    _active_sessions = _load_sessions(configuration, proto, do_lock=do_lock)
    result = _active_sessions.get(client_id, {}).get(
        proto, {}).get(session_id, {})

    return result


def get_open_sessions(configuration,
                      proto,
                      client_id=None,
                      do_lock=True):
    """Returns dictionary {session_id: session}
    with open proto sessions for client_id"""
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, do_lock: %s"
    #              % (proto, client_id, do_lock))
    result = {}
    _active_sessions = _load_sessions(configuration, proto, do_lock=do_lock)
    # logger.debug("__active_sessions: %s" % __active_sessions)
    if client_id is not None:
        result = _active_sessions.get(client_id, {}).get(
            proto, {})
    else:
        for (_, open_sessions) in _active_sessions.iteritems():
            open_proto_session = open_sessions.get(proto, {})
            if open_proto_session:
                result.update(open_proto_session)

    return result


def track_close_session(configuration,
                        proto,
                        client_id,
                        client_address,
                        client_port,
                        session_id=None,
                        do_lock=True):
    """Track that proto session for client_id is closed,
    returns closed session dictionary"""
    logger = configuration.logger
    # msg = "track close session for proto: '%s'" % proto \
    #     + " from %s:%s with session_id: %s, client_id: %s, do_lock: %s" % \
    #     (client_address, client_port, session_id, client_id, do_lock)
    # logger.debug(msg)
    result = {}
    if not session_id:
        session_id = "%s:%s" % (client_address, client_port)

    if do_lock:
        sessions_lock = _acquire_sessions_lock(
            configuration, proto, exclusive=True)
    _active_sessions = _load_sessions(configuration, proto, do_lock=False)
    open_sessions = _active_sessions.get(client_id, {}).get(proto, {})
    if open_sessions and open_sessions.has_key(session_id):
        try:
            result = open_sessions[session_id]
            del open_sessions[session_id]
            if not _save_sessions(configuration,
                                  proto, _active_sessions, do_lock=False):
                raise IOError("%s save sessions failed for %s" %
                              (proto, client_id))
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
    if do_lock:
        _release_sessions_lock(sessions_lock)

    return result


def track_close_expired_sessions(
        configuration,
        proto,
        client_id=None,
        do_lock=True):
    """Track expired sessions and close them.
    Returns dictionary of closed sessions {session_id: session}"""
    logger = configuration.logger
    # msg = "track close sessions for proto: '%s'" % proto \
    #     + " with client_id: %s, do_lock: %s" % \
    #     (client_id, do_lock)
    # logger.debug(msg)
    result = {}
    session_timeout = io_session_timeout.get(proto, 0)
    if do_lock:
        sessions_lock = _acquire_sessions_lock(
            configuration, proto, exclusive=True)
    open_sessions = get_open_sessions(
        configuration, proto, client_id=client_id, do_lock=False)
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
                                    do_lock=False)
            if closed_session is not None:
                result[cur_session_id] = closed_session
    if do_lock:
        _release_sessions_lock(sessions_lock)

    return result


def active_sessions(configuration,
                    proto,
                    client_id,
                    do_lock=True):
    """Look up how many active proto sessions client_id has running"""
    logger = configuration.logger

    open_sessions = get_open_sessions(configuration,
                                      proto,
                                      client_id=client_id,
                                      do_lock=do_lock)

    result = len(open_sessions)

    return result
