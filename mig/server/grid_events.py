#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_events - event handler to monitor files and trigger actions
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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
"""

import fnmatch
import glob
import logging
import logging.handlers
import os
import sys
import tempfile
import time

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
from shared.serial import load
from shared.vgrid import vgrid_is_owner_or_member

# Global trigger rule dictionary with rules for all VGrids

all_rules = {}
configuration, logger = None, None

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
        vgrid_name = rel_path.replace(os.sep + 'triggers', '')
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
        rel_path = src_path.replace(base_dir, '').lstrip(os.sep)
        vgrid_prefix = os.path.join(base_dir, rule['vgrid_name'])
        self.__workflow_info(configuration, rule['vgrid_name'],
                             "handle %s for %s" % (rule['action'], rel_path))
        if rule['action'] in ['trigger-%s' % i for i in valid_trigger_changes]:
            change = rule['action'].replace('trigger-', '')
            FakeEvent = self.event_map[change]
            for argument in rule['arguments']:
                pattern = os.path.join(vgrid_prefix, argument)
                for path in glob.glob(pattern):
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
                    self.__workflow_info(configuration, rule['vgrid_name'],
                                         "trigger %s event on %s" % (change,
                                                                     path))
                    self.handle_event(fake)
        elif rule['action'] == 'submit':
            mrsl_fd = tempfile.NamedTemporaryFile(delete=False)
            mrsl_path = mrsl_fd.name
            try:
                if not fill_mrsl_template(mrsl_fd, rel_path, state, rule,
                                          configuration):
                    raise Exception("fill template failed")
                            
                logger.debug("filled template for %s in %s" % \
                             (target_path, mrsl_path))
                (success, msg) = new_job(mrsl_path, rule['run_as'],
                                         configuration, False)
                if success:
                    logger.info("submitted job for %s: %s" % (target_path,
                                                              msg))
                    self.__workflow_info(configuration, rule['vgrid_name'],
                                         "submitted job for %s: %s" % \
                                         (target_path, msg))
                else:
                    raise Exception(msg)
            except Exception, exc:
                logger.error("failed to submit job for %s: %s" % (target_path,
                                                                  exc))
                self.__workflow_err(configuration, rule['vgrid_name'],
                                    "failed to submit job for %s: %s" % \
                                    (target_path, exc))
            try:
                os.remove(mrsl_path)
            except Exception, exc:
                logger.warning("clean up after submit failed: %s" % exc)
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
            for rule in rule_list:
                if fnmatch.fnmatch(src_path, target_path):
                    if not state in rule['changes']:
                        logger.info("skipping %s without change match (%s)" \
                                    % (target_path, state))
                        continue
                    # user may have been removed from vgrid - log and ignore
                    if not vgrid_is_owner_or_member(rule['vgrid_name'],
                                                    rule['run_as'],
                                                    configuration):
                        logger.warning("no such user in vgrid: %(run_as)s" \
                                       % rule)
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
    print os.environ.get('MIG_CONF', 'DEFAULT'), configuration.server_fqdn

    # Use: separate logger
    logging.basicConfig(filename=configuration.user_events_log,
                        level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logger = logging

    keep_running = True

    print 'Starting Event handler daemon - Ctrl-C to quit'

    # Monitor rule configurations

    rule_monitor = Observer()
    rule_patterns = [os.path.join(configuration.vgrid_home, "*", "triggers")]
    rule_handler = MiGRuleEventHandler(patterns=rule_patterns,
                                       ignore_directories=False,
                                       case_sensitive=True)
    rule_monitor.schedule(rule_handler, configuration.vgrid_home,
                          recursive=True)
    rule_monitor.start()

    # monitor actual files to handle events for
    
    file_monitor = Observer()
    file_patterns = [os.path.join(configuration.vgrid_files_home, "*")]
    file_handler = MiGFileEventHandler(patterns=file_patterns,
                                       ignore_directories=True,
                                       case_sensitive=True)
    file_monitor.schedule(file_handler, configuration.vgrid_files_home,
                          recursive=True)
    file_monitor.start()

    # Fake touch event on all rule files to load initial rules
    logger.info("trigger load on all rule files matching %s" % rule_patterns[0])
    for rule_path in glob.glob(rule_patterns[0]):
        logger.debug("trigger load on rules in %s" % rule_path)
        rule_handler.dispatch(FileModifiedEvent(rule_path))
    logger.debug("loaded initial rules:\n%s" % all_rules)
    
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
