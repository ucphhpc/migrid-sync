#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sftp_subsys - SFTP subsys exposing access to MiG user homes through openssh
# Copyright (C) 2010-2017  The MiG Project lead by Brian Vinter
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

"""Provides SFTP access to MiG user homes as a subsys through openssh.

Requires Paramiko module (http://pypi.python.org/pypi/paramiko) and setup of
our own PAM infrastructure using pam-mig and libnss-mig.

Then change /etc/ssh/sshd_config to use this file as sftp subsystem provider:
Subsystem   sftp    /path/to/mig/server/sftp_subsys.py

Similarly setup those logins to use credentials from individual user home dirs
and chrooting there:
Match Group mig
    AuthorizedKeysFile %h/.ssh/authorized_keys
    ChrootDirectory %h
    ForceCommand internal-sftp
    
and restart sshd.

Inspired by https://gist.github.com/lonetwin/3b5982cf88c598c0e169
"""

import os
import sys
import threading
import time

from paramiko.server import ServerInterface
from paramiko.sftp_server import SFTPServer, SFTPServerInterface
from paramiko.transport import Transport

from shared.conf import get_configuration_object
from shared.fileio import user_chroot_exceptions
from shared.logger import daemon_logger
from grid_sftp import SimpleSftpServer as SftpServerImpl


class IOSocketAdapter(object):
    """Adapt stdout and stdin to the usual socket API"""
    def __init__(self, stdin, stdout):
        self._stdin  = stdin
        self._stdout = stdout
        self._transport = None

    def send(self, data, flags=0):
        """Fake send"""
        self._stdout.flush()
        self._stdout.write(data)
        self._stdout.flush()
        return len(data)

    def recv(self, bufsize, flags=0):
        """Fake recv"""
        data = self._stdin.read(bufsize)
        return data

    def close(self):
        """Fake close"""
        self._stdin.close()
        self._stdout.close()

    def settimeout(self, ignored):
        """Ignore timeout settings"""
        pass

    def get_name(self):
        """Used for paramiko logging"""
        return 'sftp'

    def get_transport(self):
        """Lazy transport init and getter"""
        if not self._transport:
            self._transport = Transport(self)
        return self._transport


def start_server(params):
    """Run the subsystem"""
    # We need to manualy extract MiG conf path since running from openssh
    conf_path = os.path.join(os.path.dirname(__file__), 'MiGserver.conf')
    os.putenv('MIG_CONF', conf_path)
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)
    # TODO: lower default log verbosity when ready for production use
    #log_level = configuration.loglevel
    log_level = 'debug'
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]
    # Use separate logger
    logger = daemon_logger('sftp-subsys', configuration.user_sftp_subsys_log,
                           log_level)
    configuration.logger = logger
    logger.info('Basic sftp subsystem initialized')
    # Lookup chroot exceptions once and for all
    chroot_exceptions = user_chroot_exceptions(configuration)
    # Any extra chmod exceptions here - we already cover invisible_path check
    # in acceptable_chmod helper.
    chmod_exceptions = []
    configuration.daemon_conf = {
        'root_dir': os.path.abspath(configuration.user_home),
        'chroot_exceptions': chroot_exceptions,
        'chmod_exceptions': chmod_exceptions,
        'allow_password': 'password' in configuration.user_sftp_auth,
        'allow_digest': False,
        'allow_publickey': 'publickey' in configuration.user_sftp_auth,
        'user_alias': configuration.user_sftp_alias,
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
        'stop_running': threading.Event(),
        }

    try:
        logger.info('Create socket adaptor')
        socket_adapter = IOSocketAdapter(sys.stdin, sys.stdout)
        logger.info('Create server interface')
        server_if = ServerInterface()
        logger.info('Create sftp server')
        # Pass helper vars directly on class to avoid API tampering
        SftpServerImpl.configuration = configuration
        SftpServerImpl.conf = configuration.daemon_conf
        SftpServerImpl.logger = logger
        sftp_server = SFTPServer(socket_adapter, 'sftp', server=server_if,
                                 sftp_si=SftpServerImpl)
        logger.info('Start sftp server')
        sftp_server.start()
    except Exception, exc:
        logger.error('Failed to run sftp server: %s' % exc)
        

if __name__ == '__main__':    
    start_server(sys.argv)
