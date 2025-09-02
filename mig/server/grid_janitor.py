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

from mig.shared.accountreq import accept_account_req, reject_account_req
from mig.shared.base import get_user_id
from mig.shared.conf import get_configuration_object
from mig.shared.fileio import listdir, delete_file
from mig.shared.logger import daemon_logger, register_hangup_handler
from mig.shared.pwcrypto import verify_reset_token
from mig.shared.serial import load
from mig.shared.userdb import load_user_dict, default_db_path

# TODO: adjust short to subsecond and long to e.g a minute for production use
#SHORT_THROTTLE_SECS = 0.5
#LONG_THROTTLE_SECS = 60.0
SHORT_THROTTLE_SECS = 5.0
LONG_THROTTLE_SECS = 30.0

REMIND_REQ_DAYS = 5
EXPIRE_REQ_DAYS = 30
MANAGE_TRIVIAL_REQ_MINUTES = 5

EXPIRE_STATE_DAYS = 30
EXPIRE_DUMMY_JOBS_DAYS = 7
EXPIRE_TWOFACTOR_DAYS = 1

SECS_PER_MINUTE = 60
SECS_PER_HOUR = 60 * SECS_PER_MINUTE
SECS_PER_DAY =24 * SECS_PER_HOUR

stop_running = multiprocessing.Event()
(configuration, logger) = (None, None)

task_triggers = {}


# TODO: add a signal handler to force run pending tasks right away

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
    # TODO: add a more persistent marker e.g. in mig system run or files to
    #      remember last status across restarts and reboots?
    task_triggers[target] = stamp
    return task_triggers[target]


def _clean_stale_state_files(configuration, target_dir, filename_patterns,
                             expire_days, now, include_dotfiles=False):
    """Inspect and clean up stale state files matching any of filename_pattern
    in target_dir if they are at least expire_days old. Where filename_pattern
    is a list of wildcard strings checked with fnmatch. Dot-files are excluded
    from matching unless include_dotfiles is set. Directories are just skipped.
    Returns the number of actual actions taken for central throttle handling.
    """
    handled = 0
    logger.debug("clean files matching %r in %r if older than %dd" % \
                 (filename_patterns, target_dir, expire_days))
    for filename in listdir(target_dir):
        tmp_path = os.path.join(target_dir, filename)
        if not include_dotfiles and filename.startswith('.'):
            continue
        if os.path.isdir(tmp_path):
            continue
        tmp_age = -1
        for pattern in filename_patterns:
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

def manage_single_req(configuration, req_id, req_path, db_path, now):
    """Inspect single request in req_path and take care of it if it does not
    require operator interaction. That is, accept or reject password reset
    depending on reset token validity, renew account if the complete peer
    acceptance is in place and reject request if obviously invalid.
    """
    req_dict = load(req_path)
    client_id = get_user_id(configuration, req_dict)
    # NOTE: use timestamp from saved request file if available
    req_timestamp = req_dict.get('accepted_terms', now)
    user_dict = load_user_dict(logger, client_id, db_path)
    req_invalid = req_dict.get('invalid', None)
    reset_token = req_dict.get('reset_token', '')
    req_auth = req_dict.get('auth', ['migoid'])[-1]
    auth_type = req_auth.lstrip('mig').lstrip('ext')
    user_copy = True
    admin_copy = True
    default_renew = False
    if req_invalid:
        logger.info("%r made an invalid account request"% client_id)
        # NOTE: 'invalid' is a list of validation error strings if set
        reason = 'invalid request: %s.' % '. '.join(req_invalid)
        if not reject_account_req(req_id, configuration, reason,
                                  user_copy=user_copy,
                                  admin_copy=admin_copy,
                                  auth_type=auth_type):
            logger.warning("failed to reject invalid %r account request"
                           % client_id)
        else:
            logger.info("rejected invalid %r account request" % \
                        client_id)
    elif reset_token:
        valid_reset = verify_reset_token(configuration,
                                         user_dict,
                                         reset_token,
                                         req_auth,
                                         req_timestamp)
        if valid_reset:
            logger.info("%r requested and authorized password reset" % \
                        client_id)
            peer_id = user_dict.get('peers', [None])[0]
            if not accept_account_req(req_id, configuration, peer_id,
                                      user_copy=user_copy,
                                      admin_copy=admin_copy,
                                      auth_type=auth_type,
                                      default_renew=default_renew):
                logger.warning("failed to accept %r password reset" % \
                               client_id)
            else:
                logger.info("accepted %r password reset" % client_id)
        else:
            logger.warning("%r requested password reset with bad token"
                           % client_id)
            reason = 'invalid password reset token'
            if not reject_account_req(req_id, configuration, reason,
                                      user_copy=user_copy,
                                      admin_copy=admin_copy,
                                      auth_type=auth_type):
                logger.warning("failed to reject %r password reset" % \
                               client_id)
            else:
                logger.info("rejected %r password reset" % client_id)
    elif user_dict:
        logger.info("%r requested access renewal" % client_id)
        # TODO: renew if trivial with valid peer
    else:
        logger.info("%r requested a new account requiring operator" % \
                    client_id)

def manage_trivial_user_requests(configuration, now=time.time()):
    """Inspect user_pending dir and take care of any request, which do not
    require operator interaction. That is, accept or reject any password reset
    requests depending on reset token validity, renew any with complete peer
    acceptance and reject any obviously invalid requests.
    Returns the number of actual actions taken for central throttle handling.
    """
    # TODO: add simple logic to mark invalid requests already during submit?
    #       could e.g. be
    #       * non-existant, unauthorized or invalid peer
    #       * unauthorized password change
    #       * single word in full name
    #       ...
    #       Then use the invalid marker to reject in manage_single_req
    handled = 0
    now = time.time()
    db_path = default_db_path(configuration)
    for filename in listdir(configuration.user_pending):
        if filename.startswith('.'):
            continue
        req_id = filename
        req_path = os.path.join(configuration.user_pending, req_id)
        logger.debug("checking if account request in %r is trivial" % req_path)
        req_age = now - os.path.getmtime(req_path)
        req_age_minutes = req_age / SECS_PER_MINUTE
        if req_age_minutes > MANAGE_TRIVIAL_REQ_MINUTES:
            logger.info("found pending account request in %r : %dm" % \
                        (req_path, req_age_minutes))
            manage_single_req(configuration, req_id, req_path, db_path, now)
            handled += 1
    logger.debug("handled %d trivial user account request action(s)" % handled)
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
        req_id = filename
        req_path = os.path.join(configuration.user_pending, req_id)
        logger.debug("checking account request in %r" % req_path)
        req_age = now - os.path.getmtime(req_path)
        req_age_days = req_age / SECS_PER_DAY
        req_dict = load(req_path)
        client_id = get_user_id(configuration, req_dict)
        req_auth = req_dict.get('auth', ['migoid'])[-1]
        auth_type = req_auth.lstrip('mig').lstrip('ext')
        if req_age_days > REMIND_REQ_DAYS:
            logger.info("found stale account request in %r : %dd" % \
                        (req_path, req_age_days))
            # TODO: actually remind operator and user that request is pending
            #       ... possibly with copy to peers if pending acceptance.
            handled += 1
        if req_age_days > EXPIRE_REQ_DAYS:
            logger.info("found expired account request from %r in %s : %dd" % \
                        (client_id, req_path, req_age_days))            
            reason = 'failed to be verified and accepted within %d day limit' \
                     % EXPIRE_REQ_DAYS
            user_copy = True
            admin_copy = True
            if not reject_account_req(req_id, configuration, reason,
                                      user_copy=user_copy,
                                      admin_copy=admin_copy,
                                      auth_type=auth_type):
                logger.warning("failed to expire %s request from %r" % \
                               (req_id, client_id))
            else:
                logger.info("expired %s request from %r" % (req_id, client_id))
            handled += 1
    logger.debug("handled %d user account request action(s)" % handled)
    return handled

def handle_pending_requests(configuration, now=time.time()):
    """Inspect various state dirs to remind or clean up stale requests.
    Returns the number of actual actions taken for central throttle handling.
    """
    handled = 0
    logger.debug("handle pending requests")
    handled += manage_trivial_user_requests(configuration, now)
    handled += remind_and_expire_user_pending(configuration, now)
    # TODO: actually handle more requests like resources and peers
    if handled > 0:
        logger.info("handled %d pending requests" % handled)
    else:
        logger.debug("no pending requests")
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
    if _lookup_last_run(configuration, 'pending-reqs') + SECS_PER_MINUTE < now:
        tasks_completed += handle_pending_requests(configuration, now)
        _update_last_run(configuration, 'pending-reqs', now)
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
