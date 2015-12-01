#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_sftp - SFTP server providing access to MiG user homes
# Copyright (C) 2010-2015  The MiG Project lead by Brian Vinter
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

#
# This code is a heavily modified version of the sftp server from
# http://achievewith.us/hg/simple_sftp_server
#
# = Original copyright notice follows =

# This is the MIT license:
# http://www.opensource.org/licenses/mit-license.php

# Copyright (c) 2009 Digital Achievement Incorporated and contributors.

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# = End of original copyright notice =

"""Provides SFTP access to MiG user homes

Requires Paramiko module (http://pypi.python.org/pypi/paramiko).
"""

import logging
import os
import socket
import shutil
import sys
import threading
import time
from StringIO import StringIO

try:
    import paramiko
    import paramiko.util
    from paramiko.common import DEFAULT_WINDOW_SIZE, DEFAULT_MAX_PACKET_SIZE
except ImportError:
    print "ERROR: the python paramiko module is required for this daemon"
    sys.exit(1)

from shared.base import invisible_path, force_utf8
from shared.conf import get_configuration_object
from shared.griddaemons import get_fs_path, strip_root, flags_to_mode, \
     acceptable_chmod, refresh_users, refresh_jobs, hit_rate_limit, \
     update_rate_limit, expire_rate_limit, penalize_rate_limit
from shared.logger import daemon_logger
from shared.useradm import check_password_hash

configuration, logger = None, None


class SFTPHandle(paramiko.SFTPHandle):
    """Override default SFTPHandle"""
    def __init__(self, flags=0, sftpserver=None):
        paramiko.SFTPHandle.__init__(self, flags)
        self.sftpserver = None
        if sftpserver is not None:
            self.sftpserver = sftpserver
            self.logger = sftpserver.conf.get("logger", logging.getLogger())
            self.logger.debug("SFTPHandle init: %s" % repr(flags))

    def stat(self):
        """Handle operations of same name"""
        self.logger.debug("SFTPHandle stat on %s" % getattr(self, "path",
                                                            "unknown"))
        active = getattr(self, 'active')
        file_obj = getattr(self, active)
        return paramiko.SFTPAttributes.from_stat(os.fstat(file_obj.fileno()),
                                                 getattr(self, "path",
                                                         "unknown"))

    def chattr(self, attr):
        """Handle operations of same name"""
        path = getattr(self, "path", "unknown")
        self.logger.debug("SFTPHandle chattr %s on path %s" % \
                          (repr(attr), path))
        return self.sftpserver._chattr(path, attr, self)
        

class SimpleSftpServer(paramiko.SFTPServerInterface):
    """Custom SFTP server with chroot and MiG access restrictions.

    Includes basic error handling and robustness, but could be extended to
    deliver more precise error codes on common errors.

    IMPORTANT: Instances of this class generally live in background threads.
    This means that any unhandled exceptions will silently pass. Thus it is
    very important to conservatively catch and log all potential exceptions
    when debugging to avoid excessive loss of hair :-) 
    """
    def __init__(self, server, transport, fs_root, users, *largs,
                 **kwargs):
        conf = kwargs.get('conf', {})
        self.conf = conf
        self.logger = conf.get("logger", logging.getLogger())
        self.transport = transport
        self.root = fs_root
        self.chmod_exceptions = conf.get('chmod_exceptions', [])
        self.chroot_exceptions = conf.get('chroot_exceptions', [])
        self.user_name = self.transport.get_username()
        self.users = users

        # list of User login objects for user_name
        
        entries = self.users[self.user_name]
        for entry in entries:
            if entry.chroot:
                self.root = "%s/%s" % (self.root, entry.home)
                break

    # Use shared daemon fs helper functions
    
    def _get_fs_path(self, sftp_path):
        """Wrap helper"""
        #self.logger.debug("get_fs_path: %s" % sftp_path)
        reply = get_fs_path(sftp_path, self.root, self.chroot_exceptions)
        #self.logger.debug("get_fs_path returns: %s :: %s" % (sftp_path,
        #                                                     reply))
        return reply

    def _strip_root(self, sftp_path):
        """Wrap helper"""
        #self.logger.debug("strip_root: %s" % sftp_path)
        reply = strip_root(sftp_path, self.root, self.chroot_exceptions)
        #self.logger.debug("strip_root returns: %s :: %s" % (sftp_path,
        #                                                     reply))
        return reply
    
    def _acceptable_chmod(self, sftp_path, mode):
        """Wrap helper"""
        #self.logger.debug("acceptable_chmod: %s" % sftp_path)
        reply = acceptable_chmod(sftp_path, mode, self.chmod_exceptions)
        if not reply:
            self.logger.warning("acceptable_chmod failed: %s %s %s" % \
                                (sftp_path, mode, self.chmod_exceptions))
        #self.logger.debug("acceptable_chmod returns: %s :: %s" % \
        #                      (sftp_path, reply))
        return reply

    def _chattr(self, path, attr, sftphandle=None):
        """Handle chattr for SimpleSftpServer and SFTPHandle"""
        file_obj = None
        path = force_utf8(path)
        self.logger.debug("_chattr %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('chattr %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("chattr on missing path %s :: %s" % (path,
                                                                   real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        if sftphandle is not None:
            active = getattr(sftphandle, 'active')
            file_obj = getattr(sftphandle, active)            
        # Prevent users from messing with most attributes as such.
        # We end here on chmod too, so pass any mode change requests there and
        # silently ignore them otherwise. It turns out to have caused problems
        # if we rejected those other attribute changes in the past but it may
        # not be a problem anymore. If it ain't broken...
        self.logger.info("chattr %s for path %s :: %s" % \
                                (repr(attr), path, real_path))
        ignored = True
        if getattr(attr, 'st_mode', None) is not None and attr.st_mode > 0:
            self.logger.debug('_chattr st_mode: %s' % attr.st_mode)
            ignored = False
            self.logger.info("chattr %s forwarding for path %s :: %s" % \
                                (repr(attr), path, real_path))
            return self._chmod(path, attr.st_mode, sftphandle)
        if getattr(attr, 'st_atime', None) is not None or \
                 getattr(attr, 'st_mtime', None) is not None:
            ignored = False
            change_atime = getattr(attr, 'st_atime',
                                   os.path.getatime(real_path))
            change_mtime = getattr(attr, 'st_mtime',
                                   os.path.getmtime(real_path))
            self.logger.debug('_chattr st_atime: %s, st_mtime: %s' % \
                                (change_atime, change_mtime))
            os.utime(real_path, (change_atime, change_mtime))
            self.logger.info("changed times %s %s for path %s :: %s" % \
                                (change_atime, change_mtime, path, real_path))
        if getattr(attr, 'st_size', None) is not None:
            self.logger.debug('_chattr st_size: %s' % str(attr.st_size))
            ignored = False
            if file_obj is None:
                # TODO: there is no such os.truncate function! (never used?)
                os.truncate(real_path, attr.st_size)
                self.logger.info("truncated file: %s to size: %s" % \
                                (real_path, attr.st_size))
            else:
                os.ftruncate(file_obj.fileno(), attr.st_size)
                self.logger.info("truncated file: %s to size: %s" % \
                                (file_obj.name, attr.st_size))
        if ignored:
            self.logger.warning("chattr %s ignored on path %s :: %s" % \
                                (repr(attr), path, real_path))
        return paramiko.SFTP_OK

    def _chmod(self, path, mode, sftphandle=None):
        """Handle chmod for SimpleSftpServer and SFTPHandle"""
        file_obj = None
        path = force_utf8(path)
        self.logger.debug("_chmod %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('chmod %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("chmod on missing path %s :: %s" % (path,
                                                                  real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        if sftphandle is not None:
            active = getattr(sftphandle, 'active')
            file_obj = getattr(sftphandle, active)     
        # Only allow change of mode on files and only outside chmod_exceptions
        if self._acceptable_chmod(real_path, mode):
            # Only allow permission changes that won't give excessive access
            # or remove own access.
            if os.path.isdir(path):
                new_mode = (mode & 0775) | 0750
            else:
                new_mode = (mode & 0775) | 0640
            self.logger.info("chmod %s (%s) without damage on %s :: %s" % \
                                (new_mode, mode, path, real_path))
            try:
                if file_obj is None:
                    os.chmod(real_path, new_mode)
                else:
                    os.fchmod(file_obj.fileno(), new_mode)
            except Exception, err:
                self.logger.error("chmod %s (%s) failed on path %s :: %s %s" % \
                                  (new_mode, mode, path, real_path, err))
                return paramiko.SFTP_PERMISSION_DENIED
            return paramiko.SFTP_OK
        # Prevent users from messing up access modes
        self.logger.error("chmod %s rejected on path %s :: %s" % (mode, path,
                                                                  real_path))
        return paramiko.SFTP_OP_UNSUPPORTED

    # Public interface functions

    def open(self, path, flags, attr):
        """Handle operations of same name"""        
        path = force_utf8(path)
        self.logger.debug('open %s' % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('open %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("open on %s :: %s (%s %s)" % \
                          (path, real_path, repr(flags), repr(attr)))
        if not (flags & os.O_CREAT) and not os.path.exists(real_path):
            self.logger.error("open existing file on missing path %s :: %s" % \
                              (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        handle = SFTPHandle(flags, sftpserver=self)
        setattr(handle, 'real_path', real_path)
        setattr(handle, 'path', path)
        try:
            # Fake OS level open call first to avoid most flag parsing.
            # This is necessary to make things like O_CREAT, O_EXCL and
            # O_TRUNCATE consistent with the simple mode strings.
            fake = os.open(real_path, flags, 0644)
            os.close(fake)
            # Now fake our own chattr to set any requested mode and times
            self.logger.debug("fake chattr on %s :: %s (%s %s)" % \
                              (path, real_path, repr(flags), repr(attr)))
            self.chattr(path, attr)
            self.logger.debug("chattr done on %s :: %s (%s %s)" % \
                              (path, real_path, repr(flags), repr(attr)))
            mode = flags_to_mode(flags)
            if flags == os.O_RDONLY:
                # Read-only mode
                readfile = open(real_path, mode)
                writefile = None
                active = 'readfile'
            elif flags == os.O_WRONLY:
                # Write-only mode
                readfile = None
                writefile = open(real_path, mode)
                active = 'writefile'
            else:
                # All other modes are handled as read+write
                readfile = writefile = open(real_path, mode)
                active = 'writefile'
            setattr(handle, 'readfile', readfile)
            setattr(handle, 'writefile', writefile)
            setattr(handle, 'active', active)
            self.logger.debug("open done %s :: %s (%s %s)" % \
                              (path, real_path, str(handle), mode))
            return handle
        except Exception, err:
            self.logger.error("open on %s :: %s (%s) failed: %s" % \
                              (path, real_path, mode, err))
            return paramiko.SFTP_FAILURE          

    def list_folder(self, path):
        """Handle operations of same name"""
        path = force_utf8(path)
        self.logger.debug('list_folder %s' % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('list_folder %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("list_folder %s :: %s" % (path, real_path))
        reply = []
        if not os.path.exists(real_path):
            self.logger.error("list_folder on missing path %s :: %s" % \
                              (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            files = os.listdir(real_path)
        except Exception, err:
            self.logger.error("list_folder on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE          
        for filename in files:
            if invisible_path(filename):
                continue
            full_name = ("%s/%s" % (real_path, filename)).replace("//", "/")
            # stat may fail e.g. if filename is a stale storage mount point
            try:
                reply.append(paramiko.SFTPAttributes.from_stat(
                    os.stat(full_name), self._strip_root(filename)))
            except Exception, err:
                self.logger.warning("list_folder %s: stat on %s failed: %s" % \
                                    (path, full_name, err))
        self.logger.debug("list_folder %s reply %s" % (path, reply))
        return reply

    def stat(self, path):
        """Handle operations of same name"""
        path = force_utf8(path)
        self.logger.debug('stat %s' % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('stat %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("stat %s :: %s" % (path, real_path))
        # for consistency with lstat
        if not os.path.exists(real_path):
            self.logger.warning("stat on missing path %s :: %s" % \
                                (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)
        except Exception, err:
            self.logger.error("stat on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE            

    def lstat(self, path):
        """Handle operations of same name"""
        path = force_utf8(path)
        self.logger.debug('lstat %s' % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('lstat %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("lstat %s :: %s" % (path, real_path))

        if not os.path.lexists(real_path):
            self.logger.warning("lstat on missing path %s :: %s" % \
                                (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        self.logger.debug('return lstat %s' % path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)
        except Exception, err:
            self.logger.error("lstat on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE            

    def remove(self, path):
        """Handle operations of same name"""
        path = force_utf8(path)
        self.logger.debug("remove %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('remove %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("remove %s :: %s" % (path, real_path))
        # Prevent removal of special files - link to vgrid dirs, etc.
        if os.path.islink(real_path):
            self.logger.error("remove rejected on link path %s :: %s" % \
                            (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("remove on missing path %s :: %s" % (path,
                                                                   real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            os.remove(real_path)
            return paramiko.SFTP_OK
        except Exception, err:
            self.logger.error("remove on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE            

    def rename(self, oldpath, newpath):
        """Handle operations of same name"""
        oldpath = force_utf8(oldpath)
        newpath = force_utf8(newpath)
        self.logger.debug("rename %s %s" % (oldpath, newpath))
        try:
            real_oldpath = self._get_fs_path(oldpath)
        except ValueError, err:
            self.logger.warning('rename %s %s: %s' % (oldpath, newpath, err))
            return paramiko.SFTP_PERMISSION_DENIED
        # Prevent removal of special files - link to vgrid dirs, etc.
        if os.path.islink(real_oldpath):
            self.logger.error("rename on link src %s :: %s" % (oldpath,
                                                        real_oldpath))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_oldpath):
            self.logger.error("rename on missing path %s :: %s" % \
                              (oldpath, real_oldpath))
            return paramiko.SFTP_NO_SUCH_FILE
        real_newpath = self._get_fs_path(newpath)
        try:
            # Use shutil move to allow move to other file system like external
            # storage mounted file systems
            shutil.move(real_oldpath, real_newpath)
            return paramiko.SFTP_OK
        except Exception, err:
            self.logger.error("rename on %s :: %s failed: %s" % \
                              (real_oldpath, real_newpath, err))
            return paramiko.SFTP_FAILURE

    def mkdir(self, path, mode):
        """Handle operations of same name"""
        path = force_utf8(path)
        self.logger.debug("mkdir %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('mkdir %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        try:
            # Force MiG default mode
            os.mkdir(real_path, 0755)
            return paramiko.SFTP_OK
        except Exception, err:
            self.logger.error("mkdir on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE

    def rmdir(self, path):
        """Handle operations of same name"""
        path = force_utf8(path)
        self.logger.debug("rmdir %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('rmdir %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        # Prevent removal of special files - link to vgrid dirs, etc.
        if os.path.islink(real_path):
            self.logger.error("rmdir rejected on link path %s :: %s" % \
                            (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("rmdir on missing path %s :: %s" % (path,
                                                                  real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        self.logger.debug("rmdir on path %s :: %s" % (path, real_path))
        try:
            os.rmdir(real_path)
            return paramiko.SFTP_OK
        except Exception, err:
            self.logger.error("rmdir on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE

    def chattr(self, path, attr):
        """Handle operations of same name"""
        return self._chattr(path, attr)

    def chmod(self, path, mode):
        """Handle operations of same name"""
        return self._chmod(path, mode)
         
    def readlink(self, path):
        """Handle operations of same name"""
        path = force_utf8(path)
        self.logger.debug("readlink %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            self.logger.warning('readlink %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("readlink on missing path %s :: %s" % \
                              (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            return self._strip_root(os.readlink(path))
        except Exception, err:
            self.logger.error("readlink on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE

    def symlink(self, target_path, path):
        """Handle operations of same name"""
        target_path = force_utf8(target_path)
        path = force_utf8(path)
        self.logger.debug('symlink %s %s' % (target_path, path))
        # Prevent users from creating symlinks for security reasons
        self.logger.error("symlink rejected on path %s :: %s" % (target_path,
                                                                 path))
        return paramiko.SFTP_OP_UNSUPPORTED


class SimpleSSHServer(paramiko.ServerInterface):
    """Custom SSH server with multi pub key support"""
    def __init__(self, users, *largs, **kwargs):
        conf = kwargs.get('conf', {})
        self.logger = conf.get("logger", logging.getLogger())
        self.event = threading.Event()
        self.users = users
        self.client_addr = kwargs.get('client_addr')
        self.authenticated_user = None
        self.allow_password = conf.get('allow_password', True)
        self.allow_publickey = conf.get('allow_publickey', True)

    def check_channel_request(self, kind, chanid):
        """Log connections"""
        self.logger.debug("channel_request: %s, %s" % (kind, chanid))
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):
        """Password auth against usermap.

        Please note that we take serious steps to secure against password
        cracking, but that it _may_ still be possible to achieve with a big
        effort.

        Paranoid users / grid owners should not enable password access in the
        first place!
        """
        offered = None
        if hit_rate_limit(configuration, "sftp-pw", self.client_addr[0],
                          username):
            logger.warning("Rate limiting login from %s" % self.client_addr[0])
        elif self.allow_password and self.users.has_key(username):
            # list of User login objects for username
            entries = self.users[username]
            offered = password
            for entry in entries:
                if entry.password is not None:
                    # TODO: Add ssh tunneling on resource frontends
                    #       before enforcing ip check
                    # and \
                    #(entry.ip_addr is None or
                    # entry.ip_addr == self.client_addr[0]):

                    allowed = entry.password
                    self.logger.debug("Password check for %s" % username)
                    if check_password_hash(offered, allowed):
                        self.logger.info("Authenticated %s" % username)
                        self.authenticated_user = username
                        update_rate_limit(configuration, "sftp-pw",
                                          self.client_addr[0], username, True)
                        return paramiko.AUTH_SUCCESSFUL
        err_msg = "Password authentication failed for %s" % username
        self.logger.error(err_msg)
        print err_msg
        failed_count = update_rate_limit(configuration, "sftp-pw",
                                         self.client_addr[0], username, False)
        penalize_rate_limit(configuration, "sftp-pw", self.client_addr[0],
                            username, failed_count)
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        """Public key auth against usermap"""
        offered = None

        if hit_rate_limit(configuration, "sftp-key", self.client_addr[0],
                          username, max_fails=10):
            logger.warning("Rate limiting login from %s" % self.client_addr[0])
        elif self.allow_publickey and self.users.has_key(username):
            # list of User login objects for username
            entries = self.users[username]
            offered = key.get_base64()
            for entry in entries:
                if entry.public_key is not None:
                    # TODO: Add ssh tunneling on resource frontends
                    #       before enforcing ip check
                    # and \
                    # (entry.ip_addr is None or 
                    #  entry.ip_addr == self.client_addr[0]):

                    allowed = entry.public_key.get_base64()
                    self.logger.debug("Public key check for %s" % username)
                    if allowed == offered:
                        self.logger.info("Public key match for %s" % username)
                        self.authenticated_user = username
                        update_rate_limit(configuration, "sftp-key",
                                          self.client_addr[0], username, True)
                        return paramiko.AUTH_SUCCESSFUL
        err_msg = 'Public key authentication failed for %s:\n%s' % \
                  (username, offered)
        self.logger.error(err_msg)
        print err_msg
        failed_count = update_rate_limit(configuration, "sftp-key",
                                         self.client_addr[0], username, False)
        penalize_rate_limit(configuration, "sftp-key", self.client_addr[0],
                            username, failed_count)
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        """Valid auth modes"""
        auths = []
        if self.allow_password:
            auths.append('password')
        if self.allow_publickey:
            auths.append('publickey')
        return ','.join(auths)

    def get_authenticated_user(self):
        """Extract username of authenticated user"""
        return self.authenticated_user

    def check_channel_shell_request(self, channel):
        """Check for shell request"""
        self.event.set()
        return True


def accept_client(client, addr, root_dir, users, jobs, host_rsa_key, conf={}):
    """Handle a single client session"""
    logger = conf.get("logger", logging.getLogger())
    logger.debug("In session handler thread from %s %s" % (client, addr))
    # Fill users in dictionary for fast lookup. We create a list of matching
    # User objects since each user may have multiple logins (e.g. public keys)
     
    usermap = {}
    for user_obj in users:
        if not usermap.has_key(user_obj.username):
            usermap[user_obj.username] = []
        usermap[user_obj.username].append(user_obj)
        
    for user_obj in jobs:
        if not usermap.has_key(user_obj.username):
            usermap[user_obj.username] = []
        usermap[user_obj.username].append(user_obj)

    window_size = conf.get('window_size', DEFAULT_WINDOW_SIZE)
    max_packet_size = conf.get('max_packet_size', DEFAULT_MAX_PACKET_SIZE)
    host_key_file = StringIO(host_rsa_key)
    host_key = paramiko.RSAKey(file_obj=host_key_file)
    transport = paramiko.Transport(client, default_window_size=window_size,
                                   default_max_packet_size=max_packet_size)
    transport.logger = logger
    transport.load_server_moduli()
    transport.add_server_key(host_key)
    logger.info("using transport window_size %d and max_packet_size %d" % \
                 (window_size, max_packet_size))

    if conf.has_key("sftp_implementation"):
        mod_name, class_name = conf['sftp_implementation'].split(':')
        fromlist = None
        try:
            parent = mod_name[0:mod_name.rindex('.')]
            fromlist = [parent]
        except:
            pass
        mod = __import__(mod_name, fromlist=fromlist)
        impl = getattr(mod, class_name)
        logger.debug("Custom implementation: %s" % conf['sftp_implementation'])
    else:
        impl = SimpleSftpServer
    transport.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp_si=impl,
                                    transport=transport, fs_root=root_dir,
                                    users=usermap, conf=conf)

    server = SimpleSSHServer(users=usermap, conf=conf, client_addr=addr)
    transport.start_server(server=server)
    
    channel = transport.accept(conf['auth_timeout'])
    username = server.get_authenticated_user()
    if username is not None:
        #user = usermap[username]
        logger.info("Login for %s from %s" % (username, addr))
                #print "type: %s"  % type(entry.public_key)
        print "Login for %s from %s" % (username, addr)
    else:
        logger.warning("Login from %s failed" % (addr, ))
        print "Login from %s failed - closing connection" % (addr, )
        transport.close()

    # Ignore user connection here as we only care about sftp.
    # Keep the connection alive until user disconnects or server is halted.

    while transport.is_active():
        if conf['stop_running'].is_set():
            transport.close()
        time.sleep(1)


def start_service(configuration):
    """Service daemon"""
    daemon_conf = configuration.daemon_conf
    logger = daemon_conf.get("logger", logging.getLogger())
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow reuse of socket to avoid TCP time outs
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        server_socket.bind((daemon_conf['address'], daemon_conf['port']))
        server_socket.listen(10)
    except Exception, err:
        err_msg = 'Could not open socket: %s' % err
        logger.error(err_msg)
        print err_msg
        if server_socket:
            server_socket.close()
        sys.exit(1)

    logger.debug("Accepting connections")
    
    min_expire_delay = 300
    last_expire = time.time()
    while True:
        client_tuple = None
        try:
            logger.info('accept with %d active sessions' % \
                        threading.active_count())
            client_tuple = server_socket.accept()
            # accept may return None or tuple with None part in corner cases
            if client_tuple == None or None in client_tuple:
                raise Exception('got empty bogus request')
            (client, addr) = client_tuple
        except KeyboardInterrupt:
            # forward KeyboardInterrupt to main thread
            server_socket.close()
            raise
        except Exception, err:
            logger.warning('ignoring failed client connection for %s: %s' % \
                           (client_tuple, err))
            continue
        # automatic reload of users if more than refresh_delay seconds old
        refresh_delay = 5
        if daemon_conf['time_stamp'] + refresh_delay < time.time():
            daemon_conf = refresh_users(configuration, 'sftp')
        daemon_conf = refresh_jobs(configuration, 'sftp')
        logger.info("Handling session from %s %s" % (client, addr))
        worker = threading.Thread(target=accept_client,
                                  args=[client, addr, daemon_conf['root_dir'],
                                        daemon_conf['users'],
                                        daemon_conf['jobs'],
                                        daemon_conf['host_rsa_key'],
                                        daemon_conf,])
        worker.start()
        if last_expire + min_expire_delay < time.time():
            last_expire = time.time()
            expired = expire_rate_limit(configuration, "sftp-*")
            logger.debug("Expired rate limit entries: %s" % expired)
        


if __name__ == "__main__":
    configuration = get_configuration_object()

    # Use separate logger

    logger = daemon_logger("sftp", configuration.user_sftp_log, "info")
    configuration.logger = logger
    
    # Allow configuration overrides on command line
    if sys.argv[1:]:
        configuration.user_sftp_address = sys.argv[1]
    if sys.argv[2:]:
        configuration.user_sftp_port = int(sys.argv[2])

    if not configuration.site_enable_sftp:
        err_msg = "SFTP access to user homes is disabled in configuration!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)
    print """
Running grid sftp server for user sftp access to their MiG homes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    print __doc__
    address = configuration.user_sftp_address
    port = configuration.user_sftp_port
    default_host_key = """
-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEA404IBMReHOdvhhJ5YtgquY3DNi0v0QwfPUk+EcH/CxFW8UCC
SUJe85up6lEQmOE9yKvrh+3yJgIjdV/ASOw9bd/u0NgNoPwl6A6P8GzHp94vz7UP
nTp+PEUbA8gwqXnzzdeuF3dLDSXuGHdcv8qQEVRBwj/haecO0fgZcfd4fmLDAG53
e/Vwc4lVIp4xx+OQowm9RW3nsAZge1DUoxlStD1/rEzBq1DvVx1Wu8pWS48f2ABH
fHt2Z4ozypMB+a4B56jervcZCNkV/fN2bdGZ8z07hNbn/EkaH2tPw/d62zdHddum
u7Pi0tYwMZz9GN3t18r9qi5ldUJuJNeNvNc7swIBIwKCAQBuZ7rAfKK9lPunhVDm
3gYfnKClSSXakNv5MjQXQPg4k2S+UohsudZZERgEGL7rK5MJspb44Um6sJThPSLh
l1EJe2VeH8wa/iEKUDdI5GD5w7DSmcXBZY3FgKa4sbE8X84wx9g3SJIq9SqA6YTS
LzAIasDasVA6wK9tTJ6lEczPq2VkxkzpKauDMgI6SpaBV+7Un3OM7VJEbWeaJVoZ
9I/2AHfp1hDpIfmaYBCnn2Ky70PBGA8DqAnHUKiid2dfZr8jKLu287LaUHxzIZXz
qSzS6Vg1K0kc5FrgTgrjaXAGNtMenXZdw2/7PMuBDaNuNUApFUlAP5LGvPQ9IRCt
YggDAoGBAP7z3lm74yxrzSa7HRASO2v3vp7jsbaYl4jPCc+6UruBFJlmUUdIQ2fh
8i2S1M5mAvZiJ/PKLQ3r6RXxWZOeh4Vw479HFCVHr5GstSfLolJ5svY8iWEoEGdN
D8aQTQrVAJwAPbLbF4eH5lgSokjOZcWMKsekk4vX2WmCMKWCMms/AoGBAOQ9Fffg
B8TMc1b+jTcj1Py5TiFsxIe3usYjn8Pgg8kpoGfdBoS/TxwoR0MbJdrPgXDKLlLn
A4GG6/7lFmxagCAfUyR2wAsOwAugcaFwS3K4QHGPiv9cgKxt9xhuhhDqXGI2lgAu
oJLcRYBvomPQ+3cGGgifclETTWgkzD5dNVaNAoGBAMStf6RPHPZhyiUxQk4581NK
FrUWDMAPUFOYZqePvCo/AUMjC4AhzZlH5rVxRRRAEOnz8u9EMWKCycB4Wwt6S0mu
25OOmoMorAKpzZO6WKYGHFeNyRBvXRx9Rq8e3FjQM6uLKEglW0tLlG/T3EbLG09A
PkI9IV1AHL8bShlHLjV5AoGBAJyBqKn4tN64FJNsuJrWve8f+w+bCmuxL53PSPtY
H9plr9IxKQqRz9jLKY0Z7hJiZ2NIz07KS4wEvxUvX9VFXyv4OQMPmaEur5LxrQD8
i4HdbgS6M21GvqIfhN2NncJ00aJukr5L29JrKFgSCPP9BDRb9Jgy0gu1duhTv0C0
8V/rAoGAEUheXHIqv9n+3oXLvHadC3aApiz1TcyttDM0AjZoSHpXoBB3AIpPdU8O
0drRG9zJTyU/BC02FvsGAMo0ZpGQRVMuN1Jj7sHsPaUdV38P4G0EaSQJDNxwFKVN
3stfzMDGtKM9lntAsfFQ8n4yvvEbn/quEWad6srf1yxt9B4t5JA=
-----END RSA PRIVATE KEY-----
"""
    try:
        host_key_fd = open(configuration.user_sftp_key, 'r')
        host_rsa_key = host_key_fd.read()
        host_key_fd.close()
    except IOError:
        logger.info("No valid host key provided - using default")
        host_rsa_key = default_host_key
    # Allow access to vgrid linked dirs and mounted storage resource dirs
    chroot_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base),
                         os.path.abspath(configuration.vgrid_files_home),
                         os.path.abspath(configuration.resource_home),
                         os.path.abspath(configuration.seafile_mount)]
    # Any extra chmod exceptions here - we already cover invisible_path check
    # in acceptable_chmod helper.
    chmod_exceptions = []
    configuration.daemon_conf = {
        'address': address,
        'port': port,
        'root_dir': os.path.abspath(configuration.user_home),
        'chmod_exceptions': chmod_exceptions,
        'chroot_exceptions': chroot_exceptions,
        'allow_password': 'password' in configuration.user_sftp_auth,
        'allow_digest': False,
        'allow_publickey': 'publickey' in configuration.user_sftp_auth,
        'user_alias': configuration.user_sftp_alias,
        'host_rsa_key': host_rsa_key,
        'users': [],
        'jobs': [],
        'time_stamp': 0,
        'logger': logger,
        'auth_timeout': 60,
        'stop_running': threading.Event(),
        'window_size': configuration.user_sftp_window_size,
        'max_packet_size': configuration.user_sftp_max_packet_size,
        }
    logger.info("Starting SFTP server")
    info_msg = "Listening on address '%s' and port %d" % (address, port)
    logger.info(info_msg)
    print info_msg
    try:
        start_service(configuration)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print info_msg
        configuration.daemon_conf['stop_running'].set()
    active = threading.active_count() - 1
    while active > 0:
        info_msg = "Waiting for %d worker threads to finish" % active
        logger.info(info_msg)
        print info_msg
        time.sleep(1)
        active = threading.active_count() - 1
    info_msg = "Leaving with no more workers active"
    logger.info(info_msg)
    print info_msg
