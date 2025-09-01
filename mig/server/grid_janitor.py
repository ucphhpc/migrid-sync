#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_janitor - daemon to handle recurring tasks like clean up and updates
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Daemon to take care of various recurring tasks like clean up, cache updates
and pruning of pending requests.
"""

from __future__ import absolute_import, print_function

import fnmatch
import multiprocessing
import os
import signal
import sys
import time

from mig.shared.conf import get_configuration_object
from mig.shared.fileio import listdir, delete_file
from mig.shared.logger import daemon_logger, register_hangup_handler

# TODO: adjust short to subsecond and long to e.g a minute for production use
#SHORT_THROTTLE_SECS = 0.5
#LONG_THROTTLE_SECS = 60.0
SHORT_THROTTLE_SECS = 5.0
LONG_THROTTLE_SECS = 30.0

REMIND_REQ_DAYS = 5
EXPIRE_REQ_DAYS = 30

EXPIRE_STATE_DAYS = 30
EXPIRE_DUMMY_JOBS_DAYS = 7
EXPIRE_TWOFACTOR_DAYS = 1

SECS_PER_DAY = 86400
SECS_PER_HOUR = 3600
SECS_PER_MINUTE = 60

stop_running = multiprocessing.Event()
(configuration, logger) = (None, None)

task_triggers = {}


def stop_handler(sig, frame):
    """A simple signal handler to quit on Ctrl+C (SIGINT) in main"""
    # Print blank line to avoid mix with Ctrl-C line
    print("")
    stop_running.set()

def _lookup_last_run(configuration, target):
    """Check if target task is pending using internal accounting for task.
    Returns the timestamp when the task was last run in UN*X epoch.
    """
    # Lazy init
    last_stamp = task_triggers[target] = task_triggers.get(target, -1)
    if last_stamp > 0:
        logger.debug("last %s task ran at %d" % (target, last_stamp))
    else:
        logger.debug("no last %s task run in history" % target)
    return last_stamp

def _update_last_run(configuration, target, stamp):
    """Update target task pending mark using internal accounting and supplied
    task timestamp in UN*X epoch.
    Returns the same updated timestamp for the task.
    """
    # TODO: add a more persistent marker e.g. in mig_system_run or _files to
    #      remember last status across restarts and reboots?
    task_triggers[target] = stamp
    return task_triggers[target]


def _clean_stale_state_files(configuration, target_dir, filename_patterns,
                             expire_days, now, include_dotfiles=False):
    """Inspect and clean up stale state files matching any of filename_pattern
    in target_dir if they are at least expire_days old. Where filename_pattern is
    a list of wildcard strings checked with fnmatch. Dot-files are excluded
    from matching unless include_dotfiles is set.
    Returns the number of actual actions taken for central throttle handling.
    """
    handled = 0
    logger.debug("clean files matching %r in %r if older than %dd" % \
                 (filename_patterns, target_dir, expire_days))
    for filename in listdir(target_dir):
        if not include_dotfiles and filename.startswith('.'):
            continue
        tmp_age = -1
        for pattern in filename_patterns:
            tmp_path = os.path.join(target_dir, filename)
            if fnmatch.fnmatch(filename, pattern):
                logger.debug("checking if state file %r is stale" % tmp_path)
                tmp_age = now - os.path.getmtime(tmp_path)
            else:
                continue
            tmp_age_days = tmp_age / SECS_PER_DAY
            logger.debug("found state file %r of age %ds / %dd" % \
                        (tmp_path, tmp_age, tmp_age_days))
            if tmp_age_days > expire_days:
                logger.info("remove stale tmp file in %r : %dd" % (tmp_path,
                                                                 tmp_age_days))
                if not delete_file(tmp_path, logger):
                    logger.error("failed to remove stale file %r" % tmp_path)
                handled += 1
    logger.debug("handled %d stale state file cleanups" % handled)
    return handled

def clean_mig_system_files(configuration, now=time.time()):
    """Inspect and clean up stale state files in mig_system_run.
    Returns the number of actual actions taken for central throttle handling.
    """
    return _clean_stale_state_files(configuration,
                                    configuration.mig_system_files,
                                    ['tmp*', 'no_grid_jobs*'],
                                    EXPIRE_STATE_DAYS, now)

def clean_sessid_to_mrls_link_home(configuration, now=time.time()):
    """Inspect and clean up stale state files in sessid_to_mrsl_link_home.
    Returns the number of actual actions taken for central throttle handling.
    """
    return _clean_stale_state_files(configuration,
                                    configuration.sessid_to_mrsl_link_home,
                                    ['*'], EXPIRE_STATE_DAYS, now)

def clean_webserver_home(configuration, now=time.time()):
    """Inspect and clean up stale state files in webserver_home.
    Returns the number of actual actions taken for central throttle handling.
    """
    return _clean_stale_state_files(configuration,
                                    configuration.webserver_home,
                                    ['*'], EXPIRE_STATE_DAYS, now)

def clean_no_job_helpers(configuration, now=time.time()):
    """Inspect and clean up stale state empty job helpers inside user_home.
    Returns the number of actual actions taken for central throttle handling.
    """
    dummy_job_path = os.path.join(configuration.user_home,
                                  'no_grid_jobs_in_grid_scheduler')
    return _clean_stale_state_files(configuration,
                                    dummy_job_path,
                                    ['*'], EXPIRE_DUMMY_JOBS_DAYS, now)

def clean_twofactor_sessions(configuration, now=time.time()):
    """Inspect and clean up stale state files in twofactor_home.
    Returns the number of actual actions taken for central throttle handling.
    """
    return _clean_stale_state_files(configuration,
                                    configuration.twofactor_home,
                                    ['*'], EXPIRE_TWOFACTOR_DAYS, now)

def handle_state_cleanup(configuration, now=time.time()):
    """Inspect various state dirs to clean up general stale old temporay files.
    Returns the number of actual actions taken for central throttle handling.
    """
    handled = 0
    logger.debug("handle pending state cleanups")
    handled += clean_mig_system_files(configuration, now)
    handled += clean_webserver_home(configuration, now)
    if configuration.site_enable_jobs:
        handled += clean_no_job_helpers(configuration, now)
    # TODO: handle gzip of events files like cronjob
    if handled > 0:
        logger.info("handled %d pending state cleanup(s)" % handled)
    else:
        logger.debug("no pending state cleanups")
    return handled

def handle_session_cleanup(configuration, now=time.time()):
    """Inspect various state dirs to clean up stale session files specifically.
    Returns the number of actual actions taken for central throttle handling.
    """
    handled = 0
    logger.debug("handle pending session cleanups")
    if configuration.site_enable_jobs:
        handled += clean_sessid_to_mrls_link_home(configuration, now)
    handled += clean_twofactor_sessions(configuration, now)
    # TODO: handle client session tracking cleanup (cleansessions.py)
    if handled > 0:
        logger.info("handled %d pending session cleanup(s)" % handled)
    else:
        logger.debug("no pending session cleanups")
    return handled

def remind_and_expire_user_pending(configuration, now=time.time()):
    """Inspect user_pending dir and inform about pending but aging account
    requests that need operator or user action.
    Returns the number of actual actions taken for central throttle handling.
    """
    handled = 0
    now = time.time()
    for filename in listdir(configuration.user_pending):
        if filename.startswith('.'):
            continue
        req_path = os.path.join(configuration.user_pending, filename)
        logger.debug("checking account request in %r" % req_path)
        req_age = now - os.path.getmtime(req_path)
        req_age_days = req_age / SECS_PER_DAY
        if req_age_days > REMIND_REQ_DAYS:
            logger.info("found stale account request in %r : %dd" % \
                        (req_path, req_age_days))
            # TODO: actually remind operator and user that request is pending
            handled += 1
        if req_age_days > EXPIRE_REQ_DAYS:
            logger.info("found expired account request in %r : %dd" % \
                        (req_path, req_age_days))
            # TODO: actually expire request and inform user
            handled += 1
    logger.debug("handled %d user account request action(s)" % handled)
    return handled

def handle_pending_requests(configuration, now=time.time()):
    """Inspect various state dirs to remind or clean up stale requests.
    Returns the number of actual actions taken for central throttle handling.
    """
    handled = 0
    logger.debug("handle pending requests")
    handled += remind_and_expire_user_pending(configuration, now)
    # TODO: actually handle more requests like resources and peers
    if handled > 0:
        logger.info("handled %d pending requests" % handled)
    else:
        logger.debug("no pending state cleanups")
    return handled

def handle_cache_updates(configuration, now=time.time()):
    """Inspect internal cache update markers and handle any corresponding cache
    updates in one place to avoid thrashing.
    Returns the number of actual actions taken for central throttle handling.
    """
    handled = 0
    logger.debug("handle pending cache updates")
    # TODO: actually handle vgrid/user/resource/... cache updates
    if handled > 0:
        logger.info("handled %d pending cache updates" % handled)
    else:
        logger.debug("no pending state cleanups")
    return handled

def handle_janitor_tasks(configuration, now=time.time()):
    """A wrapper to take care of all regular janitor tasks like clean up and
    cache updates.
    Returns the number of actual tasks completed to let the main thread know if
    it should throttle down or continue next run right away.
    """
    tasks_completed = 0
    logger.info("handle any pending janitor tasks")
    if _lookup_last_run(configuration, 'state-cleanup') + SECS_PER_DAY < now:
        tasks_completed += handle_state_cleanup(configuration, now)
        _update_last_run(configuration, 'state-cleanup', now)
    if _lookup_last_run(configuration, 'session-cleanup') + SECS_PER_HOUR < now:
        tasks_completed += handle_session_cleanup(configuration, now)
        _update_last_run(configuration, 'state-cleanup', now)
    if _lookup_last_run(configuration, 'pending-requests') + SECS_PER_HOUR < now:
        tasks_completed += handle_pending_requests(configuration, now)
        _update_last_run(configuration, 'pending-requests', now)
    if _lookup_last_run(configuration, 'cache-updates') + SECS_PER_MINUTE < now:
        tasks_completed += handle_cache_updates(configuration, now)
        _update_last_run(configuration, 'cache-updates', now)
    if tasks_completed > 0:
        logger.info("handled %d janitor task(s)" % tasks_completed)
    else:
        logger.info("janitor found no pending tasks")
    return tasks_completed

if __name__ == "__main__":
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ["debug", "info", "warning", "error"]:
        log_level = sys.argv[1]

    # Use separate logger

    logger = daemon_logger("janitor", configuration.user_janitor_log, log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates
    register_hangup_handler(configuration)

    # Allow clean shutdown on SIGINT only to main process
    signal.signal(signal.SIGINT, stop_handler)

    if not configuration.site_enable_janitor:
        err_msg = "Janitor support is disabled in configuration!"
        logger.error(err_msg)
        print(err_msg)
        sys.exit(1)

    print(
        """This is the MiG janitor daemon which cleans up stale state data,
updates internal caches and prunes pending requests.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    )

    main_pid = os.getpid()
    print("Starting janitor daemon - Ctrl-C to quit")
    logger.info("(%s) Starting Janitor daemon" % main_pid)

    logger.debug("(%s) Starting main loop" % main_pid)
    print("%s: Start main loop" % os.getpid())
    while not stop_running.is_set():
        try:
            now = time.time()
            if handle_janitor_tasks(configuration, now) <= 0:
                time.sleep(LONG_THROTTLE_SECS)
            else:
                time.sleep(SHORT_THROTTLE_SECS)
        except KeyboardInterrupt:
            stop_running.set()
            # NOTE: we can't be sure if SIGINT was sent to only main process
            #       so we make sure to propagate to monitor child
            print("Interrupt requested - shutdown")
        except Exception as exc:
            logger.error(
                "(%s) Caught unexpected exception: %s" % (os.getpid(), exc)
            )

    print("Janitor daemon shutting down")
    logger.info("(%s) Janitor daemon shutting down" % main_pid)

    sys.exit(0)
