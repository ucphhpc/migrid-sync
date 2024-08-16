# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# support - helper functions for unit testing
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

"""Infrastruture to support assertion over a range of values.
"""

class NoBlockError(AssertionError):
    pass

class NoCasesError(AssertionError):
    pass

class AssertOver:
    def __init__(self, values=None, testcase=None):
        self._attempts = None
        self._consulted = False
        self._ended = False
        self._started = False
        self._testcase = testcase
        self._values = iter(values)

    def __call__(self, block):
        self._attempts = []

        try:
            while True:
                block_value = next(self._values)
                attempt_info = self._execute_block(block, block_value)
                self.record_attempt(attempt_info)
        except StopIteration:
            pass

        self._ended = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._attempts is None:
            raise NoBlockError()

        if len(self._attempts) == 0:
            raise NoCasesError()

        if not any(self._attempts):
            return True

        value_lines = ["- <%r> : %s" % (attempt[0], str(attempt[1])) for attempt in self._attempts if attempt]
        raise AssertionError("assertions raised for the following values:\n%s" % '\n'.join(value_lines))

    def record_attempt(self, attempt_info):
        return self._attempts.append(attempt_info)

    def to_check_callable(self):
        def raise_unless_consuted():
            if not self._consulted:
                raise AssertionError("no examiniation made of assertion of multiple values")
        return raise_unless_consuted

    def assert_success(self):
        self._consulted = True
        assert not any(self._attempts)

    @classmethod
    def _execute_block(cls, block, block_value):
        try:
            block.__call__(block_value)
            return None
        except Exception as blockexc:
            return (block_value, blockexc,)
