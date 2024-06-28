# -*- coding: utf-8 -*-

import binascii
import difflib
import os
import pwd
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))
from support import MigTestCase, testmain, temppath, cleanpath, fixturepath

from mig.shared.install import \
    generate_confs

class DummyPwInfo:
    def __init__(self, pw_uid, pw_gid):
        self.pw_uid = pw_uid
        self.pw_gid = pw_gid


def create_dummy_gpwnam(pw_uid, pw_gid):
    dummy = DummyPwInfo(pw_uid, pw_gid)
    return lambda _: dummy


class MigSharedInstall__generate_confs(MigTestCase):
    def test_creates_output_directory_and_adds_active_symlink(self):
        symlink_path = temppath('confs', self)
        cleanpath('confs-foobar', self)

        generate_confs(destination=symlink_path, destination_suffix='-foobar')

        path_kind = self.assertPathExists('confs-foobar')
        self.assertEqual(path_kind, "dir")
        path_kind = self.assertPathExists('confs')
        self.assertEqual(path_kind, "symlink")

    def test_creates_output_directory_and_repairs_active_symlink(self):
        symlink_path = temppath('confs', self)
        output_path = cleanpath('confs-foobar', self)
        nowhere_path = temppath('confs-nowhere', self, skip_clean=True)
        # arrange pre-existing symlink pointing nowhere
        os.symlink(nowhere_path, symlink_path)

        generate_confs(destination=symlink_path, destination_suffix='-foobar')

        self.assertEqual(os.readlink(symlink_path), output_path)

    def test_creates_output_directory_containing_a_standard_local_configuration(self):
        fixture_dir = fixturepath("confs-stdlocal")
        symlink_path = temppath('confs', self)
        cleanpath('confs-stdlocal', self)

        generate_confs(
            destination=symlink_path,
            destination_suffix='-stdlocal',
            user='testuser',
            group='tesggroup',
            timezone='Test/Place',
            crypto_salt='_TEST_CRYPTO_SALT'.zfill(32),
            digest_salt='_TEST_DIGEST_SALT'.zfill(32),
            seafile_secret='_test-seafile-secret='.zfill(44),
            seafile_ccnetid='_TEST_SEAFILE_CCNETID'.zfill(40),
            _getpwnam=create_dummy_gpwnam(4321, 1234),
        )

        generated_dir = os.path.realpath(symlink_path)
        os.remove(os.path.join(generated_dir, "generateconfs.log"))
        os.remove(os.path.join(generated_dir, "instructions.txt"))

        actual_files = os.listdir(fixture_dir)
        expected_files = os.listdir(fixture_dir)
        self.assertEqual(len(actual_files), len(expected_files))

        for file_name in expected_files:
            actual_file = os.path.join(generated_dir, file_name)
            expected_file = os.path.join(fixture_dir, file_name)
            self.assertFileContentIdentical(actual_file, expected_file)


if __name__ == '__main__':
    testmain(failfast=True)
