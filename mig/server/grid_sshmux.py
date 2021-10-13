#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_sshmux - open ssh multiplexing master connections
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

"""Keep persistent connections up to significantly speed up
resource ssh calls. This daemon simply opens dummy connections
to all resources that specify persistent access support. Each
connection is relatively short lived to allow better connection
error tolerance.
"""

from __future__ import print_function
from __future__ import absolute_import

import os
import signal
import sys
import threading
from time import sleep

from mig.shared.base import sandbox_resource
from mig.shared.conf import get_resource_configuration, \
    get_configuration_object
from mig.shared.logger import daemon_logger, register_hangup_handler
from mig.shared.ssh import execute_on_resource

configuration, logger = None, None


def persistent_connection(resource_config, logger):
    """Keep running a persistent master connection"""

    sleep_secs = 300
    hostname = resource_config['HOSTURL']

    # Mark this session as a multiplexing master to avoid races:
    # see further details in shared/ssh.py

    resource_config['SSHMULTIPLEXMASTER'] = True
    while True:
        try:
            logger.debug('connecting to %s' % hostname)
            (exit_code, executed) = execute_on_resource('sleep %d'
                                                        % sleep_secs,
                                                        False, resource_config,
                                                        logger)
            if 0 != exit_code:
                msg = 'ssh multiplex %s: %s returned %i' % \
                      (hostname, executed, exit_code)
                print(msg)

                # make sure control_socket was cleaned up

                host = resource_config['HOSTURL']
                identifier = resource_config['HOSTIDENTIFIER']
                unique_id = '%s.%s' % (host, identifier)
                control_socket = \
                    os.path.join(configuration.resource_home,
                                 unique_id, 'ssh-multiplexing')
                try:
                    os.remove(control_socket)
                except:
                    pass
                sleep(sleep_secs)
        except Exception as err:

            msg = '%s thread caught exception (%s) - retry later' % \
                  (hostname, err)
            print(msg)
            logger.error(msg)
            sleep(sleep_secs)

    msg = '%s thread leaving...' % hostname
    print(msg)
    logger.info(msg)


def graceful_shutdown(signum, frame):
    """ This function is responsible for shutting down the 
    system in a graceful way """

    msg = '%s: graceful_shutdown called' % sys.argv[0]
    print(msg)
    try:
        logger.info(msg)
    except Exception:
        pass
    sys.exit(0)


if __name__ == '__main__':
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger
    logger = daemon_logger("sshmux", configuration.user_sshmux_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    if not configuration.site_enable_jobs:
        err_msg = "Job support is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    print("""
Running grid ssh multiplexing server for resource ssh connection reuse.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
""")

    persistent_hosts = {}
    resource_path = configuration.resource_home
    for unique_resource_name in os.listdir(configuration.resource_home):
        res_dir = os.path.realpath(configuration.resource_home + os.sep
                                   + unique_resource_name)

        # skip all dot dirs - they are from repos etc and _not_ jobs

        if res_dir.find(os.sep + '.') != -1:
            continue
        if not os.path.isdir(res_dir):
            continue
        dir_name = os.path.basename(res_dir)
        if sandbox_resource(dir_name):
            continue
        try:
            (status, res_conf) = \
                get_resource_configuration(configuration.resource_home,
                                           unique_resource_name, logger)
            if not status:
                continue
            if 'SSHMULTIPLEX' in res_conf and res_conf['SSHMULTIPLEX']:
                print('adding multiplexing resource %s' % unique_resource_name)
                fqdn = res_conf['HOSTURL']
                res_conf['HOMEDIR'] = res_dir
                persistent_hosts[fqdn] = res_conf
        except Exception as err:

            # else:
            #    print "ignoring non-multiplexing resource %s" % unique_resource_name

            print("Failed to open resource conf '%s': %s"
                  % (unique_resource_name, err))

    threads = {}

    # register ctrl+c signal handler to shutdown system gracefully

    signal.signal(signal.SIGINT, graceful_shutdown)
    for (hostname, conf) in persistent_hosts.items():
        if hostname not in threads:
            threads[hostname] = \
                threading.Thread(target=persistent_connection, args=(conf,
                                                                     logger))
            threads[hostname].setDaemon(True)
            threads[hostname].start()

    print('Send interrupt (ctrl-c) twice to stop persistent connections')
    while True:
        sleep(60)
