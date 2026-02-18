#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# events - shared event trigger and cron/at helper functions
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
# -- END_HEADER ---
#

"""Event trigger and cron/at helper functions"""

from __future__ import print_function
from __future__ import absolute_import

import datetime
import fnmatch
import importlib
import multiprocessing
import logging
import logging.handlers
import os
import re
import shlex
import threading
import time

from mig.shared.base import client_id_dir
from mig.shared.cmdapi import parse_command_args
from mig.shared.defaults import atjobs_name, cron_log_cnt, cron_log_name, \
    cron_log_size, crontab_name, cron_output_dir, csrf_field
from mig.shared.fileio import read_file, read_file_lines, write_file
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.output import txt_format

# Init global crontab regexp once and for all
# Format: minute hour dayofmonth month dayofweek command
crontab_pattern = "^(\*|[0-9]{1,2}) (\*|[0-9]{1,2}) (\*|[0-9]{1,2}) "
crontab_pattern += "(\*|[0-9]{1,2}) (\*|[0-6]) (.*)$"
crontab_expr = re.compile(crontab_pattern)
# Init global atjobs regexp once and for all
# ISO format with space between date and time and without msecs:
# YYYY-MM-DD HH:MM:SS COMMAND
atjobs_pattern = "^([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):"
atjobs_pattern += "([0-9]{2}) (.*)$"
atjobs_expr = re.compile(atjobs_pattern)

TRIGGER_EVENT = '_trigger_event'

# Only cache rule misses for one minute at a time to catch rule updates.
# Run complete expire cycle if miss cache exceeds expire size.

MISS_CACHE_TTL = 60
CACHE_EXPIRE_SIZE = 10000

# Rate limit helpers

(RATE_LIMIT_FIELD, SETTLE_TIME_FIELD) = ('rate_limit', 'settle_time')
DEFAULT_PERIOD = 'm'
DEFAULT_TIME = '0'
UNIT_PERIODS = {
    's': 1,
    'm': 60,
    'h': 60 * 60,
    'd': 24 * 60 * 60,
    'w': 7 * 24 * 60 * 60,
}

_hits_lock = threading.Lock()
rule_hits = {}


def get_path_expand_map(configuration, trigger_path, rule, state_change):
    """Generate a dictionary with the supported variables to be expanded and
    the actual expanded values based on trigger_path and rule dictionary.
    """

    trigger_filename = os.path.basename(trigger_path)
    trigger_dirname = os.path.dirname(trigger_path)
    trigger_relpath = os.path.relpath(trigger_path, rule['vgrid_name'])
    trigger_reldirname = os.path.dirname(trigger_relpath)
    (prefix, extension) = os.path.splitext(trigger_filename)
    expand_map = {
        '+TRIGGERPATH+': trigger_path,
        '+TRIGGERRELPATH+': trigger_relpath,
        '+TRIGGERDIRNAME+': trigger_dirname,
        '+TRIGGERRELDIRNAME+': trigger_reldirname,
        '+TRIGGERFILENAME+': trigger_filename,
        '+TRIGGERPREFIX+': prefix,
        '+TRIGGEREXTENSION+': extension,
        '+TRIGGERCHANGE+': state_change,
        '+TRIGGERVGRIDNAME+': rule['vgrid_name'],
        '+TRIGGERRUNAS+': rule['run_as'],
    }

    # TODO: provide exact expanded wildcards?

    return expand_map


def get_time_expand_map(configuration, timestamp, rule):
    """Generate a dictionary with the supported variables to be expanded and
    the actual expanded values based on datetime timestamp and crontab rule
    dictionary.
    """

    # NOTE: we force two digits in the values where it can be one or two
    expand_map = {
        '+SCHEDSECOND+': "%.2d" % timestamp.second,
        '+SCHEDMINUTE+': "%.2d" % timestamp.minute,
        '+SCHEDHOUR+': "%.2d" % timestamp.hour,
        '+SCHEDDAY+': "%.2d" % timestamp.day,
        '+SCHEDMONTH+': "%.2d" % timestamp.month,
        '+SCHEDYEAR+': "%d" % timestamp.year,
        '+SCHEDDAYOFWEEK+': "%d" % timestamp.weekday(),
        '+SCHEDRUNAS+': rule['run_as'],
    }
    return expand_map


def load_crontab(client_id, configuration, allow_missing=True):
    """Load entries from plain user crontab file"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    crontab_path = os.path.join(configuration.user_settings, client_dir,
                                crontab_name)
    crontab_contents = read_file(crontab_path, _logger,
                                 allow_missing=allow_missing)
    if crontab_contents is None:
        if not allow_missing:
            _logger.error('failed reading %s crontab file' % client_id)
        crontab_contents = ''
    return crontab_contents


def load_atjobs(client_id, configuration, allow_missing=True):
    """Load entries from plain user atjobs file"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    atjobs_path = os.path.join(configuration.user_settings, client_dir,
                               atjobs_name)
    atjobs_contents = read_file(atjobs_path, _logger,
                                allow_missing=allow_missing)
    if atjobs_contents is None:
        if not allow_missing:
            _logger.error('failed reading %s atjobs file' % client_id)
        atjobs_contents = ''
    return atjobs_contents


def parse_crontab_contents(configuration, client_id, crontab_lines):
    """Parse raw crontab content lines and return a list of crontab dictionary
    entries.
    """
    _logger = configuration.logger
    crontab_entries = []
    for line in crontab_lines:
        # Ignore comments and blanks
        line = (line.split("#")[0]).strip()
        if not line:
            continue
        hit = crontab_expr.match(line.strip())
        if not hit:
            _logger.warning("Skip invalid crontab line for %s: %s" %
                            (client_id, line))
            continue
        # Format: minute hour dayofmonth month dayofweek command
        entry = {'minute': hit.group(1), 'hour': hit.group(2),
                 'dayofmonth': hit.group(3), 'month': hit.group(4),
                 'dayofweek': hit.group(5),
                 'command': shlex.split(hit.group(6)), 'run_as': client_id}
        crontab_entries.append(entry)
    return crontab_entries


def parse_atjobs_contents(configuration, client_id, atjobs_lines):
    """Parse raw atjobs content lines and return a list of atjobs dictionary
    entries.
    """
    _logger = configuration.logger
    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0)
    atjobs_entries = []
    for line in atjobs_lines:
        # Ignore comments and blanks
        line = (line.split("#")[0]).strip()
        if not line:
            continue
        hit = atjobs_expr.match(line.strip())
        if not hit:
            _logger.warning("Skip invalid atjobs line for %s: %s" %
                            (client_id, line))
            continue
        # ISO format (see top)
        try:
            when = datetime.datetime(int(hit.group(1)), int(hit.group(2)),
                                     int(hit.group(3)), int(hit.group(4)),
                                     int(hit.group(5)), int(hit.group(6)))
        except Exception as exc:
            _logger.warning("Skip invalid atjobs line for %s: %s (%s)" %
                            (client_id, line, exc))
            continue

        # Ignore seconds
        when = when.replace(second=0)
        cmd_list = shlex.split(hit.group(7))
        entry = {'time_stamp': when, 'run_as': client_id, 'command': cmd_list}
        if (when - now).total_seconds() >= 0:
            atjobs_entries.append(entry)
        else:
            _logger.warning("skip expired at job: %s" % line)
    return atjobs_entries


def parse_crontab(configuration, client_id, path):
    """Parse client_id crontab in path and return a list of crontab dictionary
    entries.
    """
    _logger = configuration.logger
    crontab_lines = read_file_lines(path, _logger)
    if crontab_lines is None:
        _logger.error("Failed to read crontab in %s" % path)
        return []
    return parse_crontab_contents(configuration, client_id, crontab_lines)


def parse_atjobs(configuration, client_id, path):
    """Parse client_id atjobs in path and return a list of atjobs dictionary
    entries.
    """
    _logger = configuration.logger
    atjobs_lines = read_file_lines(path, _logger)
    if atjobs_lines is None:
        _logger.error("Failed to read atjobs in %s" % path)
        return []
    return parse_atjobs_contents(configuration, client_id, atjobs_lines)


def parse_and_save_crontab(crontab, client_id, configuration):
    """Validate and write the crontab for client_id"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    crontab_path = os.path.join(configuration.user_settings, client_dir,
                                crontab_name)
    status, msg = True, ''
    crontab_entries = parse_crontab_contents(configuration, client_id,
                                             crontab.splitlines())
    # TODO: filter out broken lines before write?
    if write_file(crontab, crontab_path, _logger):
        msg = "Found and saved %d valid crontab entries" % len(crontab_entries)
    else:
        status = False
        msg = 'ERROR: writing crontab file'
    return (status, msg)


def parse_and_save_atjobs(atjobs, client_id, configuration):
    """Validate and write the atjobs for client_id"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    atjobs_path = os.path.join(configuration.user_settings, client_dir,
                               atjobs_name)
    status, msg = True, ''
    atjobs_entries = parse_atjobs_contents(configuration, client_id,
                                           atjobs.splitlines())
    # TODO: filter out broken lines before write?
    if write_file(atjobs, atjobs_path, _logger):
        msg = "Found and saved %d valid atjobs entries" % len(atjobs_entries)
    else:
        status = False
        msg = 'ERROR: writing atjobs file'
    return (status, msg)


def cron_match(configuration, cron_time, entry):
    """Check if cron_time matches the time specs in entry"""
    _logger = configuration.logger
    time_vals = {'minute': cron_time.minute, 'hour': cron_time.hour,
                 'month': cron_time.month, 'dayofmonth': cron_time.day,
                 'dayofweek': cron_time.weekday()}
    # TODO: extend to support e.g. */5 and the likes?
    for (name, val) in time_vals.items():
        # Strip any leading zeros before integer match
        if not fnmatch.fnmatch("%s" % val, entry[name].lstrip('0')):
            _logger.debug("cron_match failed on %s: %s vs %s" %
                          (name, val, entry[name]))
            return False
    return True


def at_remain(configuration, at_time, entry):
    """Return the number of minutes remaining before entry should run"""
    _logger = configuration.logger
    return int((entry['time_stamp'] - at_time).total_seconds() // 60)


def is_fake_event(event):
    """Check if event came from our trigger-X rules rather than a real file
    system change.
    """

    return getattr(event, TRIGGER_EVENT, False)


def extract_time_in_secs(configuration, rule, field):
    """Get time in seconds for provided free form period field. The value is a
    integer or float string with optional unit letter appended. If no unit is
    given the default period is used and if all empty the default time is used.
    """
    logger = configuration.logger
    pid = multiprocessing.current_process().pid

    limit_str = rule.get(field, '')
    if not limit_str:
        limit_str = "%s" % DEFAULT_TIME

    # NOTE: format is 3(s) or 52m
    # extract unit suffix letter and fall back to a raw value with default unit

    unit_key = DEFAULT_PERIOD
    if not limit_str[-1:].isdigit():
        val_str = limit_str[:-1]
        if limit_str[-1] in UNIT_PERIODS:
            unit_key = limit_str[-1]
        else:
            logger.warning("invalid time value %s ... fall back to defaults" %
                           limit_str)
            (unit_key, val_str) = (DEFAULT_PERIOD, DEFAULT_TIME)
    else:
        val_str = limit_str
    try:
        secs = float(val_str) * UNIT_PERIODS[unit_key]
    except Exception as exc:
        logger.error('(%s): failed to parse time %s (%s)!' % (pid, limit_str,
                                                              exc))
        secs = 0.0
    secs = max(secs, 0.0)
    return secs


def extract_hit_limit(configuration, rule, field):
    """Get rule rate limit as (max_hits, period_length)-tuple for provided
    rate limit field where the limit kicks in when more than max_hits happened
    within the last period_length seconds.
    """
    logger = configuration.logger
    limit_str = rule.get(field, '')

    # NOTE: format is 3(/m) or 52/h
    # split string on slash and fall back to no limit and default unit

    parts = (limit_str.split('/', 1) + [DEFAULT_PERIOD])[:2]
    (number, unit) = parts
    if not number.isdigit():
        number = '-1'
    if unit not in UNIT_PERIODS:
        unit = DEFAULT_PERIOD
    return (int(number), UNIT_PERIODS[unit])


def update_rule_hits(configuration,
                     rule,
                     path,
                     change,
                     ref,
                     time_stamp,
                     ):
    """Update rule hits history with event and remove expired entries. Makes
    sure to neither expire events needed for rate limit nor settle time
    checking.
    """
    logger = configuration.logger
    pid = multiprocessing.current_process().pid
    (_, hit_period) = extract_hit_limit(configuration, rule, RATE_LIMIT_FIELD)
    settle_period = extract_time_in_secs(configuration, rule,
                                         SETTLE_TIME_FIELD)

    # logger.debug('(%s) update rule hits at %s for %s and %s %s %s' % (
    #    pid,
    #    time_stamp,
    #    rule,
    #    path,
    #    change,
    #    ref,
    #    ))

    _hits_lock.acquire()
    rule_history = rule_hits.get(rule['rule_id'], [])
    rule_history.append((path, change, ref, time_stamp))
    max_period = max(hit_period, settle_period)
    period_history = [i for i in rule_history if time_stamp - i[3]
                      <= max_period]
    rule_hits[rule['rule_id']] = period_history
    _hits_lock.release()

    # logger.debug('(%s) updated rule hits for %s to %s' % (pid,
    #             rule['rule_id'], period_history))


def get_rule_hits(configuration, rule, limit_field):
    """find rule hit details"""
    logger = configuration.logger
    pid = multiprocessing.current_process().pid

    if limit_field == RATE_LIMIT_FIELD:
        (hit_count, hit_period) = extract_hit_limit(configuration, rule,
                                                    limit_field)
    elif limit_field == SETTLE_TIME_FIELD:
        (hit_count, hit_period) = (1, extract_time_in_secs(configuration, rule,
                                                           limit_field))
    else:
        logger.error('(%s) get_rule_hits invalid limit_field %s' %
                     (pid, limit_field))
        raise ValueError("got unexpected limit_field %r" % limit_field)

    _hits_lock.acquire()
    rule_history = rule_hits.get(rule['rule_id'], [])
    res = (rule_history, hit_count, hit_period)
    _hits_lock.release()

    # logger.debug('(%s) get_rule_hits found %s' % (pid, res))

    return res


def get_path_hits(configuration, rule, path, limit_field):
    """find path hit details"""

    (rule_history, hit_count, hit_period) = get_rule_hits(configuration, rule,
                                                          limit_field)
    path_history = [i for i in rule_history if i[0] == path]
    return (path_history, hit_count, hit_period)


def above_path_limit(configuration,
                     rule,
                     path,
                     limit_field,
                     time_stamp,
                     ):
    """Check path trigger history against limit field and return boolean
    indicating if the rate limit or settle time should kick in.
    """
    logger = configuration.logger
    pid = multiprocessing.current_process().pid

    (path_history, hit_count, hit_period) = get_path_hits(configuration, rule,
                                                          path, limit_field)
    if hit_count <= 0 or hit_period <= 0:

        # logger.debug('(%s) no %s limit set' % (pid, limit_field))

        return False
    period_history = [i for i in path_history if time_stamp - i[3]
                      <= hit_period]

    # logger.debug('(%s) above path %s test found %s vs %d' % (pid,
    #             limit_field, period_history, hit_count))

    if len(period_history) >= hit_count:
        return True
    return False


def show_path_hits(configuration, rule, path, limit_field):
    """Return path hit details for printing"""
    logger = configuration.logger
    pid = multiprocessing.current_process().pid

    msg = ''
    (path_history, hit_count, hit_period) = get_path_hits(configuration, rule,
                                                          path, limit_field)
    msg += \
        '(%s) found %d entries in trigger history and limit is %d per %s s' \
        % (pid, len(path_history), hit_count, hit_period)
    return msg


def wait_settled(configuration,
                 rule,
                 path,
                 change,
                 settle_secs,
                 time_stamp,
                 ):
    """Lookup recent change events on path and check if settle_secs passed
    since last one. Returns the number of seconds needed without further
    events for changes to be considered settled.
    """
    logger = configuration.logger
    pid = multiprocessing.current_process().pid

    limit_field = SETTLE_TIME_FIELD
    (path_history, _, hit_period) = get_path_hits(configuration, rule, path,
                                                  limit_field)
    period_history = [i for i in path_history if time_stamp - i[3]
                      <= hit_period]

    # logger.debug('(%s) wait_settled: path %s, change %s, settle_secs %s'
    #              % (pid, path, change, settle_secs))

    if not period_history:
        remain = 0.0
    else:

        # NOTE: the time_stamp - i[3] values are non-negative here
        # since hit_period >= 0.
        # Thus we can just take the smallest and subtract from settle_secs
        # to always wait the remaining part of settle_secs.

        remain = settle_secs - min([time_stamp - i[3] for i in
                                    period_history])

    # logger.debug('(%s) wait_settled: remain %.1f , period_history %s'
    #             % (pid, remain, period_history))

    return remain


def recently_modified(configuration, path, time_stamp, slack=2.0):
    """Check if path was actually recently modified and not just accessed.
    If atime and mtime are the same or if mtime is within slack from time_stamp
    we accept it as recently changed.
    """
    logger = configuration.logger
    pid = multiprocessing.current_process().pid

    try:
        stat_res = os.stat(path)
        result = stat_res.st_mtime == stat_res.st_atime \
            or stat_res.st_mtime > time_stamp - slack
    except OSError as exc:

        # If we get an OSError, *path* is most likely deleted

        result = True

        # logger.debug('(%s) OSError: %s' % (pid, exc))

    return result


def __cron_log(configuration, client_id, msg, level="info"):
    """Wrapper to send a single msg to user cron log file"""

    client_dir = client_id_dir(client_id)
    log_dir_path = os.path.join(configuration.user_home, client_dir,
                                cron_output_dir)
    log_path = os.path.join(log_dir_path, cron_log_name)
    if not os.path.exists(log_dir_path):
        try:
            os.makedirs(log_dir_path)
        except:
            pass
    cron_logger = logging.getLogger('cron')
    cron_logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=cron_log_size, backupCount=cron_log_cnt - 1)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
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


def __cron_warn(configuration, client_id, msg):
    """Wrapper to send a single warning msg to client_id cron log"""

    __cron_log(configuration, client_id, msg, 'warning')


def __cron_info(configuration, client_id, msg):
    """Wrapper to send a single info msg to client_id cron log"""

    __cron_log(configuration, client_id, msg, 'info')


def __handle_cronjob(configuration, client_id, timestamp, crontab_entry):
    """Actually handle valid crontab entry which is due"""
    logger = configuration.logger
    pid = multiprocessing.current_process().pid
    logger.info('(%s) in handling of %s for %s' % (pid,
                                                   crontab_entry['command'],
                                                   client_id))
    __cron_info(configuration, client_id, 'handle %s for %s' %
                (crontab_entry['command'], client_id))

    if crontab_entry['run_as'] != client_id:
        logger.error('(%s) skipping due to owner mismatch for %s and %s!' %
                     (pid, client_id, crontab_entry))
        return False

    # Expand dynamic time variables in argument once and for all

    expand_map = get_time_expand_map(configuration, timestamp, crontab_entry)
    command_list = crontab_entry['command'][:1]
    for argument in crontab_entry['command'][1:]:
        filled_argument = argument
        for (key, val) in expand_map.items():
            filled_argument = filled_argument.replace(key, val)
        __cron_info(configuration, client_id,
                    'expanded argument %s to %s' %
                    (argument, filled_argument))
        command_list.append(filled_argument)
    try:
        run_cron_command(command_list, client_id, crontab_entry, configuration)
        logger.info('(%s) done running command for %s: %s' %
                    (pid, client_id, ' '.join(command_list)))
        __cron_info(configuration, client_id,
                    'ran command: %s' % ' '.join(command_list))
    except Exception as exc:
        command_str = ' '.join(command_list)
        logger.error('(%s) failed to run command for %s: %s (%s)' %
                     (pid, client_id, command_str, exc))
        __cron_err(configuration, client_id,
                   'failed to run command: %s (%s)' % (command_str, exc))


def run_cron_handler(configuration, client_id, timestamp, crontab_entry):
    """Run crontab entry for client_id in a properly isolated process to avoid
    concurrent worker interference.
    """
    logger = configuration.logger
    pid = multiprocessing.current_process().pid

    # TODO: Replace try/catch with an event queue or process pool setup

    waiting_for_worker_resources = True
    while waiting_for_worker_resources:
        try:
            worker = \
                multiprocessing.Process(target=__handle_cronjob,
                                        args=(configuration, client_id,
                                              timestamp, crontab_entry))
            worker.daemon = True
            worker.start()
            waiting_for_worker_resources = False
        except multiprocessing.ProcessError as exc:

            # logger.debug('(%s) Waiting for worker resources to handle crontab: %s'
            #              % (pid, crontab_entry))

            time.sleep(1)


def run_cron_command(
    command_list,
    target_path,
    crontab_entry,
    configuration,
):
    """Run backend command built from command_list on behalf of user from
    crontab_entry and with args mapped to the backend variables.
    """
    logger = configuration.logger
    pid = multiprocessing.current_process().pid
    client_id = crontab_entry['run_as']
    command_str = ' '.join(command_list)
    logger.info('(%s) run command for %s: %s' % (pid, target_path,
                                                 command_list))

    # logger.debug('(%s) run %s on behalf of %s' % (pid, command_str,
    #             client_id))

    (function, user_arguments_dict) = parse_command_args(configuration,
                                                         command_list)

    form_method = 'post'
    target_op = "%s" % function
    csrf_limit = get_csrf_limit(configuration)
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    user_arguments_dict[csrf_field] = [csrf_token]

    # logger.debug('(%s) import main from %s' % (pid, function))

    main = None
    try:
        main = importlib.import_module('mig.shared.functionality.%s' %
                                       function).main

        # logger.debug('(%s) run %s on %s for %s' % \
        #              (pid, function, user_arguments_dict, client_id))

        # Fake HTTP POST manually setting fields required for CSRF check

        os.environ['HTTP_USER_AGENT'] = 'grid cron daemon'
        os.environ['BACKEND_NAME'] = '%s' % function
        os.environ['PATH_INFO'] = '%s.py' % function
        os.environ['REQUEST_METHOD'] = form_method.upper()
        # We may need a REMOTE_ADDR for gdplog call even if not really enabled
        os.environ['REMOTE_ADDR'] = '127.0.0.1'
        (output_objects, (ret_code, ret_msg)) = main(client_id,
                                                     user_arguments_dict)
    except Exception as exc:
        logger.error('(%s) failed to run %s main on %s: %s' %
                     (pid, function, user_arguments_dict, exc))
        import traceback
        logger.info('traceback:\n%s' % traceback.format_exc())
        raise exc
    logger.info('(%s) done running command for %s: %s' %
                (pid, target_path, command_str))

    # logger.debug('(%s) raw output is: %s' % (pid, output_objects))

    try:
        txt_out = txt_format(configuration, ret_code, ret_msg,
                             output_objects)
    except Exception as exc:
        txt_out = 'internal command output text formatting failed'
        logger.error('(%s) text formating failed: %s\nraw output is: %s %s %s'
                     % (pid, exc, ret_code, ret_msg, output_objects))
    if ret_code != 0:
        logger.warning('(%s) command finished but with error code %d :\n%s'
                       % (pid, ret_code, output_objects))
        raise Exception('command error: %s' % txt_out)

    # logger.debug('(%s) result was %s : %s:\n%s' % (pid, ret_code,
    #                                               ret_msg, txt_out))


def run_events_command(
    command_list,
    target_path,
    rule,
    configuration,
):
    """Run backend command built from command_list on behalf of user from
    rule and with args mapped to the backend variables.
    """
    logger = configuration.logger
    pid = multiprocessing.current_process().pid
    client_id = rule['run_as']
    command_str = ' '.join(command_list)
    logger.info('(%s) run command for %s: %s' % (pid, target_path,
                                                 command_list))

    # logger.debug('(%s) run %s on behalf of %s' % (pid, command_str,
    #             client_id))

    (function, user_arguments_dict) = parse_command_args(configuration,
                                                         command_list)

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
        exec('from mig.shared.functionality.%s import main' % function)
        exec('from mig.shared.output import txt_format')

        # logger.debug('(%s) run %s on %s for %s' % \
        #              (pid, function, user_arguments_dict, client_id))

        # Fake HTTP POST manually setting fields required for CSRF check

        os.environ['HTTP_USER_AGENT'] = 'grid events daemon'
        os.environ['PATH_INFO'] = '%s.py' % function
        os.environ['REQUEST_METHOD'] = form_method.upper()
        # We may need a REMOTE_ADDR for gdplog call even if not really enabled
        os.environ['REMOTE_ADDR'] = '127.0.0.1'
        (output_objects, (ret_code, ret_msg)) = main(client_id,
                                                     user_arguments_dict)
    except Exception as exc:
        logger.error('(%s) failed to run %s main on %s: %s' %
                     (pid, function, user_arguments_dict, exc))
        import traceback
        logger.info('traceback:\n%s' % traceback.format_exc())
        raise exc
    logger.info('(%s) done running command for %s: %s' %
                (pid, target_path, command_str))

    # logger.debug('(%s) raw output is: %s' % (pid, output_objects))

    try:
        txt_out = txt_format(configuration, ret_code, ret_msg,
                             output_objects)
    except Exception as exc:
        txt_out = 'internal command output text formatting failed'
        logger.error('(%s) text formating failed: %s\nraw output is: %s %s %s'
                     % (pid, exc, ret_code, ret_msg, output_objects))
    if ret_code != 0:
        logger.warning('(%s) command finished but with error code %d :\n%s'
                       % (pid, ret_code, output_objects))
        raise Exception('command error: %s' % txt_out)

    # logger.debug('(%s) result was %s : %s:\n%s' % (pid, ret_code,
    #                                               ret_msg, txt_out))


if __name__ == '__main__':
    from mig.shared.conf import get_configuration_object
    conf = get_configuration_object()
    client_id = '/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk'
    now = datetime.datetime.now()
    now = now.replace(second=0, microsecond=0)
    trigger_rule = {
        'templates': [], 'run_as': client_id, 'rate_limit': '',
        'vgrid_name': 'eScience', 'rule_id': 'test-dummy', 'match_dirs': False,
        'match_files': True, 'arguments': ['+TRIGGERPATH+'], 'settle_time': '',
        'path': '*.txt*', 'changes': ['modified'], 'action': 'trigger-created',
        'match_recursive': True}
    trigger_samples = [('abc.txt', 'modified'), ('subdir/def.txt', 'modified')]
    print("Test trigger event map:")
    for (path, change) in trigger_samples:
        print("Expanded path vars for %s %s:" % (path, change))
        expanded = get_path_expand_map(conf, path, trigger_rule, change)
        for (key, val) in expanded.items():
            print("    %s: %s" % (key, val))

    crontab_lines = [
        '* * * * * pack cront-test.txt cron-test-+SCHEDYEAR+-+SCHEDMONTH+-+SCHEDDAY+.zip']
    crontab_rules = parse_crontab_contents(conf, client_id, crontab_lines)
    cron_times = [now, datetime.datetime(now.year + 1, 12, 24, 12, 42),
                  datetime.datetime(now.year + 2, 1, 2, 9, 2)]
    print("Test cron event map:")
    for rule in crontab_rules:
        for timestamp in cron_times:
            match = cron_match(conf, timestamp, rule)
            print("Cron match against %s in rule: %s" % (timestamp, match))
            print("Expanded time %s vars:" % timestamp)
            expanded = get_time_expand_map(conf, timestamp, rule)
            for (key, val) in expanded.items():
                print("    %s: %s" % (key, val))
    now_stamp = now.isoformat(" ")
    atjobs_lines = ['%s touch at-test-+SCHEDYEAR+-+SCHEDMONTH+-+SCHEDDAY+.zip'
                    % now_stamp]
    print("parse at job lines: %s" % atjobs_lines)
    atjobs_rules = parse_atjobs_contents(conf, client_id, atjobs_lines)
    print("found at job rules: %s" % atjobs_rules)
    print("Test at jobs:")
    for rule in atjobs_rules:
        for timestamp in cron_times:
            remain = at_remain(conf, timestamp, rule)
            print("At %s job is %dm in the future for rule" % (
                timestamp, remain))
