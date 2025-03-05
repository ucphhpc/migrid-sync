import codecs
import json

from tests.support._env import PY2

if PY2:
    from urllib2 import HTTPError, Request, urlopen
    from urllib import urlencode
else:
    from urllib.error import HTTPError
    from urllib.parse import urlencode
    from urllib.request import urlopen, Request

from mig.lib.coresvc.payloads import PAYLOAD_POST_USER


def attempt_to_decode_response_data(data, response_encoding=None):
    if data is None:
        return None
    elif response_encoding == 'textual':
        data = codecs.decode(data, 'utf8')

        try:
            return json.loads(data)
        except Exception as e:
            return data
    elif response_encoding == 'binary':
        return data
    else:
        raise AssertionError(
            'issue_POST: unknown response_encoding "%s"' % (response_encoding,))


class CoreApiClient:
    def __init__(self, base_url):
        self._base_url = base_url

    def _issue_GET(self, request_path, query_dict=None, response_encoding='textual'):
        request_url = ''.join((self._base_url, request_path))

        if query_dict is not None:
            query_string = urlencode(query_dict)
            request_url = ''.join((request_url, '?', query_string))

        status = 0
        data = None

        try:
            response = urlopen(request_url, None, timeout=2000)

            status = response.getcode()
            data = response.read()
        except HTTPError as httpexc:
            status = httpexc.code
            data = None

        content = attempt_to_decode_response_data(data, response_encoding)
        return (status, content)

    def _issue_POST(self, request_path, request_data=None, request_json=None, response_encoding='textual'):
        request_url = ''.join((self._base_url, request_path))

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
            data = httpexc.fp.read()

        content = attempt_to_decode_response_data(data, response_encoding)
        return (status, content)

    def createUser(self, user_dict):
        payload = PAYLOAD_POST_USER.ensure(user_dict)

        return self._issue_POST('/user', request_json=dict(payload))
