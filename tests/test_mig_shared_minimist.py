from __future__ import print_function
import sys

from tests.support import MigTestCase, testmain

from mig.shared.minimist import parse_getopt_args


class TestMigSharedMinimist__getopt(MigTestCase):
    def test_arbitrary_arguments(self):
        (opts, args) = parse_getopt_args(["arg1", "arg2", "arg3"], "")

        self.assertEqual(dict(opts), {})
        self.assertEqual(args, ['arg1', 'arg2', 'arg3'])

    def test_boolean_arguments(self):
        (opts, args) = parse_getopt_args(["-a", "-b", "-c"], "x:abcy:")

        self.assertEqual(dict(opts), {
            '-a': True,
            '-b': True,
            '-c': True,
        })
        self.assertEqual(args, [])


    def test_final_argument_is_boolean(self):
        (opts, args) = parse_getopt_args(["-b", "arg1", "arg2", "arg3"], "o:b")

        self.assertEqual(dict(opts), {
            '-b': True,
        })
        self.assertEqual(args, ['arg1', 'arg2', 'arg3'])

    def test_single_argument_is_boolean(self):
        (opts, args) = parse_getopt_args(["-b", "arg1", "arg2", "arg3"], "b")

        self.assertEqual(dict(opts), {
            '-b': True,
        })
        self.assertEqual(args, ['arg1', 'arg2', 'arg3'])


if __name__ == '__main__':
    testmain()
