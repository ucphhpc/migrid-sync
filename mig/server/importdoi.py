#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# importdoi - Import DOIs from provided uri
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Import any missing DOIs from provided URI - useful from cron job"""
from __future__ import print_function
from __future__ import absolute_import

import json
import os
import requests
import sys

from mig.shared.conf import get_configuration_object
from mig.shared.defaults import public_archive_doi


def __datacite_req(format, query):
    """Low-level helper to make a request for data from DataCite"""
    url = os.path.join('https://api.datacite.org', format, query)
    #print "DEBUG: query datacite REST service on %s" % url
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("unexpected response for %s : %s : %s" %
                        (url, response.status_code, response.text))
    #print "DEBUG: response\n%s" % response.text
    parsed = json.loads(response.text)
    return parsed


def datacite_query(query):
    """Make a query against the DataCite REST interface"""
    return __datacite_req('works', query)


def datacite_full(doi):
    """Request full DataCite json content for given DOI value. This is the data
    corresponding with the Download DataCite JSON entry on the DOI search.
    """
    return __datacite_req('dois/application/vnd.datacite.datacite+json', doi)


if __name__ == '__main__':
    if not sys.argv[1:]:
        print("""USAGE:
importdoi.py VALUE
where VALUE may be an FQDN, a DOI or a query on the format 'query=BLA' .
 * FQDN results in a lookup for all DOIs matching that FQDN and dumping the
   individual results to a published-doi.json file in the corresponding
   published archive folder.
 * DOI must be relative and include a slash and it results in a specific lookup
   and dumping the result to a published-doi.json file in the corresponding
   published archive folder.
 * query=QUERY can be used to test DOI lookups without writing any files.

E.g. to import all DOIs registered by UCPH and hosted here one would run:
  importdoi.py dk.ku
or to match only those registered to erda.ku.dk:
  importdoi.py erda.ku.dk
""")
        sys.exit(1)

    configuration = get_configuration_object()
    target = sys.argv[1]
    dump = True
    query = ''
    direct = ''
    verbose = False
    if target.startswith('query='):
        dump = False
        query += '?' + target
    elif target.find('/') != -1:
        direct += target
    else:
        query += '?query=%s' % target

    if direct:
        try:
            parsed = datacite_full(direct)
        except Exception as exc:
            print("ERROR in DataCite request: %s" % exc)
            sys.exit(2)
        if verbose:
            print("parsed datacite response with %d fields" % len(parsed))
        # Result should be a plain dict here and we want a list of such dicts
        if isinstance(parsed, list):
            parsed_data = parsed
        else:
            parsed_data = [parsed]
    else:
        try:
            parsed = datacite_query(query)
        except Exception as exc:
            print("ERROR in DataCite request: %s" % exc)
            sys.exit(2)
        #print "DEBUG: parsed datacite response with %d fields" % len(parsed)
        # parsed is a dicionary with a data entry holding a list of summary
        # result dicts. The other entry is meta.
        parsed_index = parsed.get("data", [])
        #print "DEBUG: repeat full lookup for individual sparse entries"
        parsed_data = []
        for entry in parsed_index:
            attributes = entry.get('attributes', {})
            plain_doi = attributes.get("doi", None)
            if plain_doi is None:
                print("WARNING skip full lookup of malformed entry: %s" % entry)
                continue
            if verbose:
                print("repeat full lookup for %s" % plain_doi)
            try:
                full = datacite_full(plain_doi)
            except Exception as exc:
                print("ERROR in DataCite request: %s" % exc)
                continue
            parsed_data.append(full)

    imported, existing, new = 0, 0, 0
    for entry in parsed_data:
        if not isinstance(entry, dict):
            print("WARNING skip malformed entry: %s" % entry)
            continue
        #print "DEBUG: handle entry: %s" % entry
        doi_url = entry.get("id", None)
        doi = entry.get("doi", None)
        archive_url = entry.get('url', '')
        archive_id = os.path.basename(os.path.dirname(archive_url))
        if not archive_id or not doi_url:
            print("WARNING DOI or archive ID missing from %s (%s %s)" % \
                  (entry, archive_id, doi_url))
            continue
        archive_root = os.path.join(configuration.wwwpublic, 'archives',
                                    archive_id)
        if not os.path.isdir(archive_root):
            print("ERROR No archive %s for DOI %s data" % (archive_root, doi))
            continue
        doi_path = os.path.join(archive_root, public_archive_doi)
        if os.path.exists(doi_path):
            if verbose:
                print("Found existing DOI data in %s" % doi_path)
            existing += 1
            continue
        new += 1
        if dump:
            print("Save DOI %s for archive %s" % (doi, archive_id))
            doi_fd = open(doi_path, 'w')
            json.dump(entry, doi_fd)
            doi_fd.close()
            imported += 1
        else:
            print("New DOI %s for archive %s" % (doi, archive_id))
            if verbose:
                print("\t%s" % entry)

    print("Found %d existing - and imported %d of %d new DOI entries" % \
          (existing, imported, new))
    sys.exit(0)
