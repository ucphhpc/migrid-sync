# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_unittest_testcore - unit test of the corresponding mig unittest module
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# --- END_HEADER ---
#

"""Temporary wrapper allowing the inclusion of testcore into the automated suite."""

import importlib
import os
import sys

from tests.support import MigTestCase, testmain

from mig.unittest.testcore import main as testcore_main


class MigUnittestTestcore(MigTestCase):

    def test_existing_main(self):
        def raise_on_error_exit(exit_code, identifying_message=None):
            if exit_code != 0:
                if identifying_message is None:
                    identifying_message = 'unknown'
                raise AssertionError(
                    'failure in unittest/testcore: %s' % (identifying_message,))

        print("") # account for wrapped tests printing to console

        testcore_main(_exit=raise_on_error_exit)


if __name__ == '__main__':
    testmain()
