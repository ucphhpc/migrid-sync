#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# grid_transfers - transfer handler to run background data transfers
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

"""Transfer handler to take care of background data transfers requested by
users.

Requires sftp, rsync and lftp binaries to take care of the actual transfers.
"""

import glob
import logging
import logging.handlers
import os
import sys
import time
import threading

from shared.fileio import makedirs_rec, pickle
from shared.conf import get_configuration_object
from shared.defaults import datatransfers_filename, transfers_log_name, \
     transfers_log_size, transfers_log_cnt
from shared.logger import daemon_logger
from shared.safeeval import subprocess_popen, subprocess_pipe
from shared.useradm import client_dir_id, client_id_dir
from shared.transferfunctions import load_data_transfers, modify_data_transfers

# Global transfers dictionary with requests for all users

all_transfers = {}
(configuration, logger, last_update) = (None, None, 0)

command_map = {'importstr':
               {'sftp': 'sftp -B 258048 -oUser=%(username)s -oPort=%(port)s %(fqdn)s:%(src)s %(dst)s/',
                'ftp': "lftp -e 'set ftp:ssl-protect-data off' -c 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'",
                'ftps': "lftp -e 'set ftp:ssl-protect-data on' -c 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'",
                'http': "lftp -c 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'",
                'https': "lftp -c 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'",
                'webdav': "lftp -c 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'",
                'webdavs': "lftp -c 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'",
                'rsync+ssh': 'rsync -p %(port)s %(username)s@%(fqdn)s:%(src)s %(dst)s/',
                },
               'exportstr':
               {'sftp': 'sftp -B 258048 -oUser=%(username)s -oPort=%(port)s %(src)s %(fqdn)s:%(dst)s/',
                'ftp': "lftp -e 'set ftp:ssl-protect-data off' -c 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'",
                'ftps': "lftp -e 'set ftp:ssl-protect-data on' -c 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'",
                'http': "lftp -c 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'",
                'https': "lftp -c 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'",
                'webdav': "lftp -c 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'",
                'webdavs': "lftp -c 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'",
                'rsync+ssh': 'rsync -p %(port)s %(username)s@%(fqdn)s:%(src)s %(dst)s/',
                },
               'import':
               {'sftp': ['sftp', '-B', '258048', '-oUser=%(username)s', '-oPort=%(port)s', '%(fqdn)s:%(src)s', '%(dst)s/'],
                'ftp': ['lftp', '-e', 'set ftp:ssl-protect-data off', '-c', 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'],
                'ftps': ['lftp', '-e', 'set ftp:ssl-protect-data on', '-c', 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'],
                'http': ['lftp', '-c', 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'],
                'https': ['lftp', '-c', 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'],
                'webdav': ['lftp', '-c', 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'],
                'webdavs': ['lftp', '-c', 'get -O %(dst)s/ %(protocol)s://%(fqdn)s:%(port)s/%(src)s'],
                'rsync+ssh': ['rsync', '-p', '%(port)s', '%(username)s@%(fqdn)s:%(src)s', '%(dst)s/'],
                },
               'export':
                {'sftp': ['sftp', '-B', '258048', '-oUser=%(username)s', '-oPort=%(port)s', '%(src)s', '%(fqdn)s:%(dst)s/'],
                'ftp': ['lftp', '-e', 'set ftp:ssl-protect-data off', '-c', 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'],
                'ftps': ['lftp', '-e', 'set ftp:ssl-protect-data on', '-c', 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'],
                'http': ['lftp', '-c', 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'],
                'https': ['lftp', '-c', 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'],
                'webdav': ['lftp', '-c', 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'],
                'webdavs': ['lftp', '-c', 'put %(src)s %(protocol)s://%(fqdn)s:%(port)s/%(dst)s/'],
                'rsync+ssh': ['rsync', '-p', '%(port)s', '%(username)s@%(fqdn)s:%(src)s', '%(dst)s/'],
                }
               }

def __transfer_log(configuration, client_id, msg, level='info'):
    """Wrapper to send a single msg to transfer log file of client_id"""
    log_path = os.path.join(configuration.user_home, client_id_dir(client_id),
                            "transfer_output", transfers_log_name)
    makedirs_rec(os.path.dirname(log_path), configuration)
    transfers_logger = logging.getLogger('transfers')
    transfers_logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(log_path,
                                                   maxBytes=transfers_log_size,
                                                   backupCount=transfers_log_cnt - 1)
    formatter = \
              logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    transfers_logger.addHandler(handler)
    if level == 'error':
        transfers_logger.error(msg)
    elif level == 'warning':
        transfers_logger.warning(msg)
    else:
        transfers_logger.info(msg)
    handler.flush()
    handler.close()
    transfers_logger.removeHandler(handler)

def transfer_error(configuration, client_id, msg):
    """Wrapper to send a single error msg to transfer log of client_id"""
    __transfer_log(configuration, client_id, msg, 'error')

def transfer_warn(configuration, client_id, msg):
    """Wrapper to send a single warn msg to transfer log of client_id"""
    __transfer_log(configuration, client_id, msg, 'warning')

def transfer_info(configuration, client_id, msg):
    """Wrapper to send a single info msg to transfer log of client_id"""
    __transfer_log(configuration, client_id, msg, 'info')


def run_transfer(transfer_dict, client_id, configuration):
    """Run data transfer built from transfer_dict on behalf of client_id"""

    logger.info('run command for %s: %s' % (client_id, transfer_dict))
    action = transfer_dict['action']
    protocol = transfer_dict['protocol']
    if not protocol in command_map[action]:
        raise ValueError('unsupported protocol: %s' % protocol)
    command_pattern = command_map[action][protocol]
    status_path = os.path.join(configuration.user_home,
                               client_id_dir(client_id),
                               "transfer_output")
    makedirs_rec(status_path, configuration)
    if transfer_dict['action'] in ('import', ):
        logger.info('setting abs dst for action %(action)s' % transfer_dict)
        src_path_list = transfer_dict['src']
        dst_path = os.path.join(configuration.user_home,
                                client_id_dir(client_id),
                                (transfer_dict['dst']).lstrip(os.sep))
        makedirs_rec(dst_path, configuration)
    elif transfer_dict['action'] in ('export', ):
        logger.info('setting abs src for action %(action)s' % transfer_dict)
        src_path_list = []
        for src in transfer_dict['src']:
            src_path_list.append(os.path.join(configuration.user_home,
                                              client_id_dir(client_id),
                                              src.lstrip(os.sep)))
        dst_path = transfer_dict['dst']
    else:
        raise ValueError('unsupported action: %(action)s' % transfer_dict)
    run_dict = transfer_dict.copy()
    run_dict['dst'] = dst_path
    for src in src_path_list:
        run_dict['src'] = src
        command_list = [i % run_dict for i in command_pattern]
        command_str = ' '.join(command_list)
        logger.debug('run %s on behalf of %s' % (command_str, client_id))
        # TODO: switch to list form and avoid split to support space in names
        transfer_proc = subprocess_popen(command_list,
                                         stdout=subprocess_pipe,
                                         stderr=subprocess_pipe)
        exit_code = transfer_proc.wait()
        out, err = transfer_proc.communicate()
        logger.info('done running transfer %s: %s' % (run_dict['transfer_id'],
                                                  command_str))
        logger.info('raw output is: %s' % out)
        logger.info('raw error is: %s' % err)
        logger.info('result was %s' % exit_code)
        # TODO: notify main somehow that transfer is done
    logger.debug('done handling transfers in %(transfer_id)s' % transfer_dict)


def foreground_transfer(transfer_dict, client_id, configuration):
    """Run a transfer in the foreground so that it can block without
    stopping further transfer handling.
    We add a time stamp to have a sort of precise time for when the transfer
    was started.
    """

    worker = threading.Thread(target=run_transfer, args=(transfer_dict,
                                                        client_id,
                                                        configuration))
    worker.start()
    transfer_dict['__workers__'] = transfer_dict.get('__workers__', [])
    transfer_dict['__workers__'].append(worker)
    worker.join()

def background_transfer(transfer_dict, client_id, configuration):
    """Run a transfer in the background so that it can block without
    stopping further transfer handling.
    We add a time stamp to have a sort of precise time for when the transfer
    was started.
    """

    worker = threading.Thread(target=run_transfer, args=(transfer_dict,
                                                        client_id,
                                                        configuration))
    worker.daemon = True
    worker.start()
    transfer_dict['__workers__'] = transfer_dict.get('__workers__', [])
    transfer_dict['__workers__'].append(worker)


def handle_transfer(configuration, client_id, transfer_dict):
    """Actually handle valid transfer request in transfer_dict"""

    logger.info('in handling of %s %s for %s' % (transfer_dict['transfer_id'],
                                                 transfer_dict['action'],
                                                 client_id))
    transfer_info(configuration, client_id,
                  'handle %s %s' % (transfer_dict['transfer_id'],
                                    transfer_dict['action']))

    try:
        # TMP! 
        foreground_transfer(transfer_dict, client_id, configuration)
        #background_transfer(transfer_dict, client_id, configuration)
        transfer_info(configuration, client_id,
                      'ran %s %s from %s' % (transfer_dict['protocol'],
                                             transfer_dict['action'],
                                             transfer_dict['fqdn']))
    except Exception, exc:
        logger.error('failed to run %s %s from %s: %s (%s)'
                     % (transfer_dict['protocol'], transfer_dict['action'],
                        transfer_dict['fqdn'], exc, transfer_dict))
        transfer_error(configuration, client_id,
                       'failed to run %s %s from %s: %s (%s)' % \
                       (transfer_dict['protocol'], transfer_dict['action'],
                        transfer_dict['fqdn'], exc, transfer_dict))


def clean_transfer(configuration, client_id, transfer_dict):
    """Actually clean valid transfer request in transfer_dict"""

    logger.info('in cleaning of %s %s for %s' % (transfer_dict['transfer_id'],
                                                 transfer_dict['action'],
                                                 client_id))
    # TODO: clean up any removed transfers/processes here


def manage_transfers(configuration):
    """Manage all updates of saved user data transfer requests"""

    logger.debug('manage transfers')
    old_transfers = {}
    src_pattern = os.path.join(configuration.user_settings, '*',
                               datatransfers_filename)
    for transfers_path in glob.glob(src_pattern):
        if os.path.getmtime(transfers_path) < last_update:
            logger.debug('skip transfer update for unchanged path: %s' % \
                          transfers_path)
        logger.debug('handling update of transfers file: %s' % transfers_path)
        abs_client_dir = os.path.dirname(transfers_path)
        client_dir = os.path.basename(abs_client_dir)
        logger.debug('extracted client dir: %s' % client_dir)
        client_id = client_dir_id(client_dir)
        logger.debug('loading transfers for: %s' % client_id)
        (load_status, transfers) = load_data_transfers(configuration,
                                                       client_id)
        logger.debug("loaded current transfers from '%s':\n%s" % \
                     (transfers_path, transfers))

        old_transfers[client_id] = all_transfers.get(client_id, {})
        all_transfers[client_id] = transfers

    logger.debug('all transfers:\n%s' % all_transfers)
    for (client_id, transfers) in all_transfers.items():
        for (transfer_id, transfer_dict) in transfers.items():
            if not transfer_id in old_transfers.get(client_id, {}).keys():
                handle_transfer(configuration, client_id, transfer_dict)

    for (client_id, transfers) in old_transfers.items():
        for (transfer_id, transfer_dict) in transfers.items():
            if not transfer_id in all_transfers.get(client_id, {}).keys():
                clean_transfer(configuration, client_id, transfer_dict)

    
if __name__ == '__main__':
    print '''This is the MiG data transfer handler daemon which runs requested
data transfers in the background on behalf of the users. It monitors the saved
data transfer files for changes and launches external client threads to take
care of the tranfers, writing status and output to a transfer output directory
in the corresponding user home.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
'''

    configuration = get_configuration_object()

    # Use separate logger

    logger = daemon_logger('transfers', configuration.user_transfers_log,
                           "debug")
    configuration.logger = logger

    keep_running = True

    print 'Starting Data Transfer handler daemon - Ctrl-C to quit'

    logger.info('Starting data transfer handler daemon')

    while keep_running:
        try:

            manage_transfers(configuration)

            # Throttle down

            time.sleep(10)
        except KeyboardInterrupt:
            keep_running = False
        except Exception, exc:
            print 'Caught unexpected exception: %s' % exc

    print 'Data transfer handler daemon shutting down'
    logger.info('Stop data transfer handler daemon')
    sys.exit(0)
