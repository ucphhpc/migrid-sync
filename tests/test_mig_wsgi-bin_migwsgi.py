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


def _import_migwsgi():
    sys.path.append(os.path.join(MIG_BASE, 'mig/wsgi-bin'))
    migwsgi = importlib.import_module('migwsgi')
    sys.path.pop(-1)
    return migwsgi
migwsgi = _import_migwsgi()


def create_instrumented_format_output(arranged):
    def instrumented_format_output(
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
        instrumented_format_output.calls.append({ 'args': call_args })


        # FIXME: the following is a workaround for a bug that exists between the WSGI wrapper
        #        and the output formatter - specifically, the latter adds default header and
        #        title if start does not exist, but the former ensures that start always exists
        #        meaning that a default response under WSGI is missing half the HTML.
        start_obj_idx = next((i for i, obj in enumerate(out_obj) if obj['object_type'] == 'start'))
        insertion_idx = start_obj_idx

        insertion_idx += 1
        out_obj.insert(insertion_idx, {
            'object_type': 'title',
            'text': arranged,
            'meta': '',
            'style': {},
            'script': {},
        })

        # FIXME: format_output() will write the header _before_ the preamble unless there some
        #        other non-special output object prior to it.
        # insertion_idx += 1
        # out_obj.insert(insertion_idx, {
        #     'object_type': '__FORCEPREAMBLE__',
        # })

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
    instrumented_format_output.calls = []
    return instrumented_format_output


def create_wsgi_environ(config_file, wsgi_input=None, env_http_host=None, env_path_info=None):
    environ = {}
    environ['wsgi.input'] = ()
    environ['MIG_CONF'] = config_file
    environ['HTTP_HOST'] = env_http_host
    environ['PATH_INFO'] = env_path_info
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

        def fake_handler(*args):
            return [], returnvalues.OK

        def fake_start_response(status, headers, exc=None):
            fake_start_response.calls.append((status, headers, exc))
        fake_start_response.calls = []

        def fake_set_environ(value):
            fake_set_environ.value = value
        fake_set_environ.value = None

        wsgi_environ = create_wsgi_environ(
            _TEST_CONF_FILE,
            env_http_host='localhost',
            env_path_info='/'
        )

        instrumented_format_output = create_instrumented_format_output('HELLO WORLD')

        yielder = migwsgi._application(wsgi_environ, fake_start_response,
            _format_output=instrumented_format_output,
            _set_environ=fake_set_environ,
            _retrieve_handler=lambda _: fake_handler,
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
