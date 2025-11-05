# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_cat - unit test of the corresponding mig module
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

"""Unit tests of the MiG functionality file implementing the cat backend"""

from __future__ import print_function
from datetime import date, timedelta
import importlib
import os
import shutil
import sys
from types import SimpleNamespace
import unittest

from tests.support import MIG_BASE, TEST_DATA_DIR, TEST_OUTPUT_DIR, \
    MigTestCase, testmain, temppath, ensure_dirs_exist
from tests.support.fixturesupp import FixtureAssertMixin
from tests.support.snapshotsupp import SnapshotAssertMixin
from tests.support.usersupp import UserAssertMixin
from tests.support.wsgisupp import WsgiAssertMixin, create_wsgi_environ, \
                                   prepare_wsgi

from mig.lib.templates.__main__ import main as templates_main
import mig.shared.accountreq as accountreq
import mig.shared.returnvalues as returnvalues
from mig.shared.base import client_id_dir, fill_distinguished_name
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import peers_filename as DEFAULT_PEERS_FILENAME
from mig.shared.functionality.tmplinterface import _main as submain
from mig.shared.serial import dump


_MARK_COMPARED = object()
TEST_TEMPLATE_CACHE_DIR = os.path.join(TEST_OUTPUT_DIR, '__template_cache__')

def _only_output_objects(output_objects, with_object_type=None):
    return [o for o in output_objects if o['object_type'] == with_object_type]


def _trim_ends_of_lines(value):
    assert isinstance(value, str), "cannot operate on non-string value"
    split_lines = value.split('\n')
    trimmed_lines = [line.rstrip() for line in split_lines]
    return '\n'.join(trimmed_lines)


class MigSharedFunctionalityTmplInterface__basics(MigTestCase, SnapshotAssertMixin, WsgiAssertMixin):
    """Wrap unit tests for the corresponding module"""

    TEST_CLIENT_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
    TEST_CONF_FILE = os.path.join(TEST_DATA_DIR, 'MiGserver--templates.conf')

    def _provide_configuration(self):
        return 'preexisting'

    def before_each(self):
        self._configuration = get_configuration_object(
            self.TEST_CONF_FILE, skip_log=True, disable_auth_log=True)

        # clean up the configuration file specified cache directory
        shutil.rmtree(TEST_TEMPLATE_CACHE_DIR, ignore_errors=True)

        # allow the dummy plugin to be loaded
        sys.path.append(TEST_DATA_DIR)
        self._register_check(lambda: sys.path.pop())

        # prime the dummy cache
        args = SimpleNamespace(config_file=self.TEST_CONF_FILE, command="prime")
        templates_main(args, _print=lambda _: None)

    def test_rejects_invalid_request_type(self):
        self.logger.forgive_errors()
        request_body = {
            'type': 'nonexistent',
            'operation': 'read',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi)
        self.assertSnapshotOfHtmlContent(content, is_fragment=True)

    def test_succeeds_for_a_defined_handler(self):
        self.logger.forgive_errors()
        request_body = {
            'type': 'testplugin__testpluginendpoint',
            'operation': 'read',
            'greeting': 'foobar',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi)
        self.assertSnapshotOfHtmlContent(content, is_fragment=True)

    def test_gracefully_handles_a_missing_template(self):
        self.logger.forgive_errors()
        request_body = {
            'type': 'testplugin__testpluginendpoint_missing_template',
            'operation': 'read',
            'greeting': 'foobar',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi)
        self.assertSnapshotOfHtmlContent(content, is_fragment=True)


class MigSharedFunctionalityTmplInterface__migux(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    TEST_CLIENT_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        self.test_user_dir = self._provision_test_user(self, self.TEST_CLIENT_ID)

    def assertOutputFailed(self, output_objects, status, with_error_text=None):
        self.assertNotEqual(status, returnvalues.OK)
        if with_error_text:
            relevant_obj = self.assertSingleOutputObject(output_objects,
                                        with_object_type='error_text')
            self.assertEqual(relevant_obj['text'], with_error_text)

    def assertOutputSucceeded(self, output_objects, status):
        try:
            self.assertEqual(status, returnvalues.OK)
        except AssertionError:
            relevant_obj = self.assertSingleOutputObject(output_objects,
                                        with_object_type='error_text')
            raise AssertionError(relevant_obj['text'])

    def assertSingleOutputObject(self, output_objects, with_object_type=None):
        assert with_object_type is not None
        found_objects = _only_output_objects(output_objects,
                                             with_object_type=with_object_type)
        self.assertEqual(len(found_objects), 1)
        return found_objects[0]

    def test_rejects_invalid_request_type_json(self):
        self.logger.forgive_errors()
        request_body = {
            'type': '__nonexistent_type',
            'operation': 'read',
        }
        wsgi_environ = create_wsgi_environ(self.configuration, 'http://localhost/foobar',
                                           method='POST',
                                           json=request_body)

        (output_objects, status) = submain(self.configuration, self.logger,
                                           client_id=self.TEST_CLIENT_ID,
                                           environ=wsgi_environ)

        self.assertOutputFailed(output_objects, status,
                with_error_text='no such route')

    def test_rejects_invalid_request_type_form_data(self):
        self.logger.forgive_errors()
        request_body = {
            'type': 'nonexistent_type',
            'operation': 'read',
        }
        wsgi_environ = create_wsgi_environ(self.configuration, 'http://localhost/foobar',
                                           method='POST',
                                           form=request_body)

        (output_objects, status) = submain(self.configuration, self.logger,
                                           client_id=self.TEST_CLIENT_ID,
                                           environ=wsgi_environ)

        self.assertOutputFailed(output_objects, status,
                with_error_text='no such route')

    def test_list_peers_arranges_template_output(self):
        request_body = {
            'type': 'migux_apps_peers__accepted',
            'operation': 'read',
        }
        wsgi_environ = create_wsgi_environ(self.configuration, 'http://localhost/foobar',
                                           method='POST',
                                           json=request_body)

        (output_objects, status) = submain(self.configuration, self.logger,
                                           client_id=self.TEST_CLIENT_ID,
                                           environ=wsgi_environ)

        self.assertOutputSucceeded(output_objects, status)
        self.assertEqual(len(output_objects), 2)
        relevant_obj = self.assertSingleOutputObject(output_objects,
                                      with_object_type='template')

        # directly compare the template args to allow a later equality check
        template_args = relevant_obj['template_args']
        self.assertEqual(list(template_args.keys()), ['peers_listing'])
        template_args['peers_listing'] = _MARK_COMPARED

        # now compare the template output object
        self.assertEqual(relevant_obj, {
            'object_type': 'template',
            'template_name': 'search_result',
            'template_group': 'migux.apps.peers',
            'template_args': {
                'peers_listing': _MARK_COMPARED
            }
        })


class MigSharedFunctionalityTmplinterface__accepted(MigTestCase,
                                                      WsgiAssertMixin,
                                                      FixtureAssertMixin,
                                                      SnapshotAssertMixin):
    """Tests of the end to end usage of jsoninterface"""

    TEST_CLIENT_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        result = UserAssertMixin._provision_test_user_return_dict(self, self.TEST_CLIENT_ID)
        self.test_user_dir = result['user_dir']
        self.test_user_settings_dir = result['user_settings_dir']

    def _arrange_peers(self, fixture_relpath):
        peers_fixture = self.prepareFixtureAssert(fixture_relpath, fixture_format='json')
        peers_fixture.write_to_dir(self.test_user_settings_dir, output_format='pickle')

    def test_responds_with_accepted_for_content_type_form_data(self):
        self._arrange_peers('peers--single')
        request_body = {
            'type': 'migux_apps_peers__accepted',
            'operation': 'read',
            'fields': 'email,full_name',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi,
                expected_status_code=200,
                expected_content_type='text/html')

        content_trimmed = _trim_ends_of_lines(content)
        self.assertSnapshot(content_trimmed, extension='html')

    def test_accepted_when_filtering_by_query_asterisk(self):
        self._arrange_peers('peers--multiple')
        request_body = {
            'type': 'migux_apps_peers__accepted',
            'operation': 'read',
            'fields': 'full_name,email',
            'query': '*',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi,
                expected_status_code=200,
                expected_content_type='text/html')

        content_trimmed = _trim_ends_of_lines(content)
        self.assertSnapshot(content_trimmed, extension='html')

    def test_accepted_filter_query_subset_match(self):
        self._arrange_peers('peers--multiple')
        request_body = {
            'type': 'migux_apps_peers__accepted',
            'operation': 'read',
            'fields': 'full_name',
            'query': 'Test Peer User',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi,
                expected_status_code=200,
                expected_content_type='text/html')

        content_trimmed = _trim_ends_of_lines(content)
        self.assertSnapshot(content_trimmed, extension='html')


class MigSharedFunctionalityTmplinterface__requested(MigTestCase,
                                                      WsgiAssertMixin,
                                                      FixtureAssertMixin,
                                                      SnapshotAssertMixin):
    """Tests of the end to end usage of jsoninterface"""

    TEST_CLIENT_ID = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        result = UserAssertMixin._provision_test_user_return_dict(self, self.TEST_CLIENT_ID)
        self.test_user_dir = result['user_dir']
        self.test_user_settings_dir = result['user_settings_dir']

    def _arrange_pending_peers(self, fixture_relpath):
        pending_peers_fixture = self.prepareFixtureAssert(fixture_relpath, fixture_format='json')
        pending_peers_fixture.write_to_dir(self.test_user_settings_dir, output_format='pickle')

    def test_responds_with_requested_for_content_type_form_data(self):
        self._arrange_pending_peers('pending_peers--single')
        request_body = {
            'type': 'migux_apps_peers__requested',
            'operation': 'read',
            'fields': 'full_name,email',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi,
                expected_status_code=200,
                expected_content_type='text/html')

        content_trimmed = _trim_ends_of_lines(content)
        self.assertSnapshot(content_trimmed, extension='html')

    def test_requested_when_filtering_by_query_asterisk(self):
        self._arrange_pending_peers('pending_peers--multiple')
        request_body = {
            'type': 'migux_apps_peers__requested',
            'operation': 'read',
            'fields': 'full_name,email',
            'query': '*',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi,
                expected_status_code=200,
                expected_content_type='text/html')

        content_trimmed = _trim_ends_of_lines(content)
        self.assertSnapshot(content_trimmed, extension='html')

    def test_accepted_filter_query_single_match(self):
        self._arrange_pending_peers('pending_peers--multiple')
        request_body = {
            'type': 'migux_apps_peers__requested',
            'operation': 'read',
            'fields': 'full_name,email',
            'query': 'peer3@',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi,
                expected_status_code=200,
                expected_content_type='text/html')

        content_trimmed = _trim_ends_of_lines(content)
        self.assertSnapshot(content_trimmed, extension='html')

    def test_accepted_filter_expire(self):
        self._arrange_pending_peers('pending_peers--multiple')
        date_expire_in_7_days = date.today() + timedelta(days=7)
        request_body = {
            'type': 'migux_apps_peers__requested',
            'operation': 'read',
            'fields': 'full_name,email',
            'expire': date_expire_in_7_days.isoformat(),
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi,
                expected_status_code=200,
                expected_content_type='text/html')

        content_trimmed = _trim_ends_of_lines(content)
        self.assertSnapshot(content_trimmed, extension='html')

    def test_accepted_filter_kind(self):
        self._arrange_pending_peers('pending_peers--multiple')
        date_expire_in_7_days = date.today() + timedelta(days=7)
        request_body = {
            'type': 'migux_apps_peers__requested',
            'operation': 'read',
            'fields': 'full_name,email',
            'kind': 'collaboration',
        }
        prepared_wsgi = self.prepareWsgiAssert(self.configuration,
                                 'http://localhost/tmplinterface.py',
                                 form=request_body,
                                 mig_user_dn=self.TEST_CLIENT_ID)

        content, _ = self.assertWsgiResponse(None, prepared_wsgi,
                expected_status_code=200,
                expected_content_type='text/html')

        content_trimmed = _trim_ends_of_lines(content)
        self.assertSnapshot(content_trimmed, extension='html')


if __name__ == '__main__':
    testmain()
