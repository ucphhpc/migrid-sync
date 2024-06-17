#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# indexdoi - Build index of imported site DOIs
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

"""Build index page listing all imported site DOIs - useful from cron job"""

from __future__ import print_function
from __future__ import absolute_import

import datetime
import glob
import json
import os
import sys

from mig.shared.conf import get_configuration_object
from mig.shared.defaults import public_archive_doi, public_doi_index
from mig.shared.htmlgen import get_xgi_html_header, get_xgi_html_footer, \
    themed_styles, themed_scripts


def extract_imported_doi_dicts(configurationi):
    """Search published archives for imported DOI info and return a list of DOI
    registrations sorted by registration date. The contents are based on the
    downloaded DataCite JSON entry on their DOI search page.
    """
    _logger = configuration.logger
    all_imported = []
    doi_import_pattern = os.path.join(configuration.wwwpublic, 'archives',
                                      '*', public_archive_doi)
    for doi_dump_path in glob.glob(doi_import_pattern):
        try:
            json_fd = open(doi_dump_path, 'rb')
            doi_import = json.load(json_fd)
            json_fd.close()
            all_imported.append((os.path.getctime(doi_dump_path), doi_import))
        except Exception as exc:
            _logger.warning("could not load %s: %s" % (doi_dump_path, exc))
    # Sort with newest first
    all_imported.sort(reverse=True)
    date_sorted = [doi for (stamp, doi) in all_imported]
    return date_sorted


if __name__ == '__main__':
    if '-h' in sys.argv[1:]:
        print("""USAGE:
indexdoi.py [OPTIONS]

to build an index page of all locally published archives with DOIs registered.
""")
        sys.exit(1)

    configuration = get_configuration_object()
    _logger = configuration.logger
    verbose = False
    dump = True
    doi_index_path = os.path.join(configuration.wwwpublic, public_doi_index)
    now = datetime.datetime.now()
    # Ignore msec in stamp
    now -= datetime.timedelta(microseconds=now.microsecond)

    doi_exports, doi_count = [], 0
    doi_imports = extract_imported_doi_dicts(configuration)
    if verbose:
        print("extracted %d doi entries: %s" % len(doi_imports))

    # print("DEBUG: extracted DOIs:\n%s" % doi_entries)
    for entry in doi_imports:
        plain_doi = entry.get("doi", None)
        if plain_doi is None:
            print("WARNING skip handling of malformed entry: %s" % entry)
            continue
        if verbose:
            print("handling entry for %s" % plain_doi)

        doi_url = entry.get("id", None)
        archive_url = entry.get('url', '')
        archive_id = os.path.basename(os.path.dirname(archive_url))
        if not archive_id or not doi_url:
            print("WARNING DOI or archive ID missing from %s (%s %s)" %
                  (entry, archive_id, doi_url))
            continue
        archive_root = os.path.join(configuration.wwwpublic, 'archives',
                                    archive_id)
        if not os.path.isdir(archive_root):
            print("ERROR No archive %s for DOI %s data" %
                  (archive_root, plain_doi))
            continue
        doi_path = os.path.join(archive_root, public_archive_doi)
        if os.path.exists(doi_path):
            if verbose:
                print("Found existing DOI data in %s" % doi_path)
            doi_exports.append((plain_doi, archive_url))
            doi_count += 1

    if dump:
        fill_helpers = {'short_title': configuration.short_title,
                        'update_stamp': now,
                        'doi_count': doi_count,
                        }
        publish_title = '%(short_title)s DOI Index' % fill_helpers

        # Fake manager themed style setup for tablesorter layout with site style
        style_entry = themed_styles(configuration, user_settings={})
        # Fake manager themed script setup for tablesorter use
        script_entry = themed_scripts(configuration)

        # NOTE: use mark_static to insert classic page top logo like on V2 pages
        # using staticpage class for flexible skinning. Otherwise index has no
        # branding/skin whatsoever.
        contents = get_xgi_html_header(configuration, publish_title, '',
                                       style_map=style_entry,
                                       script_map=script_entry,
                                       frame=False,
                                       menu=False,
                                       widgets=False,
                                       userstyle=False,
                                       mark_static=True)

        contents += '''
<div id="doi-index" class="staticpage">
<h2 class="staticpage">%(short_title)s DOI Index</h2>
<div class="doi-index-intro">
A list of all %(doi_count)d known DOIs pointing to Archives at %(short_title)s, sorted
with the most recently discovered ones at the top.
</div>
<div class="vertical-spacer"></div>
<div class="info leftpad">
Last auto-generated on %(update_stamp)s
</div>
<div class="vertical-spacer"></div>
<div class="doi-list">
'''

        doi_lines = ''
        for (doi, url) in doi_exports:
            doi_lines += '''
        <p class="doi-line">
            <a class="url urllink leftpad" target=_blank href="%s">%s</a>
        </p>
''' % (url, doi)
        contents += doi_lines
        contents += '''
</div>
</div>
%s
''' % get_xgi_html_footer(configuration, widgets=False, mark_static=True)

        try:
            index_fd = open(doi_index_path, 'w')
            index_fd.write(contents % fill_helpers)
            index_fd.close()
            msg = "Published index of %d DOIs in %s" % \
                  (doi_count, doi_index_path)
            _logger.info(msg)
            if verbose:
                print(msg)
        except Exception as exc:
            msg = "failed to write %s: %s" % (doi_index_path, exc)
            _logger.error(msg)
            print("Error writing index of %d DOIs in %s" %
                  (doi_count, doi_index_path))
            sys.exit(1)

    sys.exit(0)
