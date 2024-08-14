from __future__ import print_function
import importlib
import os
import sys

from tests.support import MIG_BASE, MigTestCase, testmain, cleanpath


def _import_generateconfs():
    sys.path.append(os.path.join(MIG_BASE, 'mig/install'))
    mod = importlib.import_module('generateconfs')
    sys.path.pop(-1)
    return mod


# workaround for generatconfs being placed witin a non-module directory
generateconfs = _import_generateconfs()
main = generateconfs.main


def create_fake_generate_confs(return_dict=None):
    def _generate_confs(*args, **kwargs):
        return return_dict if return_dict else {}
    return _generate_confs


class MigInstallGeneateconfs__main(MigTestCase):
    def test_option_permanent_freeze(self):
        expected_generated_dir = cleanpath(
            'confs-stdlocal', self, ensure_dir=True)
        with open(os.path.join(expected_generated_dir, "instructions.txt"), "w"):
            pass
        fake_generate_confs = create_fake_generate_confs(dict(
            destination_dir=expected_generated_dir
        ))
        test_arguments = ['--permanent_freeze', 'yes']

        exit_code = main(test_arguments, _generate_confs=fake_generate_confs)

        self.assertEqual(exit_code, 0)


if __name__ == '__main__':
    testmain()
