#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# distfile - [insert a few words of module description on this line]
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

# Script version (automagically updated by cvs)

"""This module contains various wrapper functions for distributed
server IO. In that way the underlying distribution of server
files can be separated from the normal server operation.
"""

__version__ = '$Revision: 2084 $'
__revision__ = __version__

# $Id: distfile.py 2084 2007-09-11 08:39:37Z jones $

from stat import ST_SIZE as _ST_SIZE
from os.path import normpath as _normpath

try:
    from os import devnull as _devnull
except ImportError:

    # probably python < 2.4 without os.devnull

    _devnull = '/dev/null'

import shared.distbase as distbase
from shared.distbase import HTTPS_SID_PORT, HTTPS_CERT_PORT, BASE_ID, \
    BASE_HOME, HTTP_OK
from shared.serverfile import ServerFile, LOCK_UN, LOCK_SH, LOCK_EX, \
    LockingException

# Provide user agent string for use in distfile recursion check

USER_AGENT = distbase.USER_AGENT


def _line_read(data, size=-1):
    """Return the longest possible line from the beginning of the
    string, data, such that line is not longer that size chars and
    does not contain any newlines before the last character."""

    line_data = data
    if size >= 0:
        line_data = data[:size]
    index = line_data.find('\n')
    if -1 == index:
        index = len(line_data)
    return line_data[:index + 1]


# ####################
# Public file class #
# ####################


class DistFile(ServerFile):

    """File object wrapper to provide the usual file interface with
    distributed files underneath. This class inherits the interface
    from the general ServerFile interface class and adds remote calls.
    """

    fd_str = "<%s remote file '%s', mode %s at %s >"

    def __init__(
        self,
        path,
        mode='r',
        bufsize=-1,
        ):
        """Setup DistFile object"""

        # Make sure we don't run into trouble if server doesn't recognize
    # that /test//file/ is equivalent to /test/file

        path = _normpath(path)

        # Some of the file attributes inherited from file are
        # read-only (mode, closed, ...) so we must call parent
        # constructor to set them. However, we don't want to
        # create actual local file so we use a dummy.

        ServerFile.__init__(self, _devnull, mode, bufsize)

        self.providers = []

        # semi random session id for now - we should use cert access
        # instead!

        self.session_id = BASE_ID
        self.session_home = BASE_HOME
        self.session_type = None
        self.path = path
        self.bufsize = bufsize
        self.offset = 0
        self.locking = LOCK_UN

        (status, data) = self.__open_remote_file(path, mode)
        if status == 0:
            self.providers = data.split()
        else:

            # TODO: Dist FS always sets exclusive access on open for
            # now

            raise IOError('Distfile: init failed with error %s: %s'
                           % (status, data))
        if mode.startswith('w'):

            # Mimic standard python behaviour of truncating files
            # opened in write mode. Use "r+" to avoid truncating!

            self.__truncate_remote_file(self.providers, path, 0)

    # Private helper methods #

    def __read_allowed(self):
        """Check if this file is opened in a mode which allows
        read access.
        """

        return 'r' in self.mode or '+' in self.mode

    def __write_allowed(self):
        """Check if this file is opened in a mode which allows
        write access.
        """

        return 'w' in self.mode or '+' in self.mode

    def __open_remote_file(
        self,
        path,
        mode='r',
        buf=-1,
        ):
        """Request the current leader to open the active session for
        file with supplied path.
        """

        if -1 != buf:
            raise IOError('buffered reads are not supported!')

        # TODO: eliminate need for CREATE in storage code - WRITE
        # should be enough!

        if mode.startswith('w'):
            self.session_type = 'CREATE'
            distbase.open_session(path, self.session_type)
            distbase.close_session(path, self.session_type)
            self.session_type = 'WRITE'
        else:

            # TODO: handle other modes like 'a', "r+"?

            self.session_type = 'READ'

        return distbase.open_session(path, self.session_type)

    def __close_remote_file(self, path):
        """Tell the current leader to close the active session for
        file with supplied path.
        """

        return distbase.close_session(path, self.session_type)

    def __read_remote_file(
        self,
        providers,
        path,
        offset,
        bytes,
        ):
        """Read bytes from position, offset, in file with specified
        path. Try each of the providers in turn if remote read fails.
        """

        for server in providers:
            (status, data) = distbase.get_range(server,
                    HTTPS_CERT_PORT, '/%s/%s' % (self.session_home,
                    path), offset, bytes)
            if status in HTTP_OK:
                return data

        raise IOError('Error: no providers could deliver the data: %s'
                       % data)

    def __write_remote_file(
        self,
        providers,
        path,
        offset,
        bytes,
        data,
        ):
        """Write the supplied contents to all replicas of the remote
        file. This is done by forwarding the write to all replicas
        if called from the main server. When the secondary providers
        receive the write request they should only update the local
        file, not forward it again.
        """

        status_list = []
        data_list = []
        for server in providers:
            (status, reply) = distbase.put_range(
                server,
                HTTPS_CERT_PORT,
                '/%s/%s' % (self.session_home, path),
                offset,
                bytes,
                data,
                )
            status_list.append(status)
            data_list.append(reply)

        for http_status in status_list:
            if not http_status in HTTP_OK:
                raise IOError('Error: provider(s) could not update the data'
                              )

    def __truncate_remote_file(
        self,
        providers,
        path,
        size,
        ):
        """Truncate all replicas of path to the supplied size. This is
        done by forwarding the write to all replicas if called from
        the main server. When the secondary providers receive the
        write request they should only update the local file, not
        forward it again.
        """

        status_list = []
        data_list = []
        contents = ''
        if size > 0:
            contents = self.__read_remote_file(providers, path, 0, size)
        for server in providers:
            (status, data) = distbase.http_put(server, HTTPS_CERT_PORT,
                    '/%s/%s' % (self.session_home, path), contents)
            status_list.append(status)
            data_list.append(data)

        for http_status in status_list:
            if not http_status in HTTP_OK:
                raise IOError('Error: provider(s) could not truncate the file'
                              )

    def __stat_remote_file(self, providers, path):
        """Get stat data for provided path by asking providers in
        turn"""

        for server in providers:
            (status, data) = distbase.http_stat(server,
                    HTTPS_CERT_PORT, '/%s' % path, '')

            # stat returns MiG code rather than HTTP code: 0 means OK

            if not status:
                return data

        raise IOError('Error: no providers could deliver the data: %s'
                       % data)

    # Public interface methods #

    def close(self):
        """Emulate local method of same name"""

        if self.locking != LOCK_UN:
            self.unlock()
        self.__close_remote_file(self.path)

        # Again we need parent method to manipulate read-only attributes

        ServerFile.close(self)

    def flush(self):
        """Emulate local method of same name"""

        if self.closed:
            raise ValueError('I/O operation on closed file')

        # Always in sync

        return

    def seek(self, offset, whence=0):
        """Emulate local method of same name"""

        if self.closed:
            raise ValueError('I/O operation on closed file')
        if 0 == whence:

            # absolute offset from beginning

            self.offset = offset
        elif 1 == whence:

            # offset relative to current position

            self.offset += offset
        elif 2 == whence:

            # absolute offset from end

            data = self.__stat_remote_file(self.providers, self.path)
            stat_data = eval('%s' % data)
            self.offset = stat_data[_ST_SIZE] + offset
        else:
            raise IOError('Invalid whence argument: %s!' % whence)

    def tell(self):
        """Emulate local method of same name"""

        if self.closed:
            raise ValueError('I/O operation on closed file')
        return self.offset

    def read(self, bytes=-1):
        """Emulate local method of same name"""

        if self.closed:
            raise ValueError('I/O operation on closed file')
        if not self.__read_allowed():
            raise IOError('Illegal read: path %s, mode %s !'
                           % (self.path, self.mode))

        data = self.__read_remote_file(self.providers, self.path,
                self.offset, bytes)
        self.offset += len(data)
        return data

    def readline(self, size=-1):
        """Emulate local method of same name"""

        old_offset = self.offset
        data = self.read(size)
        line = _line_read(data, size)
        self.offset = old_offset + len(line)
        return line

    def readlines(self, size=-1):
        """Emulate local method of same name"""

        lines = []
        old_offset = self.offset
        data = self.read(-1)
        self.offset = old_offset
        data_len = len(data)
        while self.offset < data_len:
            line = _line_read(data[self.offset:], size)
            self.offset += len(line)
            lines.append(line)
        return lines

    def truncate(self, size=-1):
        """Truncate file to specified size or current postion"""

        if self.closed:
            raise ValueError('I/O operation on closed file')
        if not self.__write_allowed():
            raise IOError('Illegal truncate: path %s, mode %s !'
                           % (self.path, self.mode))
        if size == -1:
            size = self.offset
        self.__truncate_remote_file(self.providers, self.path, size)

    def write(self, data):
        """Emulate local method of same name"""

        # TODO: we might save a bit by caching writes
        # Exclusive write locks prevent concurrent access anyway, so could just
        # cache written data in self and only flush on explicit flush or close.

        if self.closed:
            raise ValueError('I/O operation on closed file')
        if not self.__write_allowed():
            raise IOError('Illegal write: path %s, mode %s !'
                           % (self.path, self.mode))
        self.__write_remote_file(self.providers, self.path,
                                 self.offset, len(data), data)
        self.offset += len(data)

    def writelines(self, lines):
        """Emulate local method of same name"""

        self.write(''.join(lines))

    def lock(self, mode):
        """Additional method to integrate file locking with file
        object. Allowed modes are the constants listed at the
        beginning of this file.
        """

        if mode not in [LOCK_UN, LOCK_SH, LOCK_EX]:
            raise LockingException('Locking error: unknown mode: %s')
        if self.locking != LOCK_UN and mode != LOCK_UN:
            raise LockingException('Locking rejected: already locked')
        self.locking = mode

    def unlock(self):
        """Unlock file by calling lock with unlock flag"""

        self.lock(LOCK_UN)

    def get_lock_mode(self):
        """Test the current lock mode for the file"""

        return self.locking

    def __iter__(self):
        for line in self.readlines():
            yield line
        return

    def __str__(self):
        """How to represent this file object as a string"""

        state = 'open'
        if self.closed:
            state = 'closed'
        return self.fd_str % (state, self.path, self.mode,
                              self.providers)


