#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# grid_events - event handler to monitor files and trigger actions
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Event handler to monitor vgrid files for creation, modification and removal
and trigger any associated actions based on rule database.

Requires watchdog module (https://pypi.python.org/pypi/watchdog).
"""

import fnmatch
import glob
import logging
import logging.handlers
import os
import re
import sys
import tempfile
import time
import threading
from shared.fileio import makedirs_rec, pickle

try:
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler, \
        FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, \
        DirModifiedEvent, DirCreatedEvent, DirDeletedEvent
except ImportError:
    print 'ERROR: the python watchdog module is required for this daemon'
    sys.exit(1)

from shared.conf import get_configuration_object
from shared.defaults import valid_trigger_changes, workflows_log_name, \
    workflows_log_size, workflows_log_cnt
from shared.job import fill_mrsl_template, new_job
from shared.logger import daemon_logger
from shared.serial import load
from shared.vgrid import vgrid_is_owner_or_member

# Global trigger rule dictionary with rules for all VGrids

all_rules = {}
rule_hits = {}
(_rate_limit_field, _settle_time_field) = ('rate_limit', 'settle_time')
_default_period = 'm'
_default_time = '0'
_unit_periods = {
    's': 1,
    'm': 60,
    'h': 60 * 60,
    'd': 24 * 60 * 60,
    'w': 7 * 24 * 60 * 60,
    }
_hits_lock = threading.Lock()
(configuration, logger) = (None, None)


def get_expand_map(trigger_path, rule, state_change):
    """Generate a dictionary with the supported variables to be expanded and
    the actual expanded values based on trigger_path and rule dictionary.
    """

    trigger_filename = os.path.basename(trigger_path)
    trigger_dirname = os.path.dirname(trigger_path)
    (prefix, extension) = os.path.splitext(trigger_filename)
    expand_map = {
        '+TRIGGERPATH+': trigger_path,
        '+TRIGGERDIRNAME+': trigger_dirname,
        '+TRIGGERFILENAME+': trigger_filename,
        '+TRIGGERPREFIX+': prefix,
        '+TRIGGEREXTENSION+': extension,
        '+TRIGGERCHANGE+': state_change,
        '+TRIGGERVGRIDNAME+': rule['vgrid_name'],
        '+TRIGGERRUNAS+': rule['run_as'],
        }

    # TODO: provide exact expanded wildcards?

    return expand_map


def make_fake_event(path, state):
    """Create a fake state change event for path. Looks up path to see if the
    change is a directory or file.
    """

    file_map = {'modified': FileModifiedEvent,
                'created': FileCreatedEvent,
                'deleted': FileDeletedEvent}
    dir_map = {'modified': DirModifiedEvent,
               'created': DirCreatedEvent, 'deleted': DirDeletedEvent}
    if os.path.isdir(path):
        return dir_map[state](path)
    else:
        return file_map[state](path)


def extract_time_in_secs(rule, field):
    """Get time in seconds for provided free form period field. The value is a
    integer or float string with optional unit letter appended. If no unit is
    given the default period is used and if all empty the default time is used.
    """

    limit_str = rule.get(field, '')
    if not limit_str:
        limit_str = str(_default_time)

    # NOTE: format is 3(s) or 52m
    # extract unit suffix letter and fall back to a raw value with default unit

    unit_key = _default_period
    if not limit_str[-1:].isdigit():
        val_str = limit_str[:-1]
        if limit_str[-1] in _unit_periods.keys():
            unit_key = limit_str[-1]
        else:

            # print "ERROR: invalid time value %s ... fall back to defaults" % \
            #      limit_str

            (unit_key, val_str) = (_default_period, _default_time)
    else:
        val_str = limit_str
    try:
        secs = float(val_str) * _unit_periods[unit_key]
    except Exception, exc:
        print 'ERROR: failed to parse time %s (%s)!' % (limit_str, exc)
        secs = 0.0
    secs = max(secs, 0.0)
    return secs


def extract_hit_limit(rule, field):
    """Get rule rate limit as (max_hits, period_length)-tuple for provided
    rate limit field where the limit kicks in when more than max_hits happened
    within the last period_length seconds.
    """

    limit_str = rule.get(field, '')

    # NOTE: format is 3(/m) or 52/h
    # split string on slash and fall back to no limit and default unit

    parts = (limit_str.split('/', 1) + [_default_period])[:2]
    (number, unit) = parts
    if not number.isdigit():
        number = '-1'
    if unit not in _unit_periods.keys():
        unit = _default_period
    return (int(number), _unit_periods[unit])


def update_rule_hits(
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

    (_, hit_period) = extract_hit_limit(rule, _rate_limit_field)
    settle_period = extract_time_in_secs(rule, _settle_time_field)
    logger.debug('update rule hits at %s for %s and %s %s %s'
                 % (time_stamp, rule, path, change, ref))
    _hits_lock.acquire()
    rule_history = rule_hits.get(rule['rule_id'], [])
    rule_history.append((path, change, ref, time_stamp))
    max_period = max(hit_period, settle_period)
    period_history = [i for i in rule_history if time_stamp - i[3]
                      <= max_period]
    rule_hits[rule['rule_id']] = period_history
    _hits_lock.release()
    logger.debug('updated rule hits for %s to %s' % (rule['rule_id'],
                 period_history))


def get_rule_hits(rule, limit_field):
    """find rule hit details"""

    if limit_field == _rate_limit_field:
        (hit_count, hit_period) = extract_hit_limit(rule, limit_field)
    elif limit_field == _settle_time_field:
        (hit_count, hit_period) = (1, extract_time_in_secs(rule,
                                   limit_field))
    _hits_lock.acquire()
    rule_history = rule_hits.get(rule['rule_id'], [])
    res = (rule_history, hit_count, hit_period)
    _hits_lock.release()
    logger.debug('get_rule_hits found %s' % (res, ))
    return res


def get_path_hits(rule, path, limit_field):
    """find path hit details"""

    (rule_history, hit_count, hit_period) = get_rule_hits(rule,
            limit_field)
    path_history = [i for i in rule_history if i[0] == path]
    return (path_history, hit_count, hit_period)


def above_path_limit(
    rule,
    path,
    limit_field,
    time_stamp,
    ):
    """Check path trigger history against limit field and return boolean
    indicating if the rate limit or settle time should kick in.
    """

    (path_history, hit_count, hit_period) = get_path_hits(rule, path,
            limit_field)
    if hit_count <= 0 or hit_period <= 0:
        logger.debug('no %s limit set' % limit_field)
        return False
    period_history = [i for i in path_history if time_stamp - i[3]
                      <= hit_period]
    logger.debug('above path %s test found %s vs %d' % (limit_field,
                 period_history, hit_count))
    if len(period_history) >= hit_count:
        return True
    return False


def show_path_hits(rule, path, limit_field):
    """Return path hit details for printing"""

    msg = ''
    (path_history, hit_count, hit_period) = get_path_hits(rule, path,
            limit_field)
    msg += \
        'found %d entries in trigger history and limit is %d per %s s' \
        % (len(path_history), hit_count, hit_period)
    return msg


def wait_settled(
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

    limit_field = _settle_time_field
    (path_history, _, hit_period) = get_path_hits(rule, path,
            limit_field)
    period_history = [i for i in path_history if time_stamp - i[3]
                      <= hit_period]
    logger.debug('wait_settled: path %s, change %s, settle_secs %s'
                 % (path, change, settle_secs))
    if not period_history:
        remain = 0.0
    else:

        # NOTE: the time_stamp - i[3] values are non-negative here
        # since hit_period >= 0.
        # Thus we can just take the smallest and subtract from settle_secs
        # to always wait the remaining part of settle_secs.

        remain = settle_secs - min([time_stamp - i[3] for i in
                                   period_history])
    logger.debug('wait_settled: remain %.1f , period_history %s'
                 % (remain, period_history))
    return remain


def recently_modified(path, time_stamp, slack=2.0):
    """Check if path was actually recently modified and not just accessed.
    If atime and mtime are the same or if mtime is within slack from time_stamp
    we accept it as recently changed.
    """

    try:
        stat_res = os.stat(path)
        result = stat_res.st_mtime == stat_res.st_atime \
            or stat_res.st_mtime > time_stamp - slack
    except OSError, ex:

        # If we get an OSError, *path* is most likely deleted

        result = True
        logger.debug('OSError: %s' % str(ex))

    return result


def map_args_to_vars(var_list, arg_list):
    """Map command args to backend var names - if more args than vars we
    assume variable length on the first arg:
       zip src1 src2 src3 dst -> src: [src1, src2, src3], dst: [dst]
    """

    args_dict = dict(zip(var_list, [[] for _ in var_list]))
    remain_vars = [i for i in var_list]
    remain_args = [i for i in arg_list]
    while remain_args:
        args_dict[remain_vars[0]].append(remain_args[0])
        del remain_args[0]
        if len(remain_args) < len(remain_vars):
            del remain_vars[0]
    return args_dict


def run_command(
    command_list,
    target_path,
    rule,
    configuration,
    ):
    """Run backend command built from command_list on behalf of user from
    rule and with args mapped to the backend variables.
    """

    # TODO: add all ops with effect here!

    command_map = {
        'pack': ['src', 'dst'],
        'unpack': ['src', 'dst'],
        'zip': ['src', 'dst'],
        'unzip': ['src', 'dst'],
        'tar': ['src', 'dst'],
        'untar': ['src', 'dst'],
        'cp': ['src', 'dst'],
        'mv': ['src', 'dst'],
        'rm': ['path'],
        'rmdir': ['path'],
        'truncate': ['path'],
        'touch': ['path'],
        'mkdir': ['path'],
        'submit': ['path'],
        'canceljob': ['job_id'],
        'resubmit': ['job_id'],
        'jobaction': ['job_id', 'action'],
        'liveio': ['action', 'src', 'dst', 'job_id'],
        'mqueue': ['queue', 'action', 'msg_id', 'msg'],
        }
    logger.info('run command for %s: %s' % (target_path, command_list))
    if not command_list or not command_list[0] in command_map:
        raise ValueError('unsupported command: %s' % command_list[0])
    function = command_list[0]
    args_form = command_map[function]
    client_id = rule['run_as']
    command_str = ' '.join(command_list)
    logger.debug('run %s on behalf of %s' % (command_str, client_id))
    user_arguments_dict = map_args_to_vars(args_form, command_list[1:])
    logger.debug('import main from %s' % function)
    main = id
    txt_format = id
    try:
        exec 'from shared.functionality.%s import main' % function
        exec 'from shared.output import txt_format'
        logger.debug('run %s on %s and %s' % (function, client_id,
                     user_arguments_dict))

        # Fake HTTP POST

        os.environ['REQUEST_METHOD'] = 'POST'
        (output_objects, (ret_code, ret_msg)) = main(client_id,
                user_arguments_dict)
    except Exception, exc:
        logger.error('failed to run %s on %s: %s' % (function,
                     user_arguments_dict, exc))
        raise exc
    logger.info('done running command for %s: %s' % (target_path,
                command_str))
    logger.debug('raw output is: %s' % output_objects)
    try:
        txt_out = txt_format(configuration, ret_code, ret_msg,
                             output_objects)
    except Exception, exc:
        txt_out = 'internal command output text formatting failed'
        logger.error('text formating failed: %s\nraw output is: %s %s %s'
                      % (exc, ret_code, ret_msg, output_objects))
    if ret_code != 0:
        raise Exception('command error: %s' % txt_out)
    logger.info('result was %s : %s:\n%s' % (ret_code, ret_msg,
                txt_out))


class MiGRuleEventHandler(PatternMatchingEventHandler):

    """Rule pattern-matching event handler to take care of VGrid rule changes
    and update the global rule database.
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

    def update_rules(self, event):
        """Handle all rule updates"""

        state = event.event_type
        src_path = event.src_path
        if event.is_directory:
            logger.debug('skip rule update for directory: %s'
                         % src_path)
        logger.debug('%s rule file: %s' % (state, src_path))
        rel_path = \
            src_path.replace(os.path.join(configuration.vgrid_home, ''
                             ), '')
        vgrid_name = rel_path.replace(os.sep
                + configuration.vgrid_triggers, '')
        vgrid_prefix = os.path.join(configuration.vgrid_files_home,
                                    vgrid_name, '')
        logger.info('refresh %s rules from %s' % (vgrid_name, src_path))
        try:
            new_rules = load(src_path)
        except Exception, exc:
            new_rules = []
            if state != 'deleted':
                logger.error('failed to load event handler rules from %s (%s)'
                              % (src_path, exc))
        logger.info("loaded new rules from '%s':\n%s" % (src_path,
                    new_rules))

        # Remove all old rules for this vgrid and
        # leave rules for parent and sub-vgrids

        for target_path in all_rules.keys():
            all_rules[target_path] = [i for i in all_rules[target_path]
                    if i['vgrid_name'] != vgrid_name]
            remain_rules = [i for i in all_rules[target_path]
                            if i['vgrid_name'] != vgrid_name]
            if remain_rules:
                all_rules[target_path] = remain_rules
                logger.debug('remain_rules for: %s \n%s'
                             % (target_path, remain_rules))
            else:
                logger.debug('removing rules for: %s ' % target_path)
                del all_rules[target_path]
        for entry in new_rules:
            rule_id = entry['rule_id']
            path = entry['path']
            logger.info('updating rule: %s, path: %s, entry:\n%s'
                        % (rule_id, path, entry))
            abs_path = os.path.join(vgrid_prefix, path)
            all_rules[abs_path] = all_rules.get(abs_path, []) + [entry]
        logger.info('all rules:\n%s' % all_rules)

    def on_modified(self, event):
        """Handle modified rule file"""

        self.update_rules(event)

    def on_created(self, event):
        """Handle new rule file"""

        self.update_rules(event)

    def on_deleted(self, event):
        """Handle deleted rule file"""

        self.update_rules(event)


class MiGFileEventHandler(PatternMatchingEventHandler):

    """File pattern-matching event handler to take care of VGrid file changes
    and the corresponding action triggers.
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

    def __workflow_log(
        self,
        configuration,
        vgrid_name,
        msg,
        level='info',
        ):
        """Wrapper to send a single msg to vgrid workflows page log file"""

        log_name = '%s.%s' % (configuration.vgrid_triggers,
                              workflows_log_name)
        log_path = os.path.join(configuration.vgrid_home, vgrid_name,
                                log_name)
        workflows_logger = logging.getLogger('workflows')
        workflows_logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(log_path,
                maxBytes=workflows_log_size,
                backupCount=workflows_log_cnt - 1)
        formatter = \
            logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        workflows_logger.addHandler(handler)
        if level == 'error':
            workflows_logger.error(msg)
        elif level == 'warning':
            workflows_logger.warning(msg)
        else:
            workflows_logger.info(msg)
        handler.flush()
        handler.close()
        workflows_logger.removeHandler(handler)

    def __workflow_err(
        self,
        configuration,
        vgrid_name,
        msg,
        ):
        """Wrapper to send a single error msg to vgrid workflows page log"""

        self.__workflow_log(configuration, vgrid_name, msg, 'error')

    def __workflow_warn(
        self,
        configuration,
        vgrid_name,
        msg,
        ):
        """Wrapper to send a single warning msg to vgrid workflows page log"""

        self.__workflow_log(configuration, vgrid_name, msg, 'warning')

    def __workflow_info(
        self,
        configuration,
        vgrid_name,
        msg,
        ):
        """Wrapper to send a single error msg to vgrid workflows page log"""

        self.__workflow_log(configuration, vgrid_name, msg, 'info')

    def __add_trigger_job_ent(
        self,
        configuration,
        event,
        rule,
        jobid,
        ):
        result = True

        vgrid_name = rule['vgrid_name']
        trigger_job_dir = os.path.join(configuration.vgrid_home,
                os.path.join(vgrid_name, '.%s.jobs'
                % configuration.vgrid_triggers))
        trigger_job_filepath = os.path.join(trigger_job_dir, jobid)

        if makedirs_rec(trigger_job_dir, configuration):
            trigger_job_dict = {
                'jobid': jobid,
                'owner': rule['run_as'],
                'rule': rule,
                'event': {},
                }
            src_path = ''
            if hasattr(event, 'src_path'):
                src_path = event.src_path
            dest_path = ''
            if hasattr(event, 'dest_path'):
                dest_path = event.dest_path
            trigger_job_dict['event']['src_path'] = src_path
            trigger_job_dict['event']['dest_path'] = dest_path
            trigger_job_dict['event']['time_stamp'] = event.time_stamp
            trigger_job_dict['event']['event_type'] = event.event_type
            trigger_job_dict['event']['is_directory'] = \
                event.is_directory
            logger.debug('trigger_job_dict: %s' % trigger_job_dict)
            if not pickle(trigger_job_dict, trigger_job_filepath,
                          logger):
                result = False
        else:
            logger.error('Failed to create trigger job dir: %s'
                         % trigger_job_dir)
            result = False

        return result

    def __handle_trigger(
        self,
        event,
        target_path,
        rule,
        ):
        """Actually handle valid trigger for a specific event and the
        corresponding target_path pattern and trigger rule.
        """

        state = event.event_type
        src_path = event.src_path
        time_stamp = event.time_stamp
        _chain = getattr(event, '_chain', [(src_path, state)])
        base_dir = configuration.vgrid_files_home
        rel_src = src_path.replace(base_dir, '').lstrip(os.sep)
        vgrid_prefix = os.path.join(base_dir, rule['vgrid_name'])
        logger.info('in handling of %s for %s %s' % (rule['action'],
                    state, rel_src))
        above_limit = False

        # Run settle time check first to only trigger rate limit if settled

        for (name, field) in [('settle time', _settle_time_field),
                              ('rate limit', _rate_limit_field)]:
            if above_path_limit(rule, src_path, field, time_stamp):
                above_limit = True
                logger.warning('skip %s due to %s: %s' % (src_path,
                               name, show_path_hits(rule, src_path,
                               field)))
                self.__workflow_warn(configuration, rule['vgrid_name'],
                        'skip %s trigger due to %s: %s' % (rel_src,
                        name, show_path_hits(rule, src_path, field)))
                break

        # TODO: consider if we should skip modified when just created

        # We receive modified events even when only atime changed - ignore them

        if state == 'modified' and not recently_modified(src_path,
                time_stamp):
            logger.info('skip %s which only changed atime' % src_path)
            self.__workflow_info(configuration, rule['vgrid_name'],
                                 'skip %s modified access time only event'
                                  % rel_src)
            return

        # Always update here to get trigger hits even for limited events

        update_rule_hits(rule, src_path, state, '', time_stamp)
        if above_limit:
            return
        logger.info('proceed with handling of %s for %s %s'
                    % (rule['action'], state, rel_src))
        self.__workflow_info(configuration, rule['vgrid_name'],
                             'handle %s for %s %s' % (rule['action'],
                             state, rel_src))
        settle_secs = extract_time_in_secs(rule, _settle_time_field)
        if settle_secs > 0.0:
            wait_secs = settle_secs
        else:
            wait_secs = 0.0
            logger.debug('no settle time for %s (%s)' % (target_path,
                         rule))
        while wait_secs > 0.0:
            logger.info('wait %.1fs for %s file events to settle down'
                        % (wait_secs, src_path))
            self.__workflow_info(configuration, rule['vgrid_name'],
                                 'wait %.1fs for events on %s to settle'
                                  % (wait_secs, rel_src))
            time.sleep(wait_secs)
            logger.debug('slept %.1fs for %s file events to settle down'
                          % (wait_secs, src_path))
            time_stamp += wait_secs
            wait_secs = wait_settled(rule, src_path, state,
                    settle_secs, time_stamp)

        # TODO: perhaps we should discriminate on files and dirs here?

        if rule['action'] in ['trigger-%s' % i for i in
                              valid_trigger_changes]:
            change = rule['action'].replace('trigger-', '')

            # Expand dynamic variables in argument once and for all

            expand_map = get_expand_map(rel_src, rule, state)
            for argument in rule['arguments']:
                filled_argument = argument
                for (key, val) in expand_map.items():
                    filled_argument = filled_argument.replace(key, val)
                self.__workflow_info(configuration, rule['vgrid_name'],
                        'expanded argument %s to %s' % (argument,
                        filled_argument))
                pattern = os.path.join(vgrid_prefix, filled_argument)
                for path in glob.glob(pattern):
                    rel_path = \
                        path.replace(configuration.vgrid_files_home, '')
                    _chain += [(path, change)]

                    # Prevent obvious trigger chain cycles

                    if (path, change) in _chain[:-1]:
                        flat_chain = ['%s : %s' % pair for pair in
                                _chain]
                        chain_str = ' <-> '.join(flat_chain)
                        rel_chain_str = \
                            chain_str.replace(configuration.vgrid_files_home,
                                '')
                        logger.warning('breaking trigger cycle %s'
                                % chain_str)
                        self.__workflow_warn(configuration,
                                rule['vgrid_name'],
                                'breaking trigger cycle %s'
                                % rel_chain_str)
                        continue
                    fake = make_fake_event(path, change)
                    fake._chain = _chain
                    logger.info('trigger %s event on %s' % (change,
                                path))
                    self.__workflow_info(configuration,
                            rule['vgrid_name'], 'trigger %s event on %s'
                             % (change, rel_path))
                    self.handle_event(fake)
        elif rule['action'] == 'submit':
            mrsl_fd = tempfile.NamedTemporaryFile(delete=False)
            mrsl_path = mrsl_fd.name

            # Expand dynamic variables in argument once and for all

            expand_map = get_expand_map(rel_src, rule, state)
            try:
                for job_template in rule['templates']:
                    mrsl_fd.truncate(0)
                    if not fill_mrsl_template(
                        job_template,
                        mrsl_fd,
                        rel_src,
                        state,
                        rule,
                        expand_map,
                        configuration,
                        ):
                        raise Exception('fill template failed')
                    logger.debug('filled template for %s in %s'
                                 % (target_path, mrsl_path))
                    (success, msg, jobid) = new_job(mrsl_path,
                            rule['run_as'], configuration, False,
                            returnjobid=True)

                    if success:
                        self.__add_trigger_job_ent(configuration,
                                event, rule, jobid)

                        logger.info('submitted job for %s: %s'
                                    % (target_path, msg))
                        self.__workflow_info(configuration,
                                rule['vgrid_name'],
                                'submitted job for %s: %s' % (rel_src,
                                msg))
                    else:
                        raise Exception(msg)
            except Exception, exc:
                logger.error('failed to submit job(s) for %s: %s'
                             % (target_path, exc))
                self.__workflow_err(configuration, rule['vgrid_name'],
                                    'failed to submit job for %s: %s'
                                    % (rel_src, exc))
            try:
                os.remove(mrsl_path)
            except Exception, exc:
                logger.warning('clean up after submit failed: %s' % exc)
        elif rule['action'] == 'command':

            # Expand dynamic variables in argument once and for all

            expand_map = get_expand_map(rel_src, rule, state)
            command_str = ''
            command_list = (rule['arguments'])[:1]
            for argument in (rule['arguments'])[1:]:
                filled_argument = argument
                for (key, val) in expand_map.items():
                    filled_argument = filled_argument.replace(key, val)
                self.__workflow_info(configuration, rule['vgrid_name'],
                        'expanded argument %s to %s' % (argument,
                        filled_argument))
                command_list.append(filled_argument)
            try:
                run_command(command_list, target_path, rule,
                            configuration)
                self.__workflow_info(configuration, rule['vgrid_name'],
                        'ran command: %s' % ' '.join(command_list))
            except Exception, exc:
                logger.error('failed to run command for %s: %s (%s)'
                             % (target_path, command_str, exc))
                self.__workflow_err(configuration, rule['vgrid_name'],
                                    'failed to run command for %s: %s (%s)'
                                     % (rel_src, command_str, exc))
        else:
            logger.error('unsupported action: %(action)s' % rule)

    def run_handler(self, event):
        """Trigger any rule actions bound to file state change"""

        state = event.event_type
        src_path = event.src_path
        is_directory = event.is_directory
        logger.info('got %s event for path: %s' % (state, src_path))
        logger.debug('filter %s against %s' % (all_rules.keys(),
                     src_path))

        # Each target_path pattern has one or more rules associated

        for (target_path, rule_list) in all_rules.items():

            # Do not use ordinary fnmatch as it lets '*' match anything
            # including '/' which leads to greedy matching in subdirs

            recursive_regexp = fnmatch.translate(target_path)
            direct_regexp = recursive_regexp.replace('.*', '[^/]*')
            recursive_hit = re.match(recursive_regexp, src_path)
            direct_hit = re.match(direct_regexp, src_path)
            if direct_hit or recursive_hit:
                logger.debug('matched %s for %s and/or %s' % (src_path,
                             direct_regexp, recursive_regexp))
                for rule in rule_list:

                    # user may have been removed from vgrid - log and ignore

                    if not vgrid_is_owner_or_member(rule['vgrid_name'],
                            rule['run_as'], configuration):
                        logger.warning('no such user in vgrid: %(run_as)s'
                                 % rule)
                        continue

                    # Rules may listen for only file or dir events and with
                    # recursive directory search

                    if is_directory and not rule.get('match_dirs',
                            False):
                        logger.debug('skip event %s handling for dir: %s'
                                 % (rule['rule_id'], src_path))
                        continue
                    if not is_directory and not rule.get('match_files',
                            True):
                        logger.debug('skip %s event handling for file: %s'
                                 % (rule['rule_id'], src_path))
                        continue
                    if not direct_hit and not rule.get('match_recursive'
                            , False):
                        logger.debug('skip %s recurse event handling for: %s'
                                 % (rule['rule_id'], src_path))
                        continue
                    if not state in rule['changes']:
                        logger.info('skip %s %s event handling for: %s'
                                    % (rule['rule_id'], state,
                                    src_path))
                        continue

                    logger.info('trigger %s for %s: %s' % (rule['action'
                                ], src_path, rule))
                    self.__handle_trigger(event, target_path, rule)
            else:
                logger.debug('skip %s with no matching rules'
                             % target_path)

    def handle_event(self, event):
        """Handle an event in the background so that it can block without
        stopping further event handling.
        We add a time stamp to have a sort of precise time for when the event
        was received. Still not perfect but better than comparing with 'now'
        values obtained deeply in handling calls.
        """

        event.time_stamp = time.time()
        worker = threading.Thread(target=self.run_handler, args=(event,
                                  ))
        worker.daemon = True
        worker.start()

    def on_modified(self, event):
        """Handle modified files"""

        self.handle_event(event)

    def on_created(self, event):
        """Handle created files"""

        self.handle_event(event)

    def on_deleted(self, event):
        """Handle deleted files"""

        self.handle_event(event)

    def on_moved(self, event):
        """Handle moved files: we translate a move to a created and a deleted
        event since the single event with src and dst does not really fit our
        model all that well.
        """

        for (change, path) in [('created', event.dest_path), ('deleted'
                               , event.src_path)]:
            fake = make_fake_event(path, change)
            self.handle_event(fake)


if __name__ == '__main__':
    print '''This is the MiG event handler daemon which monitors VGrid files
and triggers any configured events when target files are created, modifed or
deleted. VGrid owners can configure rules to trigger such events based on file
changes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
'''

    configuration = get_configuration_object()

    # Use separate logger

    logger = daemon_logger('events', configuration.user_events_log,
                           configuration.loglevel)

    keep_running = True

    print 'Starting Event handler daemon - Ctrl-C to quit'

    logger.info('Starting Event handler daemon')

    logger.info('initializing rule listener')

    # Monitor rule configurations

    rule_monitor = Observer()
    rule_patterns = [os.path.join(configuration.vgrid_home, '*',
                     configuration.vgrid_triggers)]
    rule_handler = MiGRuleEventHandler(patterns=rule_patterns,
            ignore_directories=False, case_sensitive=True)
    rule_monitor.schedule(rule_handler, configuration.vgrid_home,
                          recursive=True)
    rule_monitor.start()

    logger.info('initializing file listener - may take some time')

    # monitor actual files to handle events for

    file_monitor = Observer()
    file_patterns = [os.path.join(configuration.vgrid_files_home, '*')]
    file_handler = MiGFileEventHandler(patterns=file_patterns,
            ignore_directories=False, case_sensitive=True)
    file_monitor.schedule(file_handler, configuration.vgrid_files_home,
                          recursive=True)
    file_monitor.start()

    logger.info('trigger rule refresh')

    # Fake touch event on all rule files to load initial rules

    logger.info('trigger load on all rule files (greedy) matching %s'
                % rule_patterns[0])

    # We manually walk and test to get the greedy "*" directory match behaviour
    # of the PatternMatchingEventHandler

    all_trigger_rules = []
    for (root, _, files) in os.walk(configuration.vgrid_home):
        if configuration.vgrid_triggers in files:
            rule_path = os.path.join(root, configuration.vgrid_triggers)
            all_trigger_rules.append(rule_path)
    for rule_path in all_trigger_rules:
        logger.debug('trigger load on rules in %s' % rule_path)
        rule_handler.dispatch(FileModifiedEvent(rule_path))
    logger.debug('loaded initial rules:\n%s' % all_rules)

    logger.info('ready to handle triggers')

    while keep_running:
        try:

            # Throttle down

            time.sleep(1)
        except KeyboardInterrupt:
            keep_running = False
            rule_monitor.stop()
            file_monitor.stop()
        except Exception, exc:
            print 'Caught unexpected exception: %s' % exc

    rule_monitor.join()
    file_monitor.join()
    print 'Event handler daemon shutting down'
    sys.exit(0)
