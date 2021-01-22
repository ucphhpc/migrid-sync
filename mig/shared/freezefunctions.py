#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# freezefunctions - freeze archive helper functions
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Freeze archive functions"""
from __future__ import print_function
from __future__ import absolute_import

import base64
import datetime
import json
import os
import sys
import time
from urllib import quote

from mig.shared.base import client_id_dir, distinguished_name_to_user, \
    brief_list, pretty_format_user
from mig.shared.defaults import freeze_meta_filename, freeze_lock_filename, \
    wwwpublic_alias, public_archive_dir, public_archive_index, \
    public_archive_files, public_archive_doi, freeze_flavors, keyword_final, \
    keyword_pending, keyword_updating, keyword_auto, keyword_any, \
    keyword_all, max_freeze_files, archives_cache_filename, \
    freeze_on_tape_filename, archive_marks_dir, csrf_field
from mig.shared.fileio import md5sum_file, sha1sum_file, sha256sum_file, \
    sha512sum_file, supported_hash_algos, write_file, copy_file, copy_rec, \
    move_file, move_rec, remove_rec, delete_file, delete_symlink, \
    makedirs_rec, make_symlink, make_temp_dir, acquire_file_lock, \
    release_file_lock, walk, listdir
from mig.shared.filemarks import get_filemark, update_filemark
from mig.shared.html import get_xgi_html_preamble, get_xgi_html_footer, \
    man_base_js, themed_styles, themed_scripts, tablesorter_pager
from mig.shared.pwhash import make_path_hash
from mig.shared.serial import load, dump

TARGET_ARCHIVE = 'ARCHIVE'
TARGET_PATH = 'PATH'
ARCHIVE_PREFIX = 'archive-'
CACHE_EXT = ".cache"
__chksum_unset = 'please request explicitly'
__auto_meta = [('CREATOR', 'Creator'), ('CREATED_TIMESTAMP', 'Date')]
__public_meta = [('AUTHOR', 'Author(s)'), ('NAME', 'Title'),
                 ('DESCRIPTION', 'Description')]
__meta_archive_internals = [freeze_meta_filename, freeze_lock_filename]
__public_archive_internals = [public_archive_index, public_archive_files,
                              public_archive_doi]


def brief_freeze(freeze_dict):
    """Returns a version of freeze_dict where the optional FILES list is
    restricted in length with the brief_list helper function to avoid spamming
    log excessively.
    """
    brief_dict = {}
    brief_dict.update(freeze_dict)
    if brief_dict.get('FILES', False):
        brief_dict['FILES'] = brief_list(brief_dict['FILES'])
    return brief_dict


def public_freeze_id(freeze_dict, configuration):
    """Translate internal freeze_id to a public identifier used in the URL when
    publishing frozen archives. I.e. map to new client_id sub-dir for recent
    archives or fall back to the legacy location directly in freeze_home.
    For legacy archives we used url safe base64 encoding and for recent
    archives we've switched to a 128-bit hash of the unique archive path to
    avoid URL collisions.
    """
    _logger = configuration.logger
    _logger.debug("lookup public id for %s" % brief_freeze(freeze_dict))

    # NOTE: We used to store all archives in a single shared folder for the
    #       original 1st format. This prevented collisions but had the drawback
    #       that lookup grew extremely slow with many archives.
    #       Then we decided to split up archive storage into user-specific
    #       subdirs in the 2nd format and explicitly added a PERSONAL=True
    #       field to be able to distinguish. Due to a bug the public_freeze_id
    #       was not in effect modified to take the user-specific subdir into
    #       account in this 2nd format, which potentially could result in ID
    #       collisions. We fixed the bug and introduced the 3rd format where
    #       user subdir and freeze ID is used as a identifier and marked all
    #       newer archives fixed with a FORMAT=2 field in order to handle
    #       them properly without breaking backward compatibility.

    # TODO: remove broken FORMAT < 2 with potential collisions when possible!
    if not freeze_dict.get('PERSONAL', False) or \
            freeze_dict.get('FORMAT', 1) < 2:
        return base64.urlsafe_b64encode(freeze_dict['ID'])
    # For all current archives we use unique client_id/freeze_id as ID and hash
    # it to a shorter fixed-size but safe version in line with doc string.
    client_dir = client_id_dir(freeze_dict['CREATOR'])
    location = os.path.join(client_dir, freeze_dict['ID'])
    return make_path_hash(configuration, location)


def published_dir(freeze_dict, configuration):
    """Translate internal freeze_id to a published archive dir"""
    return os.path.join(configuration.wwwpublic, public_archive_dir,
                        public_freeze_id(freeze_dict, configuration))


def published_url(freeze_dict, configuration, target=public_archive_index):
    """Translate internal freeze_id to a published archive URL. The optional
    target argument is used to request a specific archive helper instead of
    the landing page.
    """
    base_url = configuration.migserver_http_url
    if configuration.migserver_https_sid_url:
        base_url = configuration.migserver_https_sid_url
    return os.path.join(base_url, 'public', public_archive_dir,
                        public_freeze_id(freeze_dict, configuration),
                        target)


def build_freezeitem_object(configuration, freeze_dict, summary=False,
                            pending_updates=False):
    """Build a frozen archive object based on input freeze_dict.
    The optional summary argument can be used to build just a archive summary
    rather than the full dictionary of individual file details.
    The optional pending_updates is simply inserted as-is.
    """
    freeze_id = freeze_dict['ID']
    flavor = freeze_dict.get('FLAVOR', 'freeze')
    if summary:
        freeze_files = len(freeze_dict.get('FILES', []))
    else:
        freeze_files = []
        for file_item in freeze_dict['FILES']:
            quoted_name = quote(file_item['name'])
            file_ext = os.path.splitext(file_item['name'])[1].lstrip('.')
            type_icon = "fileicon"
            if file_ext:
                type_icon += " ext_%s" % file_ext
            showfile_link = {
                'object_type': 'link',
                'destination': 'showfreezefile.py?freeze_id=%s;path=%s' %
                (freeze_dict['ID'], quoted_name),
                'class': '%s iconleftpad iconspace' % type_icon,
                'title': 'Show archive file %(name)s' % file_item,
                'text': ''
            }
            int_timestamp = int(file_item['timestamp'])
            # NOTE: datetime is not json-serializable so we force to string
            dt_timestamp = datetime.datetime.fromtimestamp(int_timestamp)
            str_timestamp = "%s" % dt_timestamp
            # NOTE: xmlrpc is limited to 32-bit ints so force size to string
            str_size = "%(size)s" % file_item
            entry = {
                'object_type': 'frozenfile',
                'name': file_item['name'],
                'showfile_link': showfile_link,
                'timestamp': int_timestamp,
                'date': str_timestamp,
                'size': str_size,
            }
            # Users may delete pending or non permanent archives
            if freeze_dict.get('STATE', keyword_final) != keyword_final or \
                    flavor not in configuration.site_permanent_freeze:
                delfile_link = {
                    'object_type': 'link', 'destination':
                    "javascript: confirmDialog(%s, '%s', %s, %s);" %
                    ('delfreeze', 'Really remove %s from %s?' %
                     (quoted_name, freeze_id), 'undefined',
                     "{freeze_id: '%s', flavor: '%s', 'path': '%s'}" %
                     (freeze_id, flavor, quoted_name)),
                    'class': 'removelink iconleftpad iconspace', 'title':
                    'Remove %s from %s' % (quoted_name, freeze_id),
                    'text': ''
                }
                entry['delfile_link'] = delfile_link
            for algo in supported_hash_algos():
                chksum_field = '%ssum' % algo
                entry[chksum_field] = file_item.get(chksum_field,
                                                    __chksum_unset)
            freeze_files.append(entry)

    created_timetuple = freeze_dict['CREATED_TIMESTAMP'].timetuple()
    created_asctime = time.asctime(created_timetuple)
    created_epoch = time.mktime(created_timetuple)
    freeze_obj = {
        'object_type': 'frozenarchive',
        'id': freeze_dict['ID'],
        'name': freeze_dict['NAME'],
        'description': freeze_dict['DESCRIPTION'],
        'creator': freeze_dict['CREATOR'],
        'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
                                                        created_asctime),
        'state': freeze_dict.get('STATE', keyword_final),
        'frozenfiles': freeze_files,
        'pending_updates': pending_updates
    }

    for field in ('author', 'department', 'organization', 'publish',
                  'publish_url', 'flavor'):
        if not freeze_dict.get(field.upper(), None) is None:
            freeze_obj[field] = freeze_dict[field.upper()]
    # NOTE: datetime is not json-serializable so we force to string
    for field in ('location', ):
        if not freeze_dict.get(field.upper(), None) is None:
            freeze_obj[field] = [(i, str(j))
                                 for (i, j) in freeze_dict[field.upper()]]
    return freeze_obj


def parse_time_delta(str_value):
    """Translate a time string into a datetime.timedelta object. If the
    str_value is an integer without unit it is interpreted as a number of
    minutes. Otherwise a value and one of the common time units like m(inute),
    h(our), d(ay) and w(eek) is expected.
    """
    default_unit = 'm'
    if str_value.isdigit():
        count, unit = int(str_value), default_unit
    else:
        count, unit = int(str_value[:-1]), str_value[-1]
    if unit == 'm':
        multiplier = 1
    elif unit == 'h':
        multiplier = 60
    elif unit == 'd':
        multiplier = 24*60
    elif unit == 'w':
        multiplier = 7*24*60
    minutes = multiplier * count
    return datetime.timedelta(minutes=minutes)


def parse_isoformat(str_value):
    """Translate a ISO8601 string like 2020-09-30T15:51:17+0200 into a datetime
    object. This is a convenience wrapper using datetime.strptime until we get
    native datetime.fromisoformat() in python 3.7+
    Please note that it completely ignores timezone offset assuming it matches
    local timezone.
    """
    format_str = "%Y-%m-%dT%H:%M:%S"
    # Simply ignore timezone offset expecting it to match local timezone
    if len(str_value) > 19:
        stripped = str_value[:19]
    else:
        stripped = str_value
    return datetime.datetime.strptime(stripped, format_str)


def load_cached_meta(configuration, client_id, freeze_id=keyword_all):
    """Helper to fetch cached metadata dictionary for freeze_id archive of
    client_id. Uses a private dictionary mapping freeze_id to meta data dicts
    in the user_cache subdir for the user.
    The default freeze_id of keyword_all means return complete cache dictionary
    and a specific freeze_id returns only that entry or None if it doesn't
    exist.
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    user_cache = os.path.join(configuration.user_cache, client_dir)
    archives_cache = os.path.join(user_cache, archives_cache_filename)
    lock_path = "%s.lock" % archives_cache
    _logger.debug('load archives cache %s' % archives_cache)
    lock_handle = None
    try:
        lock_handle = acquire_file_lock(lock_path, exclusive=False)
        frozen_cache = load(archives_cache)
    except Exception as err:
        frozen_cache = {}
        _logger.warning('could not load freeze cache %s: %s' %
                        (archives_cache, err))
    if lock_handle:
        release_file_lock(lock_handle)
    if freeze_id == keyword_all:
        return frozen_cache
    return frozen_cache.get(freeze_id, None)


def update_cached_meta(configuration, client_id, freeze_id, freeze_meta):
    """Helper to update cached metadata dictionary for freeze_id archive of
    client_id. Uses a private dictionary mapping freeze_id to meta data dicts
    in the user_cache subdir for the user.
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    user_cache = os.path.join(configuration.user_cache, client_dir)
    archives_cache = os.path.join(user_cache, archives_cache_filename)
    lock_path = "%s.lock" % archives_cache
    _logger.debug('load archives cache %s' % archives_cache)
    lock_handle = None
    try:
        lock_handle = acquire_file_lock(lock_path, exclusive=True)
        if os.path.exists(archives_cache):
            frozen_cache = load(archives_cache)
        else:
            frozen_cache = {}
        frozen_cache[freeze_id] = freeze_meta
        dump(frozen_cache, archives_cache)
        update_status = True
    except Exception as err:
        update_status = False
        _logger.warning('could not update %s in freeze cache %s: %s' %
                        (freeze_id, archives_cache, err))
    if lock_handle:
        release_file_lock(lock_handle)
    return update_status


def list_frozen_archives(configuration, client_id, strict_owner=False,
                         caching=False):
    """Find all frozen_archives owned by user. We used to store all archives
    directly in freeze_home, but have switched to client_id sub dirs since they
    are personal anyway. Look in the client_id folder first.
    If strict_owner is requested the list will only include archives where the
    CREATOR meta field matches client_id. This may leave out archives for
    renamed users or any future shared archives.
    The optional caching argument specifies whether any cached version should
    unconditionally be used.
    """
    _logger = configuration.logger
    # NOTE: we rely on quite lax cache locking here as it's single user cache
    #       and we should get eventual consistency anyway
    frozen_cache = load_cached_meta(configuration, client_id)
    if caching and frozen_cache:
        return (True, frozen_cache.keys())

    frozen_list = []
    dir_content = []

    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    for archive_home in (user_archives, configuration.freeze_home):
        try:
            dir_content += listdir(archive_home)
        except Exception:
            if not makedirs_rec(archive_home, configuration):
                _logger.error(
                    'could not able to create directory %s' % archive_home)
                return (False, "archive setup is broken")

    for entry in dir_content:

        # Skip dot files/dirs and cache entries

        if not entry.startswith(ARCHIVE_PREFIX) or entry.endswith(CACHE_EXT):
            continue
        if is_frozen_archive(client_id, entry, configuration):

            # entry is a frozen archive - check ownership

            freeze_id = entry

            (meta_status, meta_out) = get_frozen_meta(client_id, freeze_id,
                                                      configuration, caching)
            if not meta_status:
                _logger.warning("skip archive %s without metadata" % freeze_id)
                continue
            if strict_owner and meta_out['CREATOR'] != client_id:
                _logger.warning("skip archive %s with wrong owner (%s)" %
                                (freeze_id, client_id))
                continue
            frozen_list.append(freeze_id)
            if not freeze_id in frozen_cache:
                update_cached_meta(configuration, client_id, freeze_id,
                                   meta_out)
        else:
            _logger.warning('%s in %s is not a directory, move it?' %
                            (entry, configuration.freeze_home))
    return (True, frozen_list)


def is_frozen_archive(client_id, freeze_id, configuration):
    """Check that freeze_id is an existing frozen archive. I.e. that it is
    available either in the new client_id sub-dir or directly in the legacy
    freeze_home location. Importantly in the latter case it MUST have the right
    owner.
    We do accept owner differences for archives in the new layout, because they
    should only ever end up like that due to edituser where we don't change
    published archive owner due to conistency considerations.
    """
    _logger = configuration.logger
    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    for archive_home in (user_archives, configuration.freeze_home):
        freeze_path = os.path.join(archive_home, freeze_id)
        if os.path.isdir(freeze_path) and \
                os.path.isfile(os.path.join(freeze_path, freeze_meta_filename)):
            # NOTE: we MUST check owner for legacy archives for access control
            if archive_home == configuration.freeze_home:
                (meta_status, meta_out) = get_frozen_meta(client_id, freeze_id,
                                                          configuration)
                if not meta_status:
                    _logger.warning("skip archive %s with broken metadata" %
                                    freeze_id)
                    continue
                if meta_out['CREATOR'] != client_id:
                    _logger.warning("skip old archive %s with wrong owner %s"
                                    % (freeze_id, meta_out['CREATOR']))
                    continue
            return True
    return False


def mark_archives_modified(configuration, client_id, freeze_id, when):
    """Make file markers to tell other callers about changed or new archives.
    Makes a marker for the given freeze_id plus a shared ANY archive.
    """
    client_dir = client_id_dir(client_id)
    base_dir = os.path.join(configuration.mig_system_run, archive_marks_dir,
                            client_dir)
    # NOTE: always update shared ANY marker, too
    if freeze_id != keyword_any:
        update_filemark(configuration, base_dir, keyword_any, when)
    return update_filemark(configuration, base_dir, freeze_id, when)


def pending_archives_update(configuration, client_id, freeze_id=keyword_any):
    """Check if archive with freeze_id for client_id indicates a pending
    update. The default is to check for any archive if no explicit freeze_id
    is provided.
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    base_dir = os.path.join(configuration.mig_system_run,
                            archive_marks_dir, client_dir)
    last_changed = get_filemark(configuration, base_dir, freeze_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    user_cache = os.path.join(configuration.user_cache, client_dir)
    archives_cache = os.path.join(user_cache, archives_cache_filename)
    cache_changed = 0
    if os.path.exists(archives_cache):
        cache_changed = os.path.getmtime(archives_cache)
    if last_changed is None:
        _logger.debug("missing archive change marker for %s - update" %
                      client_id)
        # NOTE: set last changed now to force update check first time
        last_changed = time.time()
        update_filemark(configuration, base_dir, freeze_id, last_changed)
    if cache_changed < last_changed:
        _logger.debug("stale cache or missing archive marker for %s - update" %
                      client_id)
        return True
    else:
        return False


def get_frozen_meta(client_id, freeze_id, configuration, caching=False):
    """Helper to fetch dictionary of metadata for a frozen archive. I.e. load
    the data either from the new client_id sub-dir or directly from the legacy
    freeze_home location.
    The optional caching argument toggles unconditional load from any cache.
    """
    _logger = configuration.logger
    freeze_dict = {}
    if caching:
        freeze_dict = load_cached_meta(configuration, client_id, freeze_id)
    if freeze_dict:
        return (True, freeze_dict)
    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    for archive_home in (user_archives, configuration.freeze_home):
        meta_path = os.path.join(archive_home, freeze_id,
                                 freeze_meta_filename)
        if not os.path.isfile(meta_path):
            continue
        lock_path = os.path.join(archive_home, freeze_id,
                                 freeze_lock_filename)
        meta_lock = acquire_file_lock(lock_path, exclusive=False)
        freeze_dict = load(meta_path)
        release_file_lock(meta_lock)
        if freeze_dict:
            break
    if freeze_dict:
        update_cached_meta(configuration, client_id, freeze_id, freeze_dict)
        return (True, freeze_dict)
    return (False, 'Could not open metadata for frozen archive %s' % freeze_id)


def get_frozen_files(client_id, freeze_id, configuration,
                     checksum_list=['md5'], max_chunks=-1,
                     force_refresh=False):
    """Helper to list names and stats for files in a frozen archive.
    I.e. lookup the contents of an achive either in the new client_id sub-dir
    or directly in the legacy freeze_home location.
    The optional checksum_list arguments can be used to switch between
    potentially heavy checksum calculation e.g. when used in freezedb.
    By default entire files are checksummed for any algos in checksum_list.
    The optional force_refresh flag can be used to refresh cached values even
    if meta file did not change since last call. This is helpful to track
    progress in big file copies/uploads.
    """
    _logger = configuration.logger
    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    found, arch_dir = False, ''
    for archive_home in (user_archives, configuration.freeze_home):
        arch_dir = os.path.join(archive_home, freeze_id)
        if os.path.isdir(arch_dir):
            found = True
            break
    if not found:
        return (False, 'Could not open frozen archive %s' % freeze_id)
    # NOTE: this is the files-only cache stored in ARCHIVE.cache
    cache_path = "%s%s" % (arch_dir, CACHE_EXT)
    meta_path = os.path.join(arch_dir, freeze_meta_filename)
    file_map = {}
    needs_update = False
    try:
        cached = []
        if os.path.isfile(cache_path):
            cached = load(cache_path)
        if cached:
            if os.path.getmtime(cache_path) < os.path.getmtime(meta_path):
                _logger.debug("files cache is older than meta for %s in %s" %
                              (freeze_id, cache_path))
                needs_update = True
            elif checksum_list:
                for checksum in checksum_list:
                    if [entry['name'] for entry in cached if
                        entry.get("%ssum" % checksum, __chksum_unset)
                            == __chksum_unset]:
                        needs_update = True
                        break
            elif force_refresh:
                needs_update = True

            if not needs_update:
                _logger.debug("using cached info for %s in %s" % (freeze_id,
                                                                  cache_path))
                return (True, cached)
            _logger.info("insufficient cached info for %s in %s" %
                         (freeze_id, cache_path))
            file_map = dict([(entry['name'], entry) for entry in cached])
        else:
            _logger.debug("no cached files info in %s" % cache_path)
    except Exception as err:
        _logger.warning("failed to load files cache in %s: %s" %
                        (cache_path, err))
    # Walk archive and fill file data using any cached fields for speed
    # TODO: switch to combined list and stat with scandir instead of walk?
    files = []
    updates = 0
    for (root, _, filenames) in walk(arch_dir):
        for name in filenames:
            if name in __meta_archive_internals + __public_archive_internals:
                continue
            frozen_path = os.path.join(root, name)
            _logger.debug("refresh cache for file %s" % frozen_path)
            rel_path = os.path.join(root.replace(arch_dir, '', 1), name)
            rel_path = rel_path.lstrip(os.sep)
            entry = file_map.get(rel_path, {})
            if not entry or needs_update:
                entry['name'] = entry.get('name', rel_path)
                file_ctime, file_size = -1, -1
                try:
                    file_ctime = os.path.getctime(frozen_path)
                    file_size = os.path.getsize(frozen_path)
                except Exception as err:
                    _logger.warning("failed to update cached %s stats: %s" %
                                    (frozen_path, err))
                entry['timestamp'] = file_ctime
                entry['size'] = file_size
                updates += 1

            for algo in supported_hash_algos():
                chksum_field = '%ssum' % algo
                entry[chksum_field] = entry.get(chksum_field, __chksum_unset)
            # Update checksum (entire file) if requested and not there already
            if 'md5' in checksum_list and entry['md5sum'] == __chksum_unset:
                entry['md5sum'] = md5sum_file(frozen_path,
                                              max_chunks=max_chunks)
                updates += 1
            elif 'sha1' in checksum_list and \
                    entry['sha1sum'] == __chksum_unset:
                entry['sha1sum'] = sha1sum_file(frozen_path,
                                                max_chunks=max_chunks)
                updates += 1
            elif 'sha256' in checksum_list and \
                    entry['sha256sum'] == __chksum_unset:
                entry['sha256sum'] = sha256sum_file(frozen_path,
                                                    max_chunks=max_chunks)
                updates += 1
            elif 'sha512' in checksum_list and \
                    entry['sha512sum'] == __chksum_unset:
                entry['sha512sum'] = sha512sum_file(frozen_path,
                                                    max_chunks=max_chunks)
                updates += 1
            files.append(entry)
    if updates > 0:
        # Save updated cache
        try:
            dump(files, cache_path)
            _logger.info("saved files cache in %s" % cache_path)
        except Exception as err:
            _logger.warning("failed to save files cache in %s: %s" %
                            (cache_path, err))
    return (True, files)


def get_frozen_archive(client_id, freeze_id, configuration,
                       checksum_list=['md5'], caching=False):
    """Helper to extract all details for a frozen archive. I.e. extract the
    contents of the archive either in the new client_id sub-dir or directly in
    the legacy freeze_home location.
    The optional checksum_list argument can be used to switch between
    potentially heavy checksum calculation e.g. when used in freezedb.
    The optional caching argument specifies whether any cached version should
    unconditionally be used.
    """
    _logger = configuration.logger
    if not is_frozen_archive(client_id, freeze_id, configuration):
        return (False, 'no such frozen archive id: %s' % freeze_id)

    (meta_status, meta_out) = get_frozen_meta(client_id, freeze_id,
                                              configuration, caching)
    if not meta_status:
        return (False, 'failed to extract meta data for %s' % freeze_id)

    # Keep refreshing cache while archive operations are in progress
    if caching:
        cache_refresh = False
    elif meta_out.get('STATE', keyword_final) == keyword_updating:
        cache_refresh = True
    else:
        cache_refresh = False
    _logger.debug("get frozen files for %s with refresh: %s" %
                  (freeze_id, cache_refresh))
    (files_status, files_out) = get_frozen_files(client_id, freeze_id,
                                                 configuration, checksum_list,
                                                 force_refresh=cache_refresh)
    if not files_status:
        return (False, 'failed to extract files for %s' % freeze_id)
    _logger.debug("loaded files for '%s': %s" %
                  (freeze_id, brief_list(files_out)))
    freeze_dict = {'ID': freeze_id}
    freeze_dict.update(meta_out)
    freeze_dict['FILES'] = files_out
    # NOTE: optional marker from actual tape writing
    if configuration.site_freeze_to_tape and configuration.freeze_tape:
        arch_dir = get_frozen_root(client_id, freeze_id, configuration)
        tape_marker_path = os.path.join(arch_dir, freeze_on_tape_filename)
        tape_marker_path = tape_marker_path.replace(
            configuration.freeze_home, configuration.freeze_tape)
        if os.path.isfile(tape_marker_path):
            try:
                with open(tape_marker_path) as marker_fd:
                    on_tape_value = marker_fd.readline().strip()
                # NOTE: the required date format is ISO8601
                #       like 2020-09-30T15:51:17+0200)
                on_tape_date = parse_isoformat(on_tape_value)
                # NOTE: mark legacy tape deadline entry to current naming
                last = freeze_dict['LOCATION'][-1]
                if last[0] == 'tape':
                    freeze_dict['LOCATION'][-1] = ('tape deadline', last[1])
                freeze_dict['LOCATION'].append(('tape', on_tape_date))
                _logger.debug("added on tape date for '%s': %s" %
                              (freeze_id, on_tape_date))
            except Exception as err:
                _logger.error("failed to extract on tape date from %s: %s" %
                              (tape_marker_path, err))

    return (True, freeze_dict)


def get_frozen_root(client_id, freeze_id, configuration):
    """Lookup the directory root of freeze_id of client_id"""
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    archive_path = os.path.join(configuration.freeze_home, client_dir)
    if freeze_id:
        archive_path = os.path.join(archive_path, freeze_id)
    return archive_path


def init_frozen_archive(freeze_meta, client_id, configuration):
    """Helper to create a basic archive dir for a new archive from client_id.
    Creates a suitable random tempdir and saves a pickle with meta data there.
    Returns the full freeze_dict including the unique ID.
    """
    _logger = configuration.logger
    user_archives = get_frozen_root(client_id, '', configuration)
    try:
        arch_dir = make_temp_dir(prefix=ARCHIVE_PREFIX,
                                 dir=user_archives)
    except Exception as err:
        _logger.error("create dir for %s from %s failed: %s" % (freeze_meta,
                                                                client_id, err))
        return (False, 'Error preparing new frozen archive: %s' % err)

    freeze_id = os.path.basename(arch_dir)
    now = datetime.datetime.now()
    _logger.debug("created archive dir for %s" % freeze_id)
    freeze_dict = {
        'CREATED_TIMESTAMP': now,
        'CREATOR': client_id,
        'PERSONAL': True,
        'FORMAT': 2,
    }
    freeze_dict.update(freeze_meta)
    freeze_dict.update({'ID': freeze_id,
                        'STATE': freeze_dict.get('STATE', keyword_pending)})

    (save_status, save_res) = save_frozen_meta(freeze_dict, arch_dir,
                                               configuration)
    if not save_status:
        _logger.error(save_res)
        remove_rec(arch_dir, configuration)
        return (False, 'Error in init frozen archive info: %s' % err)
    return (True, freeze_dict)


def copy_frozen_files(freeze_id, arch_dir, freeze_copy, configuration):
    """Copy user files into archive"""
    _logger = configuration.logger
    copied_files = []
    _logger.debug("copy for %s: %s" % (freeze_id, freeze_copy))
    for (real_source, rel_dst) in freeze_copy:
        freeze_path = os.path.join(arch_dir, rel_dst)
        copied_files.append(rel_dst)
        _logger.debug("copy %s to %s" % (real_source, freeze_path))
        if os.path.isdir(real_source):
            (status, msg) = copy_rec(real_source, freeze_path, configuration)
            if not status:
                _logger.error("copy %s recursively to %s: %s" %
                              (real_source, freeze_path, msg))
                return (False, 'Error copying files to archive')
        else:
            (status, msg) = copy_file(real_source, freeze_path, configuration)
            if not status:
                _logger.error("copy %s to %s: %s" %
                              (real_source, freeze_path, msg))
                return (False, 'Error copying file to archive')
    return (True, copied_files)


def move_frozen_files(freeze_id, arch_dir, freeze_move, configuration):
    """Move uploaded files into archive"""
    _logger = configuration.logger
    moved_files = []
    _logger.debug("move for %s: %s" % (freeze_id, freeze_move))
    for (real_source, rel_dst) in freeze_move:
        # Strip relative dir from move targets
        freeze_path = os.path.join(arch_dir, os.path.basename(rel_dst))
        moved_files.append(os.path.basename(rel_dst))
        _logger.debug("move %s to %s" % (real_source, freeze_path))
        if os.path.isdir(real_source):
            (status, msg) = move_rec(real_source, freeze_path, configuration)
            if not status:
                _logger.error("move %s recursively to %s: %s" %
                              (real_source, freeze_path, msg))
                return (False, 'Error moving files into archive')
        else:
            (status, msg) = move_file(real_source, freeze_path, configuration)
            if not status:
                _logger.error("move %s to %s: %s" %
                              (real_source, freeze_path, msg))
                return (False, 'Error moving file into archive')
    return (True, moved_files)


def upload_frozen_files(freeze_id, arch_dir, freeze_upload, configuration):
    """Save uploaded files into archive"""
    _logger = configuration.logger
    uploaded_files = []
    _logger.info("save %s for %s" % ([i[0] for i in freeze_upload], freeze_id))
    for (filename, contents) in freeze_upload:
        freeze_path = os.path.join(arch_dir, filename)
        uploaded_files.append(filename)
        _logger.debug("save uploaded %s to %s" % (filename, freeze_path))
        if not write_file(contents, freeze_path, _logger):
            _logger.error("write upload %s to %s" % (filename, freeze_path))
            return (False, 'Error saving uploaded files in archive')
    return (True, uploaded_files)


def handle_frozen_files(freeze_id, arch_dir, freeze_copy, freeze_move,
                        freeze_upload, configuration):
    """Take care of all the copy, move and upload file handling"""
    (copy_status, copy_res) = copy_frozen_files(freeze_id, arch_dir,
                                                freeze_copy, configuration)
    if not copy_status:
        return (copy_status, copy_res)
    (move_status, move_res) = move_frozen_files(freeze_id, arch_dir,
                                                freeze_move, configuration)
    if not move_status:
        return (move_status, move_res)
    (upload_status, upload_res) = upload_frozen_files(freeze_id, arch_dir,
                                                      freeze_upload,
                                                      configuration)
    if not upload_status:
        return (upload_status, upload_res)
    return (True, copy_res + move_res + upload_res)


def format_meta(key, val):
    """Simple helper to mangle meta field display on landing page"""
    out = val
    if key == 'CREATOR':
        # NOTE: when you publish you loose anonymity
        out = pretty_format_user(val, hide_email=False)
    elif key == 'CREATED_TIMESTAMP':
        # Drop microsecond precision
        out = val.replace(microsecond=0)
    return out


def write_landing_page(freeze_dict, arch_dir, frozen_files, cached,
                       configuration):
    """Write a landing page for archive publishing. Depending on archive state
    it will be a draft or the final version.
    """
    _logger = configuration.logger
    freeze_id = freeze_dict['ID']
    published_id = public_freeze_id(freeze_dict, configuration)
    real_pub_dir = published_dir(freeze_dict, configuration)
    real_pub_index = os.path.join(arch_dir, public_archive_index)
    real_pub_files = os.path.join(arch_dir, public_archive_files)
    arch_url = published_url(freeze_dict, configuration)
    files_url = published_url(freeze_dict, configuration, public_archive_files)
    doi_url = published_url(freeze_dict, configuration, public_archive_doi)
    freeze_dict['PUBLISH_URL'] = arch_url
    _logger.debug("create landing page for %s on %s" % (freeze_id, arch_url))
    publish_preamble = ""
    publish_title = "Public Archive: %s" % published_id
    if freeze_dict.get('STATE', keyword_final) == keyword_pending:
        publish_preamble += """
<div class='draft warn_message'>
THIS IS ONLY A DRAFT - EXPLICIT FREEZE IS STILL PENDING!
</div>
"""
        publish_title = "Public Archive Preview: %s" % published_id

    # jquery support for tablesorter
    # table initially sorted by col. 0 (filename)

    refresh_call = 'ajax_showfiles("%s", "%s")' % \
        (freeze_id, ['md5'])
    table_spec = {'table_id': 'frozenfilestable', 'sort_order': '[[0,0]]',
                  'refresh_call': refresh_call}
    (add_import, add_init, add_ready) = man_base_js(configuration,
                                                    [table_spec])
    add_init += """
    /* NOTE: use a URL lookup helper for all URLs to avoid cross-domain ajax
             requests and the resulting rejects when using alias domains.
    */
    function lookup_url(url) {
        var raw_array = url.split('/');
        var relative_url = raw_array.slice(3, raw_array.Length).join('/');
        var current_array = $(location).attr('href').split('/');
        var protocol = current_array[0];
        var fqdn = current_array[2];
        return protocol + '//' + fqdn + '/' + relative_url;
    }
    function ajax_showfiles(freeze_id, checksum_list) {
        var url = lookup_url('%s');
        var tbody_elem = $('#frozenfilestable tbody');
        $(tbody_elem).empty();
        console.debug('Loading files from '+url+' ...');
        $('#ajax_status').html('Loading files ...');
        $('#ajax_status').addClass('spinner iconleftpad');
        var files_req = $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json',
            success: function(jsonRes, textStatus) {
                console.debug('got response from files lookup: '+textStatus);
                console.debug(jsonRes);
                var chunk_size = 200;
                var files_data = '';
                var entry = null;
                var i, j, name;
                /* NOTE: only md5sums really fit page width so hide the rest */
                /* var chksums = ['md5sum', 'sha1sum', 'sha256sum', 'sha512sum']; */
                var chksums = ['md5sum'];
                for (i=0; i < jsonRes.length; i++) {
                    console.debug('found file: '+ jsonRes[i].name);
                    entry = jsonRes[i];
                    files_data += '<tr><td><a href=\"'+entry.name+'\">'+entry.name+'</a></td><td><div class=\"sortkey hidden\">'+entry.timestamp+'</div>'+entry.date+'</td><td>'+entry.size+'</td><td class=\"md5sum hidden\"><pre>'+entry.md5sum+ \
                        '</pre></td><td class=\"sha1sum hidden\"><pre>'+entry.sha1sum+'</pre></td><td class=\"sha256sum hidden\"><pre>'+ \
                            entry.sha256sum+'</pre></td><td class=\"sha512sum hidden\"><pre>'+ \
                                entry.sha512sum+'</pre></td></tr>';
                    /* chunked updates - append after after every chunk_size entries */
                    if (i > 0 && i %% chunk_size === 0) {
                        console.debug('append chunk of ' + \
                                      chunk_size + ' entries');
                        $(tbody_elem).append(files_data);
                        files_data = "";
                    }
                }
                if (files_data) {
                    console.debug('append remaining chunk of ' + (i %% chunk_size) + ' entries');
                    $(tbody_elem).append(files_data);
                }
                /* Inspect first element and enable available checksums */
                if (entry !== null) {
                    for (j=0; j < chksums.length; j++) {
                        name = chksums[j];
                        var sum = $(entry).attr(name);
                        /* console.debug('found '+name+' checksum: '+ sum); */
                        if (sum.indexOf(' ') === -1) {
                            console.debug('show '+name);
                            $('.'+name).show();
                        } else {
                            console.debug('no '+name+' to show');
                        }
                     }
                }

                $('#ajax_status').html('');
                $('#ajax_status').removeClass('spinner iconleftpad');
                $('#frozenfilestable').trigger('update');
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error('files lookup failed: '+ \
                              textStatus+' : '+errorThrown);
                $('#ajax_status').html('No files data available');
                $('#ajax_status').removeClass('spinner iconleftpad');
            }
        });
    }
    function toggle_raw_doi_meta() {
        $('#raw_doi_meta').toggle();
        if ($('#toggle_raw_doi_link').hasClass('doishowdetails')) {
            $('#toggle_raw_doi_link').removeClass('doishowdetails');
            $('#toggle_raw_doi_link').addClass('doihidedetails');
        } else {
            $('#toggle_raw_doi_link').removeClass('doihidedetails');
            $('#toggle_raw_doi_link').addClass('doishowdetails');
        }
    }
    function ajax_showdoi() {
        var url = lookup_url('%s');
        console.debug('loading DOI data from '+url+' ...');
        $('#doicontents').html('Loading DOI data ...');
        $('#doicontents').addClass('spinner iconleftpad');
        var doi_req = $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json',
            success: function(jsonRes, textStatus) {
                console.debug('got response from doi lookup: '+textStatus);
                console.debug(jsonRes);
                var doi_data = '', raw_meta='';
                var doi_url = jsonRes.id;
                var doi = jsonRes.doi;
                var datacite_url = 'https://search.datacite.org/works/'+doi;
                doi_data += '<h4>Archive DOI</h4>';
                doi_data += '<p><a class=\"iconleftpad doilink\" href=\"';
                doi_data += doi_url + '\">'+doi_url+'</a></p>';
                doi_data += '<h4>DataCite Entry</h4>';
                doi_data += '<p>Complete DOI meta data and citation info is ';
                doi_data += 'available in the <a class=\"iconleftpad doisearchlink\"';
                doi_data += 'href=\"' + datacite_url + '\">';
                doi_data += 'DataCite DOI Collection</a>.</p>';
                doi_data += '<h4>DOI Details</h4>';
                raw_meta += JSON.stringify(jsonRes, null, 4);
                $('#doicontents').html(doi_data);
                $('#raw_doi_meta').html(raw_meta);
                $('#doicontents').removeClass('spinner iconleftpad');
                $('#doitoggle').show();
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.info('No DOI data found')
                console.debug('DOI request said: '+ \
                              textStatus+' : '+errorThrown);
                doi_data = 'No DOI data found';
                $('#doicontents').html(doi_data);
                $('#doicontents').removeClass('spinner iconleftpad');
            }
        });
    }
    """ % (files_url, doi_url)
    add_ready += """
    ajax_showdoi('%s');
    %s;
    """ % (freeze_id, refresh_call)
    # Fake manager themed style setup for tablesorter layout with site style
    style_entry = themed_styles(configuration, user_settings={})
    base_style = style_entry.get("base", "")
    advanced_style = style_entry.get("advanced", "")
    skin_style = style_entry.get("skin", "")
    # Fake manager themed script setup for tablesorter use
    script_entry = themed_scripts(configuration)
    script_entry['advanced'] += add_import
    script_entry['init'] += add_init
    script_entry['ready'] += add_ready

    # Use the default preamble to get style, skin and so on right

    contents = get_xgi_html_preamble(configuration, publish_title, "",
                                     style_map=style_entry,
                                     script_map=script_entry,
                                     widgets=False,
                                     userstyle=False,
                                     user_settings={})

    # Manually create modified page start like get_xgi_html_header but
    # using staticpage class for flexible skinning

    contents += """
<body class='staticpage'>
<div id='topspace'>
</div>
<div class='staticpage' id='toplogo'>

<div class='staticpage' id='toplogoleft'>
</div>
<div class='staticpage' id='toplogocenter'>
<img src='%s/banner-logo.jpg' id='logoimagecenter'
     class='staticpage' alt='site logo center'/>
</div>
<div class='staticpage' id='toplogoright'>
</div>
</div>

<div class='contentblock staticpage archive' id='nomenu'>
<div id='migheader'>
</div>
<div class='staticpage' id='content' lang='en'>
""" % configuration.site_skin_base

    # Then fill actual archive page

    auto_line = ''
    auto_map = {'published_id': published_id}
    # TODO: drop meta_label here
    for (meta_key, meta_label) in __auto_meta:
        meta_value = freeze_dict.get(meta_key, '')
        auto_map[meta_key.lower()] = format_meta(meta_key, meta_value)

    auto_line = """This is the public archive with ID %(published_id)s created
on %(created_timestamp)s by %(creator)s.""" % auto_map
    contents += """
%s
<div class='archive-header'>
<p class='archive-autometa archive-box'>%s
</p>
</div>

<div class='archive-metadata'>
<h2 class='staticpage'>Archive Meta Data</h2>
""" % (publish_preamble, auto_line)
    for (meta_key, meta_label) in __public_meta:
        meta_value = freeze_dict.get(meta_key, '')
        if meta_value:
            # Preserve any text formatting in e.g. description
            contents += """<h4 class='staticpage'>%s</h4>
<pre class='archive-%s standardfonts'>%s</pre>
""" % (meta_label, meta_label.lower(), format_meta(meta_key, meta_value))
    contents += """</div>

<div class='archive-doidata'>
<h2 class='staticpage'>Archive DOI Data</h2>
    <div id='doicontents'><!-- filled by AJAX call--></div>
    <div id='doitoggle' class='hidden'>
    <a id='toggle_raw_doi_link' class='iconleftpad doishowdetails'
    href='#' onClick='toggle_raw_doi_meta();'>Show/hide all DOI meta data</a>
    registered with DataCite.
    </div>
    <div id='raw_doi_meta' class='hidden archive-box'>
    <!-- filled by AJAX call-->
    </div>
    """
    contents += """</div>
    """

    # TODO: chunk json files for responsive AJAX load?
    toolbar = tablesorter_pager(configuration)
    contents += """
<div class='archive-filestable'>
<h2 class='staticpage'>Archive Files</h2>
    %s
    <table id='frozenfilestable' class='frozenfiles columnsort'>
        <thead class='title'>
            <tr><th>Name</th><th>Date</th><th>Size</th>
            <th class='md5sum hidden'>MD5 Checksum</th>
            <th class='sha1sum hidden'>SHA1 Checksum</th>
            <th class='sha256sum hidden'>SHA256 Checksum</th>
            <th class='sha512sum hidden'>SHA512 Checksum</th>
            </tr>
        </thead>
        <tbody><!-- rows filled by AJAX call--></tbody>
    </table>
    """ % toolbar
    contents += """</div>
%s
    """ % get_xgi_html_footer(configuration, widgets=False)
    if not make_symlink(arch_dir, real_pub_dir, _logger, force=True) or \
            not write_file(contents, real_pub_index, _logger) or \
            not write_file(json.dumps(cached), real_pub_files, _logger):
        return (False, 'Error making landing page for archive publishing')
    return (True, freeze_dict)


def remove_landing_page(freeze_dict, arch_dir, configuration,
                        allow_missing=False):
    """Remove previously generated landing page. Optional allow_missing can be
    used to silently ignore cases where the archive was never published.
    """
    _logger = configuration.logger
    freeze_id = freeze_dict['ID']
    real_pub_dir = published_dir(freeze_dict, configuration)
    real_pub_index = os.path.join(arch_dir, public_archive_index)
    real_pub_files = os.path.join(arch_dir, public_archive_files)
    if freeze_dict.get('PUBLISH_URL', ''):
        del freeze_dict['PUBLISH_URL']
    _logger.debug("remove landing page for %s" % freeze_id)
    if not delete_symlink(real_pub_dir, _logger, allow_missing=allow_missing) \
       or not delete_file(real_pub_index, _logger, allow_missing=allow_missing)\
       or not delete_file(real_pub_files, _logger, allow_missing=allow_missing):
        return (False, 'Error removing published landing page for archive')
    return (True, freeze_dict)


def save_frozen_meta(freeze_dict, arch_dir, configuration):
    """Save meta data dictionary after updates to archive"""
    _logger = configuration.logger
    freeze_id = freeze_dict['ID']
    _logger.info("update meta for %s" % freeze_id)
    meta_dict = {}
    meta_dict.update(freeze_dict)
    # Do not save files list in meta, we keep it in separate cache
    if meta_dict.get('FILES', ''):
        del meta_dict['FILES']
    meta_path = os.path.join(arch_dir, freeze_meta_filename)
    lock_path = os.path.join(arch_dir, freeze_lock_filename)
    status, reply = True, freeze_dict
    meta_lock = None
    try:
        meta_lock = acquire_file_lock(lock_path)
        dump(meta_dict, meta_path)
    except Exception as err:
        _logger.error("update meta failed: %s" % err)
        status = False
        reply = 'Error saving frozen archive info: %s' % err
    if meta_lock:
        release_file_lock(meta_lock)
    return (status, reply)


def commit_frozen_archive(freeze_dict, arch_dir, configuration):
    """Commit after update to archive"""
    _logger = configuration.logger
    freeze_id = freeze_dict['ID']
    # Mark as saved on disk and hint about any tape archiving schedule
    now = datetime.datetime.now()
    slack = 2
    # Skip microseconds
    on_disk_date = datetime.datetime.now().replace(microsecond=0)
    archive_locations = [('disk', on_disk_date)]
    if freeze_dict.get('STATE', keyword_final) == keyword_final and \
            configuration.site_freeze_to_tape:
        delay = parse_time_delta(configuration.site_freeze_to_tape)
        on_tape_deadline = on_disk_date + delay
        archive_locations.append(('tape deadline', on_tape_deadline))

        # TODO: maintain or calculate total file count and size here
        total_files = freeze_dict.get('TOTALFILES', '?')
        total_size = freeze_dict.get('TOTALSIZE', '?')
        _logger.info("%s archive %s of %s marked %s with %s files of %sb" %
                     (freeze_dict['FLAVOR'], freeze_id, freeze_dict['CREATOR'],
                      freeze_dict['STATE'], total_files, total_size))
        _logger.info("%s archive %s finalized with on-tape deadline %s" %
                     (freeze_dict['FLAVOR'], freeze_id, on_tape_deadline))
    freeze_dict['LOCATION'] = archive_locations
    (save_status, save_res) = save_frozen_meta(freeze_dict, arch_dir,
                                               configuration)
    if not save_status:
        return (save_status, save_res)
    return (True, freeze_dict)


def create_frozen_archive(freeze_meta, freeze_copy, freeze_move,
                          freeze_upload, client_id, configuration):
    """Create or update existing non-persistant archive with provided meta data
    fields and provided freeze_copy files from user home, freeze_move from
    temporary upload dir and freeze_upload files from form.
    Fails if it is an existing archive in the FINAL or UPDATING state.
    Returns a dictionary based on freeze_meta, but with additional existing
    and updated archive values.
    """
    _logger = configuration.logger

    # Create if new and load existing otherwise
    freeze_id = freeze_meta.get('ID', keyword_auto)
    if not freeze_id or freeze_id == keyword_auto:
        existing_archive = False
        (init_status, init_res) = init_frozen_archive(freeze_meta, client_id,
                                                      configuration)
    else:
        existing_archive = True
        (init_status, init_res) = get_frozen_archive(client_id, freeze_id,
                                                     configuration,
                                                     checksum_list=[])

    # Shared handling of above init/load status
    if not init_status:
        _logger.error(init_res)
        return (init_status, init_res)

    # We received the updated freeze_meta dict from init
    freeze_dict = init_res
    freeze_id = freeze_dict['ID']
    if existing_archive:
        # Legacy archives may not have all fields set
        published = freeze_dict.get('PUBLISH', False)
        state = freeze_dict.get('STATE', keyword_final)
        freeze_dict.update(freeze_meta)
    else:
        published = False
        state = freeze_meta['STATE']

    _logger.debug("%s create/update archive with dict: %s" %
                  (client_id, brief_freeze(freeze_dict)))

    # Bail out if user attempts to edit already persistant or changing archive
    if existing_archive:
        if state == keyword_final:
            _logger.error("changes to persistant archive %s for %s refused" %
                          (freeze_id, client_id))
            return (False, "Error: persistant archives cannot be edited")
        elif state == keyword_updating:
            _logger.error("changes to archive %s for %s refused during update"
                          % (freeze_id, client_id))
            return (False, "Error: archives cannot be edited during updates")

    arch_dir = get_frozen_root(client_id, freeze_id, configuration)

    _logger.debug("marking archive %s for update" % freeze_id)
    updating_dict = {}
    updating_dict.update(freeze_dict)
    updating_dict['STATE'] = keyword_updating
    (save_status, save_res) = save_frozen_meta(updating_dict, arch_dir,
                                               configuration)
    if not save_status:
        _logger.error("could not save %s metadata for update: %s" % (freeze_id,
                                                                     save_res))
        return (False, "Error: registering archive for update")

    _logger.debug("marked archive %s for update and proceeding" % freeze_id)
    (files_status, files_res) = handle_frozen_files(freeze_id, arch_dir,
                                                    freeze_copy, freeze_move,
                                                    freeze_upload,
                                                    configuration)
    if not files_status:
        _logger.error(files_res)
        return (files_status, files_res)
    # Merge list of existing files from loaded archive with new ones
    frozen_files = [i['name'] for i in freeze_dict.get('FILES', [])
                    if i['name'] not in __public_archive_internals]
    frozen_files += files_res
    _logger.debug("proceed with frozen_files: %s" % brief_list(frozen_files))

    freeze_entries = len(frozen_files)
    if freeze_entries > max_freeze_files:
        _logger.error("Max file count exceeded in %s for %s: %s" %
                      (freeze_id, client_id, freeze_entries))
        return (False, "Error: Too many archive files (%s), max %s" %
                (freeze_entries, max_freeze_files))

    if state == keyword_final and freeze_entries < 1:
        _logger.error("No files included in %s for %s: %s" %
                      (freeze_id, client_id, freeze_entries))
        return (False, "Error: final archives must have one or more files")

    if freeze_dict.get('PUBLISH', False):
        # NOTE: force cache generation without chksums for immediate use here
        (files_status, cached) = get_frozen_files(client_id, freeze_id,
                                                  configuration, [],
                                                  force_refresh=True)
        if not files_status:
            return (False, 'failed to build cached files for %s' % freeze_id)
        _logger.debug("loaded cached files for '%s': %s" %
                      (freeze_id, brief_list(cached)))
        # Add human-friendly text timestamp
        for i in cached:
            i['date'] = "%s" % \
                datetime.datetime.fromtimestamp(int(i['timestamp']))
        (web_status, web_res) = write_landing_page(freeze_dict, arch_dir,
                                                   frozen_files, cached,
                                                   configuration)
    elif published:
        (web_status, web_res) = remove_landing_page(freeze_dict, arch_dir,
                                                    configuration,
                                                    allow_missing=True)
    else:
        (web_status, web_res) = True, {}

    # Shared handling of above publish status
    if not web_status:
        _logger.error(web_res)
        return (False, web_res)
    # We received publish updates for published landing page
    freeze_dict.update(web_res)

    # Change state back from updating to previous or requested
    _logger.debug("commit archive %s" % freeze_id)
    (commit_status, commit_res) = commit_frozen_archive(freeze_dict, arch_dir,
                                                        configuration)
    if not commit_status:
        _logger.error(commit_res)
        return (False, commit_res)
    # We received location updates from commit
    freeze_dict = commit_res
    mark_archives_modified(configuration, client_id, freeze_id, time.time())
    return (True, freeze_dict)


def delete_archive_files(freeze_dict, client_id, path_list, configuration):
    """Delete one or more files specified in path_list from an existing archive
    at the low level. Assumes previous checking of proper ownership and
    persistance restrictions as well as all paths being inside archive.
    """
    _logger = configuration.logger
    freeze_id = freeze_dict['ID']
    arch_dir = get_frozen_root(client_id, freeze_id, configuration)
    status, msg_list, deleted = True, [], []
    _logger.debug("marking archive %s for update in file delete" % freeze_id)
    updating_dict = {}
    updating_dict.update(freeze_dict)
    updating_dict['STATE'] = keyword_updating
    (save_status, save_res) = save_frozen_meta(updating_dict, arch_dir,
                                               configuration)
    if not save_status:
        _logger.error("could not save %s metadata for update: %s" % (freeze_id,
                                                                     save_res))
        return (False, "Error: marking archive for update")

    _logger.debug("marked archive %s for update and proceeding" % freeze_id)

    for path in path_list:
        arch_path = os.path.join(arch_dir, path)
        if os.path.isdir(arch_path) and not remove_rec(arch_path, configuration):
            _logger.error("could not remove archive dir %s for %s" %
                          (arch_path, freeze_id))
            status = False
            msg_list.append('Error deleting archive %s folder %s' %
                            (freeze_id, path))
            continue
        elif os.path.isfile(arch_path) and not delete_file(arch_path, _logger):
            _logger.error("could not remove archive file %s (%s) for %s" %
                          (arch_path, path, freeze_id))
            status = False
            msg_list.append('Error deleting archive %s file %s' %
                            (freeze_id, path))
            continue
        deleted.append(path)

    if not deleted:
        return (status, msg_list)

    # Files deleted - remove paths from archive FILES list and update cache

    freeze_dict['FILES'] = [i for i in freeze_dict.get('FILES', []) if
                            i['name'] not in deleted]

    # NOTE: this is the files-only cache stored in ARCHIVE.cache
    cache_path = "%s%s" % (arch_dir, CACHE_EXT)
    if os.path.isfile(cache_path):
        cached = load(cache_path)
        if not cached:
            cached = []
        _logger.info("pruning %d cache entries in %s" % (len(cached),
                                                         cache_path))
        cached = [entry for entry in cached if entry['name'] not in deleted]
        # Save updated cache
        try:
            dump(cached, cache_path)
            _logger.info("saved %d cache entries in %s" % (len(cached),
                                                           cache_path))
        except Exception as err:
            _logger.warning("failed to save pruned cache in %s: %s" %
                            (cache_path, err))

    if freeze_dict.get('PUBLISH', False):
        frozen_files = [i['name'] for i in freeze_dict.get('FILES', [])
                        if i['name'] not in __public_archive_internals]
        (web_status, web_res) = write_landing_page(freeze_dict, arch_dir,
                                                   frozen_files, cached,
                                                   configuration)
        if not web_status:
            _logger.error(web_res)
            return (False, web_res)

    (commit_status, commit_res) = commit_frozen_archive(freeze_dict, arch_dir,
                                                        configuration)
    if not commit_status:
        _logger.error(commit_res)
        return (False, commit_res)

    mark_archives_modified(configuration, client_id, freeze_id, time.time())
    return (status, msg_list)


def delete_frozen_archive(freeze_dict, client_id, configuration):
    """Delete an existing frozen archive at the low level. Assumes previous
    checking of proper ownership and persistance restrictions.
    """
    _logger = configuration.logger
    freeze_id = freeze_dict['ID']
    arch_dir = get_frozen_root(client_id, freeze_id, configuration)
    if freeze_dict.get('PUBLISH', False):
        (web_status, web_res) = remove_landing_page(freeze_dict, arch_dir,
                                                    configuration,
                                                    allow_missing=True)
        if not web_status:
            _logger.error(web_res)
            return (False, web_res)

    if not delete_file(arch_dir+CACHE_EXT, _logger, allow_missing=True) \
            or not remove_rec(arch_dir, configuration):
        _logger.error("could not remove archive dir for %s" %
                      brief_freeze(freeze_dict))
        return (False, 'Error deleting frozen archive %s' % freeze_id)
    mark_archives_modified(configuration, client_id, freeze_id, time.time())
    return (True, '')


def import_freeze_form(configuration, client_id, output_format,
                       form_append='', csrf_token=''):
    """HTML for the import of archives"""
    fill_helpers = {'vgrid_label': configuration.site_vgrid_label,
                    'output_format': output_format, 'form_append': form_append,
                    'csrf_field': csrf_field, 'csrf_token': csrf_token,
                    'target_op': 'cp', 'form_method': 'post'}
    # TODO: move js to separate function?
    html = ''
    html += '''
    <script>
    function toggle_overwrite_warning() {
        if ($("#overwrite_check").prop("checked")) {
            $("#overwrite_warn").show();
        } else {
            $("#overwrite_warn").hide();
        }
    }
    </script>
    '''
    html += '''
    <form id="import_freeze_form" method="%(form_method)s" action="%(target_op)s.py">
    <fieldset>
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="output_format" value="%(output_format)s" />
        <input type="hidden" name="action" value="create" />
        <p>
        You can import the files and directories you stored in an archive, e.g.
        to restore your own original copy of read-only material.
        Just leave Source path to "*" to import entire archive content.
        </p>
        <p class="warningtext">
        Please select a destination folder where the import does not interfere
        with your existing data.
        </p>
        <table>
        <tr><td colspan=2>
        <label for="freeze_id">Archive ID:</label>
        <input id="importfreezeid" class="singlefield" type="text" name="freeze_id" size=50
        value="" required pattern="[^ ]+"
        title="id string of archive to import from" />
        </td></tr>
        <tr><td colspan=2>
        <label for="src">Source path:</label>
        <input id="importsrc" class="singlefield" type="text" name="src" size=50
        value="" required pattern="[^ ]+"
        title="relative path or pattern of files to import from archive" />
        <tr><td colspan=2>
        <label for="dst">Destination folder:</label>
        <input id="importdst" class="singlefield" type="text" name="dst" size=50
        value="" required pattern="[^ ]+" readonly
        title="relative directory path to import archive into" />
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <br />
        </td></tr>
        <tr><td colspan=2>
        <br/>
        </td></tr>
        <tr class="hidden"><td colspan=2>
        <!-- NOTE: we translate individual flag helpers in jquery fileman -->
        <!-- always use recursive -->
        <label for="recursive">Recursive:</label>
        <input type="checkbox" name="recursive" checked="checked" />
        </td></tr>
        <tr><td colspan=2>
        <!-- toggle force on/off -->
        <label for="overwrite">Overwrite files:</label>
        <input id="overwrite_check" type="checkbox" name="overwrite"
            onClick="toggle_overwrite_warning();" />
        <span id="overwrite_warn" class="hidden iconspace leftpad warn">
        careful - may result in data loss!</span>
        </td></tr>
        <tr><td colspan=2>
        %(form_append)s
        </td></tr>
        </table>
    </fieldset>
    </form>
''' % fill_helpers
    return html


if __name__ == "__main__":
    if not sys.argv[2:]:
        print("USAGE: freezefunctions.py CLIENT_ID ARCHIVE_ID")
        print("       Runs basic unit tests for the ARCHIVE_ID of CLIENT_ID")
        sys.exit(1)
    from mig.shared.conf import get_configuration_object
    configuration = get_configuration_object()
    client_id = sys.argv[1]
    freeze_id = sys.argv[2]
    print("Loading %s of %s" % (freeze_id, client_id))
    (load_status, freeze_dict) = get_frozen_archive(client_id, freeze_id,
                                                    configuration)
    if not load_status:
        print("Failed to load %s for %s: %s" % (freeze_id, client_id,
                                                freeze_dict))
        sys.exit(1)
    print("Metadata for %s is:" % freeze_id)
    for (meta_key, meta_label) in __public_meta:
        meta_value = freeze_dict.get(meta_key, '')
        if meta_value:
            # Preserve any text formatting in e.g. description
            print("%s: %s" % (meta_label, format_meta(meta_key, meta_value)))
