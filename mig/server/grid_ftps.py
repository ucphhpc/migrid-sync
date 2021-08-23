#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_ftps - secure ftp server wrapping ftp in tls/ssl and mapping user home
# Copyright (C) 2014-2021  The MiG Project lead by Brian Vinter
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
# This code is a heavily modified version of the tls server example from the
# pyftpdlib package
# https://code.google.com/p/pyftpdlib
#
# = Original copyright notice follows =

#  pyftpdlib is released under the MIT license, reproduced below:
#  ======================================================================
#  Copyright (C) 2007-2013 Giampaolo Rodola' <g.rodola@gmail.com>
#
#                         All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
#  ======================================================================

"""An RFC-4217 asynchronous FTPS server supporting both SSL and TLS.

Extended to fit MiG user auth and access restrictions.

Requires PyOpenSSL module (http://pypi.python.org/pypi/pyOpenSSL) unless
only used in plain FTP mode.
"""

from __future__ import print_function
from __future__ import absolute_import

import base64
import os
import sys
import time

try:
    from pyftpdlib.authorizers import DummyAuthorizer, AuthenticationFailed
    from pyftpdlib.handlers import FTPHandler, TLS_FTPHandler
    from pyftpdlib.servers import ThreadedFTPServer
    from pyftpdlib.filesystems import AbstractedFS, FilesystemError
except ImportError:
    print("ERROR: the python pyftpdlib module is required for this daemon")
    raise
# PyOpenSSL is required for strong encryption
try:
    import OpenSSL
except ImportError:
    print("WARNING: the python OpenSSL module is required for FTPS")
    OpenSSL = None

from mig.shared.accountstate import check_account_accessible
from mig.shared.base import invisible_path, force_utf8, force_native_str
from mig.shared.conf import get_configuration_object
from mig.shared.fileio import user_chroot_exceptions
from mig.shared.griddaemons.ftps import default_max_user_hits, \
    default_user_abuse_hits, default_proto_abuse_hits, \
    default_max_secret_hits, default_username_validator, \
    get_fs_path, acceptable_chmod, refresh_user_creds, refresh_share_creds, \
    update_login_map, login_map_lookup, hit_rate_limit, expire_rate_limit, \
    check_twofactor_session, validate_auth_attempt
from mig.shared.logger import daemon_logger, register_hangup_handler
from mig.shared.pwhash import make_simple_hash
from mig.shared.tlsserver import hardened_openssl_context
from mig.shared.useradm import check_password_hash
from mig.shared.validstring import possible_user_id, possible_sharelink_id
from mig.shared.vgrid import in_vgrid_share


configuration, logger = None, None


class MiGTLSFTPHandler(TLS_FTPHandler):
    """Hardened version of TLS_FTPHandler to fix
    https://github.com/giampaolo/pyftpdlib/issues/315

    Makes sure buffer gets reset after AUTH to avoid command injection.
    """

    def ftp_AUTH(self, line):
        res = super(MiGTLSFTPHandler, self).ftp_AUTH(line)
        # NOTE: fix for https://github.com/giampaolo/pyftpdlib/issues/315
        print("DEBUG: reset in buffer on switch to secure channel")
        print("I.e. truncate '%s'" % self.ac_in_buffer)
        # IMPORTANT: buffer must be bytes on all python versions
        self.ac_in_buffer = b''
        self.incoming = []
        return res


class MiGUserAuthorizer(DummyAuthorizer):
    """Authenticate/authorize against MiG users DB and user password files.
    Only instantiated once from central server thread so we don't need locking
    in creds refresh.
    """

    authenticated_user = None

    min_expire_delay = 120
    last_expire = time.time()

    def _update_logins(self, configuration, user_id):
        """Update user DB for user_id and internal user_table for logins.
        Only called from central auth thread - no locking required.
        """
        daemon_conf = configuration.daemon_conf
        # No need for locking here - please see docstring note
        changed_users = update_users(configuration, daemon_conf['login_map'],
                                     user_id)
        logger.debug("found changed logins %s" % changed_users)
        if not changed_users:
            return None
        # Fill users in dictionary for fast lookup. We create a list of
        # matching User objects since each user may have multiple logins (e.g.
        # public keys)
        for username in changed_users:
            logger.debug("update user %s" % username)
            # Always remove old entries
            if self.has_user(username):
                self.remove_user(username)
            # Make sure user is still in logins - the change could be removal
            user_obj_list = login_map_lookup(daemon_conf, username)
            if not user_obj_list:
                logger.info("user %s is no longer allowed" % username)
                continue
            # We prefer last entry with password but fall back to any entry
            # to assure at least a hit
            user_obj = (user_obj_list + [i for i in user_obj_list
                                         if i.password is not None])[-1]
            home_path = os.path.join(daemon_conf['root_dir'], user_obj.home)
            # Expand symlinked homes for aliases
            if os.path.islink(home_path):
                try:
                    home_path = os.readlink(home_path)
                except Exception as err:
                    logger.error("could not expand link %s" % home_path)
                    continue
            logger.debug("add user to user_table: %s" % user_obj)
            # The add_user format and perm string meaning is explained at:
            # http://code.google.com/p/pyftpdlib/wiki/Tutorial#2.2_-_Users
            # NOTE: force saved password hash to native string format
            self.add_user(username, force_native_str(user_obj.password),
                          home_path, perm='elradfmwM')
        logger.debug("updated user_table: %s" % self.user_table)

    def validate_authentication(self, username, password, handler):
        """Password auth against internal DB built from login_map.

        Please note that we take serious steps to secure against password
        cracking, but that it _may_ still be possible to achieve with a big
        effort.

        The following is checked before granting auth:
        1) Valid username
        2) Valid user (Does user exist with enabled FTPS)
        3) Account is active and not expired
        4) Valid 2FA session (if 2FA is enabled)
        5) Hit rate limit (Too many auth attempts)
        6) Valid password (if password enabled)
        """
        hashed_secret = None
        disconnect = False
        strict_password_policy = True
        password_offered = None
        password_enabled = False
        invalid_username = False
        invalid_user = False
        account_accessible = False
        valid_password = False
        valid_twofa = False
        exceeded_rate_limit = False
        client_ip = handler.remote_ip
        client_port = handler.remote_port
        # NOTE: keep username on native form in general
        username = force_native_str(username)
        daemon_conf = configuration.daemon_conf
        max_user_hits = daemon_conf['auth_limits']['max_user_hits']
        user_abuse_hits = daemon_conf['auth_limits']['user_abuse_hits']
        proto_abuse_hits = daemon_conf['auth_limits']['proto_abuse_hits']
        max_secret_hits = daemon_conf['auth_limits']['max_secret_hits']
        logger.debug("Authentication for %s from %s" % (username, client_ip))
        logger.debug("daemon_conf['allow_password']: %s" %
                     daemon_conf['allow_password'])

        # For e.g. GDP we require all logins to match active 2FA session IP,
        # but otherwise user may freely switch net during 2FA lifetime.
        if configuration.site_twofactor_strict_address:
            enforce_address = client_ip
        else:
            enforce_address = None

        # We don't have a handle_request for server so expire here instead

        if self.last_expire + self.min_expire_delay < time.time():
            self.last_expire = time.time()
            expire_rate_limit(configuration, "ftps",
                              expire_delay=self.min_expire_delay)
        if hit_rate_limit(configuration, 'ftps', client_ip, username,
                          max_user_hits=max_user_hits):
            exceeded_rate_limit = True
        elif not default_username_validator(configuration, username):
            invalid_username = True
        elif daemon_conf['allow_password']:
            hash_cache = daemon_conf['hash_cache']
            # NOTE: keep password on native form in general
            password_offered = force_native_str(password)
            # NOTE: base64 encode requires byte string and returns byte string
            hashed_secret = make_simple_hash(
                base64.b64encode(force_utf8(password_offered)))
            # Only sharelinks should be excluded from strict password policy
            if configuration.site_enable_sharelinks and \
                    possible_sharelink_id(configuration, username):
                strict_password_policy = False
            logger.info("refresh login for %s" % username)
            self._update_logins(configuration, username)
            if not self.has_user(username):
                if not os.path.islink(
                        os.path.join(daemon_conf['root_dir'], username)):
                    invalid_user = True
                entries = []
            else:
                # list of User login objects for username
                entries = [self.user_table[username]]
            # NOTE: always check accessible unless invalid_user to make sure
            #       we don't report expired for active users with auth disabled
            if not invalid_user:
                account_accessible = check_account_accessible(configuration,
                                                              username, 'ftps')
            for entry in entries:
                if entry['pwd'] is not None:
                    password_enabled = True
                    # NOTE: make sure allowed value is native string as well
                    password_allowed = force_native_str(entry['pwd'])
                    logger.debug("Password check for %s" % username)
                    if check_password_hash(
                            configuration, 'ftps', username,
                            password_offered, password_allowed,
                            hash_cache, strict_password_policy):
                        valid_password = True
                        break
            if valid_password and check_twofactor_session(
                    configuration, username, enforce_address, 'ftps'):
                valid_twofa = True

        # Update rate limits and write to auth log

        (authorized, disconnect) = validate_auth_attempt(
            configuration,
            'ftps',
            'password',
            username,
            client_ip,
            client_port,
            secret=hashed_secret,
            invalid_username=invalid_username,
            invalid_user=invalid_user,
            account_accessible=account_accessible,
            valid_twofa=valid_twofa,
            authtype_enabled=password_enabled,
            valid_auth=valid_password,
            exceeded_rate_limit=exceeded_rate_limit,
            user_abuse_hits=user_abuse_hits,
            proto_abuse_hits=proto_abuse_hits,
            max_secret_hits=max_secret_hits,
        )

        if disconnect:
            handler._shutdown_connecting_dtp()
        if authorized:
            self.authenticated_user = username
            return True
        else:
            # Must raise AuthenticationFailed exception since version 1.0.0 instead
            # of returning bool
            self.authenticated_user = None
            raise AuthenticationFailed()


class MiGRestrictedFilesystem(AbstractedFS):
    """Restrict access to user home and symlinks into the dirs configured in
    chroot_exceptions. Prevent access to a few hidden files.
    """

    chmod_exceptions = None

    # Use shared daemon fs helper functions

    def _acceptable_chmod(self, ftps_path, mode):
        """Wrap helper"""
        #logger.debug("acceptable_chmod: %s" % ftps_path)
        reply = acceptable_chmod(ftps_path, mode, self.chmod_exceptions)
        if not reply:
            logger.warning("acceptable_chmod failed: %s %s %s" %
                           (ftps_path, mode, self.chmod_exceptions))
        # logger.debug("acceptable_chmod returns: %s :: %s" % \
        #                      (ftps_path, reply))
        return reply

    # Public interface functions

    def validpath(self, path):
        """Check that user is allowed inside path checking against configured
        chroot_exceptions and built-in hidden paths.
        """
        daemon_conf = configuration.daemon_conf
        try:
            get_fs_path(configuration, path, self.root,
                        daemon_conf['chroot_exceptions'])
            #logger.debug("accepted access to %s" % path)
            return True
        except ValueError as err:
            logger.warning("rejected illegal access to %s :: %s" % (path, err))
            return False

    def chmod(self, path, mode):
        """Change file/directory mode with MiG restrictions"""
        real_path = self.ftp2fs(path)
        daemon_conf = configuration.daemon_conf
        self.chmod_exceptions = daemon_conf['chmod_exceptions']
        # Only allow change of mode on files and only outside chmod_exceptions
        if not self._acceptable_chmod(path, mode):
            # Prevent users from messing up access modes
            logger.warning("chmod %s rejected on path %s :: %s" % (mode, path,
                                                                   real_path))
            raise FilesystemError("requested permission change not allowed")

        # Only allow permission changes that won't give excessive access
        # or remove own access.
        if os.path.isdir(path):
            new_mode = (mode & 0o775) | 0o750
        else:
            new_mode = (mode & 0o775) | 0o640
        logger.info("chmod %s (%s) without damage on %s :: %s" %
                    (new_mode, mode, path, real_path))
        return AbstractedFS.chmod(self, path, new_mode)

    def listdir(self, path):
        """List the content of a directory with MiG restrictions"""
        return [i for i in AbstractedFS.listdir(self, path) if not
                invisible_path(i)]

    ### Force symlinks to look like real dirs to avoid client confusion ###
    def lstat(self, path):
        """Modified to always return real stat to hide symlinks"""
        return self.stat(path)

    def readlink(self, path):
        """Modified to always return just path to hide symlinks"""
        return path

    def islink(self, path):
        """Modified to always return False to hide symlinks"""
        return False

    def lexists(self, path):
        """Modified to always check with stat to hide symlinks"""
        try:
            self.stat(path)
            return True
        except:
            return False

    def rmdir(self, path):
        """Handle operations of same name"""
        ftp_path = self.fs2ftp(path)
        # Prevent removal of special dirs
        if in_vgrid_share(configuration, path) == ftp_path[1:]:
            logger.error("rmdir on vgrid src %s :: %s" % (ftp_path,
                                                          path))
            raise FilesystemError("requested rmdir not allowed")
        return AbstractedFS.rmdir(self, path)

    def remove(self, path):
        """Handle operations of same name"""
        ftp_path = self.fs2ftp(path)
        # Prevent removal of special files
        if in_vgrid_share(configuration, path) == ftp_path[1:]:
            logger.error("remove on vgrid src %s :: %s" % (ftp_path,
                                                           path))
            raise FilesystemError("requested remove not allowed")
        return AbstractedFS.remove(self, path)

    def rename(self, old_path, new_path):
        """Handle operations of same name"""
        ftp_old_path = self.fs2ftp(old_path)
        ftp_new_path = self.fs2ftp(new_path)
        # Prevent rename of special files
        if in_vgrid_share(configuration, old_path) == ftp_old_path[1:]:
            logger.error("rename on vgrid src %s :: %s" % (ftp_old_path,
                                                           old_path))
            raise FilesystemError("requested rename not allowed")
        return AbstractedFS.rename(self, old_path, new_path)


def update_users(configuration, login_map, username):
    """Update login_map with username/password pairs for username and any
    aliases.
    """
    # Only need to update users and shares here, since jobs only use sftp
    changed_users, changed_shares = [], []
    if possible_user_id(configuration, username):
        daemon_conf, changed_users = refresh_user_creds(configuration, 'ftps',
                                                        username)
    if configuration.site_enable_sharelinks and \
            possible_sharelink_id(configuration, username):
        daemon_conf, changed_shares = refresh_share_creds(configuration,
                                                          'ftps', username)
    update_login_map(daemon_conf, changed_users, changed_jobs=[],
                     changed_shares=changed_shares)
    return changed_users + changed_shares


def start_service(conf):
    """Main server"""
    daemon_conf = configuration.daemon_conf
    authorizer = MiGUserAuthorizer()
    if daemon_conf['nossl'] or not configuration.user_ftps_key:
        logger.warning('Not wrapping connections in SSL - only for testing!')
        handler = FTPHandler
    elif OpenSSL is None:
        logger.error("Can't run FTPS server without PyOpenSSL!")
        return False
    else:
        logger.info("Using fully encrypted mode")
        handler = MiGTLSFTPHandler
        # requires SSL for both control and data channel
        handler.tls_control_required = True
        handler.tls_data_required = True
        keyfile = certfile = conf.user_ftps_key
        handler.certfile = certfile
        # Harden TLS/SSL if possible, requires recent pyftpdlib
        if hasattr(handler, 'ssl_context'):
            dhparamsfile = configuration.user_shared_dhparams
            legacy_tls = configuration.site_enable_ftps_legacy_tls
            ssl_ctx = hardened_openssl_context(conf, OpenSSL, keyfile,
                                               certfile,
                                               dhparamsfile=dhparamsfile,
                                               allow_pre_tlsv12=legacy_tls)
            handler.ssl_context = ssl_ctx
        else:
            logger.warning("Unable to enforce explicit strong TLS connections")
            logger.warning(
                "Upgrade to a recent pyftpdlib for maximum security")

    # NOTE: We use the threaded FTP server to prevent slow requests from
    # blocking the flow of all other clients. Auth still takes place in main
    # process thread so we don't need locking on user creds refresh.
    handler.authorizer = authorizer
    handler.abstracted_fs = MiGRestrictedFilesystem
    # TODO: masqueraded ftps fails from fireftp - maybe this would help?
    # if configuration.user_ftps_show_address != configuration.user_ftps_address:
    #    handler.masquerade_address = socket.gethostbyname(
    #        configuration.user_ftps_show_address)
    handler.passive_ports = conf.user_ftps_pasv_ports
    server = ThreadedFTPServer((conf.user_ftps_address,
                                conf.user_ftps_ctrl_port),
                               handler)
    server.serve_forever()


if __name__ == '__main__':
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("ftps", configuration.user_ftps_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # Allow configuration overrides on command line
    nossl = False
    if sys.argv[2:]:
        configuration.user_ftps_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_ftps_ctrl_port = int(sys.argv[3])
    if sys.argv[4:]:
        nossl = (sys.argv[4].lower() in ('1', 'true', 'yes', 'on'))

    if not configuration.site_enable_ftps:
        err_msg = "FTPS access to user homes is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)
    print("""
Running grid ftps server for user ftps access to their MiG homes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
""")
    print(__doc__)
    address = configuration.user_ftps_address
    ctrl_port = configuration.user_ftps_ctrl_port
    pasv_ports = configuration.user_ftps_pasv_ports

    # Lookup chroot exceptions once and for all
    chroot_exceptions = user_chroot_exceptions(configuration)
    # Any extra chmod exceptions here - we already cover invisible_path check
    # in acceptable_chmod helper.
    chmod_exceptions = []
    configuration.daemon_conf = {
        'address': address,
        'ctrl_port': ctrl_port,
        'pasv_ports': pasv_ports,
        'root_dir': os.path.abspath(configuration.user_home),
        'chmod_exceptions': chmod_exceptions,
        'chroot_exceptions': chroot_exceptions,
        'allow_password': 'password' in configuration.user_ftps_auth,
        'allow_digest': False,
        'allow_publickey': 'publickey' in configuration.user_ftps_auth,
        'user_alias': configuration.user_ftps_alias,
        # No creds locking needed here due to central auth
        'creds_lock': None,
        'users': [],
        'shares': [],
        'login_map': {},
        'hash_cache': {},
        'time_stamp': 0,
        'logger': logger,
        'nossl': nossl,
        # TODO: Add the following to configuration:
        # max_ftps_user_hits
        # max_ftps_user_abuse_hits
        # max_ftps_proto_abuse_hits
        # max_ftps_secret_hits
        'auth_limits':
            {'max_user_hits': default_max_user_hits,
             'user_abuse_hits': default_user_abuse_hits,
             'proto_abuse_hits': default_proto_abuse_hits,
             'max_secret_hits': default_max_secret_hits,
             }
    }
    logger.info("Starting FTPS server")
    info_msg = "Listening on address '%s' and port %d" % (address, ctrl_port)
    logger.info(info_msg)
    print(info_msg)
    while True:
        try:
            start_service(configuration)
        except KeyboardInterrupt:
            info_msg = "Received user interrupt"
            logger.info(info_msg)
            print(info_msg)
            configuration.daemon_conf['stop_running'].set()
            break
        except Exception as exc:
            err_msg = "Received unexpected error: %s" % exc
            logger.error(err_msg)
            print(err_msg)
            # Throttle a bit
            time.sleep(5)
    info_msg = "Leaving with no more workers active"
    logger.info(info_msg)
    print(info_msg)
