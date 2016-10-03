#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# freezefunctions - freeze archive helper functions
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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
     public_archive_dir, public_archive_index, freeze_flavors
from shared.fileio import md5sum_file, sha1sum_file, write_file, copy_file, \
     copy_rec, move_file, move_rec, remove_rec, makedirs_rec, make_symlink, \
     make_temp_dir
from shared.html import get_cgi_html_preamble, get_cgi_html_footer
from shared.serial import load, dump

__cache_ext = ".cache"

def public_freeze_id(freeze_dict, configuration):
    """Translate internal freeze_id to a public identifier used when publishing
    frozen archives. I.e. map to new client_id sub-dir for recent archives or
    fall back to the legacy location directly in freeze_home.
    In the future we may want to map to a global DOI but we
    just map to to url safe base64 version of the freeze ID for now.
    """
    # TODO: remove legacy look-up directly in freeze_home when migrated
    if freeze_dict.get('PERSONAL', False):
        location = freeze_dict['ID']
    else:
        configuration.logger.debug("lookup public id for %s" % freeze_dict)
        client_dir = client_id_dir(freeze_dict['CREATOR'])
        location = os.path.join(client_dir, freeze_dict['ID'])
    return base64.urlsafe_b64encode(freeze_dict['ID'])

def published_dir(freeze_dict, configuration):
    """Translate internal freeze_id to a published archive dir"""
    return os.path.join(configuration.wwwpublic, public_archive_dir,
                        public_freeze_id(freeze_dict, configuration))

def published_url(freeze_dict, configuration):
    """Translate internal freeze_id to a published archive URL"""
    return os.path.join(configuration.migserver_http_url, 'public',
                        public_archive_dir, public_freeze_id(freeze_dict,
                                                             configuration),
                        public_archive_index)

def build_freezeitem_object(configuration, freeze_dict, summary=False):
    """Build a frozen archive object based on input freeze_dict.
    The optional summary argument can be used to build just a archive summary
    rather than the full dictionary of individual file details.
    """
    if summary:
        freeze_files = len(freeze_dict.get('FILES', []))
    else:
        freeze_files = []
        for file_item in freeze_dict['FILES']:
            showfile_link = {'object_type': 'link',
                             'destination': 'showfreezefile.py?'
                             'freeze_id=%s;path=%s' % \
                             (freeze_dict['ID'], file_item['name']),
                             'title': 'Show archive file %s' % file_item['name'],
                             'text': file_item['name']}
            freeze_files.append({
                'object_type': 'frozenfile',
                'name': file_item['name'],
                'showfile_link': showfile_link,
                'size': file_item['size'],
                'md5sum': file_item['md5sum'],
                'sha1sum': file_item['sha1sum'],
                })
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
        'frozenfiles': freeze_files,
        }
    for field in ('author', 'department', 'organization', 'publish',
                  'publish_url', 'flavor'):
        if not freeze_dict.get(field.upper(), None) is None:
            freeze_obj[field] = freeze_dict[field.upper()]
    # NOTE: datetime is not json-serializable so we force to string
    for field in ('location', ):
        if not freeze_dict.get(field.upper(), None) is None:
            freeze_obj[field] = [(i, str(j)) for (i, j) in freeze_dict[field.upper()]]
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
    minutes =  multiplier * count
    return datetime.timedelta(minutes=minutes)

def list_frozen_archives(configuration, client_id):
    """Find all frozen_archives owned by user. We used to store all archives
    directly in freeze_home, but have switched to client_id sub dirs since they
    are personal anyway. Look in the client_id folder first.
    """
    logger = configuration.logger
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
                logger.error(
                    'freezefunctions.py: not able to create directory %s'
                    % archive_home)
                return (False, "archive setup is broken")

    for entry in dir_content:

        # Skip dot files/dirs and cache entries

        if entry.startswith('.') or entry.endswith(__cache_ext):
            continue
        if is_frozen_archive(client_id, entry, configuration):

            # entry is a frozen archive - check ownership

            (meta_status, meta_out) = get_frozen_meta(client_id, entry, configuration)
            if meta_status and meta_out['CREATOR'] == client_id:
                frozen_list.append(entry)
        else:
            logger.warning(
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
    return (False, 'Could not open metadata for frozen archive %s' % \
            freeze_id)

def get_frozen_files(client_id, freeze_id, configuration, checksum='md5'):
    """Helper to list names and stats for files in a frozen archive.
    I.e. lookup the contents of an achive either in the new client_id sub-dir
    or directly in the legacy freeze_home location.
    The optional checksum argument can be used to switch between potentially
    heavy checksum calculation e.g. when used in freezedb.
    """
    _logger = configuration.logger
    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    found = False
    for archive_home in (user_archives, configuration.freeze_home):
        frozen_dir = os.path.join(archive_home, freeze_id)
        if os.path.isdir(frozen_dir):
            found = True
            break
    if not found:
        return (False, 'Could not open frozen archive %s' % freeze_id)
    chksum_unset = 'please request explicitly'
    cache_path = "%s%s" % (frozen_dir, __cache_ext)
    file_map = {}
    try:
        cached = []
        if os.path.isfile(cache_path):
            cached = load(cache_path)
        if cached:
            if not checksum or cached[-1].get("%ssum" % checksum,
                                              chksum_unset) != chksum_unset:
                _logger.debug("using cached info for %s in %s" % (freeze_id,
                                                                  cache_path))
                return (True, cached)
            else:
                _logger.info("insufficient cached info in %s" % cache_path)
                file_map = dict([(entry['name'], entry) for entry in cached])
        else:
            _logger.debug("no cached files info in %s" % cache_path)
    except Exception, err:
        _logger.warning("failed to load files cache in %s: %s" % \
                        (cache_path, err))
    # Walk archive and fill file data using any cached fields for speed
    # TODO: switch to combined list and stat with scandir instead of walk?
    files = []
    for (root, _, filenames) in walk(frozen_dir):
        for name in filenames:
            if name in [freeze_meta_filename]:
                continue
            frozen_path = os.path.join(root, name)
            rel_path = os.path.join(root.replace(frozen_dir, '', 1), name)
            rel_path = rel_path.lstrip(os.sep)
            entry = file_map.get(rel_path, None)
            if entry is None:
                entry = {'name': rel_path,
                         'timestamp': os.path.getctime(frozen_path),
                         'size': os.path.getsize(frozen_path),
                         'md5sum': chksum_unset,
                         'sha1sum': chksum_unset}
            # Update checksum if requested and not there already
            if checksum == 'md5' and entry['md5sum'] == chksum_unset:
                # Checksum first 32 MB of files
                entry['md5sum'] = md5sum_file(frozen_path)
            elif checksum == 'sha1':
                # Checksum first 32 MB of files
                entry['sha1sum'] = sha1sum_file(frozen_path)
            files.append(entry)
    # Save updated cache
    try:
        dump(files, cache_path)
        _logger.info("saved files cache in %s" % cache_path)
    except Exception, err:
        _logger.warning("failed to save files cache in %s: %s" % \
                        (cache_path, err))
    return (True, files)

def get_frozen_archive(client_id, freeze_id, configuration, checksum='md5'):
    """Helper to extract all details for a frozen archive. I.e. extract the
    contents of the archive either in the new client_id sub-dir or directly in
    the legacy freeze_home location.
    The optional checksum argument can be used to switch between potentially
    heavy checksum calculation e.g. when used in freezedb.
    """
    if not is_frozen_archive(client_id, freeze_id, configuration):
        return (False, 'no such frozen archive id: %s' % freeze_id)
    (meta_status, meta_out) = get_frozen_meta(client_id, freeze_id,
                                              configuration)
    if not meta_status:
        return (False, 'failed to extract meta data for %s' % freeze_id)
    (files_status, files_out) = get_frozen_files(client_id, freeze_id,
                                                 configuration, checksum)
    if not files_status:
        return (False, 'failed to extract files for %s' % freeze_id)
    freeze_dict = {'ID': freeze_id, 'FILES': files_out}
    freeze_dict.update(meta_out)
    return (True, freeze_dict)

def create_frozen_archive(freeze_meta, freeze_copy, freeze_move,
                          freeze_upload, client_id, configuration):
    """Create a new frozen archive with meta data fields and provided
    freeze_copy files from user home, freeze_move from temporary upload dir
    and freeze_upload files from form.
    Updates freeze_meta with the saved archive values.
    """
    logger = configuration.logger
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    try:
        frozen_dir = make_temp_dir(prefix='archive-',
                                   dir=user_archives)
    except Exception, err:
        return (False, 'Error preparing new frozen archive: %s' % err)

    freeze_id = os.path.basename(frozen_dir)    
    freeze_dict = {
        'ID': freeze_id,
        'CREATED_TIMESTAMP': datetime.datetime.now(),
        'CREATOR': client_id,
        'PERSONAL': True,
        }
    freeze_dict.update(freeze_meta)
    if freeze_meta['PUBLISH']:
        real_pub_dir = published_dir(freeze_dict, configuration)
        real_pub_index = os.path.join(real_pub_dir, public_archive_index)
        freeze_dict['PUBLISH_URL'] = published_url(freeze_dict, configuration)
    frozen_files = []
    logger.info("create_frozen_archive: save meta for %s" % freeze_id)
    try:
        dump(freeze_dict, os.path.join(frozen_dir, freeze_meta_filename))
        # Make sure caller receives actual meta data to be able to look up
        # public freeze ID
        freeze_meta.update(freeze_dict)
    except Exception, err:
        logger.error("create_frozen_archive: failed: %s" % err)
        remove_rec(frozen_dir, configuration)
        return (False, 'Error writing frozen archive info: %s' % err)

    logger.info("create_frozen_archive: copy %s for %s" % \
                              (freeze_copy, freeze_id))
    for (real_source, rel_dst) in freeze_copy:
        freeze_path = os.path.join(frozen_dir, rel_dst)
        frozen_files.append(rel_dst)
        logger.debug("create_frozen_archive: copy %s" % freeze_path)
        if os.path.isdir(real_source):
            (status, msg) = copy_rec(real_source, freeze_path, configuration)
            if not status:
                logger.error("create_frozen_archive: failed: %s" % msg)
                remove_rec(frozen_dir, configuration)
                return (False, 'Error writing frozen archive')
        else:
            (status, msg) = copy_file(real_source, freeze_path, configuration)
            if not status:
                logger.error("create_frozen_archive: failed: %s" % msg)
                remove_rec(frozen_dir, configuration)
                return (False, 'Error writing frozen archive')
    logger.info("create_frozen_archive: move %s for %s" % \
                              (freeze_move, freeze_id))
    for (real_source, rel_dst) in freeze_move:
        # Strip relative dir from move targets
        freeze_path = os.path.join(frozen_dir, os.path.basename(rel_dst))
        frozen_files.append(os.path.basename(rel_dst))
        logger.debug("create_frozen_archive: move %s" % freeze_path)
        if os.path.isdir(real_source):
            (status, msg) = move_rec(real_source, freeze_path, configuration)
            if not status:
                logger.error("create_frozen_archive: failed: %s" % msg)
                remove_rec(frozen_dir, configuration)
                return (False, 'Error writing frozen archive')
        else:
            (status, msg) = move_file(real_source, freeze_path, configuration)
            if not status:
                logger.error("create_frozen_archive: failed: %s" % msg)
                remove_rec(frozen_dir, configuration)
                return (False, 'Error writing frozen archive')
    logger.info("create_frozen_archive: save %s for %s" % \
                              ([i[0] for i in freeze_upload], freeze_id))
    for (filename, contents) in freeze_upload:
        freeze_path = os.path.join(frozen_dir, filename)
        frozen_files.append(filename)
        logger.debug("create_frozen_archive: write %s" % freeze_path)
        if not write_file(contents, freeze_path, logger):
            logger.error("create_frozen_archive: failed: %s" % err)
            remove_rec(frozen_dir, configuration)
            return (False, 'Error writing frozen archive')

    if freeze_dict['PUBLISH']:
        published_id = public_freeze_id(freeze_dict, configuration)
        public_meta = [('CREATOR', 'Owner'), ('NAME', 'Name'),
                       ('DESCRIPTION', 'Description'),
                       ('CREATED_TIMESTAMP', 'Date')]

        # Use the default preamle to get style, skin and so on right
        
        contents = get_cgi_html_preamble(configuration, "Public Archive: %s" % \
                                         published_id, "", widgets=False)

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

<div class='contentblock staticpage' id='nomenu'>
<div id='migheader'>
</div>
<div class='staticpage' id='content' lang='en'>
""" % configuration.site_skin_base

        # Then fill actual archive page
    
        contents += """
<div>
<h1 class='staticpage'>Public Archive</h1>
This is the public archive with unique ID %s .<br/>
The user-supplied meta data and files are available below.

<h2 class='staticpage'>Archive Meta Data</h2>
""" % published_id
        for (meta_key, meta_label) in public_meta:
            meta_value = freeze_dict.get(meta_key, '')
            if meta_value:
                contents += """%s: %s<br/>
""" % (meta_label, meta_value)
        contents += """
<h2 class='staticpage'>Archive Files</h2>
        """
        for rel_path in frozen_files:
            # Careful to avoid problems with filenames containing single quotes
            # and encode e.g. percent signs that would otherwise interfere
            contents += '''<a href="%s">%s</a><br/>
''' % (quote(rel_path), rel_path)
        contents += """
</div>
%s
        """ % get_cgi_html_footer(configuration, widgets=False)
        if not make_symlink(frozen_dir, real_pub_dir, logger) or \
               not write_file(contents, real_pub_index, configuration.logger):
            logger.error("create_frozen_archive: publish failed")
            remove_rec(frozen_dir, configuration)
            return (False, 'Error publishing frozen archive')
    # Mark as saved on disk and hint about any tape archiving schedule
    now = datetime.datetime.now()
    slack = 2
    # Skip microseconds
    on_disk_date = datetime.datetime.now().replace(microsecond=0)
    archive_locations = [('disk', on_disk_date)]
    on_tape_date = None
    if configuration.site_freeze_to_tape:
        delay = parse_time_delta(configuration.site_freeze_to_tape)
        on_tape_date = on_disk_date + delay
        archive_locations.append( ('tape', on_tape_date))
    freeze_dict['LOCATION'] = archive_locations
    logger.info("create_frozen_archive: update meta for %s" % freeze_id)
    try:
        dump(freeze_dict, os.path.join(frozen_dir, freeze_meta_filename))
    except Exception, err:
        logger.error("create_frozen_archive: failed: %s" % err)
        remove_rec(frozen_dir, configuration)
        return (False, 'Error updating frozen archive info: %s' % err)
    return (True, freeze_id)

def delete_frozen_archive(client_id, freeze_id, configuration):
    """Delete an existing frozen archive without checking ownership or
    persistance of frozen archives.
    """
    # TODO: remove legacy look-up directly in freeze_home when migrated
    client_dir = client_id_dir(client_id)
    user_archives = os.path.join(configuration.freeze_home, client_dir)
    for archive_home in (user_archives, configuration.freeze_home):
        frozen_dir = os.path.join(archive_home, freeze_id)
        if remove_rec(frozen_dir, configuration):
            return (True, '')
    return (False, 'Error deleting frozen archive "%s"' % freeze_id)


