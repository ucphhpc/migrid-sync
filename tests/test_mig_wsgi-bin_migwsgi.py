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

from tests.support import MIG_BASE, TEST_BASE, TEST_DATA_DIR, MigTestCase, testmain
from mig.shared.output import format_output
import mig.shared.returnvalues as returnvalues


from tests.support import PY2, is_path_within, \
    create_wsgi_environ, create_wsgi_start_response, \
    ServerAssertMixin, HtmlAssertMixin
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


def _is_return_value(return_value):
    defined_return_values = returnvalues.__dict__.values()
    return return_value in defined_return_values


def _trigger_and_unpack_result(application_result, result_kind='textual'):
    assert result_kind in ('textual', 'binary', 'none')

    chunks = list(application_result)

    if result_kind == 'none':
        assert len(chunks) == 0, "invocation returned output but none expected"
        return None

    assert len(chunks) > 0, "invocation returned no output"
    complete_value = b''.join(chunks)
    if result_kind == 'binary':
        decoded_value = complete_value
    else:
        decoded_value = codecs.decode(complete_value, 'utf8')
    return decoded_value


def create_instrumented_fieldstorage_to_dict():
    def _instrumented_fieldstorage_to_dict(fieldstorage):
        return _instrumented_fieldstorage_to_dict._result

    _instrumented_fieldstorage_to_dict._result = {
        'output_format': ('html',)
    }

    def set_result(result):
        _instrumented_fieldstorage_to_dict._result = result

    _instrumented_fieldstorage_to_dict.set_result = set_result

    return _instrumented_fieldstorage_to_dict


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

        if _instrumented_format_output._file:
            return format_output(
                configuration,
                backend,
                ret_val,
                ret_msg,
                out_obj,
                outputformat,
            )

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
    _instrumented_format_output._file = False
    _instrumented_format_output.values = dict(
        title_text='',
        header_text='',
    )


    def _set_file(is_enabled):
        _instrumented_format_output._file = is_enabled

    setattr(_instrumented_format_output, 'set_file', _set_file)

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


def noop(*args):
    pass


class MigWsgi_binMigwsgi(MigTestCase, ServerAssertMixin, HtmlAssertMixin):
    def assertInstrumentation(self):
        simulated_action = self.instrumented_retrieve_handler.simulated
        self.assertIsNotNone(simulated_action.returning, "no response programmed")

        def was_called(fake):
            assert hasattr(fake, 'calls')
            return len(fake.calls) > 0

        self.assertTrue(was_called(self.instrumented_format_output), "no output generated")
        self.assertTrue(was_called(self.instrumented_retrieve_handler), "no output generated")

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        # generic WSGI setup
        self.fake_wsgi_environ = create_wsgi_environ(self.configuration, wsgi_variables=dict(
            http_host='localhost',
            path_info='/',
        ))
        self.fake_start_response = create_wsgi_start_response()

        # MiG WSGI wrapper specific setup
        self.instrumented_fieldstorage_to_dict = create_instrumented_fieldstorage_to_dict()
        self.instrumented_format_output = create_instrumented_format_output()
        self.instrumented_retrieve_handler = create_instrumented_retrieve_handler()

        self.application_args = (self.configuration, self.fake_wsgi_environ, self.fake_start_response,)
        self.application_kwargs = dict(
            _wrap_wsgi_errors=noop,
            _format_output=self.instrumented_format_output,
            _fieldstorage_to_dict=self.instrumented_fieldstorage_to_dict,
            _retrieve_handler=self.instrumented_retrieve_handler,
            _set_environ=noop,
        )

    def test_return_value_ok_returns_status_200(self):
        self.instrumented_retrieve_handler.program([], returnvalues.OK)

        application_result = migwsgi._application(
            *self.application_args,
            **self.application_kwargs
        )

        _trigger_and_unpack_result(application_result)

        self.assertInstrumentation()
        self.assertWsgiResponseStatus(self.fake_start_response, 200)

    def test_return_value_ok_returns_valid_html_page(self):
        self.instrumented_retrieve_handler.program([], returnvalues.OK)

        application_result = migwsgi._application(
            *self.application_args,
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
            **self.application_kwargs
        )

        output = _trigger_and_unpack_result(application_result)

        self.assertInstrumentation()
        self.assertHtmlElementTextContent(output, 'title', 'TEST', trim_newlines=True)

    def test_return_value_ok_serving_a_binary_file(self):
        test_binary_file = os.path.join(TEST_DATA_DIR, 'loading.gif')
        with open(test_binary_file, 'rb') as f:
            test_binary_data = f.read()

        self.instrumented_fieldstorage_to_dict.set_result({
            'output_format': ('file',)
        })
        self.instrumented_format_output.set_file(True)

        file_obj = { 'object_type': 'binary', 'data': test_binary_data }
        self.instrumented_retrieve_handler.program([file_obj], returnvalues.OK)

        application_result = migwsgi._application(
            *self.application_args,
            **self.application_kwargs
        )

        output = _trigger_and_unpack_result(application_result, 'binary')

        self.assertInstrumentation()
        self.assertEqual(output, test_binary_data)

    def test_serve_paths_signle_file_at_limit(self):
        test_binary_file = os.path.join(TEST_DATA_DIR, 'loading.gif')
        test_binary_file_size = os.stat(test_binary_file).st_size
        with open(test_binary_file, 'rb') as fh_test_file:
            test_binary_data = fh_test_file.read()

        self.configuration.migserver_server_maxsize = test_binary_file_size

        self.instrumented_fieldstorage_to_dict.set_result({
            'output_format': ('serve',)
        })
        self.instrumented_format_output.set_file(True)

        output_obj = {
            'object_type': 'serve_paths',
            'paths': [test_binary_file]
        }
        self.instrumented_retrieve_handler.program([output_obj], returnvalues.OK)

        application_result = migwsgi._application(
            *self.application_args,
            **self.application_kwargs
        )

        output = _trigger_and_unpack_result(application_result, 'binary')

        self.assertInstrumentation()
        self.assertEqual(output, test_binary_data)

    def test_serve_paths_signle_file_over_limit(self):
        test_binary_file = os.path.join(TEST_DATA_DIR, 'loading.gif')
        test_binary_file_size = os.stat(test_binary_file).st_size
        with open(test_binary_file, 'rb') as fh_test_file:
            test_binary_data = fh_test_file.read()

        self.configuration.migserver_server_maxsize = test_binary_file_size - 1

        self.instrumented_fieldstorage_to_dict.set_result({
            'output_format': ('serve',)
        })
        self.instrumented_format_output.set_file(True)

        output_obj = {
            'object_type': 'serve_paths',
            'paths': [test_binary_file]
        }
        self.instrumented_retrieve_handler.program([output_obj], returnvalues.OK)

        application_result = migwsgi._application(
            *self.application_args,
            **self.application_kwargs
        )

        _trigger_and_unpack_result(application_result, 'none')

        self.assertInstrumentation()
        self.assertWsgiResponseStatus(self.fake_start_response, 422)


if __name__ == '__main__':
    testmain()
