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

"""Unit tests for the generateconfs utility"""

from __future__ import absolute_import

from tests.support import MigTestCase, testmain
from mig.install.generateconfs import _PARAMETERS
from mig.shared.install import generate_confs, _GENERATE_CONFS_PARAMETERS


class MigInstallGenerateconfs(MigTestCase):
    def test_consistent_parameters(self):
        mismatched = _GENERATE_CONFS_PARAMETERS - set(_PARAMETERS)
        self.assertEqual(len(mismatched), 0,
                         "defined parameters do not match generate_confs()")


if __name__ == '__main__':
    testmain()
