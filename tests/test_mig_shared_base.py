# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_compat - unit test of the corresponding mig shared module
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

"""Unit tests for the migrid module pointed to in the filename"""

import binascii
import os
import sys

from tests.support import PY2, MigTestCase, testmain

from mig.shared.base import force_default_fs_coding_rec, force_default_str_coding_rec

DUMMY_BYTECHARS = b'DEADBEEF'
DUMMY_BYTESRAW = binascii.unhexlify('DEADBEEF') # 4 bytes
DUMMY_UNICODE = u'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®'


class MigSharedBase__force_default_fs_coding_rec(MigTestCase):
    """Unit tests of mig.shared.base force_default_fs_coding_rec()"""

    def test_encode_a_string(self):
        output = force_default_fs_coding_rec('foobar')

        self.assertEqual(output, 'foobar')

    def test_encode_within_a_dict(self):
        output = force_default_fs_coding_rec({ 'key': 'value' })

        self.assertEqual(output, { 'key': 'value' })

    def test_encode_within_a_list(self):
        output = force_default_fs_coding_rec(['foo', 'bar', 'baz'])

        self.assertEqual(output, ['foo', 'bar', 'baz'])

    def test_encode_within_a_tuple(self):
        output = force_default_fs_coding_rec(('foo', 'bar', 'baz'))

        self.assertEqual(output, ('foo', 'bar', 'baz'))


class MigSharedBase__force_default_str_coding_rec(MigTestCase):
    """Unit tests of mig.shared.base force_default_str_coding_rec()"""

    def test_encode_a_string(self):
        output = force_default_str_coding_rec('foobar')

        self.assertEqual(output, 'foobar')

    def test_encode_within_a_dict(self):
        output = force_default_str_coding_rec({ 'key': 'value' })

        self.assertEqual(output, { 'key': 'value' })

    def test_encode_within_a_list(self):
        output = force_default_str_coding_rec(['foo', 'bar', 'baz'])

        self.assertEqual(output, ['foo', 'bar', 'baz'])

    def test_encode_within_a_tuple(self):
        output = force_default_str_coding_rec(('foo', 'bar', 'baz'))

        self.assertEqual(output, ('foo', 'bar', 'baz'))


if __name__ == '__main__':
    testmain()
