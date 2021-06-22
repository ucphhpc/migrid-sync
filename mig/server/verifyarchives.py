#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# verifyarchives - Search for missing files in user Archives
# Copyright (C) 2021  The MiG Project lead by Brian Vinter
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

"""Verify Archive intergrity by comparing archive cache with actual contents"""

from __future__ import print_function
from __future__ import absolute_import

import datetime
import fnmatch
import getopt
import os
import pickle
import sys
import time

from mig.shared.base import client_dir_id, distinguished_name_to_user
from mig.shared.defaults import freeze_meta_filename, freeze_lock_filename, \
    public_archive_index, public_archive_files, public_archive_doi, \
    keyword_pending, keyword_final


def check_archive_integrity(configuration, user_id, freeze_path, verbose=False):
    """Inspect Archives in freeze_path and compare contents to pickled cache.
    The cache is a list with one dictionary per file using the format:
    {'sha512sum': '...', 'name': 'relpath/to/file.ext',
    'timestamp': 1624273389.482884, 'md5sum': '...', 'sha256sum': '...',
    'sha1sum': '...', 'size': 123247} and where the checksums are only actually
    informative if the user requested them on showfreeze. Thus, just check
    timestamp and size in general.
    """
    if verbose:
        print("Compare cache and contents for %s" % freeze_path)
    cache_path = "%s.cache" % freeze_path
    meta_path = os.path.join(freeze_path, freeze_meta_filename)
    try:
        cache_fd = open(cache_path)
        cache = pickle.load(cache_fd)
        cache_fd.close()
        meta_fd = open(meta_path)
        meta = pickle.load(meta_fd)
        meta_fd.close()
    except Exception as exc:
        print("Could not open archive helpers %s and %s for verification: %s" %
              (cache_path, meta_path, exc))
        return False
    ignore_files = [freeze_lock_filename, freeze_meta_filename, '%s.lock' %
                    freeze_meta_filename, public_archive_index,
                    public_archive_files, public_archive_doi]
    for entry in cache:
        if entry['name'] in ignore_files:
            continue
        archive_path = os.path.join(freeze_path, entry['name'])
        try:
            archived_stat = os.stat(archive_path)
            archived_size = archived_stat.st_size
            archived_created = archived_stat.st_ctime
            archived_modified = archived_stat.st_mtime
            meta_state = meta.get('STATE', keyword_pending)
            if archived_size != entry['size']:
                if meta_state == keyword_final:
                    print("Archive entry %s has wrong size %d (expected %d)" %
                          (archive_path, archived_size, entry['size']))
                    return False
                elif verbose:
                    print("ignore size mismatch on non-final %s" %
                          archive_path)
            elif int(entry['timestamp'] not in [int(archived_created), int(archived_modified)]):
                if meta_state == keyword_final:
                    print("Archive entry %s has wrong timestamp %d / %d (expected %d, %s)" %
                          (archive_path, archived_created, archived_modified,
                           entry['timestamp'], archived_stat))
                    return False
                elif verbose:
                    print("ignore ctime mismatch on non-final %s" %
                          archive_path)
        except Exception as exc:
            print("Archive entry %s failed verification: %s" %
                  (archive_path, exc))
            return False
        if verbose:
            print("Archive entry %s passed verification" % archive_path)
    return True


def usage(name='verifyarchives.py'):
    """Usage help"""

    print("""Verify Archive integrity using cache and actual contents.
Usage:
%(name)s [VERIFY_OPTIONS]
Where VERIFY_OPTIONS may be one or more of:
   -A CREATED_AFTER    Limit to Archives created after CREATED_AFTER (epoch)
   -B CREATED_BEFORE   Limit to Archives created before CREATED_BEFORE (epoch)
   -c CONF_FILE        Use CONF_FILE as server configuration
   -h                  Show this help
   -I CERT_DN          Filter to Archives of user ID (distinguished name pattern)
   -n ARCHIVE_NAME     Filter to specific Archive name(s) (pattern)
   -v                  Verbose output
""" % {'name': name})


if '__main__' == __name__:
    conf_path = None
    verbose = False
    opt_args = 'A:B:c:hI:n:v'
    now = int(time.time())
    created_after, created_before = 0, now
    distinguished_name = '*'
    archive_name = '*'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-A':
            after = now
            if val.startswith('+'):
                after += int(val[1:])
            elif val.startswith('-'):
                after -= int(val[1:])
            else:
                after = int(val)
            created_after = after
        elif opt == '-B':
            before = now
            if val.startswith('+'):
                before += int(val[1:])
            elif val.startswith('-'):
                before -= int(val[1:])
            else:
                before = int(val)
            created_before = before
        elif opt == '-c':
            conf_path = val
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-I':
            distinguished_name = val
        elif opt == '-n':
            archive_name = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            usage()
            sys.exit(0)

    archive_hits = {}
    from mig.shared.conf import get_configuration_object
    configuration = get_configuration_object()
    print("searching for Archives with creation stamp between %d and %d" %
          (created_after, created_before))
    for user_dir in os.listdir(configuration.freeze_home):
        base_path = os.path.join(configuration.freeze_home, user_dir)
        # Skip non-dirs and dirs not matching user IDs
        if not os.path.isdir(base_path) or user_dir.find('+') == -1:
            continue
        user_id = client_dir_id(user_dir)
        user_dict = distinguished_name_to_user(user_id)
        if not fnmatch.fnmatch(user_id, distinguished_name):
            if verbose:
                print("skip Archives for %s not matching owner pattern %s" %
                      (user_id, distinguished_name))
            continue

        for freeze_name in os.listdir(base_path):
            if not fnmatch.fnmatch(freeze_name, "archive-??????"):
                continue
            if not fnmatch.fnmatch(freeze_name, archive_name):
                if verbose:
                    print("filter Archive %s not matching name pattern %s" %
                          (freeze_name, archive_name))
                continue
            freeze_path = os.path.join(base_path, freeze_name)
            created_time = int(os.path.getctime(freeze_path))
            if created_time < created_after or created_time > created_before:
                if verbose:
                    print("skip Archive %s outside creation window %d - %d" %
                          (freeze_name, created_after, created_before))
                continue
            elif verbose:
                print("found %s for %s from %d to verify" %
                      (freeze_name, user_id, created_time))
            archive_hits[user_id] = archive_hits.get(user_id, [])
            archive_hits[user_id].append(freeze_path)

    print("Archive integrity checks:")
    for (user_id, archive_list) in archive_hits.items():
        for freeze_path in archive_list:
            verified = check_archive_integrity(
                configuration, user_id, freeze_path, verbose)
            if verified:
                print("%s [PASS]" % freeze_path)
            else:
                print("%s [FAIL]" % freeze_path)
