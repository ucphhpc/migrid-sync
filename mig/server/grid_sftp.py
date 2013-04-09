#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_sftp - SFTP server providing access to MiG user homes
# Copyright (C) 2010-2012  The MiG Project lead by Brian Vinter
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

"""Provide SFTP access to MiG user homes"""

import base64
import glob
import logging
import os
import socket
import shutil
import sys
import threading
import time
from StringIO import StringIO
import paramiko
import paramiko.util

from shared.base import client_dir_id, client_alias, invisible_path
from shared.conf import get_configuration_object
from shared.useradm import ssh_authkeys, get_ssh_authkeys, ssh_authpasswords, \
     get_ssh_authpasswords, check_password_hash, extract_field


configuration, logger = None, None


class User(object):
    """User login class to hold a single valid login for a user"""
    def __init__(self, username, password, 
                 chroot=True, home=None, public_key=None):
        self.username = username
        self.password = password
        self.chroot = chroot
        self.public_key = public_key
        if type(public_key) in (str, unicode):
            head, tail = public_key.split(' ')[:2]
            bits = base64.decodestring(tail)
            msg = paramiko.Message(bits)
            if head == 'ssh-rsa':
                parse_key = paramiko.RSAKey
            elif head == 'ssh-dss':
                parse_key = paramiko.DSSKey
            else:
                # Try RSA for unknown key types
                parse_key = paramiko.RSAKey
            try:
                key = parse_key(msg)
            except:
                key = None
            self.public_key = key

        self.home = home
        if self.home is None:
            self.home = self.username


class SFTPHandle(paramiko.SFTPHandle):
    """Override default SFTPHandle"""
    def __init__(self, flags=0, conf={}):
        paramiko.SFTPHandle.__init__(self, flags)
        self.logger = conf.get("logger", logging.getLogger())
        self.logger.debug("SFTPHandle init")

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
        self.logger.debug("SFTPHandle chattr on %s: %s" % \
                          (getattr(self, "path", "unknown"), attr))
        

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

    def _get_fs_path(self, sftp_path):
        """Internal helper to translate path with chroot and invisible files
        in mind"""
        real_path = "%s/%s" % (self.root, sftp_path)
        real_path = real_path.replace('//', '/')
        self.logger.debug("get_fs_path: %s :: %s" % (sftp_path, real_path))
        accept_roots = [self.root] + self.chroot_exceptions

        accepted = False
        for accept_path in accept_roots:
            expanded_path = os.path.realpath(real_path)
            if expanded_path.startswith(accept_path):
                # Found matching root - check visibility
                if not invisible_path(real_path):
                    accepted = True
                break
            
        if not accepted:
            self.logger.error("rejecting illegal path: %s" % real_path)
            raise ValueError("Invalid path")
        self.logger.debug("get_fs_path returns: %s :: %s" % (sftp_path,
                                                             real_path))
        return real_path

    def _strip_root(self, path):
        """Internal helper to strip root prefix for chrooted locations"""
        self.logger.debug("strip root on path: %s" % path)
        accept_roots = [self.root] + self.chroot_exceptions
        for root in accept_roots:
            if path.startswith(root):
                self.logger.debug("strip_root returns chrooted: %s" % \
                                  path.replace(root, ''))
                return path.replace(root, '')
        self.logger.debug("strip_root returns: %s" % path)
        return path

    def _flags_to_mode(self, flags):
        """Internal helper to convert bitmask of os.O_* flags to open-mode.

        It only handles read, write and append with and without truncation.
        Append and write always creates the file if missing, so checking for
        missing file creation flag should generally be handled separately.
        The same goes for handling of invalid flag combinations.

        This function is inspired by the XMP example in the fuse-python code
        http://sourceforge.net/apps/mediawiki/fuse/index.php?title=Main_Page
        but we need to prevent truncation unless explicitly requested.
        """
        # Truncate per default when enabling write - disable later if needed
        main_modes = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
        mode = main_modes[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]
        
        if flags & os.O_APPEND:
            mode = mode.replace('w', 'a', 1)
        # Disable truncation unless explicitly requested
        if not (flags & os.O_TRUNC):
            mode = mode.replace('w', 'r+', 1)
        return mode

    def _acceptable_chmod(self, path):
        """Internal helper to check that a chmod request is safe. That is, it
        only changes permission on files. Furthermore anything inside the dirs
        in chmod_exceptions should be left alone to avoid users touching
        read-only files or enabling execution of custom cgi scripts with
        potentially arbitrary code.
        """
        if os.path.isfile(path):
            if True in [os.path.realpath(path).startswith(i + os.sep) \
                        for i in self.chmod_exceptions]:
                return False
            else:
                return True
        else:
            return False

    def open(self, path, flags, attr):
        """Handle operations of same name"""        
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("open on %s :: %s (%s %s)" % \
                          (path, real_path, repr(flags), repr(attr)))
        if not (flags & os.O_CREAT) and not os.path.exists(real_path):
            self.logger.error("open existing file on missing path %s :: %s" % \
                              (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        handle = SFTPHandle(flags, conf=self.conf)
        setattr(handle, 'real_path', real_path)
        setattr(handle, 'path', path)
        try:
            # Fake OS level open call first to avoid most flag parsing.
            # This is necessary to make things like O_CREAT, O_EXCL and
            # O_TRUNCATE consistent with the simple mode strings.
            fake = os.open(real_path, flags, 0644)
            os.close(fake)
            mode = self._flags_to_mode(flags)
            if flags == os.O_RDONLY:
                # Read-only mode
                readfile = open(real_path, mode)
                setattr(handle, 'readfile', readfile)
                active = 'readfile'
            else:
                # All other modes are handled as writes
                writefile = open(real_path, mode)
                setattr(handle, 'writefile', writefile)
                active = 'writefile'
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
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("list_folder %s :: %s" % (path, real_path))
        rc = []
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
                rc.append(paramiko.SFTPAttributes.from_stat(
                    os.stat(full_name), self._strip_root(filename)))
            except Exception, err:
                self.logger.warning("list_folder %s: stat on %s failed: %s" % \
                                    (path, full_name, err))
        self.logger.debug("list_folder %s rc %s" % (path, rc))
        return rc

    def stat(self, path):
        """Handle operations of same name"""
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("stat %s :: %s" % (path, real_path))
        # for consistency with lstat
        if not os.path.exists(real_path):
            self.logger.error("stat on missing path %s :: %s" % (path,
                                                                 real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)
        except Exception, err:
            self.logger.error("lstat on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE            

    def lstat(self, path):
        """Handle operations of same name"""
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            return paramiko.SFTP_PERMISSION_DENIED
        self.logger.debug("lstat %s :: %s" % (path, real_path))
        if not os.path.lexists(real_path):
            self.logger.error("lstat on missing path %s :: %s" % (path,
                                                                real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)
        except Exception, err:
            self.logger.error("lstat on %s :: %s failed: %s" % \
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE            

    def remove(self, path):
        """Handle operations of same name"""
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
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
        self.logger.debug("rename %s %s" % (oldpath, newpath))
        try:
            real_oldpath = self._get_fs_path(oldpath)
        except ValueError, err:
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
        self.logger.debug("mkdir %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
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
        self.logger.debug("rmdir %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
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
        self.logger.debug("chattr %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("chattr on missing path %s :: %s" % (path,
                                                                   real_path))
            return paramiko.SFTP_NO_SUCH_FILE

        # Prevent users from messing with attributes as such.
        # We end here on chmod too, so pass any mode change requests there and
        # silently ignore them otherwise. It turns out to have caused problems
        # if we rejected those other attribute changes in the past but it may
        # not be a problem anymore. If it ain't broken...
        if hasattr(attr, 'st_mode') and attr.st_mode:
            self.logger.info("chattr %s forwarding for path %s :: %s" % \
                                (repr(attr), path, real_path))
            return self.chmod(path, attr.st_mode)
        else:
            self.logger.error("chattr %s ignored on path %s :: %s" % \
                                (repr(attr), path, real_path))
            return paramiko.SFTP_OK

    def chmod(self, path, mode):
        """Handle operations of same name"""
        self.logger.debug("chmod %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("chmod on missing path %s :: %s" % (path,
                                                                  real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        old_mode = os.stat(real_path).st_mode
        # Only allow change of mode on files and only outside chmod_exceptions
        if self._acceptable_chmod(real_path):
            # Only allow permission changes that won't give excessive access
            # or remove own access.
            new_mode = (mode & 0755) | 0600
            self.logger.info("chmod %s (%s) without damage on %s :: %s" % \
                                (new_mode, mode, path, real_path))
            try:
                os.chmod(real_path, new_mode)
            except Exception, err:
                self.logger.error("chmod %s (%s) failed on path %s :: %s %s" % \
                                  (new_mode, mode, path, real_path, err))
                return paramiko.SFTP_PERMISSION_DENIED
            return paramiko.SFTP_OK
        # Prevent users from messing up access modes
        self.logger.error("chmod %s rejected on path %s :: %s" % (mode, path,
                                                                  real_path))
        return paramiko.SFTP_OP_UNSUPPORTED
         
    def readlink(self, path):
        """Handle operations of same name"""
        self.logger.debug("readlink %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError, err:
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
        if self.allow_password and self.users.has_key(username):
            # list of User login objects for username
            entries = self.users[username]
            offered = password
            for entry in entries:
                if entry.password is not None:
                    allowed = entry.password
                    self.logger.debug("Password check for %s" % username)
                    if check_password_hash(offered, allowed):
                        self.logger.info("Authenticated %s" % username)
                        self.authenticated_user = username
                        return paramiko.AUTH_SUCCESSFUL
        err_msg = "Password authentication failed for %s" % username
        self.logger.error(err_msg)
        print err_msg
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        """Public key auth against usermap"""
        offered = None
        if self.allow_publickey and self.users.has_key(username):
            # list of User login objects for username
            entries = self.users[username]
            offered = key.get_base64()
            for entry in entries:
                if entry.public_key is not None:
                    allowed = entry.public_key.get_base64()
                    self.logger.debug("Public key check for %s" % username)
                    if allowed == offered:
                        self.logger.info("Public key match for %s" % username)
                        self.authenticated_user = username
                        return paramiko.AUTH_SUCCESSFUL
        err_msg = 'Public key authentication failed for %s:\n%s' % \
                  (username, offered)
        self.logger.error(err_msg)
        print err_msg
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


def accept_client(client, addr, root_dir, users, host_rsa_key, conf={}):
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

    host_key_file = StringIO(host_rsa_key)
    host_key = paramiko.RSAKey(file_obj=host_key_file)
    transport = paramiko.Transport(client)
    transport.logger = logger
    transport.load_server_moduli()
    transport.add_server_key(host_key)

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

    server = SimpleSSHServer(users=usermap, conf=conf)
    transport.start_server(server=server)
    channel = transport.accept()
    username = server.get_authenticated_user()
    if username is not None:
        user = usermap[username]
        logger.info("Login for %s from %s" % (username, addr))
        print "Login for %s from %s" % (username, addr)

    # Ignore user connection here as we only care about sftp.
    # Keep the connection alive until user disconnects or server is halted.

    while transport.is_active():
        if conf['stop_running'].is_set():
            transport.close()
        time.sleep(1)


def refresh_users(conf):
    '''Reload users from conf if it changed on disk. Add user entries for all
    active keys and passwords enabled in conf. Optionally add short ID
    username alias entries for all users if that is enabled in the conf.
    Removes all the user entries no longer active, too.
    '''
    logger = conf.get("logger", logging.getLogger())
    last_update = conf['time_stamp']
    old_usernames = [i.username for i in conf['users']]
    cur_usernames = []
    authkeys_pattern = os.path.join(conf['root_dir'], '*', ssh_authkeys)
    authpasswords_pattern = os.path.join(conf['root_dir'], '*',
                                         ssh_authpasswords)
    short_id, short_alias = None, None
    matches = []
    if conf['allow_publickey']:
        matches += [(ssh_authkeys, i) for i in glob.glob(authkeys_pattern)]
    if conf['allow_password']:
        matches += [(ssh_authpasswords, i) \
                    for i in glob.glob(authpasswords_pattern)] 
    for (auth_file, path) in matches:
        logger.debug("Checking %s" % path)
        user_home = path.replace(os.sep + auth_file, '')
        user_dir = user_home.replace(conf['root_dir'] + os.sep, '')
        user_id = client_dir_id(user_dir)
        user_alias = client_alias(user_id)
        cur_usernames.append(user_alias)
        if conf['user_alias']:
            short_id = extract_field(user_id, conf['user_alias'])
            short_alias = client_alias(short_id)
            cur_usernames.append(short_alias)
        if last_update >= os.path.getmtime(path):
            continue
        # Create user entry for each valid key and password 
        if auth_file == ssh_authkeys:
            all_keys = get_ssh_authkeys(path)
            all_passwords = []
            # Clean up all old key entries for this user
            conf['users'] = [i for i in conf['users'] \
                             if i.username != user_alias or \
                             i.public_key is None]
        else:
            all_keys = []
            all_passwords = get_ssh_authpasswords(path)
            # Clean up all old password entries for this user
            conf['users'] = [i for i in conf['users'] \
                             if i.username != user_alias or \
                             i.password is None]
        for user_key in all_keys:
            if not user_key.startswith('ssh-rsa ') and \
                   not user_key.startswith('ssh-dss '):
                logger.warning("Skipping broken key %s for user %s" % \
                               (user_key, user_id))
                continue
            user_key = user_key.strip()
            logger.debug("Adding user:\nname: %s\nalias: %s\nhome: %s\nkey: %s"\
                        % (user_id, user_alias, user_dir, user_key))
            conf['users'].append(
                User(username=user_alias, home=user_dir, password=None,
                     public_key=user_key, chroot=True),
                )
            # Add short alias copy if user aliasing is enabled
            if short_id:
                logger.debug("Adding alias:\nname: %s\nalias: %s\nhome: %s\nkey: %s"\
                             % (user_id, short_alias, user_dir, user_key))
                conf['users'].append(
                    User(username=short_alias, home=user_dir, password=None,
                         public_key=user_key, chroot=True),
                    )
        for user_password in all_passwords:
            user_password = user_password.strip()
            logger.debug("Adding user:\nname: %s\nalias: %s\nhome: %s\npw: %s"\
                        % (user_id, user_alias, user_dir, user_password))
            conf['users'].append(
                User(username=user_alias, home=user_dir,
                     password=user_password, public_key=None, chroot=True))
            # Add short alias copy if user aliasing is enabled
            if short_id:
                logger.debug("Adding alias:\nname: %s\nalias: %s\nhome: %s\nkey: %s"\
                             % (user_id, short_alias, user_dir, user_password))
                conf['users'].append(
                    User(username=short_alias, home=user_dir, password=user_password,
                         public_key=None, chroot=True),
                    )
    removed = [i for i in old_usernames if not i in cur_usernames]
    if removed:
        logger.info("Removing login for %d deleted users" % len(removed))
        conf['users'] = [i for i in conf['users'] if not i.username in removed]
    logger.info("Refreshed users from configuration (%d users)" % \
                len(conf['users']))
    conf['time_stamp'] = time.time()
    return conf

def start_service(service_conf):
    """Service daemon"""
    logger = service_conf.get("logger", logging.getLogger())
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow reuse of socket to avoid TCP time outs
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        server_socket.bind((service_conf['address'], service_conf['port']))
        server_socket.listen(10)
    except Exception, err:
        err_msg = 'Could not open socket: %s' % err
        logger.error(err_msg)
        print err_msg
        if server_socket:
            server_socket.close()
        sys.exit(1)

    logger.debug("Accepting connections")
    while True:
        try:
            client_tuple = server_socket.accept()
            # accept may return None or tuple with None part in corner cases
            if client_tuple == None or None in client_tuple:
                raise Exception('got empty bogus request')
            (client, addr) = client_tuple
        except KeyboardInterrupt:
            # forward KeyboardInterrupt to main thread
            raise
        except Exception, err:
            logger.warning('ignoring failed client connection: %s' % err)
            continue
        # automatic reload of users if more than refresh_delay seconds old
        refresh_delay = 60
        if service_conf['time_stamp'] + refresh_delay < time.time():
            service_conf = refresh_users(service_conf)
        logger.info("Handling session from %s %s" % (client, addr))
        worker = threading.Thread(target=accept_client,
                                  args=[client, addr, service_conf['root_dir'],
                                        service_conf['users'],
                                        service_conf['host_rsa_key'],
                                        service_conf,])
        worker.start()


if __name__ == "__main__":
    configuration = get_configuration_object()
    logger = configuration.logger
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
                         os.path.abspath(configuration.resource_home)]
    # Don't allow chmod in dirs with CGI access as it introduces arbitrary
    # code execution vulnerabilities
    chmod_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base)]
    sftp_conf = {'address': address,
                 'port': port,
                 'root_dir': os.path.abspath(configuration.user_home),
                 'chmod_exceptions': chmod_exceptions,
                 'chroot_exceptions': chroot_exceptions,
                 'allow_password': 'password' in configuration.user_sftp_auth,
                 'allow_publickey': 'publickey' in configuration.user_sftp_auth,
                 'user_alias': configuration.user_sftp_alias,
                 'host_rsa_key': host_rsa_key,
                 'users': [],
                 'time_stamp': 0,
                 'logger': logger,
                 'stop_running': threading.Event()}
    info_msg = "Listening on address '%s' and port %d" % (address, port)
    logger.info(info_msg)
    print info_msg
    try:
        start_service(sftp_conf)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print info_msg
        sftp_conf['stop_running'].set()
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
