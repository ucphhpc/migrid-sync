#
# --- BEGIN_HEADER ---
#
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
from typing import NamedTuple

from bin.addheader import Header
from bin.addheader import __file__ as addheader_file
from bin.addheader import main, parse_file
from tests.support import MigTestCase
from tests.support.iosupp import read_file, read_tree, write_file, write_tree

FILE_CONTENT = '''"""Python module"""
def func(a, b):
    return a + b
'''
HEADER_SHEBANG_LINE = "#!/usr/bin/env python\n"
HEADER_ENCODING_LINE = "# -*- coding: utf-8 -*-\n"
HEADER_FORMAT = """#
# --- BEGIN_HEADER ---
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
FILE_WITH_HEADER_CONTENT = HEADER_FORMAT + "\n" + FILE_CONTENT
DEFAULT_DESC = "[optionally add short module description on this line]"


def add_header(modulename: str, modulebody: str) -> str:
    """Naive function to add a header, used for generating test data."""
    return (
        HEADER_FORMAT % {"modulename": modulename, "description": DEFAULT_DESC}
        + "\n"
        + modulebody
    )


class ParseFileTestCase(NamedTuple):
    msg: str
    filename: str
    content: str
    expected_header: Header
    expected_ok: bool
    block_wrap: bool = False


PARSE_FILE_TEST_CASES: list[ParseFileTestCase] = [
    ParseFileTestCase(
        "package init with shebang encoding and explicit headers",
        "__init__.py",
        (
            "#!/usr/bin/env python\n"
            "# -*- coding: utf-8 -*-\n"
            "#\n"
            "# --- BEGIN_HEADER ---\n"
            "#\n"
            "# __init__ - package marker\n"
            "# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter\n"
            "#\n"
            "# This file is part of MiG.\n"
            "#\n"
            "# MiG is free software: you can redistribute it and/or modify\n"
            "# it under the terms of the GNU General Public License as published by\n"
            "# the Free Software Foundation; either version 2 of the License, or\n"
            "# (at your option) any later version.\n"
            "#\n"
            "# MiG is distributed in the hope that it will be useful,\n"
            "# but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
            "# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
            "# GNU General Public License for more details.\n"
            "#\n"
            "# You should have received a copy of the GNU General Public License\n"
            "# along with this program; if not, write to the Free Software\n"
            "# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.\n"
            "#\n"
            "# -- END_HEADER ---\n"
            "#\n"
            "\n"
            "def module_content():\n"
            "    pass\n"
            "\n"
        ),
        Header(
            module_name="__init__",
            module_description="package marker",
            authors="The MiG Project lead by Brian Vinter",
            copyright_year="2003-2021",
            project_name="MiG",
            interpreter_path="/usr/bin/env python",
            module_encoding="utf-8",
            lines=26,
        ),
        expected_ok=True,
    ),
    ParseFileTestCase(
        "module with shebang and encoding",
        "module_name.py",
        HEADER_SHEBANG_LINE
        + HEADER_ENCODING_LINE
        + FILE_WITH_HEADER_CONTENT
        % {
            "modulename": "module_name",
            "description": "module description",
        },
        Header(
            project_name="MiG",
            module_name="module_name",
            module_description="module description",
            copyright_year="2003-2026",
            authors="The MiG Project by the Science HPC Center at UCPH",
            module_encoding="utf-8",
            interpreter_path="/usr/bin/env python",
            lines=26,
        ),
        expected_ok=True,
    ),
    ParseFileTestCase(
        "module without shebang or encoding",
        "module_name.py",
        FILE_WITH_HEADER_CONTENT
        % {
            "modulename": "module_name",
            "description": "module description",
        },
        Header(
            project_name="MiG",
            module_name="module_name",
            module_description="module description",
            copyright_year="2003-2026",
            authors="The MiG Project by the Science HPC Center at UCPH",
            module_encoding="",
            interpreter_path="",
            lines=24,
        ),
        expected_ok=True,
    ),
    ParseFileTestCase(
        "minimal header",
        "minimal.py",
        (
            "# minimal - a module with a minimal header\n"
            "# Copyright (C) 2003-2026  The MiG Project Team\n"
            "# This file is part of MiG.\n"
            "def module_content():\n"
            "    pass\n"
        ),
        Header(
            module_name="minimal",
            module_description="a module with a minimal header",
            copyright_year="2003-2026",
            authors="The MiG Project Team",
            project_name="MiG",
            interpreter_path="",
            module_encoding="",
            lines=3,
        ),
        expected_ok=True,
    ),
    ParseFileTestCase(
        "override module name",
        "override.py",
        (
            "# wrong_module_name - a module with a wrong name\n"
            "# Copyright (C) 2003-2026  The MiG Project Team\n"
            "# This file is part of MiG.\n"
            "def module_content():\n"
            "    pass\n"
        ),
        Header(
            module_name="override",
            module_description="a module with a wrong name",
            copyright_year="2003-2026",
            authors="The MiG Project Team",
            project_name="MiG",
            interpreter_path="",
            module_encoding="",
            lines=3,
        ),
        expected_ok=True,
    ),
    ParseFileTestCase(
        "no spacing between module name and module description",
        "nospacing.py",
        (
            "# nospacing-a module with no spacing\n"
            "# Copyright (C) 2003-2026  The MiG Project Team\n"
            "# This file is part of MiG.\n"
            "def module_content():\n"
            "    pass\n"
        ),
        Header(
            module_name="nospacing",
            module_description="a module with no spacing",
            copyright_year="2003-2026",
            authors="The MiG Project Team",
            project_name="MiG",
            interpreter_path="",
            module_encoding="",
            lines=3,
        ),
        expected_ok=True,
    ),
    ParseFileTestCase(
        "allow empty line after encoding",
        "emptyline.py",
        (
            "# -*- coding: utf-8 -*-\n"
            "\n"
            "# emptyline - a module with an empty line after encoding\n"
            "# Copyright (C) 2003-2026  The MiG Project Team\n"
            "# This file is part of MiG.\n"
            "def module_content():\n"
            "    pass\n"
        ),
        Header(
            module_name="emptyline",
            module_description="a module with an empty line after encoding",
            copyright_year="2003-2026",
            authors="The MiG Project Team",
            project_name="MiG",
            interpreter_path="",
            module_encoding="utf-8",
            lines=5,
        ),
        expected_ok=True,
    ),
    ParseFileTestCase(
        "do not allow two empty lines after encoding",
        "twoemptylines.py",
        (
            "# -*- coding: utf-8 -*-\n"
            "\n"
            "\n"
            "# twoemptylines - a module with two empty lines after encoding\n"
            "# Copyright (C) 2003-2026  The MiG Project Team\n"
            "# This file is part of MiG.\n"
            "def module_content():\n"
            "    pass\n"
        ),
        Header(
            module_name="twoemptylines",
            module_description="",
            copyright_year="",
            authors="",
            project_name="",
            interpreter_path="",
            module_encoding="utf-8",
            lines=1,
        ),
        expected_ok=False,
    ),
    ParseFileTestCase(
        "block wrapped",
        "file.js",
        (
            "/*\n"
            "\n"
            "  # block - a js file with block wrapped header\n"
            "  # Copyright (C) 2003-2026  The MiG Project Team\n"
            "  # This file is part of MiG.\n"
            "\n"
            "*/\n"
            "function jsfun() {\n"
            "   return 123;\n"
            "}\n"
        ),
        Header(
            module_name="block",
            module_description="a js file with block wrapped header",
            copyright_year="2003-2026",
            authors="The MiG Project Team",
            project_name="MiG",
            interpreter_path="",
            module_encoding="",
            lines=7,
        ),
        expected_ok=True,
        block_wrap=True,
    ),
    ParseFileTestCase(
        "should not eat docstring",
        "keeping_docstring.py",
        (
            "#!/usr/bin/python3\n"
            "# -*- coding: utf-8 -*-\n"
            "#\n"
            "# keeping_docstring - should not eat docstring\n"
            "# Copyright (C) 2020-2021  Jonas Bardino\n"
            "#\n"
            "# This file is part of MiG.\n"
            "#\n"
            "# MiG is free software: you can redistribute it and/or modify\n"
            "# it under the terms of the GNU General Public License as published by\n"
            "# the Free Software Foundation; either version 2 of the License, or\n"
            "# (at your option) any later version.\n"
            "#\n"
            "# MiG is distributed in the hope that it will be useful,\n"
            "# but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
            "# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
            "# GNU General Public License for more details.\n"
            "#\n"
            "# You should have received a copy of the GNU General Public License\n"
            "# along with this program; if not, write to the Free Software\n"
            "# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.\n"
            "\n"
            '"""Reformat all python source code to python 3 friendly format using the\n'
            "futurize tool available from\n"
            "http://python-future.org/index.html\n"
            "\n"
            "A few manual tweaks are needed afterwards to avoid breakage.\n"
            '"""\n'
        ),
        Header(
            module_name="keeping_docstring",
            module_description="should not eat docstring",
            copyright_year="2020-2021",
            authors="Jonas Bardino",
            project_name="MiG",
            interpreter_path="/usr/bin/python3",
            module_encoding="utf-8",
            lines=21,
        ),
        expected_ok=True,
    ),
]


class TestParseFile(MigTestCase):
    """Unit tests for parse_file function."""

    def test_parse_file(self) -> None:
        for (
            msg,
            fname,
            content,
            expected,
            expected_ok,
            block_wrap,
        ) in PARSE_FILE_TEST_CASES:
            with self.subTest(msg):
                dir = self.temppath(self.id() + "_" + msg)
                write_file(dir, fname, content)

                ok, actual = parse_file(os.path.join(dir, fname), block_wrap)

                self.assertEqual(ok, expected_ok)
                self.assertEqual(actual, expected)


class TestHeader(MigTestCase):
    """Unit tests for Header class."""

    def test_format(self):
        header: Header = Header(
            project_name="MiG",
            module_name="module_name",
            module_description="module description",
            copyright_year="2003-2026",
            authors="The MiG Project by the Science HPC Center at UCPH",
            module_encoding="utf-8",
            interpreter_path="/usr/bin/env python",
        )

        actual = header.format()

        expected = (
            HEADER_SHEBANG_LINE
            + HEADER_ENCODING_LINE
            + HEADER_FORMAT
            % {
                "modulename": header.module_name,
                "description": header.module_description,
            }
        )
        self.assertEqual(actual, expected)

    def test_format_parse(self) -> None:
        dir = self.temppath(self.id())
        header: Header = Header(
            project_name="MiG",
            module_name="module_name",
            module_description="module description",
            copyright_year="2003-2026",
            authors="The MiG Project by the Science HPC Center at UCPH",
            module_encoding="utf-8",
            interpreter_path="/usr/bin/env python",
        )
        fname = header.module_name + ".py"
        formatted_header = header.format()
        header.lines = len(formatted_header.splitlines())

        write_file(dir, fname, formatted_header)
        ok, parsed = parse_file(os.path.join(dir, fname), block_wrap=False)

        self.assertTrue(ok)
        self.assertEqual(parsed, header)


class TestMain(MigTestCase):
    """Unit tests for the main function."""

    target_dir: str

    def before_each(self) -> None:
        self.target_dir = self.temppath(self.id(), ensure_dir=True)

    def test_adds_header_to_file_without_header(self) -> None:
        fname = "file_without_header.py"
        write_file(self.target_dir, fname, FILE_CONTENT)

        main([addheader_file, self.target_dir])

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

        main([addheader_file, self.target_dir])

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

            main([addheader_file])

            actual_content = read_file(self.target_dir, fname)
            self.assertEqual(content, actual_content)
        finally:
            os.chdir(oldcwd)

    def test_adds_headers_and_backs_up_unlicensed_files(self) -> None:
        gdp_files = {
            "file1.py": "content of file shared/gdp/file1.py",
            "file2.py": "content of file shared/gdp/file2.py",
        }
        shared_files = {
            "file.py": "content of shared/file.py",
        }
        initial = {
            "shared": shared_files | {"gdp": gdp_files},
        }
        write_tree(self.target_dir, initial)

        main([addheader_file, self.target_dir])

        actual = read_tree(self.target_dir)
        expected = {
            "shared": {
                "file.py.unlicensed": shared_files["file.py"],
                "file.py": add_header(
                    "file", modulebody=shared_files["file.py"]
                ),
                "gdp": {
                    "file1.py.unlicensed": gdp_files["file1.py"],
                    "file1.py": add_header(
                        "file1",
                        gdp_files["file1.py"],
                    ),
                    "file2.py.unlicensed": gdp_files["file2.py"],
                    "file2.py": add_header(
                        "file2",
                        gdp_files["file2.py"],
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
            FILE_CONTENT + format_string_line,
        )

        main([addheader_file, self.target_dir])

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
