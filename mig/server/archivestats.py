#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# frozenstats - Helper to easily traverse archives and show stats
# Copyright (C) 2020  The MiG Project lead by Brian Vinter
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

"""Helper to traverse archives to do simple statistics e.g. about time to tape
for finalized archives.
"""
from __future__ import print_function

import getopt
import glob
import os
import sys
import time

from shared.conf import get_configuration_object
from shared.serial import load


def usage(name='archivestats.py'):
    """Usage help"""

    print("""Traverse all archives and collect stats about the ones in a particular state
Usage:
%(name)s [OPTIONS] STATE
Where OPTIONS may be one or more of:
   -a CREATED_AFTER    Limit to archives created after CREATED_AFTER (epoch)
   -b CREATED_BEFORE   Limit to archives created before CREATED_BEFORE (epoch)
   -c CONF_FILE        Use CONF_FILE as server configuration
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
""" % {'name': name})


# ## Main ###

if '__main__' == __name__:
    conf_path = None
    force = False
    verbose = False
    state = 'FINAL'
    now = int(time.time())
    created_before = now
    created_after = now - (30 * 24 * 3600)
    exit_code = 0
    opt_args = 'a:b:c:fhv'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            after = created_after
            if val.startswith('+'):
                after += int(val[1:])
            elif val.startswith('-'):
                after -= int(val[1:])
            else:
                after = int(val)
            created_after = after
        elif opt == '-b':
            before = created_before
            if val.startswith('+'):
                before += int(val[1:])
            elif val.startswith('-'):
                before -= int(val[1:])
            else:
                before = int(val)
            created_before = before
        elif opt == '-c':
            conf_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)

    if conf_path and not os.path.isfile(conf_path):
        print('Failed to read configuration file: %s' % conf_path)
        sys.exit(1)

    if verbose:
        if conf_path:
            print('using configuration in %s' % conf_path)
        else:
            print('using configuration from MIG_CONF (or default)')

    if len(args) == 1:
        state = args[0]
    else:
        print("Unexpected args: %s" % args)
        usage()
        sys.exit(1)

    if verbose:
        print('stats for archives in state %r between %s and %s' % (
            state, after, before))
    retval = 0
    configuration = get_configuration_object(skip_log=True)
    meta_pattern = os.path.join(
        configuration.freeze_home, '+C=*emailAddress=*', 'archive-*', 'meta.pck')
    csv = ['USER;ID;FLAVOR;CREATED;ON_DISK;TAPE_PROMISE']
    for meta_path in glob.glob(meta_pattern):
        #print "DEBUG: found meta in %s" % meta_path
        meta_timestamp = os.path.getmtime(meta_path)
        if meta_timestamp >= created_before or meta_timestamp <= created_after:
            # print "DEBUG: filter meta in %s due to timestamp %s" % (
            #    meta_path, meta_timestamp)
            continue
        meta_dict = load(meta_path)
        helper = {'CREATOR': 'UNSET', 'ID': 'UNSET', 'STATE': 'UNSET',
                  'CREATED_TIMESTAMP': 'UNSET', 'LOCATION': 'UNSET',
                  'DISK_TIME': 'UNKNOWN', 'TAPE_PROMISE': 'UNKNOWN'}
        helper.update(meta_dict)
        if helper['STATE'] != state:
            #print "DEBUG: filter meta with state %(STATE)s" % helper
            continue
        #print "DEBUG: dict %s" % helper
        helper['LOCATION'] = helper.get('LOCATION', [])
        for (loc, stamp) in helper['LOCATION']:
            if loc == 'disk':
                helper['DISK_TIME'] = "%s" % stamp
            elif loc == 'tape':
                helper['TAPE_PROMISE'] = "%s" % stamp
            else:
                print("WARNING: unexpected location entry: %s %s" % (
                    loc, stamp))
        if verbose:
            print("%(FLAVOR)s archive %(ID)s created on %(CREATED_TIMESTAMP)s with disk time %(DISK_TIME)s and tape promise %(TAPE_PROMISE)s" % helper)

        csv.append(
            "%(CREATOR)s;%(ID)s;%(FLAVOR)s;%(CREATED_TIMESTAMP)s;%(DISK_TIME)s;%(TAPE_PROMISE)s" % helper)

    print('\n'.join(csv)+'\n')
    sys.exit(retval)
