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


class TestLegacyUserInterface(MigTestCase):
    """Test coverage of the helper pointed to in the name"""

    def _provide_configuration(self):
        return "testconfig"

    def before_each(self):
        self.configuration.user_interface = ["V4", "V3", "V2", "V1"]
        self.legacy = ["V1", "V2"]

    def test_legacy_user_interface_true_for_v1(self):
        user_settings = {"USER_INTERFACE": "V1"}
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertTrue(result)

    def test_legacy_user_interface_true_for_v2(self):
        user_settings = {"USER_INTERFACE": "V2"}
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertTrue(result)

    def test_legacy_user_interface_false_for_v3(self):
        user_settings = {"USER_INTERFACE": "V3"}
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertFalse(result)

    def test_legacy_user_interface_false_for_v4(self):
        user_settings = {"USER_INTERFACE": "V4"}
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertFalse(result)

    def test_legacy_user_interface_false_for_v1_if_not_available(self):
        user_settings = {"USER_INTERFACE": "V1"}
        self.configuration.user_interface = [
            i for i in self.configuration.user_interface if i != "V1"
        ]
        expect_warn = "ignoring invalid saved user interface value"
        with self.assertLogs(level="WARNING") as log_capture:
            result = htmlgen.legacy_user_interface(
                self.configuration, user_settings, legacy_versions=self.legacy
            )
        self.assertFalse(result)
        self.assertTrue(any(expect_warn in msg for msg in log_capture.output))

    def test_legacy_user_interface_false_for_v2_if_not_available(self):
        user_settings = {"USER_INTERFACE": "V2"}
        self.configuration.user_interface = [
            i for i in self.configuration.user_interface if i != "V2"
        ]
        expect_warn = "ignoring invalid saved user interface value"
        with self.assertLogs(level="WARNING") as log_capture:
            result = htmlgen.legacy_user_interface(
                self.configuration, user_settings, legacy_versions=self.legacy
            )
        self.assertFalse(result)
        self.assertTrue(any(expect_warn in msg for msg in log_capture.output))

    def test_legacy_user_interface_false_for_v1_if_not_configured(self):
        user_settings = {"USER_INTERFACE": "V1"}
        self.configuration.user_interface = []
        expect_warn = "ignoring invalid saved user interface value"
        with self.assertLogs(level="WARNING") as log_capture:
            result = htmlgen.legacy_user_interface(
                self.configuration, user_settings, legacy_versions=self.legacy
            )
        self.assertFalse(result)
        self.assertTrue(any(expect_warn in msg for msg in log_capture.output))

    def test_legacy_user_interface_false_for_v2_if_not_configured(self):
        user_settings = {"USER_INTERFACE": "V2"}
        self.configuration.user_interface = []
        expect_warn = "ignoring invalid saved user interface value"
        with self.assertLogs(level="WARNING") as log_capture:
            result = htmlgen.legacy_user_interface(
                self.configuration, user_settings, legacy_versions=self.legacy
            )
        self.assertFalse(result)
        self.assertTrue(any(expect_warn in msg for msg in log_capture.output))

    def test_legacy_user_interface_false_for_v3_if_not_configured(self):
        user_settings = {"USER_INTERFACE": "V3"}
        self.configuration.user_interface = []
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertFalse(result)

    def test_legacy_user_interface_false_for_v4_if_not_configured(self):
        user_settings = {"USER_INTERFACE": "V4"}
        self.configuration.user_interface = []
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertFalse(result)

    def test_legacy_user_interface_false_and_silent_for_empty_default(self):
        user_settings = {"USER_INTERFACE": ""}
        self.configuration.user_interface = []
        usual_warn = "ignoring invalid saved user interface value"
        with self.assertLogs(level="WARNING") as log_capture:
            result = htmlgen.legacy_user_interface(
                self.configuration, user_settings, legacy_versions=self.legacy
            )
        self.assertFalse(result)
        self.assertFalse(any(usual_warn in msg for msg in log_capture.output))

    def test_legacy_user_interface_false_if_unset_when_unconfigured(self):
        user_settings = {}
        self.configuration.user_interface = []
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertFalse(result)

    def test_legacy_user_interface_false_if_unset_with_modern_conf(self):
        user_settings = {}
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertFalse(result)

    def test_legacy_user_interface_true_if_unset_with_legacy_conf(self):
        user_settings = {}
        self.configuration.user_interface = ["V2", "V3"]
        result = htmlgen.legacy_user_interface(
            self.configuration, user_settings, legacy_versions=self.legacy
        )
        self.assertTrue(result)
