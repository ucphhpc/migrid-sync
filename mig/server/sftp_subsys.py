#!/usr/bin/python -s
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sftp_subsys - SFTP subsys exposing access to MiG user homes through openssh
# Copyright (C) 2010-2020  The MiG Project lead by Brian Vinter
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

# IMPORTANT: use python -s in the hash-bang at the top to disable user site
#            directory inclusion in sys.path since it would potentially lead
#            to arbitrary user code injection if any module X in
#            user_home/USERID/.local/lib/python2.7/site-packages/X shadowed
#            the non-stdlib modules imported below (details in PEP 370).

"""Provides SFTP access to MiG user homes as a subsys through openssh.

Requires Paramiko module (http://pypi.python.org/pypi/paramiko) and setup of
our own PAM infrastructure using pam-mig and libnss-mig.
IMPORTANT: We strongly recommend setting the login shell in libnss_mig.conf to
/path/to/mig/server/sftp_subsys.py
or at least /bin/sh if that doesn't work. Using e.g. /bin/bash WILL result in
unsafe evaluation of any .bashrc in the user home of the user.
Using /bin/sh requires extra care if running other sshd instances since libnss
may then allow valid MiG user login with key there, too - unless login as mig
user/group is actively prohibited or restricted there as well.

When ready point /etc/ssh/sshd_config to this file as sftp subsystem provider:
Subsystem   sftp    /path/to/mig/server/sftp_subsys.py

Similarly setup those logins to use credentials from individual user home dirs
(with implicit chrooting) like:
Match Group mig
    AuthorizedKeysFile %h/.ssh/authorized_keys
    ForceCommand /path/to/mig/server/sftp_subsys.py
    # Plus any further limitations here

and restart sshd.

Please note that the configuration generator creates a fully functional
openssh configuration including the above setup for users. So you can just
use it with --enable_sftp_subsys=True and copy the generated
sshd_config-MiG-sftp-subsys to /etc/ssh/sshd_config-MiG-sftp-subsys for easy
setup.

Inspired by https://gist.github.com/lonetwin/3b5982cf88c598c0e169
"""
from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import threading
import time

try:
    from paramiko.server import ServerInterface
    from paramiko.sftp_server import SFTPServer, SFTPServerInterface
    from paramiko.transport import Transport
except ImportError:
    print("ERROR: the python paramiko module is required for this daemon")
    sys.exit(1)

# IMPORTANT: sshd sftp subsys calls this script directly without user env so
#            we cannot rely on PYTHONPATH and instead explictly set load path
#            to include user home to allow from mig.X import Y
# NOTE: __file__ is /MIG_BASE/mig/server/sftp_subsys.py and we need MIG_BASE
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mig.server.grid_sftp import SimpleSftpServer as SftpServerImpl
from mig.shared.conf import get_configuration_object
from mig.shared.fileio import user_chroot_exceptions
from mig.shared.logger import daemon_logger, register_hangup_handler

configuration, logger = None, None


class IOSocketAdapter(object):
    """Adapt stdout and stdin to the usual socket API"""

    def __init__(self, stdin, stdout):
        self._stdin = stdin
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


if __name__ == '__main__':
    # We need to manualy extract MiG conf path since running from openssh
    conf_path = os.path.join(os.path.dirname(__file__), 'MiGserver.conf')
    os.putenv('MIG_CONF', conf_path)
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)
    log_level = configuration.loglevel
    # Use separate logger
    logger = daemon_logger('sftp-subsys', configuration.user_sftp_subsys_log,
                           log_level)
    configuration.logger = logger
    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)
    pid = os.getpid()
    logger.info('(%d) Basic sftp subsystem initialized' % pid)
    # IMPORTANT: for security reasons we only allow restricted launch
    #            The login shell should NOT evaluate arbitrary user code from
    #            profile or shell rc files and should preferably call this
    #            script directly. More info in the module doc-string above.
    fallback_shells = ['/bin/sh']
    login_shell = os.environ.get('SHELL', 'UNKNOWN')
    if sys.argv[1:] == ['-c', __file__]:
        login_shell = sys.argv[0]
    if login_shell in fallback_shells:
        logger.warning("sftp subsystem not using direct launch but %s" %
                       login_shell)
    elif login_shell != __file__:
        logger.error("sftp subsystem launched with illegal/unsafe shell: %s"
                     % login_shell)
        sys.exit(1)

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
        logger.debug('Create socket adaptor')
        socket_adapter = IOSocketAdapter(sys.stdin, sys.stdout)
        logger.debug('Create server interface')
        server_if = ServerInterface()
        logger.debug('Create sftp server')
        # Pass helper vars directly on class to avoid API tampering
        SftpServerImpl.configuration = configuration
        SftpServerImpl.conf = configuration.daemon_conf
        SftpServerImpl.logger = logger
        sftp_server = SFTPServer(socket_adapter, 'sftp', server=server_if,
                                 sftp_si=SftpServerImpl)
        logger.info('(%s) Start sftp subsys server' % pid)
        # NOTE: we explicitly loop and join thread to act on hangup signal
        sftp_server.setDaemon(False)
        sftp_server.start()
        while True:
            try:
                if configuration.daemon_conf['stop_running'].is_set():
                    # TODO: should we terminate sftp_server here?
                    logger.info('(%d) Join sftp subsys server worker' % pid)
                    sftp_server.join()
                    break
                else:
                    # Join with 1s timeout to stay responsive but catch finish
                    sftp_server.join(1)
                    # Check alive to decide if join succeeded or timed out
                    if not sftp_server.isAlive():
                        configuration.daemon_conf['stop_running'].set()
                        break
            except KeyboardInterrupt:
                logger.info("(%d) Received user interrupt" % pid)
                configuration.daemon_conf['stop_running'].set()
        logger.info('(%d) Finished sftp subsys server' % pid)
    except Exception as exc:
        logger.error('(%d) Failed to run sftp subsys server: %s' % (pid, exc))
        import traceback
        logger.error(traceback.format_exc())
