#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# kernel - [insert a few words of module description on this line]
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
    Implements operations
"""
from __future__ import print_function


import os, threading, time, errno, socket, signal

from core.specialized.aux import flag2mode
from core.storage.passthrough import Passthrough as storage_impl
import core.network.rpc as network_impl
from core.state  import State, Peer, SINGULAR, MASTER, REPLICA, UPGRADING, SPARE, REMOTE_READER
from core.specialized.logger import Logger
from core.dispatchers import _dispatcher, _master_dispatcher, _replica_dispatcher, \
                            _ondemandfetch_dispatcher
from core.exceptions import GRSException
from core.specialized import ReadWriteLock

def stacktraces():
    import sys, traceback
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# ThreadID: %s" % threadId)
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    
    import pprint
    pp = pprint.PrettyPrinter()
    pp.pprint(code)
    
def instancetypestr(instancetype):
    strs = {SINGULAR: ' standalone ',
            MASTER: '** MASTER **',
            REPLICA: ' replica ',
            UPGRADING: ' upgrading',
            SPARE: ' spare ',
            REMOTE_READER: ' odf reader '
            }
            
    return strs[instancetype]
                        
class _system(threading.Thread):
    """
        Handles periodic maintenance and heartbeat
    """
    def __init__(self, kernel):
        threading.Thread.__init__(self)
        self.kernel = kernel
        self.options = kernel.options # convinience
        self.logger = kernel.logger 
        self.state = kernel.state
        self.stop = False
        
    def run(self):
        while not self.stop: 
            self.logger.debug("Heartbeat %s (%s)" % (instancetypestr(self.state.instancetype), self.state.group))
            self.state._mark_can_replicate()
            try: # will detect a deadlock in the kernel, debug only
                self.kernel.storage.getlock(None).acquireWrite(30) 
            except Exception as v:
                print(" !!!!!!!!!!!!!!!! THREAD HANG DETECTED !!!!!!!!!!!!!!!!!")
                print(v)
                stacktraces()
                self.kernel.fshalt()
                return
                
            deadies = [p for p in self.state.group if p.dead]
            for p in deadies:
                self.logger.debug("Permanently killing %s" % p)
                self.state.group.remove(p)
                self.state._mark_can_replicate()
                
            if self.state.instancetype == MASTER and \
                not self.state.must_run_election and \
                len(self.state.unconnected_nodes) == 0 and \
                self.state.active_group_size < self.options.maxcopies  and \
                len(self.state.spares) > 0:
                # we are low on members, act on it.
                self.kernel._spare_upgrade()                
                                
            # Somebody connected to us, or we were told somebody is out there
            # Now connect back to them.
            if len(self.state.unconnected_nodes) > 0:                
                self.logger.info("%s: new unconnected peers discovered, connecting back. Elect: %s" % (__name__, self.state.must_run_election))
                self.kernel._connect_to_known_peers()
            self.kernel.storage.getlock(None).release()
            
            peer = self.state.watchee     
            #self.logger.debug("Checking health of %s" % peer) # noisy
            if peer is not None:
                try:
                    result = peer.link.ping(self.state.me.connection, None)
                    if result == 'LOST':
                        # Peer lost us!
                        msg = "%s %s lost contact with us without us noticing - investigate!" % (__name__, peer)
                        self.logger.error(msg)
                except Exception as v:
                    # remove peer if anything goes wrong. Lock just around this.
                    self.logger.info("%s lost contact with %s over %s" % (__name__, peer, v))
                    self.kernel._handle_dead_peer(peer)
                        
            with(self.kernel.storage.getlock(None).writelock): 
                #self.logger.info("Group now is %s. unconnected_nodes %s"  % ( self.state.group, self.state.unconnected_nodes))
                if self.state.must_run_election and not self.state.election_in_progress and len(self.state.unconnected_nodes) == 0:
                    self.kernel._run_election()
                    
                
            time.sleep(self.options.heartbeat)
        

class Kernel(object):
            
    class __kernel(object):
        """ Implementation of the singleton interface """              
        
        def __init__(self, options):
            if options is None:
                raise Exception("A configuration instance must be supplied")
            
            self.options = options
            self.oft_lock = threading.RLock()
            self.oft_rwlock = ReadWriteLock.ReadWriteLock()
            self.oft = {}
            
                             
        def fsinit(self):
            self.logger = Logger(self.options.logdir, "%s.%s.log" % \
                (self.options.serveraddress, self.options.serverport), False, self.options.logverbosity, self.options.logquiet) 
            self.logger.debug("> Kernel.fsinit")
    
            try:
                self.state = State(self.logger, self.options, (self.options.serveraddress, self.options.serverport))

                self.logger.debug("> Kernel.fsinit state created")
                # instance type is handled within state
        
        
                self.storage = storage_impl(self.options)
                self.network = network_impl            

                self.storage.start()
                self.network.start(self, self.options)

                self.logger.debug("> Kernel.fsinit storage and network modules up")
        
                self.maintenance = _system(self)
                self.maintenance.start() # start the periodic heartbeat
                self.logger.debug("> Kernel.fsinit maintenance thread up")
        
                # pick the initial dispatcher
                self.dispatcher = self._pick_dispatcher()
            except Exception as v:
                self.logger.error("Crash in fsinit - filesystem will hang now %s" % v)
            self.logger.debug("< Leaving Kernel.fsinit")
            
        def fshalt(self):
            """Shut down in an orderly fashion"""
            self.dispatcher.force_sync()
            self.maintenance.stop = True
            self.maintenance.join()    
            self.network.stop()

                     
        # PRIVATE/INTERNAL
        # communication internal
        def __broadcast(self, force_election, op, *args):
            ret = []            
            self.logger.debug("__broadcast '%s/%s'" % (op, str(args)))
            for connected_peer in self.state.active_members:
                try:
                    ret.append((connected_peer, getattr(connected_peer.link, op)(*args)))
                except Exception as v:
                    self.logger.error("Broadcast - peer %s faulted, error '%s'"% (connected_peer, v))
                    self._handle_dead_peer(connected_peer, force_election)
            return ret
                    
        # statekeeping and process management
        def _pick_dispatcher(self):
            """
                Pick a dispatcher
            """
            # Change dispatcher requires we are sure that all pending operations have been consistently flushed
            dispatch_class = None

            itype = self.state.instancetype
            if itype == SINGULAR:
                dispatch_class = _dispatcher # special case for local-only
            elif itype == MASTER:                
                dispatch_class = _master_dispatcher
            elif itype == REPLICA: 
                dispatch_class = _replica_dispatcher
            elif itype == SPARE: 
                dispatch_class = _ondemandfetch_dispatcher
            else:
                raise Exception("Invalid instance_type %d when picking dispatcher" % itype)        
            
            self.logger.info("Changing dispatcher to '%s'" % dispatch_class.__name__)
            self.state._mark_can_replicate()            
            return dispatch_class(self)
        #END_DEF pick_dispatcher     
        
        def _add_new_peer(self, peer):
            """
            peer: a Peer object which may or may not be empty (other than connection information)
            """
            self.logger.info("Seeing if we need to add %s to group of %s." % (peer, self.state.group))
            existing = self.state.find(peer.connection)
            if existing is None:
                self.logger.debug("Adding %s TO %s" % (peer, self.state.group))
                self.state.group.append(peer)
                self.state.group = sorted(self.state.group)
                self.state._mark_can_replicate()
            else:
                self.logger.warning("Peer %s already known" % peer) # it's a (non-critical) bug if this happens
                 
        
        def _handle_dead_peer(self, peer, force_election = True):
            if not peer.dead:
                self.logger.info("Lost contact with %s, removing from group and reconfiguring" % peer)
                peer.dead = True
                self.state._mark_can_replicate()

            if force_election:
                self.state.must_run_election = True
                
        
        def _connect_to_known_peers(self):
            """
            Connects to any peers that we might know of that aren't already connected.
            
            A state lock should be in place when entering this function
            """
            hold_election = False
            
            for unconnected_peer in self.state.unconnected_nodes:
                self.logger.debug("Connecting to %s" % str(unconnected_peer)) 
                retval = self.network.connect_to_peer(unconnected_peer, self.state.identification)
                if retval is None:
                    self.logger.warn("Transmission failure '%s', dropping. Group is now %s" % \
                        (str(unconnected_peer), self.state.group)) 
                    self.state.group.remove(unconnected_peer)
                    self.state._mark_can_replicate()                    
                    continue

                (link, data) = retval
                unconnected_peer.link = link
                if unconnected_peer.recontact:
                    self.state.must_run_election = True
                    
                
                if data is None:
                    # rebound request - just ignore it.
                    self.logger.debug("Received counter-connect from %s, returning" % str(unconnected_peer.connection))
                    continue
                      
                (me_type, step, score, others, remote_instancetype) = data
                self.logger.info("_connect_to_known_peers data package (me %d/remote %d) %s" % (me_type, remote_instancetype, data))
                if me_type == -1:
                    continue                                     
                
                unconnected_peer.link = link
                
                unconnected_peer.score = score
                unconnected_peer.recontact = False
                
                if me_type == -2:
                    unconnected_peer.instancetype = SPARE
                                    
                # FIXME make it so that spares cannot dictate to us
                if me_type == SPARE:
                    self.state.me.instancetype = SPARE
                elif me_type == REPLICA:
                    self.state.me.instancetype = REPLICA
                    hold_election = True
                else:
                    raise GRSException("Unknown me_type %s in %s when connecting to %s" % (me_type, data, unconnected_peer.connection))
                    
                for other in others:
                    new_peer = Peer(connection = tuple(other), recontact = True)
                    if self.state.find(new_peer.connection) is None:
                        self._add_new_peer(new_peer)
                            
                                                        
        def _run_election(self):
            """
            A global lock should be in place when entering this function
            """
            # TODO Should scores be updated every once in a while
            self.state.election_in_progress = True
            self.logger.info("*** ELECTION PROCESS RUNNING ***")
            try:
                for connected_peer in self.state.active_members:
                    try:
                        (status, step, score) = connected_peer.link.election_begin(self.state.current_step, self.state.score, self.state.conn_info_all)
                        connected_peer.score = score
                    except socket.error:
                        self._handle_dead_peer(connected_peer)
                        continue
                    if status == 'IN_PROGRESS' or status == 'HOLD':
                        # election in progress elsewhere
                        self.logger.info("Attempted to hold election but %s beat us to it." % connected_peer)
                        return
                    elif status == 'I_WIN':
                        self.logger.info("Held election but %s has higher and took over." % connected_peer)
                        self.state.me.instancetype = REPLICA
                        self.state.must_run_election = False
                        return
                    elif status != 'I_LOSE':
                        self.logger.error("Invalid response from election voter %s " % status)
                        self.state.must_run_election = False
                        
                # I win
                self.logger.info("I won the election")
                    
                # make sure all members are connectable still
                self.__broadcast(False, 'ping', self.state.me.connection, None)
                
                all_members = sorted(self.state.active_members)
                all_members.extend(self.state.spares)
                for i in range(len(all_members)):
                    itype = REPLICA if i < self.options.maxcopies-1 else SPARE
                    self.logger.debug("Assigning %s to type %s" % (all_members[i], itype))
                    all_members[i].instancetype = itype
                    
                self.state.me.instancetype = MASTER
                
                group_update = [(peer.connection[0], peer.connection[1], peer.score, peer.instancetype) for peer in self.state.group]
                for i in range(len(all_members)):
                    try:
                        getattr(all_members[i].link, "election_finished")(group_update)
                    except Exception as v:
                        self.logger.error("%s failed to communicate new status to %s (%s)"% (__name__, all_members[i], v))
                        self._handle_dead_peer(all_members[i], False)
                
                self.state.must_run_election = False                  
            except Exception as v:
                self.logger.error("Crash in _run_election. Cause '%s'" % v)
                raise
            finally:
                self.__election_finished()
                
        def __election_finished(self):
            self.state.election_in_progress = False
              # TODO consider not clearing this here, but rather in e_finish and master set. 
            # done, and everybody know their place. Now pick a dispatcher that suits.
            self.dispatcher = self._pick_dispatcher()                                                
            
        def _spare_upgrade(self):
            """
            Master operation - upgrade a spare to full
            TODO: split this operation up so we can transfer partial datasets
            """
            if len(self.state.spares) < 1:
                self.logger.error("%s no spares to upgrade" % (__name__))
            
            spare = self.state.spares[0]
            
            self.logger.info(" ** BEGINNING UPGRADE OF SPARE %s ** " % spare)
            binary_data = self.network.wrapbinary(self.storage.get_full_dataset())
            spare.node_upgrade(self.state.me.connection, binary_data, self.state.group.conn_info_all)
        
        # NETWORK COMMAND AND CONTROL
        def node_register(self, ident):
            """
            Called when a new peer arrives and wants to enter the group
            """
            with(self.storage.getlock(None).writelock):
                try:
                    self.logger.info("Got a hello from a peer with ident %s" % (ident))
                    (server, port, step, score, neverparticipate) = ident
                    if (server, port) in self.state.conn_info_all:
                        self.logger.debug("Preexisting peer said hello %s. Returning." % ident)
                        peer_type = -1
                    elif self.state.instancetype == SPARE:
                        peer_type = -2
                    else:
                        if step < self.state.current_step or neverparticipate or self.state.active_group_size >= self.options.maxcopies:
                            peer_type = SPARE
                        elif step >= self.state.current_step:
                            peer_type = REPLICA
                            if step > self.state.current_step:
                                # FIXME: validate buffer length in write_dispatcher if master and delayed writes
                                pass

                        new_peer = Peer(connection = (server, port), score = score, recontact = False, initial_type = peer_type) # FIXME allow spares
                        self._add_new_peer(new_peer) 
                    
                    # This tells everybody current about peer, which in turn causes peer to know about them.
                    # FIXME stop this, and instead let peer handle it itself
                    #self.__broadcast(False, "network_update_notification", "PEER_UP", (server, port))
                    
                    returnvalue = (peer_type, self.state.current_step, self.state.score, self.state.conn_info_all, self.state.instancetype)    
                    self.logger.debug("Node_register returns %s to %s" % (returnvalue, (server, port)))                
                    return returnvalue                    
                    
                except Exception as v:
                    self.logger.error("Node_register failed for %s: %s" % (ident, v))
                    raise

        def node_unregister(self, peer):
            self.logger.info("Controlled goodbye from a peer %s" % peer)
            for p in self.state.group:
                if p.connection == tuple(peer):
                    p.dead = True
                    
        def node_upgrade(self, master, data, step):
            """
                Sent to spares to upgrade to full copy
            """
            with self.storage.getlock(None).writelock:
                if self.state.instancetype < SPARE:
                    raise GRSException("Received request to upgrade when not a spare")
                
                unwrapped = self.network.unwrapbinary(data)
                self.storage.set_full_dataset(unwrapped)
                self.state.me.instancetype = REPLICA
                self.state.current_step = step
                self.state.checkpoint_id()
                                    
        def network_update_notification(self, cmd, arg):
            """
            Used to receive updates from other network parties. 
            Does NOT ask for an election - that is the job of the originating party.
            """
            self.logger.info("network_update_notification cmd=%s, arg={%s}", cmd, arg)
            if cmd == 'PEER_DOWN':
                arg = tuple(arg)
                if self.state.me.connection == arg:
                    raise GRSException("Internal error: invalid kill attempt from remote peer")
                    
                self._handle_dead_peer(arg, False)
            elif cmd == 'PEER_UP':
                arg = tuple(arg)
                if self.state.me.connection == arg:
                    self.logger.error("PEER_UP received about myself")
                    return
                new_peer = Peer(connection = arg)
                self._add_new_peer(new_peer)
                
            
        def ping(self, whoami, dumb_data_carrier):
            """
            Ping a service. dumb_data_carrier is used solely to test responsiveness at different workloads
            """
            #self.logger.debug("Ping received")
            del dumb_data_carrier
            p = self.state.find(tuple(whoami))    
            if p is None:
                self.logger.warning("%s group of %s heard from %s but this was not found" % (__name__, self.state.group, whoami))
                return 'LOST'
                
            p.last_seen = time.time()    
            return 'OK'
            
        def election_begin(self, remote_current_step, remote_current_score, remote_conn_info_all):
            if self.state.election_in_progress:
                self.logger.debug("Election request received - signaling election in progress")
                return ("IN_PROGRESS", self.state.current_step, self.state.score)
                
            with self.storage.getlock(None).writelock:
                self.logger.debug("%s Comparing my group %s with remote %s. Identical? %s" % (__name__, self.state.conn_info_all, remote_conn_info_all, self.state.compare(remote_conn_info_all)) )
                
                if not self.state.compare(remote_conn_info_all):
                    self.logger.debug("States not identical, asking remote to hold")
                    return ("HOLD", self.state.current_step, self.state.score)
                    
                if remote_current_step < self.state.current_step or \
                    (remote_current_step == self.state.current_step and remote_current_score <= self.state.score):
                    self.logger.debug("Election request received - I won")
                    self.state.must_run_election = True
                    return ("I_WIN", self.state.current_step, self.state.score)
                
                #if remote_current_step > self.state.current_step or remote_current_score > self.state.score:
                self.logger.debug("Election request received - I lost")
                return ('I_LOSE', self.state.current_step, self.state.score)
                
        def election_finished(self, group_update):
            with(self.storage.getlock(None).writelock):
                self.logger.info("Received election finished, group update %s" % (group_update))
                for peer in group_update:
                    #self.logger.debug("election_finished: updating %s !! " % peer)
                    (server, port, score, instancetype) = peer
                    existing = self.state.find((server, port))
                    if existing is None:
                        raise GRSException("Election_finished received. Could not find peer %s in group of %s!" % (peer, self.state.group))
                    existing.score = score
                    existing.instancetype = instancetype
                        
            self.state.must_run_election = False
            self.__election_finished() 
                                            
            
        # EXTERNAL COMMAND AND CONTROL
        def branch(self, subtree_root, destination, message):
            if self.state.instancetype > MASTER:
                return "NOT_MASTER"
            try:
                with(self.storage.getlock(None).writelock):
                    code = self.storage.branch(subtree_root, destination, message)                    
                    if code < 0:
                        return "INTERNAL_ERROR"
            except:
                raise
            
            return "OK"                
                    
        # OPEN FILE HANDLING
        def _oft_get(self, args):
            """
            Retrieve the cached open file proxy. 
            Note: do not acquire oft_lock around this.
            """
            (path, flags, mode) = args
            l = (path, flags, tuple(mode))
            #self.oft_lock.acquire()

            if l not in self.oft: 
                # raises IOError if it fails, otherwise has sideeffect of opening the file
                ret = self.open(path, flags, *tuple(mode))  

            file_fd = self.oft[l]
            self.logger.debug("_oft_get %s - %s" % (l, file_fd))
            #self.oft_lock.release()
            return file_fd
            
        def _oft_add(self, path, flags, mode, retval):
            """Called ONLY by open (adds the opened file information to the cache)"""
            l = (path, flags, tuple(mode))
            #self.oft_lock.acquire()
            self.logger.debug("_oft_added %s - %s - %s" % ((path, flags), self.oft.get(l), retval))
            if l not in self.oft:
                self.oft[l] = retval
            #self.oft_lock.release()
        
        def _oft_release(self, path, flags, mode):
            """Called ONLY by release"""
            l = (path, flags, tuple(mode))
            try:
                self.logger.debug("_oft_release %s - %s" % (l, self.oft[l]))
                del self.oft[l]
            except KeyError:
                pass # legit
            
        # Convinience wrappers
            
        ### DIRECTORY OPS ###
        def readdir(self, path, offset, internal):
            # TODO It might make sense here to cache stat data IF we are operating per remote.                    
            return self.dispatcher.do_read_op(internal, "readdir", path, offset)
            
        ### FILE OPS ###
        # READS            
        def open(self, path, flags, additional_mode = [], internal = { 'local': None }): 
            """
            File open operation

            No creation (O_CREAT, O_EXCL) and by default also no truncation (O_TRUNC) flags will be passed to open(). 
            If an application specifies O_TRUNC, fuse first calls truncate() and then open(). Only if 'atomic_o_trunc'
             has been specified and kernel version is 2.6.24 or later, O_TRUNC is passed on to open.

            Unless the 'default_permissions' mount option is given, open should check if the operation is permitted 
            for the given flags. Optionally open may also return an arbitrary filehandle in the fuse_file_info structure, 
            which will be passed to all file operations.           
            
            NOTE: The internal parameter is disregarded and only included to present a consistent API
            """
            if 'remote' in internal:
                raise GRSException("Open is never called remotely")
            
            accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
            
            if isinstance(additional_mode, int): # HACK
                additional_mode = [additional_mode]

            # The reason why we need to replicate opens is because it can be used to make a file of size 0. (O_CREAT)
            if (flags & accmode) != os.O_RDONLY:    
                self.logger.debug("%s, %s, %s, %s, %s" % (internal, "open", path, flags, list(additional_mode)))
                retval = self.dispatcher.do_write_op(internal, "open", path, flags, list(additional_mode))
            else:
                retval = self.dispatcher.do_read_op(internal, "open", path, flags, list(additional_mode))

            if retval <= 0:
                raise IOError(abs(retval), "Error ROFS", path)
            else:                
                self._oft_add(path, flags, tuple(additional_mode), retval)
                
            return (path, flags, additional_mode)
            
        def read(self, size, offset, internal):
            return self.dispatcher.do_read_op(internal, "read", size, offset)
            
        def fgetattr(self, internal):
            return self.dispatcher.do_read_op(internal, "fgetattr")
            
        def flush(self, internal):
            """
            Possibly flush cached data

            BIG NOTE: This is not equivalent to fsync(). It's not a request to sync dirty data.

            Flush is called on each close() of a file descriptor. So if a filesystem wants to return write 
            errors in close() and the file has cached dirty data, this is a good place to write back data
            and return any errors. Since many applications ignore close() errors this is not always useful.

            NOTE: The flush() method may be called more than once for each open(). 
            This happens if more than one file descriptor refers to an opened file due 
            to dup(), dup2() or fork() calls.
            It is not possible to determine if a flush is final, so each flush should be treated equally.
            Multiple write-flush sequences are relatively rare, so this shouldn't be a problem.

            Filesystems shouldn't assume that flush will always be called after some writes, 
            or that if will be called at all.            
            """
            return self.dispatcher.do_read_op(internal, "flush") 
            
        def release(self, flags, internal):
            """
            Release an open file

            Release is called when there are no more references to an open file: all file descriptors are closed 
            and all memory mappings are unmapped.

            For every open() call there will be exactly one release() call with the same flags and file descriptor. 
            It is possible to have a file opened more than once, in which case only the last release will mean, 
            that no more reads/writes will happen on the file. The return value of release is ignored.
            
            NOTE: the given flag parameter is overwritten by the stored value
            """
            (path, flags, mode) = internal['file_id']
            accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
            if (flags & accmode) != os.O_RDONLY:
                self.dispatcher.do_write_op(internal,  "release", flags)
            else:             
                self.dispatcher.do_read_op(internal, "release", flags)
            self._oft_release(*internal['file_id'])
            
        
        def lock(self, cmd, owner, additional_args = {}, internal = {}):
            pass
            
        # WRITES
        def write(self, buf, offset, internal):
            return self.dispatcher.do_write_op(internal, "write", buf, offset)

        def fsync(self, isfsyncfile, internal):
            return self.dispatcher.force_sync() # TODO: can limit the bufferflush by using the file reference
            
        def ftruncate(self, length, internal):
            return self.dispatcher.do_write_op(internal, "ftruncate", length)
            

        #### NON FILE/DIRECTORY-SPECIFIC OPERATIONS ####
         ## Reads
        def getattr(self, path, internal):
            return self.dispatcher.do_read_op(internal, "getattr", path)

        def readlink(self, path, internal):
            return self.dispatcher.do_read_op(internal, "readlink", path)

        def access(self, path, mode, internal):
            return self.dispatcher.do_read_op(internal, "access", path, mode)            
            
         ## Writes
        def unlink(self, path, internal):
            return self.dispatcher.do_write_op(internal, "unlink", path)

        def symlink(self, path, path2, internal):
            return self.dispatcher.do_write_op(internal, "symlink", path, path2)

        def rename(self, path, path2, internal):
            return self.dispatcher.do_write_op(internal, "rename", path, path2)

        def link(self, path, path2, internal):
            return self.dispatcher.do_write_op(internal, "link", path, path2)

        def chmod(self, path, mode, internal):
            return self.dispatcher.do_write_op(internal, "chmod", path, mode)

        def chown(self, path, user, group, internal):
            return self.dispatcher.do_write_op(internal, "chown", path, user, group)

        def truncate(self, path, length, internal):
            return self.dispatcher.do_write_op(internal, "truncate", path, length)

        def mknod(self, path, mode, dev, internal):
            return self.dispatcher.do_write_op(internal, "mknod", path, mode, dev)
            
            
        def mkdir(self, path, mode, internal):
            return self.dispatcher.do_write_op(internal, "mkdir", path, mode)

        def rmdir(self, path, internal):
            return self.dispatcher.do_write_op(internal, "rmdir", path)

        def utime(self, path, times, internal):
            return self.dispatcher.do_write_op(internal, "utime", path, times)
            

        #  The Python stdlib doesn't know of subsecond preciseness in acces/modify times.
        def utimens(self, internal, path, ts_acc, ts_mod):            
            self.dispatcher.do_write_op(internal, "utime", path, ts_acc, ts_mod)


        def statfs(self):
            """
            Should return an object with statvfs attributes (f_bsize, f_frsize...).
            Eg., the return value of os.statvfs() is such a thing (since py 2.2).
            If you are not reusing an existing statvfs object, start with
            fuse.StatVFS(), and define the attributes.

            To provide usable information (ie., you want sensible df(1)
            output, you are suggested to specify the following attributes:

                - f_bsize - preferred size of file blocks, in bytes
                - f_frsize - fundamental size of file blcoks, in bytes
                  [if you have no idea, use the same as blocksize]
                - f_blocks - total number of blocks in the filesystem
                - f_bfree - number of free blocks
                - f_files - total number of file inodes
                - f_ffree - nunber of free file inodes
            """
            return os.statvfs(self.options.backingstore)

    # storage for the instance reference
    __instance = None

    def __init__(self, options = None):
        """ Create singleton instance """
        # Check whether we already have an instance
        if Kernel.__instance is None:
            # Create and remember instance
            Kernel.__instance = Kernel.__kernel(options)
            
        # Store instance reference as the only member in the handle
        self.__dict__['_Kernel__instance'] = Kernel.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)



