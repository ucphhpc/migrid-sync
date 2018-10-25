#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cmdapi - shared backend command line access helper functions
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

"""Helpers to expose functionality backends on command-line form"""

import getopt


# TODO: switch to a command+flags+args map suitable for direct argparse use?

def get_flag_map(configuration):
    """Generate a dictionary with the supported optional command flags. Only
    commands with flags are included.
    """

    flags_map = {'cp': ['r', 'f'], 'rm': ['r', 'f'], 'mkdir': ['p']}
    return flags_map


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
    if configuration.site_enable_sharelinks:
        # TODO: expose additional operations for sharelinks?
        #       maybe split up sharelinks.py into explicit action scripts?
        cmd_map.update({
            # 'addsharelink': ['path', 'read_access', 'write_access', 'invite', 'msg'],
            'delsharelink': ['share_id'],
        })
    if configuration.site_enable_transfers:
        cmd_map.update({
            'datatransfer': ['transfer_id', 'action'],
        })
    if configuration.site_enable_preview:
        cmd_map.update({
            'imagepreview': ['flags', 'action', 'path', 'extension'],
        })
    if configuration.site_enable_freeze:
        # NOTE: createbackup is a one-shot create+finalize backup helper.
        cmd_map.update({
            'createbackup': ['freeze_name', 'freeze_copy_0'],
            'deletebackup': ['freeze_id'],
            'addfreezedata': ['freeze_id', 'freeze_copy_0'],
        })
    if configuration.site_enable_crontab:
        cmd_map.update({
            'crontab': ['crontab', 'action'],
        })
    return cmd_map


def map_args_to_vars(var_list, arg_list):
    """Map command args to backend var names - if more args than vars we
    assume variable length on the first arg:
       zip src1 src2 src3 dst -> src: [src1, src2, src3], dst: [dst]
    """

    # TODO: this naive first arg expansion does NOT always make sense!
    #       e.g. chksum HASH_ALGO PATH DST MAX_CHUNKS called with
    #       chksum md5 welcome.txt readme.txt checksums.out -1
    #       should really assign welcome.txt and readme.txt to PATH
    #       but actually assigns md5 and welcome.txt to HASH instead.
    #
    #       We need something like the *nargs* helper in argparse to make it.

    args_dict = dict(zip(var_list, [[] for _ in var_list]))
    remain_vars = [i for i in var_list]
    remain_args = [i for i in arg_list]
    while remain_args:
        args_dict[remain_vars[0]].append(remain_args[0])
        del remain_args[0]
        if len(remain_args) < len(remain_vars):
            del remain_vars[0]
    return args_dict


def get_usage_map(configuration):
    """Generate a dictionary with commands and their usage help strings"""
    command_map = get_command_map(configuration)
    flag_map = get_flag_map(configuration)
    usage_map = {}
    for (cmd, args) in command_map.items():
        flags = ''
        if flag_map.get(cmd, []):
            flags = ' '.join(['[-%s]' % i for i in flag_map[cmd]])
        # We allow variable number of args in map args but only expose for some
        # TODO: fix expansion and extend to all lengths here
        if args[0] in ['src', 'path', 'job_id']:
            args.insert(1, '[%s ..]' % args[0])
        args_upper = ' '.join(args).upper()
        usage_map[cmd] = "%s %s %s" % (cmd, flags, args_upper)
    return usage_map


def parse_command_args(configuration, command_list):
    """Parse user commands as the ones found in cron/at and events rules"""
    command_map = get_command_map(configuration)
    if not command_list or not command_list[0] in command_map:
        raise ValueError('unsupported command: %s' % command_list[0])
    function = command_list[0]
    args_form = command_map[function]
    flag_map = get_flag_map(configuration)
    flag_chars = flag_map.get(function, [])
    opts_str = ''.join(flag_chars)
    flags = ''
    try:
        (opts, args) = getopt.getopt(command_list[1:], opts_str)
    except getopt.GetoptError, goe:
        print 'Error: %s' % goe
        raise ValueError("Error: command parsing failed: %s" % goe)

    for (opt, val) in opts:
        opt_char = opt.lstrip('-')
        if opt_char in flag_chars:
            flags += opt_char
        else:
            raise ValueError('Error: %s not supported!' % opt)

    user_arguments_dict = map_args_to_vars(args_form, args)
    user_arguments_dict['flags'] = [flags]
    return (function, user_arguments_dict)


if __name__ == '__main__':
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    for cmd_list in [['cp', 'srcfile', 'dstfile'],
                     ['cp', 'srcfile', 'srcfile2', 'dstdir'],
                     ['cp', '-r', 'srcdir', 'dstdir'],
                     ['cp', '-f', 'srcdir', 'dstdir'],
                     ['cp', '-rf', 'srcdir', 'dstdir'],
                     ['cp', '-r', '-f', 'srcdir', 'dstdir'],
                     ['cp', '-r', 'srcdir', 'srcdir2', 'dstdir']]:
        print "Parsing %s" % cmd_list
        (backend, args_dict) = parse_command_args(conf, cmd_list)
        print "Backend %s received args %s" % (backend, args_dict)
    for (cmd, usage) in get_usage_map(conf).items():
        print "Usage for %s\n\t%s" % (cmd, usage)
