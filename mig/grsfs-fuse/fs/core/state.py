#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# state - [insert a few words of module description on this line]
# Copyright (C) 2003-2011  The MiG Project lead by Brian Vinter
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

"""
Contains:
    current state information
    group handling operations.
    
Not thread-safe.
Callers should use join/leave meta-operations rather than operating on the members set.


Created by Jan Wiberg on 2010-03-21.
Copyright (c) 2010 Jan Wiberg. All rights reserved.
"""

from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
from builtins import object
import itertools
import os
import sys
import time
if sys.version_info[0] >= 3:
    import pickle
else:
    import cPickle as pickle

from core.specialized.aux import total_ordering

SINGULAR = 0  # standalone
MASTER = 1  # member
REPLICA = 2  # member

UPGRADING = 10  # spare
SPARE = 11  # spare
REMOTE_READER = 12  # spare


@total_ordering
class Peer(object):
    def __init__(self, connection, me=False, score=-1, recontact=True, initial_type=REPLICA):
        # validate - non-pythonic but tired of getting bitten by this
        (host, port) = connection
        assert isinstance(me, bool) and isinstance(
            host, str) and isinstance(port, int)

        # 'immutable' data
        self.connection = (host, port)  # ensures that its a tuple, not a list.
        self.me = me

        # transient information that may be changed at any time.
        self.recontact = recontact
        self.score = score
        self.dead = False
        self.link = None
        self.last_seen = time.time()
        self.instancetype = initial_type

    def is_alive_active(self):
        """
        true if this is not a spare/upgrading and not dead
        """
        return self.instancetype < UPGRADING and self.dead == False

    def is_active_member(self):
        """
        true if is_active_member_core holds AND is not the "me" instance AND it has an active link
        """
        return self.me == False and self.link is not None and self.is_alive_active()

    def should_connect_to(self):
        """
            Active members should be connected to. Upgrading
        """
        return self.me == False and self.link is None and self.dead == False

    def __lt__(self, other):
        return self.score < other.score

    def __gt__(self, other):
        return self.score > other.score

    def __eq__(self, other):
        #print "Comparing peer %s to %s" % (self, other)
        return (self.connection == other.connection)

    def __bs(self, val):
        """
        Translates a boolean to short string format for debug printing.
        """
        if val:
            return "Y"
        return "n"

    def __str__(self):
        """docstring for __str__"""
        return "<P%s. L:%s|M:%s|T:%d>" % (self.connection, self.__bs(self.link is not None), self.__bs(self.me), self.instancetype)

    def __repr__(self):
        return self.__str__()


class State(object):
    """docstring for State"""
    group = []  # the set of Peer objects
    state = {}  # internal filesystem statekeeping (not related to network)

    def __init__(self, logger, options, whoami):
        self.logger = logger
        self.logger.debug("> State.init called")
        self.options = options
        self._load_state()

        self.logger.debug("> State.init loaded state")

        # election state keeping
        self.must_run_election = False
        self.election_in_progress = False

        if self.options.mincopies == 0:
            me_type = SINGULAR  # mostly for debugging
        elif self.options.neverparticipate:
            me_type = REMOTE_READER
        elif self.options.spare:
            me_type = SPARE
        else:
            me_type = REPLICA
        self.me = Peer(connection=whoami, me=True, initial_type=me_type)
        self.group.append(self.me)

        self.logger.debug(
            "> State.init initial instance type set to %s" % self.me.instancetype)

        try:
            for conn_info in self.options.initial_connect_list:
                if conn_info == whoami:
                    self.logger.info("Loopback connection ignored")

                self.logger.info("%s.__init__: Added %s to active peer list" % (
                    self.__class__.__name__, conn_info))
                self.group.append(
                    Peer(connection=conn_info, initial_type=REPLICA))

            from core.specialized.benchmark import compute_score
            self.score = compute_score(self.options)
            self.logger.info("Scored %s on the benchmark, logical clock at %d" % (
                self.score, self.state['clock']))

            # replication
            self.can_replicate = False

        except Exception as v:
            print(v)

    def _load_state(self):
        bss = self.options.backingstorestate
        if not (os.path.exists(bss) and os.path.isfile(bss)):
            self.state = {"clock": 0}
            f = open(bss, "w")
            pickle.dump(self.state, f)
            f.close()
        else:
            f = open(bss, "r")
            self.state = pickle.load(f)
            f.close()

        self.current_step = self.state['clock']

    def get_instancetype(self):
        """
            Wraps the call to self.me
        """
        return self.me.instancetype

    instancetype = property(get_instancetype, None)

    def _get_identification(self):
        """
        Returns the core information that needs to be known about this instance.
        """
        return (self.options.serveraddress, self.options.serverport, self.current_step, self.score, self.options.neverparticipate)

    identification = property(_get_identification, None)
    #######################################################
    # MEMBER OPERATIONS
    #######################################################

    def _get_connections_only(self):
        """Return just a list of tuples with the connection information to the peers we know of"""
        return [peer.connection for peer in self.group]

    conn_info_all = property(_get_connections_only, None)

    def _mark_can_replicate(self):
        """
            Sets a flag that specifies if replication is currently possible
            Must be called at every group or state change.
        """
        if self.instancetype == MASTER:
            # import pdb
            # pdb.set_trace()
            count_actives = len(self.active_members) + 1
            count_upgrades = len(
                [p for p in self.group if p.instancetype >= UPGRADING])
            # Print it out so we can tell whats going on even if logger is disabled
            print("can_replicate: step %d, actives %s, upgrades %s for group %s" % (
                self.current_step, count_actives, count_upgrades, self.group))
            if count_actives >= self.options.maxcopies:
                self.can_replicate = True
            else:
                self.can_replicate = count_actives >= self.options.mincopies and (
                    count_actives + count_upgrades) >= self.options.maxcopies
        else:
            self.can_replicate = False
        # done

    def _get_active_members(self):
        """
        returns a list of peers that we have connected to and is not ourselves.
        Opposite of get_connect_list
        """
        return sorted([peer for peer in self.group if peer.is_active_member()])

    active_members = property(_get_active_members, None)

    def _get_unconnected(self):
        """
        Returns a list of peers that we know about but have not yet connected to, or am ourselves.
        Opposite of get_connected 

        Does not return those that are spares.
        """
        return [peer for peer in self.group if peer.should_connect_to()]

    unconnected_nodes = property(_get_unconnected, None)

    def _get_everyone(self):
        """
        All that is not me
        """
        return [peer for peer in self.group if not peer.me and peer.link is None and peer.dead != False]

    everyone = property(_get_everyone, None)

    def _get_watchee(self):
        """
        Returns the member that it is my responsibility to watch.

        master watches replica2, spare watches nobody, replica1 watches master, replica2 watches replica1.
        """
        connected = sorted(
            [peer for peer in self.group if peer.is_alive_active()])
        #print "Whole group is now %s. Core group is %s" % (self.group, connected)
        if len(connected) <= 1 or self.get_instancetype() >= UPGRADING:
            return None

        return connected[(connected.index(self.me) + len(connected) - 1) % len(connected)]

    watchee = property(_get_watchee, None)

    def _get_spares(self):
        return [peer for peer in self.group if peer.instancetype == SPARE]

    spares = property(_get_spares, None)

    def find(self, connection_tuple):
        #print "Checking for %s in %s." %(connection_tuple, self.group)
        for p in self.group:
            if p.connection == connection_tuple:
                return p
        return None

    def compare(self, remote_conn_info_all):
        """
        Compares for equality. Tries to fix data that may have been mangled during serialization
        """
        remote_fixed = set()
        local_fixed = set()
        for p in remote_conn_info_all:
            remote_fixed.add(tuple(p))

        for p in self.conn_info_all:
            local_fixed.add(tuple(p))

        return local_fixed == remote_fixed

    # count properties
    def _get_member_size(self):
        return len(self.active_members) + (1 if self.me.instancetype < SPARE else 0)

    active_group_size = property(_get_member_size, None)

    #######################################################
    # Logical clock state machine -- advance, checkpoint
    # Not thread-safe by design
    #######################################################
    def checkpoint_id(self):
        """Persists the sequential id"""
        f = open(self.options.backingstorestate, "w")
        self.state['clock'] = self.current_step
        pickle.dump(self.state, f, protocol=-1)
        f.close()

    def advance_id(self):
        """
        Return a unique sequential id
        """
        self.current_step += 1
        return self.current_step
