# from mig.shared.base import distinguished_name_to_user
from mig.shared.functionality import migadmin
from mig.shared.httpsclient import generic_id_field
from mig.shared.output import html_format
from tests.support import MigTestCase
from tests.support.snapshotsupp import SnapshotAssertMixin
from tests.support.usersupp import TEST_USER_DN, UserAssertMixin


class TestMigAdmin(MigTestCase, UserAssertMixin, SnapshotAssertMixin):

    def _provide_configuration(self):
        """Return configuration to use"""
        return "testconfig"

    def test_main_snapshot(self):
        self._provision_test_user(self, TEST_USER_DN)
        self.configuration.admin_list = [TEST_USER_DN]
        self.configuration.site_enable_migadmin = True
        self.configuration.migadmin_view_access = "ANY"
        self.configuration.migadmin_act_access = "ANY"
        environ = {
            "SCRIPT_URI": "https://test.url",
            generic_id_field: "https://openidv2.domain"
        }

        outobjs, retval = migadmin.main(TEST_USER_DN, {}, environ=environ)
        output = html_format(self.configuration, retval, "", outobjs)

        self.assertSnapshotOfHtmlContent(output)


if __name__ == "__main__":
    TestMigAdmin.run()