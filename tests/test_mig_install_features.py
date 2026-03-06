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
from types import SimpleNamespace

from tests.support import MIG_BASE, TEST_DATA_DIR, MigTestCase, testmain


from mig.install.features import args_main, Features


TEST_FEATURES_EXAMPLES_DIR = os.path.join(TEST_DATA_DIR, 'features')


class FakePrint:
    def __init__(self):
        self._lines = []

    def __call__(self, value=''):
        self._lines.append(value)


def _make_example_features_instance(example_name, overrides_supported={}):
    example_dir = os.path.join(TEST_FEATURES_EXAMPLES_DIR, example_name)
    features_file = os.path.join(example_dir, 'features.ini')
    requirements_dir = os.path.join(example_dir, 'requirements')

    features = Features.from_definitions_file(features_file,
                                              requirements_dir,
                                              overrides_supported)

    return example_dir, features


class MigInstallFeatures_logic(MigTestCase):
    """Unit test helper for the migrid code pointed to in class name"""

    def assertOutputLines(self, fake_print, expected_lines):
        assert isinstance(fake_print, FakePrint)

        self.assertEqual(fake_print._lines, expected_lines)

    def test_command_show(self):
        args = SimpleNamespace(
            command='show',
        )
        fake_print = FakePrint()
        _, features = _make_example_features_instance('basic')

        ret = args_main(args, print=fake_print, features=features)

        self.assertEqual(ret, 0)
        self.assertOutputLines(fake_print, [
            "available features: BAR, BAZ, FOO",
        ])

    def test_command_enabled_default_on(self):
        args = SimpleNamespace(
            command='enabled',
            c=None,
            dotenv=None,
            env=None,
        )
        fake_print = FakePrint()
        fake_warn = FakePrint()
        _, features = _make_example_features_instance('basic')

        ret = args_main(args, print=fake_print, warn=fake_warn, features=features)

        self.assertEqual(ret, 0)
        self.assertOutputLines(fake_warn, [
            "no feature coniguration available; showing those enabled by default only"
        ])
        self.assertOutputLines(fake_print, [
            "enabled features: BAZ",
        ])

    def test_command_enabled_using_dotenv(self):
        fake_print = FakePrint()
        example_dir, features = _make_example_features_instance('basic')
        args = SimpleNamespace(
            command='enabled',
            c=None,
            dotenv=os.path.join(example_dir, '.env--enable-foo'),
            env=None,
        )

        ret = args_main(args, print=fake_print, features=features)

        self.assertEqual(ret, 0)
        self.assertOutputLines(fake_print, [
            "enabled features: BAZ, FOO",
        ])

    def test_command_enabled_using_env(self):
        fake_print = FakePrint()
        example_dir, features = _make_example_features_instance('basic')
        args = SimpleNamespace(
            command='enabled',
            c=None,
            dotenv=None,
            env={
                'ENABLE_BAR': 'true',
            },
        )

        ret = args_main(args, print=fake_print, features=features)

        self.assertEqual(ret, 0)
        self.assertOutputLines(fake_print, [
            "enabled features: BAR, BAZ",
        ])

    def test_command_install_check(self):
        fake_print = FakePrint()
        example_dir, features = _make_example_features_instance('basic')
        args = SimpleNamespace(
            command='install',
            check=True,
            c=None,
            dotenv=os.path.join(example_dir, '.env--enable-foo'),
            env=None
        )

        ret = args_main(args, print=fake_print, features=features)

        self.assertEqual(ret, 0)
        self.assertOutputLines(fake_print, [
            f"pip install -r {os.path.join(example_dir, 'requirements/baz-requirements.txt')}",
            f"pip install -r {os.path.join(example_dir, 'requirements/foo-requirements.txt')}",
        ])

    def test_overridden_package_version(self):
        fake_print = FakePrint()
        example_dir, features = _make_example_features_instance('basic',
                overrides_supported={
                    'FOO': {
                        'somepkg': 'OVERRIDE_SOMEPKG_VERSION',
                    }
                })
        args = SimpleNamespace(
            command='install',
            check=True,
            c=None,
            dotenv=None,
            env={
                'ENABLE_FOO': 'true',
                'OVERRIDE_SOMEPKG_VERSION': '4.5.5',
            }
        )

        ret = args_main(args, print=fake_print, features=features)

        self.assertEqual(ret, 0)
        self.assertOutputLines(fake_print, [
            f"pip install -r {os.path.join(example_dir, 'requirements/baz-requirements.txt')}",
            "pip install somepkg==4.5.5 otherpkg==4.5.6",
        ])



class MigInstallFeatures_smoke(MigTestCase):
    """Unit test helper for the migrid code pointed to in class name"""

    def assertOutputLines(self, fake_print, expected_lines):
        assert isinstance(fake_print, FakePrint)

        self.assertEqual(fake_print._lines, expected_lines)

    def test_command_show(self):
        args = SimpleNamespace(
            command='show',
        )
        fake_print = FakePrint()

        ret = args_main(args, print=fake_print)

        self.assertEqual(ret, 0)
        self.assertOutputLines(fake_print, [
            "available features: CLOUD, MIGUX",
        ])


if __name__ == '__main__':
    testmain()
