#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# events - shared event trigger and cron/at helper functions
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

"""Event trigger and cron/at helper functions"""

from __future__ import print_function
from __future__ import absolute_import

import datetime
import fnmatch
import os
import re
import shlex

from mig.shared.base import client_id_dir
from mig.shared.defaults import crontab_name, atjobs_name
from mig.shared.fileio import read_file, read_file_lines, write_file

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


def get_path_expand_map(trigger_path, rule, state_change):
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


def get_time_expand_map(timestamp, rule):
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
        expanded = get_path_expand_map(path, trigger_rule, change)
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
            expanded = get_time_expand_map(timestamp, rule)
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
