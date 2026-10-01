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

import importlib
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

    def test_user_interface_v4_templates_init_javascript_loader(self):
        """Test that the template base_package javascript bootstrap script is
        inserted into the DOM if the underlying package provides it.
        """

        active_templates = self.configuration.division(section_name="TEMPLATES")
        base_packages = active_templates.base_packages
        self.assertNotEqual(base_packages, "")

        result = htmlgen.get_xgi_html_header(
            configuration=self.configuration,
            title="title",
            header="header",
            script_map=defaultdict(str),
            base_menu=["setup"],
            user_settings={"USER_INTERFACE": "V4"},
        )

        parsed = etree.HTML(result)
        scripts = parsed.findall(".//script[@src]")

        # Check if the expected loader scripts for each base_package are inserted
        # into the DOM
        for package in base_packages:
            imported_package = importlib.import_module(package)
            self.assertIsNotNone(imported_package)
            self.assertTrue(hasattr(imported_package, "INIT_JAVASCRIPT_LOADER"))
            self.assertIsInstance(imported_package.INIT_JAVASCRIPT_LOADER, str)
            expected_loader_script = imported_package.INIT_JAVASCRIPT_LOADER

            script_loader = next(
                script
                for script in scripts
                if expected_loader_script in script.attrib["src"]
            )

            self.assertEqual(
                script_loader.attrib["src"],
                "/assets/%s/%s" % (package, expected_loader_script),
            )

    def test_user_interface_non_v4_templates_init_javascript_loader(self):
        """Test that no script src is added to DOM if the user interface is not V4"""
        result = htmlgen.get_xgi_html_header(
            configuration=self.configuration,
            title="title",
            header="header",
            script_map=defaultdict(str),
            base_menu=["setup"],
            user_settings={"USER_INTERFACE": "V3"},
        )

        parsed = etree.HTML(result)
        scripts = parsed.findall(".//script[@src]")
        self.assertEqual(len(scripts), 0)
