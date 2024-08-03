# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_install_geneateconfs - unit test of generateconfs
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

"""Unit tests for the configuration object"""

import inspect
import io
import json

from tests.support import MigTestCase, testmain, fixturefile
from mig.shared.configuration import Configuration


def _is_method(value):
    return type(value).__name__ == 'method'


def _to_dict(obj):
    return {k: v for k, v in inspect.getmembers(obj) if not (k.startswith('__') or _is_method(v))}


class MigSharedConfiguration(MigTestCase):
    def test_default_object(self):
        expected_values = fixturefile('mig_shared_configuration--new', fixture_format='json')

        configuration = Configuration(None)
        # TODO: the following work around default values set for these on the instance that
        #       no longer make total sense but fiddling with them is better as a follow-up.
        configuration.certs_path = '/some/place/certs'
        configuration.state_path = '/some/place/state'
        configuration.mig_path = '/some/place/mig'

        actual_values = _to_dict(configuration)

        self.maxDiff = None
        self.assertEqual(actual_values, expected_values)


if __name__ == '__main__':
    testmain()
