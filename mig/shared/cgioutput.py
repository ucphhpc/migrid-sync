#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cgioutput - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

"""Class to handle CGI output.

It gathers all output and a status before outputting anything
in order to allow a consistent format:
STATUSCODE
CONTENT
"""
from __future__ import print_function

from builtins import object
import sys


class CGIOutput(object):

    """Handle CGI output"""

    logger = None
    output = None

    # In Python, a constant is nothing more than a variable whose
    # value is not changed by the program.

    OK = 0
    CLIENT_ERROR = 1
    ERROR = 2

    def __init__(self, logger):
        self.output = []
        self.logger = logger

    def client(self, client):
        """Write output only relevant for client"""

        new_tuple = (client, '')
        self.output.append(new_tuple)

    def client_html(self, client, html=True):
        """Write html output only relevant for client"""

        if html:
            new_tuple = (client, '')
            self.output.append(new_tuple)

    def out(self, client, internal=''):
        """Write a message to client and log and possibly an extra
        internal message to the log"""

        if internal == '':
            new_tuple = (client, client)
        else:
            new_tuple = (client, '%s internal: %s|' % (client,
                         internal))
        self.output.append(new_tuple)

    def internal(self, internal):
        """Write an internal message (sensitive data)"""

        new_tuple = ('', internal)
        self.output.append(new_tuple)

    def reply_and_exit(self, status, append_newline=True):
        """Write client output to client and client and internal
        output to log file. Then exit script with exit code.
        """

        client_msg_string = ''
        internal_msg_string = ''

        for (client, internal) in self.output:
            if client:
                client_msg_string += '%s' % client
                if append_newline:
                    client_msg_string += '\n'
            else:
                client_msg_string += ''
            if internal:
                internal_msg_string += '%s ' % internal

        # use sys.stdout.write() for printing string to avoid extra
        # newline

        if status == self.OK:
            print('0')
            sys.stdout.write(client_msg_string)
            self.logger.info("%s .Replied 'OK'" % internal_msg_string)
            sys.exit(0)
        elif status == self.CLIENT_ERROR:

            # log with info level

            print('1')
            sys.stdout.write(client_msg_string)
            self.logger.info("%s .Replied 'ERROR'"
                              % internal_msg_string)
            sys.exit(1)
        elif status == self.ERROR:

            # log with error level

            print('1')
            sys.stdout.write(client_msg_string)
            self.logger.error("CGI error: %s .Replied 'ERROR'"
                               % internal_msg_string)
            sys.exit(1)


