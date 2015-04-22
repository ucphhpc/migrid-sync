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

try:
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler, FileMovedEvent, \
         FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
except ImportError:
    print "ERROR: the python watchdog module is required for this daemon"
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
_default_period = 'm'
_unit_periods = {'s': 1, 'm': 60, 'h': 60*60, 'd': 24 * 60 * 60,
                 'w': 7 * 24 * 60 * 60}
_hits_lock = threading.Lock()
configuration, logger = None, None

def get_expand_map(trigger_path, rule, state_change):
    """Generate a dictionary with the supported variables to be expanded and
    the actual expanded values based on trigger_path and rule dictionary.
    """
    trigger_filename = os.path.basename(trigger_path)
    trigger_dirname = os.path.dirname(trigger_path)
    (prefix, extension) = os.path.splitext(trigger_filename)
    expand_map = {'+TRIGGERPATH+': trigger_path,
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

def extract_hit_limit(rule, field):
    """Get rule rate limit as (max_hits, period_length)-tuple for provided
    rate limit field where the limit kicks in when more than max_hits happened
    within the last period_length seconds.
    """
    limit_str = rule.get(field, '')
    # NOTE: format is 3(/m) or 52/h
    # split string on slash and fall back to no limit and default unit
    parts = (limit_str.split("/", 1)+[_default_period])[:2]
    number, unit = parts
    if not number.isdigit():
        number = '-1'
    if unit not in _unit_periods.keys():
        unit = _default_period
    return (int(number), _unit_periods[unit])

def above_rate_limit(rule):
    """Check rule history against rate limit and return boolean indicating if
    the rate limit should kick in.
    """
    now = time.time()
    hit_count, hit_period = extract_hit_limit(rule, 'rate_limit')
    logger.info("check rate limit at %s for %s" % (now, rule))
    if hit_count <= 0:
        logger.info("no rate limit set")
        return False
    _hits_lock.acquire()
    rule_history = rule_hits.get(rule['rule_id'], [])
    period_history = [i for i in rule_history if now - i[-1] <= hit_period]
    _hits_lock.release()
    logger.info("check rate limit found %s vs %d" % \
                (period_history, hit_count))
    if len(period_history) >= hit_count:
        return True
    return False

def update_rate_limit(rule, path, change, ref):
    """Update rule history with event and remove expired entries"""
    now = time.time()
    _, hit_period = extract_hit_limit(rule, 'rate_limit')
    logger.info("update rate limit at %s for %s and %s %s %s" % \
                (now, rule, path, change, ref))
    _hits_lock.acquire()
    rule_history = rule_hits.get(rule['rule_id'], [])
    rule_history.append((path, change, ref, time.time()))
    period_history = [i for i in rule_history if now - i[-1] <= hit_period]
    rule_hits[rule['rule_id']] = period_history
    _hits_lock.release()
    logger.info("update rate limit left with %s" % period_history)

def show_rate_limit(rule):
    """Return rate limit details for printing"""
    msg = ''
    hit_count, hit_period = extract_hit_limit(rule, 'rate_limit')
    _hits_lock.acquire()
    rule_history = rule_hits.get(rule['rule_id'], [])
    msg += 'found %d entries in trigger history and limit is %d per %s s' % \
           (len(rule_history), hit_count, hit_period)
    _hits_lock.release()
    return msg

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

def run_command(command_list, target_path, rule, configuration):
    """Run backend command built from command_list on behalf of user from
    rule and with args mapped to the backend variables.
    """
    # TODO: add all ops with effect here!
    command_map = {
        'pack': ['src', 'dst'], 'unpack': ['src', 'dst'],
        'zip': ['src', 'dst'], 'unzip': ['src', 'dst'],
        'tar': ['src', 'dst'], 'untar': ['src', 'dst'],
        'cp': ['src', 'dst'], 'mv': ['src', 'dst'],
        'rm': ['path'], 'rmdir': ['path'], 'truncate': ['path'],
        'touch': ['path'], 'mkdir': ['path'], 'submit': ['path'],
        'canceljob': ['job_id'], 'resubmit': ['job_id'],
        'jobaction': ['job_id', 'action'], 
        'liveio': ['action', 'src', 'dst', 'job_id'],
        'mqueue': ['queue', 'action', 'msg_id', 'msg'],
        }
    logger.info("run command for %s: %s" % (target_path, command_list))
    if not command_list or not command_list[0] in command_map:
        raise ValueError('unsupported command: %s' % command_list[0])
    function = command_list[0]
    args_form = command_map[function]
    client_id = rule['run_as']
    command_str = ' '.join(command_list)
    logger.info("run %s on behalf of %s" % (command_str, client_id))
    user_arguments_dict = map_args_to_vars(args_form, command_list[1:])
    logger.info("import main from %s" % function)
    main = id
    txt_format = id
    try:
        exec 'from shared.functionality.%s import main' % function
        exec 'from shared.output import txt_format'
        logger.info("run %s on %s and %s" % (function, client_id,
                                             user_arguments_dict))
        # Fake HTTP POST
        os.environ['REQUEST_METHOD'] = 'POST'
        (output_objects, (ret_code, ret_msg)) = \
                         main(client_id, user_arguments_dict)
    except Exception, exc:
        logger.error("failed to run %s on %s: %s" % \
                     (function, user_arguments_dict, exc))
        raise exc
    logger.info("done running command for %s: %s" % (target_path, command_str))
    logger.info("raw output is: %s" % output_objects)
    txt_out = txt_format(configuration, ret_code, ret_msg, output_objects)
    if ret_code != 0:
        raise Exception('command error: %s' % txt_format)
    logger.info("result was %s : %s:\n%s" % (ret_code, ret_msg, txt_out))

        
class MiGRuleEventHandler(PatternMatchingEventHandler):
    """Rule pattern-matching event handler to take care of VGrid rule changes
    and update the global rule database.
    """

    def __init__(self, patterns=None, ignore_patterns=None,
                 ignore_directories=False, case_sensitive=False):
        """Constructor"""
        PatternMatchingEventHandler.__init__(self, patterns, ignore_patterns,
                                             ignore_directories,
                                             case_sensitive)

    def update_rules(self, event):
        """Handle all rule updates"""
        state = event.event_type
        src_path = event.src_path
        if event.is_directory:
            logger.debug("skipping rule update for directory: %s" % src_path)
        logger.debug("%s rule file: %s" % (state, src_path))
        rel_path = src_path.replace(os.path.join(configuration.vgrid_home, ""),
                                    '')
        vgrid_name = rel_path.replace(os.sep + configuration.vgrid_triggers, '')
        vgrid_prefix = os.path.join(configuration.vgrid_files_home,
                                    vgrid_name, '')
        logger.info("refresh %s rules from %s" % (vgrid_name, src_path))
        try:
            new_rules = load(src_path)
        except Exception, exc:
            new_rules = []
            if state != "deleted":
                logger.error("failed to load event handler rules from %s" % \
                             src_path)
        logger.info("loaded new rules from %s:\n%s" % (src_path, new_rules))
        # Remove all old rules for this vgrid
        for target_path in all_rules.keys():
            all_rules[target_path] = [i for i in all_rules[target_path] if \
                                      i['vgrid_name'] != vgrid_name] 
        for entry in new_rules:
            logger.info("updating rule entry:\n%s" % entry)
            path = entry['path']
            abs_path = os.path.join(vgrid_prefix, path)
            all_rules[abs_path] = all_rules.get(abs_path, []) + [entry]
        logger.info("all rules:\n%s" % all_rules)

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

    event_map = {'modified': FileModifiedEvent, 'created': FileCreatedEvent,
                 'deleted': FileDeletedEvent, 'moved': FileMovedEvent}

    def __init__(self, patterns=None, ignore_patterns=None,
                 ignore_directories=False, case_sensitive=False):
        """Constructor"""
        PatternMatchingEventHandler.__init__(self, patterns, ignore_patterns,
                                             ignore_directories,
                                             case_sensitive)

    def __workflow_log(self, configuration, vgrid_name, msg, level='info'):
        """Wrapper to send a single msg to vgrid workflows page log file"""
        log_path = os.path.join(configuration.vgrid_home, vgrid_name,
                                workflows_log_name)
        workflows_logger = logging.getLogger('workflows')
        workflows_logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=workflows_log_size,
            backupCount=workflows_log_cnt-1)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        workflows_logger.addHandler(handler)
        if level == 'error':
            workflows_logger.error(msg)
        elif level == 'warning':
            workflows_logger.warning(msg)
        else:
            workflows_logger.info(msg)
        handler.flush()
        workflows_logger.removeHandler(handler)

    def __workflow_err(self, configuration, vgrid_name, msg):
        """Wrapper to send a single error msg to vgrid workflows page log"""
        self.__workflow_log(configuration, vgrid_name, msg, 'error')

    def __workflow_warn(self, configuration, vgrid_name, msg):
        """Wrapper to send a single warning msg to vgrid workflows page log"""
        self.__workflow_log(configuration, vgrid_name, msg, 'warning')

    def __workflow_info(self, configuration, vgrid_name, msg):
        """Wrapper to send a single error msg to vgrid workflows page log"""
        self.__workflow_log(configuration, vgrid_name, msg, 'info')

    def __handle_trigger(self, event, target_path, rule):
        """Actually handle valid trigger for a specific event and the
        corresponding target_path pattern and trigger rule.
        """
        state = event.event_type
        src_path = event.src_path
        _chain = getattr(event, '_chain', [(src_path, state)])
        base_dir = configuration.vgrid_files_home
        rel_src = src_path.replace(base_dir, '').lstrip(os.sep)
        vgrid_prefix = os.path.join(base_dir, rule['vgrid_name'])
        self.__workflow_info(configuration, rule['vgrid_name'],
                             "handle %s for %s" % (rule['action'], rel_src))
        if above_rate_limit(rule):
            logger.info("skipping %s due to rate limit: %s" % \
                        (target_path, show_rate_limit(rule)))
            self.__workflow_warn(configuration, rule['vgrid_name'],
                                 "skip %s trigger due to rate limit %s" % \
                                 (rel_src, show_rate_limit(rule)))
        elif rule['action'] in ['trigger-%s' % i for i in valid_trigger_changes]:
            change = rule['action'].replace('trigger-', '')
            FakeEvent = self.event_map[change]
            # Expand dynamic variables in argument once and for all
            expand_map = get_expand_map(rel_src, rule, state)
            for argument in rule['arguments']:
                filled_argument = argument
                for (key, val) in expand_map.items():
                    filled_argument = filled_argument.replace(key, val)
                self.__workflow_info(configuration, rule['vgrid_name'],
                                     "expanded argument %s to %s" % \
                                     (argument, filled_argument))
                pattern = os.path.join(vgrid_prefix, filled_argument)
                for path in glob.glob(pattern):
                    rel_path = path.replace(configuration.vgrid_files_home, '')
                    _chain += [(path, change)]
                    # Prevent obvious trigger chain cycles
                    if (path, change) in _chain[:-1]:
                        flat_chain = ["%s : %s" % pair for pair in _chain]
                        chain_str = ' <-> '.join(flat_chain)
                        rel_chain_str = chain_str.replace(
                            configuration.vgrid_files_home, '')
                        logger.warning("breaking trigger cycle %s" % chain_str)
                        self.__workflow_warn(configuration, rule['vgrid_name'],
                                             "breaking trigger cycle %s" % \
                                             rel_chain_str)
                        continue
                    fake = FakeEvent(path)
                    fake._chain = _chain
                    logger.info("trigger %s event on %s" % (change, path))
                    update_rate_limit(rule, target_path, state, '')
                    self.__workflow_info(configuration, rule['vgrid_name'],
                                         "trigger %s event on %s" % (change,
                                                                     rel_path))
                    self.handle_event(fake)
        elif rule['action'] == 'submit':
            mrsl_fd = tempfile.NamedTemporaryFile(delete=False)
            mrsl_path = mrsl_fd.name
            # Expand dynamic variables in argument once and for all
            expand_map = get_expand_map(rel_src, rule, state)
            try:
                for job_template in rule['templates']:
                    mrsl_fd.truncate(0)
                    if not fill_mrsl_template(job_template, mrsl_fd, rel_src,
                                              state, rule, expand_map,
                                              configuration):
                        raise Exception("fill template failed")
                    logger.debug("filled template for %s in %s" % \
                                 (target_path, mrsl_path))
                    (success, msg) = new_job(mrsl_path, rule['run_as'],
                                             configuration, False)
                    if success:
                        logger.info("submitted job for %s: %s" % (target_path,
                                                                  msg))
                        update_rate_limit(rule, target_path, state, msg)
                        self.__workflow_info(configuration, rule['vgrid_name'],
                                             "submitted job for %s: %s" % \
                                             (rel_src, msg))
                    else:
                        raise Exception(msg)
            except Exception, exc:
                logger.error("failed to submit job(s) for %s: %s" % \
                             (target_path, exc))
                self.__workflow_err(configuration, rule['vgrid_name'],
                                    "failed to submit job for %s: %s" % \
                                    (rel_src, exc))
            try:
                os.remove(mrsl_path)
            except Exception, exc:
                logger.warning("clean up after submit failed: %s" % exc)
        elif rule['action'] == 'command':
            # Expand dynamic variables in argument once and for all
            expand_map = get_expand_map(rel_src, rule, state)
            command_str = ''
            command_list = rule['arguments'][:1]
            for argument in rule['arguments'][1:]:
                filled_argument = argument
                for (key, val) in expand_map.items():
                    filled_argument = filled_argument.replace(key, val)
                self.__workflow_info(configuration, rule['vgrid_name'],
                                     "expanded argument %s to %s" % \
                                     (argument, filled_argument))
                command_list.append(filled_argument)
            try:
                run_command(command_list, target_path, rule, configuration)
                self.__workflow_info(configuration, rule['vgrid_name'],
                                     "ran command: %s" % \
                                     (' '.join(command_list)))
            except Exception, exc:
                logger.error("failed to run command for %s: %s (%s)" % \
                             (target_path, command_str, exc))
                self.__workflow_err(configuration, rule['vgrid_name'],
                                    "failed to run command for %s: %s (%s)" % \
                                    (rel_src, command_str, exc))
        else:
            logger.error("unsupported action: %(action)s" % rule)

    def handle_event(self, event):
        """Trigger any rule actions bound to file state change"""
        state = event.event_type
        src_path = event.src_path
        if event.is_directory:
            logger.debug("skipping event handling for directory: %s" % \
                         src_path)
        logger.info("got %s event for file: %s" % (state, src_path))
        logger.debug("filter %s against %s" % (all_rules.keys(), src_path))
        for (target_path, rule_list) in all_rules.items():
            # Do not use ordinary fnmatch as it lets '*' match anything
            # including '/' which leads to greedy matching in subdirs
            as_regexp = fnmatch.translate(target_path).replace('.*', '[^/]*')
            if re.match(as_regexp, src_path):
                logger.debug("matched %s for %s" % (src_path, as_regexp))
                for rule in rule_list:
                    # user may have been removed from vgrid - log and ignore
                    if not vgrid_is_owner_or_member(rule['vgrid_name'],
                                                    rule['run_as'],
                                                    configuration):
                        logger.warning("no such user in vgrid: %(run_as)s" \
                                       % rule)
                        continue
                    if not state in rule['changes']:
                        logger.info("skipping %s without change match (%s)" \
                                    % (target_path, state))
                        continue
                    
                    logger.info("trigger %s for %s: %s" % \
                                (rule['action'], src_path, rule))
                    self.__handle_trigger(event, target_path, rule)
            else:
                logger.debug("skipping %s with no matching rules" % \
                             target_path)

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
        """Handle moved files"""
        self.handle_event(event)


if __name__ == "__main__":
    print '''This is the MiG event handler daemon which monitors VGrid files
and triggers any configured events when target files are created, modifed or
deleted. VGrid owners can configure rules to trigger such events based on file
changes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
'''

    configuration = get_configuration_object()

    # Use separate logger

    logger = daemon_logger("events", configuration.user_events_log, "info")

    keep_running = True

    print 'Starting Event handler daemon - Ctrl-C to quit'

    logger.info("Starting Event handler daemon")

    logger.info("initializing rule listener")

    # Monitor rule configurations

    rule_monitor = Observer()
    rule_patterns = [os.path.join(configuration.vgrid_home, "*", 
                                  configuration.vgrid_triggers)]
    rule_handler = MiGRuleEventHandler(patterns=rule_patterns,
                                       ignore_directories=False,
                                       case_sensitive=True)
    rule_monitor.schedule(rule_handler, configuration.vgrid_home,
                          recursive=True)
    rule_monitor.start()

    logger.info("initializing file listener - may take some time")

    # monitor actual files to handle events for
    
    file_monitor = Observer()
    file_patterns = [os.path.join(configuration.vgrid_files_home, "*")]
    file_handler = MiGFileEventHandler(patterns=file_patterns,
                                       ignore_directories=True,
                                       case_sensitive=True)
    file_monitor.schedule(file_handler, configuration.vgrid_files_home,
                          recursive=True)
    file_monitor.start()

    logger.info("trigger rule refresh")

    # Fake touch event on all rule files to load initial rules

    logger.info("trigger load on all rule files (greedy) matching %s" % \
                rule_patterns[0])

    # We manually walk and test to get the greedy "*" directory match behaviour
    # of the PatternMatchingEventHandler
    all_trigger_rules = []
    for root, _, files in os.walk(configuration.vgrid_home):
        if configuration.vgrid_triggers in files:
            rule_path = os.path.join(root, configuration.vgrid_triggers)
            all_trigger_rules.append(rule_path)
    for rule_path in all_trigger_rules:
        logger.debug("trigger load on rules in %s" % rule_path)
        rule_handler.dispatch(FileModifiedEvent(rule_path))
    logger.debug("loaded initial rules:\n%s" % all_rules)

    logger.info("ready to handle triggers")

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
