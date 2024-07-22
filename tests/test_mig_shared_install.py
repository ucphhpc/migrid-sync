# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_install - unit test of the corresponding mig shared module
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

import binascii
import difflib
import os
import pwd
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))

from support import MIG_BASE, MigTestCase, testmain, temppath, cleanpath, fixturepath, is_path_within

from mig.shared.defaults import keyword_auto
from mig.shared.install import determine_timezone, generate_confs


class DummyPwInfo:
    """Wrapper to assist in create_dummy_gpwnam"""

    def __init__(self, pw_uid, pw_gid):
        self.pw_uid = pw_uid
        self.pw_gid = pw_gid


def create_dummy_gpwnam(pw_uid, pw_gid):
    """Helper to mimic pwd.getpwnam /etc/passwd lookup for arbitrary users"""

    dummy = DummyPwInfo(pw_uid, pw_gid)
    return lambda _: dummy


def noop(*args, **kwargs):
    if args:
        return args[0]
    return None


class MigSharedInstall__determine_timezone(MigTestCase):
    """Coverage of timezone determination."""

    def test_determines_tz_utc_fallback(self):
        timezone = determine_timezone(
            _environ={}, _path_exists=lambda _: False, _print=noop)

        self.assertEqual(timezone, 'UTC')

    def test_determines_tz_via_environ(self):
        example_environ = {
            'TZ': 'Example/Enviromnent'
        }
        timezone = determine_timezone(_environ=example_environ)

        self.assertEqual(timezone, 'Example/Enviromnent')

    def test_determines_tz_via_localtime(self):
        def exists_localtime(value):
            saw_call = value == '/etc/localtime'
            exists_localtime.was_called = saw_call
            return saw_call
        exists_localtime.was_called = False

        timezone = determine_timezone(
            _environ={}, _path_exists=exists_localtime)

        self.assertTrue(exists_localtime.was_called)
        self.assertIsNotNone(timezone)

    def test_determines_tz_via_timedatectl(self):
        def exists_timedatectl(value):
            saw_call = value == '/usr/bin/timedatectl'
            exists_timedatectl.was_called = saw_call
            return saw_call
        exists_timedatectl.was_called = False

        timezone = determine_timezone(
            _environ={}, _path_exists=exists_timedatectl, _print=noop)

        self.assertTrue(exists_timedatectl.was_called)
        self.assertIsNotNone(timezone)


class MigSharedInstall__generate_confs(MigTestCase):
    """Unit test helper for the migrid code pointed to in class name"""

    def before_each(self):
        self.output_path = temppath('sharedinstall', self)

    def test_creates_output_directory_and_adds_active_symlink(self):
        symlink_path = cleanpath('sharedinstall/confs', self, skip_clean=True)
        folder_path = cleanpath('sharedinstall/confs-foobar', self, skip_clean=True)

        generate_confs(self.output_path, destination_suffix='-foobar')

        path_kind = self.assertPathExists('sharedinstall/confs-foobar')
        self.assertEqual(path_kind, "dir")
        path_kind = self.assertPathExists('sharedinstall/confs')
        self.assertEqual(path_kind, "symlink")

    def test_creates_output_directory_and_repairs_active_symlink(self):
        symlink_path = temppath('xxxconfs', self)
        folder_path = cleanpath('xxxconfs-foobar', self)
        nowhere_path = temppath('xxxconfs-nowhere', self, skip_clean=True)
        # arrange pre-existing symlink pointing nowhere
        os.symlink(nowhere_path, symlink_path)

        generate_confs(self.output_path, destination=symlink_path, destination_suffix='-foobar')

        self.assertEqual(os.readlink(symlink_path), folder_path)

    def test_creates_output_directory_containing_a_standard_local_configuration(self):
        fixture_dir = fixturepath("confs-stdlocal")
        expected_generated_dir = cleanpath('sharedinstall/confs-stdlocal', self, skip_clean=True)
        symlink_path = temppath('sharedinstall/confs', self, skip_clean=True)

        generate_confs(
            self.output_path,
            destination_suffix='-stdlocal',
            user='testuser',
            group='testgroup',
            mig_code='/home/mig/mig',
            mig_certs='/home/mig/certs',
            mig_state='/home/mig/state',
            timezone='Test/Place',
            crypto_salt='_TEST_CRYPTO_SALT'.zfill(32),
            digest_salt='_TEST_DIGEST_SALT'.zfill(32),
            seafile_secret='_test-seafile-secret='.zfill(44),
            seafile_ccnetid='_TEST_SEAFILE_CCNETID'.zfill(40),
            _getpwnam=create_dummy_gpwnam(4321, 1234),
        )

        generated_dir = os.path.realpath(symlink_path)
        self.assertEqual(generated_dir, expected_generated_dir)

        os.remove(os.path.join(generated_dir, "generateconfs.log"))
        os.remove(os.path.join(generated_dir, "instructions.txt"))

        actual_files = os.listdir(fixture_dir)
        expected_files = os.listdir(fixture_dir)
        self.assertEqual(len(actual_files), len(expected_files))

        for file_name in expected_files:
            actual_file = os.path.join(generated_dir, file_name)
            expected_file = os.path.join(fixture_dir, file_name)
            self.assertFileContentIdentical(actual_file, expected_file)

    def test_kwargs_for_paths_auto(self):
        def capture_defaulted(*args, **kwargs):
            capture_defaulted.kwargs = kwargs
            return args[0]
        capture_defaulted.kwargs = None

        options = generate_confs(
            '/some/arbitrary/path',
            _getpwnam=create_dummy_gpwnam(4321, 1234),
            _prepare=capture_defaulted,
            _writefiles=noop,
            _instructions=noop,
        )

        defaulted = capture_defaulted.kwargs
        self.assertPathWithin(defaulted['mig_certs'], MIG_BASE)
        self.assertPathWithin(defaulted['mig_state'], MIG_BASE)

    def test_options_for_source_auto(self):
        options = generate_confs(
            '/some/arbitrary/path',
            source=keyword_auto,
            _getpwnam=create_dummy_gpwnam(4321, 1234),
            _prepare=noop,
            _writefiles=noop,
            _instructions=noop,
        )
        expected_template_dir = os.path.join(MIG_BASE, 'mig/install')

        self.assertEqual(options['template_dir'], expected_template_dir)

    def test_options_for_source_relative(self):
        options = generate_confs(
            '/current/working/directory/mig/install',
            source='.',
            _getpwnam=create_dummy_gpwnam(4321, 1234),
            _prepare=noop,
            _writefiles=noop,
            _instructions=noop,
        )

        self.assertEqual(options['template_dir'],
                         '/current/working/directory/mig/install')

    def test_options_for_destination_auto(self):
        options = generate_confs(
            '/some/arbitrary/path',
            destination=keyword_auto,
            destination_suffix='_suffix',
            _getpwnam=create_dummy_gpwnam(4321, 1234),
            _prepare=noop,
            _writefiles=noop,
            _instructions=noop,
        )

        self.assertEqual(options['destination_link'],
                         '/some/arbitrary/path/confs')
        self.assertEqual(options['destination_dir'],
                         '/some/arbitrary/path/confs_suffix')

    def test_options_for_destination_relative(self):
        options = generate_confs(
            '/current/working/directory',
            destination='generate-confs',
            destination_suffix='_suffix',
            _getpwnam=create_dummy_gpwnam(4321, 1234),
            _prepare=noop,
            _writefiles=noop,
            _instructions=noop,
        )

        self.assertEqual(options['destination_link'],
                         '/current/working/directory/generate-confs')
        self.assertEqual(options['destination_dir'],
                         '/current/working/directory/generate-confs_suffix')


if __name__ == '__main__':
    testmain()
