# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
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

"""Unit tests for the MiG WSGI glue"""

import codecs
from configparser import ConfigParser
import importlib
import os
import stat
import sys

from tests.support import MIG_BASE, MigTestCase, testmain
from mig.shared.output import format_output
import mig.shared.returnvalues as returnvalues


from tests.support import PY2, is_path_within
from mig.shared.base import client_id_dir, client_dir_id, get_short_id, \
    invisible_path, allow_script, brief_list


_LOCAL_MIG_BASE = '/usr/src/app' if PY2 else MIG_BASE # account for execution in container
_PYTHON_MAJOR = '2' if PY2 else '3'
_TEST_CONF_DIR = os.path.join(MIG_BASE, "envhelp/output/testconfs-py%s" % (_PYTHON_MAJOR,))
_TEST_CONF_FILE = os.path.join(_TEST_CONF_DIR, "MiGserver.conf")
_TEST_CONF_SYMLINK = os.path.join(MIG_BASE, "envhelp/output/testconfs")


# workaround for migwsgi being placed witin a non-module directory
def _import_migwsgi():
    sys.path.append(os.path.join(MIG_BASE, 'mig/wsgi-bin'))
    migwsgi = importlib.import_module('migwsgi')
    sys.path.pop(-1)
    return migwsgi
migwsgi = _import_migwsgi()


def _assert_local_config():
    try:
        link_stat = os.lstat(_TEST_CONF_SYMLINK)
        assert stat.S_ISLNK(link_stat.st_mode)
        configdir_stat = os.stat(_TEST_CONF_DIR)
        assert stat.S_ISDIR(configdir_stat.st_mode)
        config = ConfigParser()
        config.read([_TEST_CONF_FILE])
        return config
    except Exception as exc:
        raise AssertionError('local configuration invalid or missing: %s' % (str(exc),))


def _assert_local_config_global_values(config):
    config_global_values = dict(config.items('GLOBAL'))

    for path in ('mig_path', 'certs_path', 'state_path'):
        path_value = config_global_values.get(path)
        if not is_path_within(path_value, start=_LOCAL_MIG_BASE):
            raise AssertionError('local config contains bad path: %s=%s' % (path, path_value))

    return config_global_values


def _is_return_value(return_value):
    defined_return_values = returnvalues.__dict__.values()
    return return_value in defined_return_values


def _trigger_and_unpack_result(application_result):
    chunks = list(application_result)
    assert len(chunks) > 0, "invocation returned no output"
    complete_value = b''.join(chunks)
    decoded_value = codecs.decode(complete_value, 'utf8')
    return decoded_value


def create_instrumented_format_output():
    def _instrumented_format_output(
        configuration,
        backend,
        ret_val,
        ret_msg,
        out_obj,
        outputformat,
    ):
        # record the call args
        call_args_out_obj = list(out_obj) # capture the original before altering it
        call_args = (configuration, backend, ret_val, ret_msg, call_args_out_obj, outputformat,)
        _instrumented_format_output.calls.append({ 'args': call_args })

        # FIXME: the following is a workaround for a bug that exists between the WSGI wrapper
        #        and the output formatter - specifically, the latter adds default header and
        #        title if start does not exist, but the former ensures that start always exists
        #        meaning that a default response under WSGI is missing half the HTML.
        start_obj_idx = next((i for i, obj in enumerate(out_obj) if obj['object_type'] == 'start'))
        insertion_idx = start_obj_idx

        # FIXME: format_output() is sensitive to ordering and MUST see a title object _before_
        #        anything else otherwise the preamble ends up written above the header and thus
        #        an invalid HTML page is served.
        insertion_idx += 1
        out_obj.insert(insertion_idx, {
            'object_type': 'title',
            'text': _instrumented_format_output.values['title_text'],
            'meta': '',
            'style': {},
            'script': {},
        })

        insertion_idx += 1
        out_obj.insert(insertion_idx, {
            'object_type': 'header',
            'text': _instrumented_format_output.values['header_text']
        })

        return format_output(
            configuration,
            backend,
            ret_val,
            ret_msg,
            out_obj,
            outputformat,
        )
    _instrumented_format_output.calls = []
    _instrumented_format_output.values = dict(
        title_text='',
        header_text='',
    )

    def _program_values(**kwargs):
        _instrumented_format_output.values.update(kwargs)

    _instrumented_format_output.set_values = _program_values

    return _instrumented_format_output


def create_instrumented_retrieve_handler():
    def _simulated_action(*args):
        return _simulated_action.returning or ([], returnvalues.ERROR)
    _simulated_action.calls = []
    _simulated_action.returning = None

    def _program_response(output_objects=None, return_value=None):
        assert _is_return_value(return_value), "return value must be present in returnvalues"
        assert isinstance(output_objects, list)
        _simulated_action.returning = (output_objects, return_value)

    def _instrumented_retrieve_handler(*args):
        _instrumented_retrieve_handler.calls.append(tuple(args))
        return _simulated_action
    _instrumented_retrieve_handler.calls = []

    _instrumented_retrieve_handler.program = _program_response
    _instrumented_retrieve_handler.simulated = _simulated_action

    return _instrumented_retrieve_handler


def create_wsgi_environ(config_file, wsgi_variables):
    environ = {}
    environ['wsgi.input'] = ()
    environ['MIG_CONF'] = config_file
    environ['HTTP_HOST'] = wsgi_variables.get('http_host')
    environ['PATH_INFO'] = wsgi_variables.get('path_info')
    environ['SCRIPT_URI'] = ''.join(('http://', environ['HTTP_HOST'], environ['PATH_INFO']))
    return environ


def noop(*args):
    pass


class MigWsgi_binMigwsgi(MigTestCase):
    def assertInstrumentation(self):
        simulated_action = self.instrumented_retrieve_handler.simulated
        self.assertIsNotNone(simulated_action.returning, "no response programmed")

        def was_called(fake):
            assert hasattr(fake, 'calls')
            return len(fake.calls) > 0

        self.assertTrue(was_called(self.instrumented_format_output), "no output generated")
        self.assertTrue(was_called(self.instrumented_retrieve_handler), "no output generated")

    def assertResponseStatus(self, expected_status_code):
        def called_once(fake):
            assert hasattr(fake, 'calls')
            return len(fake.calls) == 1

        self.assertTrue(called_once(self.fake_start_response))
        thecall = self.fake_start_response.calls[0]
        wsgi_status = thecall[0]
        actual_status_code = int(wsgi_status[0:3])
        self.assertEqual(actual_status_code, expected_status_code)

    def assertHtmlElementTextContent(self, output, tag_name, expected_text, trim_newlines=True):
        # TODO: this is a definitively stop-gap way of finding a tag within the HTML
        #       and is used purely to keep this initial change to a reasonable size.
        tag_open = ''.join(['<', tag_name, '>'])
        tag_open_index = output.index(tag_open)
        tag_close = ''.join(['</', tag_name, '>'])
        tag_close_index = output.index(tag_close)
        actual_text = output[tag_open_index+len(tag_open):tag_close_index]
        if trim_newlines:
            actual_text = actual_text.strip('\n')
        self.assertEqual(actual_text, expected_text)

    def assertIsValidHtmlDocument(self, value):
        assert isinstance(value, type(u""))
        assert value.startswith("<!DOCTYPE")
        end_html_tag_idx = value.rfind('</html>')
        maybe_document_end = value[end_html_tag_idx:].rstrip()
        self.assertEqual(maybe_document_end, '</html>')

    def before_each(self):
        config = _assert_local_config()
        config_global_values = _assert_local_config_global_values(config)

        def fake_start_response(status, headers, exc=None):
            fake_start_response.calls.append((status, headers, exc))
        fake_start_response.calls = []
        self.fake_start_response = fake_start_response

        def fake_set_environ(value):
            fake_set_environ.calls.append((value))
        fake_set_environ.calls = []
        self.fake_set_environ = fake_set_environ

        fake_wsgi_environ = create_wsgi_environ(_TEST_CONF_FILE, wsgi_variables=dict(
            http_host='localhost',
            path_info='/',
        ))

        self.instrumented_format_output = create_instrumented_format_output()
        self.instrumented_retrieve_handler = create_instrumented_retrieve_handler()

        self.application_args = (fake_wsgi_environ, fake_start_response,)
        self.application_kwargs = dict(
            _format_output=self.instrumented_format_output,
            _retrieve_handler=self.instrumented_retrieve_handler,
            _set_environ=fake_set_environ,
        )

    def test_return_value_ok_returns_status_200(self):
        self.instrumented_retrieve_handler.program([], returnvalues.OK)

        application_result = migwsgi._application(
            *self.application_args,
            _wrap_wsgi_errors=noop,
            _config_file=_TEST_CONF_FILE,
            _skip_log=True,
            **self.application_kwargs
        )

        _trigger_and_unpack_result(application_result)

        self.assertInstrumentation()
        self.assertResponseStatus(200)

    def test_return_value_ok_returns_valid_html_page(self):
        self.instrumented_retrieve_handler.program([], returnvalues.OK)

        application_result = migwsgi._application(
            *self.application_args,
            _wrap_wsgi_errors=noop,
            _config_file=_TEST_CONF_FILE,
            _skip_log=True,
            **self.application_kwargs
        )

        output = _trigger_and_unpack_result(application_result)

        self.assertInstrumentation()
        self.assertIsValidHtmlDocument(output)

    def test_return_value_ok_returns_expected_title(self):
        self.instrumented_format_output.set_values(title_text='TEST')
        self.instrumented_retrieve_handler.program([], returnvalues.OK)

        application_result = migwsgi._application(
            *self.application_args,
            _wrap_wsgi_errors=noop,
            _config_file=_TEST_CONF_FILE,
            _skip_log=True,
            **self.application_kwargs
        )

        output = _trigger_and_unpack_result(application_result)

        self.assertInstrumentation()
        self.assertHtmlElementTextContent(output, 'title', 'TEST', trim_newlines=True)


if __name__ == '__main__':
    testmain()
