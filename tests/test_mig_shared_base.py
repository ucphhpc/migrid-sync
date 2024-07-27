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

from mig.shared.base import force_default_fs_coding_rec, \
    force_default_fs_coding, force_default_str_coding_rec, \
    force_default_str_coding, force_utf8, force_unicode

DUMMY_BYTECHARS = b'DEADBEEF'
DUMMY_BYTESRAW = binascii.unhexlify('DEADBEEF') # 4 bytes
DUMMY_UNICODE = u'UniCode123½¾µßðþđŋħĸþł@ª€£$¥©®'


class MigSharedBase__force_default_fs_coding_rec(MigTestCase):
    """Unit tests of mig.shared.base force_default_fs_coding_rec()"""

    def test_encode_a_string(self):
        output = force_default_fs_coding_rec('foobar')

        self.assertEqual(output, b'foobar')

    def test_encode_within_a_dict(self):
        output = force_default_fs_coding_rec({ 'key': 'value' })

        self.assertEqual(output, { b'key': b'value' })

    def test_encode_within_a_list(self):
        output = force_default_fs_coding_rec(['foo', 'bar', 'baz'])

        self.assertEqual(output, [b'foo', b'bar', b'baz'])

    def test_encode_within_a_tuple_string(self):
        output = force_default_fs_coding_rec(('foo', 'bar', 'baz'))

        self.assertEqual(output, (b'foo', b'bar', b'baz'))

    def test_encode_within_a_tuple_bytes(self):
        output = force_default_fs_coding_rec((b'foo', b'bar', b'baz'))

        self.assertEqual(output, (b'foo', b'bar', b'baz'))

    def test_encode_within_a_tuple_unicode(self):
        output = force_default_fs_coding_rec((u'foo', u'bar', u'baz'))

        self.assertEqual(output, (b'foo', b'bar', b'baz'))


class MigSharedBase__force_utf8(MigTestCase):
    """Unit tests of mig.shared.base force_utf8()"""

    def test_encode_string(self):
        output = force_utf8('foobar')

        self.assertEqual(output, b'foobar')

    def test_encode_bytes(self):
        output = force_utf8(b'foobar')

        self.assertEqual(output, b'foobar')

    def test_encode_unicode(self):
        output = force_utf8(u'foobar')

        self.assertEqual(output, b'foobar')


class MigSharedBase__force_unicode(MigTestCase):
    """Unit tests of mig.shared.base force_unicode()"""

    def test_encode_string(self):
        output = force_unicode('foobar')

        self.assertEqual(output, u'foobar')

    def test_encode_bytes(self):
        output = force_unicode(b'foobar')

        self.assertEqual(output, u'foobar')

    def test_encode_unicode(self):
        output = force_unicode(u'foobar')

        self.assertEqual(output, u'foobar')

if __name__ == '__main__':
    testmain(failfast=True)
