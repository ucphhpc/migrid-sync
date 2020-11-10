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
from mig.shared.defaults import freeze_meta_filename
from mig.shared.fileio import unpickle, walk
from mig.shared.notification import send_email
from mig.shared.safeeval import subprocess_popen, subprocess_pipe
from mig.shared.useradm import init_user_adm, search_users, default_search


def usage(name='createuser.py'):
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
   -t FS_TYPE          Limit disk stats to mounts of given FS_TYPE
   -u USER_FILE        Read user information from pickle file
   -v                  Verbose output
""" % {'name': name})


if '__main__' == __name__:
    (args, app_dir, db_path) = init_user_adm()
    conf_path = None
    fs_opts = []
    expire = None
    force = False
    verbose = False
    user_file = None
    search_filter = default_search()
    expire_before, expire_after = None, None
    opt_args = 'a:b:c:d:fht:u:v'
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
        elif opt == '-t':
            for fs_type in val.split():
                fs_opts += ['-t', fs_type]
        elif opt == '-u':
            user_file = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            sys.exit(1)

    if conf_path and not os.path.isfile(conf_path):
        print('Failed to read configuration file: %s' % conf_path)
        sys.exit(1)

    (configuration, all_hits) = search_users(default_search(), conf_path, db_path,
                                             verbose)
    logger = configuration.logger
    cmd_env = os.environ

    print("=== Disk Use ===")
    proc = subprocess_popen(['/bin/df', '-h'] + fs_opts, stdout=subprocess_pipe,
                            env=cmd_env)
    proc.wait()
    for line in proc.stdout.readlines():
        print(line.strip())

    print("=== Disk Mounts ===")
    proc = subprocess_popen(['mount'] + fs_opts, stdout=subprocess_pipe)
    proc.wait()
    for line in proc.stdout.readlines():
        print(line.strip())

    print("""Where
 * vgrid_files_home is all vgrid shared folders
 * vgrid_private_base/vgrid_public_base are all vgrid web portals
 * user_home is all user home dirs
 * freeze_home is frozen archives from all users
""")

    now = time.time()

    print("== Totals ==")
    print("=== Registered Local Users ===")
    all_uids = [uid for (uid, user_dict) in all_hits]
    # all_uids.sort()
    #print("DEBUG: %s" % all_uids)
    print(len(all_uids))

    print("=== Active Local Users ===")
    search_filter['expire_after'] = now
    (_, active_hits) = search_users(search_filter, conf_path, db_path, verbose)
    #only_fields = ['distinguished_name']
    # for (uid, user_dict) in active_hits:
    #    if only_fields:
    #        field_list = [str(user_dict.get(i, '')) for i in only_fields]
    #        print('%s' % ' : '.join(field_list))
    #    print(uid)
    active_uids = [uid for (uid, user_dict) in active_hits]
    # active_uids.sort()
    #print("DEBUG: %s" % active_uids)
    print(len(active_uids))

    print("=== Registered VGrids ===")
    # Extract dirs recursively in root of vgrid_home
    vgrid_count = 0
    for (root, dirs, files) in walk(configuration.vgrid_home):
        # Filter dot dirs
        for i in [j for j in dirs if j.startswith('.')]:
            dirs.remove(i)
        if not dirs:
            continue
        #print("DEBUG: %s %s" % (root, dirs))
        vgrid_count += len(dirs)
    print(vgrid_count)

    print("=== Frozen Archives ===")
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
            archive_count += 1
            # Stop recursion
            for i in dirs:
                dirs.remove(i)
    print(archive_count)

    print("== This Week ==")
    print("=== Registered and Renewed Local Users ===")
    # TODO: this is inaccurate as it does not apply for e.g. short term peers.
    #       We can eventually switch to the new created and renewed user fields.
    # NOTE: first or repeat signup sets expire field to 365 days into the future.
    # We simply lookup all users with expire more than 358 days from now.
    nearly_a_year = now + (365 - 7) * 24 * 3600
    search_filter = default_search()
    search_filter['expire_after'] = nearly_a_year
    (_, reg_hits) = search_users(search_filter, conf_path, db_path, verbose)
    reg_uids = [uid for (uid, user_dict) in reg_hits]
    # reg_uids.sort()
    print(len(reg_uids))

    print("=== Recently expired Local Users ===")
    a_week_ago = now - 7 * 24 * 3600
    search_filter = default_search()
    search_filter['expire_after'] = a_week_ago
    search_filter['expire_before'] = now
    (_, exp_hits) = search_users(search_filter, conf_path, db_path, verbose)
    exp_uids = [uid for (uid, user_dict) in exp_hits]
    # exp_uids.sort()
    print(len(exp_uids))

    print("=== Registered and Updated VGrids ===")
    # NOTE: no maxdepth since nested vgrids are allowed, mindepth is known for target, however
    # NOTE: vgrid_home/X ctime also gets updated on any file changes in that dir
    vgrid_count = 0
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
        vgrid_count += 1
    print(vgrid_count)

    print("=== Frozen Archives ===")
    # NOTE: meta.pck file never changes for archives
    # TODO: update to fit only new client_id location when migrated
    archive_count = 0
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
            archive_count += 1
            #print("DEBUG: %s" % root)
    print(archive_count)

    print("== User Distribution ==")
    search_filter = default_search()
    (_, all_hits) = search_users(search_filter, conf_path, db_path, verbose)

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
    print("=== By Organisation ===")
    org_list = org_map.items()
    org_list.sort()
    for (org, cnt) in org_list:
        print('%d\t%s' % (cnt, org))

    print("=== By Email Domain ===")
    domain_list = domain_map.items()
    domain_list.sort()
    for (domain, cnt) in domain_list:
        print('%d\t%s' % (cnt, domain))
