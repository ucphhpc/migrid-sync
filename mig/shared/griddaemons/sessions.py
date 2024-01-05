#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sessions - grid daemon session tracker helper functions
# Copyright (C) 2010-2024  The MiG Project lead by Brian Vinter
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

# NOTE: we rely on psutil for post-mortem expiring stale sessions not closed
try:
    import psutil
except ImportError:
    psutil = None

from mig.shared.base import brief_list
from mig.shared.defaults import io_session_timeout, io_session_stale
from mig.shared.fileio import pickle, unpickle, acquire_file_lock, \
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
    sessions_filepath = os.path.join(configuration.mig_system_run, "%s.%s" %
                                     (proto, _sessions_filename))
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


def clear_sessions(configuration, proto, do_lock=True):
    """Clear sessions"""
    logger = configuration.logger
    return _save_sessions(configuration, proto, {}, do_lock=do_lock)


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
    If session_id is NOT set then client_ip:client_port
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
    except Exception as exc:
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
    """Returns active session if it exists for proto, client_id and
    session_id.
    """
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, session_id: %s," \
    #              % (proto, client_id, session_id) \
    #              + " do_lock: %s" % do_lock)
    result = None
    _active_sessions = _load_sessions(configuration, proto, do_lock=do_lock)
    result = _active_sessions.get(client_id, {}).get(proto,
                                                     {}).get(session_id, {})

    return result


def get_open_sessions(configuration, proto, client_id=None, do_lock=True):
    """Returns dictionary {session_id: session} with open proto sessions for
    client_id.
    """
    logger = configuration.logger
    # logger.debug("proto: '%s', client_id: %s, do_lock: %s"
    #              % (proto, client_id, do_lock))
    result = {}
    _active_sessions = _load_sessions(configuration, proto, do_lock=do_lock)
    # logger.debug("__active_sessions: %s" % __active_sessions)
    if client_id is not None:
        result = _active_sessions.get(client_id, {}).get(proto, {})
    else:
        for (_, open_sessions) in _active_sessions.items():
            open_proto_session = open_sessions.get(proto, {})
            if open_proto_session:
                result.update(open_proto_session)

    return result


def track_close_session_list(configuration, proto, session_list, do_lock=True):
    """Track that proto sessions in session_list are closed. Returns list of
    closed session dictionaries.
    """
    logger = configuration.logger
    result = []
    logger.debug("track close session list %s for proto %s" %
                 (brief_list([i['session_id'] for i in session_list]), proto))
    if not session_list:
        return result

    # Lock for critical section with load, update and save sessions
    if do_lock:
        sessions_lock = _acquire_sessions_lock(configuration, proto,
                                               exclusive=True)

    _active_sessions = _load_sessions(configuration, proto, do_lock=False)
    for cur_session in session_list:
        session_id = cur_session['session_id']
        client_id = cur_session['client_id']
        timestamp = cur_session['timestamp']
        session_info = "proto %s, session_id %s, client_id %s, timestamp %d" % \
                       (proto, session_id, client_id, timestamp)
        client_proto_sessions = _active_sessions.get(
            client_id, {}).get(proto, {})
        if client_proto_sessions and session_id in client_proto_sessions:
            try:
                tracked = client_proto_sessions[session_id]
                if timestamp is None or timestamp == tracked['timestamp']:
                    del client_proto_sessions[session_id]
                    result.append(tracked)
                elif timestamp is not None:
                    msg = "track close session skip %s - wrong time %d"
                    logger.debug(msg % (session_info, tracked['timestamp']))
            except Exception as exc:
                result.append(None)
                msg = "track close session failed for %s: %s"
                logger.error(msg % (session_info, exc))
        else:
            msg = "track close session NOT found: %s"
            logger.warning(msg % session_info)
    logger.debug("track close session list for proto %s saves %d entries" %
                 (proto, len(client_proto_sessions)))

    if not _save_sessions(configuration, proto, _active_sessions,
                          do_lock=False):
        raise IOError("%s save sessions failed for %s" % (proto, session_list))

    if do_lock:
        _release_sessions_lock(sessions_lock)

    logger.debug("track close session list for proto %s returns %s" %
                 (proto, brief_list([i['session_id'] for i in result])))
    return result


def track_close_session(configuration,
                        proto,
                        client_id,
                        client_address,
                        client_port,
                        session_id=None,
                        timestamp=None,
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
    if open_sessions and session_id in open_sessions:
        try:
            result = open_sessions[session_id]
            if timestamp is None or timestamp == result['timestamp']:
                del open_sessions[session_id]
                if not _save_sessions(configuration,
                                      proto, _active_sessions, do_lock=False):
                    raise IOError("%s save sessions failed for %s" %
                                  (proto, client_id))
            elif timestamp is not None:
                logger.debug("track close session skipping"
                             + " proto: %s, session_id: %s, client_id: %s"
                             % (proto,
                                session_id,
                                client_id)
                             + ", requested timestamp: %d"
                             % timestamp
                             + ", differs from actual timestamp: %d"
                             % result['timestamp'])
        except Exception as exc:
            result = None
            msg = "track close session failed for client: %s" % client_id \
                + "with session id: %s" % session_id \
                + ", error: %s" % exc
            logger.error(msg)
    else:
        msg = "track close session: %r NOT found for proto: '%s'" \
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
    for open_session_id in open_sessions:
        timestamp = open_sessions[open_session_id]['timestamp']
        # logger.debug("current_timestamp - timestamp: %s / %s"
        #              % (current_timestamp - timestamp, session_timeout))
        if current_timestamp - timestamp > session_timeout:
            cur_session = open_sessions[open_session_id]
            cur_session_id = cur_session['session_id']
            closed_session = track_close_session(configuration, proto,
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


def lookup_live_sessions(configuration, session_id_format="%s:%s"):
    """Ask system about active network connections using psutil and extract
    a list of active ones with each item on the session_id_format.
    """
    if psutil is None:
        return None
    sessions = []
    active_connections = psutil.net_connections()
    # We consider all entries active unless they are listening or have state NONE
    # The full list of known states is available at
    # https://psutil.readthedocs.io/en/latest/#connections-constants
    inactive_states = [psutil.CONN_LISTEN, psutil.CONN_NONE]
    for connection in active_connections:
        if connection.status not in inactive_states:
            session_id = session_id_format % connection.raddr
            sessions.append(session_id)
    return sessions


def expire_dead_sessions(
        configuration,
        proto,
        client_id=None,
        do_lock=True):
    """Lookup live sessions and compare with registered open sessions to expire
    dead sessions.
    Returns dictionary of closed sessions {session_id: session}
    """
    logger = configuration.logger
    result = {}
    min_stale_secs = io_session_stale.get(proto, 0)
    # logger.debug("expire dead %s sessions for client %s" % (proto, client_id))
    live_sessions = lookup_live_sessions(configuration)
    if live_sessions is None:
        logger.warning("expire dead sessions requires psutil package")
        return result
    # logger.debug("expire dead %s sessions for %s with live_sessions: %s" %
    #             (proto, client_id, live_sessions))
    open_sessions = get_open_sessions(
        configuration, proto, client_id=client_id, do_lock=do_lock)
    # logger.debug("expire dead %s sessions for %s with open_sessions: %s" %
    #             (proto, client_id, open_sessions))
    current_timestamp = time.time()
    for open_session_id in open_sessions:
        if open_session_id in live_sessions:
            logger.debug("%s: ignore live session in expire: %s"
                         % (proto, open_session_id))
            continue
        timestamp = open_sessions[open_session_id]['timestamp']
        if current_timestamp - timestamp > min_stale_secs:
            logger.info("%s: expire dead session: %s"
                        % (proto, open_session_id))
            cur_session = open_sessions[open_session_id]
            cur_session_id = cur_session['session_id']
            closed_session = track_close_session(configuration, proto,
                                                 cur_session['client_id'],
                                                 cur_session['ip_addr'],
                                                 cur_session['tcp_port'],
                                                 session_id=cur_session_id,
                                                 timestamp=timestamp,
                                                 do_lock=do_lock)
            if closed_session is not None:
                result[cur_session_id] = closed_session
        else:
            logger.debug("%s: ignore recent session in expire: %s"
                         % (proto, open_session_id))

    return result


def expire_dead_sessions_chunked(configuration, proto, client_id=None,
                                 do_lock=True, chunk_size=64):
    """Lookup live sessions and compare with registered open sessions to expire
    dead sessions. This version applies full locking of the critical section
    but applies chunking to avoid holding the lock for long no matter how many
    sessions it needs to expire.
    Returns dictionary of closed sessions {session_id: session}
    """
    logger = configuration.logger
    result = {}
    min_stale_secs = io_session_stale.get(proto, 0)
    # logger.debug("expire dead %s sessions for client %s" % (proto, client_id))
    live_sessions = lookup_live_sessions(configuration)
    if live_sessions is None:
        logger.warning("expire dead sessions requires psutil package")
        return result
    # logger.debug("expire dead %s sessions for %s with live_sessions: %s" %
    #             (proto, client_id, live_sessions))

    # Read out current sessions and split into *guidance* chunks for expire.
    # Sessions might change before we actually lock and expire, but will only
    # ever get new sessions and remove old ones, which won't interfere.
    volatile_sessions = get_open_sessions(
        configuration, proto, client_id=client_id, do_lock=do_lock)
    ordered_sessions = list(volatile_sessions)
    ordered_sessions.sort()
    ordered_chunks = []
    for i in range(0, len(ordered_sessions), chunk_size):
        ordered_chunks.append(ordered_sessions[i:i+chunk_size])

    # Now use the guidance chunks to find and remove actually expired ones
    for chunk in ordered_chunks:
        logger.debug("expire dead %s sessions from: %s" % (proto, chunk))
        if do_lock:
            sessions_lock = _acquire_sessions_lock(configuration, proto,
                                                   exclusive=True)

        open_sessions = get_open_sessions(configuration, proto,
                                          client_id=client_id, do_lock=False)
        # logger.debug("expire dead %s sessions for %s with open_sessions: %s" %
        #             (proto, client_id, open_sessions))
        current_timestamp = time.time()
        chunk_close = []
        for open_session_id in chunk:
            if not open_session_id in open_sessions:
                logger.debug("%s: ignore recently closed session in expire: %s"
                             % (proto, open_session_id))
                continue
            if open_session_id in live_sessions:
                logger.debug("%s: ignore live session in expire: %s" %
                             (proto, open_session_id))
                continue
            timestamp = open_sessions[open_session_id]['timestamp']
            if current_timestamp - timestamp > min_stale_secs:
                logger.info("%s: expire dead session: %s" %
                            (proto, open_session_id))
                cur_session = open_sessions[open_session_id]
                chunk_close.append(cur_session)
            # else:
            #    logger.debug("%s: ignore recent session %s in expire: %d" %
            #                 (proto, open_session_id, timestamp))

        logger.debug("found %s sessions to chunk expire: %s" %
                     (proto, brief_list([i['session_id'] for i in chunk_close])))
        for closed_session in track_close_session_list(configuration, proto,
                                                       chunk_close,
                                                       do_lock=False):
            if closed_session is not None:
                result[closed_session['session_id']] = closed_session

        if do_lock:
            _release_sessions_lock(sessions_lock)

        # TODO: consider brief yield to throttle down?
        # time.sleep(0.01)

    return result


if __name__ == "__main__":
    import sys
    from mig.shared.conf import get_configuration_object
    configuration = get_configuration_object()
    _logger = configuration.logger
    client_id = 'john.doe@nowhere.org'
    proto = 'dummy'
    ip_addr = '127.0.0.1'
    if not proto in io_session_stale:
        io_session_stale[proto] = 120
    do_lock = True
    # Simulate with a reasonably big prime to excercise expire and avoid
    # perfect chunking fit.
    #sim_sessions = 19391
    #sim_sessions = 7937
    sim_sessions = 3779
    #sim_sessions = 1193
    #sim_sessions = 257
    if sys.argv[1:]:
        sim_sessions = int(sys.argv[1])
    _sessions_filename = "dummy-sessions.pck"
    clear_sessions(configuration, proto, do_lock)
    print("cleared all %s sessions" % proto)
    expire_helper_funcs = (expire_dead_sessions, expire_dead_sessions_chunked)
    for expire_helper in expire_helper_funcs:
        print("generating %d sessions in %s" %
              (sim_sessions, _sessions_filename))
        open_sessions = _load_sessions(configuration, proto, do_lock)
        now = time.time()
        for i in range(sim_sessions):
            sub = open_sessions[client_id] = open_sessions.get(client_id, {})
            subsub = sub[proto] = sub.get(proto, {})
            session_id = "%s-session-%.6d" % (client_id, i)
            entry = {'session_id': session_id, 'client_id': client_id,
                     'timestamp': int(now) - i, 'proto': proto, 'ip_addr': ip_addr,
                     'tcp_port': int(i)}
            subsub[session_id] = entry
        print("save %d sessions in %s" % (len(subsub), _sessions_filename))
        _save_sessions(configuration, proto, open_sessions, do_lock)
        active_cnt = active_sessions(configuration, proto, client_id, do_lock)
        print("now %s has %d active %s sessions recorded" % (client_id,
                                                             active_cnt,
                                                             proto))
        print("clean expired sessions in %s with %s" % (_sessions_filename,
                                                        expire_helper))
        before_expire = time.time()
        res = expire_helper(configuration, proto, do_lock=do_lock)
        after_expire = time.time()
        sorted_expired = list(res)
        sorted_expired.sort()
        print("cleaned expired %s sessions in %.3fs: %s" %
              (proto, (after_expire - before_expire),
               brief_list(sorted_expired)))
        active_cnt = active_sessions(configuration, proto, client_id, do_lock)
        print("now %s has %d active %s sessions recorded" % (client_id,
                                                             active_cnt,
                                                             proto))
        clear_sessions(configuration, proto, do_lock)
        print("cleared all %s sessions" % proto)
        active_cnt = active_sessions(configuration, proto, client_id, do_lock)
        print("now %s has %d active %s sessions recorded" % (client_id,
                                                             active_cnt,
                                                             proto))
