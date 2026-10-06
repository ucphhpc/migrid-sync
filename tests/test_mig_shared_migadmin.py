#
# --- BEGIN_HEADER ---
#
# test_mig_shared_migadmin - unit test of the corresponding mig shared module
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

"""Unit tests of the mig.shared.functionality.migadmin module"""

import os
import shutil
import tempfile
from typing import ContextManager, TextIO
from unittest.mock import patch

from mig.shared.functionality import migadmin
from mig.shared.httpsclient import generic_id_field
from mig.shared.output import html_format
from tests.support import MigTestCase
from tests.support.configsupp import write_configuration
from tests.support.snapshotsupp import SnapshotAssertMixin
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin


class TestMain(MigTestCase, UserAssertMixin, SnapshotAssertMixin):
    """Test the main function of the migadmin module."""

    config_file: tempfile.NamedTemporaryFile
    tempdir: str

    def __init__(self, *args) -> None:
        super().__init__(*args)

    def _provide_configuration(self) -> str:
        return "testconfig"

    def before_each(self) -> None:
        self.tempdir = tempfile.mkdtemp(prefix=self.id().replace(".", "_"))
        self.configuration.site_enable_migadmin = True
        self.configuration.migadmin_view_access = "ANY"
        self.configuration.migadmin_act_access = "ANY"
        self.configuration.logfile = "/tmp/mig.log"
        self.config_file = tempfile.NamedTemporaryFile(
            dir=self.tempdir,
            prefix="MigServer",
            suffix=".conf",
            mode="w+t",
            delete=False,
        )

    def after_each(self) -> None:
        shutil.rmtree(self.tempdir)

    def write_config_and_patch_environ(self) -> ContextManager:
        """
        Writes the configuration file, and patches `os.environ` with
        the location, along with other required values.
        """

        write_configuration(self.configuration, self.config_file)
        self.config_file.close()

        environ = {
            "MIG_CONF": self.config_file.name,
            "SCRIPT_URI": "https://test.url",
            generic_id_field: "https://openidv2.domain",
        }
        return patch("os.environ", environ)

    def test_snapshot_is_not_admin(self) -> None:
        self._provision_test_user(self, TEST_USER_DN)
        self.configuration.admin_list = []  # user is not admin

        with self.write_config_and_patch_environ():
            outobjs, retval = migadmin.main(TEST_USER_DN, {})
            output = html_format(self.configuration, retval, "", outobjs)

        self.assertSnapshotOfHtmlContent(output)

    def test_snapshot_is_admin(self):
        self._provision_test_user(self, TEST_USER_DN)
        self.configuration.admin_list = [TEST_USER_DN]

        with self.write_config_and_patch_environ():
            outobjs, retval = migadmin.main(TEST_USER_DN, {})
            output = html_format(self.configuration, retval, "", outobjs)

        self.assertSnapshotOfHtmlContent(output)
