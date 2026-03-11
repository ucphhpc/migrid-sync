#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# lustrequota - helpers to support lustre quota
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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

"""helpers to support lustre quota"""

import os
import shlex
import stat
import subprocess
import time

# NOTE: we rely on psutil to resolve lustre mount point
try:
    import psutil
except ImportError:
    psutil = None

from mig.shared.base import force_unicode
from mig.shared.fileio import (
    make_symlink,
    makedirs_rec,
    pickle,
    save_json,
    scandir,
    unpickle,
    walk,
    write_file,
)
from mig.shared.vgrid import vgrid_flat_name

try:
    from lustreclient.lfs import (
        lfs_get_project_quota,
        lfs_set_project_id,
        lfs_set_project_quota,
    )
except ImportError:
    lfs_set_project_id = None
    lfs_get_project_quota = None
    lfs_set_project_quota = None


def __get_lustre_basepath(configuration, lustre_basepath=None):
    """If *lustre_basepath* is provided then check it,
    otherwise try to resolve it"""
    if psutil is None:
        return None

    valid_lustre_basepath = None
    for dpart in psutil.disk_partitions(all=True):
        if dpart.fstype == "lustre":
            if (
                lustre_basepath
                and lustre_basepath.startswith(dpart.mountpoint)
                and os.path.isdir(lustre_basepath)
            ):
                valid_lustre_basepath = lustre_basepath
                break
            elif dpart.mountpoint.endswith(configuration.server_fqdn):
                valid_lustre_basepath = dpart.mountpoint
            else:
                check_lustre_basepath = os.path.join(
                    dpart.mountpoint, configuration.server_fqdn
                )
                if os.path.isdir(check_lustre_basepath):
                    valid_lustre_basepath = check_lustre_basepath
                    break

    return valid_lustre_basepath


def __get_gocryptfs_socket(configuration, gocryptfs_sock=None):
    """If *gocryptfs_sock* is provided then check it,
    otherwise return default if it exists"""
    valid_gocryptfs_sock = None
    if gocryptfs_sock is None:
        gocryptfs_sock = (
            "/var/run/gocryptfs.%s.sock" % configuration.server_fqdn
        )
    if os.path.exists(gocryptfs_sock):
        gocryptfs_sock_stat = os.lstat(gocryptfs_sock)
        if stat.S_ISSOCK(gocryptfs_sock_stat.st_mode):
            valid_gocryptfs_sock = gocryptfs_sock

    return valid_gocryptfs_sock


def __shellexec(
    configuration,
    command,
    args=[],
    stdin_str=None,
    stdout_filepath=None,
    stderr_filepath=None,
):
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
        __args, stdin=stdin_handle, stdout=stdout_handle, stderr=stderr_handle
    )
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
        logger.debug(
            "%s %s: rc: %s, stdout: %s, error: %s"
            % (command, " ".join(args), rc, stdout, stderr)
        )
    else:
        logger.error(
            "shellexec: %s %s: rc: %s, stdout: %s, error: %s"
            % (command, " ".join(__args), rc, stdout, stderr)
        )

    return (rc, stdout, stderr)


def __set_project_id(
    configuration, lustre_basepath, quota_datapath, quota_name, quota_lustre_pid
):
    """Set lustre project *quota_lustre_pid*
    Find the next *free* project id (PID) if *quota_lustre_pid* is occupied
    NOTE: lustre uses a global counter for project id's (PID)
          That means that different datasets and sub-mounts
          share the same project id counter
    # TODO: Add 'lustre_pid' offset support to configuration ?
    """

    # Find next unused lustre project id

    max_lustre_pid = 4294967294
    logger = configuration.logger
    next_lustre_pid = quota_lustre_pid
    while next_lustre_pid < max_lustre_pid:
        rc, currfiles, _, _, _ = lfs_get_project_quota(
            lustre_basepath, next_lustre_pid
        )
        if rc != 0:
            logger.error(
                "Failed to fetch quota for lustre project id: %d, %r"
                % (next_lustre_pid, lustre_basepath)
                + ", rc: %d" % rc
            )
            return -1
        if currfiles == 0:
            break
        logger.info(
            "Skipping project id: %d" % next_lustre_pid
            + " already registered with %d files" % currfiles
        )
        next_lustre_pid += 1

    if next_lustre_pid == max_lustre_pid:
        logger.error("Reached max lustre project id: %d" % max_lustre_pid)
        return -1

    # Set new project id

    logger.info(
        "Setting lustre project id: %d for %r: %r"
        % (next_lustre_pid, quota_name, quota_datapath)
    )
    rc = lfs_set_project_id(quota_datapath, next_lustre_pid, 1)
    if rc != 0:
        logger.error(
            "lfs_set_project_id failed for lustre project id: %d for %r: %r"
            % (next_lustre_pid, quota_name, quota_datapath)
            + ", rc: %d" % rc
        )
        return -1

    # Dump lustre pid in quota_datapath and wait for it to appear in the quota

    lustre_pid_filepath = os.path.join(quota_datapath, ".lustrepid")
    status = write_file(next_lustre_pid, lustre_pid_filepath, logger)
    if not status:
        logger.error(
            "Failed write lustre project id: %d for %r to %r"
            % (next_lustre_pid, quota_name, quota_datapath)
        )
        return -1

    # Wait for files to appear in quota before returning

    files = 0
    waiting = 0
    max_waiting = 60
    while files == 0 and waiting < max_waiting:
        rc, files, _, _, _ = lfs_get_project_quota(
            lustre_basepath, next_lustre_pid
        )
        if rc != 0:
            files = 0
            logger.error(
                "lfs_get_project_quota failed for:"
                + " %d, %r, %r, rc: %d"
                % (next_lustre_pid, quota_name, quota_datapath, rc)
            )
        if files == 0:
            logger.info(
                "Waiting for lustre quota: %d: %r: %r"
                % (next_lustre_pid, quota_name, quota_datapath)
            )
            time.sleep(1)
        max_waiting += 1

    if waiting == max_waiting:
        logger.error(
            "Failed to fetch quota for:"
            + " %d, %r, %r" % (next_lustre_pid, quota_name, quota_datapath)
        )
        return -1

    return next_lustre_pid


def __update_quota(
    configuration,
    lustre_basepath,
    lustre_setting,
    quota_name,
    quota_type,
    data_basefs,
    gocryptfs_sock,
    timestamp,
):
    """Update quota for *quota_name*, if new entry then
    assign lustre project id and set default quota.
    If existing entry then update quota settings if changed
    and fetch file and bytes usage and store it as pickle and json
    """
    logger = configuration.logger
    quota_limits_changed = False
    next_lustre_pid = lustre_setting.get("next_pid", -1)
    if next_lustre_pid == -1:
        logger.error(
            "Invalid lustre quota next_pid: %d for: %r"
            % (next_lustre_pid, quota_name)
        )
        return False

    # Resolve quota limit and data basepath

    if quota_type == "vgrid":
        default_quota_limit = configuration.quota_vgrid_limit
        data_basepath = configuration.vgrid_files_writable
    else:
        default_quota_limit = configuration.quota_user_limit
        data_basepath = configuration.user_home

    if data_basepath.startswith(configuration.state_path):
        rel_data_basepath = data_basepath.replace(
            configuration.state_path, ""
        ).lstrip(os.sep)
    else:
        logger.error(
            "Failed to resolve relative data basepath from: %r" % data_basepath
        )
        return False

    # Resolve quota data path
    # if gocryptfs then resolve encrypted path otherwise use plain path

    if configuration.quota_backend == "lustre":
        quota_basefs = "lustre"
        quota_datapath = os.path.join(
            lustre_basepath, rel_data_basepath, quota_name
        )

    elif configuration.quota_backend == "lustre-gocryptfs":
        quota_basefs = "fuse.gocryptfs"
        stdin_str = os.path.join(rel_data_basepath, quota_name)
        cmd = "gocryptfs-xray -encrypt-paths %s" % gocryptfs_sock
        rc, stdout, stderr = __shellexec(
            configuration, cmd, stdin_str=stdin_str
        )
        if rc == 0 and stdout:
            encoded_path = stdout.strip()
            quota_datapath = os.path.join(lustre_basepath, encoded_path)
        else:
            logger.error(
                "Failed to resolve encrypted path for: %r" % quota_name
                + ", rc: %d, error: %s" % (rc, stderr)
            )
            return False
    else:
        logger.error("Invalid quota backend: %r" % configuration.quota_backend)
        return False

    # Check if valid lustre data dir

    if not os.path.isdir(quota_datapath):
        msg = "skipping entry: %r : %r, no lustre data path: %r" % (
            quota_type,
            quota_name,
            quota_datapath,
        )
        # NOTE: log error and return false if dir is missing
        #       and we expect data to be on lustre or gocryoptfs)
        if data_basefs == quota_basefs:
            logger.error(msg)
            return False
        else:
            logger.debug(msg)
            return True

    logger.debug("Setting quota for lustre dir: %r" % quota_datapath)

    # Load quota if it exists otherwise new quota

    quota_filepath = os.path.join(
        configuration.quota_home,
        configuration.quota_backend,
        quota_type,
        "%s.pck" % quota_name,
    )
    if os.path.exists(quota_filepath):
        quota = unpickle(quota_filepath, logger)
        if not quota:
            logger.error(
                "Failed to load quota settings for: %r from %r"
                % (quota_name, quota_filepath)
            )
            return False
    else:
        quota = {
            "lustre_pid": next_lustre_pid,
            "files": -1,
            "bytes": -1,
            "softlimit_bytes": -1,
            "hardlimit_bytes": -1,
        }

    # Fetch quota lustre pid

    quota_lustre_pid = quota.get("lustre_pid", -1)
    if quota_lustre_pid == -1:
        logger.error(
            "Invalid quota lustre pid: %d for %r"
            % (quota_lustre_pid, quota_name)
        )
        return False

    # If new entry then set lustre project id

    new_lustre_pid = -1
    if quota_lustre_pid == next_lustre_pid:
        new_lustre_pid = __set_project_id(
            configuration,
            lustre_basepath,
            quota_datapath,
            quota_name,
            quota_lustre_pid,
        )
        if new_lustre_pid == -1:
            logger.error(
                "Failed to set project id: %d, %r, %r"
                % (new_lustre_pid, quota_name, quota_datapath)
            )
            return False
        lustre_setting["next_pid"] = new_lustre_pid + 1
        quota["lustre_pid"] = quota_lustre_pid = new_lustre_pid

    # Get current quota values for lustre_pid

    rc, currfiles, currbytes, softlimit_bytes, hardlimit_bytes = (
        lfs_get_project_quota(lustre_basepath, quota_lustre_pid)
    )
    if rc != 0:
        logger.error(
            "lfs_get_project_quota failed for: %d, %r, %r"
            % (quota_lustre_pid, quota_name, quota_datapath)
            + ", rc: %d" % rc
        )
        return False

    # Update quota info

    if currfiles == 0 or currbytes == 0:
        logger.warning(
            "lustre_basepath: %r: pid: %d: quota_type: %s"
            % (lustre_basepath, quota_lustre_pid, quota_type)
            + "quota_name: %s, files: %d, bytes: %d"
            % (quota_name, currfiles, currbytes)
        )

    quota["mtime"] = timestamp
    quota["files"] = currfiles
    quota["bytes"] = currbytes

    # If new entry use default quota
    # and update quota if changed

    if new_lustre_pid > -1:
        quota_limits_changed = True
        quota["softlimit_bytes"] = default_quota_limit
        quota["hardlimit_bytes"] = default_quota_limit
    elif hardlimit_bytes != quota.get(
        "hardlimit_bytes", -1
    ) or softlimit_bytes != quota.get("softlimit_bytes", -1):
        quota_limits_changed = True
        quota["softlimit_bytes"] = softlimit_bytes
        quota["hardlimit_bytes"] = hardlimit_bytes

    if quota_limits_changed:
        rc = lfs_set_project_quota(
            quota_datapath,
            quota_lustre_pid,
            quota["softlimit_bytes"],
            quota["hardlimit_bytes"],
        )
        if rc != 0:
            logger.error(
                "Failed to set quota limit: %d/%d"
                % (softlimit_bytes, hardlimit_bytes)
                + " for lustre project id: %d, %r, %r, rc: %d"
                % (quota_lustre_pid, quota_name, quota_datapath, rc)
            )
            return False

    # Save current quota

    new_quota_basepath = os.path.join(
        configuration.quota_home,
        configuration.quota_backend,
        quota_type,
        str(timestamp),
    )
    if not os.path.exists(new_quota_basepath) and not makedirs_rec(
        new_quota_basepath, configuration
    ):
        logger.error(
            "Failed to create new quota base path: %r" % new_quota_basepath
        )
        return False

    new_quota_filepath_pck = os.path.join(
        new_quota_basepath, "%s.pck" % quota_name
    )

    logger.debug(
        "Saving: %s: %s: %s -> %r"
        % (quota_type, quota_name, quota, new_quota_filepath_pck)
    )

    status = pickle(quota, new_quota_filepath_pck, logger)
    if not status:
        logger.error(
            "Failed to save quota for: %r to %r"
            % (quota_name, new_quota_filepath_pck)
        )
        return False

    new_quota_filepath_json = os.path.join(
        new_quota_basepath, "%s.json" % quota_name
    )
    status = save_json(quota, new_quota_filepath_json, logger)
    if not status:
        logger.error(
            "Failed to save quota for: %r to %r"
            % (quota_name, new_quota_filepath_json)
        )
        return False

    # Create symlink to new quota

    status = make_symlink(
        new_quota_filepath_pck, quota_filepath, logger, force=True
    )
    if not status:
        logger.error(
            "Failed to make quota symlink for: %r: %r -> %r"
            % (quota_name, new_quota_filepath_pck, quota_filepath)
        )
        return False

    return True


def update_lustre_quota(configuration):
    """Update lustre quota for users and vgrids"""
    logger = configuration.logger

    # Check if lustreclient module was imported correctly

    if (
        lfs_set_project_id is None
        or lfs_get_project_quota is None
        or lfs_set_project_quota is None
    ):
        logger.error("Failed to import lustreclient module")
        return False

    retval = True
    timestamp = int(time.time())

    # Get lustre_basepath

    lustre_basepath = __get_lustre_basepath(configuration)
    if lustre_basepath:
        logger.debug("Using lustre basepath: %r" % lustre_basepath)
    else:
        logger.error(
            "Found no valid lustre mounts for: %s" % configuration.server_fqdn
        )
        return False

    # Get gocryptfs socket if enabled

    gocryptfs_sock = None
    if configuration.quota_backend == "lustre-gocryptfs":
        gocryptfs_sock = __get_gocryptfs_socket(configuration)
        if gocryptfs_sock:
            logger.debug("Using gocryptfs socket: %r" % gocryptfs_sock)
        else:
            logger.error("Missing gocryptfs socket")
            return False

    # Load lustre quota settings

    lustre_setting_filepath = os.path.join(
        configuration.quota_home, "%s.pck" % configuration.quota_backend
    )
    if os.path.exists(lustre_setting_filepath):
        lustre_setting = unpickle(lustre_setting_filepath, logger)
        if not lustre_setting:
            logger.error(
                "Failed to load lustre quota: %r" % lustre_setting_filepath
            )
            return False
    else:
        lustre_setting = {"next_pid": 1, "mtime": 0}

    # Update quota

    quota_targets = {
        "vgrid": {
            "basefs": "lustre",
            "entries": {},
        },
        "user": {
            "basefs": "lustre",
            "entries": {},
        },
    }

    # Resolve basefs if possible

    for dpart in psutil.disk_partitions(all=True):
        mountpoint = dpart.mountpoint.rstrip(os.sep)
        fstype = dpart.fstype
        if mountpoint == configuration.vgrid_files_writable.rstrip(os.sep):
            logger.debug(
                "Found basefs for vgrid data: %r : %r" % (mountpoint, fstype)
            )
            quota_targets["vgrid"]["basefs"] = fstype
        if mountpoint == configuration.user_home.rstrip(os.sep):
            logger.debug(
                "Found basefs for user data: %r : %r" % (mountpoint, fstype)
            )
            quota_targets["user"]["basefs"] = fstype

    # Resolve vgrids and sub-vgrids

    for root, dirs, _ in walk(configuration.vgrid_home, topdown=True):
        for dirent in dirs:
            vgrid_dirpath = os.path.join(root, dirent)
            owners_filepath = os.path.join(vgrid_dirpath, "owners")
            if os.path.isfile(owners_filepath):
                vgrid = vgrid_flat_name(
                    vgrid_dirpath[len(configuration.vgrid_home) :],
                    configuration,
                )
                logger.debug("Found vgrid: %r" % vgrid)
                quota_targets["vgrid"]["entries"][vgrid] = 1

    # Resolve users

    with scandir(configuration.user_home) as it:
        for entry in it:
            if os.path.islink(entry.path):
                userhome = os.readlink(entry.path)
                # NOTE: Relative links are prefixed with 'user_home'
                if not userhome.startswith(os.sep):
                    userhome = os.path.join(configuration.user_home, userhome)
            else:
                userhome = entry.path
            if os.path.isdir(userhome):
                user = os.path.basename(userhome)
            else:
                logger.debug(
                    "skipping non-userhome: %r (%r)" % (userhome, entry.path)
                )
                continue
            # NOTE: Multiple links might point to same user
            quota_targets["user"]["entries"][user] = True

    # Update quotas

    for quota_type in quota_targets:
        target = quota_targets.get(quota_type, {})
        data_basefs = target.get("basefs", "lustre")
        quota_entries = target.get("entries", {})
        for quota_entry in quota_entries:
            status = __update_quota(
                configuration,
                lustre_basepath,
                lustre_setting,
                quota_entry,
                quota_type,
                data_basefs,
                gocryptfs_sock,
                timestamp,
            )
            if not status:
                retval = False

    # Save updated lustre quota settings

    lustre_setting["mtime"] = timestamp
    status = pickle(lustre_setting, lustre_setting_filepath, logger)
    if not status:
        logger.error(
            "Failed to save lustra quota settings: %r" % lustre_setting_filepath
        )

    return retval
