#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_ftps - secure ftp server wrapping ftp in tls/ssl and mapping user home
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

Requires PyOpenSSL module (http://pypi.python.org/pypi/pyOpenSSL).
"""

import logging
import os
import sys
import time

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import TLS_FTPHandler
from pyftpdlib.servers import FTPServer

from shared.base import client_dir_id, client_alias, invisible_path
from shared.conf import get_configuration_object
from shared.griddaemons import get_fs_path, strip_root, \
     flags_to_mode, acceptable_chmod, refresh_users
from shared.useradm import check_password_hash


configuration, logger = None, None


class MiGUserAuthorizer(DummyAuthorizer):
    """Autehnticate/authorize againstMiG users DB"""

    users = None
    authenticated_user = None

    def update_logins(self):
        """Update login DB"""

        # TODO: move update to connect handler?

        daemon_conf = configuration.daemon_conf

        logger.info("update user list")

        # automatic reload of users if more than refresh_delay seconds old
        refresh_delay = 60
        if daemon_conf['time_stamp'] + refresh_delay < time.time():
            daemon_conf = refresh_users(configuration, 'ftps')

        logger.info("update usermap")
        usermap = {}
        for user_obj in configuration.daemon_conf['users']:
            if not usermap.has_key(user_obj.username):
                usermap[user_obj.username] = []
            usermap[user_obj.username].append(user_obj)
        self.users = usermap
        logger.info("updated usermap: %s" % self.users)
        logger.info("update user_table")
        # Fill users in dictionary for fast lookup. We create a list of
        # matching User objects since each user may have multiple logins (e.g.
        # public keys)
        for (username, user_obj_list) in self.users.items():
            if self.has_user(username):
                self.remove_user(username)
            # TODO: should we allow multiple entries?
            user_obj = user_obj_list[0]
            home_path = os.path.join(daemon_conf['root_dir'], user_obj.home)
            logger.info("add user to user_table: %s" % user_obj)
            self.add_user(username, user_obj.password,
                          home_path, perm='elradfmw')
        logger.info("updated user_table: %s" % self.user_table)

    def validate_authentication(self, username, password, handler):
        """Password auth against usermap.

        Please note that we take serious steps to secure against password
        cracking, but that it _may_ still be possible to achieve with a big
        effort.

        Paranoid users / grid owners should not enable password access in the
        first place!
        """
        logger.info("Authenticating %s" % username)
        self.update_logins()
        
        offered = None
        if 'password' in configuration.user_ftps_auth and \
               self.has_user(username):
            # list of User login objects for username
            entries = [self.user_table[username]]
            offered = password
            for entry in entries:
                if entry['pwd'] is not None:
                    allowed = entry['pwd']
                    logger.debug("Password check for %s" % username)
                    if check_password_hash(offered, allowed):
                        logger.info("Authenticated %s" % username)
                        self.authenticated_user = username
                        return True
        err_msg = "Password authentication failed for %s" % username
        logger.error(err_msg)
        print err_msg
        return False


def start_service(conf):
    """Main server"""
    authorizer = MiGUserAuthorizer()
    handler = TLS_FTPHandler
    handler.certfile = conf.user_ftps_key
    handler.authorizer = authorizer
    handler.passive_ports = range(conf.user_ftps_pasv_ports[0],
                                  conf.user_ftps_pasv_ports[1])
    
    # requires SSL for both control and data channel
    handler.tls_control_required = True
    handler.tls_data_required = True
    server = FTPServer((conf.user_ftps_address, conf.user_ftps_ctrl_port),
                       handler)
    server.serve_forever()
        

if __name__ == '__main__':
    configuration = get_configuration_object()
    # TMP: separate logger for now
    #logger = configuration.logger
    logging.basicConfig(filename="ftps.log", level=logging.DEBUG,
                        format="%(asctime)s %(levelname)s %(message)s")
    logger = logging


    # TMP: until we get real conf
    configuration.site_enable_ftps = True
    configuration.user_ftps_address = ''
    configuration.user_ftps_ctrl_port = 8023
    configuration.user_ftps_pasv_ports = range(8050, 8100)
    configuration.user_ftps_key = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "ftpd-keycert.pem"))
    configuration.user_ftps_auth = "password"
    configuration.user_ftps_alias = "email"    


    if not configuration.site_enable_ftps:
        err_msg = "FTPS access to user homes is disabled in configuration!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)
    print """
Running grid ftps server for user ftps access to their MiG homes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    address = configuration.user_ftps_address
    ctrl_port = configuration.user_ftps_ctrl_port
    pasv_ports = configuration.user_ftps_pasv_ports
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
        host_key_fd = open(configuration.user_ftps_key, 'r')
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
    configuration.daemon_conf = {
        'address': address,
        'ctrl_port': ctrl_port,
        'pasv_ports': pasv_ports,
        'root_dir': os.path.abspath(configuration.user_home),
        'chmod_exceptions': chmod_exceptions,
        'chroot_exceptions': chroot_exceptions,
        'allow_password': 'password' in configuration.user_ftps_auth,
        'allow_publickey': 'publickey' in configuration.user_ftps_auth,
        'user_alias': configuration.user_ftps_alias,
        'host_rsa_key': host_rsa_key,
        'users': [],
        'time_stamp': 0,
        'logger': logger,
        }
    info_msg = "Listening on address '%s' and port %d" % (address, ctrl_port)
    logger.info(info_msg)
    print info_msg
    try:
        start_service(configuration)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print info_msg
        configuration.daemon_conf['stop_running'].set()
    info_msg = "Leaving with no more workers active"
    logger.info(info_msg)
    print info_msg
