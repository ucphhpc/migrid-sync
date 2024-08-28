#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

"""Configuration related details within the test support library."""

from threading import Thread, Event as ThreadEvent


class ServerWithinThreadExecutor:
    """Execute a server within a thread ensuring we are able to
    block until it is ready to recieve test requests.

    The only requirements on being able to do so are the server
    supporting an on_start callback which is to be called when
    the server is ready to handle requests."""

    def __init__(self, ServerClass, *args, **kwargs):
        self._serverclass = ServerClass
        self._arguments = (args, kwargs)
        self._started = ThreadEvent()
        self._thread = None
        self._wrapped = None

    def run(self):
        server_args, server_kwargs = self._arguments

        server_kwargs['on_start'] = lambda _: self._started.set()

        self._wrapped = self._serverclass(*server_args, **server_kwargs)

        try:
            self._wrapped.serve_forever()
        except Exception as e:
            pass

    def start(self):
        self._thread = Thread(target=self.run)
        self._thread.start()

    def start_wait_until_ready(self):
        self.start()
        self._started.wait()
        return self

    def stop(self):
        self.stop_server()
        self._wrapped = None
        self._thread.join()
        self._thread = None

    def stop_server(self):
        self._wrapped.shutdown()
        self._wrapped.server_close()


def make_wrapped_server(ServerClass, *args, **kwargs):
    return ServerWithinThreadExecutor(ServerClass, *args, **kwargs)
