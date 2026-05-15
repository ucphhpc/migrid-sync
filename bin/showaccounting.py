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

from __future__ import absolute_import, print_function

import csv
import datetime
import getopt
import locale
import math
import os
import re
import sys

from mig.lib.accounting import get_usage, human_readable_filesize
from mig.shared.base import distinguished_name_to_user
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import gdp_distinguished_field, user_db_filename
from mig.shared.useradm import load_user_db

valid_output_formats = ["default", "csv"]


def usage(name="showaccounting.py"):
    """Usage help"""

    print(
        """Create accounting information based on quota.
Usage:
%(name)s [ACCOUNTING_OPTIONS]
Where ACCOUNTING_OPTIONS may be one or more of:
   -h                  Show this help
   -v                  Verbose output
   -i                  Show bytes in SI units (power of 10)
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DECIMALS         Number of decimals (default 3)
   -f USER_FILTER      Regex user (CERT_DN) filter
   -l LOCALE_FORMAT    Use specific locale format (locale -a)
   -m MINIMUM_USAGE    Only show accounts using more than
                       minimum usage (TiB)
   -o FORMAT           Output format 
                       Supported formats: %(valid_output_formats)s
   -t TIMESTAMP        Use specific timestamp, latest if unset
"""
        % {"name": name, "valid_output_formats": valid_output_formats}
    )


def show_accounting(
    configuration,
    timestamp,
    user_filter,
    minimum_usage,
    si_byte_format,
    decimals,
    output_format,
    verbose,
):
    """Print user accounting report"""
    user_filter_re = None
    if user_filter:
        try:
            user_filter_re = re.compile(user_filter)
        except Exception as err:
            print(
                "ERROR: Failed to compile user_filter: %r error: %s"
                % (user_filter, err)
            )
            return

    account_usage = get_usage(
        configuration,
        timestamp=timestamp,
        decimals=decimals,
        si_byte_format=si_byte_format,
        verbose=verbose,
    )
    if account_usage is None:
        print("ERROR: Missing account usage data")
        return

    # Load userdb
    user_db_filepath = os.path.join(
        configuration.user_db_home, user_db_filename
    )
    try:
        user_db = load_user_db(user_db_filepath)
    except Exception as err:
        print(
            "WARNING: Failed to load user_db from: %r, error: %s"
            % (user_db_filepath, err)
        )
        user_db = {}

    accounting = account_usage.get("accounting", {})
    accounting_timestamp = account_usage.get("timestamp", 0)
    accounting_datestr = datetime.datetime.fromtimestamp(
        accounting_timestamp
    ).strftime("%d/%m/%Y-%H:%M:%S")

    # Sorted by total bytes and print usage for users

    report_total_users = 0
    report_shown_users = 0
    report_total_bytes = 0
    report_shown_bytes = 0
    total_bytes_map = {}
    for userid, values in accounting.items():
        # Do not show GDP project users
        # projects are accounted for by the main user
        if (
            configuration.site_enable_gdp
            and userid.find("/%s=" % gdp_distinguished_field) != -1
        ):
            continue
        report_total_users += 1
        total_bytes = values.get("total_bytes", 0)
        report_total_bytes += total_bytes
        if total_bytes < minimum_usage or (
            user_filter_re and not user_filter_re.fullmatch(userid)
        ):
            continue
        report_shown_users += 1
        report_shown_bytes += total_bytes
        total_bytes_map_userlist = total_bytes_map.get(total_bytes, [])
        total_bytes_map_userlist.append(userid)
        total_bytes_map[total_bytes] = total_bytes_map_userlist
    sorted_total_bytes = sorted(list(total_bytes_map), reverse=True)

    if output_format == "default":
        print(
            "\nAccounting (%d) %s for storage quota(s):"
            % (accounting_timestamp, accounting_datestr)
        )
        for quota_fs, values in account_usage.get("quota", {}).items():
            quota_mtime = values.get("mtime", 0)
            quota_datestr = datetime.datetime.fromtimestamp(
                quota_mtime
            ).strftime("%d/%m/%Y-%H:%M:%S")
            print(" - %s (%d) %s" % (quota_fs, quota_mtime, quota_datestr))

        print(
            "Found a total of %s users using %s storage"
            % (
                report_total_users,
                human_readable_filesize(report_total_bytes, decimals=decimals),
            )
        )
        print(
            "Showing details for %s users using %s storage"
            % (
                report_shown_users,
                human_readable_filesize(report_shown_bytes, decimals=decimals),
            )
        )
        print("User filter: %r" % user_filter)
        print(
            "Minimum usage: %s"
            % human_readable_filesize(minimum_usage, decimals=decimals)
        )
        for total_bytes in sorted_total_bytes:
            for userid in total_bytes_map[total_bytes]:
                user_dict = distinguished_name_to_user(userid)
                user_db_ent = user_db.get(userid, {})
                report = accounting[userid]
                total_report = report.get("total_report", "")
                home_report = report.get("home_report", "")
                freeze_report = report.get("freeze_report", "")
                vgrid_report = report.get("vgrid_report", "")
                ext_users_report = report.get("ext_users_report", "")
                peers_report = report.get("peers_report", "")
                print(
                    "\n-------------------------------------------------------------------------------"
                )
                if verbose:
                    print("%s:" % userid)
                print("Username: %s" % user_dict.get("full_name", ""))
                print("Email: %s" % user_dict.get("email", ""))
                print("Organization: %s" % user_db_ent.get("organization", ""))
                print("Faculty: %s" % user_db_ent.get("faculty", ""))
                print("Institute: %s" % user_db_ent.get("institute", ""))
                print(
                    "Expire: %s"
                    % datetime.datetime.fromtimestamp(
                        user_db_ent.get("expire", 0)
                    ).strftime("%d/%m/%Y-%H:%M:%S")
                )
                if total_report:
                    print(total_report)
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
    else:
        output_list = []
        for total_bytes in sorted_total_bytes:
            for userid in total_bytes_map[total_bytes]:
                user_db_ent = user_db.get(userid, {})
                report = accounting[userid]
                output_ent = {}
                output_ent["faculty"] = user_db_ent.get("faculty", "")
                output_ent["institute"] = user_db_ent.get("institute", "")
                output_ent["username"] = user_db_ent.get("full_name", "")
                output_ent["email"] = user_db_ent.get("email", "")
                user_total_bytes = report.get("total_bytes", 0)
                output_ent["bytes"] = user_total_bytes
                if si_byte_format:
                    output_ent["bytes_tb"] = locale.format_string(
                        "%.*f", (decimals, user_total_bytes * 1.0 / 1000**4)
                    )
                else:
                    output_ent["bytes_tib"] = locale.format_string(
                        "%.*f", (decimals, user_total_bytes * 1.0 / 1024**4)
                    )
                output_list.append(output_ent)
        if output_list:
            if output_format == "csv":
                fieldnames = [
                    "faculty",
                    "institute",
                    "username",
                    "email",
                    "bytes",
                ]
                if si_byte_format:
                    fieldnames.append("bytes_tb")
                else:
                    fieldnames.append("bytes_tib")
                writer = csv.DictWriter(
                    sys.stdout, fieldnames=fieldnames, delimiter=";"
                )
                _ = writer.writeheader()
                _ = writer.writerows(output_list)


if "__main__" == __name__:
    conf_path = None
    user_filter = None
    si_byte_format = False
    output_format = "default"
    decimals = 3
    timestamp = 0
    locale_format = None
    minimum_usage = 0
    verbose = False
    valid_output_formats = ["default", "csv"]
    opt_args = "hvic:d:f:l:m:o:t:"
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
        for opt, val in opts:
            if opt == "-h":
                usage()
                sys.exit(0)
            elif opt == "-v":
                verbose = True
            elif opt == "-i":
                si_byte_format = True
            elif opt == "-c":
                conf_path = val
            elif opt == "-d":
                decimals = int(val)
            elif opt == "-f":
                user_filter = val
            elif opt == "-l":
                locale_format = val
            elif opt == "-m":
                minimum_usage = math.ceil(float(val) * (1024**4))
            elif opt == "-o":
                output_format = val
            elif opt == "-t":
                timestamp = int(val)
            else:
                print("Error: %s not supported!" % opt)
                usage()
                sys.exit(1)
    except getopt.GetoptError as err:
        print("Error: %s" % err)
        usage()
        sys.exit(1)

    try:
        if locale_format:
            locale.setlocale(locale.LC_ALL, locale_format)
    except Exception as err:
        print(
            "Failed to set locale format: %r, error: %s" % (locale_format, err)
        )
        sys.exit(1)

    if output_format not in valid_output_formats:
        print(
            "Invalid summary format: %r, valid formats: %s"
            % (output_format, valid_output_formats)
        )
        sys.exit(1)

    configuration = get_configuration_object(
        config_file=conf_path, skip_log=True, disable_auth_log=True
    )

    show_accounting(
        configuration,
        timestamp,
        user_filter,
        minimum_usage,
        si_byte_format,
        decimals,
        output_format,
        verbose,
    )

    sys.exit(0)
