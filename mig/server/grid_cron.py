#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# grid_cron - daemon to monitor user crontabs and trigger actions
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Daemon to monitor user crontabs and trigger any associated actions when
configured.

Requires watchdog module (https://pypi.python.org/pypi/watchdog).
"""

import datetime
import fnmatch
import glob
import logging
import logging.handlers
import os
import signal
import sys
import tempfile
import time
import threading
import multiprocessing

try:
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler, \
        FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, \
        DirModifiedEvent, DirCreatedEvent, DirDeletedEvent
except ImportError:
    print 'ERROR: the python watchdog module is required for this daemon'
    sys.exit(1)

# Use the scandir module version if available:
# https://github.com/benhoyt/scandir
# Otherwise fail

try:
    from scandir import scandir, walk, __version__ as scandir_version
    if float(scandir_version) < 1.3:

        # Important os.walk compatibility utf8 fixes were not added until 1.3

        raise ImportError('scandir version is too old >= 1.3 required')
except ImportError, exc:
    print 'ERROR: %s' % str(exc)
    sys.exit(1)

from shared.base import force_utf8, client_dir_id, client_id_dir
from shared.conf import get_configuration_object
from shared.defaults import crontab_name, cron_log_name, \
    cron_log_size, cron_log_cnt, csrf_field
from shared.events import get_time_expand_map, map_args_to_vars, \
    get_command_map, parse_crontab, cron_match
from shared.fileio import makedirs_rec
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.job import fill_mrsl_template, new_job
from shared.logger import daemon_logger, reopen_log

# Global cron entry dictionaries with crontabs for all users

all_crontabs = {}

# TODO: we only run ONE handler process - eliminate shared state?

# Global state helpers used in a number of functions and methods

shared_state = {}
shared_state['base_dir'] = None
shared_state['base_dir_len'] = 0
shared_state['crontab_inotify'] = None
shared_state['crontab_handler'] = None

_cron_event = '_cron_event'
stop_running = multiprocessing.Event()
(configuration, logger) = (None, None)


def stop_handler(sig, frame):
    """A simple signal handler to quit on Ctrl+C (SIGINT) in main"""
    # Print blank line to avoid mix with Ctrl-C line
    print ''
    stop_running.set()

def hangup_handler(sig, frame):
    """A simple signal handler to force log reopening on SIGHUP"""

    pid = multiprocessing.current_process().pid
    logger.info('(%s) reopening log in reaction to hangup signal' % pid)
    reopen_log(configuration)
    logger.info('(%s) reopened log after hangup signal' % pid)


def run_command(
    command_list,
    target_path,
    crontab_entry,
    configuration,
    ):
    """Run backend command built from command_list on behalf of user from
    crontab_entry and with args mapped to the backend variables.
    """

    pid = multiprocessing.current_process().pid
    command_map = get_command_map(configuration)
    logger.info('(%s) run command for %s: %s' % (pid, target_path,
                command_list))
    if not command_list or not command_list[0] in command_map:
        raise ValueError('unsupported command: %s' % command_list[0])
    function = command_list[0]
    args_form = command_map[function]
    client_id = crontab_entry['run_as']
    command_str = ' '.join(command_list)

    # logger.debug('(%s) run %s on behalf of %s' % (pid, command_str,
    #             client_id))

    user_arguments_dict = map_args_to_vars(args_form, command_list[1:])

    form_method = 'post'
    target_op = "%s" % function
    csrf_limit = get_csrf_limit(configuration)
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    user_arguments_dict[csrf_field] = [csrf_token]

    # logger.debug('(%s) import main from %s' % (pid, function))

    main = id
    txt_format = id
    try:
        exec 'from shared.functionality.%s import main' % function
        exec 'from shared.output import txt_format'

        # logger.debug('(%s) run %s on %s for %s' % \
        #              (pid, function, user_arguments_dict, client_id))

        # Fake HTTP POST manually setting fields required for CSRF check

        os.environ['HTTP_USER_AGENT'] = 'grid cron daemon'
        os.environ['PATH_INFO'] = '%s.py' % function
        os.environ['REQUEST_METHOD'] = form_method.upper()
        (output_objects, (ret_code, ret_msg)) = main(client_id,
                user_arguments_dict)
    except Exception, exc:
        logger.error('(%s) failed to run %s main on %s: %s' % \
                     (pid, function, user_arguments_dict, exc))
        import traceback
        logger.info('traceback:\n%s' % traceback.format_exc())
        raise exc
    logger.info('(%s) done running command for %s: %s' % (pid,
                target_path, command_str))

    # logger.debug('(%s) raw output is: %s' % (pid, output_objects))

    try:
        txt_out = txt_format(configuration, ret_code, ret_msg,
                             output_objects)
    except Exception, exc:
        txt_out = 'internal command output text formatting failed'
        logger.error('(%s) text formating failed: %s\nraw output is: %s %s %s'
                      % (pid, exc, ret_code, ret_msg, output_objects))
    if ret_code != 0:
        logger.warning('(%s) command finished but with error code %d :\n%s' \
                       % (pid, ret_code, output_objects))
        raise Exception('command error: %s' % txt_out)


    # logger.debug('(%s) result was %s : %s:\n%s' % (pid, ret_code,
    #                                               ret_msg, txt_out))


class MiGCrontabEventHandler(PatternMatchingEventHandler):

    """Crontab pattern-matching event handler to take care of crontab changes
    and update the global crontab database.
    """

    def __init__(
        self,
        patterns=None,
        ignore_patterns=None,
        ignore_directories=False,
        case_sensitive=False,
        ):
        """Constructor"""

        PatternMatchingEventHandler.__init__(self, patterns,
                ignore_patterns, ignore_directories, case_sensitive)

    def __update_crontab_monitor(
        self,
        configuration,
        src_path,
        state,
        ):

        pid = multiprocessing.current_process().pid

        if state == 'created':

            # logger.debug('(%s) Updating crontab monitor for src_path: %s, event: %s'
            #              % (pid, src_path, state))

            print '(%s) Updating crontab monitor for src_path: %s, event: %s' \
                % (pid, src_path, state)

            if os.path.exists(src_path):

                # _crontab_monitor_lock.acquire()

                if not shared_state['crontab_inotify']._wd_for_path.has_key(src_path):

                    # logger.debug('(%s) Adding watch for: %s' % (pid,
                    #             src_path))

                    shared_state['crontab_inotify'].add_watch(force_utf8(src_path))

                    # Fire 'modified' events for all dirs and files in subpath
                    # to ensure that all crontab files are loaded

                    for ent in scandir(src_path):
                        if ent.is_dir(follow_symlinks=True):

                            # logger.debug('(%s) Dispatch DirCreatedEvent for: %s'
                            #         % (pid, ent.path))

                            shared_state['crontab_handler'].dispatch(DirCreatedEvent(ent.path))
                        elif ent.path.find(configuration.user_settings) \
                            > -1:

                            # logger.debug('(%s) Dispatch FileCreatedEvent for: %s'
                            #         % (pid, ent.path))

                            shared_state['crontab_handler'].dispatch(FileCreatedEvent(ent.path))

                # else:
                #    logger.debug('(%s) crontab_monitor watch already exists for: %s'
                #                  % (pid, src_path))
        else:
           logger.debug('(%s) unhandled event: %s for: %s' % (pid,
                        state, src_path))

    def update_crontabs(self, event):
        """Handle all crontab updates"""

        pid = multiprocessing.current_process().pid
        state = event.event_type
        src_path = event.src_path

        if event.is_directory:
            self.__update_crontab_monitor(configuration, src_path, state)
        elif os.path.basename(src_path) == crontab_name:
            logger.debug('(%s) %s -> Updating crontab for: %s' % (pid,
                         state, src_path))
            rel_path = src_path[len(configuration.user_settings):]
            client_dir = os.path.basename(os.path.dirname(src_path))
            client_id = client_dir_id(client_dir)
            user_home = os.path.join(configuration.user_home, client_dir)
            logger.info('(%s) refresh %s crontab from %s' % (pid,
                        client_id, src_path))
            if state == 'deleted':
                cur_crontab = []
                logger.debug("(%s) deleted crontab from '%s'" % \
                             (pid, src_path))
            else:
                cur_crontab = parse_crontab(configuration, client_id, src_path)
                logger.debug("(%s) loaded new crontab from '%s':\n%s" % \
                             (pid, src_path, cur_crontab))

            # Replace crontabs for this user
            
            all_crontabs[src_path] = cur_crontab
            logger.debug('(%s) all crontabs: %s' % (pid, all_crontabs))
        else:
            logger.debug('(%s) %s skipping _NON_ crontab file: %s' % (pid,
                         state, src_path))

    def on_modified(self, event):
        """Handle modified crontab file"""

        self.update_crontabs(event)

    def on_created(self, event):
        """Handle new crontab file"""

        self.update_crontabs(event)

    def on_deleted(self, event):
        """Handle deleted crontab file"""

        self.update_crontabs(event)


def __cron_log(configuration, client_id, msg, level="info"):
        """Wrapper to send a single msg to user cron log file"""

        client_dir = client_id_dir(client_id)
        log_path = os.path.join(configuration.user_home, client_dir,
                                cron_log_name)
        cron_logger = logging.getLogger('cron')
        cron_logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(log_path,
                maxBytes=cron_log_size,
                backupCount=cron_log_cnt - 1)
        formatter = \
            logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        cron_logger.addHandler(handler)
        if level == 'error':
            cron_logger.error(msg)
        elif level == 'warning':
            cron_logger.warning(msg)
        else:
            cron_logger.info(msg)
        handler.flush()
        handler.close()
        cron_logger.removeHandler(handler)

def __cron_err(configuration, client_id, msg):
    """Wrapper to send a single error msg to client_id cron log"""

    __cron_log(configuration, client_id, msg, 'error')

def __cron_warn(configuration, client_id,  msg):
    """Wrapper to send a single warning msg to client_id cron log"""

    __cron_log(configuration, client_id, msg, 'warning')

def __cron_info(configuration, client_id,  msg):
    """Wrapper to send a single info msg to client_id cron log"""

    __cron_log(configuration, client_id, msg, 'info')


def __handle_cronjob(configuration, client_id, timestamp, crontab_entry):
    """Actually handle valid crontab entry which is due"""

    pid = multiprocessing.current_process().pid
    logger.info('(%s) in handling of %s for %s' % (pid,
                    crontab_entry['command'], client_id))
    __cron_info(configuration, client_id, 'handle %s for %s' % \
                (crontab_entry['command'], client_id))

    if crontab_entry['run_as'] != client_id:
        logger.error('(%s) skipping due to owner mismatch for %s and %s!' % \
                     (pid, client_id, crontab_entry))
        return False

    # Expand dynamic time variables in argument once and for all

    expand_map = get_time_expand_map(timestamp, crontab_entry)
    command_list = crontab_entry['command'][:1]
    for argument in crontab_entry['command'][1:]:
        filled_argument = argument
        for (key, val) in expand_map.items():
            filled_argument = filled_argument.replace(key, val)
        __cron_info(configuration, client_id,
                    'expanded argument %s to %s' % \
                    (argument, filled_argument))
        command_list.append(filled_argument)
    try:
        run_command(command_list, client_id, crontab_entry, configuration)
        logger.info('(%s) done running command for %s: %s' % \
                    (pid, client_id, ' '.join(command_list)))
        __cron_info(configuration, client_id,
                    'ran command: %s' % ' '.join(command_list))
    except Exception, exc:
        command_str = ' '.join(command_list)
        logger.error('(%s) failed to run command for %s: %s (%s)' % \
                     (pid, client_id, command_str, exc))
        __cron_err(configuration, client_id,
                       'failed to run command: %s (%s)' % (command_str, exc))


def run_handler(configuration, client_id, timestamp, crontab_entry):
    """Run crontab entry for client_id in a separate thread"""

    pid = multiprocessing.current_process().pid

    # TODO: Replace try / catch with a 'event queue / thread pool' setup

    waiting_for_thread_resources = True
    while waiting_for_thread_resources:
        try:
            worker = \
                   threading.Thread(target=__handle_cronjob,
                                    args=(configuration, client_id,
                                          timestamp, crontab_entry))
            worker.daemon = True
            worker.start()
            waiting_for_thread_resources = False
        except threading.ThreadError, exc:

            # logger.debug('(%s) Waiting for thread resources to handle crontab: %s'
            #              % (pid, crontab_entry))
            
            time.sleep(1)


def monitor(configuration):
    """Monitors the filesystem for crontab changes"""

    pid = multiprocessing.current_process().pid

    print 'Starting global crontab monitor process'
    logger.info('Starting global crontab monitor process')

    # Set base_dir and base_dir_len

    shared_state['base_dir'] = os.path.join(configuration.user_settings)
    shared_state['base_dir_len'] = len(shared_state['base_dir'])

    # Allow e.g. logrotate to force log re-open after rotates

    signal.signal(signal.SIGHUP, hangup_handler)

    # Monitor crontab configurations

    crontab_monitor_home = shared_state['base_dir']
    recursive_crontab_monitor = True

    crontab_monitor = Observer()
    crontab_pattern = os.path.join(crontab_monitor_home, '*', crontab_name)
    shared_state['crontab_handler'] = MiGCrontabEventHandler(
        patterns=[crontab_pattern], ignore_directories=False,
        case_sensitive=True)

    crontab_monitor.schedule(shared_state['crontab_handler'],
                          configuration.user_settings,
                          recursive=recursive_crontab_monitor)
    crontab_monitor.start()

    if len(crontab_monitor._emitters) != 1:
        logger.error('(%s) Number of crontab_monitor._emitters != 1' % pid)
        return 1
    crontab_monitor_emitter = min(crontab_monitor._emitters)
    if not hasattr(crontab_monitor_emitter, '_inotify'):
        logger.error('(%s) crontab_monitor_emitter require inotify' % pid)
        return 1
    shared_state['crontab_inotify'] = crontab_monitor_emitter._inotify._inotify

    logger.info('(%s) trigger crontab refresh' % (pid, ))

    # Fake touch event on all crontab files to load initial crontabs

    logger.info('(%s) trigger load on all crontab files (greedy) matching %s'
                 % (pid, crontab_pattern))

    # We manually walk and test to get the greedy "*" directory match behaviour
    # of the PatternMatchingEventHandler

    all_crontab_files = []

    for (root, _, files) in walk(crontab_monitor_home):
        if crontab_name in files:
            crontab_path = os.path.join(root, crontab_name)
            all_crontab_files.append(crontab_path)

    for crontab_path in all_crontab_files:

        # logger.debug('(%s) trigger load on crontabs in %s' % (pid,
        #             crontab_path))

        shared_state['crontab_handler'].dispatch(FileModifiedEvent(crontab_path))

    # logger.debug('(%s) loaded initial crontabs:\n%s' % (pid, all_crontab_files))

    while not stop_running.is_set():
        try:
            loop_start = datetime.datetime.now()
            logger.debug('main loop started with %d crontabs' % \
                         len(all_crontabs))
            for crontab_path, user_crontab in all_crontabs.items():
                client_dir = os.path.basename(os.path.dirname(crontab_path))
                client_id = client_dir_id(client_dir)
                for entry in user_crontab:
                    logger.debug('inspect cron entry for %s: %s' % \
                                 (client_id, entry))
                    if cron_match(configuration, loop_start, entry):
                        logger.info('run matching cron entry: %s' % entry)
                        run_handler(configuration, client_id, loop_start,
                                    entry)
        except KeyboardInterrupt:
            print '(%s) caught interrupt' % pid
            stop_running.set()
        except Exception, exc:
            logger.error('unexpected exception in monitor: %s' % exc)
            import traceback
            print traceback.format_exc()

        # Throttle down until next minute

        loop_time = (datetime.datetime.now() - loop_start).seconds
        if loop_time > 60:
            logger.warning('(%s) loop did not finish before next tick: %s' % \
                           (os.getpid(), loop_time))
            loop_time = 59
        # Target sleep until start of next minute
        sleep_time = max(60 - (loop_time + loop_start.second), 1)
        # TODO: this debug log never shows up - conflict with user info log?
        #       at least it does if changed to info.
        logger.debug('main loop sleeping %ds' % sleep_time)
        #print('main loop sleeping %ds' % sleep_time)
        time.sleep(sleep_time)


    print '(%s) Exiting crontab monitor' % pid
    logger.info('(%s) Exiting crontab monitor' % pid)
    return 0


if __name__ == '__main__':
    # Force no log init since we use separate logger
    configuration = get_configuration_object(skip_log=True)

    log_level = configuration.loglevel
    if sys.argv[1:] and sys.argv[1] in ['debug', 'info', 'warning',
            'error']:
        log_level = sys.argv[1]

    # Use separate logger

    logger = daemon_logger('cron', configuration.user_cron_log,
                           log_level)
    configuration.logger = logger

    # Allow e.g. logrotate to force log re-open after rotates

    signal.signal(signal.SIGHUP, hangup_handler)

    # Allow clean shutdown on SIGINT only to main process

    signal.signal(signal.SIGINT, stop_handler)

    if not configuration.site_enable_crontab:
        err_msg = "Cron support is disabled in configuration!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)

    print '''This is the MiG cron handler daemon which monitors user crontab
files and reacts to any configured actions when time is up.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
'''

    main_pid = os.getpid()
    print 'Starting Cron handler daemon - Ctrl-C to quit'
    logger.info('(%s) Starting Cron handler daemon' % main_pid)

    # Start a single global monitor for all crontabs

    crontab_monitor = multiprocessing.Process(target=monitor,
                                              args=(configuration, ))
    crontab_monitor.start()

    logger.debug('(%s) Starting main loop' % main_pid)
    print "%s: Start main loop" % os.getpid()
    while not stop_running.is_set():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            stop_running.set()
            # NOTE: we can't be sure if SIGINT was sent to only main process
            #       so we make sure to propagate to monitor child
            print "Interrupt requested - close monitor and shutdown"
            logger.info('(%s) Shut down monitor and wait' % os.getpid())
            mon_pid = crontab_monitor.pid
            if mon_pid is not None:
                logger.debug('send exit signal to monitor %s' % mon_pid)
                os.kill(mon_pid, signal.SIGINT)
            break
        except Exception, exc:
            logger.error('(%s) Caught unexpected exception: %s' % (os.getpid(),
                                                                   exc))
            
    mon_pid = crontab_monitor.pid
    logger.info('Wait for crontab monitors to clean up')
    crontab_monitor.join(5)
    if crontab_monitor.is_alive():
        logger.warning("force kill %s: %s" % (mon_pid,
                                              crontab_monitor.is_alive()))
        crontab_monitor.terminate()
    else:
        logger.debug('crontab monitor %s: done' % mon_pid)

    print 'Cron handler daemon shutting down'
    logger.info('(%s) Cron handler daemon shutting down' % main_pid)

    sys.exit(0)
