#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mig_lustre_quota - MiG lustre quota manager
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Assign lustre project id's to new users and vgrids,
set default quota on new entries and update existing quotas if changed.
Fetch the number of files and bytes used by each project id.
"""

import os
import sys
import time
import getopt
import shlex
import subprocess
import psutil

from mig.shared.base import force_unicode
from mig.shared.conf import get_configuration_object
from mig.shared.fileio import unpickle, pickle, save_json, makedirs_rec, \
    make_symlink
from mig.shared.logger import daemon_logger

from pylustrequota.lfs import lfs_set_project_id, lfs_get_project_quota, \
    lfs_set_project_quota


def usage(name=sys.argv[0]):
    """Usage help"""
    msg = """Usage: %(name)s [OPTIONS]
Where OPTIONS may be one or more of:
   -h|--help                    Show this help
   -v|--verbose                 Verbose output
   -q|--quiet                   No stdout/stderr output
   -c PATH|--config=PATH        Path to config file
   -l PATH|--lustre-basepath    Path to lustre base
   -g PATH|--gocryptfs-sock     Path to gocryptfs socket
""" % {'name': name}
    print(msg, file=sys.stderr)


def INFO(configuration, msg, verbose=False):
    """log info and print to stdout on verbose"""
    configuration.logger.info(msg)
    if verbose:
        print(msg)


def ERROR(configuration, msg, quiet=False):
    """log error and print to stderr on verbose"""
    configuration.logger.error(msg)
    if not quiet:
        print("ERROR: %s" % msg, file=sys.stderr)


def DEBUG(configuration, msg, verbose=False):
    """log debug and print to stderr on verbose"""
    configuration.logger.debug(msg)
    if verbose and configuration.loglevel == 'debug':
        print("DEBUG: %s" % msg, file=sys.stderr)


def __shellexec(configuration,
                command,
                args=[],
                stdin_str=None,
                stdout_filepath=None,
                stderr_filepath=None):
    """Execute shell command
    Returns (exit_code, stdout, stderr) of subprocess"""
    result = 0
    logger = configuration.logger
    stdin_handle = subprocess.PIPE
    stdout_handle = subprocess.PIPE
    stderr_handle = subprocess.PIPE
    if stdout_filepath is not None:
        stdout_handle = open(stdout_filepath, "w+")
    if stderr_filepath is not None:
        stderr_handle = open(stderr_filepath, "w+")
    __args = shlex.split(command)
    __args.extend(args)
    logger.debug("__args: %s" % __args)
    process = subprocess.Popen(
        __args,
        stdin=stdin_handle,
        stdout=stdout_handle,
        stderr=stderr_handle)
    if stdin_str:
        process.stdin.write(stdin_str.encode())
    stdout, stderr = process.communicate()
    rc = process.wait()

    if stdout_filepath:
        stdout = stdout_filepath
        stdout_handle.close()
    if stderr_filepath:
        stderr = stderr_filepath
        stderr_handle.close()

    # Close stdin, stdout and stderr FDs if they exists
    if process.stdin:
        process.stdin.close()
    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()

    if stdout:
        stdout = force_unicode(stdout)
    if stderr:
        stderr = force_unicode(stderr)
    if result == 0:
        logger.debug("%s %s: rc: %s, stdout: %s, error: %s"
                     % (command,
                        " ".join(args),
                        rc,
                        stdout,
                        stderr))
    else:
        logger.error("shellexec: %s %s: rc: %s, stdout: %s, error: %s"
                     % (command,
                        " ".join(__args),
                        rc,
                        stdout,
                        stderr))

    return (rc, stdout, stderr)


def __update_quota(configuration,
                   lustre_basepath,
                   lustre_setting,
                   quota_name,
                   quota_type,
                   gocryptfs_sock,
                   timestamp,
                   verbose,
                   quiet):
    """Update quota for *quota_name*, if new entry then
    assign lustre project id and set default quota.
    If existing entry then update quota settings if changed
    and fetch file and bytes usage and store it as pickle and json
    """
    logger = configuration.logger
    quota_limits_changed = False
    next_lustre_pid = lustre_setting.get('next_pid', -1)
    if next_lustre_pid == -1:
        msg = "Invalid lustre quota next_pid: %d for: %r" \
            % (next_lustre_pid, quota_name)
        ERROR(configuration, msg, quiet)
        return False
    if quota_type == 'vgrid':
        default_quota_limit = configuration.vgrid_quota_limit
        data_basepath = configuration.vgrid_files_writable
    else:
        default_quota_limit = configuration.user_quota_limit
        data_basepath = configuration.user_home

    # Load quota if it exists otherwise new quota

    quota_filepath = os.path.join(configuration.quota_home,
                                  quota_type,
                                  "%s.pck" % quota_name)

    if os.path.exists(quota_filepath):
        quota = unpickle(quota_filepath, logger)
        if not quota:
            msg = "Failed to load quota settings for: %r from %r" \
                % (quota_name, quota_filepath)
            ERROR(configuration, msg, quiet)
            return False
    else:
        quota = {'lustre_pid': next_lustre_pid,
                 'files': -1,
                 'bytes': -1,
                 'softlimit_bytes': -1,
                 'hardlimit_bytes': -1,
                 }

    quota_lustre_pid = quota.get('lustre_pid', -1)
    if quota_lustre_pid == -1:
        msg = "Invalid quota lustre pid: %d for %r" \
            % (quota_lustre_pid, quota_name)
        ERROR(configuration, msg, quiet)
        return False

    # Resolve quota data path

    if not gocryptfs_sock:
        quota_datapath = os.path.join(data_basepath,
                                      quota_name)
    else:
        rel_data_basepath = data_basepath. \
            replace(configuration.state_path + os.sep, "")
        stdin_str = os.path.join(rel_data_basepath, quota_name)
        cmd = "gocryptfs-xray -encrypt-paths %s" % gocryptfs_sock
        (rc, stdout, stderr) = __shellexec(configuration,
                                           cmd,
                                           stdin_str=stdin_str)
        if rc == 0 and stdout:
            encoded_path = stdout.strip()
            quota_datapath = os.path.join(lustre_basepath,
                                          encoded_path)
        else:
            msg = "Failed to resolve encrypted path for: %r" \
                % quota_name \
                + ", rc: %d, error: %s" \
                % (rc, stderr)
            ERROR(configuration, msg, quiet)
            return False

    # Skip non-dir entries

    if not os.path.isdir(quota_datapath):
        msg = "Skipping non-dir entry: %r: %r" \
            % (quota_name, quota_datapath)
        DEBUG(configuration, msg, verbose)
        return True

    # If new entry then set lustre project id

    if quota_lustre_pid == next_lustre_pid:
        # TODO: Mask out path's from log if gocryptfs ?
        msg = "Setting lustre project id: %d for %r: %r" \
            % (quota_lustre_pid, quota_name, quota_datapath)
        INFO(configuration, msg)
        rc = lfs_set_project_id(quota_datapath, quota_lustre_pid, 1)
        if rc == 0:
            lustre_setting['next_pid'] = quota_lustre_pid + 1
        else:
            msg = "Failed to set lustre project id: %d for %r: %r" \
                % (quota_lustre_pid, quota_name, quota_datapath) \
                + ", rc: %d, error: %s" \
                % (rc, stderr)
            ERROR(configuration, msg, quiet)
            return False

    # Get current quota values for lustre_pid

    (rc, currfiles, currbytes, softlimit_bytes, hardlimit_bytes) \
        = lfs_get_project_quota(quota_datapath, quota_lustre_pid)
    if rc != 0:
        msg = "Failed to fetch quota for lustre project id: %d, %r, %r" \
            % (quota_lustre_pid, quota_name, quota_datapath) \
            + ", rc: %d, error: %s" \
            % (rc, stderr)
        ERROR(configuration, msg, quiet)
        return False

    # Update quota info

    quota['mtime'] = timestamp
    quota['files'] = currfiles
    quota['bytes'] = currbytes

    # If new entry use default quota
    # and update quota if changed

    if quota_lustre_pid == next_lustre_pid:
        quota_limits_changed = True
        quota['softlimit_bytes'] = default_quota_limit
        quota['hardlimit_bytes'] = default_quota_limit
    elif hardlimit_bytes != quota.get('hardlimit_bytes', -1) \
            or softlimit_bytes != quota.get('softlimit_bytes', -1):
        quota_limits_changed = True
        quota['softlimit_bytes'] = softlimit_bytes
        quota['hardlimit_bytes'] = hardlimit_bytes

    if quota_limits_changed:
        rc = lfs_set_project_quota(quota_datapath,
                                   quota_lustre_pid,
                                   quota['softlimit_bytes'],
                                   quota['hardlimit_bytes'],
                                   )
        if rc != 0:
            msg = "Failed to set quota limit: %d/%d" \
                % (softlimit_bytes,
                   hardlimit_bytes) \
                + " for lustre project id: %d, %r, %r, rc: %d" \
                % (quota_lustre_pid,
                   quota_name,
                   quota_datapath,
                   rc)
            ERROR(configuration, msg, quiet)
            return False

    # Save current quota

    new_quota_basepath = os.path.join(configuration.quota_home,
                                      quota_type,
                                      str(timestamp))
    if not os.path.exists(new_quota_basepath) \
            and not makedirs_rec(new_quota_basepath, configuration):
        msg = "Failed to create new quota base path: %r" \
            % new_quota_basepath
        ERROR(configuration, msg, quiet)
        return False

    new_quota_filepath_pck = os.path.join(new_quota_basepath,
                                          "%s.pck" % quota_name)
    status = pickle(quota, new_quota_filepath_pck, logger)
    if not status:
        msg = "Failed to save quota for: %r to %r" \
            % (quota_name, new_quota_filepath_pck)
        ERROR(configuration, msg, quiet)
        return False
    new_quota_filepath_json = os.path.join(new_quota_basepath,
                                           "%s.json" % quota_name)
    status = save_json(quota,
                       new_quota_filepath_json,
                       logger)
    if not status:
        msg = "Failed to save quota for: %r to %r" \
            % (quota_name, new_quota_filepath_json)
        ERROR(configuration, msg, quiet)
        return False

    # Create symlink to new quota

    status = make_symlink(new_quota_filepath_pck,
                          quota_filepath,
                          logger,
                          force=True)
    if not status:
        msg = "Failed to make quota symlink for: %r: %r -> %r" \
            % (quota_name, new_quota_filepath_pck, quota_filepath)
        ERROR(configuration, msg, quiet)
        return False

    return True


def update_quota(configuration,
                 lustre_basepath,
                 gocryptfs_sock,
                 verbose,
                 quiet):
    """Update lustre quotas for users and vgrids"""
    logger = configuration.logger
    retval = True
    timestamp = int(time.time())

    # Load lustre quota settings

    lustre_setting_filepath = os.path.join(configuration.quota_home,
                                           'lustre.pck')
    if os.path.exists(lustre_setting_filepath):
        lustre_setting = unpickle(lustre_setting_filepath,
                                  logger)
        if not lustre_setting:
            msg = "Failed to load lustre quota: %r" % lustre_setting_filepath
            ERROR(configuration, msg, quiet)
            return False
    else:
        lustre_setting = {'next_pid': 1,
                          'mtime': 0}

    # Update quotas

    for quota_type in ('vgrid', 'user'):
        if quota_type == 'vgrid':
            scandir = configuration.vgrid_home
        else:
            scandir = configuration.user_home

        # Scan for new and modified entries

        with os.scandir(scandir) as it:
            for entry in it:
                if not os.path.isdir(entry.path):
                    # Only take dirs into account
                    msg = "Skiping non-dir path: %r" % entry.path
                    DEBUG(configuration, msg, verbose)
                    continue
                status = __update_quota(configuration,
                                        lustre_basepath,
                                        lustre_setting,
                                        entry.name,
                                        quota_type,
                                        gocryptfs_sock,
                                        timestamp,
                                        verbose,
                                        quiet,
                                        )
                if not status:
                    retval = False

    # Save updated lustre quota settings

    lustre_setting['mtime'] = timestamp
    status = pickle(lustre_setting,
                    lustre_setting_filepath,
                    logger)
    if not status:
        msg = "Failed to save lustra quota settings: %r" \
            % lustre_setting_filepath
        ERROR(configuration, msg, quiet)

    return retval


def main():
    retval = True
    verbose = False
    quiet = False
    config_file = None
    lustre_basepath = None
    gocryptfs_sock = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvqc:l:g:",
                                   ["help", "verbose", "quiet", "config=",
                                    "--lustre-basepath", "--gocryptfs-sock="])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            elif opt in ("-v", "--verbose"):
                verbose = True
            elif opt in ("-q", "--quiet"):
                quiet = True
            elif opt in ("-c", "--config"):
                config_file = arg
            elif opt in ("-l", "--lustre-basepath"):
                lustre_basepath = arg
            elif opt in ("-g", "--gocryptfs-sock"):
                gocryptfs_sock = arg
    except Exception as err:
        print(err, file=sys.stderr)
        usage()
        return 1

    if quiet:
        verbose = False

    # Initialize configuration

    try:
        configuration = get_configuration_object(config_file=config_file)
    except Exception as err:
        print(err, file=sys.stderr)
        usage()
        return 1

    # Use separate logger

    logger = daemon_logger("quota",
                           configuration.user_quota_log,
                           configuration.loglevel)
    configuration.logger = logger

    # If lustre_basepath is provided then check it,
    # otherwise try to resolve it

    valid_lustre_basepath = None
    for mount in psutil.disk_partitions(all=True):
        if mount.fstype == "lustre":
            if lustre_basepath \
                    and lustre_basepath.startswith(mount.mountpoint) \
                    and os.path.isdir(lustre_basepath):
                valid_lustre_basepath = lustre_basepath
                break
            elif mount.mountpoint.endswith(configuration.server_fqdn):
                valid_lustre_basepath = mount.mountpoint
            else:
                check_lustre_basepath = os.path.join(mount.mountpoint,
                                                     configuration.server_fqdn)
                if os.path.isdir(check_lustre_basepath):
                    valid_lustre_basepath = check_lustre_basepath
                    break

    if valid_lustre_basepath is None:
        if lustre_basepath:
            msg = "Lustre base: %r is NOT mounted" % lustre_basepath
        else:
            msg = "Found no valid lustre mounts for: %s" \
                % configuration.server_fqdn
        ERROR(configuration, msg, quiet)
        return False

    INFO(configuration,
         "Using lustre basepath: %r" % valid_lustre_basepath,
         verbose)

    # Check gocryptfs socket

    valid_gocryptfs_sock = None
    if gocryptfs_sock is None:
        check_gocryptfs_sock = "/var/run/gocryptfs.%s.sock" \
            % configuration.server_fqdn
        if os.path.exists(check_gocryptfs_sock):
            valid_gocryptfs_sock = check_gocryptfs_sock

    INFO(configuration,
         "Using gocryptfs socket: %r" % valid_gocryptfs_sock,
         verbose)

    # Perform update

    status = update_quota(configuration,
                          valid_lustre_basepath,
                          valid_gocryptfs_sock,
                          verbose,
                          quiet)
    if status:
        retval = 0
    if not status:
        retval = 1

    return retval


if __name__ == "__main__":
    status = main()
    if status:
        sys.exit(0)
    else:
        sys.exit(1)
