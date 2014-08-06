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

import os
import sys
import time

try:
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler
except ImportError:
    print "ERROR: the python watchdog module is required for this daemon"
    sys.exit(1)

from shared.conf import get_configuration_object

# Global trigger rule dictionary with rules for all VGrids

all_rules = {}
configuration, logger = None, None

class MiGFileEventHandler(PatternMatchingEventHandler):
    """File pattern-matching event handler to take care of VGrid file changes
    and the corresponding action triggers.
    """
    
    def handle_event(self, event):
        """Trigger any rule actions bound to file state change"""
        state = event.event_type
        src_path = event.src_path
        if event.is_directory:
            logger.info("skipping event handling for directory: %s" % src_path)
        logger.info("%s event for file: %s" % (state, src_path))
        rule = all_rules.get(src_path, {})
        if rule:
            logger.info("TODO: trigger action for %s: %s" % (src_path, rule))

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


class MiGRuleEventHandler(PatternMatchingEventHandler):
    """Rule pattern-matching event handler to take care of VGrid rule changes
    and update the global rule database.
    """

    def update_rules(self, event):
        """Handle all rule updates"""
        state = event.event_type
        src_path = event.src_path
        if event.is_directory:
            logger.info("skipping rule update for directory: %s" % src_path)
        logger.info("%s rule file: %s" % (state, src_path))
        rel_path = src_path.replace(configuration.vgrid_home + os.sep, '')
        vgrid_name = rel_path.replace(os.sep + 'events', '')
        logger.info("TODO: refresh %s rules from %s" % (vgrid_name, src_path))
        new_rules = {}
        for (target, rule) in all_rules.items():
            vgrid_prefix = os.path.join(configuration.vgrid_files_home,
                                        vgrid_name, '')
            if target.startswith(vgrid_prefix):
                logger.info("refresh rule for %s: %s" % (src_path, rule))
                if not target in new_rules:
                    logger.info("removing old rule for %s: %s" % (target, rule))
                    del all_rules[target]
                else:
                    logger.info("updating rule for %s: %s" % (target, rule))
                    all_rules[target] = new_rules[target]


    def on_modified(self, event):
        """Handle modified rule file"""
        self.update_rules(event)

    def on_created(self, event):
        """Handle new rule file"""
        self.update_rules(event)

    def on_deleted(self, event):
        """Handle deleted rule file"""
        self.update_rules(event)


# ## MAIN ###

print '''This is the MiG event handler daemon which monitors VGrid files and
triggers any configured events when target files are created, modifed or
deleted. VGrid owners can configure rules to trigger such events based on file
changes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
'''

configuration = get_configuration_object()
print os.environ.get('MIG_CONF', 'DEFAULT'), configuration.server_fqdn
logger = configuration.logger

keep_running = True

print 'Starting Event handler daemon - Ctrl-C to quit'

# Monitor rule configurations

rule_monitor = Observer()
rule_monitor.schedule(MiGRuleEventHandler, configuration.vgrid_home)
rule_monitor.start()

# monitor actual files to handle events for

file_monitor = Observer()
file_monitor.schedule(MiGFileEventHandler, configuration.vgrid_files_home)
file_monitor.start()

while keep_running:
    try:

        # Throttle down

        time.sleep(1)
    except KeyboardInterrupt:

        keep_running = False
    except Exception, exc:
        print 'Caught unexpected exception: %s' % exc

rule_monitor.stop()
file_monitor.stop()
print 'Event handler daemon shutting down'
sys.exit(0)
