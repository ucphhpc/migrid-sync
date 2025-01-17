#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# testcore - Set of unit tests for shared core daemon helper functions
# Copyright (C) 2010-2020  The MiG Project lead by Brian Vinter
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

"""Unit tests for core helper functions"""
from __future__ import print_function

from builtins import range
from configparser import ConfigParser
import os
import stat
import sys
import time
import logging

sys.path.append(os.path.realpath(
    os.path.join(os.path.dirname(__file__), "../..")))
from tests.support import MIG_BASE, PY2, is_path_within

from mig.shared.base import client_id_dir, client_dir_id, get_short_id, \
    invisible_path, allow_script, brief_list


_TEST_CONF_FILE = os.environ['MIG_CONF']
_TEST_CONF_DIR = os.path.dirname(_TEST_CONF_FILE)
_TEST_CONF_SYMLINK = os.path.join(MIG_BASE, "envhelp/output/testconfs")


def _assert_local_config():
    try:
        #link_stat = os.lstat(_TEST_CONF_SYMLINK)
        #assert stat.S_ISLNK(link_stat.st_mode)
        _test_conf_dir = os.path.dirname(_TEST_CONF_DIR)
        configdir_stat = os.stat(_test_conf_dir)
        assert stat.S_ISDIR(configdir_stat.st_mode)
        config = ConfigParser()
        config.read([_TEST_CONF_FILE])
        return config
    except Exception as exc:
        raise AssertionError(
            'local configuration invalid or missing: %s' % (str(exc),))


def _assert_local_config_global_values(config):
    config_global_values = dict(config.items('GLOBAL'))

    for path in ('mig_path', 'certs_path', 'state_path'):
        path_value = config_global_values.get(path)
        if not is_path_within(path_value, start=MIG_BASE):
            raise AssertionError('local config contains bad path: %s=%s' % (path, path_value))

    return config_global_values


def main(configuration, _exit=sys.exit):
    config = _assert_local_config()
    config_global_values = _assert_local_config_global_values(config)

    print("Running unit test on shared core functions ..")

    short_alias = 'email'
    test_clients = [
        ('/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk',
         '+C=DK+ST=NA+L=NA+O=NBI+OU=NA+CN=Jonas_Bardino+emailAddress=bardino@nbi.ku.dk',
         'bardino@nbi.ku.dk')]

    for (test_id, test_dir, test_short) in test_clients:
        print("Lookup client_id_dir for %s" % test_id)
        client_dir = client_id_dir(test_id)
        print("Client dir: %s" % client_dir)
        print("Lookup client_dir_id for %s" % test_dir)
        client_id = client_dir_id(test_dir)
        print("Client id: %s" % client_id)
        print("Lookup get_short_id for %s" % test_id)
        client_short = get_short_id(configuration, client_id, short_alias)
        print("Client short id: %s" % client_short)
    if client_id != test_id:
        print("ERROR: Expected match on IDs but found: %s vs %s" %
              (client_id, test_id))
        _exit(1)
    if client_dir != test_dir:
        print("ERROR: Expected match on dirs but found: %s vs %s" %
              (client_dir, test_dir))
        _exit(1)
    if client_short != test_short:
        print("ERROR: Expected match on %s but found: %s vs %s" %
              (short_alias, client_short, test_short))
        _exit(1)


    orig_id = '/X=ab/Y=cdef ghi/Z=klmn'
    client_dir = client_id_dir(orig_id)
    client_id = client_dir_id(client_dir)
    test_paths = ['simple.txt', 'somedir/somefile.txt']
    sample_file = '.htaccess'
    sample_dir = '.vgridscm'
    illegal = ["%s%s%s" % (prefix, sample_dir, suffix) for (prefix, suffix) in
               [('', ''), ('./', ''), ('/', ''), ('somedir/', ''),
                ('/somedir/', ''), ('somedir/sub/', ''), ('/somedir/sub/', ''),
                ('', '/sub'), ('', '/sub/sample.txt'),
                ('somedir/', '/sample.txt'), ('/somedir/', '/sample.txt'),
                ('/somedir/sub/', '/sample.txt')]] + \
        ["%s%s" % (prefix, sample_file) for prefix, _ in
         [('', ''), ('./', ''), ('/', ''), ('somedir/', ''),
          ('/somedir/', ''), ('somedir/sub/', ''), ('/somedir/sub/', ''),
          ]]
    legal = ["%s%s%s" % (prefix, sample_file, suffix) for (prefix, suffix) in
             [('prefix', ''), ('somedir/prefix', ''), ('', 'suffix'),
              ('', 'suffix/somedir'), ('prefix', 'suffix')]] +\
        ["%s%s%s" % (prefix, sample_dir, suffix) for (prefix, suffix) in
         [('prefix', ''), ('somedir/prefix', ''), ('', 'suffix'),
          ('', 'suffix/somedir'), ('prefix', 'suffix')]]
    legal += ['sample.txt', 'somedir/sample.txt', '/somedir/sample.txt']
    # print("orig id %s, dir %s, id %s (match %s)" %
    #     (orig_id, client_dir, client_id, orig_id == client_id))
    print("Visible vs invisible path tests")
    # print("make sure these are visible:")
    for path in legal:
        if invisible_path(path):
            print("ERROR: Expected visible on %s but not the case" % path)
            _exit(1)
    # print("check that these are invisible:")
    for path in illegal:
        if not invisible_path(path):
            print("ERROR: Expected invisible on %s but not the case" % path)
            _exit(1)

    print("Check script restrictions:")
    access_any = ['reqoid.py', 'docs.py', 'ls.py']
    access_auth = ['sharelink.py', 'put', 'home.py']
    for script_name in access_any:
        (allow, msg) = allow_script(configuration, script_name, '')
        if not allow:
            print("ERROR: Expected anon access to %s but not the case" %
                  script_name)
            _exit(1)
        (allow, msg) = allow_script(configuration, script_name, client_id)
        if not allow:
            print("ERROR: Expected auth access to %s but not the case" %
                  script_name)
            _exit(1)
    for script_name in access_auth:
        (allow, msg) = allow_script(configuration, script_name, '')
        if configuration.site_enable_gdp and allow:
            print("ERROR: Expected anon restrict to %s but not the case" %
                  script_name)
            _exit(1)
        (allow, msg) = allow_script(configuration, script_name, client_id)
        if not allow:
            print("ERROR: Expected auth access to %s but not the case" %
                  script_name)
            _exit(1)

    print("Check brief format list limit")
    for (size, outlen) in [(5, 15), (30, 58), (200, 63)]:
        shortened = "%s" % brief_list(list(range(size)))
        if len(shortened) != outlen:
            print("ERROR: Expected brief range %d list of length %d but not the case: %s" %
                  (size, outlen, len(shortened)))
            _exit(1)

    print("Running unit test on shared core functions DONE")

    _exit(0)

if __name__ == "__main__":
    from mig.shared.conf import get_configuration_object
    main(get_configuration_object())
