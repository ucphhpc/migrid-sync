# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_cmdapi - unit tests for cmdapi helper functions
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# -- END_HEADER ---
#

"""Unit tests for cmdapi helper module"""

import unittest

# Imports of the code under test
from mig.shared.cmdapi import (
    get_command_map,
    get_flag_map,
    get_usage_map,
    legacy_main,
    map_args_to_vars,
    parse_command_args,
)

# Imports required for the unit tests themselves
from tests.support import MigTestCase, ensure_dirs_exist, testmain

# Imports required for the unit test wrapping


class TestMigSharedCmdapi(MigTestCase):
    """Unit tests for cmdapi helpers"""

    def _provide_configuration(self):
        """Return configuration to use"""
        return "testconfig"

    def before_each(self):
        """Create test environment for cmdapi tests"""
        ensure_dirs_exist(self.configuration.mig_system_files)

    def test_get_command_map_basic(self):
        """Test basic command map structure"""
        command_map = get_command_map(self.configuration)
        self.assertIsInstance(command_map, dict)
        self.assertIn("cp", command_map)
        self.assertIn("mv", command_map)
        self.assertIn("rm", command_map)
        self.assertIn("mkdir", command_map)
        self.assertIn("du", command_map)

    def test_get_command_map_with_jobs_enabled(self):
        """Test command map includes job commands when enabled"""
        self.configuration.site_enable_jobs = True
        command_map = get_command_map(self.configuration)
        self.assertIn("submit", command_map)
        self.assertIn("canceljob", command_map)
        self.assertIn("resubmit", command_map)
        self.assertIn("jobaction", command_map)
        self.assertIn("liveio", command_map)

    def test_get_command_map_with_sharelinks_enabled(self):
        """Test command map includes sharelink commands when enabled"""
        self.configuration.site_enable_sharelinks = True
        command_map = get_command_map(self.configuration)
        self.assertIn("delsharelink", command_map)
        self.assertIn("importsharelink", command_map)

    def test_get_command_map_with_transfers_enabled(self):
        """Test command map includes transfer commands when enabled"""
        self.configuration.site_enable_transfers = True
        command_map = get_command_map(self.configuration)
        self.assertIn("datatransfer", command_map)

    def test_get_command_map_with_freeze_enabled(self):
        """Test command map includes freeze commands when enabled"""
        self.configuration.site_enable_freeze = True
        command_map = get_command_map(self.configuration)
        self.assertIn("createbackup", command_map)
        self.assertIn("deletebackup", command_map)
        self.assertIn("addfreezedata", command_map)
        self.assertIn("importfreeze", command_map)

    def test_get_command_map_with_crontab_enabled(self):
        """Test command map includes crontab commands when enabled"""
        self.configuration.site_enable_crontab = True
        command_map = get_command_map(self.configuration)
        self.assertIn("crontab", command_map)

    def test_get_command_map(self):
        """Test that get_command_map returns expected command definitions"""
        cmd_map = get_command_map(self.configuration)
        # Only a subset is relevant for basic tests
        expected_subset = {
            "pack": ["src", "dst"],
            "unpack": ["src", "dst"],
            "zip": ["src", "dst"],
            "unzip": ["src", "dst"],
            "tar": ["src", "dst"],
            "untar": ["src", "dst"],
            "cp": ["src", "dst"],
            "mv": ["src", "dst"],
            "rm": ["path"],
            "du": ["path", "dst"],
            "rmdir": ["path"],
            "truncate": ["path"],
            "touch": ["path"],
            "mkdir": ["path"],
            "chksum": ["hash_algo", "path", "dst", "max_chunks"],
            "mqueue": ["queue", "action", "msg_id", "msg"],
        }
        for cmd, args in expected_subset.items():
            self.assertIn(cmd, cmd_map)
            self.assertEqual(cmd_map[cmd][: len(args)], args)

    def test_get_flag_map_structure(self):
        """Test flag map structure"""
        flag_map = get_flag_map(self.configuration)
        self.assertIsInstance(flag_map, dict)
        self.assertIn("cp", flag_map)
        self.assertIn("rm", flag_map)
        self.assertIn("du", flag_map)
        self.assertIn("mkdir", flag_map)
        self.assertIn("rmdir", flag_map)

    def test_get_flag_map_values(self):
        """Test flag map values"""
        flag_map = get_flag_map(self.configuration)
        self.assertEqual(flag_map["cp"], ["r", "f"])
        self.assertEqual(flag_map["rm"], ["r", "f"])
        self.assertEqual(flag_map["du"], ["s"])
        self.assertEqual(flag_map["mkdir"], ["p"])
        self.assertEqual(flag_map["rmdir"], ["p"])

    def test_get_flag_map(self):
        """Test that get_flag_map returns expected flag definitions"""
        flags = get_flag_map(self.configuration)
        expected = {
            "cp": ["r", "f"],
            "rm": ["r", "f"],
            "du": ["s"],
            "mkdir": ["p"],
            "rmdir": ["p"],
            "importsharelink": ["r", "f"],
            "importfreeze": ["r", "f"],
        }
        self.assertEqual(flags, expected)

    def test_get_usage_map_structure(self):
        """Test usage map structure"""
        usage_map = get_usage_map(self.configuration)
        self.assertIsInstance(usage_map, dict)
        self.assertIn("cp", usage_map)
        self.assertIn("mv", usage_map)
        self.assertIn("rm", usage_map)
        self.assertIn("mkdir", usage_map)
        self.assertIn("du", usage_map)

    def test_get_usage_map_values(self):
        """Test usage map values"""
        usage_map = get_usage_map(self.configuration)
        self.assertEqual(usage_map["cp"], "cp [-r] [-f] SRC [SRC ..] DST")
        self.assertEqual(usage_map["mv"], "mv  SRC [SRC ..] DST")
        self.assertEqual(usage_map["rm"], "rm [-r] [-f] PATH [PATH ..]")
        self.assertEqual(usage_map["mkdir"], "mkdir [-p] PATH [PATH ..]")
        self.assertEqual(usage_map["du"], "du [-s] PATH [PATH ..] DST")

    def test_get_usage_map(self):
        """Test that get_usage_map builds usage strings correctly"""
        usage = get_usage_map(self.configuration)
        # Check a known command
        self.assertIn("cp", usage)
        self.assertIn("[-r]", usage["cp"])
        self.assertIn("SRC [SRC ..] DST", usage["cp"])

    def test_map_args_to_vars_variable_length(self):
        """Test that map_args_to_vars expands variable length arguments"""
        var_list = ["src", "dst"]
        arg_list = ["a.txt", "b.txt", "c.txt"]
        result = map_args_to_vars(var_list, arg_list)
        self.assertEqual(result, {"src": ["a.txt", "b.txt"], "dst": ["c.txt"]})

    def test_map_args_to_vars_exact_match(self):
        """Test map_args_to_vars with exact number of arguments"""
        var_list = ["src", "dst"]
        arg_list = ["a.txt", "b.txt"]
        result = map_args_to_vars(var_list, arg_list)
        self.assertEqual(result, {"src": ["a.txt"], "dst": ["b.txt"]})

    def test_parse_command_args_basic(self):
        """Test that parse_command_args parses a simple command correctly"""
        cmd_list = ["cp", "srcfile", "dstfile"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "cp")
        self.assertEqual(args_dict.get("src"), ["srcfile"])
        self.assertEqual(args_dict.get("dst"), ["dstfile"])

    def test_parse_command_args_with_flags(self):
        """Test that parse_command_args handles flags correctly"""
        cmd_list = ["cp", "-r", "srcdir", "dstdir"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "cp")
        self.assertIn("flags", args_dict)
        self.assertEqual(args_dict["flags"], ["r"])

    def test_parse_command_args_with_multiple_flags(self):
        """Test that parse_command_args handles multiple combined flags"""
        cmd_list = ["cp", "-rf", "srcdir", "dstdir"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "cp")
        self.assertIn("flags", args_dict)
        self.assertEqual(args_dict["flags"], ["rf"])

    def test_parse_command_args_unsupported(self):
        """Test that parse_command_args raises on unsupported command"""
        cmd_list = ["unknown_cmd", "arg1"]
        with self.assertRaises(ValueError) as cm:
            parse_command_args(self.configuration, cmd_list)
        self.assertIn("unsupported command", str(cm.exception))

    def test_parse_command_args_delsharelink_no_flags_entry(self):
        """Regression: ensure commands without flags don't produce flags key"""
        self.configuration.site_enable_sharelinks = True
        cmd_list = ["delsharelink", "share123"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "delsharelink")
        self.assertNotIn("flags", args_dict)
        self.assertEqual(args_dict.get("share_id"), ["share123"])

    def test_parse_command_args_canceljob_no_flags_entry(self):
        """Regression: ensure commands without flags don't produce flags key"""
        self.configuration.site_enable_jobs = True
        cmd_list = ["canceljob", "job123"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "canceljob")
        self.assertNotIn("flags", args_dict)
        self.assertEqual(args_dict.get("job_id"), ["job123"])

    def test_parse_command_args_datatransfer_no_flags_entry(self):
        """Regression: ensure commands without flags don't produce flags key"""
        self.configuration.site_enable_transfers = True
        cmd_list = ["datatransfer", "transfer123"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "datatransfer")
        self.assertNotIn("flags", args_dict)
        self.assertEqual(args_dict.get("transfer_id"), ["transfer123"])

    def test_parse_command_args_deletebackup_no_flags_entry(self):
        """Regression: ensure commands without flags don't produce flags key"""
        self.configuration.site_enable_freeze = True
        cmd_list = ["deletebackup", "backup123"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "deletebackup")
        self.assertNotIn("flags", args_dict)
        self.assertEqual(args_dict.get("freeze_id"), ["backup123"])

    def test_parse_command_args_crontab_no_flags_entry(self):
        """Regression: ensure commands without flags don't produce flags key"""
        self.configuration.site_enable_crontab = True
        cmd_list = ["crontab", "transfer123", "reschedule"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "crontab")
        self.assertNotIn("flags", args_dict)
        self.assertEqual(args_dict.get("action"), ["reschedule"])

    def test_parse_command_args_mqueue_no_flags_entry(self):
        """Regression: ensure commands without flags don't produce flags key"""
        self.configuration.site_enable_jobs = True
        cmd_list = ["mqueue", "testqueue", "msgaction", "msgid", "test msg"]
        backend, args_dict = parse_command_args(self.configuration, cmd_list)
        self.assertEqual(backend, "mqueue")
        self.assertNotIn("flags", args_dict)
        self.assertEqual(args_dict.get("queue"), ["testqueue"])
        self.assertEqual(args_dict.get("msg"), ["test msg"])


class TestMigSharedCmdapi__legacy_main(MigTestCase):
    """Unit tests for legacy cmdapi self-checks"""

    def test_existing_main(self):
        """Run the legacy self-tests directly in module"""

        def raise_on_error_exit(exit_code):
            if exit_code != 0:
                if raise_on_error_exit.last_print is not None:
                    identifying_message = raise_on_error_exit.last_print
                else:
                    identifying_message = "unknown"
                raise AssertionError(
                    "failure in unittest/testcore: %s" % (identifying_message,)
                )

        raise_on_error_exit.last_print = None

        def record_last_print(value):
            """Keep track of printed output"""
            raise_on_error_exit.last_print = value

        legacy_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == "__main__":
    testmain()
