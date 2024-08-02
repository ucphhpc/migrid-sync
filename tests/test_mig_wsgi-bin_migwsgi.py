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

from configparser import ConfigParser
import importlib
import os
import stat
import sys

from tests.support import MIG_BASE, MigTestCase, testmain
import mig.shared.returnvalues as returnvalues

def create_output_returner(arranged=None):
    def test_format_output(*args):
        return arranged
    return test_format_output

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


_WSGI_BIN = os.path.join(MIG_BASE, 'mig/wsgi-bin')

def _import_migwsgi():
    sys.path.append(_WSGI_BIN)
    migwsgi = importlib.import_module('migwsgi')
    sys.path.pop(-1)
    return migwsgi


migwsgi = _import_migwsgi()


class MigSharedConfiguration(MigTestCase):
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

        test_output_returner = create_output_returner('HELLO WORLD')

        yielder = migwsgi._application(wsgi_environ, fake_start_response,
            _set_environ=fake_set_environ,
            _retrieve_handler=lambda _: fake_handler,
            _wrap_wsgi_errors=noop,
            _config_file=_TEST_CONF_FILE,
            _skip_log=True,
        )
        chunks = list(yielder)

        self.assertGreater(len(chunks), 0)
        import codecs
        print(codecs.decode(chunks[0], 'utf8'))


if __name__ == '__main__':
    testmain()
