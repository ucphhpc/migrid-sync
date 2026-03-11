# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_safeeval - unit test of the corresponding mig shared module
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Unit test safeeval functions"""

import os
import sys

from mig.shared.safeeval import *
from tests.support import MigTestCase, testmain

PWD_STR = os.getcwd()
PWD_BYTES = PWD_STR.encode("utf8")


class MigSharedSafeeval(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_subprocess_call(self):
        """Check that pwd call without args succeeds"""
        retval = subprocess_call(["pwd"], stdout=subprocess_pipe)
        self.assertEqual(retval, 0, "unexpected subprocess call pwd retval")

    def test_subprocess_call_invalid(self):
        """Check that pwd call with invalid arg fails"""
        retval = subprocess_call(["pwd", "-h"], stderr=subprocess_pipe)
        self.assertNotEqual(
            retval, 0, "unexpected subprocess call nosuchcommand retval"
        )

    def test_subprocess_check_output(self):
        """Check that pwd command output matches getcwd as bytes"""
        data = subprocess_check_output(
            ["pwd"], stdout=subprocess_pipe, stderr=subprocess_pipe
        ).strip()
        self.assertEqual(
            data, PWD_BYTES, "mismatch in subprocess check pwd output"
        )

    def test_subprocess_check_output_text(self):
        """Check that pwd command output matches getcwd as string"""
        data = subprocess_check_output(
            ["pwd"], stdout=subprocess_pipe, stderr=subprocess_pipe, text=True
        ).strip()
        self.assertEqual(
            data, PWD_STR, "mismatch in subprocess check pwd output"
        )

    def test_subprocess_popen(self):
        """Check that pwd popen output matches getcwd as bytes"""
        proc = subprocess_popen(
            ["pwd"], stdout=subprocess_pipe, stderr=subprocess_stdout
        )
        retval = proc.wait()
        data = proc.stdout.read().strip()
        self.assertEqual(
            data, PWD_BYTES, "mismatch in subprocess popen pwd output"
        )

    def test_subprocess_popen_text(self):
        """Check that pwd popen output matches getcwd as string"""
        orig = os.getcwd()
        proc = subprocess_popen(
            ["pwd"], stdout=subprocess_pipe, stderr=subprocess_stdout, text=True
        )
        retval = proc.wait()
        data = proc.stdout.read().strip()
        self.assertEqual(
            data, PWD_STR, "mismatch in subprocess popen pwd output"
        )


if __name__ == "__main__":
    testmain()
