#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# griddaemons.rate_limits - grid daemon rate limit helper functions
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

"""MiG daemon rate limit functions"""

import fnmatch
import time
import threading
import traceback

default_max_user_hits, default_fail_cache = 5, 120
default_user_abuse_hits = 25
default_proto_abuse_hits = 25
default_max_secret_hits = 10

_rate_limits = {}
_rate_limits_lock = threading.Lock()


def hit_rate_limit(configuration, proto, client_address, client_id,
                   max_user_hits=default_max_user_hits):
    """Check if proto login from client_address with client_id should be
    filtered due to too many recently failed login attempts.
    The rate limit check lookup in rate limit cache.
    The rate limit cache is a set of nested dictionaries with
    client_address, protocol, client_id and secret as keys,
    the structure is shown in the 'update_rate_limit' doc-string.
    The rate limit cache maps the number of fails/hits for each
    IP, protocol, username and secret and helps distinguish e.g.
    any other users coming from the same gateway address.
    We always allow up to max_user_hits failed login attempts for a given username
    from a given address. This is in order to make it more difficult to
    effectively lock out another user with impersonating or random logins even
    from the same (gateway) address.

    NOTE: Use expire_rate_limit to remove old rate limit entries from the cache
    """
    logger = configuration.logger
    refuse = False

    _rate_limits_lock.acquire()

    _address_limits = _rate_limits.get(client_address, {})
    _proto_limits = _address_limits.get(proto, {})
    _user_limits = _proto_limits.get(client_id, {})
    proto_hits = _proto_limits.get('hits', 0)
    user_hits = _user_limits.get('hits', 0)
    if user_hits >= max_user_hits:
        refuse = True

    _rate_limits_lock.release()

    if refuse:
        logger.warning("%s reached hit rate limit %d"
                       % (proto, max_user_hits)
                       + ", found %d of %d hit(s) "
                       % (user_hits, proto_hits)
                       + " for %s from %s"
                       % (client_id, client_address))

    return refuse


def update_rate_limit(configuration, proto, client_address, client_id,
                      login_success,
                      secret=None,
                      ):
    """Update rate limit database after proto login from client_address with
    client_id and boolean login_success status.
    The optional secret can be used to save the hash or similar so that
    repeated failures with the same credentials only count as one error.
    Otherwise some clients will retry on failure and hit the limit easily.
    The rate limit database is a set of nested dictionaries with
    client_address, protocol, client_id and secret as keys
    mapping the number of fails/hits for each IP, protocol, username and secret
    This helps distinguish e.g. any other users coming from the same
    gateway address.
    Example of rate limit database entry:
    {'127.0.0.1': {
        'fails': int (Total IP fails)
        'hits': int (Total IP fails)
        'sftp': {
            'fails': int (Total protocol fails)
            'hits': int (Total protocol hits)
            'user@some-domain.org: {
                'fails': int (Total user fails)
                'hits': int (Total user hits)
                'XXXYYYZZZ': {
                    'timestamp': float (Last updated)
                    'hits': int (Total secret hits)
                }
            }
        }
    }
    Returns tuple with updated hits:
    (address_hits, proto_hits, user_hits, secret_hits)
    """
    logger = configuration.logger
    status = {True: "success", False: "failure"}
    address_fails = old_address_fails = 0
    address_hits = old_address_hits = 0
    proto_fails = old_proto_fails = 0
    proto_hits = old_proto_hits = 0
    user_fails = old_user_fails = 0
    user_hits = old_user_hits = 0
    secret_hits = old_secret_hits = 0
    timestamp = time.time()
    if not secret:
        secret = timestamp

    _rate_limits_lock.acquire()
    try:
        # logger.debug("update rate limit db: %s" % _rate_limits)
        _address_limits = _rate_limits.get(client_address, {})
        if not _address_limits:
            _rate_limits[client_address] = _address_limits
        _proto_limits = _address_limits.get(proto, {})
        if not _proto_limits:
            _address_limits[proto] = _proto_limits
        _user_limits = _proto_limits.get(client_id, {})

        address_fails = old_address_fails = _address_limits.get('fails', 0)
        address_hits = old_address_hits = _address_limits.get('hits', 0)
        proto_fails = old_proto_fails = _proto_limits.get('fails', 0)
        proto_hits = old_proto_hits = _proto_limits.get('hits', 0)
        user_fails = old_user_fails = _user_limits.get('fails', 0)
        user_hits = old_user_hits = _user_limits.get('hits', 0)
        if login_success:
            if _user_limits:
                address_fails -= user_fails
                address_hits -= user_hits
                proto_fails -= user_fails
                proto_hits -= user_hits
                user_fails = user_hits = 0
                del _proto_limits[client_id]
        else:
            if not _user_limits:
                _proto_limits[client_id] = _user_limits
            _secret_limits = _user_limits.get(secret, {})
            if not _secret_limits:
                _user_limits[secret] = _secret_limits
            secret_hits = old_secret_hits = _secret_limits.get('hits', 0)
            if secret_hits == 0:
                address_hits += 1
                proto_hits += 1
                user_hits += 1
            address_fails += 1
            proto_fails += 1
            user_fails += 1
            secret_hits += 1
            _secret_limits['timestamp'] = timestamp
            _secret_limits['hits'] = secret_hits
            _user_limits['fails'] = user_fails
            _user_limits['hits'] = user_hits
        _address_limits['fails'] = address_fails
        _address_limits['hits'] = address_hits
        _proto_limits['fails'] = proto_fails
        _proto_limits['hits'] = proto_hits
    except Exception, exc:
        logger.error("update %s Rate limit failed: %s" % (proto, exc))
        logger.info(traceback.format_exc())

    _rate_limits_lock.release()

    """
    logger.debug("update %s rate limit %s for %s\n"
                 % (proto, status[login_success], client_address)
                 + "old_address_fails: %d -> %d\n"
                 % (old_address_fails, address_fails)
                 + "old_address_hits: %d -> %d\n"
                 % (old_address_hits, address_hits)
                 + "old_proto_fails: %d -> %d\n"
                 % (old_proto_fails, proto_fails)
                 + "old_proto_hits: %d -> %d\n"
                 % (old_proto_hits, proto_hits)
                 + "old_user_fails: %d -> %d\n"
                 % (old_user_fails, user_fails)
                 + "old_user_hits: %d -> %d\n"
                 % (old_user_hits, user_hits)
                 + "secret_hits: %d -> %d\n"
                 % (old_secret_hits, secret_hits))
    """

    if user_hits != old_user_hits:
        logger.info("update %s rate limit" % proto
                    + " %s for %s" % (status[login_success], client_address)
                    + " from %d to %d hits" % (old_user_hits, user_hits))

    return (address_hits, proto_hits, user_hits, secret_hits)


def expire_rate_limit(configuration, proto='*',
                      fail_cache=default_fail_cache):
    """Remove rate limit cache entries older than fail_cache seconds.
    Only entries in proto list will be touched,
    If proto list is empty all protocols are checked.
    Returns tuple with updated hits and expire count
    (address_hits, proto_hits, user_hits, expired)
    """
    logger = configuration.logger
    now = time.time()
    address_hits = proto_hits = user_hits = expired = 0
    # logger.debug("expire entries older than %ds at %s" % (fail_cache, now))
    _rate_limits_lock.acquire()
    try:
        for _client_address in _rate_limits.keys():
            # debug_msg = "expire addr: %s" % _client_address
            _address_limits = _rate_limits[_client_address]
            address_fails = old_address_fails = _address_limits['fails']
            address_hits = old_address_hits = _address_limits['hits']
            for _proto in _address_limits.keys():
                if _proto in ['hits', 'fails'] \
                        or not fnmatch.fnmatch(_proto, proto):
                    continue
                _proto_limits = _address_limits[_proto]
                # debug_msg += ", proto: %s" % _proto
                proto_fails = old_proto_fails = _proto_limits['fails']
                proto_hits = old_proto_hits = _proto_limits['hits']
                for _user in _proto_limits.keys():
                    if _user in ['hits', 'fails']:
                        continue
                    # debug_msg += ", user: %s" % _user
                    _user_limits = _proto_limits[_user]
                    user_fails = old_user_fails = _user_limits['fails']
                    user_hits = old_user_hits = _user_limits['hits']
                    for _secret in _user_limits.keys():
                        if _secret in ['hits', 'fails']:
                            continue
                        _secret_limits = _user_limits[_secret]
                        if _secret_limits['timestamp'] + fail_cache < now:
                            secret_hits = _secret_limits['hits']
                            # debug_msg += \
                            #"\ntimestamp: %s, secret_hits: %d" \
                            #    % (_secret_limits['timestamp'], secret_hits) \
                            #    + ", secret: %s" % _secret
                            address_fails -= secret_hits
                            address_hits -= 1
                            proto_fails -= secret_hits
                            proto_hits -= 1
                            user_fails -= secret_hits
                            user_hits -= 1
                            del _user_limits[_secret]
                            expired += 1
                    _user_limits['fails'] = user_fails
                    _user_limits['hits'] = user_hits
                    # debug_msg += "\nold_user_fails: %d -> %d" \
                    # % (old_user_fails, user_fails) \
                    #    + "\nold_user_hits: %d -> %d" \
                    #    % (old_user_hits, user_hits)
                    if user_fails == 0:
                        # debug_msg += "\nRemoving expired user: %s" % _user
                        del _proto_limits[_user]
                _proto_limits['fails'] = proto_fails
                _proto_limits['hits'] = proto_hits
                # debug_msg += "\nold_proto_fails: %d -> %d" \
                # % (old_proto_fails, proto_fails) \
                #    + "\nold_proto_hits: %d -> %d" \
                #    % (old_proto_hits, proto_hits)

            _address_limits['fails'] = address_fails
            _address_limits['hits'] = address_hits
            # debug_msg += "\nold_address_fails: %d -> %d" \
            # % (old_address_fails, address_fails) \
            #    + "\nold_address_hits: %d -> %d" \
            #    % (old_address_hits, address_hits)
            # logger.debug(debug_msg)

    except Exception, exc:
        logger.error("expire rate limit failed: %s" % exc)
        logger.info(traceback.format_exc())

    _rate_limits_lock.release()

    if expired:
        logger.info("expire %s rate limit expired %d items" % (proto,
                                                               expired))
        # logger.debug("expire %s rate limit expired %s" % (proto, expired))

    return (address_hits, proto_hits, user_hits, expired)


def penalize_rate_limit(configuration, proto, client_address, client_id,
                        user_hits, max_user_hits=default_max_user_hits):
    """Stall client for a while based on the number of rate limit failures to
    make sure dictionary attackers don't really load the server with their
    repeated force-failed requests. The stall penalty is a linear function of
    the number of failed attempts.
    """
    logger = configuration.logger
    sleep_secs = 3 * (user_hits - max_user_hits)
    if sleep_secs > 0:
        logger.info("stall %s rate limited user %s from %s for %ds" %
                    (proto, client_id, client_address, sleep_secs))
        time.sleep(sleep_secs)
    return sleep_secs
