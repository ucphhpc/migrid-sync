#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# usagestats - Collect and report various central usage stats for the site
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

"""Show basic stats about site users and storage use"""

from __future__ import print_function
from __future__ import absolute_import

import getopt
import os
import sys
import time

from mig.shared.base import extract_field
from mig.shared.defaults import freeze_meta_filename, keyword_auto
from mig.shared.fileio import unpickle, walk
from mig.shared.notification import send_email
from mig.shared.safeeval import subprocess_popen, subprocess_pipe
from mig.shared.serial import dump
from mig.shared.useradm import init_user_adm, search_users, default_search

valid_output_formats = ['csv', 'txt', 'pickle', 'json', 'yaml']


def usage(name='usagestats.py'):
    """Usage help"""

    print("""Collect site stats based on MiG user database and file system.
Usage:
%(name)s [OPTIONS]
Where OPTIONS may be one or more of:
   -a EXPIRE_AFTER     Limit to users set to expire after EXPIRE_AFTER time
   -b EXPIRE_BEFORE    Limit to users set to expire before EXPIRE_BEFORE time
   -c CONF_FILE        Use CONF_FILE as server configuration
   -d DB_FILE          Use DB_FILE as user data base file
   -f                  Force operations to continue past errors
   -h                  Show this help
   -o OUTPUT_FORMATS   Save collected stats on OUTPUT_FORMATS (space sep)
   -s SITE_STATS       Save collected stats in SITE_STATS (AUTO for conf value)
   -t FS_TYPE          Limit disk stats to mounts of given FS_TYPE
   -v                  Verbose output
""" % {'name': name})


def compact_stats(configuration, stats):
    """Helper to flatten stats for use in txt and csv output"""
    fill = {}
    fill['disk_use'] = '\n'.join(stats['disk']['use'])
    fill['disk_mounts'] = '\n'.join(stats['disk']['mounts'])
    fill['totals_all_users'] = stats['totals']['all_users']
    fill['totals_active_users'] = stats['totals']['active_users']
    fill['totals_vgrids'] = stats['totals']['vgrids']
    fill['totals_archives'] = stats['totals']['archives']
    fill['weekly_register_users'] = stats['weekly']['register_users']
    fill['weekly_expire_users'] = stats['weekly']['expire_users']
    fill['weekly_vgrids'] = stats['weekly']['vgrids']
    fill['weekly_archives'] = stats['weekly']['archives']

    fill['users_by_org'] = ''
    org_list = stats['org_counts'].items()
    org_list.sort()
    for (org, cnt) in org_list:
        fill['users_by_org'] += '%d\t%s\n' % (cnt, org)

    fill['users_by_domain'] = ''
    domain_list = stats['domain_counts'].items()
    domain_list.sort()
    for (domain, cnt) in domain_list:
        fill['users_by_domain'] += '%d\t%s\n' % (cnt, domain)
    return fill


def format_txt(configuration, stats):
    """Format stats for plain text output"""
    fill = compact_stats(configuration, stats)
    txt = """=== Disk Use ===
%(disk_use)s

=== Disk Mounts ===
%(disk_mounts)s

Where
 * vgrid_files_home is all vgrid shared folders
 * vgrid_private_base/vgrid_public_base are all vgrid web portals
 * user_home is all user home dirs
 * freeze_home is frozen archives from all users

== Totals ==
=== Registered Local Users ===
%(totals_all_users)d

=== Active Local Users ===
%(totals_active_users)d

=== Registered VGrids ===
%(totals_vgrids)d

=== Frozen Archives ===
%(totals_archives)d

== This Week ==
=== Registered and Renewed Local Users ===
%(weekly_register_users)d

=== Recently expired Local Users ===
%(weekly_expire_users)d

=== Registered and Updated VGrids ===
%(weekly_vgrids)d

=== Frozen Archives ===
%(weekly_archives)d

== User Distribution ==
=== By Organisation ===
%(users_by_org)s

=== By Email Domain ===
%(users_by_domain)s
"""
    return txt


def format_csv(configuration, stats):
    """Format stats for plain text output"""
    fill = compact_stats(configuration, stats)
    # TODO: properly csv format
    csv = """Disk Use
%(disk_use)s

Disk Mounts
%(disk_mounts)s

Totals
Registered Local Users;%(totals_all_users)d
Active Local Users;%(totals_active_users)d
Registered VGrids;%(totals_vgrids)d
Frozen Archives;%(totals_archives)d

This Week
Registered and Renewed Local Users;%(weekly_register_users)d
Recently expired Local Users;%(weekly_expire_users)d
Registered and Updated VGrids;%(weekly_vgrids)d
Frozen Archives;%(weekly_archives)d

User Distribution
By Organisation
%(users_by_org)s

By Email Domain
%(users_by_domain)s
"""
    return csv


def write_sitestats(configuration, stats, path_prefix, output_format):
    """Dump stats to file(s) of given output_format(s) using format name
    as extension"""

    for ext in output_format:
        dst_path = "%s.%s" % (path_prefix, ext)
        if ext == 'csv':
            out = format_csv(configuration, stats)
            with open(dst_path, "w") as fh:
                fh.write(out)
        elif ext == 'txt':
            out = format_txt(configuration, stats)
            with open(dst_path, "w") as fh:
                fh.write(out)
        elif ext in ['json', 'yaml', 'pickle']:
            dump(stats, dst_path, serializer=ext)
        else:
            return False
    return True


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    fs_opts = []
    expire = None
    force = False
    verbose = False
    sitestats_home = None
    output_formats = []
    search_filter = default_search()
    expire_before, expire_after = None, None
    opt_args = 'a:b:c:d:fho:s:t:u:v'
    try:
        (opts, args) = getopt.getopt(args, opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-a':
            search_filter['expire_after'] = int(val)
        elif opt == '-b':
            search_filter['expire_before'] = int(val)
        elif opt == '-c':
            conf_path = val
        elif opt == '-d':
            db_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-o':
            for ext in val.split():
                if ext in valid_output_formats:
                    output_formats.append(ext)
                else:
                    print("Error: unsupported output format: %s" % ext)
        elif opt == '-s':
            sitestats_home = val
        elif opt == '-t':
            for fs_type in val.split():
                fs_opts += ['-t', fs_type]
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            sys.exit(1)

    if conf_path and not os.path.isfile(conf_path):
        print('Failed to read configuration file: %s' % conf_path)
        sys.exit(1)

    (configuration, all_hits) = search_users(
        default_search(), conf_path, db_path)
    logger = configuration.logger
    cmd_env = os.environ
    now = time.time()
    site_stats = {'created': now, 'disk': {'use': [], 'mounts': []},
                  'totals': {'all_users': 0, 'active_users': 0, 'vgrids': 0,
                             'archives': 0},
                  'weekly': {'all_users': 0, 'active_users': 0, 'vgrids': 0,
                             'archives': 0},
                  'org_counts': {}, 'domain_counts': {}}

    if sitestats_home == keyword_auto:
        sitestats_home = configuration.sitestats_home

    sitestats_path = None
    if sitestats_home:
        sitestats_path = os.path.join(sitestats_home, 'usagestats-%d' % now)
        if not output_formats:
            output_formats = ['json']
        print("Writing collected site stats in %s" % sitestats_path)

    if not verbose and sitestats_path is None:
        print("Neither verbose nor writing site stats - boring!")

    proc = subprocess_popen(['/bin/df', '-h'] + fs_opts, stdout=subprocess_pipe,
                            env=cmd_env)
    proc.wait()
    for line in proc.stdout.readlines():
        site_stats['disk']['use'].append(line.strip())
    if verbose:
        print("=== Disk Use ===")
        print('\n'.join(site_stats['disk']['use']))

    proc = subprocess_popen(['mount'] + fs_opts, stdout=subprocess_pipe)
    proc.wait()
    for line in proc.stdout.readlines():
        site_stats['disk']['mounts'].append(line.strip())
    if verbose:
        print("=== Disk Mounts ===")
        print('\n'.join(site_stats['disk']['mounts']))
        print("""Where
 * vgrid_files_home is all vgrid shared folders
 * vgrid_private_base/vgrid_public_base are all vgrid web portals
 * user_home is all user home dirs
 * freeze_home is frozen archives from all users
""")

    all_uids = [uid for (uid, user_dict) in all_hits]
    # all_uids.sort()
    #print("DEBUG: %s" % all_uids)
    site_stats['totals']['all_users'] = len(all_uids)
    if verbose:
        print("== Totals ==")
        print("=== Registered Local Users ===")
        print(site_stats['totals']['all_users'])

    search_filter['expire_after'] = now
    (_, active_hits) = search_users(search_filter, conf_path, db_path)
    #only_fields = ['distinguished_name']
    # for (uid, user_dict) in active_hits:
    #    if only_fields:
    #        field_list = [str(user_dict.get(i, '')) for i in only_fields]
    #        print('%s' % ' : '.join(field_list))
    #    print(uid)
    active_uids = [uid for (uid, user_dict) in active_hits]
    # active_uids.sort()
    site_stats['totals']['active_users'] = len(active_uids)
    #print("DEBUG: %s" % active_uids)
    if verbose:
        print("=== Active Local Users ===")
        print(site_stats['totals']['active_users'])

    # Extract dirs recursively in root of vgrid_home
    for (root, dirs, files) in walk(configuration.vgrid_home):
        # Filter dot dirs
        for i in [j for j in dirs if j.startswith('.')]:
            dirs.remove(i)
        if not dirs:
            continue
        #print("DEBUG: %s %s" % (root, dirs))
        site_stats['totals']['vgrids'] += len(dirs)
    if verbose:
        print("=== Registered VGrids ===")
        print(site_stats['totals']['vgrids'])

    # Archives are in root and in user ID subdirs
    archive_count = 0
    for (root, dirs, files) in walk(configuration.freeze_home):
        # Filter dot dirs
        for i in [j for j in dirs if j.startswith('.')]:
            dirs.remove(i)
        sub_dir = root.replace(configuration.freeze_home, '').strip(os.sep)
        sub_parts = sub_dir.split(os.sep)
        if len(sub_parts) > 2:
            # Stop recursion
            #print("DEBUG: stop recursion at %s" % root)
            for i in dirs:
                dirs.remove(i)
            continue
        if sub_parts[-1].find('archive-') != -1 and \
                freeze_meta_filename in files:
            #print("DEBUG: %s" % root)
            site_stats['totals']['archives'] += 1
            # Stop recursion
            for i in dirs:
                dirs.remove(i)

    if verbose:
        print("=== Frozen Archives ===")
        print(site_stats['totals']['archives'])

    # TODO: this is inaccurate as it does not apply for e.g. short term peers.
    #       We can eventually switch to the new created and renewed user fields.
    # NOTE: first or repeat signup sets expire field to 365 days into the future.
    # We simply lookup all users with expire more than 358 days from now.
    nearly_a_year = now + (365 - 7) * 24 * 3600
    search_filter = default_search()
    search_filter['expire_after'] = nearly_a_year
    (_, reg_hits) = search_users(search_filter, conf_path, db_path)
    reg_uids = [uid for (uid, user_dict) in reg_hits]
    # reg_uids.sort()
    site_stats['weekly']['register_users'] = len(reg_uids)

    if verbose:
        print("== This Week ==")
        print("=== Registered and Renewed Local Users ===")
        print(site_stats['weekly']['register_users'])

    a_week_ago = now - 7 * 24 * 3600
    search_filter = default_search()
    search_filter['expire_after'] = a_week_ago
    search_filter['expire_before'] = now
    (_, exp_hits) = search_users(search_filter, conf_path, db_path)
    exp_uids = [uid for (uid, user_dict) in exp_hits]
    # exp_uids.sort()
    site_stats['weekly']['expire_users'] = len(exp_uids)
    if verbose:
        print("=== Recently expired Local Users ===")
        print(site_stats['weekly']['expire_users'])

    # NOTE: no maxdepth since nested vgrids are allowed, mindepth is known for target, however
    # NOTE: vgrid_home/X ctime also gets updated on any file changes in that dir
    for (root, dirs, files) in walk(configuration.vgrid_home):
        # Filter dot dirs
        for i in [j for j in dirs if j.startswith('.')]:
            dirs.remove(i)
        if root == configuration.vgrid_home:
            continue
        root_mtime = os.path.getmtime(root)
        if root_mtime < a_week_ago:
            continue
        #print("DEBUG: %s" % root)
        site_stats['weekly']['vgrids'] += 1

    if verbose:
        print("=== Registered and Updated VGrids ===")
        print(site_stats['weekly']['vgrids'])

    # NOTE: meta.pck file never changes for archives
    # TODO: update to fit only new client_id location when migrated
    for (root, dirs, files) in walk(configuration.freeze_home):
        # Filter dot dirs
        for i in [j for j in dirs if j.startswith('.')]:
            dirs.remove(i)
        sub_dir = root.replace(configuration.freeze_home, '').strip(os.sep)
        sub_parts = sub_dir.split(os.sep)
        if len(sub_parts) > 3:
            # Stop recursion
            for i in dirs:
                dirs.remove(i)
            continue
        if sub_parts[-1].find('archive-') == -1 or \
                not freeze_meta_filename in files:
            continue
        meta_path = os.path.join(root, freeze_meta_filename)
        meta_mtime = os.path.getmtime(meta_path)
        if meta_mtime > a_week_ago and meta_mtime < now:
            site_stats['weekly']['archives'] += 1
            #print("DEBUG: %s" % root)

    if verbose:
        print("=== Frozen Archives ===")
        print(site_stats['weekly']['archives'])

    # Organisation and email domain stats
    search_filter = default_search()
    (_, all_hits) = search_users(search_filter, conf_path, db_path)

    org_map = {}
    domain_map = {}
    for (uid, user_dict) in all_hits:
        org = user_dict.get('organization', 'UNKNOWN')
        if org not in org_map:
            org_map[org] = 0
        org_map[org] += 1
        email = user_dict.get('email', 'UNKNOWN')
        domain = email.split('@', 1)[1].strip()
        if domain not in domain_map:
            domain_map[domain] = 0
        domain_map[domain] += 1
    site_stats['org_counts'].update(org_map)
    site_stats['domain_counts'].update(domain_map)

    if verbose:
        print("== User Distribution ==")
        print("=== By Organisation ===")
        org_list = site_stats['org_counts'].items()
        org_list.sort()
        for (org, cnt) in org_list:
            print('%d\t%s' % (cnt, org))

        print("=== By Email Domain ===")
        domain_list = site_stats['domain_counts'].items()
        domain_list.sort()
        for (domain, cnt) in domain_list:
            print('%d\t%s' % (cnt, domain))

    if sitestats_path and not write_sitestats(configuration, site_stats,
                                              sitestats_path, output_formats):
        print("Error: writing site stats to %s failed!" % sitestats_path)

    sys.exit(0)
