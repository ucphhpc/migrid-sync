#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# Plumber - Tunnels traffic between two sockets
#
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

import logging
import os
import select
import sys
import threading
import time

try:
    import OpenSSL
except ImportError:
    print 'WARNING: the python OpenSSL module is required for vm-proxy'
    OpenSSL = None


class Plumber:
    """Plumber, select only plumber
  
    A primitive for tunneling traffic between two sockets. If sockets where called
    pipes then you get why I named it 'Plumber'.
    
    - The sockets are changed to non-blocking mode upon Plumber Construction
    - The sockets sockets must be connected when instanciating the Plumber
    - Pipe is a blocking call, it is freed when the sockets are closed
    - When the first read error occurs both sockets are closed.
    
    TODO: - optimize the handling of SSL WantWriteError / WantReadError
    """

    def __init__(
        self,
        source,
        sink,
        buffer_size=1024,
        detach=False,
        ):

        self.running = True

        self.buffer_size = buffer_size

        self.source = source
        self.sink = sink

        self.source.setblocking(0)
        self.sink.setblocking(0)

        self.source_name = self.source.getpeername()
        self.source_fn = self.source.fileno()

        self.sink_name = self.sink.getpeername()
        self.sink_fn = self.sink.fileno()

        logging.debug('%s <--> %s', self.source_name, self.sink_name)
        logging.debug('[Source=%s %d,%s,\n  Sink=%s %d,%s]' % (
            self.source,
            self.source_fn,
            self.source_name,
            self.sink,
            self.sink_fn,
            self.sink_name,
            ))

        if detach:
            self.sink_thread = threading.Thread(target=self.pipe)
            self.sink_thread.setDaemon(False)
            self.sink_thread.start()
        else:
            self.pipe()

    def pipe(self):

        readable = []  # This list will the contain the sockets with data
        writable = []  # Writable sockets, must be check for throttling
        errors = []  # Unused, should be used for error checking

        while self.running:

            try:
                (readable, writable, errors) = \
                    select.select([self.source, self.sink], [], [])

                if len(readable) > 0:
                    for input_socket in readable:

                        if input_socket.fileno() == self.sink_fn:

                            (r, w, e) = select.select([],
                                    [self.source], [])
                            if len(w) > 0:
                                data = \
                                    input_socket.recv(self.buffer_size)
                                self.source.send(data)
                        else:

                            (r, w, e) = select.select([], [self.sink],
                                    [])
                            if len(w) > 0:
                                data = \
                                    input_socket.recv(self.buffer_size)
                                self.sink.send(data)
            except OpenSSL.SSL.WantWriteError:

        # logging.exception('%s PLUMBER: Unexpected error: %s' % (self, sys.exc_info()[2]))

                pass
            except OpenSSL.SSL.WantReadError:

        # logging.exception('%s PLUMBER: Unexpected error: %s' % (self, sys.exc_info()[2]))

                pass
            except:
                logging.debug('%s %s %s: read failure, probable disconnect.'
                               % (self, self.source_name,
                              self.sink_name))
                logging.exception('PLUMBER: Unexpected error: %s'
                                  % sys.exc_info()[2])
                self.running = 0

        self.source.close()
        self.sink.close()

        logging.debug('%s: closed sockets (%d,%d).' % (self,
                      self.source_fn, self.sink_fn))


class PlumberTS:
    """PlumberTS, threading and select
    
    A primitive for tunneling traffic between two sockets. If sockets where called
    pipes then you get why I named it 'Plumber'.
    
    - The sockets are changed to BLOCKING mode upon Plumber Construction
    - The sockets sockets must be connected when instanciating the Plumber
    - When the first read error occurs both sockets are closed.  
    """

    def __init__(
        self,
        source,
        sink,
        buffer_size=1024,
        detach=False,
        ):

        self.buffer_size = buffer_size
        logging.debug('%s <--> %s', source.getpeername(),
                      sink.getpeername())

        source.setblocking(1)
        sink.setblocking(1)

        self.running = True
        self.proxyLock = threading.Lock()

        self.source_thread = threading.Thread(target=self.pipe,
                args=(source, sink))
        self.source_thread.setDaemon(False)
        self.source_thread.start()

        if detach:
            self.sink_thread = threading.Thread(target=self.pipe,
                    args=(sink, source))
            self.sink_thread.setDaemon(False)
            self.sink_thread.start()
        else:
            self.pipe(sink, source)

    def pipe(self, source, sink):

        source_name = source.getpeername()
        sink_name = sink.getpeername()

        while self.running:

            try:
                (r, w, e) = select.select([source], [], [])

                if len(r) > 0:

                    (rr, ww, ee) = select.select([], [sink], [])
                    if len(ww) > 0:

                        self.proxyLock.acquire()
                        data = source.recv(self.buffer_size)

                        if not data:
                            self.running = False
                            self.proxyLock.release()
                            break

                        sink.send(data)
                        self.proxyLock.release()
            except:

                logging.debug('%s %s : read PWN3D!' % (self,
                              source_name))
                self.running = False
                break

        logging.debug('%s %s : closing socket.' % (self, source_name))
        source.close()
        sink.close()


class PlumberTO:
    """PlumberTO, threading
  
    A primitive for tunneling traffic between two sockets. If sockets where called
    pipes then you get why I named it 'Plumber'.
    
    - The sockets are changed to BLOCKING mode upon Plumber Construction
    - The sockets sockets must be connected when instanciating the Plumber
    - When the first read error occurs both sockets are closed.
    
    WARN: Only use this plumber with threadsafe sockets!
    """

    def __init__(
        self,
        source,
        sink,
        buffer_size=1024,
        detach=False,
        ):

        self.buffer_size = buffer_size
        logging.debug('%s <--> %s', source.getpeername(),
                      sink.getpeername())

        self.running = True
        source.setblocking(1)
        sink.setblocking(1)

        self.source_thread = threading.Thread(target=self.pipe,
                args=(source, sink))
        self.source_thread.setDaemon(False)
        self.source_thread.start()

        if detach:
            self.sink_thread = threading.Thread(target=self.pipe,
                    args=(sink, source))
            self.sink_thread.setDaemon(False)
            self.sink_thread.start()
        else:
            self.pipe(sink, source)

    def pipe(self, source, sink):

        source_name = source.getpeername()
        sink_name = sink.getpeername()

        while self.running:

            try:

                data = source.recv(self.buffer_size)
                if not data:
                    self.running = False
                    break
                sink.send(data)
            except:

                logging.debug('%s %s : read PWN3D!' % (self,
                              source_name))
                self.running = False
                break

        logging.debug('%s %s : closing socket.' % (self, source_name))
        source.close()
        sink.close()
