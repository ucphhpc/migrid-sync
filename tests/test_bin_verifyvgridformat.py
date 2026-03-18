# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_bin_verifyvgridformat - unit tests for the verifyvgridformat bin script
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Unit tests for bin/verifyvgridformat.py"""

import io
import os
import sys
import unittest
from unittest.mock import patch

from bin.verifyvgridformat import verify_vgrid_format
# Imports required for building the vgrid test fixtures
from mig.shared.vgrid import vgrid_flat_name

# Imports required for the unit tests themselves
from tests.support import MIG_BASE, MigTestCase, ensure_dirs_exist, testmain


class TestBinVerifyVgridFormat(MigTestCase):
    """Unit tests for verify_vgrid_format"""

    def _provide_configuration(self):
        """Return configuration to use"""
        return "testconfig"

    def before_each(self):
        """Set up vgrid directory structure for each test"""
        ensure_dirs_exist(self.configuration.vgrid_home)
        ensure_dirs_exist(self.configuration.vgrid_files_home)
        ensure_dirs_exist(self.configuration.vgrid_files_writable)

    def _make_vgrid(self, name):
        """Create a minimal vgrid directory with an owners file."""
        vgrid_path = os.path.join(self.configuration.vgrid_home, name)
        ensure_dirs_exist(vgrid_path)
        owners_path = os.path.join(vgrid_path, "owners")
        open(owners_path, "w").close()

    def _make_vgrid_files_dir(self, vgrid_name):
        """Create a plain directory at vgrid_files_home for vgrid (legacy)."""
        vgrid_files_path = os.path.join(
            self.configuration.vgrid_files_home, vgrid_name
        )
        ensure_dirs_exist(vgrid_files_path)
        return vgrid_files_path

    def _make_vgrid_files_symlink(self, vgrid_name):
        """Create a symlink at vgrid_files_home pointing into vgrid_files_writable."""
        flat_name = vgrid_flat_name(vgrid_name, self.configuration)
        writable_path = os.path.join(
            self.configuration.vgrid_files_writable, flat_name
        )
        ensure_dirs_exist(writable_path)
        link_path = os.path.join(
            self.configuration.vgrid_files_home, vgrid_name
        )
        # Ensure any intermediate directories exist as plain dirs
        ensure_dirs_exist(os.path.dirname(link_path))
        os.symlink(writable_path, link_path)
        return link_path

    def _make_subvgrid_writable_symlink(self, parent_vgrid, subvgrid):
        """Create a symlink inside the parent's writable dir pointing to the
        sub-vgrid's flat writable dir, as required by the modern nested format.
        Assumes the parent vgrid is already in modern format (symlink exists).
        """
        full_name = os.path.join(parent_vgrid, subvgrid)
        flat_full = vgrid_flat_name(full_name, self.configuration)
        flat_parent = vgrid_flat_name(parent_vgrid, self.configuration)
        writable_target = os.path.join(
            self.configuration.vgrid_files_writable, flat_full
        )
        ensure_dirs_exist(writable_target)
        parent_writable = os.path.join(
            self.configuration.vgrid_files_writable, flat_parent
        )
        ensure_dirs_exist(parent_writable)
        link_path = os.path.join(parent_writable, subvgrid)
        os.symlink(writable_target, link_path)
        return link_path

    def test_no_vgrids_returns_true(self):
        """Verify returns True when no vgrids are present in vgrid_home."""
        result = verify_vgrid_format(self.configuration)
        self.assertTrue(result)

    def test_invalid_vgrid_name_returns_false(self):
        """Verify returns False when named vgrid has no owners file."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = verify_vgrid_format(
                self.configuration, vgrid_name="nonexistent"
            )
        self.assertFalse(result)
        output = captured.getvalue()
        self.assertIn("Invalid vgrid", output)

    def test_top_vgrid_legacy_format_returns_true(self):
        """Verify returns True for top-level vgrid using legacy format (plain dir)."""
        self._make_vgrid("testvgrid")
        self._make_vgrid_files_dir("testvgrid")
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = verify_vgrid_format(self.configuration)
        self.assertTrue(result)
        output = captured.getvalue()
        self.assertIn("legacy format", output)

    def test_top_vgrid_modern_format_returns_true(self):
        """Verify returns True for top-level vgrid using modern format (symlink)."""
        self._make_vgrid("testvgrid")
        self._make_vgrid_files_symlink("testvgrid")
        result = verify_vgrid_format(self.configuration)
        self.assertTrue(result)

    def test_subvgrid_modern_format_returns_true(self):
        """Verify returns True when both top and sub-vgrid use modern format.

        The top-level vgrid has a symlink in vgrid_files_home pointing to its
        writable dir, and inside that writable dir the sub-vgrid entry is also
        a symlink pointing to the sub-vgrid's own flat writable dir."""
        self._make_vgrid("testvgrid")
        self._make_vgrid("testvgrid/subvgrid")
        self._make_vgrid_files_symlink("testvgrid")
        self._make_subvgrid_writable_symlink("testvgrid", "subvgrid")
        result = verify_vgrid_format(self.configuration)
        self.assertTrue(result)

    def test_vgrid_with_missing_files_dir_returns_false(self):
        """Verify returns False when a vgrid exists but has no directory in
        vgrid_files_home."""
        self._make_vgrid("testvgrid")
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            # Intentionally do NOT create any directory in vgrid_files_home
            result = verify_vgrid_format(self.configuration)
        self.assertFalse(result)
        output = captured.getvalue()
        self.assertIn("Missing vgrid files", output)

    def test_subvgrid_with_symlink_inside_plain_dir_top_returns_true(self):
        """Verify returns True when top vgrid uses legacy format but sub-vgrid
        has a symlink inside the plain-dir parent.

        Both vgrid data directories are accessible, so the format is valid
        (though the top-level vgrid is flagged for reformatting)."""
        self._make_vgrid("testvgrid")
        self._make_vgrid("testvgrid/subvgrid")
        # Top vgrid: plain dir (legacy format)
        self._make_vgrid_files_dir("testvgrid")
        # Sub-vgrid: symlink inside the plain-dir parent
        flat_subvgrid = vgrid_flat_name(
            "testvgrid/subvgrid", self.configuration
        )
        writable_target = os.path.join(
            self.configuration.vgrid_files_writable, flat_subvgrid
        )
        ensure_dirs_exist(writable_target)
        subvgrid_link = os.path.join(
            self.configuration.vgrid_files_home, "testvgrid", "subvgrid"
        )
        os.symlink(writable_target, subvgrid_link)

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = verify_vgrid_format(self.configuration)
        self.assertTrue(result)
        output = captured.getvalue()
        self.assertIn("legacy format", output)

    def test_specific_vgrid_name_modern_format_returns_true(self):
        """Verify returns True when targeting a named vgrid in modern format."""
        self._make_vgrid("testvgrid")
        self._make_vgrid_files_symlink("testvgrid")
        result = verify_vgrid_format(
            self.configuration, vgrid_name="testvgrid"
        )
        self.assertTrue(result)

    def test_specific_vgrid_name_legacy_format_returns_true(self):
        """Verify returns True when targeting a named vgrid in legacy format."""
        self._make_vgrid("testvgrid")
        self._make_vgrid_files_dir("testvgrid")
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = verify_vgrid_format(
                self.configuration, vgrid_name="testvgrid"
            )
        self.assertTrue(result)
        output = captured.getvalue()
        self.assertIn("legacy format", output)

    def test_verbose_no_vgrids_produces_no_output(self):
        """Verify verbose mode with no vgrids produces no output and returns True."""
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = verify_vgrid_format(
                self.configuration, verbose=True
            )
        self.assertTrue(result)
        self.assertEqual(captured.getvalue(), "")

    def test_verbose_modern_format_reports_up_to_date(self):
        """Verify verbose mode reports up-to-date for a modern format vgrid."""
        self._make_vgrid("testvgrid")
        self._make_vgrid_files_symlink("testvgrid")
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = verify_vgrid_format(
                self.configuration, verbose=True
            )
        self.assertTrue(result)
        self.assertIn("up to date", captured.getvalue())

    def test_verbose_legacy_format_reports_reformat_commands(self):
        """Verify verbose mode shows reformat commands for legacy format vgrid."""
        self._make_vgrid("testvgrid")
        self._make_vgrid_files_dir("testvgrid")
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            result = verify_vgrid_format(
                self.configuration, verbose=True
            )
        self.assertTrue(result)
        output = captured.getvalue()
        self.assertIn("legacy format", output)
        self.assertIn("commands for reformatting", output)


if __name__ == "__main__":
    testmain()
