from __future__ import print_function
import sys

from tests.support import MigTestCase, testmain

from mig.lib.coresvc.payloads import \
    Payload as ArgumentBundle, \
    PayloadDefinition as ArgumentBundleDefinition, \
    PayloadException


def _contains_a_thing(value):
    assert 'thing' in value


def _upper_case_only(value):
    """value must be upper case"""
    assert value == value.upper(), _upper_case_only.__doc__


class TestMigSharedArguments__bundles(MigTestCase):
    ThingsBundle = ArgumentBundleDefinition('Things', [
        ('some_field', _contains_a_thing),
        ('other_field', _contains_a_thing),
    ])

    def assertBundleOfKind(self, value, bundle_kind=None):
        assert isinstance(bundle_kind, str) and bundle_kind
        self.assertIsInstance(value, ArgumentBundle, "value is not an argument bundle")
        self.assertEqual(value.name, bundle_kind, "expected %s bundle, got %s" % (bundle_kind, value.name))

    def test_bundling_arguments_produces_a_bundle(self):
        bundle = self.ThingsBundle('abcthing', 'thingdef')

        self.assertBundleOfKind(bundle, bundle_kind='Things')

    def test_raises_on_missing_positional_arguments(self):
        with self.assertRaises(PayloadException) as raised:
            self.ThingsBundle(['a'])
        self.assertEqual(str(raised.exception), 'Error: too few arguments given (expected 2 got 1)')

    def test_ensuring_arguments_returns_a_bundle(self):
        bundle = self.ThingsBundle.ensure_bundle(['abcthing', 'thingdef'])

        self.assertBundleOfKind(bundle, bundle_kind='Things')

    def test_ensuring_an_existing_bundle_returns_it_unchanged(self):
        existing_bundle = self.ThingsBundle('abcthing', 'thingdef')

        bundle = self.ThingsBundle.ensure_bundle(existing_bundle)

        self.assertIs(bundle, existing_bundle)

    def test_ensuring_on_a_list_of_args_validates_them(self):
        with self.assertRaises(Exception) as raised:
            bundle = self.ThingsBundle.ensure_bundle(['abcthing', 'def'])
        self.assertEqual(str(raised.exception), 'payload failed to validate:\n- other_field: required')

    def test_ensuring_on_invalid_args_produces_reports_with_errors(self):
        UpperCaseValue = ArgumentBundle.define('UpperCaseValue', ['ustring'], {
            'ustring': _upper_case_only
        })

        with self.assertRaises(Exception) as raised:
            bundle = UpperCaseValue.ensure_bundle(['lowerCHARS'])
        self.assertEqual(str(raised.exception), 'payload failed to validate:\n- ustring: value must be upper case')

    def test_ensuring_on_invalid_args_containing_none_behaves_correctly(self):
        UpperCaseValue = ArgumentBundle.define('UpperCaseValue', ['ustring'], {
            'ustring': _upper_case_only
        })

        with self.assertRaises(Exception) as raised:
            bundle = UpperCaseValue.ensure_bundle([None])
        self.assertEqual(str(raised.exception), 'payload failed to validate:\n- ustring: missing')


if __name__ == '__main__':
    testmain()
