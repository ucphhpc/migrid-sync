#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
#
# addheader - add license header to all code modules.
# Copyright (C) 2009-2026  The MiG Project by the Science HPC Center at UCPH
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

"""Search code tree and add the required header to all python modules."""

from __future__ import annotations

import datetime
import fnmatch
import logging
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import mig to assure we have a suitable python module load path
try:
    import mig
except ImportError:
    mig = None  # type: ignore[assignment]

if mig is None:
    # NOTE: include cmd parent path in search path for mig.X imports to work
    MIG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
    logger.info("Using mig installation in %s", MIG_ROOT)
    sys.path.append(MIG_ROOT)

from mig.shared.fileio import read_file_lines, read_head_lines, write_file_lines
from mig.shared.projcode import CODE_ROOT, JAVASCRIPT, list_code_files


@dataclass
class Header:
    module_name: str = ""
    module_description: str = ""
    project_name: str = ""
    authors: str = ""
    copyright_year: str = ""
    interpreter_path: str = ""
    module_encoding: str = ""
    lines: int = 0

    def overlay(self, other: Header) -> None:
        for field in fields(self):
            if not getattr(self, field.name):
                setattr(self, field.name, getattr(other, field.name))

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def format(
        self,
        explicit_border: bool = True,
        block_wrap: bool = False,
    ) -> str:
        header = LICENSE_TEXT % self.to_dict()

        if explicit_border:
            header = EXPLICIT_BORDER_FORMAT % (BEGIN_MARKER, header, END_MARKER)

        if block_wrap:
            header = BLOCK_WRAP_FORMAT % header

        if not block_wrap and self.module_encoding:
            header = f"# -*- coding: {self.module_encoding} -*-\n" + header

        if self.interpreter_path:
            header = f"#!{self.interpreter_path}\n" + header

        return header


# Modify these to fit actual project
PROJ_CONSTS = Header(
    project_name="MiG",
    module_name="",
    module_description="[optionally add short module description on this line]",
    authors="The MiG Project by the Science HPC Center at UCPH",
    copyright_year="2003-%d" % datetime.date.today().year,
    # Set interpreter path and file encoding if not already set in source files
    # Use empty string to leave them alone.
    interpreter_path="/usr/bin/env python",
    module_encoding="",
)


BEGIN_MARKER = "--- BEGIN_HEADER ---"
END_MARKER = "--- END_HEADER ---"
BACKUP_SUFFIX = ".unlicensed"

# Mandatory copyright notice for any license
LICENSE_TEXT = """#
# %(module_name)s - %(module_description)s
# Copyright (C) %(copyright_year)s  %(authors)s
"""

# This is the actual GPL version 2 header to match
# http://opensource.org/licenses/GPL-2.0
# Replace text if another license is desired.
# Additionally add a file called COPYING in the root of the distributed source
# with a verbatim copy of the license text:
# wget -O COPYING http://www.gnu.org/licenses/gpl2.txt

LICENSE_TEXT += """#
# This file is part of %(project_name)s.
#
# %(project_name)s is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# %(project_name)s is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA."""

EXPLICIT_BORDER_FORMAT = """#
# %s
#
%s
#
# %s
#
"""

BLOCK_WRAP_FORMAT = """
/*
%s
*/
"""

COMPLETE_MESSAGE = """Added license headers to code in '%s'"

Don't forget to include COPYING file in root of source, e.g. run:
wget -O COPYING http://www.gnu.org/licenses/gpl2.txt
if using the default GPL v2 license here."""

RE_PYTHON_ENCODING = re.compile(r"# -\*- coding: ([a-zA-Z0-9-]+) -\*-")
RE_MODULE_LINE = re.compile(r"# ([^ ]+) *\- *(.+)")
RE_COPYRIGHT_LINE = re.compile(
    r"# Copyright \(C\) (20[0-9]{2}(-20[0-9]{2})?)  ?(.+)"
)
RE_PROJECT_LINE = re.compile(r"# This file is part of (.+).")


def parse_file(
    path: str, block_wrap: bool, preamble_lines: int = 100
) -> tuple[bool, Header]:
    logger.debug("trying to parse module header of %r", path)

    head_lines = read_head_lines(path, preamble_lines, None)
    header_lines: list[str] = []
    block_lines: Optional[int] = None
    if block_wrap:
        block_lines, header_lines = _parse_block_wrap(head_lines)
    else:
        header_lines = _filter_header_lines(head_lines)

    ok, parsed = _parse_lines(header_lines)

    if path.endswith(".py"):
        parsed.module_name = os.path.basename(path).removesuffix(".py")

    # if it was wrapped in a block, we count all block lines
    if block_lines is not None:
        parsed.lines = block_lines

    return ok, parsed


def _filter_header_lines(head_lines: list[str]) -> list[str]:
    header_lines: list[str] = []
    for ln in head_lines:
        if ln.startswith("#") or ln == "\n":
            header_lines.append(ln)
        else:
            break
    return header_lines


def _parse_block_wrap(head_lines: list[str]) -> tuple[int, list[str]]:
    block_wrap_opened = False
    block_lines = 0
    block_content: list[str] = []
    for ln in head_lines:
        ln = ln.strip()
        block_lines += 1
        if not block_wrap_opened:
            if ln == "/*":
                block_wrap_opened = True
            continue
        if ln == "*/":
            break
        else:
            # prefix all non-comment lines within the block in order to ease
            # parsing as a non-block comment
            prefix = "" if ln.startswith("#") else "#"
            block_content.append(prefix + ln)
    return block_lines, block_content

    for ln in head_lines:
        ln = ln.strip()
        if not hash_quote_begun:
            if ln.startswith("#"):
                hash_quote_begun = True
                header_lines.append(ln)
            else:
                # ignore other block wrapped lines
                extra_lines += 1
            continue
        if ln.startswith("#") or ln == "\n":
            header_lines.append(ln)
        elif ln == "*/":
            extra_lines += 1
            break


def _parse_lines(header_lines: list[str]) -> tuple[bool, Header]:
    parsed = Header()

    if not header_lines:
        return False, parsed

    # try to parse shebang
    if header_lines[parsed.lines].startswith("#!"):
        parsed.interpreter_path = header_lines[parsed.lines][2:].strip()
        parsed.lines += 1

    if parsed.lines >= len(header_lines):
        return False, parsed

    # try to parse module encoding
    if encoding_match := RE_PYTHON_ENCODING.match(header_lines[parsed.lines]):
        parsed.module_encoding = encoding_match.group(1)
        parsed.lines += 1

    # specifically allow a single empty line after the encoding line, if it is
    # then followed by a commented out line, as that has been a common
    # formatting error in the migrid-sync code-base
    if (
        parsed.module_encoding != ""
        and parsed.lines + 1 < len(header_lines)
        and header_lines[parsed.lines].strip() == ""
        and header_lines[parsed.lines + 1].startswith("#")
    ):
        parsed.lines += 1

    parsed.lines = _parse_header_consume_empty_lines(header_lines, parsed.lines)
    if parsed.lines >= len(header_lines):
        return False, parsed

    # consume BEGIN_MARKER
    if header_lines[parsed.lines].strip() == "# " + BEGIN_MARKER:
        parsed.lines += 1

    parsed.lines = _parse_header_consume_empty_lines(header_lines, parsed.lines)
    if parsed.lines >= len(header_lines):
        return False, parsed

    # try to parse module name and description
    if module_ln_match := RE_MODULE_LINE.match(header_lines[parsed.lines]):
        parsed.module_name = module_ln_match.group(1)
        parsed.module_description = module_ln_match.group(2)
        parsed.lines += 1
    else:
        logger.debug("could not parse module line")
        return False, parsed

    parsed.lines = _parse_header_consume_empty_lines(header_lines, parsed.lines)
    if parsed.lines >= len(header_lines):
        return False, parsed

    # try to parse copyright line
    if copyright_ln_match := RE_COPYRIGHT_LINE.match(
        header_lines[parsed.lines]
    ):
        parsed.copyright_year = copyright_ln_match.group(1)
        parsed.authors = copyright_ln_match.group(3)
        parsed.lines += 1
    else:
        logger.debug("could not parse copyright line")
        return False, parsed

    parsed.lines = _parse_header_consume_empty_lines(header_lines, parsed.lines)
    if parsed.lines >= len(header_lines):
        return False, parsed

    # try to parse project line
    if project_ln_match := RE_PROJECT_LINE.match(header_lines[parsed.lines]):
        parsed.project_name = project_ln_match.group(1)
        parsed.lines += 1
    else:
        logger.debug("could not parse project line")
        return False, parsed

    # consume the rest of the header
    while parsed.lines < len(header_lines) and header_lines[
        parsed.lines
    ].startswith("#"):
        parsed.lines += 1

    return True, parsed


def check_header(path: str, opts: Header, preamble_lines: int = 100) -> bool:
    """Check if path has a credible license header and otherwise adds one.

    Only looks inside the first preamble_lines of the file and if it doesn't
    find an existing license header there it adds a standard header populated
    with project variables from `opts`.
    """
    module_preamble = "\n".join(read_head_lines(path, preamble_lines, None))
    return BEGIN_MARKER in module_preamble or opts["authors"] in module_preamble


def _parse_header_consume_empty_lines(header_lines: list[str], ptr: int) -> int:
    while ptr < len(header_lines) and header_lines[ptr].strip() == "#":
        ptr += 1
    return ptr


def add_header(
    path: str,
    explicit_border: bool = True,
    block_wrap: bool = False,
    force_update: bool = False,
) -> None:
    """
    Add the required copyright and license header to module in path.

    Also creates a '.unlicensed' backup copy of each file changed.

    Args:
        path: Path to the file to add header to.
        opts: Header options that are used to format the header.
        explicit_border: Optionally wrap the license text in begin and end
            lines that are easy to find, so that license can be updated or
            replaced later.
        block_wrap: Optionally wrap license lines in block comments where
            needed, for example for for languages like C and JavaScript where
            the per-line commenting using hash (#) does not work.
        force_update: Optionally force updating the given header, using the
            project defaults and the parsed values to update any existing
            header.
    """
    ok, header = parse_file(path, block_wrap)

    if ok and not force_update:
        logger.info("Skip %s with existing header", path)
        return

    module_lines = read_file_lines(path, None)
    if not write_file_lines(module_lines, path + BACKUP_SUFFIX, None):
        logger.warning("Failed to create backup of %s - skip!", path)
        return False

    header.overlay(PROJ_CONSTS)
    header.module_name = os.path.basename(path).removesuffix(".py")

    # no shebang if executable bit is not set
    if not os.access(path, os.X_OK):
        header.interpreter_path = ""

    header_lines = header.format(
        explicit_border=explicit_border, block_wrap=block_wrap
    ).splitlines(keepends=True)

    if ok and force_update:
        # remove existing parsed header
        module_lines = module_lines[header.lines :]

    # Make sure there's a blank line between license header and code
    if module_lines and module_lines[0].strip():
        header_lines.append("\n")

    if not write_file_lines(header_lines + module_lines, path, None):
        logger.warning("Failed to write %s with added headers!", path)
        return

    logger.debug("Wrote %s with added headers", path)


def find_matching_project_pattern(src_path: str, mig_code_base: str) -> Optional[str]:
    for pattern in list_code_files():
        pattern = os.path.normpath(
            os.path.join(mig_code_base, CODE_ROOT, pattern)
        )
        # logger.debug("Testing %s against %s", src_path, pattern)
        if src_path == pattern or fnmatch.fnmatch(src_path, pattern):
            return pattern
        # else:
        # logger.debug("Source path %s does not match %s", src_path, pattern)
    return None


def main(argv: list[str], environ: Optional[Mapping[str, str]] = None) -> None:
    """Run header addition for given argv."""

    environ = environ or {}
    logging.basicConfig(level=environ.get("LOG_LEVEL", "warning").upper())

    target = os.getcwd()
    if len(argv) > 1:
        target = os.path.abspath(argv[1])

    mig_code_base = target
    if len(argv) > 2:
        mig_code_base = os.path.abspath(argv[2])

    force_update = environ.get("ADDHEADER_FORCE_UPDATE", "").upper() == "TRUE"

    for root, _, files in os.walk(target):
        # skip all dot dirs - they are from repos etc and _not_ jobs
        if root.find(os.sep + ".") != -1:
            continue

        for name in files:
            src_path = os.path.join(root, name)
            if os.path.islink(src_path):
                continue

            if src_path.endswith(BACKUP_SUFFIX):
                continue

            if "venv" in src_path:
                continue

            pattern = find_matching_project_pattern(src_path, mig_code_base)
            if pattern is None:
                continue

            logger.info("Matched %s against %s", src_path, pattern)
            add_header(
                src_path,
                block_wrap=src_path.endswith(".js"),
                force_update=force_update,
            )

    print(COMPLETE_MESSAGE % target)


if __name__ == "__main__":
    main(sys.argv, os.environ)
