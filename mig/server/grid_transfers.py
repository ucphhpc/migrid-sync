#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# grid_transfers - transfer handler to run background data transfers
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

from __future__ import print_function
from __future__ import absolute_import

from builtins import zip
import datetime
import glob
import logging
import logging.handlers
import multiprocessing
import os
import signal
import sys
import time
import traceback

from mig.shared.base import client_dir_id, client_id_dir, force_native_str
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import datatransfers_filename, transfers_log_size, \
    transfers_log_cnt, user_keys_dir, _user_invisible_paths
from mig.shared.fileio import makedirs_rec, pickle
from mig.shared.logger import daemon_logger, register_hangup_handler
from mig.shared.notification import notify_user_thread
from mig.shared.pwhash import unscramble_digest, fernet_decrypt_password
from mig.shared.safeeval import subprocess_popen, subprocess_pipe, \
    subprocess_list2cmdline
from mig.shared.transferfunctions import blind_pw, load_data_transfers, \
    update_data_transfer, get_status_dir, sub_pid_list, add_sub_pid, \
    del_sub_pid, kill_sub_pid, add_worker_transfer, del_worker_transfer, \
    all_worker_transfers, get_worker_transfer
from mig.shared.validstring import valid_user_path

# Global helper dictionaries with requests for all users

all_transfers = {}
all_workers = {}
sub_pid_map = None
stop_running = multiprocessing.Event()
(configuration, logger, last_update) = (None, None, 0)

# Tune default lftp buffer size - the built-in size is 32k, but a 128k buffer
# was experimentally determined to provide significantly better throughput on
# fast networks:
# http://www.lucidpixels.com/blog/optimizationsforlftpon10gbenetworks
# Our own experiments also point to 128k improving performance by about 25%
# while further increasin the buffer size adds no clear gain.
lftp_buffer_bytes = 131072
# Tune default lftp block size for sftp - experimentally determined for good
# throughput. Our experiments show a 5-10% performance increase with 64k over
# the default 32k size.
# Please note that lftp runs into a bug if requesting more than 64k for sftp
# e.g. something like "mirror: basic: file size decreased during transfer"
# and the resulting file turning up corrupted.
lftp_sftp_block_bytes = 65536
# Special marker for rsync excludes on list form
RSYNC_EXCLUDES_LIST = '__RSYNC_EXCLUDES_LIST__'


def stop_handler(signal, frame):
    """A simple signal handler to quit on Ctrl+C (SIGINT) in main"""
    # Print blank line to avoid mix with Ctrl-C line
    print('')
    stop_running.set()


def __transfer_log(configuration, client_id, msg, level='info'):
    """Wrapper to send a single msg to transfer log file of client_id"""
    status_dir = get_status_dir(configuration, client_id)
    log_path = os.path.join(status_dir, configuration.site_transfer_log)
    makedirs_rec(os.path.dirname(log_path), configuration)
    transfers_logger = logging.getLogger('background-transfer')
    transfers_logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=transfers_log_size, backupCount=transfers_log_cnt-1)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
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
    time_stamp = datetime.datetime.now().ctime()
    transfer_id = transfer_dict['transfer_id']
    rel_src = transfer_dict.get("rel_src", False)
    if not rel_src:
        rel_src = ', '.join(transfer_dict['src'])
    res_dir = get_status_dir(configuration, client_id, transfer_id)
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
        except Exception as exc:
            logger.error("writing status file %s for %s failed: %s" %
                         (path, blind_pw(transfer_dict), exc))
            status = False
    return status


def get_ssh_auth(pubkey_auth, transfer_dict=None):
    """Generate robust command line options for ssh-based transfers.

    The pubkey_auth argument is a boolean indicating if the login relies on
    public key authentication. Otherwise the options for password
    authentication are returned.
    If transfer_dict is set it will be used to expand the variables in the
    resulting string.

    Make sure we don't get bitten by any restrictive system-wide or
    account-specific ssh settings. Also use a known_hosts file for client_id
    to avoid polluting the known hosts file of the UNIX account user, while
    allowing looser host key checking to avoid common host key errors.
    """
    ssh_auth = "-oForwardAgent=no -oForwardX11=no"
    ssh_auth += " -oStrictHostKeyChecking=no "
    ssh_auth += " -oUserKnownHostsFile=%(known_hosts)s"
    if pubkey_auth:
        ssh_auth += " -oPasswordAuthentication=no"
        ssh_auth += " -oPubkeyAuthentication=yes -i %(key)s"
    else:
        ssh_auth += " -oPubkeyAuthentication=no"
        ssh_auth += " -oPasswordAuthentication=yes"
    if transfer_dict is not None:
        ssh_auth = ssh_auth % transfer_dict
    return ssh_auth


def get_ssl_auth(pki_auth, transfer_dict=None):
    """Generate robust command line options for ssl-based transfers.

    The keycert_auth argument is a boolean indicating if the login relies on
    PKI authentication with a user key and certificate. Otherwise the options
    for password authentication are returned.
    If transfer_dict is set it will be used to expand the variables in the
    resulting string.
    """
    ssl_auth = ""
    if pki_auth:
        ssl_auth += "set ssl:key-file %(key)s;set ssl:cert-file %(cert)s"
    if transfer_dict is not None:
        ssl_auth = ssl_auth % transfer_dict
    return ssl_auth


def get_exclude_list(keyword, sep_char, to_string, user_excludes=[]):
    """Get an excludes helper for filtered transfers. The keyword argument is
    inserted for each exclude entry. The sep_char argument is used to separate
    the keyword and the value to be excluded. If to_string is set the result is
    a string and otherwise the excludes are returned on list form.
    The optional list of user_excludes is explicitly prepended to the system
    default excludes so that they can't override or reset the latter.
    NOTE: list is passed into subprocess without shell interpretation so
    quoting is NOT needed, and in fact would break the excludes.
    """
    exc_pattern = '%s%s%%s' % (keyword, sep_char)
    all_excludes = user_excludes + _user_invisible_paths
    if to_string:
        return ' '.join([exc_pattern % i for i in all_excludes])
    else:
        return [exc_pattern % i for i in all_excludes]


def get_lftp_target(is_import, is_file, user_excludes=[]):
    """Get a target helper for lftp-based transfers. The is_import argument is
    used to distinguish the direction and the is_file argument decides whether
    to use a plain get/put or a mirror command. We try to continue/resume
    transfers in any case.
    The optional list of user_excludes is passed more or less verbatim to the
    underlying command.
    Returns a 3-tuple of lists containing args, excludes and source+dst
    suitable for eventually plugging into the command list from command map.
    """
    lftp_args = []
    src = '%(src)s'
    dst = '%(dst)s/'
    # Pack all login and address into src to avoid problems with e.g. Amazon S3
    # refusing explicit open on base URL first.
    remote = '%(protocol)s://%(username)s:%(password)s@%(fqdn)s:%(port)s/'
    if is_import:
        src = remote + src
    else:
        dst = remote + dst

    if is_file:
        # NOTE: no exclude list for single file, but we already filter illegal
        #       paths in main import/export loop, so we only need to worry
        #       about implicit ones from recursive transfers.
        exclude_list = []
        # Make sure to protect exotic chars from interpretation by lftp/shell
        transfer_target = ["-O '%s'" % dst, "'%s'" % src]
        if is_import:
            lftp_args += ["get", "-c"]
        else:
            lftp_args += ["put", "-c"]
    else:
        # NOTE: we actively filter illegal paths from these recursive transfers
        # There's a slight difference in the handling of exclude in lftp and
        # rsync with the former using regex and the latter using glob by
        # default. It is not obvious to unify the format in either way.
        exclude_list = get_exclude_list('--exclude', ' ', False,
                                        user_excludes)
        # IMPORTANT: Use Resume, follow symlinks and keep all but suid perms.
        #            We DON'T preserve device files, owner/group and can't
        #            preserve timestamps.
        lftp_args += ["mirror", "-cLv"]
        # Make sure to protect exotic chars from interpretation by lftp/shell
        transfer_target = ["'%s'" % src, "'%s'" % dst]
        # Add reverse direction flag for export
        if not is_import:
            lftp_args += ["-R"]
    return (lftp_args, exclude_list, transfer_target)


def get_rsync_target(is_import, is_file, user_excludes=[], compress=False):
    """Get target helpers for rsync-based transfers. The is_import argument is
    used to distinguish the direction and the is_file argument decides whether
    to use a plain or recursive transfer command. Basically we could always
    use recursive for rsync, but we explicitly set it for symmetry with the
    lftp commands.
    The optional list of user_excludes is passed more or less verbatim to the
    underlying command.
    The optional compress option specifies if the compression flag should be
    enabled.
    Returns a 3-tuple of lists containing flags, excludes and source+dst
    suitable for eventually plugging into the command list from command map.
    """
    # IMPORTANT: Follow symlinks, preserve executability and timestamps.
    #            We DON'T preserve device files, owner/group and other perms.
    # NOTE: enabling -S (efficient sparse file handling) kills performance.
    rsync_args = ['-LEt']
    if not is_file:
        rsync_args[0] += 'r'
    if compress:
        rsync_args[0] += 'z'
    # NOTE: enable argument protection in protocol instead of quoting src/dst
    rsync_args[0] += 's'
    # NOTE: we actively filter illegal paths from all rsync transfers
    exclude_list = get_exclude_list('--exclude', '=', False, user_excludes)
    # NOTE: rsync fails with explicit quotes in the path on remote side if we
    #       use the same quoting here as with lftp. We leave them out and rely
    #       on subprocess without shell locally and protect args flag remotely.
    #       Not that we care too much about what the remote shell does anyway.
    if is_import:
        transfer_target = ["%(fqdn)s:%(src)s", "%(dst)s/"]
    else:
        transfer_target = ["%(src)s", "%(fqdn)s:%(dst)s/"]
    return (rsync_args, exclude_list, transfer_target)


def get_cmd_map():
    """Get a lookup map of commands for the transfers"""
    # Helpers for lftp and rsync
    # NOTE: net:socket-buffer tuning seems to have no significant effect
    lftp_core_opts = "set xfer:buffer-size %(lftp_buf_size)d"
    lftp_core_opts += ";set dns:fatal-timeout 60;set dns:max-retries 3"
    lftp_core_opts += ";set cmd:fail-exit on;set bmk:save-passwords off"
    lftp_core_opts += ";set net:max-retries 3;set net:persist-retries 3"
    # TODO: can lftp be configured to not leak fs layout in log?
    lftp_core_opts += ";set net:timeout 60;set xfer:log-file %(log_path)s"
    rsync_core_opts = ["--log-file=%(log_path)s", "--verbose"]
    # Bump sftp buffer from default 32k to improve throughput, and bump max
    # number of packets in transit from 16 to 64 for additional gains.
    sftp_buf_str = "set sftp:max-packets-in-flight 64"
    for target in ("read", "write"):
        sftp_buf_str += ";set sftp:size-%s %%(lftp_sftp_block_size)d" % target
    # TODO: switch to GET/PUT rather than PROPFIND/MKCOL for basic HTTP(S)?
    #http_tweak_str = "set http:use-propfind off;set http:use-mkcol off"
    http_tweak_str = ""
    webdav_tweak_str = "set http:use-propfind on;set http:use-mkcol on"
    base_ssl_str = "%(ssl_auth)s"
    ftps_ssl_str = "set ftp:ssl-force;set ftp:ssl-protect-data on"
    sftp_key_str = "set sftp:connect-program ssh -a -x %(ssh_auth)s"
    # All the port and login settings must be passed to ssh command
    rsyncssh_transport_str = "ssh -p %(port)s -l %(username)s %(ssh_auth)s"

    # Command helpers
    # Empty password is fine here and won't interfere with key auth.
    # NOTE: lftp at CentOS was tested to work with commands like these
    # lftp -c "set xfer:buffer-size $BUFSIZE ; set sftp:size-read $BUFSIZE ; set sftp:size-write $BUFSIZE ; get -O /tmp sftp://USERNAME:PW@io.erda.dk:22/build/dblzeros.bin"
    # lftp -c "set xfer:buffer-size $BUFSIZE; set ftp:ssl-force ; set ftp:ssl-protect-data on ; get -O /tmp ftp://USERNAME:PW@io.erda.dk:8021/welcome.txt"
    # or the explicit open version, which we don't want since it fails for S3
    # lftp -c "set xfer:buffer-size $BUFSIZE ; set sftp:size-read $BUFSIZE ; set sftp:size-write $BUFSIZE ; open -u USERNAME,PW -p 22 sftp://io.erda.dk ; get -O build/ build/dblzeros.bin"
    # lftp -c "set xfer:buffer-size $BUFSIZE; set ftp:ssl-force ; set ftp:ssl-protect-data on ; open -u USERNAME,PW -p 8021 ftp://io.erda.dk ; get -O /tmp welcome.txt"

    cmd_map = {'import':
               {'sftp': ['lftp', '-c',
                         ';'.join([lftp_core_opts, sftp_buf_str, sftp_key_str,
                                   ' '.join(['%(lftp_args)s',
                                             '%(lftp_excludes)s',
                                             '%(lftp_src)s', '%(lftp_dst)s'])
                                   ])],
                'ftp': ['lftp', '-c',
                        ';'.join([lftp_core_opts,
                                  ' '.join(['%(lftp_args)s',
                                            '%(lftp_excludes)s',
                                            '%(lftp_src)s', '%(lftp_dst)s'])
                                  ])],
                'ftps': ['lftp', '-c',
                         ';'.join([lftp_core_opts, base_ssl_str, ftps_ssl_str,
                                   ' '.join(['%(lftp_args)s',
                                             '%(lftp_excludes)s',
                                             '%(lftp_src)s', '%(lftp_dst)s'])
                                   ])],
                'http': ['lftp', '-c',
                         ';'.join([lftp_core_opts, http_tweak_str,
                                   ' '.join(['%(lftp_args)s',
                                             '%(lftp_excludes)s',
                                             '%(lftp_src)s', '%(lftp_dst)s'])
                                   ])],
                'https': ['lftp', '-c',
                          ';'.join([lftp_core_opts, http_tweak_str,
                                    base_ssl_str,
                                    ' '.join(['%(lftp_args)s',
                                              '%(lftp_excludes)s',
                                              '%(lftp_src)s', '%(lftp_dst)s'])
                                    ])],
                'webdav': ['lftp', '-c',
                           ';'.join([lftp_core_opts, webdav_tweak_str,
                                     ' '.join(['%(lftp_args)s',
                                               '%(lftp_excludes)s',
                                               '%(lftp_src)s', '%(lftp_dst)s'])
                                     ])],
                'webdavs': ['lftp', '-c',
                            ';'.join([lftp_core_opts, webdav_tweak_str,
                                      base_ssl_str,
                                      ' '.join(['%(lftp_args)s',
                                                '%(lftp_excludes)s',
                                                '%(lftp_src)s', '%(lftp_dst)s'])
                                      ])],
                'rsyncssh': ['rsync', '-e', rsyncssh_transport_str] +
                rsync_core_opts + ['%(rsync_args)s', RSYNC_EXCLUDES_LIST,
                                   '%(rsync_src)s', '%(rsync_dst)s'],
                'rsyncd': ['rsync'] + rsync_core_opts +
                ['%(rsync_args)s', RSYNC_EXCLUDES_LIST,
                 '%(rsync_src)s', '%(rsync_dst)s'],
                },
               'export':
               {'sftp': ['lftp', '-c',
                         ';'.join([lftp_core_opts, sftp_buf_str, sftp_key_str,
                                   ' '.join(['%(lftp_args)s',
                                             '%(lftp_excludes)s',
                                             '%(lftp_src)s', '%(lftp_dst)s'])
                                   ])],
                'ftp': ['lftp', '-c',
                        ';'.join([lftp_core_opts,
                                  ' '.join(['%(lftp_args)s',
                                            '%(lftp_excludes)s',
                                            '%(lftp_src)s', '%(lftp_dst)s'])
                                  ])],
                'ftps': ['lftp', '-c',
                         ';'.join([lftp_core_opts, base_ssl_str, ftps_ssl_str,
                                   ' '.join(['%(lftp_args)s',
                                             '%(lftp_excludes)s',
                                             '%(lftp_src)s', '%(lftp_dst)s'])
                                   ])],
                'http': ['lftp', '-c',
                         ';'.join([lftp_core_opts, http_tweak_str,
                                   ' '.join(['%(lftp_args)s',
                                             '%(lftp_excludes)s',
                                             '%(lftp_src)s', '%(lftp_dst)s'])
                                   ])],
                'https': ['lftp', '-c',
                          ';'.join([lftp_core_opts, http_tweak_str, base_ssl_str,
                                    ' '.join(['%(lftp_args)s',
                                              '%(lftp_excludes)s',
                                              '%(lftp_src)s', '%(lftp_dst)s'])
                                    ])],
                'webdav': ['lftp', '-c',
                           ';'.join([lftp_core_opts, webdav_tweak_str,
                                     ' '.join(['%(lftp_args)s',
                                               '%(lftp_excludes)s',
                                               '%(lftp_src)s', '%(lftp_dst)s'])
                                     ])],
                'webdavs': ['lftp', '-c',
                            ';'.join([lftp_core_opts, webdav_tweak_str,
                                      base_ssl_str,
                                      ' '.join(['%(lftp_args)s',
                                                '%(lftp_excludes)s',
                                                '%(lftp_src)s', '%(lftp_dst)s'])
                                      ])],
                'rsyncssh': ['rsync', '-e', rsyncssh_transport_str] +
                rsync_core_opts + ['%(rsync_args)s', RSYNC_EXCLUDES_LIST,
                                   '%(rsync_src)s', '%(rsync_dst)s'],
                'rsyncd': ['rsync'] + rsync_core_opts +
                ['%(rsync_args)s', RSYNC_EXCLUDES_LIST,
                 '%(rsync_src)s', '%(rsync_dst)s'],
                }
               }
    return cmd_map


def run_transfer(configuration, client_id, transfer_dict):
    """Actual data transfer built from transfer_dict on behalf of client_id"""

    logger.debug('run transfer for %s: %s' % (client_id,
                                              blind_pw(transfer_dict)))
    transfer_id = transfer_dict['transfer_id']
    action = transfer_dict['action']
    protocol = transfer_dict['protocol']
    status_dir = get_status_dir(configuration, client_id, transfer_id)
    cmd_map = get_cmd_map()
    if not protocol in cmd_map[action]:
        raise ValueError('unsupported protocol: %s' % protocol)

    client_dir = client_id_dir(client_id)
    makedirs_rec(status_dir, configuration)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep
    # TODO: we should refactor to move command extraction into one function
    command_pattern = cmd_map[action][protocol]
    target_helper_list = []
    key_path = transfer_dict.get("key", "")
    if key_path:
        # Use key with given name from settings dir
        settings_base_dir = os.path.abspath(os.path.join(
            configuration.user_settings, client_dir)) + os.sep
        key_path = os.path.join(settings_base_dir, user_keys_dir,
                                key_path.lstrip(os.sep))
        # IMPORTANT: path must be expanded to abs for proper chrooting
        key_path = os.path.abspath(key_path)
        if not valid_user_path(configuration, key_path, settings_base_dir):
            logger.error('rejecting illegal directory traversal for %s (%s)'
                         % (key_path, blind_pw(transfer_dict)))
            raise ValueError("user provided a key outside own settings!")
    rel_src_list = transfer_dict['src']
    rel_dst = transfer_dict['dst']
    compress = transfer_dict.get("compress", False)
    exclude = transfer_dict.get("exclude", [])
    if transfer_dict['action'] in ('import', ):
        logger.debug('setting abs dst for action %(action)s' % transfer_dict)
        src_path_list = transfer_dict['src']
        dst_path = os.path.join(base_dir, rel_dst.lstrip(os.sep))
        dst_path = os.path.abspath(dst_path)
        for src in rel_src_list:
            abs_dst = os.path.join(dst_path, src.lstrip(os.sep))
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_dst = os.path.abspath(abs_dst)
            # Reject illegal directory traversal and hidden files
            if not valid_user_path(configuration, abs_dst, base_dir, True):
                logger.error('rejecting illegal directory traversal for %s (%s)'
                             % (abs_dst, blind_pw(transfer_dict)))
                raise ValueError("user provided a destination outside home!")
            if src.endswith(os.sep):
                target_helper_list.append((get_lftp_target(True, False,
                                                           exclude),
                                           get_rsync_target(True, False,
                                                            exclude,
                                                            compress)))
            else:
                target_helper_list.append((get_lftp_target(True, True,
                                                           exclude),
                                           get_rsync_target(True, True,
                                                            exclude,
                                                            compress)))
        makedirs_rec(dst_path, configuration)
    elif transfer_dict['action'] in ('export', ):
        logger.debug('setting abs src for action %(action)s' % transfer_dict)
        dst_path = transfer_dict['dst']
        src_path_list = []
        for src in rel_src_list:
            src_path = os.path.join(base_dir, src.lstrip(os.sep))
            # IMPORTANT: path must be expanded to abs for proper chrooting
            src_path = os.path.abspath(src_path)
            # Reject illegal directory traversal and hidden files
            if not valid_user_path(configuration, src_path, base_dir, True):
                logger.error('rejecting illegal directory traversal for %s (%s)'
                             % (src, blind_pw(transfer_dict)))
                raise ValueError("user provided a source outside home!")
            src_path_list.append(src_path)
            if src.endswith(os.sep) or os.path.isdir(src):
                target_helper_list.append((get_lftp_target(False, False,
                                                           exclude),
                                           get_rsync_target(False, False,
                                                            exclude,
                                                            compress)))
            else:
                target_helper_list.append((get_lftp_target(False, True,
                                                           exclude),
                                           get_rsync_target(False, True,
                                                            exclude,
                                                            compress)))
    else:
        raise ValueError('unsupported action for %(transfer_id)s: %(action)s'
                         % transfer_dict)
    run_dict = transfer_dict.copy()
    run_dict['log_path'] = os.path.join(status_dir, 'transfer.log')
    # Use private known hosts file for ssh transfers as explained above
    # NOTE: known_hosts containing '=' silently leads to rest getting ignored!
    #       use /dev/null to skip host key verification completely for now.
    #run_dict['known_hosts'] = os.path.join(base_dir, '.ssh', 'known_hosts')
    run_dict['known_hosts'] = '/dev/null'
    # Make sure password is set to empty string as default
    run_dict['password'] = run_dict.get('password', '')
    # TODO: this is a bogus cert path for now - we don't support ssl certs
    run_dict['cert'] = run_dict.get('cert', '')
    # IMPORTANT: must be implicit proto or 'ftp://' (not ftps://) and similarly
    #            webdav(s) must use explicit http(s) instead. In both cases we
    #            replace protocol between cmd selection and lftp path expansion
    if run_dict['protocol'] == 'ftps':
        run_dict['orig_proto'] = run_dict['protocol']
        run_dict['protocol'] = 'ftp'
        logger.info('force %(orig_proto)s to %(protocol)s for %(transfer_id)s'
                    % run_dict)
    elif run_dict['protocol'].startswith('webdav'):
        run_dict['orig_proto'] = run_dict['protocol']
        run_dict['protocol'] = run_dict['protocol'].replace('webdav', 'http')
        logger.info('force %(orig_proto)s to %(protocol)s for %(transfer_id)s'
                    % run_dict)
    if key_path:
        rel_key = run_dict['key']
        rel_cert = run_dict['cert']
        run_dict['key'] = key_path
        run_dict['cert'] = key_path.replace(rel_key, rel_cert)
        run_dict['ssh_auth'] = get_ssh_auth(True, run_dict)
        run_dict['ssl_auth'] = get_ssl_auth(True, run_dict)
    else:
        # Extract encrypted or digest password if set
        password_encrypted = run_dict.get('password_encrypted', '')
        password_digest = run_dict.get('password_digest', '')
        if password_encrypted:
            run_dict['password'] = fernet_decrypt_password(configuration,
                                                           password_encrypted)
        elif password_digest:
            _, _, _, payload = password_digest.split("$")
            unscrambled = unscramble_digest(configuration.site_digest_salt,
                                            payload)
            _, _, password = unscrambled.split(":")
            run_dict['password'] = password
        run_dict['ssh_auth'] = get_ssh_auth(False, run_dict)
        run_dict['ssl_auth'] = get_ssl_auth(False, run_dict)
    run_dict['rel_dst'] = rel_dst
    run_dict['dst'] = dst_path
    run_dict['lftp_buf_size'] = run_dict.get('lftp_buf_size',
                                             lftp_buffer_bytes)
    run_dict['lftp_sftp_block_size'] = run_dict.get('sftp_sftp_block_size',
                                                    lftp_sftp_block_bytes)
    status = 0
    for (src, rel_src, target_helper) in zip(src_path_list, rel_src_list,
                                             target_helper_list):
        (lftp_target, rsync_target) = target_helper
        logger.debug('setting up %(action)s for %(src)s' % run_dict)
        if run_dict['protocol'] == 'sftp' and not os.path.isabs(src):
            # NOTE: lftp interprets sftp://FQDN/SRC as absolute path /SRC
            #       We force relative paths into user home with a tilde.
            #       The resulting sftp://FQDN/~/SRC looks funky but works.
            run_dict['src'] = "~/%s" % src
        else:
            # All other paths are probably absolute or auto-chrooted anyway
            run_dict['src'] = src
        run_dict['rel_src'] = rel_src
        run_dict['lftp_args'] = ' '.join(lftp_target[0]) % run_dict
        run_dict['lftp_excludes'] = ' '.join(lftp_target[1])
        # src and dst may actually be reversed for lftp, but for symmetry ...
        run_dict['lftp_src'] = lftp_target[2][0] % run_dict
        run_dict['lftp_dst'] = lftp_target[2][1] % run_dict
        run_dict['rsync_args'] = ' '.join(rsync_target[0]) % run_dict
        # Preserve excludes on list form for rsync, where it matters
        run_dict[RSYNC_EXCLUDES_LIST] = rsync_target[1]
        run_dict['rsync_src'] = rsync_target[2][0] % run_dict
        run_dict['rsync_dst'] = rsync_target[2][1] % run_dict
        blind_dict = blind_pw(run_dict)
        logger.debug('expanded vars to %s' % blind_dict)
        # NOTE: Make sure NOT to break rsync excludes on list form as they
        # won't work if concatenated to a single string in command_list!
        command_list, blind_list = [], []
        for i in command_pattern:
            if i == RSYNC_EXCLUDES_LIST:
                command_list += run_dict[RSYNC_EXCLUDES_LIST]
                blind_list += run_dict[RSYNC_EXCLUDES_LIST]
            else:
                command_list.append(i % run_dict)
                blind_list.append(i % blind_dict)
        command_str = ' '.join(command_list)
        # NOTE: we wrap list entries in quotes for usable log line
        blind_str = subprocess_list2cmdline(blind_list)
        logger.info('run %s on behalf of %s' % (blind_str, client_id))
        transfer_proc = subprocess_popen(command_list,
                                         stdout=subprocess_pipe,
                                         stderr=subprocess_pipe)
        # Save transfer_proc.pid for use in clean up during shutdown
        # in that way we can resume pretty smoothly in next run.
        sub_pid = transfer_proc.pid
        logger.info('%s %s running transfer process %s' % (client_id,
                                                           transfer_id,
                                                           sub_pid))
        add_sub_pid(configuration, sub_pid_map, client_id, transfer_id,
                    sub_pid)
        out, err = transfer_proc.communicate()
        # NOTE: process output is on system bytecode format and we need string
        out, err = force_native_str(out), force_native_str(err)
        exit_code = transfer_proc.wait()
        status |= exit_code
        del_sub_pid(configuration, sub_pid_map, client_id, transfer_id,
                    sub_pid)
        logger.info('done running transfer %s: %s' % (transfer_id, blind_str))
        logger.debug('raw output is: %s' % out)
        logger.debug('raw error is: %s' % err)
        logger.debug('result was %s' % exit_code)
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


def clean_transfer(configuration, client_id, transfer_id, force=False):
    """Actually clean transfer worker from client_id and transfer_id"""
    logger.debug('in cleaning of %s %s' % (client_id, transfer_id))
    worker = get_worker_transfer(configuration, all_workers, client_id,
                                 transfer_id)
    logger.debug('cleaning worker %s for %s %s' % (worker, client_id,
                                                   transfer_id))
    del_worker_transfer(configuration, all_workers, client_id, transfer_id)
    sub_procs = sub_pid_list(configuration, sub_pid_map, client_id,
                             transfer_id)
    logger.debug('cleaning sub procs %s for %s %s' % (sub_procs, client_id,
                                                      transfer_id))
    for sub_pid in sub_procs:
        if not force:
            logger.warning('left-over child in %s %s: %s' %
                           (client_id, transfer_id, sub_procs))
        if not kill_sub_pid(configuration, client_id, transfer_id, sub_pid):
            logger.error('could not terminate child process in %s %s: %s' %
                         (client_id, transfer_id, sub_procs))
        del_sub_pid(configuration, sub_pid_map, client_id, transfer_id,
                    sub_pid)


def wrap_run_transfer(configuration, client_id, transfer_dict):
    """Wrap the execution of data transfer so that exceptions and errors are
    caught and logged. Updates state, calls the run_transfer function on input
    and finally updates state again afterwards.
    """
    transfer_id = transfer_dict['transfer_id']
    transfer_dict['status'] = "ACTIVE"
    transfer_dict['exit_code'] = -1
    all_transfers[client_id][transfer_id]['status'] = transfer_dict['status']
    (save_status, save_msg) = update_data_transfer(configuration, client_id,
                                                   transfer_dict)
    if not save_status:
        logger.error("failed to save %s status for %s: %s" %
                     (transfer_dict['status'], transfer_id, save_msg))
        return save_status
    try:
        run_transfer(configuration, client_id, transfer_dict)
    except Exception as exc:
        logger.error("run transfer failed: %s" % exc)
        logger.error(traceback.format_exc())
        transfer_dict['status'] = "FAILED"
        if not transfer_result(configuration, client_id, transfer_dict,
                               transfer_dict['exit_code'], '',
                               'Fatal error during transfer: %s' % exc):
            logger.error('writing transfer status for %s failed' % transfer_id)

    all_transfers[client_id][transfer_id]['status'] = transfer_dict['status']
    (save_status, save_msg) = update_data_transfer(configuration, client_id,
                                                   transfer_dict)
    if not save_status:
        logger.error("failed to save %s status for %s: %s" %
                     (transfer_dict['status'], transfer_id, save_msg))

    status_msg = '%s %s from %s in %s %s with status code %s' % \
                 (transfer_dict['protocol'], transfer_dict['action'],
                  transfer_dict['fqdn'], transfer_id, transfer_dict['status'],
                  transfer_dict['exit_code'])
    if transfer_dict['status'] == 'FAILED':
        transfer_error(configuration, client_id, status_msg)
    else:
        transfer_info(configuration, client_id, status_msg)
    notify = transfer_dict.get('notify', False)
    if notify:
        job_dict = {'NOTIFY': [notify], 'JOB_ID': 'NOJOBID',
                    'USER_CERT': client_id}
        job_dict.update(transfer_dict)
        logger.info("notify for %(transfer_id)s: %(notify)s" % transfer_dict)
        notifier = notify_user_thread(
            job_dict, [transfer_id, job_dict['status'], status_msg],
            'TRANSFERCOMPLETE', logger, '', configuration)
        # Try finishing delivery but do not block forever on one message
        notifier.join(30)
    logger.info("finished wrap run transfer %(transfer_id)s" % transfer_dict)


def background_transfer(configuration, client_id, transfer_dict):
    """Run a transfer in the background so that it can block without
    stopping further transfer handling.
    """
    transfer_id = transfer_dict['transfer_id']
    worker = multiprocessing.Process(target=wrap_run_transfer,
                                     args=(configuration, client_id,
                                           transfer_dict))
    worker.start()
    add_worker_transfer(configuration, all_workers, client_id, transfer_id,
                        worker)


def foreground_transfer(configuration, client_id, transfer_dict):
    """Run a transfer in the foreground so that it can block without
    stopping further transfer handling.
    """
    transfer_id = transfer_dict['transfer_id']
    add_worker_transfer(configuration, all_workers, client_id, transfer_id,
                        None)
    wrap_run_transfer(configuration, client_id, transfer_dict)
    del_worker_transfer(configuration, all_workers, client_id, transfer_id)


def handle_transfer(configuration, client_id, transfer_dict):
    """Actually handle valid transfer request in transfer_dict"""
    logger.debug('in handling of %s %s for %s' % (transfer_dict['transfer_id'],
                                                  transfer_dict['action'],
                                                  client_id))
    if transfer_dict['status'] == "ACTIVE":
        msg = 'transfer service restarted: resume interrupted %(transfer_id)s '
        msg += '%(action)s (please ignore any recent log errors)'
    else:
        msg = 'start %(transfer_id)s %(action)s'
    transfer_info(configuration, client_id, msg % transfer_dict)

    try:
        # Switch to foreground here for easier debugging
        #foreground_transfer(configuration, client_id, transfer_dict)
        background_transfer(configuration, client_id, transfer_dict)
    except Exception as exc:
        logger.error('failed to run %s %s from %s: %s (%s)'
                     % (transfer_dict['protocol'], transfer_dict['action'],
                        transfer_dict['fqdn'], exc, blind_pw(transfer_dict)))
        transfer_error(configuration, client_id,
                       'failed to run %s %s from %s: %s' %
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
            # logger.debug('skip transfer update for unchanged path: %s' % \
            #              transfers_path)
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
            logger.error('could not load transfer for path: %s' %
                         transfers_path)
            continue

        old_transfers[client_id] = all_transfers.get(client_id, {})
        all_transfers[client_id] = transfers

    for (client_id, transfers) in all_transfers.items():
        for (transfer_id, transfer_dict) in transfers.items():
            #logger.debug('inspecting transfer:\n%s' % blind_pw(transfer_dict))
            transfer_status = transfer_dict['status']
            if transfer_status in ("DONE", "FAILED", "PAUSED"):
                # logger.debug('skip %(status)s transfer %(transfer_id)s' % \
                #             transfer_dict)
                continue
            if transfer_status in ("ACTIVE", ):
                if get_worker_transfer(configuration, all_workers, client_id,
                                       transfer_id):
                    logger.debug('wait for transfer %(transfer_id)s' %
                                 transfer_dict)
                    continue
                else:
                    logger.info('restart transfer %(transfer_id)s' %
                                transfer_dict)
            logger.info('handle %(status)s transfer %(transfer_id)s' %
                        transfer_dict)
            handle_transfer(configuration, client_id, transfer_dict)


if __name__ == '__main__':
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning', 'error']:
        log_level = sys.argv[1]

    # Use separate logger

    logger = daemon_logger('transfers', configuration.user_transfers_log,
                           log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    if not configuration.site_enable_transfers:
        err_msg = "Data transfers are disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    print('''This is the MiG data transfer handler daemon which runs requested
data transfers in the background on behalf of the users. It monitors the saved
data transfer files for changes and launches external client processes to take
care of the tranfers, writing status and output to a transfer output directory
in the corresponding user home.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
''')

    print('Starting Data Transfer handler daemon - Ctrl-C to quit')

    logger.info('Starting data transfer handler daemon')

    # IMPORTANT: If SIGINT reaches multiprocessing it kills manager dict
    # proxies and makes sub_pid_map access fail. Register a signal handler
    # here to avoid that and allow proper clean up
    signal.signal(signal.SIGINT, stop_handler)

    # Keep track of worker subprocesses for proper clean up on shutdown.
    # They get orphaned if worker is terminated, so we kill them in order to
    # allow a clean resume on next start.
    # We use a shared manager dictionary with a pid list for each transfer_id
    # to have multiprocessing access without races.
    transfer_manager = multiprocessing.Manager()
    # Ignore bogus "Instance of 'SyncManager' has no 'dict' member (no-member)"
    sub_pid_map = transfer_manager.dict()  # pylint: disable=no-member

    while not stop_running.is_set():
        try:
            manage_transfers(configuration)

            for (client_id, transfer_id, worker) in \
                    all_worker_transfers(configuration, all_workers):
                if not worker:
                    continue
                logger.debug('Checking if %s %s with pid %d is finished' %
                             (client_id, transfer_id, worker.pid))
                worker.join(1)
                if worker.is_alive():
                    logger.debug('Worker for %s %s running with pid %d' %
                                 (client_id, transfer_id, worker.pid))
                else:
                    logger.info('Removing finished %s %s with pid %d' %
                                (client_id, transfer_id, worker.pid))
                    clean_transfer(configuration, client_id, transfer_id)

            # Throttle down

            time.sleep(30)
        except Exception as exc:
            print('Caught unexpected exception: %s' % exc)
            time.sleep(10)

    print('Cleaning up active transfers')
    logger.info('Cleaning up workers to prepare for exit')
    for (client_id, transfer_id, worker) in \
            all_worker_transfers(configuration, all_workers):
        if not worker or not worker.is_alive():
            continue
        # Terminate worker first to stop further handling, then kill any
        # orphaned subprocesses associated with it for clean resume later
        logger.info('Terminating %s %s worker with pid %d' %
                    (client_id, transfer_id, worker.pid))
        worker.terminate()
        logger.info('Terminating any %s %s child processes' % (client_id,
                                                               transfer_id))
        clean_transfer(configuration, client_id, transfer_id, force=True)

    print('Data transfer handler daemon shutting down')
    logger.info('Stop data transfer handler daemon')
    sys.exit(0)
