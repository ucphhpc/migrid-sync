#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# events - shared event trigger helper functions
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

"""Event trigger helper functions"""

import os

def get_command_map(configuration):
    """Generate a dictionary with the supported commands and their expected
    call arguments."""
    
    # TODO: add all ops with effect here!

    return {
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
        'filemetaio': ['flags', 'action', 'path', 'extension'],
        }

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


if __name__ == '__main__':
    rule = {'templates': [], 'run_as': '/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk', 'rate_limit': '', 'vgrid_name': 'eScience', 'rule_id': 'test-dummy', 'match_dirs': False, 'match_files': True, 'arguments': ['+TRIGGERPATH+'], 'settle_time': '', 'path': '*.txt*', 'changes': ['modified'], 'action': 'trigger-created', 'match_recursive': True}
    samples = [('abc.txt', 'modified'), ('subdir/def.txt', 'modified')]
    print "Test event map:"
    for (path, change) in samples:
        print "Expanded vars for %s %s:" % (path, change)
        expanded = get_expand_map(path, rule, change)
        for (key, val) in expanded.items():
            print "    %s: %s" % (key, val)
        
