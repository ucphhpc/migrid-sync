#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_sftp - SFTP server providing access to MiG user homes
# Copyright (C) 2010-2024  The MiG Project lead by Brian Vinter
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

from __future__ import print_function
from __future__ import absolute_import

import base64
import os
import shutil
import socket
import sys
import threading
import time
from functools import wraps

try:
    import paramiko
    import paramiko.util
    from paramiko.common import DEFAULT_WINDOW_SIZE, DEFAULT_MAX_PACKET_SIZE
except ImportError:
    print("ERROR: the python paramiko module is required for this daemon")
    sys.exit(1)

from mig.shared.accountstate import check_account_accessible
from mig.shared.base import invisible_path, force_utf8, force_native_str, \
    force_native_fs, NativeStringIO
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import keyword_auto, STRONG_SSH_KEXALGOS, \
    STRONG_SSH_CIPHERS, STRONG_SSH_MACS, STRONG_SSH_LEGACY_KEXALGOS, \
    STRONG_SSH_LEGACY_MACS
from mig.shared.fileio import check_write_access, user_chroot_exceptions, \
    read_file
from mig.shared.gdp.all import project_open, project_close, project_log
from mig.shared.griddaemons.sftp import default_username_validator, \
    default_max_user_hits, default_user_abuse_hits, \
    default_proto_abuse_hits, default_max_secret_hits, \
    get_fs_path, strip_root, flags_to_mode, acceptable_chmod, \
    refresh_user_creds, refresh_job_creds, refresh_share_creds, \
    refresh_jupyter_creds, update_login_map, login_map_lookup, \
    hit_rate_limit, expire_rate_limit, clear_sessions, \
    track_open_session, track_close_session, expire_dead_sessions, \
    active_sessions, check_twofactor_session, validate_auth_attempt, authlog
from mig.shared.logger import daemon_logger, daemon_gdp_logger, \
    register_hangup_handler
from mig.shared.notification import send_system_notification
from mig.shared.pwcrypto import make_simple_hash
from mig.shared.useradm import check_password_hash
from mig.shared.validstring import possible_user_id, possible_gdp_user_id, \
    possible_job_id, possible_sharelink_id, possible_jupyter_mount_id
from mig.shared.vgrid import in_vgrid_share
from mig.shared.vgridaccess import is_vgrid_parent_placeholder
from mig.shared.workflows import add_workflow_job_history_entry

configuration, logger = None, None


class SFTPHandle(paramiko.SFTPHandle):
    """Override default SFTPHandle"""

    # Init internal args so that they can be overriden on class before init

    logger = None
    sftpserver = None
    ftrace = None
    valid_ftrace_types = None

    def __init__(self, flags=0, sftpserver=None):
        paramiko.SFTPHandle.__init__(self, flags)
        if sftpserver is not None:
            self.sftpserver = sftpserver
        if self.logger is None:
            self.logger = logger
        if configuration.site_enable_gdp:
            self.valid_ftrace_types = ['read', 'write']
            self.ftrace = {}
            for ftracetype in self.valid_ftrace_types:
                self.ftrace[ftracetype] = \
                    {'startpos': 0,
                     'endpos': 0,
                     'count': 0,
                     'logstatus': False}
        # self.logger.debug("SFTPHandle init: %s" % repr(flags))

    def __workflow_history_log(method):
        @wraps(method)
        def _impl(self, *method_args, **method_kwargs):
            if not configuration.site_enable_workflow_history:
                return method(self, *method_args, **method_kwargs)
            operation = method.__name__

            if operation != 'write':
                return method(self, *method_args, **method_kwargs)

            path = getattr(self, "path", None)
            user_name = getattr(self, "user_name", None)

            # Strip leading slash - should only be necessary in manual testing
            path = path.lstrip(os.sep)
            if os.sep in path:
                # TODO: is this really correct for nested vgrids?
                vgrid = path.split(os.sep, 1)[0]
            else:
                vgrid = path

            # logger.debug('path is now %s' % path)

            status, msg = add_workflow_job_history_entry(
                configuration,
                vgrid,
                user_name,
                operation,
                path)

            # logger.debug('logging status: %s, %s' % (status, msg))

            return method(self, *method_args, **method_kwargs)

        return _impl

    def __gdp_log(method):
        """Decorator used for GDP logging
        The first non-contiguous read/write operation is logged.
        Thereafter all contiguous read/write operations are clustered
        into one log entry to avoid log flooding.
        Upon 'close' the clustered log entry is written to the log"""
        @wraps(method)
        def _impl(self, *method_args, **method_kwargs):
            if not configuration.site_enable_gdp \
                    or configuration.loglevel != 'debug':
                return method(self, *method_args, **method_kwargs)
            logger = configuration.logger
            result = None
            valid_log_actions = {'read': 'accessed',
                                 'write': 'modified'}
            operation = method.__name__
            path = getattr(self, "path", None)
            user_name = getattr(self, "user_name", None)
            ip_addr = getattr(self, "ip_addr", None)
            if path is None:
                logger.error("Missing GDP log path")
                return None
            if user_name is None:
                logger.error("Missing GDP log user_name")
                return None
            if ip_addr is None:
                logger.error("Missing GDP log ip_addr")
                return None

            # read / write
            #
            # GDP logging is performed before the actual read/write
            # operation to ensure that files are _NOT_ accessed/modified
            # without a corresponding log entry.

            if operation in ('read', 'write'):
                log_action = valid_log_actions.get(operation, None)
                if log_action is None:
                    logger.error(
                        "Missing GDP log action for operation: '%s'"
                        % method.__name__)
                    return None
                ftrace = self.ftrace.get(operation, None)
                if ftrace is None:
                    logger.error(
                        "Missing GDP log ftrace for operation: '%s'"
                        % operation)
                    return None
                if operation == "read":
                    offset = method_args[0]
                    length = method_args[1]
                    currentpos = self.readfile.tell()
                    endpos = offset + length
                elif operation == "write":
                    offset = method_args[0]
                    length = len(method_args[1])
                    currentpos = self.writefile.tell()
                    endpos = offset + length
                else:
                    return None
                if ftrace['count'] == 0 \
                        or offset < ftrace['startpos']:
                    ftrace['startpos'] = offset
                if endpos > ftrace['endpos']:
                    ftrace['endpos'] = endpos

                # Log first read/write and all non-contiguous read/writes
                # Cluster contiguous read/writes into one log entry

                if ftrace['count'] == 0 \
                        or offset != currentpos:
                    msg = "(%s:%s)" % (ftrace['startpos'], ftrace['endpos'])
                    ftrace['logstatus'] = project_log(configuration,
                                                      'sftp',
                                                      user_name,
                                                      ip_addr,
                                                      log_action,
                                                      path=path,
                                                      details=msg,
                                                      )
                    ftrace['startpos'] = ftrace['endpos']
                    ftrace['count'] = 1
                else:
                    ftrace['count'] += 1

                # Only invoke read/write operation if log was successful

                if ftrace['logstatus']:
                    try:
                        result = method(self, *method_args, **method_kwargs)
                    except Exception as exc:
                        result = None
                        msg = "(%d:%d): %s" \
                            % (offset, offset+length, exc)
                        logger.error("%s failed: '%s': %s"
                                     % (operation, path, msg))
                        project_log(configuration,
                                    'sftp',
                                    user_name,
                                    ip_addr,
                                    log_action,
                                    failed=True,
                                    path=path,
                                    details=msg,
                                    )

                # Verify that the calculated and real file end positions match
                # TODO: This check might be removed

                file_endpos = -1
                if method.__name__ == "read":
                    file_endpos = self.readfile.tell()
                elif method.__name__ == "write":
                    file_endpos = self.writefile.tell()
                if file_endpos != endpos:
                    msg = "GDP log calculated endpos: %s != " \
                        % endpos \
                        + " file endpos: %s, '%s'" % \
                        (file_endpos, self.sftpserver._get_fs_path(path))
                    logger.warning(msg)

            # close

            elif operation == "close":

                # Invoke 'close' to flush outstanding file writes

                try:
                    result = method(self, *method_args, **method_kwargs)
                except Exception as exc:
                    result = None
                    logger.error("%s failed: '%s': %s"
                                 % (operation, path, exc))

                # After close flush pending read/write log entries

                for ftrace_type in self.valid_ftrace_types:
                    log_action = valid_log_actions.get(ftrace_type, None)
                    if log_action is None:
                        logger.error(
                            "Missing GDP log action for ftrace: '%s'"
                            % ftrace_type)
                    else:
                        ftrace = self.ftrace[ftrace_type]
                        if ftrace['count'] > 1:
                            msg = "(%s:%s)" % (
                                ftrace['startpos'], ftrace['endpos'])
                            project_log(configuration,
                                        'sftp',
                                        user_name,
                                        ip_addr,
                                        log_action,
                                        path=path,
                                        details=msg,
                                        )
            return result
        return _impl

    def stat(self):
        """Handle operations of same name"""
        # self.logger.debug("SFTPHandle stat on %s" % getattr(self, "path",
        #                                                    "unknown"))
        active = getattr(self, 'active')
        file_obj = getattr(self, active)
        return paramiko.SFTPAttributes.from_stat(os.fstat(file_obj.fileno()),
                                                 getattr(self, "path",
                                                         "unknown"))

    def chattr(self, attr):
        """Handle operations of same name"""
        path = getattr(self, "path", "unknown")
        # self.logger.debug("SFTPHandle chattr %s on path %s" %
        #                  (repr(attr), [path]))
        return self.sftpserver._chattr(path, attr, self)

    @__gdp_log
    def read(self, offset, length):
        """Handle operations of same name"""
        path = getattr(self, "path", "unknown")
        #self.logger.debug("read %db @%d of %s" % (length, offset, [path]))
        try:
            return super(SFTPHandle, self).read(offset, length)
        except Exception as exc:
            self.logger.error("read %db @%d of %s failed: %s" %
                              (length, offset, [path], exc))
            raise exc

    @__gdp_log
    @__workflow_history_log
    def write(self, offset, data):
        """Handle operations of same name"""
        path = getattr(self, "path", "unknown")
        #self.logger.debug("write %db @%d of %s" % (len(data), offset, [path]))
        try:
            return super(SFTPHandle, self).write(offset, data)
        except Exception as exc:
            self.logger.error("write %db @%d of %s failed: %s" %
                              (len(data), offset, [path], exc))
            raise exc

    @__gdp_log
    def close(self):
        """Handle operations of same name"""
        return super(SFTPHandle, self).close()


class SimpleSftpServer(paramiko.SFTPServerInterface):
    """Custom SFTP server with chroot and MiG access restrictions.

    Includes basic error handling and robustness, but could be extended to
    deliver more precise error codes on common errors.

    IMPORTANT: Instances of this class generally live in background threads.
    This means that any unhandled exceptions will silently pass. Thus it is
    very important to conservatively catch and log all potential exceptions
    when debugging to avoid excessive loss of hair :-)
    """

    # Init internal args so that they can be overriden on class before init
    # when instantiation needs to be implicit.

    configuration = None
    conf = None
    logger = None
    transport = None
    root = None
    ip_addr = None
    src_port = None

    def __init__(self, server, *largs, **kwargs):
        """Init"""
        paramiko.SFTPServerInterface.__init__(self, server)
        # From openssh subsys global configuration and logger may be missing
        global configuration, logger
        if self.configuration:
            configuration = self.configuration
        if self.logger is None:
            logger = configuration.logger
            self.logger = logger
        else:
            logger = self.logger

        if self.conf is None:
            conf = kwargs.get('conf', {})
            # Fall back to daemon_conf from configuration
            if not conf and configuration:
                conf = configuration.daemon_conf
            self.conf = conf
        conf = self.conf
        # logger.debug('logger available in SimpleSftpServer init')
        if self.transport is None:
            self.transport = kwargs.get('transport', None)
        # logger.debug('using transport: %s' % self.transport)
        if self.root is None:
            self.root = kwargs.get('fs_root', None)
            if not self.root:
                self.root = conf.get('root_dir', None)
        # logger.debug('using root: %s' % self.root)
        self.chroot_exceptions = conf.get('chroot_exceptions', keyword_auto)
        self.chmod_exceptions = conf.get('chmod_exceptions', [])
        # For stand-alone paramiko servers the active user is in transport,
        # where as for paramiko subsys in openssh it is in USER env.
        if self.transport:
            # IMPORTANT: use already authenticated login username rather than
            # untrusted transport.get_username() here
            # logger.debug('extract authenticated user from server')
            self.user_name = server.get_authenticated_user()
            src_ip, src_port = self.transport.getpeername()
            self.ip_addr = src_ip
            self.src_port = int(src_port)
            logger.debug('setting up session for %s from %s:%s' %
                         (self.user_name, self.ip_addr, self.src_port))
        else:
            # logger.debug('active env: %s' % os.environ)
            username = force_native_str(os.environ.get('USER', 'INVALID'))
            logger.debug('refresh user entry for %s' % username)
            # Either of user, job and share keys may have changed
            daemon_conf = self.conf
            update_sftp_login_map(daemon_conf, username,
                                  password=True, key=True)
            self.user_name = username

            # Env holds client info in 'SSH_CLIENT' as 'a.b.c.d rport lport'
            ssh_client = force_native_str(os.environ.get('SSH_CLIENT', 'NONE'))
            # Zero-pad to make sure extraction fails gracefully if missing
            ssh_client += ' 0 0'
            src_ip, src_port = ssh_client.split()[0:2]
            self.ip_addr = src_ip
            self.src_port = int(src_port)

        # logger.debug('auth user is %s' % self.user_name)

        # logger.debug('update user chroot based on login map')

        # list of User login objects for user_name

        entries = login_map_lookup(conf, self.user_name)
        if not entries:
            raise Exception("user not found in login map!")
        for entry in entries:
            if entry.chroot:
                # TODO: we used to force utf8 here - where should it take place now?
                self.root = force_native_str("%s/%s" % (self.root, entry.home))
                break
        # logger.debug('auth user chroot is %s' % self.root)

    def _abort_on_missing_client_var(self, caller):
        """Simple helper to abort further action in session_started and
        session_ended if any of the required client variables like user_name,
        ip_addr or src_port are unset. Logs the caller and values first and
        then raises ValueError if so.
        """
        client_vars = {'user_name': self.user_name, 'ip_addr': self.ip_addr,
                       'src_port': self.src_port}
        for name in client_vars:
            if not client_vars[name]:
                msg = "abort %s: missing mandatory %r value" % (caller, name)
                details = "user_name %r, ip_addr %r, src_port %r" % \
                    (self.user_name, self.ip_addr, self.src_port)
                logger.error("%s : %s" % (msg, details))
                raise ValueError(msg)

    def session_started(self):
        """Perform any necessary setup before handling callbacks from SFTP
        operations.
        """
        global configuration, logger
        username, client_ip = self.user_name, self.ip_addr
        tcp_port = self.src_port
        max_sftp_sessions = configuration.user_sftp_max_sessions
        # We skip track session on reject with e.g. disabled or expired account
        self._session_tracked = False
        exceeded_rate_limit = False
        exceeded_max_sessions = False
        invalid_username = False
        account_accessible = False
        valid_twofa = False
        if self.transport is None:
            proto = 'sftp-subsys'
        else:
            proto = 'sftp'
        if configuration.site_twofactor_strict_address:
            enforce_address = client_ip
        else:
            enforce_address = None

        # logger.debug("%r session started for %s from %s:%s"
        #             % (proto, username, client_ip, tcp_port))
        self._abort_on_missing_client_var('session_started')

        # TODO: merge sftp and sftp-subsys auth validation into single helper?
        # NOTE: proto == 'sftp' is handled in _validate_authentication
        if proto == 'sftp-subsys':
            #logger.debug("sftp-subsys env is: %s" % os.environ)
            # TODO: can we extract actual auth method somehow instead of this
            #       dummy 'session' workaround when auth is handled by sshd?
            authtype = os.environ.get('AUTHTYPE', 'session')
            # NOTE: emulate native auth case for same 2fa check
            valid_key, valid_password = True, True
            active_count = active_sessions(configuration, proto, username)
            # validate rate_limit, max_sessions and twofactor session
            if hit_rate_limit(configuration, proto, client_ip, username,
                              max_user_hits=default_max_user_hits):
                exceeded_rate_limit = True
            # NOTE: we delay dead session cleanup until limit is hit
            elif max_sftp_sessions > 0 and active_count >= max_sftp_sessions \
                    and active_count - \
                    len(expire_dead_sessions(configuration, proto, username)) \
                    >= max_sftp_sessions:
                exceeded_max_sessions = True
            elif not default_username_validator(configuration, username):
                invalid_username = True
            else:
                # NOTE: subsys+key skips PAM and thus needs access check here
                if check_account_accessible(configuration, username, proto):
                    account_accessible = True
                if (valid_key and check_twofactor_session(
                    configuration, username, enforce_address, 'sftp-key')) \
                    or (valid_password and check_twofactor_session(
                        configuration, username, enforce_address, 'sftp-pw')):
                    valid_twofa = True
            (authorized, disconnect) = validate_auth_attempt(
                configuration,
                proto,
                authtype,
                username,
                client_ip,
                tcp_port,
                authtype_enabled=True,
                valid_auth=True,
                invalid_username=invalid_username,
                account_accessible=account_accessible,
                valid_twofa=valid_twofa,
                exceeded_rate_limit=exceeded_rate_limit,
                exceeded_max_sessions=exceeded_max_sessions,
                user_abuse_hits=default_user_abuse_hits,
                proto_abuse_hits=default_proto_abuse_hits,
                max_secret_hits=default_max_secret_hits,
            )
            if not authorized or disconnect:
                # NOTE: validate_auth_attempt will log why
                raise Exception("reject client based on failed session checks")

        # Track session
        active_session = track_open_session(configuration, proto, username,
                                            client_ip, tcp_port,
                                            authorized=True)
        if not active_session:
            raise Exception("failed to track open session")
        self._session_tracked = True
        # Open GDP project
        if configuration.site_enable_gdp:
            # NOTE: In GDP we do not distinguish between 'sftp' and
            #       'sftp-subsys'
            (gdp_project, msg) = project_open(configuration, 'sftp', client_ip,
                                              username)
            if not gdp_project:
                send_system_notification(username, ['SFTP', 'ERROR'], msg,
                                         configuration)
                logger.error(msg)
                raise Exception(msg)

    def session_ended(self):
        """The SFTP server session has just ended, either cleanly or via an
        exception. Perform any necessary cleanup before this object is
        destroyed.
        """
        global configuration, logger
        username, client_ip = self.user_name, self.ip_addr
        tcp_port = self.src_port
        if self.transport is None:
            proto = 'sftp-subsys'
        else:
            proto = 'sftp'

        # logger.debug("%r session ended for %s from %s:%s"
        #             % (proto, username, client_ip, tcp_port))

        # No session tracking if e.g. refused with expired/disabled account
        if not self._session_tracked:
            logger.info("no tracked %s session for refused try by %r from %s:%s"
                        % (proto, username, client_ip, tcp_port))
            return

        self._abort_on_missing_client_var('session_ended')

        status = track_close_session(configuration, proto, username, client_ip,
                                     tcp_port)
        if not status:
            logger.error("failed to track close session")
        active_count = active_sessions(configuration, proto, username)
        logger.info("remaining %d active sessions for %s" % (active_count,
                                                             username))

        if configuration.site_enable_gdp and active_count == 0:
            # NOTE: In GDP we do not distinguish
            #       between 'sftp' and 'sftp-subsys'
            project_close(configuration, 'sftp', client_ip, username)

    def __gdp_log(self, operation, path, dst_path=None, flags=None,
                  error=None):
        """GDP logger helper function"""
        if not configuration.site_enable_gdp:
            return True
        logger = configuration.logger
        result = False
        skiplog = False
        log_action = ''
        log_msg = None
        log_error = False

        # open

        if operation == "open":
            if flags is None:
                logger.error("Missing GDP log flags")
                return False
            if path is None:
                logger.error("Missing GDP log path")
                return False
            if flags & os.O_CREAT:
                log_action = 'created'
            elif flags & (os.O_WRONLY |
                          os.O_TRUNC):
                log_action = 'truncated'
            elif flags == os.O_RDONLY:
                # NOTE: os.O_RDONLY == 0
                log_action = 'accessed'
            else:
                log_action = 'modified'

        # list_folder

        elif operation == "list_folder":
            if path is None:
                logger.error("Missing GDP log path")
                return False
            log_action = 'accessed'

        # remove

        elif operation == "remove":
            if path is None:
                logger.error("Missing GDP log path")
                return False
            log_action = 'deleted'

        # rename

        elif operation == "rename":
            if path is None:
                logger.error("Missing GDP log path")
                return False
            if dst_path is None:
                logger.error("Missing GDP log dst_path")
                return False
            log_action = 'moved'

        # mkdir

        elif operation == "mkdir":
            if path is None:
                logger.error("Missing GDP log path")
                return False
            log_action = 'created'

        # rmdir

        elif operation == "rmdir":
            if path is None:
                logger.error("Missing GDP log path")
                return False
            log_action = 'deleted'

        # Currently we do not add failed message directly
        # to log as it might contain user information

        if error is not None:
            log_error = True
            log_msg = error

        # Log message

        if skiplog:
            result = True
        elif log_action:
            result = project_log(configuration,
                                 'sftp',
                                 self.user_name,
                                 self.ip_addr,
                                 log_action,
                                 failed=log_error,
                                 path=path,
                                 dst_path=dst_path,
                                 details=log_msg,
                                 )
        return result

    # Use shared daemon fs helper functions

    def _get_fs_path(self, sftp_path):
        """Wrap helper"""
        try:
            # self.logger.debug("get_fs_path: %s" % [sftp_path])
            abs_path = os.path.abspath(os.path.join(self.root,
                                                    sftp_path.lstrip(os.sep)))
            # self.logger.debug("get_fs_path abs: %s" % [abs_path])
            reply = get_fs_path(configuration, abs_path, self.root,
                                self.chroot_exceptions)
            # self.logger.debug("get_fs_path returns: %s :: %s" % ([sftp_path],
            #                                                      [reply]))
            return reply
        except Exception as exc:
            self.logger.error("get_fs_path failed: %s" % exc)
            # import traceback
            # self.logger.debug("Traceback:\n%s" % traceback.format_exc())
            raise exc

    def _strip_root(self, sftp_path):
        """Wrap helper"""
        # self.logger.debug("strip_root: %s" % sftp_path)
        reply = strip_root(configuration, sftp_path, self.root,
                           self.chroot_exceptions)
        # self.logger.debug("strip_root returns: %s :: %s" % (sftp_path,
        #                                                     reply))
        return reply

    def _acceptable_chmod(self, sftp_path, mode):
        """Wrap helper"""
        # self.logger.debug("acceptable_chmod: %s" % sftp_path)
        reply = acceptable_chmod(sftp_path, mode, self.chmod_exceptions)
        if not reply:
            self.logger.warning("acceptable_chmod failed: %s %s %s" %
                                (sftp_path, mode, self.chmod_exceptions))
        # self.logger.debug("acceptable_chmod returns: %s :: %s" % \
        #                      (sftp_path, reply))
        return reply

    def _chattr(self, path, attr, sftphandle=None):
        """Handle chattr for SimpleSftpServer and SFTPHandle"""
        file_obj = None
        # TODO: should we still force utf8 and if so where?
        # path = force_utf8(path)
        # Paramiko seems to handle *native* strings correctly across py version
        path = force_native_str(path)
        # self.logger.debug("_chattr %s" % [path])
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('chattr %s: %s' % ([path], [err]))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.warning("chattr on missing path %s :: %s" %
                                ([path], [real_path]))
            return paramiko.SFTP_NO_SUCH_FILE
        # self.logger.debug("_chattr %s check write acces" % [path])
        # TODO: let non-modifying requests through here?
        if not check_write_access(real_path):
            self.logger.warning('chattr on read-only path %s :: %s' %
                                ([path], [real_path]))
            return paramiko.SFTP_PERMISSION_DENIED
        #self.logger.debug("_chattr %s activate" % [path])
        if sftphandle is not None:
            active = getattr(sftphandle, 'active')
            file_obj = getattr(sftphandle, active)

        # Prevent users from messing with most attributes as such.
        # We end here on chmod too, so pass any mode change requests there and
        # silently ignore them otherwise. It turns out to have caused problems
        # if we rejected those other attribute changes in the past but it may
        # not be a problem anymore. If it ain't broken...
        # self.logger.debug("chattr %s for path %s :: %s" %
        #                  (repr(attr), [path], [real_path]))
        ignored = True
        if getattr(attr, 'st_mode', None) is not None and attr.st_mode > 0:
            # self.logger.debug('_chattr st_mode: %s' % attr.st_mode)
            ignored = False
            # self.logger.debug("chattr %s forwarding for path %s :: %s" %
            #                  (repr(attr), [path], [real_path]))
            return self._chmod(path, attr.st_mode, sftphandle)
        if getattr(attr, 'st_atime', None) is not None or \
                getattr(attr, 'st_mtime', None) is not None:
            # self.logger.debug('_chattr st_atime or st_mtime: %s' % [path])
            ignored = False
            change_atime = getattr(attr, 'st_atime',
                                   os.path.getatime(real_path))
            change_mtime = getattr(attr, 'st_mtime',
                                   os.path.getmtime(real_path))
            # self.logger.debug('_chattr st_atime: %s, st_mtime: %s' %
            #                  (change_atime, change_mtime))
            os.utime(real_path, (change_atime, change_mtime))
            self.logger.info("changed times %s %s for path %s :: %s" %
                             (change_atime, change_mtime, [path], [real_path]))
        if getattr(attr, 'st_size', None) is not None:
            # self.logger.debug('_chattr st_size: %s' % attr.st_size)
            ignored = False
            # self.logger.debug("_chattr truncate %s" % [path])
            if file_obj is None:
                # We must open file to truncate as there is no os.truncate
                try:
                    tmp_fd = open(real_path, 'r+b')
                    os.ftruncate(tmp_fd.fileno(), attr.st_size)
                    tmp_fd.close()
                except Exception as exc:
                    self.logger.error("truncate %s to %s failed: %s" %
                                      ([real_path], attr.st_size, exc))
            else:
                os.ftruncate(file_obj.fileno(), attr.st_size)
            self.logger.info("truncated file: %s to size: %s" %
                             ([real_path], attr.st_size))
        # self.logger.debug('_chattr check mode 0: %s ignored %s st mode %s' %
        #                  ([path], ignored, getattr(attr, 'st_mode', -1)))
        # NOTE: chmod 0 PATH are very common - silently ignore to reduce noise
        #       st_mode may be 0 or None depending on python version.
        if ignored and getattr(attr, 'st_mode', None) is not None and attr.st_mode > 0:
            self.logger.warning("chattr %s ignored on path %s :: %s" %
                                (repr(attr), [path], [real_path]))
        # self.logger.debug("_chattr %s complete" % [path])
        return paramiko.SFTP_OK

    def _chmod(self, path, mode, sftphandle=None):
        """Handle chmod for SimpleSftpServer and SFTPHandle"""
        file_obj = None
        # TODO: where should we force utf8 now?
        # path = force_utf8(path)
        # self.logger.debug("_chmod %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('chmod %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("chmod on missing path %s :: %s" % (path,
                                                                  real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        if not check_write_access(real_path):
            self.logger.warning('chmod on read-only path %s :: %s' %
                                (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if sftphandle is not None:
            active = getattr(sftphandle, 'active')
            file_obj = getattr(sftphandle, active)

        # Only allow change of mode on files and only outside chmod_exceptions
        if self._acceptable_chmod(real_path, mode):
            # Only allow permission changes that won't give excessive access
            # or remove own access.
            if os.path.isdir(path):
                new_mode = (mode & 0o775) | 0o750
            else:
                new_mode = (mode & 0o775) | 0o640
            # self.logger.debug("chmod %s (%s) without damage on %s :: %s" %
            #                  (new_mode, mode, path, real_path))
            try:
                if file_obj is None:
                    os.chmod(real_path, new_mode)
                else:
                    os.fchmod(file_obj.fileno(), new_mode)
            except Exception as err:
                self.logger.error("chmod %s (%s) failed on path %s :: %s %s" %
                                  (new_mode, mode, path, real_path, err))
                return paramiko.SFTP_PERMISSION_DENIED
            return paramiko.SFTP_OK
        # Prevent users from messing up access modes
        self.logger.warning("chmod %s rejected on path %s :: %s" % (mode, path,
                                                                    real_path))
        return paramiko.SFTP_OP_UNSUPPORTED

    # Public interface functions

    def open(self, path, flags, attr):
        """Handle operations of same name"""
        # TODO: where should we force utf8 now?
        # path = force_utf8(path)
        # self.logger.debug('open %s' % [path])
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('open %s: %s' % ([path], [err]))
            return paramiko.SFTP_PERMISSION_DENIED
        except Exception as exc:
            self.logger.warning('open %s: %s' % ([path], [exc]))
            return paramiko.SFTP_PERMISSION_DENIED
        # self.logger.debug("open on %s :: %s (%s %s)" %
        #                   ([path], [real_path], repr(flags), repr(attr)))
        if not (flags & os.O_CREAT) and not os.path.exists(real_path):
            self.logger.error("open existing file on missing path %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        if (flags & (os.O_CREAT |
                     os.O_RDWR |
                     os.O_WRONLY |
                     os.O_APPEND |
                     os.O_TRUNC)) \
                and not check_write_access(real_path, parent_dir=True):
            self.logger.error("open for modify on read-only path %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if not self.__gdp_log("open", path, flags=flags):
            return paramiko.SFTP_FAILURE
        # self.logger.debug("open SFTPHandle on %s" % [path])
        handle = SFTPHandle(flags, sftpserver=self)
        setattr(handle, 'real_path', real_path)
        setattr(handle, 'path', path)
        setattr(handle, 'user_name', self.user_name)
        setattr(handle, 'ip_addr', self.ip_addr)
        # self.logger.debug("Prepared SFTPHandle on %s" % [path])
        try:
            # Fake OS level open call first to avoid most flag parsing.
            # This is necessary to make things like O_CREAT, O_EXCL and
            # O_TRUNCATE consistent with the simple mode strings.
            fake = os.open(real_path, flags, 0o644)
            os.close(fake)
            # Now fake our own chattr to set any requested mode and times
            # self.logger.debug("fake chattr on %s :: %s (%s %s)" %
            #                   ([path], [real_path], repr(flags), repr(attr)))
            self.chattr(path, attr)
            # self.logger.debug("chattr done on %s :: %s (%s %s)" %
            #                   ([path], [real_path], repr(flags), repr(attr)))
            mode = flags_to_mode(flags)
            # NOTE: force binary here to avoid unicode in py3
            mode += 'b'
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
            # self.logger.debug("open done %s :: %s (%s %s)" %
            #                   ([path], [real_path], handle, mode))
            return handle
        except Exception as err:
            self.logger.error("open on %s :: %s (%s) failed: %s" %
                              ([path], [real_path], mode, [err]))
            self.__gdp_log("open", path, flags=flags, error=err)
            self.logger.error("open on %s :: %s (%s) failed: %s" %
                              ([path], [real_path], mode, [err]))
            return paramiko.SFTP_FAILURE

    def list_folder(self, path):
        """Handle operations of same name"""
        # self.logger.debug('list_folder %s' % [path])
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('list_folder %s: %s' % ([path], [err]))
            return paramiko.SFTP_PERMISSION_DENIED
        except Exception as exc:
            self.logger.warning('list_folder %s: %s' % ([path], [exc]))
            return paramiko.SFTP_PERMISSION_DENIED
        # self.logger.debug("list_folder %s :: %s" % ([path], [real_path]))
        reply = []
        if not os.path.exists(real_path):
            self.logger.warning("list_folder on missing path %s :: %s" %
                                ([path], [real_path]))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            files = os.listdir(real_path)
        except Exception as err:
            self.logger.error("list_folder on %s :: %s failed: %s" %
                              ([path], [real_path], [err]))
            return paramiko.SFTP_FAILURE
        if not self.__gdp_log("list_folder", path):
            return paramiko.SFTP_FAILURE
        self.logger.debug("list_folder files :: %s" % files)
        for filename in files:
            # self.logger.debug("list_folder for %s" % filename)
            if invisible_path(filename):
                continue
            #full_name = ("%s/%s" % (real_path, filename)).replace("//", "/")
            full_name = os.path.join(real_path,
                                     filename.lstrip(os.sep)).replace("//", "/")
            self.logger.debug("list_folder stat %s" % [full_name])
            # stat may fail e.g. if filename is a stale storage mount point
            try:
                # NOTE: filename must be on native string format
                reply.append(paramiko.SFTPAttributes.from_stat(
                    os.stat(full_name),
                    force_native_str(self._strip_root(filename))))
            except Exception as err:
                self.logger.warning("list_folder %s: stat on %s failed: %s" %
                                    ([path], [full_name], [err]))
        # self.logger.debug("list_folder %s reply %s" % ([path], [reply]))
        return reply

    def stat(self, path):
        """Handle operations of same name"""
        # TODO: where should we force utf8 now?
        # path = force_utf8(path)
        # self.logger.debug('stat %s' % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('stat %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        except Exception as exc:
            self.logger.warning('stat %s: %s' % ([path], [exc]))
            return paramiko.SFTP_PERMISSION_DENIED
        # self.logger.debug("stat %s :: %s" % (path, real_path))
        # for consistency with lstat
        if not os.path.exists(real_path):
            # It's common to check file existence with stat so don't warn
            # self.logger.debug("stat on missing path %s :: %s" %
            #                  (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)
        except Exception as err:
            self.logger.error("stat on %s :: %s failed: %s" %
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE

    def lstat(self, path):
        """Handle operations of same name"""
        # TODO: where should we force utf8 now?
        # path = force_utf8(path)
        # self.logger.debug('lstat %s' % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('lstat %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        # self.logger.debug("lstat %s :: %s" % (path, real_path))
        if not os.path.lexists(real_path):
            # It's common to check file existence with stat so no warning here
            # self.logger.debug("lstat on missing path %s :: %s" %
            #                  (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        # self.logger.debug('return lstat %s' % path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)
        except Exception as err:
            self.logger.error("lstat on %s :: %s failed: %s" %
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE

    def remove(self, path):
        """Handle operations of same name"""
        # TODO: where should we force utf8 now?
        # path = force_utf8(path)
        # self.logger.debug("remove %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('remove %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        if not check_write_access(real_path):
            self.logger.warning('remove on read-only path %s :: %s' %
                                (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        # self.logger.debug("remove %s :: %s" % (path, real_path))
        # Prevent removal of special files - link to vgrid dirs, etc.
        if os.path.islink(real_path):
            self.logger.error("remove rejected on link path %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if in_vgrid_share(configuration, real_path) == path.lstrip(os.sep):
            self.logger.error("remove rejected on vgrid root %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if is_vgrid_parent_placeholder(configuration, path.lstrip(os.sep),
                                       real_path, False):
            self.logger.error("remove rejected on vgrid parent placeholder %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("remove on missing path %s :: %s" % (path,
                                                                   real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        if not self.__gdp_log("remove", path):
            return paramiko.SFTP_FAILURE
        try:
            os.remove(real_path)
            self.logger.info("removed %s :: %s" % (path, real_path))
            return paramiko.SFTP_OK
        except Exception as err:
            self.__gdp_log("remove", path, error=err)
            self.logger.error("remove on %s :: %s failed: %s" %
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE

    def rename(self, oldpath, newpath):
        """Handle operations of same name"""
        # TODO: where should we force utf8 now?
        # oldpath = force_utf8(oldpath)
        # newpath = force_utf8(newpath)
        # self.logger.debug("rename %s %s" % (oldpath, newpath))
        try:
            real_oldpath = self._get_fs_path(oldpath)
        except ValueError as err:
            self.logger.warning('rename %s %s: %s' % (oldpath, newpath, err))
            return paramiko.SFTP_PERMISSION_DENIED
        # Prevent removal of special files - link to vgrid dirs, etc.
        if os.path.islink(real_oldpath):
            self.logger.error("rename on link src %s :: %s" % (oldpath,
                                                               real_oldpath))
            return paramiko.SFTP_PERMISSION_DENIED
        if in_vgrid_share(configuration, real_oldpath) == oldpath.lstrip(os.sep):
            self.logger.error("rename on vgrid share root %s :: %s" % (oldpath,
                                                                       real_oldpath))
            return paramiko.SFTP_PERMISSION_DENIED
        if is_vgrid_parent_placeholder(configuration, oldpath.lstrip(os.sep),
                                       real_oldpath, False):
            self.logger.error("rename on vgrid parent placeholder %s :: %s"
                              % (oldpath, real_oldpath))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_oldpath):
            self.logger.error("rename on missing path %s :: %s" %
                              (oldpath, real_oldpath))
            return paramiko.SFTP_NO_SUCH_FILE
        if not check_write_access(real_oldpath):
            self.logger.warning('move on read-only old path %s :: %s' %
                                (oldpath, real_oldpath))
            return paramiko.SFTP_PERMISSION_DENIED
        real_newpath = self._get_fs_path(newpath)
        if not check_write_access(real_newpath, parent_dir=True):
            self.logger.warning('move on read-only new path %s :: %s' %
                                (newpath, real_newpath))
            return paramiko.SFTP_PERMISSION_DENIED
        if not self.__gdp_log("rename", oldpath, dst_path=newpath):
            return paramiko.SFTP_FAILURE
        try:
            # Use shutil move to allow move to other file system like external
            # storage mounted file systems
            shutil.move(real_oldpath, real_newpath)
            self.logger.info("renamed %s to %s :: %s to %s"
                             % (oldpath, newpath, real_oldpath, real_newpath))
            return paramiko.SFTP_OK
        except Exception as err:
            self.__gdp_log("rename", oldpath, dst_path=newpath,
                           error=err)
            self.logger.error("rename on %s :: %s failed: %s" %
                              (real_oldpath, real_newpath, err))
            return paramiko.SFTP_FAILURE

    def mkdir(self, path, mode):
        """Handle operations of same name"""
        # TODO: where should we force utf8 now?
        # path = force_utf8(path)
        # self.logger.debug("mkdir %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('mkdir %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        if os.path.isdir(real_path):
            self.logger.warning("mkdir on existing directory %s :: %s" %
                                (path, real_path))
            return paramiko.SFTP_FAILURE
        if not check_write_access(real_path, parent_dir=True):
            self.logger.warning('mkdir on read-only path %s :: %s' %
                                (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if not self.__gdp_log("mkdir", path):
            return paramiko.SFTP_FAILURE
        try:
            # Force MiG default mode
            os.mkdir(real_path, 0o755)
            self.logger.info("made dir %s :: %s" % (path, real_path))
            return paramiko.SFTP_OK
        except Exception as err:
            self.__gdp_log("mkdir", path, error=err)
            self.logger.error("mkdir on %s :: %s failed: %s" %
                              (path, real_path, err))
            return paramiko.SFTP_FAILURE

    def rmdir(self, path):
        """Handle operations of same name"""
        # TODO: where should we force utf8 now?
        # path = force_utf8(path)
        # self.logger.debug("rmdir %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('rmdir %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        # Prevent removal of special files - link to vgrid dirs, etc.
        if os.path.islink(real_path):
            self.logger.error("rmdir rejected on link path %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if in_vgrid_share(configuration, real_path) == path.lstrip(os.sep):
            self.logger.error("rmdir rejected on vgrid share root %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if is_vgrid_parent_placeholder(configuration, path.lstrip(os.sep),
                                       real_path, False):
            self.logger.error("rmdir rejected on vgrid parent placeholder %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.warning("rmdir on missing path %s :: %s" % (path,
                                                                    real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        if not check_write_access(real_path):
            self.logger.warning('rmdir on read-only path %s :: %s' %
                                (path, real_path))
            return paramiko.SFTP_PERMISSION_DENIED
        if not self.__gdp_log("rmdir", path):
            return paramiko.SFTP_FAILURE
        # self.logger.debug("rmdir on path %s :: %s" % (path, real_path))
        try:
            os.rmdir(real_path)
            self.logger.info("removed dir %s :: %s" % (path, real_path))
            return paramiko.SFTP_OK
        except Exception as err:
            self.__gdp_log("rmdir", path, error=err)
            self.logger.error("rmdir on %s :: %s failed: %s" %
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
        # TODO: where should we force utf8 now?
        # path = force_utf8(path)
        # self.logger.debug("readlink %s" % path)
        try:
            real_path = self._get_fs_path(path)
        except ValueError as err:
            self.logger.warning('readlink %s: %s' % (path, err))
            return paramiko.SFTP_PERMISSION_DENIED
        if not os.path.exists(real_path):
            self.logger.error("readlink on missing path %s :: %s" %
                              (path, real_path))
            return paramiko.SFTP_NO_SUCH_FILE
        try:
            return self._strip_root(os.readlink(path))
        except Exception as err:
            self.logger.warning("readlink on %s :: %s failed: %s" %
                                (path, real_path, err))
            return paramiko.SFTP_FAILURE

    def symlink(self, target_path, path):
        """Handle operations of same name"""
        # TODO: where should we force utf8 now?
        # target_path = force_utf8(target_path)
        # path = force_utf8(path)
        # self.logger.debug('symlink %s %s' % (target_path, path))
        # Prevent users from creating symlinks for security reasons
        self.logger.error("symlink rejected on path %s :: %s" % (target_path,
                                                                 path))
        return paramiko.SFTP_OP_UNSUPPORTED


class SimpleSSHServer(paramiko.ServerInterface):
    """Custom SSH server with multi pub key support"""

    # Init internal args so that they can be overriden on class before init
    # when instantiation needs to be implicit.

    conf = None
    logger = None
    client_addr = None
    transport = None

    def __init__(self, *largs, **kwargs):
        paramiko.ServerInterface.__init__(self)
        conf = kwargs.get('conf', {})
        if not conf:
            conf = configuration.daemon_conf
        self.conf = conf
        self.logger = logger
        self.event = threading.Event()
        self.client_addr = kwargs.get('client_addr')
        self.authenticated_user = None
        self.allow_password = conf.get('allow_password', True)
        self.allow_publickey = conf.get('allow_publickey', True)
        self.transport = kwargs.get('transport')

    def _validate_authentication(self, username, password=None, key=None):
        """Authorize users and log auth attempts.
        Key and password auth against usermap.

        The following is checked before granting auth:
        1) Valid username
        2) Valid user (Does user exist with enabled SFTP)
        3) Account is active and not expired
        4) Valid 2FA session (if 2FA is enabled)
        5) Hit rate limit (Too many auth attempts)
        6) Max sessions (Too many open sessions)
        7) Valid password (if password enabled)
        8) Valid key (if key enabled)
        """
        hashed_secret = None
        disconnect = False
        strict_password_policy = True
        # Support password legacy policy during log in for transition periods
        allow_legacy = True
        password_offered = None
        key_offered = None
        password_enabled = False
        key_enabled = False
        invalid_username = False
        invalid_user = False
        account_accessible = False
        valid_key = False
        valid_password = False
        valid_twofa = False
        exceeded_rate_limit = False
        exceeded_max_sessions = False
        update_key_map = False
        update_password_map = False
        daemon_conf = self.conf
        # NOTE: keep username on native form in general
        username = force_native_str(username)
        client_ip = self.client_addr[0]
        tcp_port = self.client_addr[1]
        active_count = active_sessions(configuration, 'sftp', username)
        max_sftp_sessions = daemon_conf['auth_limits']['max_sftp_sessions']
        max_user_hits = daemon_conf['auth_limits']['max_user_hits']
        user_abuse_hits = daemon_conf['auth_limits']['user_abuse_hits']
        proto_abuse_hits = daemon_conf['auth_limits']['proto_abuse_hits']
        max_secret_hits = daemon_conf['auth_limits']['max_secret_hits']

        authtype = ''
        if key is not None:
            authtype = 'publickey'
        elif password is not None:
            authtype = 'password'
        elif (key is None and password is None) \
                or (key is not None and password is not None):
            logger.error("Exactly one of key or password is expected")
            self.transport.close()
            return paramiko.AUTH_FAILED

        # For e.g. GDP we require all logins to match active 2FA session IP,
        # but otherwise user may freely switch net during 2FA lifetime.
        if configuration.site_twofactor_strict_address:
            enforce_address = client_ip
        else:
            enforce_address = None
        if hit_rate_limit(configuration, 'sftp', client_ip, username,
                          max_user_hits=max_user_hits):
            exceeded_rate_limit = True
        elif max_sftp_sessions > 0 and active_count >= max_sftp_sessions:
            # TODO: run expire_dead_sessions here like for subsys case?
            exceeded_max_sessions = True
        elif not default_username_validator(configuration, username):
            invalid_username = True
        else:
            if key is not None:
                update_key_map = True
                key_offered = key.get_base64()
                hashed_secret = key_offered
            if password is not None:
                update_password_map = True
                hash_cache = daemon_conf['hash_cache']
                # NOTE: keep password on native form in general
                password_offered = force_native_str(password)
                # IMPORTANT: pass a hash of password to register_auth_attempt
                # since we NEVER want to save passwords to disk. We base64
                # encode it before hashing for symmetry with how we do in PAM.
                # NOTE: base64 encode requires byte string and returns byte string
                hashed_secret = make_simple_hash(base64.b64encode(force_utf8(
                    password_offered)))
                # Only sharelinks should be excluded from strict password policy
                if possible_sharelink_id(configuration, username):
                    strict_password_policy = False
            update_sftp_login_map(daemon_conf, username,
                                  password=update_password_map,
                                  key=update_key_map)
            login_map = login_map_lookup(daemon_conf, username)
            if not login_map \
                    and not os.path.islink(
                        os.path.join(self.conf['root_dir'], username)):
                invalid_user = True
            elif check_account_accessible(configuration, username, 'sftp'):
                account_accessible = True
            for entry in login_map:
                if password is not None and entry.password is not None:
                    password_enabled = True
                    # NOTE: make sure allowed value is native string as well
                    password_allowed = force_native_str(entry.password)
                if key is not None and self.allow_publickey \
                        and entry.public_key is not None:
                    key_enabled = True
                    key_allowed = entry.public_key.get_base64()
                if (password_enabled or key_enabled) \
                        and entry.ip_addr is not None \
                        and entry.ip_addr != client_ip:
                    self.logger.warning(
                        "ignore login as %s with wrong IP: %s vs %s" %
                        (username, entry.ip_addr, client_ip))
                    continue
                if key_enabled and key_allowed == key_offered:
                    valid_key = True
                    break
                if password_enabled and check_password_hash(
                        configuration, 'sftp', username,
                        password_offered, password_allowed,
                        hash_cache, strict_password_policy, allow_legacy):
                    valid_password = True
                    break
            if (valid_key and check_twofactor_session(
                    configuration, username, enforce_address, 'sftp-key')) \
                or (valid_password and check_twofactor_session(
                    configuration, username, enforce_address, 'sftp-pw')):
                valid_twofa = True

        if authtype == 'publickey' \
                and not key_enabled \
                and not invalid_username \
                and not invalid_user \
                and account_accessible \
                and not exceeded_rate_limit:
            # Do not register missing SSH keys attempt
            # if everything else is valid
            (authorized, disconnect) = (False, False)
        else:
            # Update rate limits and write to auth log
            (authorized, disconnect) = validate_auth_attempt(
                configuration,
                'sftp',
                authtype,
                username,
                client_ip,
                tcp_port,
                secret=hashed_secret,
                invalid_username=invalid_username,
                invalid_user=invalid_user,
                account_accessible=account_accessible,
                valid_twofa=valid_twofa,
                authtype_enabled=(key_enabled or password_enabled),
                valid_auth=(valid_key or valid_password),
                exceeded_rate_limit=exceeded_rate_limit,
                exceeded_max_sessions=exceeded_max_sessions,
                user_abuse_hits=user_abuse_hits,
                proto_abuse_hits=proto_abuse_hits,
                max_secret_hits=max_secret_hits,
            )
        if disconnect:
            self.transport.close()
        if authorized:
            self.authenticated_user = username
            result = paramiko.AUTH_SUCCESSFUL
        else:
            result = paramiko.AUTH_FAILED

        return result

    def check_channel_request(self, kind, chanid):
        """Log connections"""
        # self.logger.debug("channel_request: %s, %s" % (kind, chanid))
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):
        """Password auth against usermap.

        Please note that we take serious steps to secure against password
        cracking, but that it _may_ still be possible to achieve with a big
        effort.

        Paranoid users / grid owners should not enable password access in the
        first place!
        """
        return self._validate_authentication(username, password=password)

    def check_auth_publickey(self, username, key):
        """Public key auth against usermap"""
        return self._validate_authentication(username, key=key)

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
        # TODO: is this correct behaviour?
        return True


def update_sftp_login_map(daemon_conf, username, password=False, key=False):
    """Update sftp login map"""

    changed_users, changed_jobs, changed_shares = [], [], []
    changed_shares, changed_jupyter_mounts = [], []

    # Either of user, sharelinks, jobs or jupyter may have changed
    if password or key:
        if possible_user_id(configuration, username) \
                or (configuration.site_enable_gdp
                    and possible_gdp_user_id(configuration, username)):
            _, changed_users = refresh_user_creds(configuration,
                                                  'sftp', username)
        if possible_sharelink_id(configuration, username):
            _, changed_shares = refresh_share_creds(configuration,
                                                    'sftp', username)
    if key:
        # Jobs and jupyter only use keys
        if possible_job_id(configuration, username):
            _, changed_jobs = refresh_job_creds(configuration,
                                                'sftp', username)
        if possible_jupyter_mount_id(configuration, username):
            _, changed_jupyter_mounts = refresh_jupyter_creds(
                configuration, 'sftp', username)
    # Now update login map for any changed credentials
    update_login_map(daemon_conf, changed_users, changed_jobs,
                     changed_shares, changed_jupyter_mounts)

    return daemon_conf


def accept_client(client, addr, root_dir, host_rsa_key, conf={}):
    """Handle a single client session"""
    # logger.debug("In session handler thread from %s %s" % (client, addr))

    window_size = conf.get('window_size', DEFAULT_WINDOW_SIZE)
    max_packet_size = conf.get('max_packet_size', DEFAULT_MAX_PACKET_SIZE)
    # NOTE: flexible native string StringIO supported on both python 2 and 3
    host_key_file = NativeStringIO(force_native_str(host_rsa_key))
    host_key = paramiko.RSAKey(file_obj=host_key_file)
    transport = paramiko.Transport(client, default_window_size=window_size,
                                   default_max_packet_size=max_packet_size)
    # Restrict transport to strong ciphers+kex+digests used in OpenSSH
    transport_security = transport.get_security_options()
    recommended_ciphers = STRONG_SSH_CIPHERS.split(',')
    available_ciphers = transport_security.ciphers
    strong_ciphers = [i for i in recommended_ciphers if i in available_ciphers]
    # logger.debug("TLS ciphers available %s, used %s" % (available_ciphers,
    #                                                    strong_ciphers))
    if strong_ciphers:
        transport_security.ciphers = strong_ciphers
    else:
        logger.warning("No strong TLS ciphers available!")
        logger.info("You need a recent paramiko for best security")
    # NOTE: paramiko doesn't yet implement strong modern kex algos - use legacy
    # A number of paramiko tickets indicate plans and interest for adding the
    # strong curve25519-sha256@libssh.org eventually, but progress looks
    # stalled. Until then our best alternative appears to be the legacy
    # diffie-hellman-group-exchange-sha256 fallback, which should be safe as
    # long as the moduli size tuning of e.g. ssh-audit is applied:
    # http://cert.europa.eu/static/WhitePapers/CERT-EU-SWP_16-002_Weaknesses%20in%20Diffie-Hellman%20Key%20v1_0.pdf
    recommended_kex = STRONG_SSH_KEXALGOS.split(',')
    fallback_kex = STRONG_SSH_LEGACY_KEXALGOS.split(',')
    available_kex = transport_security.kex
    strong_kex = [i for i in recommended_kex if i in available_kex]
    medium_kex = [i for i in fallback_kex if i in available_kex]
    # logger.debug("TLS kex available %s, used %s (or fallback to %s)" %
    #             (available_kex, strong_kex, medium_kex))
    if strong_kex:
        # logger.debug("Using only strong key exchange algorithms: %s" %
        #             ', '.join(strong_kex))
        transport_security.kex = strong_kex
    elif medium_kex:
        # logger.debug("Using only medium strength key exchange algorithms: %s" %
        #             ', '.join(medium_kex))
        transport_security.kex = medium_kex
    else:
        logger.warning("No strong TLS key exchange algorithm available!")
        logger.info("You need a recent paramiko for best security")
    recommended_digests = STRONG_SSH_MACS.split(',')
    fallback_digests = STRONG_SSH_LEGACY_MACS.split(',')
    available_digests = transport_security.digests
    strong_digests = [i for i in recommended_digests if i in available_digests]
    medium_digests = [i for i in fallback_digests if i in available_digests]
    # logger.debug("TLS digests available %s, used %s (or fallback to %s)" %
    #             (available_digests, strong_digests, medium_digests))
    if strong_digests:
        # logger.debug("Using only strong message auth codes: %s" %
        #             ', '.join(strong_digests))
        transport_security.digests = strong_digests
    elif medium_digests:
        # logger.debug("Using only medium strength message auth codes: %s" %
        #             ', '.join(medium_digests))
        transport_security.digests = medium_digests
    else:
        logger.warning("No strong TLS digest algorithm available!")
        logger.info("You need paramiko 1.16 or later for best security")

    # Default forces re-keying after every 512MB or same number of packets.
    # We bump that to reduce the slowing effect of those: it's a security
    # trade-off but OpenSSH does re-keying even less frequently.
    # Please note that some weaker ciphers still cap re-key limit below the
    # value we set here and in the client.
    # logger.debug("Double default re-keying sizes %d bytes / %d packets" %
    #             (transport.packetizer.REKEY_BYTES,
    #              transport.packetizer.REKEY_PACKETS))
    # Bump re-keying from 512MB to 2GB to reduce large transfer slow-downs
    rekey_scale = 4
    transport.packetizer.REKEY_BYTES *= rekey_scale
    # Allow receiving this many bytes after a re-key request before terminating
    transport.packetizer.REKEY_BYTES_OVERFLOW_MAX *= rekey_scale
    # Bump re-keying packet counts too to make sure it doesn't override size
    transport.packetizer.REKEY_PACKETS *= rekey_scale
    transport.packetizer.REKEY_PACKETS_OVERFLOW_MAX *= rekey_scale
    logger.info("Using re-keying sizes %d bytes / %d packets" %
                (transport.packetizer.REKEY_BYTES,
                 transport.packetizer.REKEY_PACKETS))

    transport.logger = logger
    # Try to load precomputed primes from /etc/ssh/moduli
    # NOTE: they should preferably be tuned in line with:
    #       https://stribika.github.io/2015/01/04/secure-secure-shell.html
    if not transport.load_server_moduli():
        logger.warning("Load server moduli failed, group-exchange disabled")
    transport.add_server_key(host_key)
    # Force keep-alive and see if it helps detect broken sessions in tracking
    transport.set_keepalive(900)

    if "sftp_implementation" in conf:
        mod_name, class_name = conf['sftp_implementation'].split(':')
        fromlist = None
        try:
            parent = mod_name[0:mod_name.rindex('.')]
            fromlist = [parent]
        except:
            pass
        mod = __import__(mod_name, fromlist=fromlist)
        impl = getattr(mod, class_name)
        # logger.debug("Custom implementation: %s" % conf['sftp_implementation'])
    else:
        impl = SimpleSftpServer
    transport.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp_si=impl,
                                    transport=transport, fs_root=root_dir,
                                    conf=conf)

    server = SimpleSSHServer(conf=conf, client_addr=addr, transport=transport)
    # Catch and only log connection accept errors
    try:
        transport.start_server(server=server)
        channel = transport.accept(conf['auth_timeout'])
    except Exception as err:
        logger.warning('client negotiation error for %s: %s' %
                       (addr, err))

    username = server.get_authenticated_user()
    success = False
    if username is not None:
        success = True
        active_count = active_sessions(configuration, 'sftp', username)
        logger.info("Proceed with login for %s with %d active sessions"
                    % (username, active_count))
    if success:
        msg = "Login for %s from %s" % (username, addr, )
        print(msg)
        logger.info(msg)
    else:
        msg = "Login from %s failed - closing connection" % (addr, )
        print(msg)
        logger.info(msg)
        transport.close()

    # Ignore user connection here as we only care about sftp.
    # Keep the connection alive until user disconnects or server is halted.

    # NOTE: is_active check does not seem to always catch broken connections
    # http://stackoverflow.com/questions/20147902/how-to-know-if-a-paramiko-ssh-channel-is-disconnected
    #       We try to keep connections alive and force failure with timeout.

    while transport.is_active():
        if conf['stop_running'].is_set():
            transport.close()
        time.sleep(1)

    if username is not None:
        if success:
            msg = "Logout for %s from %s" % (username, addr, )
            print(msg)
            logger.info(msg)


def start_service(configuration):
    """Service daemon"""
    daemon_conf = configuration.daemon_conf
    window_size = daemon_conf.get('window_size', DEFAULT_WINDOW_SIZE)
    max_packet_size = daemon_conf.get(
        'max_packet_size', DEFAULT_MAX_PACKET_SIZE)
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow reuse of socket to avoid TCP time outs
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((daemon_conf['address'], daemon_conf['port']))
        server_socket.listen(10)
    except Exception as err:
        err_msg = 'Could not open socket: %s' % err
        logger.error(err_msg)
        print(err_msg)
        if server_socket:
            server_socket.close()
        sys.exit(1)

    logger.info("accept connections: window_size %d / max_packet_size %d" %
                (window_size, max_packet_size))

    min_expire_delay = 300
    last_expire = time.time()
    while True:
        client_tuple = None
        try:
            # logger.debug('accept with %d active sessions' %
            #             threading.active_count())
            client_tuple = server_socket.accept()
            # accept may return None or tuple with None part in corner cases
            if client_tuple is None or None in client_tuple:
                raise Exception('got empty bogus request')
            (client, addr) = client_tuple
        except KeyboardInterrupt:
            # forward KeyboardInterrupt to main thread
            server_socket.close()
            raise
        except Exception as err:
            logger.warning('ignoring failed client connection for %s: %s' %
                           (client_tuple, err))
            continue
        logger.info("Handling new session from %s %s (%d active sessions)" %
                    (client, addr, threading.active_count()))
        worker = threading.Thread(target=accept_client,
                                  args=[client, addr, daemon_conf['root_dir'],
                                        daemon_conf['host_rsa_key'],
                                        daemon_conf])
        worker.start()
        if last_expire + min_expire_delay < time.time():
            last_expire = time.time()
            expire_rate_limit(configuration, "sftp",
                              expire_delay=min_expire_delay)


if __name__ == "__main__":
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("sftp", configuration.user_sftp_log, log_level)
    configuration.logger = logger
    auth_logger = daemon_logger(
        "sftp-auth", configuration.user_auth_log, log_level)
    configuration.auth_logger = auth_logger
    if configuration.site_enable_gdp:
        gdp_logger = daemon_gdp_logger("sftp-gdp",
                                       level=log_level)
        configuration.gdp_logger = gdp_logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # Allow configuration overrides on command line
    if sys.argv[2:]:
        configuration.user_sftp_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_sftp_port = int(sys.argv[3])

    if not configuration.site_enable_sftp:
        err_msg = "SFTP access to user homes is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)
    print("""
Running grid sftp server for user sftp access to their MiG homes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
""")
    print(__doc__)
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
    # NOTE: read possibly combined key/cert and strip any non-key content
    # NOTE: paramiko.RSAKey expects '-----X RSA PRIVATE KEY-----'
    #       Newer versions of 'openssl rsa -in X.key -text' generate
    #       '-----X PRIVATE KEY-----'
    header_marks = {'genric': '-----BEGIN PRIVATE KEY-----',
                    'rsa': '-----BEGIN RSA PRIVATE KEY-----',
                    }
    footer_marks = {'genric': '-----END PRIVATE KEY-----',
                    'rsa': '-----END RSA PRIVATE KEY-----',
                    }
    possible_rsa_key = read_file(configuration.user_sftp_key, logger)
    host_key = None
    for header_type, header_mark in header_marks.items():
        footer_mark = footer_marks[header_type]
        if possible_rsa_key.find(header_mark) != -1:
            host_key = possible_rsa_key.split(header_mark, 1)[-1]
            host_key = host_key.split(footer_mark, 1)[0]
    host_rsa_key = None
    if host_key:
        host_rsa_key = "%s%s%s" \
            % (header_marks['rsa'],
               host_key,
               footer_marks['rsa'])
        logger.debug("Using host key: %s" % configuration.user_sftp_key)
    else:
        info_msg = "No valid host key provided - using default"
        logger.info(info_msg)
        print(info_msg)
        host_rsa_key = default_host_key
    # Validate host rsa key before starting server
    try:
        host_key_file = NativeStringIO(force_native_str(host_rsa_key))
        paramiko.RSAKey(file_obj=host_key_file)
    except Exception:
        import traceback
        err_msg = "Invalid host RSA key\n%s" \
            % traceback.format_exc()
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)
    # Lookup chroot exceptions once and for all
    chroot_exceptions = user_chroot_exceptions(configuration)
    # Any extra chmod exceptions here - we already cover invisible_path check
    # in acceptable_chmod helper.
    chmod_exceptions = []
    configuration.daemon_conf = {
        'address': address,
        'port': port,
        'root_dir': os.path.abspath(configuration.user_home),
        'chroot_exceptions': chroot_exceptions,
        'chmod_exceptions': chmod_exceptions,
        'allow_password': 'password' in configuration.user_sftp_auth,
        'allow_digest': False,
        'allow_publickey': 'publickey' in configuration.user_sftp_auth,
        'user_alias': configuration.user_sftp_alias,
        'host_rsa_key': host_rsa_key,
        # Lock needed here due to threaded creds updates
        'creds_lock': threading.Lock(),
        'users': [],
        'jobs': [],
        'shares': [],
        'jupyter_mounts': [],
        'login_map': {},
        'hash_cache': {},
        'time_stamp': 0,
        'logger': logger,
        'auth_timeout': 60,
        'stop_running': threading.Event(),
        'window_size': configuration.user_sftp_window_size,
        'max_packet_size': configuration.user_sftp_max_packet_size,
        # TODO: Add the following to configuration:
        # max_sftp_user_hits
        # max_sftp_user_abuse_hits
        # max_sftp_proto_abuse_hits
        # max_sftp_secret_hits
        'auth_limits':
            {'max_sftp_sessions': configuration.user_sftp_max_sessions,
             'max_user_hits': default_max_user_hits,
             'user_abuse_hits': default_user_abuse_hits,
             'proto_abuse_hits': default_proto_abuse_hits,
             'max_secret_hits': default_max_secret_hits,
             },
    }
    if configuration.site_enable_gdp:
        # Close projects marked as open due to NON-clean exits
        project_close(configuration, 'sftp', address, user_id=None)
    # Start with fresh session tracker
    clear_sessions(configuration, 'sftp')
    logger.info("Starting SFTP server")
    info_msg = "Listening on address '%s' and port %d" % (address, port)
    logger.info(info_msg)
    print(info_msg)
    try:
        start_service(configuration)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print(info_msg)
        configuration.daemon_conf['stop_running'].set()
    active = threading.active_count() - 1
    while active > 0:
        info_msg = "Waiting for %d worker threads to finish" % active
        logger.info(info_msg)
        print(info_msg)
        time.sleep(1)
        active = threading.active_count() - 1
    info_msg = "Leaving with no more workers active"
    logger.info(info_msg)
    print(info_msg)
