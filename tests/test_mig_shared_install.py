# -*- coding: utf-8 -*-

import binascii
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), ".")))
from support import MigTestCase, testmain, temppath, cleanpath

from mig.shared.install import \
    generate_confs

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


if __name__ == '__main__':
    testmain()
