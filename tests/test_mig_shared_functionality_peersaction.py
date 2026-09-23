# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_functionality_cat - unit test of the corresponding mig module
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

"""Unit tests of the MiG functionality file implementing the cat backend"""

from __future__ import print_function
from datetime import date, timedelta
import importlib
import os
import shutil
import sys
from time import mktime
import unittest

from tests.support import MIG_BASE, PY2, TEST_DATA_DIR, MigTestCase, testmain, \
    temppath, ensure_dirs_exist
from tests.support.fixturesupp import TEST_FIXTURE_DIR
from tests.support.picklesupp import PickleAssertMixin
from tests.support.usersupp import UserAssertMixin

import mig.shared.returnvalues as returnvalues
from mig.shared.base import client_id_dir
from mig.shared.functionality.peersaction import _main as submain


def create_http_environ(configuration):
    """Small helper that can create a minimum viable environ dict suitable
    for passing to http-facing code for the supplied configuration.
    """

    environ = {}
    environ['MIG_CONF'] = configuration.config_file
    environ['HTTP_HOST'] = 'localhost'
    environ['PATH_INFO'] = '/'
    environ['REMOTE_ADDR'] = '127.0.0.1'
    environ['SCRIPT_URI'] = ''.join(('https://', environ['HTTP_HOST'],
                                     environ['PATH_INFO']))
    return environ


def _fake_safe_handler(*args):
    return True


def _only_output_objects(output_objects, with_object_type=None):
    return [o for o in output_objects if o['object_type'] == with_object_type]


class MigSharedFunctionalityPeersaction(MigTestCase,
                                        PickleAssertMixin,
                                        UserAssertMixin):
    """Wrap unit tests for the corresponding module"""

    TEST_CLIENT_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
    TEST_PEER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Peer User/emailAddress=peer@example.com'

    def _provide_configuration(self):
        return 'testconfig'

    def before_each(self):
        self.test_user_dir = self._provision_test_user(self, self.TEST_CLIENT_DN)
        self.test_environ = create_http_environ(self.configuration)

    @property
    def client_user_settings_dir(self):
        user_settings_dir = os.path.normpath(self.configuration.user_settings)
        return os.path.join(user_settings_dir, client_id_dir(self.TEST_CLIENT_DN))

    def assertSingleOutputObject(self, output_objects, with_object_type=None):
        assert with_object_type is not None
        found_objects = _only_output_objects(output_objects,
                                             with_object_type=with_object_type)
        self.assertEqual(len(found_objects), 1)
        return found_objects[0]

    def test_ignores_requests_with_peers_disabled(self):
        with open(os.path.join(self.test_user_dir, 'foobar.txt'), 'w'):
            pass
        payload = {
            'action': 'accept',
            'peers_label': [],
            'peers_kind': 'collaboration',
            'peers_expire': '',
            'peers_format': 'userid',
            'peers_content': ['ABCDE'],
            'peers_invite': '',
        }

        (output_objects, status) = submain(self.configuration, self.logger,
                                           client_id=self.TEST_CLIENT_DN,
                                           user_arguments_dict=payload,

                                           environ=self.test_environ,
                                           _safe_handler=_fake_safe_handler)

        self.assertEqual(status, returnvalues.OK)
        relevant_obj = self.assertSingleOutputObject(output_objects,
                                      with_object_type='text')
        text_lines = relevant_obj['text'].split('\n')
        self.assertEqual(text_lines[0], 'Peers use is disabled on this site.')

    def test_rejects_reqeusts_with_no_valid_peers_provided(self):
        self.configuration.site_enable_peers = True
        with open(os.path.join(self.test_user_dir, 'foobar.txt'), 'w'):
            pass
        payload = {
            'action': ['reject'],
            'peers_label': [],
            'peers_kind': ['collaboration'],
            'peers_expire': '',
            'peers_format': ['userid'],
            'peers_content': ['ABCDE'],
            'peers_invite': '',
        }
        def fake_safe_handler(*args):
            return True

        (output_objects, status) = submain(self.configuration, self.logger,
                                           client_id=self.TEST_CLIENT_DN,
                                           user_arguments_dict=payload,
                                           environ=self.test_environ,
                                           _safe_handler=_fake_safe_handler)

        # NOTE: no need to check page related entries
        output_objects = output_objects[3:]
        relevant_obj = self.assertSingleOutputObject(output_objects,
                                      with_object_type='error_text')
        self.assertTrue(relevant_obj['text'].startswith('Parsing failed:'))

    def test_creating_a_peer(self):
        self.configuration.site_enable_peers = True
        self.logger.forgive_errors()
        expire_in_3_days = int(mktime((date.today() + timedelta(days=3)).timetuple()))
        payload = {
            'action': ['accept'],
            'peers_label': [],
            'peers_kind': ['collaboration'],
            'peers_expire': [str(expire_in_3_days)],
            'peers_format': ['userid'],
            'peers_content': [self.TEST_PEER_DN],
            'peers_invite': '',
        }
        def fake_safe_handler(*args):
            return True

        (output_objects, status) = submain(self.configuration, self.logger,
                                           client_id=self.TEST_CLIENT_DN,
                                           user_arguments_dict=payload,
                                           environ=self.test_environ,
                                           _safe_handler=fake_safe_handler)

        self.assertEqual(status, returnvalues.OK)
        content = self.assertUserPeers(self.TEST_CLIENT_DN)
        self.assertIn(self.TEST_PEER_DN, content)

        fake_send_email = self.configuration.context_get('notifier').send_email
        self.assertTrue(fake_send_email.called_once)
        self.assertTrue(fake_send_email.email_was_sent_to('admin@example.com'))

    def test_importing_peers(self):
        self.configuration.site_enable_peers = True
        peers_csv = os.path.join(TEST_FIXTURE_DIR, "csv", "peers-for-import.csv")
        with open(peers_csv) as f:
            content = f.read()
        date_expire_in_8_days = date.today() + timedelta(days=8)

        payload = {
            'action': ['import'],
            'peers_content': [peers_csv],
            'peers_label': ['some_peer_label'],
            'peers_kind': ['course'],
            'peers_expire': [date_expire_in_8_days.isoformat()],
            'peers_format': ['csvform'],
            'peers_content': [content],
            'peers_invite': ['true'],
        }
        def fake_safe_handler(*args):
            return True

        (output_objects, status) = submain(self.configuration, self.logger,
                                           client_id=self.TEST_CLIENT_DN,
                                           user_arguments_dict=payload,
                                           environ=self.test_environ,
                                           _safe_handler=fake_safe_handler)

        fake_send_email = self.configuration.context_get('notifier').send_email
        self.assertTrue(fake_send_email.email_was_sent_to('admin@example.com'))
        self.assertTrue(fake_send_email.email_was_sent_to('peer1@example.com'))
        self.assertTrue(fake_send_email.email_was_sent_to('peer2@example.com'))
        self.assertTrue(fake_send_email.email_was_sent_to('peer3@example.com'))


if __name__ == '__main__':
    testmain()
