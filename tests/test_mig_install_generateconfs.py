# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_install_generateconfs - unit test of the corresponding mig module
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

"""Unit tests for the migrid module pointed to in the filename"""

from __future__ import print_function

import importlib
import os
import sys

from tests.support import MIG_BASE, MigTestCase, testmain, cleanpath

from mig.install.generateconfs import _PARAMETERS
from mig.shared.install import generate_confs, _GENERATE_CONFS_PARAMETERS

def _import_generateconfs():
    """Internal helper to work around non-package import location"""
    sys.path.append(os.path.join(MIG_BASE, 'mig/install'))
    mod = importlib.import_module('generateconfs')
    sys.path.pop(-1)
    return mod


# workaround for generatconfs being placed witin a non-module directory
generateconfs = _import_generateconfs()
main = generateconfs.main


def create_fake_generate_confs(return_dict=None):
    """Fake generate confs helper"""
    def _generate_confs(*args, **kwargs):
        _generate_confs.settings = kwargs
        if return_dict:
            return (return_dict, {})
        else:
            return ({}, {})
    _generate_confs.settings = None
    return _generate_confs


def noop(*args):
    pass


class MigInstallGenerateconfs(MigTestCase):
    def test_consistent_parameters(self):
        mismatched = _GENERATE_CONFS_PARAMETERS - set(_PARAMETERS)
        self.assertEqual(len(mismatched), 0,
                         "defined parameters do not match generate_confs()")


class MigInstallGenerateconfs__main(MigTestCase):
    """Unit test helper for the migrid code pointed to in class name"""

    def test_option_permanent_freeze(self):
        expected_generated_dir = cleanpath('confs-stdlocal', self,
                                           ensure_dir=True)
        with open(os.path.join(expected_generated_dir, "instructions.txt"),
                  "w"):
            pass
        fake_generate_confs = create_fake_generate_confs(
            dict(destination_dir=expected_generated_dir))
        test_arguments = ['--permanent_freeze', 'yes']

        exit_code = main(
            test_arguments, _generate_confs=fake_generate_confs, _print=noop)
        self.assertEqual(exit_code, 0)

    def test_option_storage_protocols(self):
        expected_generated_dir = cleanpath('confs-stdlocal', self,
                                           ensure_dir=True)
        with open(os.path.join(expected_generated_dir, "instructions.txt"),
                  "w"):
            pass
        fake_generate_confs = create_fake_generate_confs(
            dict(destination_dir=expected_generated_dir))
        test_arguments = ['--storage_protocols', 'proto1 proto2 proto3']

        exit_code = main(
            test_arguments, _generate_confs=fake_generate_confs, _print=noop)
        self.assertEqual(exit_code, 0)
        settings = fake_generate_confs.settings
        self.assertIn('storage_protocols', settings)
        self.assertEqual(settings['storage_protocols'], 'proto1 proto2 proto3')

    def test_option_wwwserve_max_bytes(self):
        expected_generated_dir = cleanpath('confs-stdlocal', self,
                                           ensure_dir=True)
        with open(os.path.join(expected_generated_dir, "instructions.txt"),
                  "w"):
            pass
        fake_generate_confs = create_fake_generate_confs(
            dict(destination_dir=expected_generated_dir))
        test_arguments = ['--wwwserve_max_bytes', '43211234']

        exit_code = main(
            test_arguments, _generate_confs=fake_generate_confs, _print=noop)
        settings = fake_generate_confs.settings
        self.assertIn('wwwserve_max_bytes', settings)
        self.assertEqual(settings['wwwserve_max_bytes'], 43211234)


if __name__ == '__main__':
    testmain()
