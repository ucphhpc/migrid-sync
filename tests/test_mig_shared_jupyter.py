# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_jupyter - unit test of the corresponding mig shared module
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
import time
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from tests.support import TEST_OUTPUT_DIR, MigTestCase, FakeConfiguration, \
    cleanpath, testmain
from mig.shared.jupyter import gen_openid_template


class MigSharedJupyter(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_jupyter_gen_openid_template_openid_auth(self):
        filled = gen_openid_template("/some-jupyter-url", "MyDefine", "OpenID")
        expected = """
<IfDefine MyDefine>
    <Location /some-jupyter-url>
        # Pass SSL variables on
        SSLOptions +StdEnvVars
        AuthType OpenID
        require valid-user
    </Location>
</IfDefine>
"""
        self.assertEqual(filled, expected)

    def test_jupyter_gen_openid_template_oidc_auth(self):
        filled = gen_openid_template("/some-jupyter-url", "MyDefine",
                                     "openid-connect")
        expected = """
<IfDefine MyDefine>
    <Location /some-jupyter-url>
        # Pass SSL variables on
        SSLOptions +StdEnvVars
        AuthType openid-connect
        require valid-user
    </Location>
</IfDefine>
"""
        self.assertEqual(filled, expected)

    def test_jupyter_gen_openid_template_invalid_url_type(self):
        rejected = False
        try:
            filled = gen_openid_template(None, "MyDefine",
                                         "no-such-auth-type")
        except AssertionError as err:
            rejected = True
        self.assertTrue(rejected)

    def test_jupyter_gen_openid_template_invalid_define_type(self):
        rejected = False
        try:
            filled = gen_openid_template("/some-jupyter-url", None,
                                         "no-such-auth-type")
        except AssertionError as err:
            rejected = True
        self.assertTrue(rejected)

    def test_jupyter_gen_openid_template_invalid_auth_type(self):
        rejected = False
        try:
            filled = gen_openid_template("/some-jupyter-url", "MyDefine",
                                         None)
        except AssertionError as err:
            rejected = True
        self.assertTrue(rejected)

    def test_jupyter_gen_openid_template_invalid_auth_val(self):
        rejected = False
        try:
            filled = gen_openid_template("/some-jupyter-url", "MyDefine",
                                         "no-such-auth-type")
        except AssertionError as err:
            rejected = True
        self.assertTrue(rejected)

    # TODO: add more coverage of module


if __name__ == '__main__':
    testmain()
