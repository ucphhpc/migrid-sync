#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showaccounting - Display storage accounting
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Create accounting information for users"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import getopt
import re
import datetime

from mig.shared.conf import get_configuration_object
from mig.lib.accounting import get_usage, human_readable_filesize


def usage(name='accounting.py'):
    """Usage help"""

    print("""Create accounting information based on quota.
Usage:
%(name)s [ACCOUNTING_OPTIONS]
Where ACCOUNTING_OPTIONS may be one or more of:
   -h                  Show this help
   -v                  Verbose output
   -c CONF_FILE        Use CONF_FILE as server configuration
   -f User filter      Regex user (CERT_DN) filter
   -m Minimum usage    Only show accounts using more than
                       minimum usage (TB).
   -t TIMESTAMP        Use specific timestamp, latest if unset
""" % {'name': name})


def show_accounting(configuration,
                    timestamp,
                    user_filter,
                    minimum_usage):
    """Print user accointing report"""
    user_filter_re = None
    if user_filter:
        try:
            user_filter_re = re.compile(user_filter)
        except Exception as err:
            print("ERROR: Failed to compile user_filter: %r error: %s"
                  % (user_filter, err))
            return

    usage = get_usage(configuration,
                      timestamp=timestamp,
                      verbose=verbose)

    accounting = usage.get('accounting', {})
    accounting_timestamp = usage.get('timestamp', 0)
    accounting_datestr \
        = datetime.datetime.fromtimestamp(accounting_timestamp) \
        .strftime('%d/%m/%Y-%H:%M:%S')

    # Sorted by total bytes and print usage for users

    report_total_users = 0
    report_shown_users = 0
    report_total_bytes = 0
    report_shown_bytes = 0
    total_bytes_map = {}
    for username, values in accounting.items():
        # Do not show GDP project users
        # projects are accounted for by the main user
        if configuration.site_enable_gdp \
                and username.find("/GDP=") != -1:
            continue
        report_total_users += 1
        total_bytes = values.get('total_bytes', 0)
        report_total_bytes += total_bytes
        if total_bytes < minimum_usage \
                or user_filter_re and not user_filter_re.fullmatch(username):
            continue
        report_shown_users += 1
        report_shown_bytes += total_bytes
        total_bytes_map_userlist = total_bytes_map.get(total_bytes, [])
        total_bytes_map_userlist.append(username)
        total_bytes_map[total_bytes] = total_bytes_map_userlist
    sorted_total_bytes = sorted(list(total_bytes_map.keys()), reverse=True)

    print("\nAccounting (%d) %s for storage quota(s):"
          % (accounting_timestamp, accounting_datestr))
    for quota_fs, values in usage.get('quota', {}).items():
        quota_mtime = values.get('mtime', 0)
        quota_datestr = datetime.datetime.fromtimestamp(quota_mtime) \
            .strftime('%d/%m/%Y-%H:%M:%S')
        print(" - %s (%d) %s" % (quota_fs,
                                 quota_mtime,
                                 quota_datestr))

    print("Found a total of %s users using %s storage"
          % (report_total_users,
             human_readable_filesize(report_total_bytes)))
    print("Showing details for %s users using %s storage "
          % (report_shown_users,
             human_readable_filesize(report_shown_bytes)))
    print("User filter: %r" % user_filter)
    print("Minumum usage: %s" % human_readable_filesize(minimum_usage))
    for total_bytes in sorted_total_bytes:
        total_bytes_human = human_readable_filesize(total_bytes)
        for username in total_bytes_map[total_bytes]:
            report = accounting[username]
            home_report = report.get('home_report', '')
            freeze_report = report.get('freeze_report', '')
            vgrid_report = report.get('vgrid_report', '')
            ext_users_report = report.get('ext_users_report', '')
            peers_report = report.get('peers_report', '')
            print("\n%s:" % username)
            print("Total usage: %s" % total_bytes_human)
            if home_report:
                print(home_report)
            if freeze_report:
                print(freeze_report)
            if vgrid_report:
                print(vgrid_report)
            if ext_users_report:
                print(ext_users_report)
            if peers_report:
                print(peers_report)


if '__main__' == __name__:
    conf_path = None
    user_filter = None
    timestamp = 0
    minimum_usage = 0
    verbose = False
    opt_args = 'hvc:f:m:t:'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
        for (opt, val) in opts:
            if opt == '-h':
                usage()
                sys.exit(0)
            if opt == '-v':
                verbose = True
            elif opt == '-c':
                conf_path = val
            elif opt == '-f':
                user_filter = val
            elif opt == '-m':
                minimum_usage = float(val)*(1024**4)
            elif opt == '-t':
                timestamp = int(val)
            else:
                print('Error: %s not supported!' % opt)
                usage()
                sys.exit(1)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    configuration = get_configuration_object(config_file=conf_path,
                                             skip_log=True,
                                             disable_auth_log=True)

    show_accounting(configuration,
                    timestamp,
                    user_filter,
                    minimum_usage)

    sys.exit(0)
