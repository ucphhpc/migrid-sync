#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# freezefunctions - freeze archive helper functions
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

"""Freeze archive functions"""

import base64
import datetime
import os
import time
# NOTE: Use faster scandir if available
try:
    from scandir import walk, __version__ as scandir_version
    if float(scandir_version) < 1.3:
        # Important os.walk compatibility utf8 fixes were not added until 1.3
        raise ImportError("scandir version is too old: fall back to os.walk")
except ImportError:
    from os import walk
from urllib import quote

from shared.base import client_id_dir
from shared.defaults import freeze_meta_filename, wwwpublic_alias, \
    public_archive_dir, public_archive_index, freeze_flavors, keyword_final, \
    keyword_pending, keyword_auto, max_freeze_files
from shared.fileio import md5sum_file, sha1sum_file, sha256sum_file, \
    sha512sum_file, supported_hash_algos, write_file, copy_file, copy_rec, \
    move_file, move_rec, remove_rec, delete_file, delete_symlink, \
    makedirs_rec, make_symlink, make_temp_dir
from shared.html import get_cgi_html_preamble, get_cgi_html_footer
from shared.pwhash import make_path_hash
from shared.serial import load, dump

TARGET_ARCHIVE = 'ARCHIVE'
TARGET_PATH = 'PATH'
__cache_ext = ".cache"
__chksum_unset = 'please request explicitly'


def public_freeze_id(freeze_dict, configuration):
    """Translate internal freeze_id to a public identifier used in the URL when
    publishing frozen archives. I.e. map to new client_id sub-dir for recent
    archives or fall back to the legacy location directly in freeze_home.
    For legacy archives we used url safe base64 encoding and for recent
    archives we've switched to a 128-bit hash of the unique archive path to
    avoid URL collisions.
    """
    _logger = configuration.logger
    _logger.debug("lookup public id for %s" % freeze_dict)

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


def published_url(freeze_dict, configuration):
    """Translate internal freeze_id to a published archive URL"""
    base_url = configuration.migserver_http_url
    if configuration.migserver_https_sid_url:
        base_url = configuration.migserver_https_sid_url
    return os.path.join(base_url, 'public', public_archive_dir,
                        public_freeze_id(freeze_dict, configuration),
                        public_archive_index)


def build_freezeitem_object(configuration, freeze_dict, summary=False):
    """Build a frozen archive object based on input freeze_dict.
    The optional summary argument can be used to build just a archive summary
    rather than the full dictionary of individual file details.
    """
    freeze_id = freeze_dict['ID']
    flavor = freeze_dict.get('FLAVOR', 'freeze')
    if summary:
        freeze_files = len(freeze_dict.get('FILES', []))
    else:
        freeze_files = []
        for file_item in freeze_dict['FILES']:
            quoted_name = quote(file_item['name'])
            showfile_link = {
                'object_type': 'link',
                'destination': 'showfreezefile.py?freeze_id=%s;path=%s' %
                (freeze_dict['ID'], quoted_name),
                'class': 'viewlink iconspace',
                'title': 'Show archive file %(name)s' % file_item,
                'text': ''
            }
            int_timestamp = int(file_item['timestamp'])
            # NOTE: datetime is not json-serializable so we force to string
            dt_timestamp = datetime.datetime.fromtimestamp(int_timestamp)
            str_timestamp = "%s" % dt_timestamp
            entry = {
                'object_type': 'frozenfile',
                'name': file_item['name'],
                'showfile_link': showfile_link,
                'timestamp': int_timestamp,
                'date': str_timestamp,
                'size': file_item['size'],
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
                    'class': 'removelink iconspace', 'title':
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


def list_frozen_archives(configuration, client_id):
    """Find all frozen_archives owned by user. We used to store all archives
    directly in freeze_home, but have switched to client_id sub dirs since they
    are personal anyway. Look in the client_id folder first.
    """
    _logger = configuration.logger
    frozen_list = []
    dir_content = []

    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    for archive_home in (user_archives, configuration.freeze_home):
        try:
            dir_content += os.listdir(archive_home)
        except Exception:
            if not makedirs_rec(archive_home, configuration):
                _logger.error(
                    'freezefunctions.py: not able to create directory %s'
                    % archive_home)
                return (False, "archive setup is broken")

    for entry in dir_content:

        # Skip dot files/dirs and cache entries

        if entry.startswith('.') or entry.endswith(__cache_ext):
            continue
        if is_frozen_archive(client_id, entry, configuration):

            # entry is a frozen archive - check ownership

            (meta_status, meta_out) = get_frozen_meta(client_id, entry,
                                                      configuration)
            if meta_status and meta_out['CREATOR'] == client_id:
                frozen_list.append(entry)
        else:
            _logger.warning(
                '%s in %s is not a directory, move it?'
                % (entry, configuration.freeze_home))
    return (True, frozen_list)


def is_frozen_archive(client_id, freeze_id, configuration):
    """Check that freeze_id is an existing frozen archive. I.e. that it is
    available either in the new client_id sub-dir or directly in the legacy
    freeze_home location.
    """
    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    for archive_home in (user_archives, configuration.freeze_home):
        freeze_path = os.path.join(archive_home, freeze_id)
        if os.path.isdir(freeze_path) and \
                os.path.isfile(os.path.join(freeze_path, freeze_meta_filename)):
            return True
    return False


def get_frozen_meta(client_id, freeze_id, configuration):
    """Helper to fetch dictionary of metadata for a frozen archive. I.e. load
    the data either from the new client_id sub-dir or directly from the legacy
    freeze_home location.
    """
    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    for archive_home in (user_archives, configuration.freeze_home):
        frozen_path = os.path.join(archive_home, freeze_id,
                                   freeze_meta_filename)
        if not os.path.isfile(frozen_path):
            continue
        freeze_dict = load(frozen_path)
        if freeze_dict:
            return (True, freeze_dict)
    return (False, 'Could not open metadata for frozen archive %s' %
            freeze_id)


def get_frozen_files(client_id, freeze_id, configuration,
                     checksum_list=['md5']):
    """Helper to list names and stats for files in a frozen archive.
    I.e. lookup the contents of an achive either in the new client_id sub-dir
    or directly in the legacy freeze_home location.
    The optional checksum_list arguments can be used to switch between
    potentially heavy checksum calculation e.g. when used in freezedb.
    """
    _logger = configuration.logger
    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    found = False
    for archive_home in (user_archives, configuration.freeze_home):
        arch_dir = os.path.join(archive_home, freeze_id)
        if os.path.isdir(arch_dir):
            found = True
            break
    if not found:
        return (False, 'Could not open frozen archive %s' % freeze_id)
    cache_path = "%s%s" % (arch_dir, __cache_ext)
    file_map = {}
    try:
        cached = []
        if os.path.isfile(cache_path):
            cached = load(cache_path)
        if cached:
            needs_update = False
            if os.path.getmtime(cache_path) < os.path.getmtime(arch_dir):
                needs_update = True
            elif checksum_list:
                for checksum in checksum_list:
                    if [entry['name'] for entry in cached if
                        entry.get("%ssum" % checksum, __chksum_unset)
                            == __chksum_unset]:
                        needs_update = True
                        break

            if not needs_update:
                _logger.debug("using cached info for %s in %s" % (freeze_id,
                                                                  cache_path))
                return (True, cached)
            _logger.info("insufficient cached info for %s in %s" %
                         (freeze_id, cache_path))
            file_map = dict([(entry['name'], entry) for entry in cached])
        else:
            _logger.debug("no cached files info in %s" % cache_path)
    except Exception, err:
        _logger.warning("failed to load files cache in %s: %s" %
                        (cache_path, err))
    # Walk archive and fill file data using any cached fields for speed
    # TODO: switch to combined list and stat with scandir instead of walk?
    files = []
    updates = 0
    for (root, _, filenames) in walk(arch_dir):
        for name in filenames:
            if name in [freeze_meta_filename]:
                continue
            frozen_path = os.path.join(root, name)
            _logger.debug("refresh cache for file %s" % frozen_path)
            rel_path = os.path.join(root.replace(arch_dir, '', 1), name)
            rel_path = rel_path.lstrip(os.sep)
            entry = file_map.get(rel_path, None)
            if entry is None:
                entry = {'name': rel_path,
                         'timestamp': os.path.getctime(frozen_path),
                         'size': os.path.getsize(frozen_path)
                         }
                updates += 1
            for algo in supported_hash_algos():
                chksum_field = '%ssum' % algo
                entry[chksum_field] = entry.get(chksum_field, __chksum_unset)
            # Update checksum if requested and not there already
            if 'md5' in checksum_list and entry['md5sum'] == __chksum_unset:
                # Checksum first 32 MB of files
                entry['md5sum'] = md5sum_file(frozen_path)
                updates += 1
            elif 'sha1' in checksum_list and \
                    entry['sha1sum'] == __chksum_unset:
                # Checksum first 32 MB of files
                entry['sha1sum'] = sha1sum_file(frozen_path)
                updates += 1
            elif 'sha256' in checksum_list and \
                    entry['sha256sum'] == __chksum_unset:
                # Checksum first 32 MB of files
                entry['sha256sum'] = sha256sum_file(frozen_path)
                updates += 1
            elif 'sha512' in checksum_list and \
                    entry['sha512sum'] == __chksum_unset:
                # Checksum first 32 MB of files
                entry['sha512sum'] = sha512sum_file(frozen_path)
                updates += 1
            files.append(entry)
    if updates > 0:
        # Save updated cache
        try:
            dump(files, cache_path)
            _logger.info("saved files cache in %s" % cache_path)
        except Exception, err:
            _logger.warning("failed to save files cache in %s: %s" %
                            (cache_path, err))
    return (True, files)


def get_frozen_archive(client_id, freeze_id, configuration,
                       checksum_list=['md5']):
    """Helper to extract all details for a frozen archive. I.e. extract the
    contents of the archive either in the new client_id sub-dir or directly in
    the legacy freeze_home location.
    The optional checksum_list argument can be used to switch between
    potentially heavy checksum calculation e.g. when used in freezedb.
    """
    _logger = configuration.logger
    if not is_frozen_archive(client_id, freeze_id, configuration):
        return (False, 'no such frozen archive id: %s' % freeze_id)
    (meta_status, meta_out) = get_frozen_meta(client_id, freeze_id,
                                              configuration)
    if not meta_status:
        return (False, 'failed to extract meta data for %s' % freeze_id)
    _logger.debug("loaded meta for '%s': %s" % (freeze_id, meta_out))
    (files_status, files_out) = get_frozen_files(client_id, freeze_id,
                                                 configuration, checksum_list)
    if not files_status:
        return (False, 'failed to extract files for %s' % freeze_id)
    _logger.debug("loaded files for '%s': %s" % (freeze_id, files_out))
    freeze_dict = {'ID': freeze_id}
    freeze_dict.update(meta_out)
    freeze_dict['FILES'] = files_out
    return (True, freeze_dict)


def get_frozen_root(client_id, freeze_id, configuration):
    """Lookup the directory root of freeze_id of client_id"""
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
        arch_dir = make_temp_dir(prefix='archive-',
                                 dir=user_archives)
    except Exception, err:
        _logger.error("create dir for %s from %s failed: %s" % (freeze_meta,
                                                                client_id, err))
        return (False, 'Error preparing new frozen archive: %s' % err)

    freeze_id = os.path.basename(arch_dir)
    _logger.debug("created archive dir for %s" % freeze_id)
    freeze_dict = {
        'CREATED_TIMESTAMP': datetime.datetime.now(),
        'CREATOR': client_id,
        'PERSONAL': True,
        'FORMAT': 2,
    }
    freeze_dict.update(freeze_meta)
    freeze_dict.update({'ID': freeze_id,
                        'STATE': freeze_dict.get('STATE', keyword_pending)})

    _logger.info("save meta data for %s" % freeze_id)
    try:
        dump(freeze_dict, os.path.join(arch_dir, freeze_meta_filename))
    except Exception, err:
        _logger.error("save meta for %s failed: %s" % (freeze_dict, err))
        # We clean up here if init fails - leave it on any later errors
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


def write_landing_page(freeze_dict, arch_dir, frozen_files, configuration):
    """Write a landing page for archive publishing. Depending on archive state
    it will be a draft or the final version.
    """
    _logger = configuration.logger
    freeze_id = freeze_dict['ID']
    published_id = public_freeze_id(freeze_dict, configuration)
    public_meta = [('CREATOR', 'Owner'), ('NAME', 'Name'),
                   ('DESCRIPTION', 'Description'),
                   ('CREATED_TIMESTAMP', 'Date')]
    real_pub_dir = published_dir(freeze_dict, configuration)
    real_pub_index = os.path.join(arch_dir, public_archive_index)
    arch_url = published_url(freeze_dict, configuration)
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

    # Use the default preamble to get style, skin and so on right

    contents = get_cgi_html_preamble(configuration, publish_title, "",
                                     widgets=False, userstyle=False)

    # Manually create modified page start like get_cgi_html_header but
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

    contents += """
%s
<div class='archive-header'>
<h1 class='staticpage'>Public Archive</h1>
This is the public archive with unique ID %s .<br/>
The user-supplied meta data and files are available below.
</div>

<div class='archive-metadata'>
<h2 class='staticpage'>Archive Meta Data</h2>
""" % (publish_preamble, published_id)
    for (meta_key, meta_label) in public_meta:
        meta_value = freeze_dict.get(meta_key, '')
        if meta_value:
            # Preserve any text formatting in e.g. description
            contents += """<h4 class='staticpage'>%s</h4>
<pre class='archive-%s'>%s</pre>
""" % (meta_label, meta_label.lower(), meta_value)
    contents += """</div>

<div class='archive-files'>
<h2 class='staticpage'>Archive Files</h2>
        """
    for rel_path in frozen_files:
        # Careful to avoid problems with filenames containing single quotes
        # and encode e.g. percent signs that would otherwise interfere
        contents += '''<a href="%s">%s</a><br/>
''' % (quote(rel_path), rel_path)
    contents += """</div>
%s
        """ % get_cgi_html_footer(configuration, widgets=False)
    if not make_symlink(arch_dir, real_pub_dir, _logger, force=True) or \
            not write_file(contents, real_pub_index, _logger):
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
    if freeze_dict.get('PUBLISH_URL', ''):
        del freeze_dict['PUBLISH_URL']
    _logger.debug("remove landing page for %s" % freeze_id)
    if not delete_symlink(real_pub_dir, _logger, allow_missing=allow_missing) or \
            not delete_file(real_pub_index, _logger, allow_missing=allow_missing):
        return (False, 'Error removing published landing page for archive')
    return (True, freeze_dict)


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
        on_tape_date = on_disk_date + delay
        archive_locations.append(('tape', on_tape_date))
        # TODO: maintain or calculate total file count and size here
        total_files = freeze_dict.get('TOTALFILES', '?')
        total_size = freeze_dict.get('TOTALSIZE', '?')
        _logger.info("%s archive %s of %s marked %s with %s files of %sb" %
                     (freeze_dict['FLAVOR'], freeze_id, freeze_dict['CREATOR'],
                      freeze_dict['STATE'], total_files, total_size))
        _logger.info("freeze %s finalized with on-tape %s promise" %
                     (freeze_id, on_tape_date))
    freeze_dict['LOCATION'] = archive_locations
    _logger.info("update meta for %s" % freeze_id)
    try:
        dump(freeze_dict, os.path.join(arch_dir, freeze_meta_filename))
    except Exception, err:
        _logger.error("update meta failed: %s" % err)
        return (False, 'Error updating frozen archive info: %s' % err)
    return (True, freeze_dict)


def create_frozen_archive(freeze_meta, freeze_copy, freeze_move,
                          freeze_upload, client_id, configuration):
    """Create or update existing non-persistant archive with provided meta data
    fields and provided freeze_copy files from user home, freeze_move from
    temporary upload dir and freeze_upload files from form.
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

    _logger.debug("create/update archive with dict: %s" % freeze_dict)

    # Bail out if user attempts to edit already persistant archive
    if existing_archive and state == keyword_final:
        _logger.error("access to persistant archive %s for %s refused" %
                      (freeze_id, client_id))
        return (False, "Error: persistant archives cannot be edited")

    arch_dir = get_frozen_root(client_id, freeze_id, configuration)

    (files_status, files_res) = handle_frozen_files(freeze_id, arch_dir,
                                                    freeze_copy, freeze_move,
                                                    freeze_upload,
                                                    configuration)
    if not files_status:
        _logger.error(files_res)
        return (files_status, files_res)
    # Merge list of existing files from loaded archive with new ones
    frozen_files = [i['name'] for i in freeze_dict.get('FILES', [])
                    if i['name'] != public_archive_index]
    frozen_files += files_res
    _logger.debug("proceed with frozen_files: %s" % frozen_files)

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

    if published:
        (web_status, web_res) = write_landing_page(freeze_dict, arch_dir,
                                                   frozen_files, configuration)
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

    # Do not save files list in meta, we keep it in separate cache
    if freeze_dict.get('FILES', ''):
        del freeze_dict['FILES']
    (commit_status, commit_res) = commit_frozen_archive(freeze_dict, arch_dir,
                                                        configuration)
    if not commit_status:
        _logger.error(commit_res)
        return (False, commit_res)
    # We received location updates from commit
    freeze_dict = commit_res
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

    cache_path = "%s%s" % (arch_dir, __cache_ext)
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
        except Exception, err:
            _logger.warning("failed to save pruned cache in %s: %s" %
                            (cache_path, err))

    if freeze_dict.get('PUBLISH', False):
        frozen_files = [i['name'] for i in freeze_dict.get('FILES', [])
                        if i['name'] != public_archive_index]
        (web_status, web_res) = write_landing_page(freeze_dict, arch_dir,
                                                   frozen_files, configuration)
        if not web_status:
            _logger.error(web_res)
            return (False, web_res)

    (commit_status, commit_res) = commit_frozen_archive(freeze_dict, arch_dir,
                                                        configuration)
    if not commit_status:
        _logger.error(commit_res)
        return (False, commit_res)

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

    if not delete_file(arch_dir+__cache_ext, _logger, allow_missing=True) \
            or not remove_rec(arch_dir, configuration):
        _logger.error("could not remove archive dir for %s" % freeze_dict)
        return (False, 'Error deleting frozen archive %s' % freeze_id)
    return (True, '')
