#
# --- BEGIN_HEADER ---
#
# test_bin_addheader - unit tests for the bin.addheader module
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
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# --- END_HEADER ---
#

"""Unit tests of the bin.addheader module."""

import os

from bin.addheader import __file__ as addheader_module_file
from bin.addheader import main
from tests.support import MigTestCase, temppath
from tests.support.iosupp import read_file, read_tree, write_file, write_tree

FILE_WITHOUT_HEADER_CONTENT = '''"""Python module without header"""
def func(a, b):
    return a + b
'''
HEADER_FORMAT = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
#
# %(modulename)s - %(description)s
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
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# --- END_HEADER ---
#

"""
FILE_WITH_HEADER_CONTENT = HEADER_FORMAT + FILE_WITHOUT_HEADER_CONTENT
DEFAULT_DESC = "[optionally add short module description on this line]"


def add_header(modulename: str, modulebody: str) -> str:
    """Naive function to add a header, used for generating test data."""
    return (
        HEADER_FORMAT % {"modulename": modulename, "description": DEFAULT_DESC}
        + modulebody
    )


class TestMain(MigTestCase):
    """Unit tests for the main function."""

    target_dir: str

    def before_each(self) -> None:
        self.maxDiff = None
        self.target_dir = temppath(self.id(), self, ensure_dir=True)

    def test_adds_header_to_file_without_header(self) -> None:
        fname = "file_without_header.py"
        write_file(self.target_dir, fname, FILE_WITHOUT_HEADER_CONTENT)

        main([addheader_module_file, self.target_dir])

        actual_content = read_file(self.target_dir, fname)
        expected_content = FILE_WITH_HEADER_CONTENT % {
            "modulename": "file_without_header",
            "description": "[optionally add short module description on this line]",
        }
        self.assertEqual(expected_content, actual_content)

    def test_does_not_change_file_with_header(self) -> None:
        fname = "file_with_header.py"
        content = FILE_WITH_HEADER_CONTENT % {
            "modulename": "file_with_header",
            "description": "pre-existing description",
        }
        write_file(self.target_dir, fname, content)

        main([addheader_module_file, self.target_dir])

        actual_content = read_file(self.target_dir, fname)
        self.assertEqual(content, actual_content)

    def test_updates_files_in_cwd_if_no_path_arg_is_given(self) -> None:
        oldcwd = os.getcwd()
        try:
            os.chdir(self.target_dir)
            fname = "file_with_header.py"
            content = FILE_WITH_HEADER_CONTENT % {
                "modulename": "file_with_header",
                "description": "pre-existing description",
            }
            write_file(self.target_dir, fname, content)

            main([addheader_module_file])

            actual_content = read_file(self.target_dir, fname)
            self.assertEqual(content, actual_content)
        finally:
            os.chdir(oldcwd)

    def test_adds_headers_and_backs_up_unlicensed_files(self) -> None:
        initial = {
            "shared": {
                "file.py": "content of shared/file.py",
                "gdp": {
                    "file1.py": "content of file shared/gdp/file1.py",
                    "file2.py": "content of file shared/gdp/file2.py",
                },
            },
        }
        write_tree(self.target_dir, initial)

        main([addheader_module_file, self.target_dir])

        actual = read_tree(self.target_dir)
        expected = {
            "shared": {
                "file.py.unlicensed": initial["shared"]["file.py"],
                "file.py": add_header("file", initial["shared"]["file.py"]),
                "gdp": {
                    "file1.py.unlicensed": initial["shared"]["gdp"]["file1.py"],
                    "file1.py": add_header(
                        "file1",
                        initial["shared"]["gdp"]["file1.py"],
                    ),
                    "file2.py.unlicensed": initial["shared"]["gdp"]["file2.py"],
                    "file2.py": add_header(
                        "file2",
                        initial["shared"]["gdp"]["file2.py"],
                    ),
                },
            },
        }
        self.assertEqual(expected, actual)

    def test_adds_header_to_file_with_format_string_in_module_body(
        self,
    ) -> None:
        fname = "file_without_header_with_format_string.py"
        format_string_line = '\nformat_string = "%s"\n'
        write_file(
            self.target_dir,
            fname,
            FILE_WITHOUT_HEADER_CONTENT + format_string_line,
        )

        main([addheader_module_file, self.target_dir])

        actual_content = read_file(self.target_dir, fname)
        expected_content = (
            FILE_WITH_HEADER_CONTENT
            % {
                "modulename": "file_without_header_with_format_string",
                "description": DEFAULT_DESC,
            }
            + format_string_line
        )
        self.assertEqual(expected_content, actual_content)
