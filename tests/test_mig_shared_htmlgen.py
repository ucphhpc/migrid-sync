#
# --- BEGIN_HEADER ---
#
# test_mig_shared_htmlgen - unit tests for htmlgen functions
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# --- END_HEADER ---
#

"""Unit tests of the mig.shared.htmlgen module."""

from collections import defaultdict

from lxml import etree

from mig.shared import htmlgen
from tests.support import MigTestCase


class TestGetXgiHtmlHeader(MigTestCase):
    """Unit tests of the get_xgi_html_header function."""

    def _provide_configuration(self) -> str:
        return "testconfig"

    def test_user_menu_setup_disabled_if_setup_app_not_specified(self):
        result = htmlgen.get_xgi_html_header(
            configuration=self.configuration,
            title="title",
            header="header",
            script_map=defaultdict(str),
        )

        parsed = etree.HTML(result)
        links = parsed.findall('.//div[@id="userMenu"]//a[@class]')
        link_setup = next(
            link
            for link in links
            if "link-setup" in link.attrib["class"].split()
        )

        self.assertIn("disable-link", link_setup.attrib["class"].split())

    def test_user_menu_setup_enabled_if_setup_app_specified(self):
        result = htmlgen.get_xgi_html_header(
            configuration=self.configuration,
            title="title",
            header="header",
            script_map=defaultdict(str),
            base_menu=["setup"],
        )

        parsed = etree.HTML(result)
        links = parsed.findall('.//div[@id="userMenu"]//a[@class]')
        link_setup = next(
            link
            for link in links
            if "link-setup" in link.attrib["class"].split()
        )

        self.assertNotIn("disable-link", link_setup.attrib["class"].split())
