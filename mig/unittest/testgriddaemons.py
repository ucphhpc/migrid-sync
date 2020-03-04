#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# testgriddaemons- Set of unit tests for grid daemon helper functions
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

"""Unit tests for grid daemon helper functions"""

import sys
import time
import logging

from shared.griddaemons.ratelimits import default_max_user_hits, \
    expire_rate_limit, hit_rate_limit, update_rate_limit
from shared.griddaemons.sessions import active_sessions, \
    get_active_session, get_open_sessions, track_open_session, \
    track_close_session, track_close_expired_sessions

# TODO: Add unit test for validate_auth_attempt ?

if __name__ == "__main__":
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    logging.basicConfig(filename=None, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    conf.logger = logging
    test_proto, test_address, test_port, test_id, test_session_id = \
        'DUMMY', '127.0.0.42', 42000, \
        'user@some-domain.org', 'DUMMY_SESSION_ID'
    test_pw = "T3stp4ss"
    invalid_id = 'root'
    print "Running unit test on rate limit functions"
    print "Force expire all"
    (_, _, _, expired) = expire_rate_limit(conf, test_proto, fail_cache=0)
    print "Expired: %s" % expired
    this_pw = test_pw
    print "Emulate rate limit"
    for i in range(default_max_user_hits-1):
        hit = hit_rate_limit(conf, test_proto, test_address, test_id)
        print "Blocked: %s" % hit
        update_rate_limit(conf, test_proto, test_address, test_id, False,
                          this_pw)
        print "Updated fail for %s:%s from %s" % \
              (test_id, this_pw, test_address)
        this_pw += 'x'
        time.sleep(1)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    print "Check with original user and password again"
    update_rate_limit(conf, test_proto, test_address, test_id, False, test_pw)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    print "Check with original user and new password again to hit limit"
    update_rate_limit(conf, test_proto, test_address, test_id, False, this_pw)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    other_proto, other_address = "BOGUS", '127.10.20.30'
    other_id, other_pw = 'other@some.org', "0th3rP4ss"
    print "Update with other proto"
    update_rate_limit(conf, other_proto, test_address, test_id, False, test_pw)
    print "Update with other address"
    update_rate_limit(conf, test_proto, other_address, test_id, False, test_pw)
    print "Update with other user"
    update_rate_limit(conf, test_proto, test_address, other_id, False, test_pw)
    print "Check with same user from other address"
    hit = hit_rate_limit(conf, test_proto, other_address, test_id)
    print "Blocked: %s" % hit
    print "Check with other user from same address"
    hit = hit_rate_limit(conf, test_proto, test_address, other_id)
    print "Blocked: %s" % hit
    time.sleep(2)
    print "Force expire some entries"
    (_, _, _, expired) = expire_rate_limit(conf, test_proto,
                                           fail_cache=default_max_user_hits)
    print "Expired: %s" % expired
    print "Test reset on success"
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    update_rate_limit(conf, test_proto, test_address, test_id, True, test_pw)
    print "Updated success for %s from %s" % (test_id, test_address)
    hit = hit_rate_limit(conf, test_proto, test_address, test_id)
    print "Blocked: %s" % hit
    print "Check with same user from other address"
    hit = hit_rate_limit(conf, test_proto, other_address, test_id)
    print "Blocked: %s" % hit
    print "Check with other user from same address"
    hit = hit_rate_limit(conf, test_proto, test_address, other_id)
    print "Blocked: %s" % hit
    print "Check with invalid user from same address"
    hit = hit_rate_limit(conf, test_proto, test_address, invalid_id)
    print "Blocked: %s" % hit
    print "Test active session counting"
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Track open session"
    track_open_session(conf, test_proto, test_id, test_address, test_port)
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Track open session"
    track_open_session(conf, test_proto, test_id, test_address, test_port+1)
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Track close session"
    track_close_session(conf, test_proto, test_id, test_address, test_port, )
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Track close session"
    track_close_session(conf, test_proto, test_id, test_address, test_port+1, )
    active_count = active_sessions(conf, test_proto, test_id)
    print "Open sessions: %d" % active_count
    print "Test session tracking functions"
    expected_session_keys = ['ip_addr',
                             'tcp_port',
                             'session_id',
                             'authorized',
                             'client_id',
                             'timestamp']
    print "Track open session #1"
    open_session = track_open_session(conf,
                                      test_proto,
                                      test_id,
                                      test_address,
                                      test_port,
                                      test_session_id,
                                      authorized=True)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(open_session, dict):
        if open_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (open_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(open_session)
        sys.exit(1)
    print "Track open session #2"
    open_session = track_open_session(conf,
                                      test_proto,
                                      test_id,
                                      test_address,
                                      test_port+1,
                                      test_session_id+"_1",
                                      authorized=True)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(open_session, dict):
        if open_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (open_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(open_session)
        sys.exit(1)
    print "Track open session #3"
    open_session = track_open_session(conf,
                                      test_proto,
                                      test_id+"_1",
                                      test_address,
                                      test_port+2,
                                      test_session_id+"_2",
                                      authorized=True)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(open_session, dict):
        if open_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (open_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(open_session)
        sys.exit(1)
    print "Track open session #4"
    open_session = track_open_session(conf,
                                      test_proto,
                                      test_id+"_1",
                                      test_address,
                                      test_port+3,
                                      test_session_id+"_3",
                                      authorized=True)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(open_session, dict):
        if open_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (open_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(open_session)
    print "Track get open sessions #1"
    cur_open_sessions = get_open_sessions(conf, 'INVALID')
    if isinstance(cur_open_sessions, dict):
        if not cur_open_sessions:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % cur_open_sessions
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(cur_open_sessions)
        sys.exit(1)
    print "Track get open sessions #2"
    cur_open_sessions = get_open_sessions(conf, test_proto, 'INVALID')
    if isinstance(cur_open_sessions, dict):
        if not cur_open_sessions:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % cur_open_sessions
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(cur_open_sessions)
        sys.exit(1)
    print "Track get open sessions #3"
    cur_open_sessions = get_open_sessions(conf, test_proto)
    if isinstance(cur_open_sessions, dict):
        if len(cur_open_sessions.keys()) != 4:
            print "ERROR: Expected dictionary #keys: 4" \
                + ", found: %s, %s" % (len(cur_open_sessions.keys()),
                                       cur_open_sessions.keys())
            sys.exit(1)
        status = True
        for (key, val) in cur_open_sessions.iteritems():
            if not isinstance(val, dict) \
                    or val.keys() != expected_session_keys:
                status = False
                print "ERROR: Invalid session dictionary: '%s'" \
                    % (val)
                sys.exit(1)
        if status:
            print "OK"
    else:
        print "ERROR: Expected dictionary: %s" % type(cur_open_sessions)
        sys.exit(1)
    print "Track get open sessions #4"
    cur_open_sessions = get_open_sessions(conf,
                                          test_proto,
                                          client_id=test_id)
    if isinstance(cur_open_sessions, dict):
        if len(cur_open_sessions.keys()) != 2:
            print "ERROR: Expected dictionary #keys: 2" \
                + ", found: %s, %s" % (len(cur_open_sessions.keys()),
                                       cur_open_sessions.keys())
            sys.exit(1)
        status = True
        for (key, val) in cur_open_sessions.iteritems():
            if not isinstance(val, dict) \
                    or val.keys() != expected_session_keys:
                status = False
                print "ERROR: Invalid session dictionary: '%s'" \
                    % (val)
                sys.exit(1)
        if status:
            print "OK"
    else:
        print "ERROR: Expected dictionary: %s" % type(cur_open_sessions)
        sys.exit(1)
    print "Track get active session #1"
    active_session = get_active_session(conf,
                                        'INVALID',
                                        test_id,
                                        test_session_id)
    if isinstance(active_session, dict):
        if not active_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % active_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(active_session)
        sys.exit(1)
    print "Track get active session #2"
    active_session = get_active_session(conf,
                                        test_proto,
                                        'INVALID',
                                        test_session_id)
    if isinstance(active_session, dict):
        if not active_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % active_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(active_session)
        sys.exit(1)
    print "Track get active session #3"
    active_session = get_active_session(conf,
                                        test_proto,
                                        test_id,
                                        'INVALID')
    if isinstance(active_session, dict):
        if not active_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % active_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(active_session)
        sys.exit(1)
    print "Track get active session #4"
    active_session = get_active_session(conf,
                                        test_proto,
                                        test_id,
                                        test_session_id)
    if isinstance(active_session, dict):
        if active_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (active_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(active_session)
        sys.exit(1)
    print "Track close session #1"
    close_session = track_close_session(conf,
                                        'INVALID',
                                        test_id,
                                        test_address,
                                        test_port,
                                        session_id=test_session_id)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(close_session, dict):
        if not close_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % close_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(close_session)
        sys.exit(1)
    print "Track close session #2"
    close_session = track_close_session(conf,
                                        test_proto,
                                        'INVALID',
                                        test_address,
                                        test_port,
                                        session_id=test_session_id)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(close_session, dict):
        if not close_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % close_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(close_session)
        sys.exit(1)
    print "Track close session #3"
    close_session = track_close_session(conf,
                                        test_proto,
                                        test_id,
                                        test_address,
                                        test_port,
                                        session_id=None)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(close_session, dict):
        if not close_session:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % close_session
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(close_session)
        sys.exit(1)
    print "Track close session #4"
    close_session = track_close_session(conf,
                                        test_proto,
                                        test_id,
                                        test_address,
                                        test_port,
                                        session_id=test_session_id)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(close_session, dict):
        if close_session.keys() == expected_session_keys:
            print "OK"
        else:
            print "ERROR: Invalid session dictionary: '%s'" \
                % (close_session)
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(close_session)
        sys.exit(1)
    print "Track close expired sessions #1"
    expired_sessions = track_close_expired_sessions(conf,
                                                    'INVALID')
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(expired_sessions, dict):
        if not expired_sessions:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % expired_sessions
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(expired_sessions)
        sys.exit(1)
    print "Track close expired sessions #2"
    expired_sessions = track_close_expired_sessions(conf,
                                                    test_proto,
                                                    'INVALID')
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 1:
        print "ERROR: Excpected 1 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(expired_sessions, dict):
        if not expired_sessions:
            print "OK"
        else:
            print "ERROR: Excpected empty dictionary: %s" \
                % expired_sessions
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(expired_sessions)
        sys.exit(1)
    print "Track close expired sessions #3"
    expired_sessions = track_close_expired_sessions(conf,
                                                    test_proto,
                                                    client_id=test_id)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 2:
        print "ERROR: Excpected 2 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(expired_sessions, dict):
        if len(expired_sessions.keys()) == 1:
            status = True
            for (key, val) in expired_sessions.iteritems():
                if not isinstance(val, dict) \
                        or val.keys() != expected_session_keys:
                    status = False
                    print "ERROR: Invalid session dictionary: '%s'" \
                        % (val)
                    sys.exit(1)
            if status:
                print "OK"
        else:
            print "ERROR: Expected 1 expired session, found: %s" \
                % len(expired_sessions.keys())
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(expired_sessions)
        sys.exit(1)
    print "Track close expired sessions #4"
    expired_sessions = track_close_expired_sessions(conf,
                                                    test_proto)
    active_count = active_sessions(conf, test_proto, test_id)
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id, active_count)
        sys.exit(1)
    active_count = active_sessions(conf, test_proto, test_id+"_1")
    if active_count != 0:
        print "ERROR: Excpected 0 active session(s) for: %s, found: %d" \
            % (test_id+"_1", active_count)
        sys.exit(1)
    if isinstance(expired_sessions, dict):
        if len(expired_sessions.keys()) == 2:
            status = True
            for (key, val) in expired_sessions.iteritems():
                if not isinstance(val, dict) \
                        or val.keys() != expected_session_keys:
                    status = False
                    print "ERROR: Invalid session dictionary: '%s'" \
                        % (val)
                    sys.exit(1)
            if status:
                print "OK"
        else:
            print "ERROR: Expected 2 expired session, found: %s" \
                % len(expired_sessions.keys())
            sys.exit(1)
    else:
        print "ERROR: Expected dictionary: %s" % type(expired_sessions)
        sys.exit(1)
