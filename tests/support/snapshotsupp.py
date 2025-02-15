# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# snapahotsupp - snapshot helpers for unit tests
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Test support code for the use of snapshots in tests."""

import difflib
import errno
import re
import os

from tests.support.suppconst import TEST_BASE

TEST_SNAPSHOTS_DIR = os.path.join(TEST_BASE, "snapshots")

try:
    os.mkdir(TEST_SNAPSHOTS_DIR)
except OSError as direxc:
    if direxc.errno != errno.EEXIST:  # FileExistsError
        raise


def _delimited_lines(value):
    """Break a value by newlines into lines suitable for diffing."""

    found_index = -1
    from_index = 0
    last_index = len(value) - 1

    lines = []

    while from_index < last_index:
        found_index = value.find('\n', from_index)
        if found_index == -1:
            break
        found_index += 1
        lines.append(value[from_index:found_index])
        from_index = found_index

    if from_index != last_index and found_index == -1:
        lines.append(value[from_index:])

    return lines


def _force_refresh_snapshots():
    """Check whether the environment specifies snapshots should be refreshed."""

    env_refresh_snapshots = os.environ.get('REFRESH_SNAPSHOTS', 'no').lower()
    return env_refresh_snapshots in ('true', 'yes', '1')


class SnapshotAssertMixin:
    """Custom assertions alowing the use of snapshots within tests."""

    def assertSnapshot(self, actual_content, extension=None):
        """Load a snapshot corresponding to the named test and check that its
        content, which is th expectatoin, matches what was actually given. In
        the case a snapshot does not exist it is saved on first invocation."""

        assert extension is not None

        file_name = ''.join([self._testMethodName, ".", extension])
        file_path = os.path.join(TEST_SNAPSHOTS_DIR, file_name)

        if not os.path.isfile(file_path) or _force_refresh_snapshots():
            # first execution, save snapshot only
            with open(file_path, "w") as snapshot_file:
                snapshot_file.write(actual_content)
            return

        with open(file_path) as snapshot_file:
            expected_content = snapshot_file.read()

        if actual_content == expected_content:
            # they match, nothing more to do
            return

        udiff = difflib.unified_diff(
            _delimited_lines(expected_content),
            _delimited_lines(actual_content),
            'expected',
            'actual'
        )
        raise AssertionError(
            "content did not match snapshot\n\n%s" % (''.join(udiff),))
