#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# events - shared event trigger helper functions
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

"""Event trigger helper functions"""

import fnmatch
import os
import re

from shared.base import client_id_dir
from shared.defaults import crontab_name

# Init global crontab regexp once and for all
# Format: minute hour dayofmonth month dayofweek command
crontab_pattern = "^(\*|[0-9]{1,2}) (\*|[0-9]{1,2}) (\*|[0-9]{1,2}) "
crontab_pattern += "(\*|[0-9]{1,2}) (\*|[0-6]) (.*)$"
crontab_expr = re.compile(crontab_pattern)


def get_command_map(configuration):
    """Generate a dictionary with the supported commands and their expected
    call arguments."""
    
    # TODO: add all ops with effect here!

    cmd_map = {
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
        'chksum': ['hash_algo', 'path', 'dst', 'max_chunks'],
        'mqueue': ['queue', 'action', 'msg_id', 'msg'],
        }
    if configuration.site_enable_jobs:
        cmd_map.update({
            'submit': ['path'],
            'canceljob': ['job_id'],
            'resubmit': ['job_id'],
            'jobaction': ['job_id', 'action'],
            'liveio': ['action', 'src', 'dst', 'job_id'],
            })
    #if configuration.site_enable_sharelinks:
    #    cmd_map.update({
    #        'sharelink': ['path', 'read_access', 'write_access', 'invite', 'msg'],
    #        })
    if configuration.site_enable_transfers:
        cmd_map.update({
            'datatransfer': ['transfer_id', 'action'],
            })
    if configuration.site_enable_preview:
        cmd_map.update({
            'imagepreview': ['flags', 'action', 'path', 'extension'],
            })
    if configuration.site_enable_freeze:
        cmd_map.update({
            'createbackup': ['freeze_name', 'freeze_copy_0'],
            'deletebackup': ['freeze_id'],
            })
    return cmd_map

def get_expand_map(trigger_path, rule, state_change):
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

def load_crontab(client_id, configuration, allow_missing=True):
    """Load entries from plain user crontab file"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    crontab_path = os.path.join(configuration.user_settings, client_dir,
                                crontab_name)
    try:
        crontab_fd = open(crontab_path, "rb")
        crontab_contents = crontab_fd.read()
        crontab_fd.close()
    except Exception, exc:
        _logger.error('failed reading %s crontab file: %s' % (client_id, exc))
        crontab_contents = ''
    return crontab_contents

def parse_crontab_contents(configuration, client_id, crontab_lines):
    """Parse raw crontab content lines and return a list of crontab dictionary
    entries.
    """
    _logger = configuration.logger
    crontab_entries = []
    for line in crontab_lines:
        # Skip comments
        if line.startswith("#"):
            continue
        hit = crontab_expr.match(line.strip())
        if not hit:
            _logger.warning("Skip invalid crontab line for %s: %s" % \
                            (client_id, line))
            continue
        # Format: minute hour dayofmonth month dayofweek command
        entry = {'minute': hit.group(1), 'hour': hit.group(2),
                 'dayofmonth': hit.group(3), 'month': hit.group(4),
                 'dayofweek': hit.group(5), 'command': hit.group(6).split(),
                 'run_as': client_id}
        crontab_entries.append(entry)
    return crontab_entries
    
def parse_crontab(configuration, client_id, path):
    """Parse client_id crontab in path and return a list of crontab dictionary
    entries.
    """
    _logger = configuration.logger
    try:
        cron_fd = open(path, 'r')
        crontab_lines = cron_fd.readlines()
        cron_fd.close()
    except Exception, exc:
        _logger.error("Failed to read crontab in %s" % path)
        return []
    return parse_crontab_contents(configuration, client_id, crontab_lines)

def parse_and_save_crontab(crontab, client_id, configuration):
    """Validate and write the crontab for client_id"""
    client_dir = client_id_dir(client_id)
    crontab_path = os.path.join(configuration.user_settings, client_dir,
                                crontab_name)
    # Create crontab dir for any old users
    try:
        os.mkdir(crontab_path)
    except:
        pass
    status, msg = True, ''
    crontab_entries = parse_crontab_contents(configuration, client_id,
                                             crontab.splitlines())
    try:
        crontab_fd = open(crontab_path, "wb")
        # TODO: filter out broken lines before write?
        crontab_fd.write(crontab)
        crontab_fd.close()
        msg = "Found and saved %d valid crontab entries" % len(crontab_entries)
    except Exception, exc:
        status = False
        msg = 'ERROR: writing %s crontab file: %s' % (client_id, exc)
    return (status, msg)

def cron_match(configuration, cron_time, entry):
    """Check if cron_time matches the time specs in crontab_entry"""
    _logger = configuration.logger
    time_vals = {'minute': cron_time.minute, 'hour': cron_time.hour,
                 'month': cron_time.month, 'dayofmonth': cron_time.day,
                 'dayofweek': cron_time.weekday()}
    # TODO: extend to support e.g. */5 and the likes?
    for name, val in time_vals.items():
        # Strip any leading zeros before integer match
        if not fnmatch.fnmatch("%s" % val, entry[name].lstrip('0')):
            _logger.debug("cron_match failed on %s: %s vs %s" % \
                          (name, val, entry[name]))
            return False
    return True

if __name__ == '__main__':
    rule = {'templates': [], 'run_as': '/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk', 'rate_limit': '', 'vgrid_name': 'eScience', 'rule_id': 'test-dummy', 'match_dirs': False, 'match_files': True, 'arguments': ['+TRIGGERPATH+'], 'settle_time': '', 'path': '*.txt*', 'changes': ['modified'], 'action': 'trigger-created', 'match_recursive': True}
    samples = [('abc.txt', 'modified'), ('subdir/def.txt', 'modified')]
    print "Test event map:"
    for (path, change) in samples:
        print "Expanded vars for %s %s:" % (path, change)
        expanded = get_expand_map(path, rule, change)
        for (key, val) in expanded.items():
            print "    %s: %s" % (key, val)
        
