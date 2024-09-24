# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# htmlsupp - test support library for WSGI
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

from collections import namedtuple
import codecs
from io import BytesIO

from mig.shared.output import format_output
import mig.shared.returnvalues as returnvalues


def _is_return_value(return_value):
    defined_return_values = returnvalues.__dict__.values()
    return return_value in defined_return_values


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
        # capture the original before altering it
        call_args_out_obj = list(out_obj)
        call_args = (configuration, backend, ret_val, ret_msg,
                     call_args_out_obj, outputformat,)
        _instrumented_format_output.calls.append({'args': call_args})

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
        start_obj_idx = next((i for i, obj in enumerate(
            out_obj) if obj['object_type'] == 'start'))
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
        assert _is_return_value(
            return_value), "return value must be present in returnvalues"
        assert isinstance(output_objects, list)
        _simulated_action.returning = (output_objects, return_value)

    def _instrumented_retrieve_handler(*args):
        _instrumented_retrieve_handler.calls.append(tuple(args))
        return _simulated_action
    _instrumented_retrieve_handler.calls = []

    _instrumented_retrieve_handler.program = _program_response
    _instrumented_retrieve_handler.simulated = _simulated_action

    return _instrumented_retrieve_handler


class WsgibinInstrumentation:
    def __init__(self):
        self.fieldstorage_to_dict = create_instrumented_fieldstorage_to_dict()
        self.format_output = create_instrumented_format_output()
        self.retrieve_handler = create_instrumented_retrieve_handler()

    def _set_response_content(self, content, returnvalue):
        self.retrieve_handler.program(content, returnvalue)

    def _set_response_file(self, returnbytes, returnvalue):
        self.fieldstorage_to_dict.set_result({
            'output_format': ('file',)
        })
        self.format_output.set_file(True)
        file_obj = {'object_type': 'binary', 'data': returnbytes}
        self.set_response([file_obj], returnvalue)

    def set_response(self, content, returnvalue, responding_with='objects'):
        assert not (content is not None and file is not None)

        if responding_with == 'file':
            assert isinstance(
                returnvalue, bytes), "file response demands bytes"
            self._set_response_file(content, returnvalue)
        elif responding_with == 'objects':
            self._set_response_content(content, returnvalue)
        else:
            raise NotImplementedError()


class WsgibinAssertMixin:
    def assertWsgibinInstrumentation(self, instrumentation=None):
        if instrumentation is None:
            instrumentation = getattr(self, 'wsgibin_instrumentation', None)
        assert isinstance(instrumentation, WsgibinInstrumentation)

        simulated_action = instrumentation.retrieve_handler.simulated
        self.assertIsNotNone(simulated_action.returning,
                             "no response programmed")

        def was_called(fake):
            assert hasattr(fake, 'calls')
            return len(fake.calls) > 0

        self.assertTrue(was_called(
            instrumentation.format_output), "no output generated")
        self.assertTrue(was_called(
            instrumentation.retrieve_handler), "no output generated")
