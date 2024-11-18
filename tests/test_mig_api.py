from __future__ import print_function
import codecs
import json
import os
import sys
import unittest
from threading import Thread
from unittest import skip

from tests.support import PY2, MIG_BASE, TEST_OUTPUT_DIR, MigTestCase, \
    testmain, temppath, make_wrapped_server

from mig.api import ThreadedApiHttpServer, _extend_configuration, _create_and_expose_server
from mig.shared.conf import get_configuration_object

_PYTHON_MAJOR = '2' if PY2 else '3'
_TEST_CONF_DIR = os.path.join(
    MIG_BASE, "envhelp/output/testconfs-py%s" % (_PYTHON_MAJOR,))
_TEST_CONF_FILE = os.path.join(_TEST_CONF_DIR, "MiGserver.conf")


if PY2:
    from urllib2 import HTTPError, urlopen, Request
else:
    from urllib.error import HTTPError
    from urllib.request import urlopen, Request


class MigServerGrid_openid(MigTestCase):
    def before_each(self):
        self.server_addr = None
        self.server_thread = None

    def _provide_configuration(self):
        return 'testconfig'

    def after_each(self):
        if self.server_thread:
            self.server_thread.stop()

    def issue_request(self, request_path):
        return self.issue_GET(request_path)

    def issue_GET(self, request_path):
        assert isinstance(request_path, str) and request_path.startswith(
            '/'), "require http path starting with /"
        request_url = ''.join(
            ('http://', self.server_addr[0], ':', str(self.server_addr[1]), request_path))

        status = 0
        data = None

        try:
            response = urlopen(request_url, None, timeout=2000)

            status = response.getcode()
            data = response.read()
        except HTTPError as httpexc:
            status = httpexc.code
            data = None

        return (status, data)

    def issue_POST(self, request_path, request_data=None, request_json=None):
        assert isinstance(request_path, str) and request_path.startswith(
            '/'), "require http path starting with /"
        request_url = ''.join(
            ('http://', self.server_addr[0], ':', str(self.server_addr[1]), request_path))

        if request_data and request_json:
            raise ValueError(
                "only one of data or json request data may be specified")

        status = 0
        data = None

        try:
            if request_json is not None:
                request_data = codecs.encode(json.dumps(request_json), 'utf8')
                request_headers = {
                    'Content-Type': 'application/json'
                }
                request = Request(request_url, request_data,
                                  headers=request_headers)
            elif request_data is not None:
                request = Request(request_url, request_data)
            else:
                request = Request(request_url)

            response = urlopen(request, timeout=2000)

            status = response.getcode()
            data = response.read()
        except HTTPError as httpexc:
            status = httpexc.code
            data = None

        try:
            data = json.loads(data)
        except Exception as e:
            pass

        return (status, data)

    @unittest.skipIf(PY2, "Python 3 only")
    def test__GET_returns_not_found_for_missing_path(self):
        self.server_addr = ('localhost', 4567)
        configuration = self._make_configuration(self.logger, self.server_addr)
        self.server_thread = self._make_server(
            configuration).start_wait_until_ready()

        status, _ = self.issue_request('/user')

        self.assertEqual(status, 404)

    @unittest.skipIf(PY2, "Python 3 only")
    def test__GET_openid_user__top_level_request_succeeds_with_status_ok(self):
        self.server_addr = ('localhost', 4567)
        configuration = self._make_configuration(self.logger, self.server_addr)
        self.server_thread = self._make_server(
            configuration).start_wait_until_ready()

        status, _ = self.issue_request('/openid/user')

        self.assertEqual(status, 400)

    @unittest.skipIf(PY2, "Python 3 only")
    def test_GET__openid_user_username__user_userid_request_succeeds_with_status_ok(self):
        example_username = 'dummy-user'
        example_username_home_dir = temppath(
            'state/user_home/%s' % example_username, self, ensure_dir=True)
        test_user_home = os.path.dirname(
            example_username_home_dir)  # strip user from path
        test_state_dir = os.path.dirname(test_user_home)
        test_user_db_home = os.path.join(test_state_dir, "user_db_home")

        self.server_addr = ('localhost', 4567)
        configuration = self._make_configuration(self.logger, self.server_addr, overrides=dict(
            user_home=test_user_home,
            user_db_home=test_user_db_home,
        ))
        self.server_thread = self._make_server(
            configuration).start_wait_until_ready()

        # /openid/user/dummy-user
        the_url = '/openid/user/%s' % (example_username,)
        status, body = self.issue_request(the_url)

        self.assertEqual(status, 200)
        self.assertEqual(body, b'FOOBAR')

    @unittest.skipIf(PY2, "Python 3 only")
    def test_GET_openid_user_username(self):
        flask_app = None

        self.server_addr = ('localhost', 4567)
        configuration = self._make_configuration(self.logger, self.server_addr)
        self.server_thread = self._make_server(configuration)
        # flask_app = _create_and_bind_flask_app_to_server(self.server_thread, configuration)
        self.server_thread.start_wait_until_ready()

        request_json = json.dumps({})
        request_data = codecs.encode(request_json, 'utf8')

        status, content = self.issue_GET('/openid/user/dummy-user')

        self.assertEqual(status, 200)
        self.assertEqual(content, b'FOOBAR')

    @unittest.skipIf(PY2, "Python 3 only")
    def test_POST_user__bad_input_data(self):
        flask_app = None

        self.server_addr = ('localhost', 4567)
        configuration = self._make_configuration(self.logger, self.server_addr)
        self.server_thread = self._make_server(configuration)
        self.server_thread.start_wait_until_ready()

        status, content = self.issue_POST('/openid/user', request_json={
            'greeting': 'provocation'
        })

        self.assertEqual(status, 422)

    @unittest.skipIf(PY2, "Python 3 only")
    def test_POST_user(self):
        flask_app = None

        self.server_addr = ('localhost', 4567)
        configuration = self._make_configuration(self.logger, self.server_addr)
        self.server_thread = self._make_server(configuration)
        self.server_thread.start_wait_until_ready()

        status, content = self.issue_POST('/openid/user', request_json={
            'greeting': 'hello client!',
        })

        self.assertEqual(status, 201)
        self.assertEqual(content, b'hello client!')

    def _make_configuration(self, test_logger, server_addr, overrides=None):
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
    def _make_server(configuration):
        def _on_instance(server):
            server.server_app = _create_and_expose_server(server.configuration)

        server_thread = make_wrapped_server(
            ThreadedApiHttpServer, configuration, on_instance=_on_instance)
        return server_thread


if __name__ == '__main__':
    testmain()
