# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_url - unit test of the corresponding mig shared module
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Unit tests for the migrid module pointed to in the filename"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from tests.support import MigTestCase, FakeConfiguration, testmain
from mig.shared.url import _get_site_urls, check_local_site_url


def _generate_dynamic_site_urls(url_base_list):
    """Simple helper to construct a list of similar URLs for each base url in
    url_base_list.
    """
    site_urls = []
    for url_base in url_base_list:
        site_urls += ['%s' % url_base, '%s/' % url_base,
                      '%s/wsgi-bin/home.py' % url_base,
                      '%s/wsgi-bin/logout.py' % url_base,
                      '%s/wsgi-bin/logout.py?return_url=' % url_base,
                      '%s/wsgi-bin/logout.py?return_url=%s' % (url_base,
                                                               ENC_URL)
                      ]
    return site_urls


DUMMY_CONF = FakeConfiguration(migserver_http_url='http://myfqdn.org',
                               migserver_https_url='https://myfqdn.org',
                               migserver_https_mig_cert_url='',
                               migserver_https_ext_cert_url='',
                               migserver_https_mig_oid_url='',
                               migserver_https_ext_oid_url='',
                               migserver_https_mig_oidc_url='',
                               migserver_https_ext_oidc_url='',
                               migserver_https_sid_url='',
                               migserver_public_url='',
                               migserver_public_alias_url='')
ENC_URL = 'https%3A%2F%2Fsomewhere.org%2Fsub%0A'
# Static site-anchored and dynamic full URLs for local site URL check success
LOCAL_SITE_URLS = ['', 'abc', 'abc.txt', '/', '/bla', '/bla#anchor',
                   '/bla/', '/bla/#anchor', '/bla/bla', '/bla/bla/bla',
                   '//bla//', './bla', './bla/', './bla/bla',
                   './bla/bla/bla', 'logout.py', 'logout.py?bla=',
                   '/cgi-sid/logout.py', '/cgi-sid/logout.py?bla=bla',
                   '/cgi-sid/logout.py?return_url=%s' % ENC_URL,
                   ]
LOCAL_BASE_URLS = _get_site_urls(DUMMY_CONF)
LOCAL_SITE_URLS += _generate_dynamic_site_urls(LOCAL_SITE_URLS)
# Dynamic full URLs for local site URL check failure
REMOTE_BASE_URLS = ['https://someevilsite.com', 'ftp://someevilsite.com']
REMOTE_SITE_URLS = _generate_dynamic_site_urls(REMOTE_BASE_URLS)


class BasicUrl(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_valid_local_site_urls(self):
        """Check known valid static and dynamic URLs"""
        for url in LOCAL_SITE_URLS:
            self.assertTrue(check_local_site_url(DUMMY_CONF, url),
                            "Local site url should succeed for %s" % url)

    def test_invalid_local_site_urls(self):
        """Check known invalid URLs"""
        for url in REMOTE_SITE_URLS:
            self.assertFalse(check_local_site_url(DUMMY_CONF, url),
                             "Local site url should fail for %s" % url)


if __name__ == '__main__':
    testmain()
