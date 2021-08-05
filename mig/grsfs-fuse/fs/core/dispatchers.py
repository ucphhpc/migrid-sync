#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# dispatchers - [insert a few words of module description on this line]
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
    Contains dispatcher related functionality
"""

import errno
import socket
import time
from core.exceptions import GRSException, GRSReplicaOutOfStep


class _dispatcher(object):
    """
        Non-replicating dispatcher.
        Not intended for normal usage, but can be useful for debugging.
    """

    def __init__(self, kernel, force_fsync_after_write=False):
        self.kernel = kernel
        self.state = kernel.state
        self.options = kernel.options
        self.network = kernel.network
        self.storage = kernel.storage
        self.logger = kernel.logger
        self.force_fsync_after_write = force_fsync_after_write
        self.last_operation = None

    def do_read_op(self, internal, op, *args):
        self.logger.debug("%s.do_read_op: %s%s (%s)" %
                          (self.__class__.__name__, op, args, internal))
        with(self.storage.getlock(None).readlock):
            f = self._resolve_for_storage(internal)
            return getattr(self.storage, op)(f, *args)

    def do_write_op(self, internal, op, *args):
        self.logger.debug("%s.do_write_op: %s%s (%s)" %
                          (self.__class__.__name__, op, args, internal))
        with(self.storage.getlock(None).writelock):
            f = self._resolve_for_storage(internal)
            ret = getattr(self.storage, op)(f, *args)
            if self.force_fsync_after_write:
                self.force_sync()
            return ret

    def force_sync(self):
        self.logger.debug("Fsync requested")

    def _resolve_for_storage(self, internal_data):
        if internal_data is not None and 'file_id' in internal_data:
            # FIXME check if its possible to get a boom here.
            return self.kernel._oft_get(internal_data['file_id'])
        return None

    def _flatten(self, l):
        out = []
        for item in l:
            if isinstance(item, (list, tuple)):
                out.extend(item)
            else:
                out.append(item)
        return out


class _master_dispatcher(_dispatcher):
    """
        Orders operations to preverse consistency and integrity.
    """

    def __init__(self, kernel, force_fsync_after_write=False):
        super(_master_dispatcher, self).__init__(
            kernel, force_fsync_after_write)

    def _replicate(self, internal, op, *args):
        """
            Caller must be writelocked when entering this
        """
        step = self.state.advance_id()

        peer_list = self.state.active_members
        self.logger.debug("Replicating to %s" % peer_list)
        count = 0
        internal['step'] = step

        # HACK we need arguments in a really specific way, so grossly mangle around until it's right
        arguments_combined = list(args)
        if op == 'write':
            arguments_combined[0] = self.network.wrapbinary(
                arguments_combined[0])

        arguments_combined.append(internal)
        arguments_combined = tuple(arguments_combined)

        for peer in peer_list:
            try:
                # call remote RPC to persist the change
                getattr(peer.link, op)(*arguments_combined)
                count += 1
            except Exception as v:  # TODO: more intelligent error handling
                self.logger.info(
                    "_replicate error %s of type %s, removing %s" % (v, type(v), peer))
                self.kernel._handle_dead_peer(peer)

        self.state.checkpoint_id()
        return count

    def do_write_op(self, internal, op, *args):
        self.logger.debug("%s.do_write_op: %s%s (%s)" %
                          (self.__class__.__name__, op, args, internal))
        with(self.storage.getlock(None).writelock):
            if not self.state.can_replicate:
                self.logger.info(
                    "%s.write attempted but no group available for replication" % self.__class__.__name__)
                return -errno.EROFS

            if internal is None:
                internal = {}
            if self._replicate(internal, op, *args) >= self.options.mincopies + 1:
                # Be unhappy if replication couldnt happen to at least one peer.
                # It is ok if we succeeded at at least one
                self.logger.error("%s.the last write failed." %
                                  self.__class__.__name__)
                return -errno.EIO

            f = self._resolve_for_storage(internal)
            ret = getattr(self.storage, op)(f, *args)
            if self.force_fsync_after_write:
                self.force_sync()
            return ret

    def _signal_critical(self, exc_class, mesg):
        self.logger.error(mesg)
        # remove myself from group
        try:
            for m in self.state.get_connected():
                self.logger.debug("Saying goodbye from me to %s" % m)
                m.link.node_unregister(self.state.me)
        except Exception as v:
            self.logger.error(
                "Error autodropping from group due to internal error, %s" % v)
        raise exc_class(mesg)
# END_DEF _master_dispatcher


class _replica_dispatcher(_master_dispatcher):
    """
        Orders operations to preverse consistency and integrity.
        Read-only version - goes over the network
        Storage may be used for caching. Writing not possible.
    """

    def __init__(self, kernel, force_fsync_after_write=False):
        super(_replica_dispatcher, self).__init__(
            kernel, force_fsync_after_write)

    def do_write_op(self, internal, op, *args):
        if internal is None or not 'step' in internal:  # reject local writes
            return -errno.EROFS  # -errno.EROFS # for read-only

        self.logger.debug("%s.do_write_op: %s%s (%s)" %
                          (self.__class__.__name__, op, args, internal))

        # TODO handle master failure here
        with(self.storage.getlock(None).writelock):
            # if we want spin waiting for the correct step, do it here.
            if internal['step'] != self.state.current_step+1:
                self._signal_critical(GRSReplicaOutOfStep,
                                      "Received unexpected step %d, this clock is at %d" % (internal['step'], self.state.current_step))

            self.state.advance_id()
            self.last_operation = (op, args)

            args = list(args)
            if op == "write":
                args[0] = self.network.unwrapbinary(args[0])
            args = tuple(args)

            try:
                # either crash or perform
                f = self._resolve_for_storage(internal)
                ret = getattr(self.storage, op)(f, *args)
            except (IOError, OSError) as xxx_todo_changeme:
                (eerrno, strerror) = xxx_todo_changeme.args
                if eerrno not in [errno.ENOENT, errno.EPERM]:
                    self.logger.debug(
                        "Unacceptable local error occured %s: %s" % (eerrno, strerror))
                    return -errno.EIO
            except Exception as v:
                self.logger.debug(
                    "Undiagnosed local write problem: %s:%s" % (type(v), v))
                return -errno.EIO

            self.last_operation = (op, args)
            if self.force_fsync_after_write:
                self.force_sync()

            self.state.checkpoint_id()
            return ret

# END_DEF _replica_dispatcher


class _ondemandfetch_dispatcher(_replica_dispatcher):
    """
        Orders operations to preverse consistency and integrity.
        Read-only version - goes over the network
        Storage may be used for caching. Writing not possible.
    """

    def __init__(self, kernel, force_fsync_after_write=False):
        super(_ondemandfetch_dispatcher, self).__init__(
            kernel, force_fsync_after_write)

    def do_read_op(self, internal, op, *args):
        self.logger.debug("-- %s.do_read_op: %s%s" %
                          (self.__class__.__name__, op, args))
        with(self.storage.getlock(None).readlock):
            try:
                connect_list = self.state.active_members
                if len(connect_list) < 1:
                    return -errno.EIO
                # PROPOSAL this could be made more flexible so we switch amongst connected partners
                peer = connect_list[0]
                self.logger.debug("Fetching from %s" % peer)
                arguments_combined = list(args)

                arguments_combined.append(internal)
                arguments_combined = tuple(arguments_combined)

                ret = getattr(peer.link, op)(*arguments_combined)
                return ret
            except socket.error as vse:  # fixme: leaky abstraction
                self.kernel._handle_dead_peer(peer)

                return self.do_read_op(internal, op, *args)
            except Exception as v:  # this is any kind of normal error
                self.logger.debug(
                    "Remote op received error %s of type %s" % (v, type(v)))
                raise

    def do_write_op(self, internal, op, *args):
        return -errno.EROFS
# END_DEF __ondemandfetch_dispatcher
