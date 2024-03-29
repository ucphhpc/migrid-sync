#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# usercache - User state caching
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""User state caching: disk use, jobs, resource access"""

from __future__ import print_function
from __future__ import absolute_import

import fcntl
import os
import time

from mig.shared.base import client_id_dir
from mig.shared.fileio import walk
from mig.shared.resource import list_resources
from mig.shared.serial import load, dump

# Only refresh stats if at least this many seconds since last refresh
JOB_REFRESH_DELAY = 120
DISK_REFRESH_DELAY = 3600
# Internal field names
TOTALS = (OWN, VGRID, JOBS) = (
    '__user_totals__', '__vgrid_totals__', '__jobs__')
(FILES, DIRECTORIES, BYTES, KIND) = \
    ('__files__', '__directories__', '__bytes__', '__kind__')
STATES = (PARSE, QUEUED, EXECUTING, FINISHED, RETRY, CANCELED, EXPIRED,
          FAILED, FROZEN) = \
    ("PARSE", "QUEUED", "EXECUTING", "FINISHED", "RETRY", "CANCELED",
     "EXPIRED", "FAILED", "FROZEN")
FINAL_STATES = (FINISHED, CANCELED, EXPIRED, FAILED)
JOBFIELDS = ["STATUS"]


def format_bytes(bytes, format):
    """Scale bytes to requested size format for pretty printing"""
    scaler = 0
    if "kilo" == format:
        scaler = 1
    elif "mega" == format:
        scaler = 2
    elif "giga" == format:
        scaler = 3
    elif "tera" == format:
        scaler = 4
    elif "peta" == format:
        scaler = 5
    elif "exa" == format:
        scaler = 6
    elif "zeta" == format:
        scaler = 7
    return bytes * 1.0 / pow(2, scaler*10)


def contents_changed(configuration, root, files, ref_stamp):
    """Check if mtime of root dir or contents changed after ref_stamp"""
    _logger = configuration.logger
    all_paths = [root]
    all_paths += [os.path.join(root, name) for name in files]
    for path in all_paths:
        try:
            file_stamp = os.path.getmtime(path)
        except Exception as exc:
            _logger.warning("getmtime failed on %s: %s" % (path, exc))
            file_stamp = -1
        if file_stamp > ref_stamp:
            return True
    return False


def update_disk_stats(configuration, stats, root, rel_root, dirs, files,
                      total):
    """Update disk stats for root"""

    _logger = configuration.logger

    # Gather size of all entries in root

    size = 0
    for name in files + dirs:
        path = os.path.join(root, name)
        # Ignore any access errors
        try:
            size += os.path.getsize(path)
        except Exception as exc:
            _logger.warning("getsize failed on %s: %s" % (path, exc))

    if rel_root not in stats:
        stats[rel_root] = {}
        stats[total][FILES] += len(files)
        stats[total][DIRECTORIES] += len(dirs)
        stats[rel_root][FILES] = len(files)
        stats[rel_root][DIRECTORIES] = len(dirs)
        stats[total][BYTES] += size
        stats[rel_root][BYTES] = size
        stats[rel_root][KIND] = total
    else:
        stats[total][FILES] += (len(files) - stats[rel_root][FILES])
        stats[rel_root][FILES] = len(files)
        stats[total][DIRECTORIES] += (len(dirs) - stats[rel_root][DIRECTORIES])
        stats[rel_root][DIRECTORIES] = len(dirs)
        stats[total][BYTES] += (size - stats[rel_root][BYTES])
        stats[rel_root][BYTES] = size
        stats[rel_root][KIND] = total
    return stats


def update_job_stats(stats, job_id, job):
    """Update job stats for job"""

    job_status = job["STATUS"]
    if job_id not in stats:
        stats[JOBS][job_status] += 1
    else:
        old_status = stats[job_id]["STATUS"]
        stats[JOBS][old_status] -= 1
        stats[JOBS][job_status] += 1
    stats[job_id] = {}
    for field in JOBFIELDS:
        stats[job_id][field] = job[field]
    return stats


def refresh_disk_stats(configuration, client_id):
    """Refresh disk use stats for specified user"""
    _logger = configuration.logger
    dirty = False
    client_dir = client_id_dir(client_id)
    user_base = os.path.join(configuration.user_home, client_dir)
    stats_base = os.path.join(configuration.user_cache, client_dir)
    stats_path = os.path.join(stats_base, "disk-stats.pck")
    lock_path = stats_path + ".lock"

    try:
        os.makedirs(stats_base)
    except:
        pass

    lock_handle = open(lock_path, 'a')

    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    try:
        stats = load(stats_path)
        stats_stamp = os.path.getmtime(stats_path)
    except IOError:
        _logger.warning("No disk stats to load - ok first time")
        stats = {OWN: {FILES: 0, DIRECTORIES: 0, BYTES: 0},
                 VGRID: {FILES: 0, DIRECTORIES: 0, BYTES: 0}}
        stats_stamp = -1

    now = time.time()
    if now < stats_stamp + DISK_REFRESH_DELAY:
        lock_handle.close()
        return stats

    # Walk entire home dir and update any parts that changed
    # Please note that walk doesn't follow symlinks so we have
    # to additionally walk vgrid dir symlinks explicitly
    cur_roots = []
    vgrid_dirs = []
    total = OWN
    for (root, dirs, files) in walk(user_base):
        rel_root = root.replace(user_base, '').lstrip(os.sep)
        cur_roots.append(rel_root)
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if os.path.islink(dir_path):
                vgrid_dirs.append(dir_path)

        # Directory and contents unchanged - ignore

        if rel_root in stats and \
                not contents_changed(configuration, root, files, stats_stamp):
            continue

        dirty = True

        update_disk_stats(configuration, stats, root, rel_root, dirs, files,
                          total)

    # Now walk vgrid dir symlinks explicitly
    total = VGRID
    for vgrid_base in vgrid_dirs:
        for (root, dirs, files) in walk(vgrid_base):
            # Still use path relative to user base!
            rel_root = root.replace(user_base, '').lstrip(os.sep)
            cur_roots.append(rel_root)

            # Directory and contents unchanged - ignore

            if rel_root in stats and \
                not contents_changed(configuration, root, files,
                                     stats_stamp):
                continue

            dirty = True

            update_disk_stats(configuration, stats, root, rel_root, dirs,
                              files, total)

    # Update stats for any roots no longer there
    # NOTE: use copy of list as we delete inline

    for rel_root in list(stats):
        if rel_root in list(TOTALS) + cur_roots:
            continue
        root = os.path.join(user_base, rel_root)
        # NOTE: legacy stats may lack KIND field - just ignore and delete
        total = stats[rel_root].get(KIND, None)
        if total:
            stats[total][FILES] -= stats[rel_root][FILES]
            stats[total][DIRECTORIES] -= stats[rel_root][DIRECTORIES]
            stats[total][BYTES] -= stats[rel_root][BYTES]
        else:
            _logger.warning("Ignoring outdated stat entry for %s: %s" %
                            (root, stats[rel_root]))
        del stats[rel_root]
        dirty = True

    if dirty:
        try:
            dump(stats, stats_path)
            stats_stamp = os.path.getmtime(stats_path)
        except Exception as exc:
            _logger.error("Could not save stats cache: %s" % exc)

    lock_handle.close()

    stats['time_stamp'] = stats_stamp
    return stats


def refresh_job_stats(configuration, client_id):
    """Refresh job stats for specified user"""
    _logger = configuration.logger
    dirty = False
    client_dir = client_id_dir(client_id)
    job_base = os.path.join(configuration.mrsl_files_dir, client_dir)
    stats_base = os.path.join(configuration.user_cache, client_dir)
    stats_path = os.path.join(stats_base, "job-stats.pck")
    lock_path = stats_path + ".lock"

    try:
        os.makedirs(stats_base)
    except:
        pass

    lock_handle = open(lock_path, 'a')

    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    job_stats = {PARSE: 0, QUEUED: 0, EXECUTING: 0, FINISHED: 0, RETRY: 0,
                 CANCELED: 0, EXPIRED: 0, FAILED: 0, FROZEN: 0}
    try:
        stats = load(stats_path)
        stats_stamp = os.path.getmtime(stats_path)
        # Backwards compatible update
        job_stats.update(stats[JOBS])
        stats[JOBS] = job_stats
    except IOError:
        _logger.warning("No job stats to load - ok first time")
        stats = {JOBS: job_stats}
        stats_stamp = -1

    now = time.time()
    if now < stats_stamp + JOB_REFRESH_DELAY:
        lock_handle.close()
        return stats

    # Inspect all jobs in user job dir and update the ones that changed
    # since last stats run
    for name in os.listdir(job_base):
        if name in stats and stats[name]["STATUS"] in FINAL_STATES:
            continue

        job_path = os.path.join(job_base, name)
        try:
            job_stamp = os.path.getmtime(job_path)
        except Exception as exc:
            _logger.warning("getmtime failed on %s: %s" % (job_path, exc))
            job_stamp = -1

        if name in stats and job_stamp < stats_stamp:
            continue

        dirty = True
        try:
            job = load(job_path)
        except Exception as exc:
            _logger.warning("unpickle failed on %s: %s" % (job_path, exc))
            continue
        update_job_stats(stats, name, job)

    if dirty:
        try:
            dump(stats, stats_path)
            stats_stamp = os.path.getmtime(stats_path)
        except Exception as exc:
            _logger.error("Could not save stats cache: %s" % exc)

    lock_handle.close()

    stats['time_stamp'] = stats_stamp
    return stats


if "__main__" == __name__:
    import sys
    if not sys.argv[1:]:
        print("USAGE: usercache.py CLIENT_ID")
        print("       Runs basic unit tests for CLIENT_ID")
        sys.exit(1)
    client_id = sys.argv[1]
    from mig.shared.conf import get_configuration_object
    conf = get_configuration_object()
    raw_stats = refresh_disk_stats(conf, client_id)
    print("user totals: %s" % raw_stats[OWN])
    print("vgrid totals: %s" % raw_stats[VGRID])
    raw_stats = refresh_job_stats(conf, client_id)
    print("total jobs: %s" % raw_stats[JOBS])
