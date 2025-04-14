from __future__ import print_function
import codecs
import errno
import json
import os
import shutil
import sys
import unittest
from threading import Thread
from unittest import skip

from tests.support import PY2, MigTestCase, testmain, temppath, \
    make_wrapped_server
from tests.support.httpsupp import HttpAssertMixin

from mig.shared.base import keyword_auto
from mig.shared.useradm import create_user
from mig.lib.coresvc import ThreadedApiHttpServer, \
    _create_and_expose_server

_TAG_P_OPEN = '<p>'
_TAG_P_CLOSE = '</p>'
_USERADM_PATH_KEYS = ('user_cache', 'user_db_home', 'user_home',
                      'user_settings', 'mrsl_files_dir', 'resource_pending')


def _extend_configuration(*args):
    pass


def ensure_dirs_needed_by_create_user(configuration):
    for config_key in _USERADM_PATH_KEYS:
        dir_path = getattr(configuration, config_key)[0:-1]
        try:
            os.mkdir(dir_path)
        except OSError as exc:
            pass


def extract_error_description_from_html(content):
    open_tag_index = content.find(_TAG_P_OPEN)
    start_index = open_tag_index + len(_TAG_P_OPEN)
    end_index = content.find(_TAG_P_CLOSE)
    error_desription = content[start_index:end_index]
    return error_desription


class MigServerGrid_openid(MigTestCase, HttpAssertMixin):
    def before_each(self):
        self.server_addr = None
        self.server_thread = None

        ensure_dirs_needed_by_create_user(self.configuration)

        self.server_addr = ('localhost', 4567)
        self.server_thread = self._make_server(
            self.configuration, self.logger, self.server_addr)

    def _provide_configuration(self):
        return 'testconfig'

    def after_each(self):
        if self.server_thread:
            self.server_thread.stop()

    def issue_GET(self, request_path):
        return self._issue_GET(self.server_addr, request_path)

    def issue_POST(self, request_path, **kwargs):
        return self._issue_POST(self.server_addr, request_path, **kwargs)

    @unittest.skipIf(PY2, "Python 3 only")
    def test__GET_returns_not_found_for_missing_path(self):
        self.server_thread.start_wait_until_ready()

        status, _ = self.issue_GET('/nonexistent')

        self.assertEqual(status, 404)

    @unittest.skipIf(PY2, "Python 3 only")
    def test_GET_user__top_level_request(self):
        self.server_thread.start_wait_until_ready()

        status, _ = self.issue_GET('/user')

        self.assertEqual(status, 400)

    @unittest.skipIf(PY2, "Python 3 only")
    def test_GET__user_userid_request_succeeds_with_status_ok(self):
        example_username = 'dummy-user'
        example_username_home_dir = temppath(
            'state/user_home/%s' % example_username, self, ensure_dir=True)
        test_user_home = os.path.dirname(
            example_username_home_dir)  # strip user from path
        test_state_dir = os.path.dirname(test_user_home)
        test_user_db_home = os.path.join(test_state_dir, "user_db_home")
        self.server_thread.start_wait_until_ready()

        status, content = self.issue_GET('/user/dummy-user')

        self.assertEqual(status, 200)
        self.assertEqual(content, 'FOOBAR')

    @unittest.skipIf(PY2, "Python 3 only")
    def test_GET_openid_user_username(self):
        self.server_thread.start_wait_until_ready()

        status, content = self.issue_GET('/user/dummy-user')

        self.assertEqual(status, 200)
        self.assertEqual(content, 'FOOBAR')

    @unittest.skipIf(PY2, "Python 3 only")
    def test_POST_user__bad_input_data(self):
        self.server_thread.start_wait_until_ready()

        status, content = self.issue_POST('/user', request_json={
            'greeting': 'provocation'
        })

        self.assertEqual(status, 400)
        error_description = extract_error_description_from_html(content)
        error_description_lines = error_description.split('<br>')
        self.assertEqual(
            error_description_lines[0], 'payload failed to validate:')

    @unittest.skipIf(PY2, "Python 3 only")
    def test_POST_user(self):
        self.server_thread.start_wait_until_ready()

        status, content = self.issue_POST('/user', response_encoding='textual', request_json=dict(
            full_name="Test User",
            organization="Test Org",
            state="NA",
            country="DK",
            email="user@example.com",
            comment="This is the create comment",
            password="password",
        ))

        self.assertEqual(status, 201)
        self.assertIsInstance(content, dict)
        self.assertIn('unique_id', content)

    def _make_configuration(self, test_logger, server_addr):
        configuration = self.configuration
        _extend_configuration(
            configuration,
            server_addr[0],
            server_addr[1],
            logger=test_logger,
            expandusername=False,
            host_rsa_key='',
            nossl=True,
            show_address=False,
            show_port=False,
        )
        return configuration

    @staticmethod
    def _make_server(configuration, logger=None, server_address=None):
        def _on_instance(server):
            server.server_app = _create_and_expose_server(
                server, server.configuration)

        (host, port) = server_address
        server_thread = make_wrapped_server(ThreadedApiHttpServer,
                                            configuration, logger, host, port, on_instance=_on_instance)
        return server_thread


class MigServerGrid_openid__existing_user(MigTestCase, HttpAssertMixin):
    def before_each(self):
        ensure_dirs_needed_by_create_user(self.configuration)

        user_dict = {
            'full_name': "Test User",
            'organization': "Test Org",
            'state': "NA",
            'country': "DK",
            'email': "user@example.com",
            'comment': "This is the create comment",
            'password': "password",
        }
        create_user(user_dict, self.configuration,
                    keyword_auto, default_renew=True)

        self.server_addr = ('localhost', 4567)
        self.server_thread = self._make_server(
            self.configuration, self.logger, self.server_addr)

    def _provide_configuration(self):
        return 'testconfig'

    def after_each(self):
        if self.server_thread:
            self.server_thread.stop()

    @unittest.skipIf(PY2, "Python 3 only")
    def test_GET_openid_user_find(self):
        self.server_thread.start_wait_until_ready()

        status, content = self._issue_GET(self.server_addr, '/user/find', {
            'email': 'user@example.com'
        })

        self.assertEqual(status, 200)

        self.assertIsInstance(content, dict)
        self.assertIn('objects', content)
        self.assertIsInstance(content['objects'], list)

        user = content['objects'][0]
        # check we received the correct user
        self.assertEqual(user['full_name'], 'Test User')

    def _make_configuration(self, test_logger, server_addr):
        configuration = self.configuration
        _extend_configuration(
            configuration,
            server_addr[0],
            server_addr[1],
            logger=test_logger,
            expandusername=False,
            host_rsa_key='',
            nossl=True,
            show_address=False,
            show_port=False,
        )
        return configuration

    @staticmethod
    def _make_server(configuration, logger=None, server_address=None):
        def _on_instance(server):
            server.server_app = _create_and_expose_server(
                server, server.configuration)

        (host, port) = server_address
        server_thread = make_wrapped_server(ThreadedApiHttpServer,
                                            configuration, logger, host, port, on_instance=_on_instance)
        return server_thread


if __name__ == '__main__':
    testmain()
