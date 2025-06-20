#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# verifyarchives - Search for missing files in user Archives
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

import fnmatch
import getopt
import os
import sys
import time

from mig.shared.base import client_dir_id, distinguished_name_to_user
from mig.shared.defaults import freeze_meta_filename, freeze_lock_filename, \
    public_archive_index, public_archive_files, public_archive_doi, \
    keyword_pending, keyword_final, keyword_any
from mig.shared.freezefunctions import sorted_hash_algos, checksum_file
from mig.shared.serial import load


def fuzzy_match(i, j, offset=2.0):
    """Compare the float values i and j and return true if j is within offset
    value of i.
    Useful for comparing e.g. file timestamps with minor fluctuations due to
    I/O times and rounding.
    """
    return (i - offset < j and j < i + offset)


def check_archive_integrity(configuration, user_id, freeze_path,
                            required_state=keyword_any, verbose=False):
    """Inspect Archives in freeze_path and compare contents to pickled cache.
    The cache is a list with one dictionary per file using the format:
    {'sha512sum': '...', 'name': 'relpath/to/file.ext',
    'timestamp': 1624273389.482884, 'md5sum': '...', 'sha256sum': '...',
    'sha1sum': '...', 'size': 123247} and where the checksums are only actually
    informative if the user requested them on showfreeze. Thus, just check
    timestamp and size in general.
    If required_state argument is passed a given archive state the check also
    fails if the archive is in any other state.
    """
    if verbose:
        print("Compare cache and contents for %s" % freeze_path)
    cache_path = "%s.cache" % freeze_path
    meta_path = os.path.join(freeze_path, freeze_meta_filename)
    ignore_files = [freeze_lock_filename, freeze_meta_filename, '%s.lock' %
                    freeze_meta_filename, public_archive_index,
                    public_archive_files, public_archive_doi]
    # NOTE: if archive has no actual files it has no cache file either
    if not os.path.exists(cache_path):
        archive_list = os.listdir(freeze_path)
        if [i for i in archive_list if not i in ignore_files]:
            print("Archive %s has data content but no file cache in %s" %
                  (freeze_path, cache_path))
            return False
        else:
            return True

    try:
        cache = load(cache_path)
        meta = load(meta_path)
    except Exception as exc:
        print("Could not open archive helpers %s and %s for verification: %s" %
              (cache_path, meta_path, exc))
        return False
    meta_state = meta.get('STATE', keyword_pending)
    if required_state != keyword_any and meta_state != required_state:
        print("Archive in %s is in %r state but check demanded state %r" %
              (freeze_path, meta_state, required_state))
        return False
    for entry in cache:
        if entry['name'] in ignore_files:
            continue
        archive_path = os.path.join(freeze_path, entry['name'])
        try:
            archived_stat = os.stat(archive_path)
            archived_size = archived_stat.st_size
            archived_created = archived_stat.st_ctime
            archived_modified = archived_stat.st_mtime
            if archived_size != entry['size']:
                if meta_state == keyword_final:
                    print("Archive entry %s has wrong size %d (expected %d)" %
                          (archive_path, archived_size, entry['size']))
                    return False
                elif verbose:
                    print("ignore size mismatch on non-final %s" %
                          archive_path)
            # NOTE: we allow a minor time offset to accept various fs hiccups
            elif not fuzzy_match(entry['timestamp'], archived_created) and \
                    not fuzzy_match(entry['timestamp'], archived_modified) and \
                    not fuzzy_match(entry.get('file_mtime', -1), archived_modified):
                if meta_state == keyword_final:
                    print("Archive entry %s has wrong timestamp %f / %f (expected %f, %s)" %
                          (archive_path, archived_created, archived_modified,
                           entry['timestamp'], archived_stat))
                    chksum_verified = False
                    for algo in sorted_hash_algos:
                        chksum = entry.get(algo, '')
                        if not chksum or ' ' in chksum:
                            continue
                        print("Checking that %s of %r matches %r" %
                              (algo, archive_path, chksum))
                        verify_chksum = checksum_file(archive_path, algo,
                                                      max_chunks=-1)
                        if verify_chksum == chksum:
                            chksum_verified = True
                            break
                    if chksum_verified:
                        print("Verified that %s of %r matches %r" %
                              (algo, archive_path, chksum))
                    else:
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
    opt_args = 'A:B:c:hI:n:s:v'
    now = int(time.time())
    created_after, created_before = 0, now
    distinguished_name = '*'
    archive_name = '*'
    required_state = keyword_any
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
        elif opt == '-s':
            required_state = val
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)
            usage()
            sys.exit(0)

    archive_hits = {}
    archive_fails = 0
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
            # NOTE: tempfile increased random part from 6 to 8 chars in py3
            if not fnmatch.fnmatch(freeze_name, "archive-??????") and \
               not fnmatch.fnmatch(freeze_name, "archive-????????"):
                continue
            if not fnmatch.fnmatch(freeze_name, archive_name):
                if verbose:
                    print("filter Archive %s not matching name pattern %s" %
                          (freeze_name, archive_name))
                continue
            freeze_path = os.path.join(base_path, freeze_name)
            created_time = int(round(os.path.getctime(freeze_path)))
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
                configuration, user_id, freeze_path, required_state, verbose)
            if verified:
                print("%s [PASS]" % freeze_path)
            else:
                print("%s [FAIL]" % freeze_path)
                archive_fails += 1
    sys.exit(archive_fails)
