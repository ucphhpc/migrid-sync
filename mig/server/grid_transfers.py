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

Requires rsync and lftp binaries to take care of the actual transfers.
"""

import datetime
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
     transfers_log_size, transfers_log_cnt, _user_invisible_paths, \
     user_keys_dir
from shared.logger import daemon_logger
from shared.safeeval import subprocess_popen, subprocess_pipe
from shared.useradm import client_dir_id, client_id_dir
from shared.transferfunctions import load_data_transfers, modify_data_transfers
from shared.validstring import valid_user_path

# Global transfers dictionary with requests for all users

all_transfers = {}
all_workers = {}
(configuration, logger, last_update) = (None, None, 0)

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

def transfer_result(configuration, client_id, transfer_dict, exit_code,
                    out_msg, err_msg):
    """Update status file from transfer_dict with the result from transfer
    that reurned exit_code, out_msg and err_msg.
    """
    logger = configuration.logger
    time_stamp = datetime.datetime.now().ctime()
    transfer_id = transfer_dict['transfer_id']
    rel_src = transfer_dict.get("rel_src", False)
    if not rel_src:
        rel_src = ', '.join(transfer_dict['src'])
    res_dir = os.path.join(configuration.user_home, client_id_dir(client_id),
                           "transfer_output", transfer_id)
    makedirs_rec(res_dir, configuration)
    status_msg = '''%s: %s %s of %s in %s finished with status %s
''' % (time_stamp, transfer_dict['protocol'], transfer_dict['action'], rel_src,
       transfer_dict['transfer_id'], exit_code)
    out_msg = '%s:\n%s\n' % (time_stamp, out_msg)
    err_msg = '%s:\n%s\n' % (time_stamp, err_msg)
    status = True
    for (ext, msg) in [("status", status_msg), ("stdout", out_msg),
                          ("stderr", err_msg)]:
        path = os.path.join(res_dir, "%s.%s" % (transfer_id, ext))
        try:
            if os.path.exists(path):
                status_fd = open(path, "a")
            else:
                status_fd = open(path, "w")
            status_fd.write(msg)
            status_fd.close()
        except Exception, exc :
            logger.error("writing status file %s for %s failed: %s" % \
                         (path, transfer_dict, exc))
            status = False
    return status

def run_transfer(transfer_dict, client_id, configuration):
    """Actual data transfer built from transfer_dict on behalf of client_id"""

    # Helpers for lftp and rsync
    # Default lftp buffer size - experimentally determined for good throughput
    _lftp_buffer_bytes = 1048576
    _base_buf_str = "set xfer:buffer-size %(lftp_buf_size)d"
    _sftp_buf_str = _base_buf_str
    for target in ("read", "write"):
        _sftp_buf_str += ";set sftp:size-%s %%(lftp_buf_size)d" % target
    _ftps_ssl_str = "set ftp:ssl-force ; set ftp:ssl-protect-data on"
    # Make sure we don't get bitten by any restrictive system-wide or
    # account-specific ssh settings. Also use a known_hosts file for client_id
    # to avoid polluting the known hosts file of the UNIX account user, while
    # allowing looser host key checking to avoid common host key errors.
    _ssh_base_opt = "-oForwardAgent=no -oForwardX11=no"
    _ssh_base_opt += " -oStrictHostKeyChecking=no "
    _ssh_base_opt += " -oUserKnownHostsFile=%(known_hosts)s"
    _ssh_key_opt = _ssh_base_opt + " -oPasswordAuthentication=no"
    _ssh_key_opt += " -oPubkeyAuthentication=yes -i %(key)s"
    _ssh_pw_opt = _ssh_base_opt + " -oPubkeyAuthentication=no"
    _ssh_pw_opt += " -oPasswordAuthentication=yes"
    _sftp_key_str = "set sftp:connect-program ssh -a -x %(auth_opt)s"
    # IMPORTANT: follow symlinks and don't preserve device files
    _rsync_flags = '-rLptgov'
    # All the port and login settings must be passed to ssh command
    _rsyncssh_transport_str = "ssh -p %(port)s -l %(username)s %(auth_opt)s"
    _login_port_str = "open -u %(username)s,%(password)s -p %(port)s "
    _exclude_list = ["--exclude=%s" % i for i in _user_invisible_paths]
    _exclude_str = ' '.join(_exclude_list).replace("=", ' ')
    _get_file_str = 'get'
    _put_file_str = 'put'
    _get_dir_str = 'mirror -Lv'
    _put_dir_str = _get_dir_str + ' -R'
    _file_dst_str = '-O %(dst)s/ %(src)s'
    _mirror_dst_str = '%(src)s %(dst)s/'
    _get_file_str = "%s %s" % (_get_file_str, _file_dst_str)
    _put_file_str = "%s %s" % (_put_file_str, _file_dst_str)
    _get_dir_str = "%s %s %s" % (_get_dir_str, _exclude_str, _mirror_dst_str)
    _put_dir_str = "%s %s %s" % (_put_dir_str, _exclude_str, _mirror_dst_str)

    # Command helpers
    # NOTE: lftp at CentOS was tested to work with commands like these
    # lftp -c "set xfer:buffer-size $BUFSIZE ; set sftp:size-read $BUFSIZE ; set sftp:size-write $BUFSIZE ; open -u USERNAME,PW -p 22 sftp://io.erda.dk ; get -O build/ build/dblzeros.bin"
    # lftp -c "set xfer:buffer-size $BUFSIZE; set ftp:ssl-force ; set ftp:ssl-protect-data on ; open -u USERNAME,PW -p 8021 ftp://io.erda.dk ; get -O /tmp welcome.txt"

    cmd_map = {'import':
               {'sftp': ['lftp', '-c',
                         ';'.join([_sftp_buf_str, _sftp_key_str,
                                   _login_port_str + '%(protocol)s://%(fqdn)s',
                                   '%(lftp_target)s'])],
                'ftp': ['lftp', '-c',
                        ';'.join([_base_buf_str, _login_port_str + \
                                  '%(protocol)s://%(fqdn)s',
                                  '%(lftp_target)s'])],
                # IMPORTANT: must be implicit proto or 'ftp://' (not ftps://)
                'ftps': ['lftp', '-c',
                         ';'.join([_base_buf_str, _ftps_ssl_str,
                                   _login_port_str + 'ftp://%(fqdn)s',
                                   '%(lftp_target)s'])],
                'http': ['lftp', '-c',
                         ';'.join([_base_buf_str, _login_port_str + \
                                  '%(protocol)s://%(fqdn)s',
                                   '%(lftp_target)s'])],
                'https': ['lftp', '-c',
                          ';'.join([_base_buf_str, _login_port_str + \
                                    '%(protocol)s://%(fqdn)s',
                                    '%(lftp_target)s'])],
                # IMPORTANT: must use explicit http(s) instead of webdav(s)
                'webdav': ['lftp', '-c',
                           ';'.join([_base_buf_str, _login_port_str + \
                                     'http://%(fqdn)s', '%(lftp_target)s'])],
                'webdavs': ['lftp', '-c',
                           ';'.join([_base_buf_str, _login_port_str + \
                                     'https://%(fqdn)s', '%(lftp_target)s'])],
                'rsyncssh': ['rsync', '-e', _rsyncssh_transport_str,
                             _rsync_flags] + _exclude_list + \
                ['%(fqdn)s:%(src)s', '%(dst)s/'],
                },
               'export':
               {'sftp': ['lftp', '-c',
                         ';'.join([_sftp_buf_str, _sftp_key_str,
                                   _login_port_str + 'sftp://%(fqdn)s',
                                   '%(lftp_target)s'])],
                'ftp': ['lftp', '-c',
                        ';'.join([_base_buf_str, _login_port_str + \
                                  'ftp://%(fqdn)s', '%(lftp_target)s'])],
                # IMPORTANT: must be implicit proto or 'ftp://' (not ftps://)
                'ftps': ['lftp', '-c',
                         ';'.join([_base_buf_str, _ftps_ssl_str,
                                   _login_port_str + 'ftp://%(fqdn)s',
                                   '%(lftp_target)s'])],
                'http': ['lftp', '-c',
                         ';'.join([_base_buf_str, _login_port_str + \
                                  '%(protocol)s://%(fqdn)s',
                                   '%(lftp_target)s'])],
                'https': ['lftp', '-c',
                          ';'.join([_base_buf_str, _login_port_str + \
                                    '%(protocol)s://%(fqdn)s',
                                    '%(lftp_target)s'])],
                # IMPORTANT: must use explicit http(s) instead of webdav(s)
                'webdav': ['lftp', '-c',
                           ';'.join([_base_buf_str, _login_port_str + \
                                     'http://%(fqdn)s', '%(lftp_target)s'])],
                'webdavs': ['lftp', '-c',
                           ';'.join([_base_buf_str, _login_port_str + \
                                     'https://%(fqdn)s', '%(lftp_target)s'])],
                'rsyncssh': ['rsync', '-e', _rsyncssh_transport_str,
                             _rsync_flags] + _exclude_list + \
                ['%(fqdn)s:%(src)s', '%(dst)s/'],
                }
               }

    logger.info('run command for %s: %s' % (client_id, transfer_dict))
    transfer_id = transfer_dict['transfer_id']
    action = transfer_dict['action']
    protocol = transfer_dict['protocol']
    if not protocol in cmd_map[action]:
        raise ValueError('unsupported protocol: %s' % protocol)

    client_dir = client_id_dir(client_id)
    
    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep
    command_pattern = cmd_map[action][protocol]
    lftp_target_list = []
    key_path = transfer_dict.get("key", "")
    if key_path:
        # Use key with given name from settings dir
        settings_base_dir = os.path.abspath(os.path.join(
            configuration.user_settings, client_dir)) + os.sep
        key_path = os.path.join(settings_base_dir, user_keys_dir,
                                key_path.lstrip(os.sep))
        key_path = os.path.abspath(key_path)
        if not valid_user_path(key_path, settings_base_dir):
            logger.error('rejecting illegal directory traversal for %s (%s)' \
                         % (key_path, transfer_dict))
            raise ValueError("user provided a key outside own settings!")
    rel_src_list = transfer_dict['src']
    rel_dst = transfer_dict['dst']
    if transfer_dict['action'] in ('import', ):
        logger.info('setting abs dst for action %(action)s' % transfer_dict)
        src_path_list = transfer_dict['src']
        dst_path = os.path.join(base_dir, rel_dst.lstrip(os.sep))
        dst_path = os.path.abspath(dst_path)
        for src in rel_src_list:
            real_dst = os.path.join(dst_path, src.lstrip(os.sep))
            real_dst = os.path.abspath(real_dst)
            # Reject illegal directory traversal and hidden files
            if not valid_user_path(real_dst, base_dir, True):
                logger.error('rejecting illegal directory traversal for %s (%s)' \
                             % (real_dst, transfer_dict))
                raise ValueError("user provided a destination outside home!")
            if src.endswith(os.sep):
                lftp_target_list.append(_get_dir_str)
            else:
                lftp_target_list.append(_get_file_str)
        makedirs_rec(dst_path, configuration)
    elif transfer_dict['action'] in ('export', ):
        logger.info('setting abs src for action %(action)s' % transfer_dict)
        dst_path = transfer_dict['dst']
        src_path_list = []
        for src in rel_src_list:
            src_path = os.path.join(base_dir, src.lstrip(os.sep))
            src_path = os.path.abspath(src_path)
            # Reject illegal directory traversal and hidden files
            if not valid_user_path(src_path, base_dir, True):
                logger.error('rejecting illegal directory traversal for %s (%s)' \
                             % (src, transfer_dict))
                raise ValueError("user provided a source outside home!")
            src_path_list.append(src_path)
            if src.endswith(os.sep) or os.path.isdir(src):
                lftp_target_list.append(_put_dir_str)
            else:
                lftp_target_list.append(_put_file_str)
    else:
        raise ValueError('unsupported action for %(transfer_id)s: %(action)s' \
                         % transfer_dict)
    run_dict = transfer_dict.copy()
    # Use private known hosts file for ssh transfers as explained above
    run_dict['known_hosts'] = os.path.join(base_dir, '.ssh', 'known_hosts')
    if key_path:
        run_dict['key'] = key_path
        run_dict['auth_opt'] = _ssh_key_opt % run_dict
    else:
        run_dict['auth_opt'] = _ssh_pw_opt % run_dict
    run_dict['rel_dst'] = rel_dst
    run_dict['dst'] = dst_path
    run_dict['lftp_buf_size'] = run_dict.get('lftp_buf_size', _lftp_buffer_bytes)
    status = 0
    for (src, rel_src, lftp_target) in zip(src_path_list, rel_src_list,
                                          lftp_target_list):
        run_dict['src'] = src
        run_dict['rel_src'] = rel_src
        run_dict['lftp_target'] = lftp_target % run_dict
        logger.info('setting up %(action)s for %(src)s' % run_dict)
        command_list = [i % run_dict for i in command_pattern]
        logger.info('expanded vars to %s' % run_dict)
        command_str = ' '.join(command_list)
        logger.debug('run %s on behalf of %s' % (command_str, client_id))
        transfer_proc = subprocess_popen(command_list,
                                         stdout=subprocess_pipe,
                                         stderr=subprocess_pipe)
        exit_code = transfer_proc.wait()
        status |= exit_code
        out, err = transfer_proc.communicate()
        logger.info('done running transfer %s: %s' % (run_dict['transfer_id'],
                                                  command_str))
        logger.info('raw output is: %s' % out)
        logger.info('raw error is: %s' % err)
        logger.info('result was %s' % exit_code)
        if not transfer_result(configuration, client_id, run_dict, exit_code,
                               out.replace(base_dir, ''),
                               err.replace(base_dir, '')):
            logger.error('writing transfer status for %s failed' % transfer_id)            

    logger.debug('done handling transfers in %(transfer_id)s' % transfer_dict)
    transfer_dict['exit_code'] = status
    if status == 0:
        transfer_dict['status'] = 'DONE'
    else:
        transfer_dict['status'] = 'FAILED'


def clean_transfer(configuration, client_id, transfer_dict):
    """Actually clean valid transfer request in transfer_dict"""
    transfer_id = transfer_dict['transfer_id']
    logger.info('in cleaning of %s %s for %s' % (transfer_id,
                                                 transfer_dict['action'],
                                                 client_id))
    if all_workers.has_key(transfer_id):
        del all_workers[transfer_id]
    # TODO: clean up any removed transfers/processes here?


def wrap_run_transfer(transfer_dict, client_id, configuration):
    """Wrap the execution of data transfer so that exceptions and errors are
    caught and logged. Updates state, calls the run_transfer function on input
    and finally updates state again afterwards.
    """
    transfer_id = transfer_dict['transfer_id']
    transfer_dict['status'] = "ACTIVE"
    transfer_dict['exit_code'] = -1
    all_transfers[client_id][transfer_id]['status'] = transfer_dict['status']
    (save_status, save_msg) = modify_data_transfers('modify', transfer_dict,
                                                    client_id, configuration)
    if not save_status:
        logger.error("failed to save %s status for %s: %s" % \
                     (transfer_dict['status'], transfer_id, save_msg))
        return save_status
    try:
        run_transfer(transfer_dict, client_id, configuration)
    except Exception, exc:
        configuration.logger.error("run transfer failed: %s" % exc)
        transfer_dict['status'] = "FAILED"
        if not transfer_result(configuration, client_id, transfer_dict,
                               transfer_dict['exit_code'], '',
                               'Fatal error during transfer: %s' % exc):
            logger.error('writing transfer status for %s failed' % transfer_id)

    all_transfers[client_id][transfer_id]['status'] = transfer_dict['status']
    (save_status, save_msg) = modify_data_transfers('modify', transfer_dict,
                                                    client_id, configuration)
    if not save_status:
        logger.error("failed to save %s status for %s: %s" % \
                     (transfer_dict['status'], transfer_id, save_msg))

    status_msg = '%s %s from %s in %s %s with status code %s' % \
                 (transfer_dict['protocol'], transfer_dict['action'],
                  transfer_dict['fqdn'], transfer_id, transfer_dict['status'],
                  transfer_dict['exit_code'])
    if transfer_dict['status'] == 'FAILED':
        transfer_error(configuration, client_id, status_msg)
    else:
        transfer_info(configuration, client_id, status_msg)
    clean_transfer(configuration, client_id, transfer_dict)


def background_transfer(transfer_dict, client_id, configuration):
    """Run a transfer in the background so that it can block without
    stopping further transfer handling.
    """

    worker = threading.Thread(target=wrap_run_transfer, args=(transfer_dict,
                                                              client_id,
                                                              configuration))
    worker.daemon = True
    worker.start()
    all_workers[transfer_dict['transfer_id']] = worker


def foreground_transfer(transfer_dict, client_id, configuration):
    """Run a transfer in the foreground so that it can block without
    stopping further transfer handling.
    """
    wrap_run_transfer(transfer_dict, client_id, configuration)
    all_workers[transfer_dict['transfer_id']] = None

def handle_transfer(configuration, client_id, transfer_dict):
    """Actually handle valid transfer request in transfer_dict"""

    logger.info('in handling of %s %s for %s' % (transfer_dict['transfer_id'],
                                                 transfer_dict['action'],
                                                 client_id))
    transfer_info(configuration, client_id,
                  'handle %s %s' % (transfer_dict['transfer_id'],
                                    transfer_dict['action']))

    try:
        # Switch to foreground here for easier debugging
        #foreground_transfer(transfer_dict, client_id, configuration)
        background_transfer(transfer_dict, client_id, configuration)
    except Exception, exc:
        logger.error('failed to run %s %s from %s: %s (%s)'
                     % (transfer_dict['protocol'], transfer_dict['action'],
                        transfer_dict['fqdn'], exc, transfer_dict))
        transfer_error(configuration, client_id,
                       'failed to run %s %s from %s: %s' % \
                       (transfer_dict['protocol'], transfer_dict['action'],
                        transfer_dict['fqdn'], exc))


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
            continue
        logger.debug('handling update of transfers file: %s' % transfers_path)
        abs_client_dir = os.path.dirname(transfers_path)
        client_dir = os.path.basename(abs_client_dir)
        logger.debug('extracted client dir: %s' % client_dir)
        client_id = client_dir_id(client_dir)
        logger.debug('loading transfers for: %s' % client_id)
        (load_status, transfers) = load_data_transfers(configuration,
                                                       client_id)
        if not load_status:
            logger.error('could not load transfer for path: %s' % \
                          transfers_path)
            continue
            
        logger.debug("loaded current transfers from '%s':\n%s" % \
                     (transfers_path, transfers))

        old_transfers[client_id] = all_transfers.get(client_id, {})
        all_transfers[client_id] = transfers

    logger.debug('all transfers:\n%s' % all_transfers)
    for (client_id, transfers) in all_transfers.items():
        for (transfer_id, transfer_dict) in transfers.items():
            transfer_status = transfer_dict['status']
            if transfer_status in ("DONE", "FAILED", "PAUSED"):
                logger.debug('skip %(status)s transfer %(transfer_id)s' % \
                             transfer_dict)
                continue
            if transfer_status in ("ACTIVE", ) and \
                   all_workers.has_key(transfer_id):
                logger.debug('wait for %(status)s transfer %(transfer_id)s' % \
                             transfer_dict)
                continue
            logger.debug('handle %(status)s transfer %(transfer_id)s' % \
                         transfer_dict)
            handle_transfer(configuration, client_id, transfer_dict)

    for (client_id, transfers) in old_transfers.items():
        for (transfer_id, transfer_dict) in transfers.items():
            if transfer_dict['status'] in ("ACTIVE", "PAUSE", ) and \
                   not transfer_id in all_transfers.get(client_id, {}).keys():
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

            time.sleep(30)
        except KeyboardInterrupt:
            keep_running = False
        except Exception, exc:
            print 'Caught unexpected exception: %s' % exc

    print 'Data transfer handler daemon shutting down'
    logger.info('Stop data transfer handler daemon')
    sys.exit(0)
