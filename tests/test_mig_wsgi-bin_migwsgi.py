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


def create_instrumented_format_output(arranged):
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
            'text': arranged,
            'meta': '',
            'style': {},
            'script': {},
        })

        insertion_idx += 1
        out_obj.insert(insertion_idx, {
            'object_type': 'header',
            'text': arranged
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
    return _instrumented_format_output


def create_instrumented_retrieve_handler(output_objects=None, return_value=None):
    if not output_objects:
        output_objects = []

    assert isinstance(output_objects, list)
    assert _is_return_value(return_value), "return value must be present in returnvalues"

    def _instrumented_retrieve_handler(*args):
        return [], return_value
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


class MigSharedConfiguration(MigTestCase):
    def assertHtmlBasics(self, value):
        assert isinstance(value, type(u""))
        assert value.startswith("<!DOCTYPE")
        end_html_tag_idx = value.rfind('</html>')
        maybe_document_end = value[end_html_tag_idx:].rstrip()
        self.assertEqual(maybe_document_end, '</html>')

    def test_xxx(self):
        config = _assert_local_config()
        config_global_values = _assert_local_config_global_values(config)

        def fake_start_response(status, headers, exc=None):
            fake_start_response.calls.append((status, headers, exc))
        fake_start_response.calls = []

        def fake_set_environ(value):
            fake_set_environ.value = value
        fake_set_environ.value = None

        wsgi_environ = create_wsgi_environ(_TEST_CONF_FILE, wsgi_variables=dict(
            http_host='localhost',
            path_info='/',
        ))

        instrumented_format_output = create_instrumented_format_output('HELLO WORLD')
        instrumented_retrieve_handler = create_instrumented_retrieve_handler(None, returnvalues.OK)

        yielder = migwsgi._application(wsgi_environ, fake_start_response,
            _format_output=instrumented_format_output,
            _retrieve_handler=instrumented_retrieve_handler,
            _set_environ=fake_set_environ,
            _wrap_wsgi_errors=noop,
            _config_file=_TEST_CONF_FILE,
            _skip_log=True,
        )
        chunks = list(yielder)

        self.assertGreater(len(chunks), 0)
        value = codecs.decode(chunks[0], 'utf8')
        self.assertHtmlBasics(value)


if __name__ == '__main__':
    testmain()
