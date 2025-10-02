# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_userio - test module of same name
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

"""Unit tests for the migrid module pointed to in the filename"""

import os
import sys
from past.builtins import basestring, unicode

from tests.support import MigTestCase, testmain

from mig.shared.userio import main as userio_main


class MigSharedUserIO(MigTestCase):
    """Unit tests for userio related helper functions"""

    def test_existing_main(self):
        def raise_on_error_exit(exit_code):
            if exit_code != 0:
                if raise_on_error_exit.last_print is not None:
                    identifying_message = raise_on_error_exit.last_print
                else:
                    identifying_message = 'unknown'
                raise AssertionError(
                    'failure in unittest/testcore: %s' % (identifying_message,))
        raise_on_error_exit.last_print = None

        def record_last_print(value):
            raise_on_error_exit.last_print = value

        userio_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == '__main__':
    testmain()
