# from mig.shared.base import distinguished_name_to_user
import os
import shutil
import tempfile
from typing import TextIO
from unittest.mock import patch

from mig.shared.functionality import migadmin
from mig.shared.httpsclient import generic_id_field
from mig.shared.output import html_format
from tests.support import MigTestCase
from tests.support.configsupp import write_configuration
from tests.support.snapshotsupp import SnapshotAssertMixin
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin


class TestMain(MigTestCase, UserAssertMixin, SnapshotAssertMixin):
    _config_file: TextIO
    config_path: str
    tempdir: str

    def __init__(self, *args) -> None:
        super().__init__(*args)

    def _provide_configuration(self) -> str:
        return "testconfig"

    def write_configuration(self) -> None:
        with self._config_file as f:
            write_configuration(self.configuration, f)
        f.close()

    def before_each(self) -> None:
        self.tempdir = tempfile.mkdtemp(prefix=self.id().replace(".", "_"))
        self._configuration = None  # TODO: fix hack to reset to default conf
        self.configuration.site_enable_migadmin = True
        self.configuration.migadmin_view_access = "ANY"
        self.configuration.migadmin_act_access = "ANY"
        self.configuration.logfile = "/tmp/mig.log"
        conf_fd, self.config_path = tempfile.mkstemp(
            dir=self.tempdir, prefix="MigServer", suffix=".conf", text=True
        )
        self._config_file = os.fdopen(conf_fd, mode="w+")

    def after_each(self) -> None:
        shutil.rmtree(self.tempdir)

    def test_snapshot_is_not_admin(self) -> None:
        self._provision_test_user(self, TEST_USER_DN)
        self.configuration.admin_list = []  # user is not admin
        self.write_configuration()
        environ = {
            "MIG_CONF": self.config_path,
            "SCRIPT_URI": "https://test.url",
            generic_id_field: "https://openidv2.domain",
        }

        with patch("os.environ", environ):
            outobjs, retval = migadmin.main(TEST_USER_DN, {})
            output = html_format(self.configuration, retval, "", outobjs)

        self.assertSnapshotOfHtmlContent(output)

    def test_snapshot_is_admin(self):
        self._provision_test_user(self, TEST_USER_DN)
        self.configuration.admin_list = [TEST_USER_DN]
        self.write_configuration()
        environ = {
            "MIG_CONF": self.config_path,
            "SCRIPT_URI": "https://test.url",
            generic_id_field: "https://openidv2.domain",
        }

        with patch("os.environ", environ):
            outobjs, retval = migadmin.main(TEST_USER_DN, {})
            output = html_format(self.configuration, retval, "", outobjs)

        self.assertSnapshotOfHtmlContent(output)
