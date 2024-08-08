from __future__ import print_function
import os
import sys
import threading

from tests.support import PY2, MIG_BASE, MigTestCase, testmain, make_wrapped_server

from mig.server.grid_openid import ThreadedOpenIDHTTPServer, _extend_configuration, main
from mig.shared.conf import get_configuration_object

if PY2:
    from urllib2 import HTTPError, urlopen
else:
    from urllib.error import HTTPError
    from urllib.request import urlopen


class MigServerGrid_openid(MigTestCase):
    def before_each(self):
        self.server_addr = None
        self.server_thread = None

    def after_each(self):
        if self.server_thread:
            self.server_thread.stop()

    def _provide_configuration(self):
        return 'testconfig'


    def issue_request(self, request_path):
        assert isinstance(request_path, str) and request_path.startswith('/'), "require http path starting with /"
        request_url =  ''.join(('http://', self.server_addr[0], ':', str(self.server_addr[1]), request_path))
        try:
            response = urlopen(request_url, None, timeout=2000)

            status = response.getcode()
            data = response.read()
            return (status, data)
        except HTTPError as httpexc:
            return (httpexc.code, None)

    def test_top_level_request_responds_status_ok(self):
        self.server_addr = ('localhost', 4567)
        configuration = self._make_configuration(self.configuration, self.logger, self.server_addr)
        self.server_thread = self._make_server(configuration).start_wait_until_ready()

        status, _ = self.issue_request('/')

        self.assertEqual(status, 200)

    def test_unknown_request_responds_status_bad_request(self):
        self.server_addr = ('localhost', 4567)
        configuration = self._make_configuration(self.configuration, self.logger, self.server_addr)
        self.server_thread = self._make_server(configuration).start_wait_until_ready()

        status, _ = self.issue_request('/foobar')

        self.assertEqual(status, 404)

    @staticmethod
    def _make_configuration(configuration, test_logger, server_addr):
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
        return make_wrapped_server(ThreadedOpenIDHTTPServer, configuration)


if __name__ == '__main__':
    testmain()
