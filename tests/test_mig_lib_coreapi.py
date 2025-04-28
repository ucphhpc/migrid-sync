import codecs
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from tests.support import MigTestCase, testmain
from tests.support.serversupp import make_wrapped_server

from mig.lib.coreapi import CoreApiClient


class TestRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        test_server = self.server

        if test_server._programmed_response:
            status, content = test_server._programmed_response
        elif test_server._programmed_error:
            status, content = test_server._programmed_error

        self.send_response(status)
        self.end_headers()
        self.wfile.write(content)


class TestHTTPServer(HTTPServer):
    def __init__(self, addr, **kwargs):
        self._programmed_error = None
        self._programmed_response = None
        self._on_start = kwargs.pop('on_start', lambda _: None)

        HTTPServer.__init__(self, addr, TestRequestHandler, **kwargs)

    def clear_programmed(self):
        self._programmed_error = None

    def set_programmed_error(self, status, content):
        assert self._programmed_response is None
        assert isinstance(content, bytes)
        self._programmed_error = (status, content)

    def set_programmed_response(self, status, content):
        assert self._programmed_error is None
        assert isinstance(content, bytes)
        self._programmed_response = (status, content)

    def set_programmed_json_response(self, status, content):
        self.set_programmed_response(status, codecs.encode(json.dumps(content), 'utf8'))

    def server_activate(self):
        HTTPServer.server_activate(self)
        self._on_start(self)


class TestMigLibCoreapi(MigTestCase):
    def before_each(self):
        self.server_addr = ('localhost', 4567)
        self.server = make_wrapped_server(TestHTTPServer, self.server_addr)

    def after_each(self):
        server = getattr(self, 'server', None)
        setattr(self, 'server', None)
        if server:
            server.stop()

    def test_raises_in_the_absence_of_success(self):
        self.server.start_wait_until_ready()
        self.server.set_programmed_error(418, b'tea; earl grey; hot')
        instance = CoreApiClient("http://%s:%s/" % self.server_addr)

        with self.assertRaises(Exception):
            instance.createUser({
                'full_name': "Test User",
                'organization': "Test Org",
                'state': "NA",
                'country': "DK",
                'email': "user@example.com",
                'comment': "This is the create comment",
                'password': "password",
            })

    def test_returs_a_user_object(self):
        test_content = {
            'foo': 1,
            'bar': True
        }
        self.server.start_wait_until_ready()
        self.server.set_programmed_json_response(201, test_content)
        instance = CoreApiClient("http://%s:%s/" % self.server_addr)

        content = instance.createUser({
            'full_name': "Test User",
            'organization': "Test Org",
            'state': "NA",
            'country': "DK",
            'email': "user@example.com",
            'comment': "This is the create comment",
            'password': "password",
        })

        self.assertIsInstance(content, dict)
        self.assertEqual(content, test_content)

if __name__ == '__main__':
    testmain()
