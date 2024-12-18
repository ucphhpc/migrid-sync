from __future__ import print_function
import sys

from tests.support import MigTestCase, testmain

from mig.shared.arguments import parse_getopt_args, \
    ArgumentBundle, ArgumentBundleDefinition


def _is_not_none(value):
    return value is not None


class TestMigSharedArguments__bundles(MigTestCase):
    ThingsBundle = ArgumentBundleDefinition('Things', [
        (None, 'some_thing', _is_not_none),
        (None, 'other_thing', _is_not_none),
    ])

    def assertBundleOfKind(self, value, bundle_kind=None):
        assert isinstance(bundle_kind, str) and bundle_kind
        self.assertIsInstance(value, ArgumentBundle, "value is not an argument bundle")
        self.assertEqual(value.name, bundle_kind, "expected %s bundle, got %s" % (bundle_kind, value.name))

    def test_bundling_arguments_produces_a_bundle(self):
        bundle = self.ThingsBundle('abc', 'def')

        self.assertBundleOfKind(bundle, bundle_kind='Things')

    def test_raises_on_missing_positional_arguments(self):
        with self.assertRaises(ValueError) as raised:
            self.ThingsBundle(['a'])
        self.assertEqual(str(raised.exception), 'Error: too few arguments given (expected 2 got 1)')

    def test_ensuring_an_existing_bundle_returns_it_unchanged(self):
        existing_bundle = self.ThingsBundle('abc', 'def')

        bundle = self.ThingsBundle.ensure_bundle(existing_bundle)

        self.assertIs(bundle, existing_bundle)

    def test_ensuring_an_list_of_arguments_returns_a_bundle(self):
        bundle = self.ThingsBundle.ensure_bundle(['abc', 'def'])

        self.assertBundleOfKind(bundle, bundle_kind='Things')


class TestMigSharedArguments__getopt(MigTestCase):
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
