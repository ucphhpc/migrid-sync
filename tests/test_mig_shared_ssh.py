# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_ssh - unit test of the corresponding mig shared module
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

import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from tests.support import TEST_OUTPUT_DIR, MigTestCase, FakeConfiguration, \
    cleanpath, testmain
from mig.shared.ssh import supported_pub_key_parsers, parse_pub_key, \
    generate_ssh_rsa_key_pair


class MigSharedSsh(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_ssh_key_generate_and_parse(self):
        parsers = supported_pub_key_parsers()
        # NOTE: should return a non-empty dict of algos and parsers
        self.assertTrue(parsers)
        self.assertTrue('ssh-rsa' in parsers)

        # Generate common sized keys and parse the result
        for keysize in (2048, 3072, 4096):
            (priv_key, pub_key) = generate_ssh_rsa_key_pair(size=keysize)
            self.assertTrue(priv_key)
            self.assertTrue(pub_key)

            # NOTE: parse_pub_key expects a native string so we use this case
            try:
                parsed = parse_pub_key(pub_key)
            except ValueError as vae:
                #print("Error in parsing pub key: %r" % vae)
                parsed = None
            self.assertTrue(parsed is not None)

            (priv_key, pub_key) = generate_ssh_rsa_key_pair(size=keysize,
                                                            encode_utf8=True)
            self.assertTrue(priv_key)
            self.assertTrue(pub_key)


if __name__ == '__main__':
    testmain()
