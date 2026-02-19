# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_events - unit tests for events/cron helper functions
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

"""Unit tests for shared events helper functions"""

import datetime
import os
import shutil
import time
import unittest

from mig.lib.events import _restore_env, _save_env, at_remain, cron_match, \
    get_path_expand_map, get_time_expand_map, load_atjobs, load_crontab
from mig.lib.events import main as events_main
from mig.lib.events import parse_and_save_atjobs, parse_and_save_crontab, \
    parse_atjobs, parse_atjobs_contents, parse_crontab, \
    parse_crontab_contents, run_cron_command, run_events_command
from mig.shared.base import distinguished_name_to_user
from tests.support import MigTestCase, ensure_dirs_exist

DUMMY_USER_DN = "/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com"
DUMMY_FULL_NAME = "Test User"
DUMMY_ORGANIZATION = "Test Org"
DUMMY_EMAIL = "test@example.com"
DUMMY_SKIP_EMAIL = ""
DUMMY_CLIENT_DIR = "+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@example.com"
DUMMY_CRON_JOB = {"command": ["touch", "test.txt"], "run_as": DUMMY_USER_DN}
DUMMY_CRONTAB_NAME = "crontab"
DUMMY_ATJOBS_NAME = "atjobs"
DUMMY_CRONTAB_CONTENT = """* * * * * /bin/test_command
30 2 * * * /usr/bin/another_command"""
DUMMY_ATJOBS_CONTENT = """2042-01-01 12:34:56 /bin/future_command"""
MUST_PRESERVE_OS_ENV = ["MIG_CONF", "HOME", "USER", "PATH", "PWD"]
DUMMY_ENV = {"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"}


class MigLibEvents(MigTestCase):
    """Unit tests for events helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return "testconfig"

    def before_each(self):
        """Set up test configuration and reset state before each test"""
        # Enable events in configuration
        self.configuration.site_enable_crontab = True

        ensure_dirs_exist(self.configuration.user_db_home)
        ensure_dirs_exist(self.configuration.user_home)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.user_cache)
        ensure_dirs_exist(self.configuration.mig_system_files)

        # Prepare user DB with a single dummy user for all tests
        self._provision_test_user(self, DUMMY_USER_DN)

    def test_load_crontab(self):
        """Test loading crontab from file"""
        crontab_path = os.path.join(
            self.configuration.user_settings,
            DUMMY_CLIENT_DIR,
            DUMMY_CRONTAB_NAME,
        )
        ensure_dirs_exist(os.path.dirname(crontab_path))
        with open(crontab_path, "w") as fd:
            fd.write(DUMMY_CRONTAB_CONTENT)

        crontab = load_crontab(DUMMY_USER_DN, self.configuration)
        self.assertIn("* * * * * /bin/test_command", crontab)

    def test_load_atjobs(self):
        """Test loading atjobs from file"""
        atjobs_path = os.path.join(
            self.configuration.user_settings,
            DUMMY_CLIENT_DIR,
            DUMMY_ATJOBS_NAME,
        )
        ensure_dirs_exist(os.path.dirname(atjobs_path))
        with open(atjobs_path, "w") as fd:
            fd.write(DUMMY_ATJOBS_CONTENT)

        atjobs = load_atjobs(DUMMY_USER_DN, self.configuration)
        self.assertIn("2042-01-01 12:34:56 /bin/future_command", atjobs)

    def test_parse_crontab_contents(self):
        """Test parsing crontab content lines"""
        crontab_lines = DUMMY_CRONTAB_CONTENT.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["command"], ["/bin/test_command"])

    def test_parse_atjobs_contents(self):
        """Test parsing atjobs content lines"""
        atjobs_lines = DUMMY_ATJOBS_CONTENT.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/future_command"])

    def test_parse_and_save_crontab(self):
        """Test parsing and saving crontab"""
        crontab = DUMMY_CRONTAB_CONTENT
        status, msg = parse_and_save_crontab(
            crontab, DUMMY_USER_DN, self.configuration
        )
        self.assertTrue(status)
        self.assertIn("valid crontab entries", msg)

    def test_parse_and_save_atjobs(self):
        """Test parsing and saving atjobs"""
        atjobs = DUMMY_ATJOBS_CONTENT
        status, msg = parse_and_save_atjobs(
            atjobs, DUMMY_USER_DN, self.configuration
        )
        self.assertTrue(status)
        self.assertIn("valid atjobs entries", msg)

    def test_cron_match(self):
        """Test cron time matching"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*",
            "hour": "*",
            "dayofmonth": "*",
            "month": "*",
            "dayofweek": "*",
        }
        self.assertTrue(cron_match(self.configuration, now, test_job))

    def test_at_remain(self):
        """Test at job remaining time calculation"""
        now = datetime.datetime.now()
        future_time = now + datetime.timedelta(minutes=30)
        test_job = {"time_stamp": future_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, 30)

    def test_get_path_expand_map(self):
        """Test path expansion map generation"""
        trigger_path = "/test/path/file.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertIn("+TRIGGERPATH+", expanded)
        self.assertEqual(expanded["+TRIGGERPATH+"], trigger_path)

    def test_get_time_expand_map(self):
        """Test time expansion map generation"""
        timestamp = datetime.datetime(2023, 1, 2, 9, 2)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertIn("+SCHEDYEAR+", expanded)
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")

    def test_run_cron_command_touch_succeeds(self):
        """Test running cron command touch succeeds"""
        target_path = "test.txt"
        command_list = ["touch", target_path]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        abs_target_path = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, target_path
        )
        if os.path.exists(abs_target_path):
            os.remove(abs_target_path)
        self.assertFalse(os.path.exists(abs_target_path))

        try:
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
            self.assertTrue(os.path.exists(abs_target_path))
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command_touch_succeeds(self):
        """Test running events command touch succeeds"""
        target_path = "test.txt"
        command_list = ["touch", target_path]
        rule = {"run_as": DUMMY_USER_DN}
        abs_target_path = os.path.join(
            self.configuration.user_home, DUMMY_CLIENT_DIR, target_path
        )
        self.assertFalse(os.path.exists(abs_target_path))
        try:
            run_events_command(
                command_list, target_path, rule, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
            self.assertTrue(os.path.exists(abs_target_path))
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_save_env(self):
        """Test saving (custom) environment"""
        original_env = {}

        test_env = original_env.copy()
        test_env.update(DUMMY_ENV)
        # Save the test environment
        saved_env = _save_env(test_env)

        # Verify that the environment was saved correctly
        self.assertEqual(saved_env, test_env)
        self.assertEqual(saved_env, DUMMY_ENV)
        self.assertEqual(len(original_env), 0)

    def test_save_env_with_no_arguments(self):
        """Test saving (default) environment with no arguments"""
        original_env = os.environ.copy()

        # Removing certain essential os.environ breaks conf, etc.
        for name in os.environ:
            if name not in MUST_PRESERVE_OS_ENV:
                del os.environ[name]
        # Save the current default environment
        saved_env = _save_env()

        self.assertEqual(saved_env, os.environ)
        self.assertNotEqual(saved_env, original_env)
        self.assertTrue(len(saved_env) <= len(MUST_PRESERVE_OS_ENV))

        # Restore the original environment to prevent side effects
        _restore_env(saved_env)

    def test_restore_env(self):
        """Test restoring (custom) environment"""
        original_env = DUMMY_ENV.copy()

        test_env = original_env.copy()
        del test_env[list(original_env)[-1]]
        test_env["NEWKEY"] = "NEWVAL"
        self.assertNotEqual(test_env, original_env)

        # Restore the original environment
        restored_env = _restore_env(original_env, test_env)

        # Verify that the environment was restored correctly
        self.assertEqual(restored_env, original_env)
        self.assertEqual(restored_env, test_env)
        self.assertEqual(original_env, DUMMY_ENV)

    def test_restore_env_with_no_arguments(self):
        """Test restoring (default) environment with no arguments"""
        original_env = os.environ.copy()

        os.environ.update(DUMMY_ENV)

        # Restore the original environment without arguments
        restored_env = _restore_env(original_env)

        # Verify that the environment was restored correctly
        self.assertEqual(restored_env, original_env)
        self.assertEqual(os.environ, original_env)

    def test_save_and_restore_env_lifecycle(self):
        """Test saving and restoring (custom) environment"""
        original_env = {}

        test_env = original_env.copy()
        test_env.update(DUMMY_ENV)
        # Save the test environment
        saved_env = _save_env(test_env)

        # Verify that the environment was saved correctly
        self.assertEqual(saved_env, test_env)
        self.assertEqual(saved_env, DUMMY_ENV)
        self.assertEqual(len(original_env), 0)

        # Restore the original environment
        restored_env = _restore_env(original_env, test_env)

        # Verify that the environment was restored correctly
        self.assertEqual(restored_env, original_env)
        self.assertEqual(restored_env, test_env)
        self.assertEqual(len(original_env), 0)

    def test_save_and_restore_env_with_no_arguments_lifecycle(self):
        """Test saving and restoring (default) environment"""
        original_env = os.environ.copy()

        # Removing certain essential os.environ breaks conf, etc.
        for name in os.environ:
            if name not in MUST_PRESERVE_OS_ENV:
                del os.environ[name]
        # Save the current default environment
        saved_env = _save_env()

        self.assertEqual(saved_env, os.environ)
        self.assertNotEqual(saved_env, original_env)
        self.assertTrue(len(saved_env) <= len(MUST_PRESERVE_OS_ENV))

        # Restore the original environment
        restored_env = _restore_env(original_env)

        # Verify that the default environment was restored correctly
        self.assertEqual(restored_env, original_env)
        self.assertEqual(original_env, os.environ)

    def test_parse_valid_crontab_file(self):
        """Test parsing valid crontab file"""
        crontab_path = os.path.join(
            self.configuration.user_settings,
            DUMMY_CLIENT_DIR,
            DUMMY_CRONTAB_NAME,
        )
        ensure_dirs_exist(os.path.dirname(crontab_path))
        with open(crontab_path, "w") as fd:
            fd.write(DUMMY_CRONTAB_CONTENT)

        parsed = parse_crontab(self.configuration, DUMMY_USER_DN, crontab_path)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["command"], ["/bin/test_command"])

    def test_parse_empty_crontab_file(self):
        """Test parsing empty crontab file"""
        crontab_path = os.path.join(
            self.configuration.user_settings,
            DUMMY_CLIENT_DIR,
            DUMMY_CRONTAB_NAME,
        )
        ensure_dirs_exist(os.path.dirname(crontab_path))
        open(crontab_path, "a").close()  # Create empty file

        parsed = parse_crontab(self.configuration, DUMMY_USER_DN, crontab_path)
        self.assertEqual(parsed, [])

    def test_parse_valid_atjobs_file(self):
        """Test parsing valid atjobs file"""
        atjobs_path = os.path.join(
            self.configuration.user_settings,
            DUMMY_CLIENT_DIR,
            DUMMY_ATJOBS_NAME,
        )
        ensure_dirs_exist(os.path.dirname(atjobs_path))
        with open(atjobs_path, "w") as fd:
            fd.write(DUMMY_ATJOBS_CONTENT)

        parsed = parse_atjobs(self.configuration, DUMMY_USER_DN, atjobs_path)
        self.assertEqual(len(parsed), 1)
        self.assertTrue(parsed[0]["time_stamp"] > datetime.datetime.now())

    def test_parse_empty_atjobs_file(self):
        """Test parsing empty atjobs file"""
        atjobs_path = os.path.join(
            self.configuration.user_settings,
            DUMMY_CLIENT_DIR,
            DUMMY_ATJOBS_NAME,
        )
        ensure_dirs_exist(os.path.dirname(atjobs_path))
        open(atjobs_path, "a").close()  # Create empty file

        parsed = parse_atjobs(self.configuration, DUMMY_USER_DN, atjobs_path)
        self.assertEqual(parsed, [])

    def test_cron_match_current_minute(self):
        """Test cron_match identifies current time match"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*",
            "hour": "*",
            "day": "*",
            "month": "*",
            "dayofweek": "*",
            "dayofmonth": "*",
        }
        self.assertTrue(cron_match(self.configuration, now, test_job))

    def test_cron_match_specific_time(self):
        """Test cron_match rejects non-matching time"""
        now = datetime.datetime.now().replace(
            hour=3, minute=15, second=0, microsecond=0
        )
        test_job = {
            "minute": "30",
            "hour": "2",
            "dayofmonth": "*",
            "month": "*",
            "dayofweek": "*",
        }
        self.assertFalse(cron_match(self.configuration, now, test_job))

    def test_at_remain_past_job(self):
        """Test at_remain with past job"""
        now = datetime.datetime.now()
        past_time = now - datetime.timedelta(minutes=30)
        test_job = {"time_stamp": past_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, -30)

    def test_get_path_expand_map_with_spaces(self):
        """Test path expansion with spaces"""
        trigger_path = "/test/path/file with spaces.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertIn("+TRIGGERFILENAME+", expanded)
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "file with spaces.txt")

    def test_get_time_expand_map_edge_cases(self):
        """Test time expansion with edge cases"""
        timestamp = datetime.datetime(2023, 12, 31, 23, 59)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "31")
        self.assertEqual(expanded["+SCHEDMONTH+"], "12")
        self.assertEqual(expanded["+SCHEDHOUR+"], "23")
        self.assertEqual(expanded["+SCHEDMINUTE+"], "59")

    def test_run_cron_command_with_invalid_command(self):
        """Test running cron command with invalid command"""
        target_path = "test.txt"
        command_list = ["invalid_command", target_path]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_invalid_command(self):
        """Test running events command with invalid command"""
        command_list = ["invalid_command", "test"]
        target_path = "/test/path"
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_cron_match_edge_cases(self):
        """Test cron_match with edge case times"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_cases = [
            (
                {
                    "minute": "0",
                    "hour": "0",
                    "dayofmonth": "1",
                    "month": "1",
                    "dayofweek": "0",
                },
                now.replace(hour=0, minute=0, day=1, month=1),
            ),
            (
                {
                    "minute": "59",
                    "hour": "23",
                    "dayofmonth": "31",
                    "month": "12",
                    "dayofweek": "6",
                },
                now.replace(hour=23, minute=59, day=31, month=12),
            ),
        ]
        for job, match_time in test_cases:
            self.assertEqual(
                cron_match(self.configuration, match_time, job),
                match_time == now,
            )

    def test_at_remain_edge_cases(self):
        """Test at_remain with edge case times"""
        now = datetime.datetime.now()
        test_cases = [
            (now + datetime.timedelta(seconds=30), 0),  # Less than 1 minute
            # 1 minute 30 seconds
            (now + datetime.timedelta(minutes=1, seconds=30), 1),
            (now + datetime.timedelta(hours=1), 60),  # 1 hour
            (now + datetime.timedelta(days=1), 1440),  # 1 day
        ]
        for future_time, expected_minutes in test_cases:
            test_job = {"time_stamp": future_time}
            remaining = at_remain(self.configuration, now, test_job)
            self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_empty_path(self):
        """Test path expansion with empty path"""
        trigger_path = ""
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        with self.assertRaises(ValueError):
            expanded = get_path_expand_map(trigger_path, rule, "modified")

    def test_get_time_expand_map_leap_year(self):
        """Test time expansion with leap year"""
        timestamp = datetime.datetime(2024, 2, 29, 12, 0)  # Leap day
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "29")
        self.assertEqual(expanded["+SCHEDMONTH+"], "02")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2024")

    def test_run_cron_command_with_spaces(self):
        """Test running cron command with spaces"""
        target_path = "test file with spaces.txt"
        command_list = ["touch", target_path]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        try:
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_cron_command_with_special_chars(self):
        """Test running cron command with special characters"""
        target_path = "/test/path/file@name#with$special&chars.txt"
        command_list = ["touch", target_path]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        # NOTE: touch fails without log in input validation
        with self.assertRaises(Exception):
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )

    def test_run_events_command_with_spaces(self):
        """Test running events command with spaces"""
        target_path = "test file with spaces.txt"
        command_list = ["touch", target_path]
        rule = {"run_as": DUMMY_USER_DN}
        try:
            run_events_command(
                command_list, target_path, rule, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_run_events_command_with_special_chars(self):
        """Test running events command with special characters"""
        target_path = "/test/path/file@name#with$special&chars.txt"
        command_list = ["touch", target_path]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "found invalid character" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_comments(self):
        """Test parsing crontab with comments"""
        crontab_content = """# This is a comment
* * * * * /bin/test_command
# Another comment
30 2 * * * /usr/bin/another_command"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["command"], ["/bin/test_command"])

    def test_parse_atjobs_with_comments(self):
        """Test parsing atjobs with comments"""
        atjobs_content = """# This is a comment
2042-01-01 12:34:56 /bin/future_command
# Another comment"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/future_command"])

    def test_cron_match_with_wildcards(self):
        """Test cron_match with various wildcard combinations"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_cases = [
            (
                {
                    "minute": "*",
                    "hour": "*",
                    "dayofmonth": "*",
                    "month": "*",
                    "dayofweek": "*",
                },
                True,
            ),
            (
                {
                    "minute": "15",
                    "hour": "*",
                    "dayofmonth": "*",
                    "month": "*",
                    "dayofweek": "*",
                },
                now.minute == 15,
            ),
            (
                {
                    "minute": "*",
                    "hour": "3",
                    "dayofmonth": "*",
                    "month": "*",
                    "dayofweek": "*",
                },
                now.hour == 3,
            ),
            (
                {
                    "minute": "*",
                    "hour": "*",
                    "dayofmonth": "15",
                    "month": "*",
                    "dayofweek": "*",
                },
                now.day == 15,
            ),
            (
                {
                    "minute": "*",
                    "hour": "*",
                    "dayofmonth": "*",
                    "month": "6",
                    "dayofweek": "*",
                },
                now.month == 6,
            ),
            (
                {
                    "minute": "*",
                    "hour": "*",
                    "dayofmonth": "*",
                    "month": "*",
                    "dayofweek": "0",
                },
                now.weekday() == 0,
            ),
        ]
        for job, expected in test_cases:
            self.assertEqual(cron_match(self.configuration, now, job), expected)

    @unittest.skip("enable next if ever relevant - fails with TypeError")
    def test_at_remain_with_timezones(self):
        """Test at_remain with different timezones"""
        now = datetime.datetime.now()
        test_cases = [
            (
                now.astimezone(datetime.timezone.utc)
                + datetime.timedelta(minutes=30),
                30,
            ),
            (
                now.astimezone(datetime.timezone.utc)
                - datetime.timedelta(minutes=30),
                -30,
            ),
        ]
        for future_time, expected_minutes in test_cases:
            test_job = {"time_stamp": future_time}
            remaining = at_remain(self.configuration, now, test_job)
            self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_with_relative_path(self):
        """Test path expansion with relative path"""
        trigger_path = "../relative/path/file.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(expanded["+TRIGGERPATH+"], "../relative/path/file.txt")
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "file.txt")
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "file")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt")

    def test_get_time_expand_map_with_milliseconds(self):
        """Test time expansion with milliseconds"""
        timestamp = datetime.datetime(2023, 1, 2, 9, 2, 30, 123456)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDSECOND+"], "30")
        self.assertEqual(expanded["+SCHEDMINUTE+"], "02")
        self.assertEqual(expanded["+SCHEDHOUR+"], "09")
        self.assertEqual(expanded["+SCHEDDAY+"], "02")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")
        self.assertEqual(expanded["+SCHEDDAYOFWEEK+"], "0")

    def test_run_cron_command_with_long_command(self):
        """Test running cron command with long command"""
        target_path = "test.txt"
        long_command = ["touch"] + ["arg"] * 100
        command_list = long_command
        crontab_entry = {"run_as": DUMMY_USER_DN}
        try:
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command_with_long_command(self):
        """Test running events command with long command"""
        target_path = "test.txt"
        long_command = ["touch"] + ["arg"] * 100
        command_list = long_command
        rule = {"run_as": DUMMY_USER_DN}
        try:
            run_events_command(
                command_list, target_path, rule, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_parse_crontab_with_invalid_lines(self):
        """Test parsing crontab with invalid lines"""
        crontab_content = """* * * * * /bin/test_command
invalid line
30 2 * * * /usr/bin/another_command"""
        crontab_lines = crontab_content.splitlines()
        with self.assertLogs(level="WARNING") as log_capture:
            parsed = parse_crontab_contents(
                self.configuration, DUMMY_USER_DN, crontab_lines
            )
            self.assertEqual(len(parsed), 2)
            self.assertTrue(
                any(
                    "Skip invalid crontab line" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_atjobs_with_invalid_lines(self):
        """Test parsing atjobs with invalid lines"""
        atjobs_content = """2042-01-01 12:34:56 /bin/future_command
invalid line
2042-01-02 12:34:56 /bin/another_command"""
        atjobs_lines = atjobs_content.splitlines()
        with self.assertLogs(level="WARNING") as log_capture:
            parsed = parse_atjobs_contents(
                self.configuration, DUMMY_USER_DN, atjobs_lines
            )
            self.assertEqual(len(parsed), 2)
            self.assertTrue(
                any(
                    "Skip invalid atjobs line" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_empty_lines(self):
        """Test parsing crontab with empty lines"""
        crontab_content = """* * * * * /bin/test_command

30 2 * * * /usr/bin/another_command
"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["command"], ["/bin/test_command"])

    def test_parse_atjobs_with_empty_lines(self):
        """Test parsing atjobs with empty lines"""
        atjobs_content = """2042-01-01 12:34:56 /bin/future_command

2042-01-02 12:34:56 /bin/another_command
"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["command"], ["/bin/future_command"])

    def test_cron_match_with_single_digit_values(self):
        """Test cron_match with single digit values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_cases = [
            (
                {
                    "minute": "5",
                    "hour": "3",
                    "dayofmonth": "7",
                    "month": "6",
                    "dayofweek": "1",
                },
                now.replace(minute=5, hour=3, day=7, month=6),
            ),
            (
                {
                    "minute": "0",
                    "hour": "0",
                    "dayofmonth": "1",
                    "month": "1",
                    "dayofweek": "0",
                },
                now.replace(minute=0, hour=0, day=1, month=1),
            ),
        ]
        for job, match_time in test_cases:
            self.assertEqual(
                cron_match(self.configuration, match_time, job),
                match_time == now,
            )

    def test_at_remain_with_same_minute_but_earlier(self):
        """Test at_remain with same minute but a few seconds earlier"""
        now = datetime.datetime.now()
        now = now.replace(second=30)
        same_minute_time = now.replace(second=42)
        test_job = {"time_stamp": same_minute_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, 0)

    def test_at_remain_with_same_minute_but_later(self):
        """Test at_remain with same minute but a few seconds later"""
        now = datetime.datetime.now()
        now = now.replace(second=30)
        same_minute_time = now.replace(second=22)
        test_job = {"time_stamp": same_minute_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, -1)

    def test_at_remain_with_same_minute_exactly(self):
        """Test at_remain with same minute exactly"""
        now = datetime.datetime.now()
        now = now.replace(second=30)
        same_minute_time = now
        test_job = {"time_stamp": same_minute_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, 0)

    def test_get_path_expand_map_with_no_extension(self):
        """Test path expansion with no extension"""
        trigger_path = "/test/path/file"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "file")
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "file")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], "")

    def test_get_time_expand_map_with_first_day(self):
        """Test time expansion with first day of month"""
        timestamp = datetime.datetime(2023, 1, 1, 0, 0)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")

    def test_run_cron_command_with_no_arguments(self):
        """Test running cron command with no arguments"""
        target_path = "dummy"
        command_list = ["touch"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        # NOTE: touch fails without log in input validation
        with self.assertRaises(Exception):
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )

    def test_run_events_command_with_no_arguments(self):
        """Test running events command with no arguments"""
        target_path = "dummy"
        command_list = ["touch"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any("path: is required" in msg for msg in log_capture.output)
            )

    def test_parse_crontab_with_trailing_whitespace(self):
        """Test parsing crontab with trailing whitespace"""
        crontab_content = """* * * * * /bin/test_command   \n"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/test_command"])

    def test_parse_atjobs_with_trailing_whitespace(self):
        """Test parsing atjobs with trailing whitespace"""
        atjobs_content = """2042-01-01 12:34:56 /bin/future_command   \n"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/future_command"])

    def test_cron_match_with_all_wildcards(self):
        """Test cron_match with all wildcards"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*",
            "hour": "*",
            "dayofmonth": "*",
            "month": "*",
            "dayofweek": "*",
        }
        self.assertTrue(cron_match(self.configuration, now, test_job))

    def test_at_remain_with_future_year(self):
        """Test at_remain with future year"""
        now = datetime.datetime.now()
        future_year = now.replace(
            year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0
        )
        test_job = {"time_stamp": future_year}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (future_year - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_with_leading_slash(self):
        """Test path expansion with leading slash"""
        trigger_path = "/file.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(expanded["+TRIGGERPATH+"], "/file.txt")
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "file.txt")
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "file")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt")

    def test_get_time_expand_map_with_last_day(self):
        """Test time expansion with last day of month"""
        timestamp = datetime.datetime(2023, 1, 31, 23, 59)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "31")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")

    def test_run_cron_command_with_output_redirection(self):
        """Test running cron command with output redirection"""
        target_path = "test.txt"
        command_list = ["touch", "test", ">", target_path]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        # NOTE: touch fails without log in input validation
        with self.assertRaises(Exception):
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )

    def test_run_events_command_with_output_redirection(self):
        """Test running events command with output redirection"""
        target_path = "test.txt"
        command_list = ["touch", "test", ">", target_path]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "found invalid character" in msg
                    for msg in log_capture.output
                )
            )

    @unittest.skip("enable next if we ever allow multispace")
    def test_parse_crontab_with_multiple_spaces(self):
        """Test parsing crontab with multiple spaces"""
        crontab_content = """*  *  *  *  *  /bin/test_command"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/test_command"])

    @unittest.skip("enable next if we ever allow multispace")
    def test_parse_atjobs_with_multiple_spaces(self):
        """Test parsing atjobs with multiple spaces"""
        atjobs_content = """2042-01-01  12:34:56  /bin/future_command"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/future_command"])

    # TODO: invert next when we implement feature at some point
    def test_cron_match_with_range_values(self):
        """Test cron_match with range values (not supported yet)"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "10-20",
            "hour": "2",
            "dayofmonth": "*",
            "month": "*",
            "dayofweek": "*",
        }
        # Should fail since ranges aren't supported, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_past_year(self):
        """Test at_remain with past year"""
        now = datetime.datetime.now()
        past_year = now.replace(year=now.year - 1)
        test_job = {"time_stamp": past_year}
        remaining = at_remain(self.configuration, now, test_job)
        # Approximately -1 year in minutes
        self.assertEqual(remaining, -525600)

    def test_at_remain_with_next_year(self):
        """Test at_remain with next year"""
        now = datetime.datetime.now()
        past_year = now.replace(year=now.year + 1)
        test_job = {"time_stamp": past_year}
        remaining = at_remain(self.configuration, now, test_job)
        # Approximately 1 year in minutes
        self.assertEqual(remaining, 525600)

    def test_get_path_expand_map_with_special_chars(self):
        """Test path expansion with special characters"""
        trigger_path = "/test/path/file@name#with$special&chars.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(
            expanded["+TRIGGERFILENAME+"], "file@name#with$special&chars.txt"
        )
        self.assertEqual(
            expanded["+TRIGGERPREFIX+"], "file@name#with$special&chars"
        )
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt")

    def test_get_time_expand_map_with_summer_time(self):
        """Test time expansion with summer time (DST)"""
        # This test may fail depending on the system's timezone and DST rules
        # Summer in Northern Hemisphere
        timestamp = datetime.datetime(2023, 7, 1, 12, 0)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "07")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")

    def test_run_cron_command_with_pipe(self):
        """Test running cron command with pipe"""
        target_path = "test.txt"
        command_list = ["touch", "test", "|", "grep", "test"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        # NOTE: touch fails without log in input validation
        with self.assertRaises(Exception):
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )

    def test_run_events_command_with_pipe(self):
        """Test running events command with pipe"""
        target_path = "test.txt"
        command_list = ["touch", "test", "|", "grep", "test"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "found invalid character" in msg
                    for msg in log_capture.output
                )
            )

    @unittest.skip("enable next if we ever allow tab sep")
    def test_parse_crontab_with_tab_separated(self):
        """Test parsing crontab with tab-separated values"""
        crontab_content = "*\t*\t*\t*\t*\t/bin/test_command"
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/test_command"])

    @unittest.skip("enable next if we ever allow tab sep")
    def test_parse_atjobs_with_tab_separated(self):
        """Test parsing atjobs with tab-separated values"""
        atjobs_content = "2042-01-01\t12:34:56\t/bin/future_command"
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/future_command"])

    def test_cron_match_with_step_values(self):
        """Test cron_match with step values (not supported but should handle)"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*/5",
            "hour": "2",
            "dayofmonth": "*",
            "month": "*",
            "dayofweek": "*",
        }
        # Should fail since steps aren't supported, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_leap_year(self):
        """Test at_remain with leap year"""
        now = datetime.datetime.now()
        leap_day = datetime.datetime(
            now.year + 4 - now.year // 4, 2, 29, 12, 0
        )  # Next leap year
        test_job = {"time_stamp": leap_day}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (leap_day - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_with_unicode(self):
        """Test path expansion with unicode characters"""
        trigger_path = "/test/path/файл.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "файл.txt")
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "файл")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt")

    def test_get_time_expand_map_with_dst_transition(self):
        """Test time expansion with DST transition"""
        # This test may fail depending on the system's timezone and DST rules
        timestamp = datetime.datetime(
            2023, 3, 12, 2, 30
        )  # DST transition in US
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "12")
        self.assertEqual(expanded["+SCHEDMONTH+"], "03")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")

    def test_run_cron_command_with_background(self):
        """Test running cron command with background execution"""
        target_path = "test.txt"
        command_list = ["touch", target_path, "&"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        # NOTE: touch succeeds treating ampersand as filename
        try:
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command_with_background(self):
        """Test running events command with background execution"""
        target_path = "test.txt"
        command_list = ["sleep", "1", "&"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_multiple_commands(self):
        """Test parsing crontab with multiple commands"""
        crontab_content = """* * * * * /bin/command1 && /bin/command2"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "&&", "/bin/command2"]
        )

    def test_parse_atjobs_with_multiple_commands(self):
        """Test parsing atjobs with multiple commands"""
        atjobs_content = (
            """2042-01-01 12:34:56 /bin/command1 && /bin/command2"""
        )
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "&&", "/bin/command2"]
        )

    @unittest.skip("implement value range check in function and enable next")
    def test_cron_match_with_invalid_values(self):
        """Test cron_match with invalid values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "60",
            "hour": "25",
            "dayofmonth": "32",
            "month": "13",
            "dayofweek": "7",
        }
        # Should fail since values are invalid, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_past_time(self):
        """Test at_remain with past time"""
        now = datetime.datetime.now()
        past_time = now - datetime.timedelta(minutes=5)
        test_job = {"time_stamp": past_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, -5)

    def test_get_path_expand_map_with_no_path(self):
        """Test path expansion with no path (just filename)"""
        trigger_path = "file.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(expanded["+TRIGGERPATH+"], "file.txt")
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "file.txt")
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "file")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt")

    def test_get_time_expand_map_with_zero_values(self):
        """Test time expansion with zero values"""
        timestamp = datetime.datetime(2023, 1, 1, 0, 0)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDSECOND+"], "00")
        self.assertEqual(expanded["+SCHEDMINUTE+"], "00")
        self.assertEqual(expanded["+SCHEDHOUR+"], "00")
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")
        self.assertEqual(expanded["+SCHEDDAYOFWEEK+"], "6")  # Sunday

    def test_run_cron_command_with_quotes(self):
        """Test running cron command with quotes"""
        target_path = "test.txt"
        command_list = ["touch", '"test with spaces"']
        crontab_entry = {"run_as": DUMMY_USER_DN}
        # NOTE: touch fails without log in input validation
        with self.assertRaises(Exception):
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )

    def test_run_events_command_with_quotes(self):
        """Test running events command with quotes"""
        target_path = "test.txt"
        command_list = ["touch", '"test with spaces"']
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
        self.assertTrue(
            any("found invalid character" in msg for msg in log_capture.output)
        )

    def test_parse_crontab_with_semicolon(self):
        """Test parsing crontab with semicolon"""
        crontab_content = """* * * * * /bin/command1; /bin/command2"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1;", "/bin/command2"]
        )

    def test_parse_atjobs_with_semicolon(self):
        """Test parsing atjobs with semicolon"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1; /bin/command2"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1;", "/bin/command2"]
        )

    # TODO: invert next when we implement feature at some point
    def test_cron_match_with_division_values(self):
        """Test cron_match with division values (not supported yet)"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*",
            "hour": "*",
            "dayofmonth": "*",
            "month": "*/1",
            "dayofweek": "*",
        }
        # Should fail since divide format is not yet allowed
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_future_time(self):
        """Test at_remain with future time"""
        now = datetime.datetime.now()
        future_time = now + datetime.timedelta(minutes=5)
        test_job = {"time_stamp": future_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, 5)

    def test_get_path_expand_map_with_windows_path(self):
        """Test path expansion with Windows path"""
        trigger_path = "C:\\path\\to\\file.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(expanded["+TRIGGERPATH+"], "C:\\path\\to\\file.txt")
        self.assertEqual(
            expanded["+TRIGGERFILENAME+"], "C:\\path\\to\\file.txt"
        )
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "C:\\path\\to\\file")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt")

    def test_get_time_expand_map_with_dst_start(self):
        """Test time expansion with DST start"""
        # This test may fail depending on the system's timezone and DST rules
        timestamp = datetime.datetime(2023, 3, 12, 3, 0)  # DST start in US
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "12")
        self.assertEqual(expanded["+SCHEDMONTH+"], "03")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")

    def test_run_cron_command_with_environment_variable(self):
        """Test running cron command with environment variable"""
        target_path = "test.txt"
        command_list = ["touch", "$HOME"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        try:
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command_with_environment_variable(self):
        """Test running events command with environment variable"""
        target_path = "test.txt"
        command_list = ["touch", "$HOME"]
        rule = {"run_as": DUMMY_USER_DN}
        try:
            run_events_command(
                command_list, target_path, rule, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_parse_crontab_with_backticks(self):
        """Test parsing crontab with backticks"""
        crontab_content = """* * * * * /bin/command1 `touch test`"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "`touch", "test`"]
        )

    def test_parse_atjobs_with_backticks(self):
        """Test parsing atjobs with backticks"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 `touch test`"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "`touch", "test`"]
        )

    @unittest.skip("implement extra value check in function and enable next")
    def test_cron_match_with_extra_fields(self):
        """Test cron_match with extra fields"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*",
            "hour": "*",
            "dayofmonth": "*",
            "month": "*",
            "dayofweek": "*",
            "extra_field": "value",
        }
        # Should fail since extra fields are present, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    # NOTE: no datetime support https://github.com/python/cpython/issues/67762
    @unittest.skip("enable if leap second handling is ever implemented")
    def test_at_remain_with_leap_second(self):
        """Test at_remain with leap second"""
        # December 31, 2016, had a leap second to include time 23:59:60
        now = datetime.datetime.now(datetime.timezone.utc)
        t_minus_sixty = now.replace(
            year=2016,
            month=12,
            day=31,
            hour=23,
            minute=59,
            second=0,
            microsecond=0,
        )
        leap_second = t_minus_sixty + datetime.timedelta(seconds=60)
        t_plus_sixty = now.replace(
            year=2017,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=59,
            microsecond=0,
        )
        self.assertEqual(
            (t_plus_sixty - t_minus_sixty).total_seconds(),
            120,
            "Leap second does not appear supported",
        )
        test_job = {"time_stamp": t_plus_sixty}
        remaining = at_remain(self.configuration, leap_second, test_job)
        # print("DEBUG: remaining now %s vs %s vs %s : %s" %
        #      (t_minus_sixty, leap_second, t_plus_sixty, remaining))
        self.assertEqual(remaining, 1)

    def test_get_path_expand_map_with_url(self):
        """Test path expansion with URL"""
        trigger_path = "http://example.com/file.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(
            expanded["+TRIGGERPATH+"], "http://example.com/file.txt"
        )
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "file.txt")
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "file")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt")

    def test_get_time_expand_map_with_new_year(self):
        """Test time expansion with New Year"""
        timestamp = datetime.datetime(2023, 1, 1, 0, 0)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2023")

    def test_parse_crontab_with_parentheses(self):
        """Test parsing crontab with parentheses"""
        crontab_content = """* * * * * /bin/command1 (arg1 arg2)"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "(arg1", "arg2)"]
        )

    def test_parse_atjobs_with_parentheses(self):
        """Test parsing atjobs with parentheses"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 (arg1 arg2)"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "(arg1", "arg2)"]
        )

    def test_cron_match_with_invalid_chars(self):
        """Test cron_match with invalid characters"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*",
            "hour": "*",
            "dayofmonth": "*",
            "month": "*",
            "dayofweek": "Sunday",
        }
        # Should fail since invalid characters are present, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_dst_end(self):
        """Test at_remain with DST end"""
        # This test may fail depending on the system's timezone and DST rules
        now = datetime.datetime.now()
        dst_end_time = now.replace(month=11, day=5, hour=1, minute=30)
        test_job = {"time_stamp": dst_end_time}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (dst_end_time - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_with_query_string(self):
        """Test path expansion with query string"""
        trigger_path = "/test/path/file.txt?param=value"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(
            expanded["+TRIGGERPATH+"], "/test/path/file.txt?param=value"
        )
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "file.txt?param=value")
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "file")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt?param=value")

    def test_get_time_expand_map_with_leap_year_start(self):
        """Test time expansion with leap year start"""
        timestamp = datetime.datetime(2024, 1, 1, 0, 0)  # Leap year
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2024")

    def test_run_cron_command_with_escaped_chars(self):
        """Test running cron command with escaped characters"""
        target_path = "test.txt"
        command_list = ["touch", "test\\ with\\ spaces"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        # NOTE: touch fails without log in input validation
        with self.assertRaises(Exception):
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )

    def test_run_events_command_with_escaped_chars(self):
        """Test running events command with escaped characters"""
        target_path = "test.txt"
        command_list = ["touch", "test\\ with\\ spaces"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "found invalid character" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_brackets(self):
        """Test parsing crontab with brackets"""
        crontab_content = """* * * * * /bin/command1 [arg1 arg2]"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "[arg1", "arg2]"]
        )

    def test_parse_atjobs_with_brackets(self):
        """Test parsing atjobs with brackets"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 [arg1 arg2]"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "[arg1", "arg2]"]
        )

    def test_cron_match_with_extra_whitespace(self):
        """Test cron_match with extra whitespace"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": " * ",
            "hour": " * ",
            "dayofmonth": " * ",
            "month": " * ",
            "dayofweek": " * ",
        }
        # Should fail since extra whitespace isn't allowed
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_future_dst_transition(self):
        """Test at_remain with future DST transition"""
        # This test may fail depending on the system's timezone and DST rules
        now = datetime.datetime.now()
        future_dst_time = now.replace(month=3, day=12, hour=2, minute=30)
        test_job = {"time_stamp": future_dst_time}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (future_dst_time - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_with_fragment(self):
        """Test path expansion with fragment"""
        trigger_path = "/test/path/file.txt#fragment"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(
            expanded["+TRIGGERPATH+"], "/test/path/file.txt#fragment"
        )
        self.assertEqual(expanded["+TRIGGERFILENAME+"], "file.txt#fragment")
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "file")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt#fragment")

    def test_get_time_expand_map_with_century_year(self):
        """Test time expansion with century year"""
        timestamp = datetime.datetime(2100, 1, 1, 0, 0)  # Year 2100
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2100")

    def test_run_cron_command_with_multiple_commands(self):
        """Test running cron command with multiple commands"""
        target_path = "test.txt"
        command_list = ["touch", "test1", "&&", "touch", "test2"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        try:
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command_with_multiple_commands(self):
        """Test running events command with multiple commands"""
        target_path = "test.txt"
        command_list = ["touch", "test1", "&&", "touch", "test2"]
        rule = {"run_as": DUMMY_USER_DN}
        try:
            run_events_command(
                command_list, target_path, rule, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_parse_crontab_with_quotes(self):
        """Test parsing crontab with quotes"""
        crontab_content = '''* * * * * /bin/command1 "arg1 with spaces"'''
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "arg1 with spaces"]
        )

    def test_parse_atjobs_with_quotes(self):
        """Test parsing atjobs with quotes"""
        atjobs_content = (
            '''2042-01-01 12:34:56 /bin/command1 "arg1 with spaces"'''
        )
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "arg1 with spaces"]
        )

    @unittest.skip("implement extra value check in function and enable next")
    def test_cron_match_with_invalid_field_count(self):
        """Test cron_match with invalid field count"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*",
            "hour": "*",
            "dayofmonth": "*",
            "month": "*",
            "dayofweek": "*",
            "extra_field": "*",
        }
        # Should fail since field count is invalid, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_past_dst_transition(self):
        """Test at_remain with past DST transition"""
        # This test may fail depending on the system's timezone and DST rules
        now = datetime.datetime.now()
        past_dst_time = now.replace(month=11, day=5, hour=1, minute=30)
        test_job = {"time_stamp": past_dst_time}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (past_dst_time - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_with_encoded_chars(self):
        """Test path expansion with encoded characters"""
        trigger_path = "/test/path/file%20with%20spaces.txt"
        rule = {"vgrid_name": "test", "run_as": DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, "modified")
        self.assertEqual(
            expanded["+TRIGGERPATH+"], "/test/path/file%20with%20spaces.txt"
        )
        self.assertEqual(
            expanded["+TRIGGERFILENAME+"], "file%20with%20spaces.txt"
        )
        self.assertEqual(expanded["+TRIGGERPREFIX+"], "file%20with%20spaces")
        self.assertEqual(expanded["+TRIGGEREXTENSION+"], ".txt")

    def test_get_time_expand_map_with_millennium_year(self):
        """Test time expansion with millennium year"""
        timestamp = datetime.datetime(2000, 1, 1, 0, 0)  # Year 2000
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "2000")

    def test_run_cron_command_with_input_redirection(self):
        """Test running cron command with input redirection"""
        target_path = "test.txt"
        command_list = ["chksum", "md5", "<", "input.txt"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        # NOTE: touch fails without log in input validation
        with self.assertRaises(Exception):
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )

    def test_run_events_command_with_input_redirection(self):
        """Test running events command with input redirection"""
        target_path = "test.txt"
        command_list = ["chksum", "md5", "<", "input.txt"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "found invalid character" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_single_quotes(self):
        """Test parsing crontab with single quotes"""
        crontab_content = """* * * * * /bin/command1 'arg1 with spaces'"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "arg1 with spaces"]
        )

    def test_parse_atjobs_with_single_quotes(self):
        """Test parsing atjobs with single quotes"""
        atjobs_content = (
            """2042-01-01 12:34:56 /bin/command1 'arg1 with spaces'"""
        )
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "arg1 with spaces"]
        )

    def test_cron_match_with_missing_fields(self):
        """Test cron_match with missing fields"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "*",
            "hour": "*",
            "dayofmonth": "*",
            "dayofweek": "*",
        }
        # NOTE: throws exception before log since values must be strings
        with self.assertRaises(Exception):
            result = cron_match(self.configuration, now, test_job)

    # NOTE: no datetime support https://github.com/python/cpython/issues/67762
    @unittest.skip("enable if leap second handling is ever implemented")
    def test_at_remain_with_future_leap_second(self):
        """Test at_remain with future leap second"""
        # December 31, 2016, had a leap second to include time 23:59:60
        now = datetime.datetime.now(datetime.timezone.utc)
        t_minus_sixty = now.replace(
            year=2016,
            month=12,
            day=31,
            hour=23,
            minute=59,
            second=0,
            microsecond=0,
        )
        leap_second = t_minus_sixty + datetime.timedelta(seconds=60)
        t_plus_sixty = now.replace(
            year=2017,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=59,
            microsecond=0,
        )
        self.assertEqual(
            (t_plus_sixty - t_minus_sixty).total_seconds(),
            120,
            "Leap second does not appear supported",
        )
        test_job = {"time_stamp": leap_second}
        remaining = at_remain(self.configuration, t_minus_sixty, test_job)
        # print("DEBUG: remaining now %s vs %s vs %s : %s" %
        #      (t_minus_sixty, leap_second, t_plus_sixty, remaining))
        self.assertEqual(remaining, 1)

    def test_get_time_expand_map_with_year_zero(self):
        """Test time expansion with year zero"""
        timestamp = datetime.datetime(1, 1, 1, 0, 0)  # Year 1
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "1")

    def test_run_cron_command_with_here_document(self):
        """Test running cron command with here document"""
        target_path = "test.txt"
        command_list = ["cat", "<<EOF", "test content", "EOF"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_here_document(self):
        """Test running events command with here document"""
        target_path = "test.txt"
        command_list = ["cat", "<<EOF", "test content", "EOF"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_backslash(self):
        """Test parsing crontab with backslash"""
        crontab_content = """* * * * * /bin/command1 arg1\\ arg2"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "arg1 arg2"])

    def test_parse_atjobs_with_backslash(self):
        """Test parsing atjobs with backslash"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 arg1\\ arg2"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "arg1 arg2"])

    def test_cron_match_with_non_string_values(self):
        """Test cron_match with non-string values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": 15,
            "hour": 3,
            "dayofmonth": 7,
            "month": 6,
            "dayofweek": 1,
        }
        # NOTE: throws exception before log since values must be strings
        with self.assertRaises(Exception):
            result = cron_match(self.configuration, now, test_job)

    # NOTE: no datetime support https://github.com/python/cpython/issues/67762
    @unittest.skip("enable if leap second handling is ever implemented")
    def test_at_remain_with_past_leap_second(self):
        """Test at_remain with past leap second"""
        # December 31, 2016, had a leap second to include time 23:59:60
        now = datetime.datetime.now(datetime.timezone.utc)
        t_minus_sixty = now.replace(
            year=2016,
            month=12,
            day=31,
            hour=23,
            minute=59,
            second=0,
            microsecond=0,
        )
        leap_second = t_minus_sixty + datetime.timedelta(seconds=60)
        t_plus_sixty = now.replace(
            year=2017,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=59,
            microsecond=0,
        )
        t_plus_sixtyone = now.replace(
            year=2017, month=1, day=1, hour=0, minute=1, second=0, microsecond=0
        )
        self.assertEqual(
            (t_plus_sixty - t_minus_sixty).total_seconds(),
            120,
            "Leap second does not appear supported",
        )
        test_job = {"time_stamp": leap_second}
        remaining = at_remain(self.configuration, t_plus_sixty, test_job)
        # print("DEBUG: remaining now %s vs %s vs %s : %s" %
        #      (t_minus_sixty, leap_second, t_plus_sixty, remaining))
        self.assertEqual(remaining, -1)
        remaining = at_remain(self.configuration, t_plus_sixtyone, test_job)
        # print("DEBUG: remaining now %s vs %s vs %s : %s" %
        #      (t_minus_sixty, leap_second, t_plus_sixtyone, remaining))
        self.assertEqual(remaining, -2)

    def test_get_time_expand_map_with_year_9999(self):
        """Test time expansion with year 9999"""
        timestamp = datetime.datetime(9999, 12, 31, 23, 59)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "31")
        self.assertEqual(expanded["+SCHEDMONTH+"], "12")
        self.assertEqual(expanded["+SCHEDYEAR+"], "9999")

    def test_run_cron_command_with_subshell(self):
        """Test running cron command with subshell"""
        target_path = "test.txt"
        command_list = ["(touch", "test1; touch", "test2)"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_subshell(self):
        """Test running events command with subshell"""
        target_path = "test.txt"
        command_list = ["(touch", "test1; touch", "test2)"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_double_backslash(self):
        """Test parsing crontab with double backslash"""
        crontab_content = """* * * * * /bin/command1 arg1\\\\ arg2"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "arg1\\", "arg2"]
        )

    def test_parse_atjobs_with_double_backslash(self):
        """Test parsing atjobs with double backslash"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 arg1\\\\ arg2"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "arg1\\", "arg2"]
        )

    def test_cron_match_with_boolean_values(self):
        """Test cron_match with boolean values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": True,
            "hour": False,
            "dayofmonth": True,
            "month": False,
            "dayofweek": True,
        }
        # NOTE: throws exception before log since values must be strings
        with self.assertRaises(Exception):
            result = cron_match(self.configuration, now, test_job)

    def test_at_remain_with_future_leap_year(self):
        """Test at_remain with future leap year"""
        now = datetime.datetime.now()
        future_leap_year = now.replace(
            year=2096, month=2, day=29, hour=12, minute=0
        )
        test_job = {"time_stamp": future_leap_year}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (future_leap_year - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_time_expand_map_with_year_0001(self):
        """Test time expansion with year 0001"""
        timestamp = datetime.datetime(1, 1, 1, 0, 0)  # Year 1
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "1")

    def test_run_cron_command_with_command_substitution(self):
        """Test running cron command with command substitution"""
        target_path = "test.txt"
        command_list = ["touch", "$(date)"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        try:
            run_cron_command(
                command_list, target_path, crontab_entry, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command_with_command_substitution(self):
        """Test running events command with command substitution"""
        target_path = "test.txt"
        command_list = ["touch", "$(date)"]
        rule = {"run_as": DUMMY_USER_DN}
        try:
            run_events_command(
                command_list, target_path, rule, self.configuration
            )
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_parse_crontab_with_caret(self):
        """Test parsing crontab with caret"""
        crontab_content = """* * * * * /bin/command1 ^arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "^arg1"])

    def test_parse_atjobs_with_caret(self):
        """Test parsing atjobs with caret"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 ^arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "^arg1"])

    def test_cron_match_with_none_values(self):
        """Test cron_match with none values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": None,
            "hour": None,
            "dayofmonth": None,
            "month": None,
            "dayofweek": None,
        }
        # NOTE: throws exception before log since values must be strings
        with self.assertRaises(Exception):
            result = cron_match(self.configuration, now, test_job)

    def test_at_remain_with_past_leap_year(self):
        """Test at_remain with past leap year"""
        now = datetime.datetime.now()
        past_leap_year = now.replace(
            year=2000, month=2, day=29, hour=12, minute=0
        )
        test_job = {"time_stamp": past_leap_year}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (past_leap_year - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_time_expand_map_with_year_9999_end(self):
        """Test time expansion with year 9999 end"""
        timestamp = datetime.datetime(9999, 12, 31, 23, 59)
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "31")
        self.assertEqual(expanded["+SCHEDMONTH+"], "12")
        self.assertEqual(expanded["+SCHEDYEAR+"], "9999")

    def test_run_cron_command_with_true_command(self):
        """Test running cron command with true command"""
        target_path = "test.txt"
        command_list = ["true"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_true_command(self):
        """Test running events command with true command"""
        target_path = "test.txt"
        command_list = ["true"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_hash(self):
        """Test parsing crontab with hash"""
        crontab_content = """* * * * * /bin/command1 #arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1"])

    def test_parse_atjobs_with_hash(self):
        """Test parsing atjobs with hash"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 #arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1"])

    def test_cron_match_with_tab_values(self):
        """Test cron_match with tab values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "\t",
            "hour": "\t",
            "dayofmonth": "\t",
            "month": "\t",
            "dayofweek": "\t",
        }
        # Should fail since values are tabs, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_future_millennium(self):
        """Test at_remain with future millennium"""
        now = datetime.datetime.now()
        future_millennium = now.replace(
            year=now.year + 1000, month=1, day=1, hour=0, minute=0
        )
        test_job = {"time_stamp": future_millennium}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (future_millennium - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_time_expand_map_with_year_0001_end(self):
        """Test time expansion with year 0001 end"""
        timestamp = datetime.datetime(1, 12, 31, 23, 59)  # Year 1
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "31")
        self.assertEqual(expanded["+SCHEDMONTH+"], "12")
        self.assertEqual(expanded["+SCHEDYEAR+"], "1")

    def test_run_cron_command_with_false_command(self):
        """Test running cron command with false command"""
        target_path = "test.txt"
        command_list = ["false"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_false_command(self):
        """Test running events command with false command"""
        target_path = "test.txt"
        command_list = ["false"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_dollar(self):
        """Test parsing crontab with dollar"""
        crontab_content = """* * * * * /bin/command1 $arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "$arg1"])

    def test_parse_atjobs_with_dollar(self):
        """Test parsing atjobs with dollar"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 $arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "$arg1"])

    def test_cron_match_with_newline_values(self):
        """Test cron_match with newline values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "\n",
            "hour": "\n",
            "dayofmonth": "\n",
            "month": "\n",
            "dayofweek": "\n",
        }
        # Should fail since values are newlines, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_past_millennium(self):
        """Test at_remain with past millennium"""
        now = datetime.datetime.now()
        past_millennium = now.replace(
            year=now.year - 1000, month=1, day=1, hour=0, minute=0
        )
        test_job = {"time_stamp": past_millennium}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (past_millennium - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_run_cron_command_with_null_command(self):
        """Test running cron command with null command"""
        target_path = "test.txt"
        command_list = [":"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_null_command(self):
        """Test running events command with null command"""
        target_path = "test.txt"
        command_list = [":"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_percent(self):
        """Test parsing crontab with percent"""
        crontab_content = """* * * * * /bin/command1 %arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "%arg1"])

    def test_parse_atjobs_with_percent(self):
        """Test parsing atjobs with percent"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 %arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "%arg1"])

    def test_cron_match_with_carriage_return_values(self):
        """Test cron_match with carriage return values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "\r",
            "hour": "\r",
            "dayofmonth": "\r",
            "month": "\r",
            "dayofweek": "\r",
        }
        # Should fail since values are carriage returns, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_future_millennium_end(self):
        """Test at_remain with future millennium end"""
        now = datetime.datetime.now()
        future_millennium_end = now.replace(
            year=now.year + 1000, month=12, day=31, hour=23, minute=59
        )
        test_job = {"time_stamp": future_millennium_end}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (future_millennium_end - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_time_expand_map_with_year_0001_start(self):
        """Test time expansion with year 0001 start"""
        timestamp = datetime.datetime(1, 1, 1, 0, 0)  # Year 1
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "1")

    def test_run_cron_command_with_builtin_command(self):
        """Test running cron command with builtin command"""
        target_path = "test.txt"
        command_list = ["builtin", "command"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_builtin_command(self):
        """Test running events command with builtin command"""
        target_path = "test.txt"
        command_list = ["builtin", "command"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_ampersand(self):
        """Test parsing crontab with ampersand"""
        crontab_content = """* * * * * /bin/command1 &arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "&arg1"])

    def test_parse_atjobs_with_ampersand(self):
        """Test parsing atjobs with ampersand"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 &arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "&arg1"])

    def test_cron_match_with_vertical_tab_values(self):
        """Test cron_match with vertical tab values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "\v",
            "hour": "\v",
            "dayofmonth": "\v",
            "month": "\v",
            "dayofweek": "\v",
        }
        # Should fail since values are vertical tabs, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_past_millennium_end(self):
        """Test at_remain with past millennium end"""
        now = datetime.datetime.now()
        past_millennium_end = now.replace(
            year=now.year - 1000, month=12, day=31, hour=23, minute=59
        )
        test_job = {"time_stamp": past_millennium_end}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (past_millennium_end - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_get_time_expand_map_with_year_9999_start(self):
        """Test time expansion with year 9999 start"""
        timestamp = datetime.datetime(9999, 1, 1, 0, 0)  # Year 9999
        rule = {"run_as": DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded["+SCHEDDAY+"], "01")
        self.assertEqual(expanded["+SCHEDMONTH+"], "01")
        self.assertEqual(expanded["+SCHEDYEAR+"], "9999")

    def test_run_cron_command_with_alias_command(self):
        """Test running cron command with alias command"""
        target_path = "test.txt"
        command_list = ["alias", "command"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_alias_command(self):
        """Test running events command with alias command"""
        target_path = "test.txt"
        command_list = ["alias", "command"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_pipe(self):
        """Test parsing crontab with pipe"""
        crontab_content = """* * * * * /bin/command1 | /bin/command2"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "|", "/bin/command2"]
        )

    def test_parse_atjobs_with_pipe(self):
        """Test parsing atjobs with pipe"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 | /bin/command2"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(
            parsed[0]["command"], ["/bin/command1", "|", "/bin/command2"]
        )

    def test_cron_match_with_form_feed_values(self):
        """Test cron_match with form feed values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "\f",
            "hour": "\f",
            "dayofmonth": "\f",
            "month": "\f",
            "dayofweek": "\f",
        }
        # Should fail since values are form feeds, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_future_century_end(self):
        """Test at_remain with future century end"""
        now = datetime.datetime.now()
        future_century_end = now.replace(
            year=now.year + 100, month=12, day=31, hour=23, minute=59
        )
        test_job = {"time_stamp": future_century_end}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (future_century_end - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_run_cron_command_with_function_command(self):
        """Test running cron command with function command"""
        target_path = "test.txt"
        command_list = ["function", "name() { command; }"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_function_command(self):
        """Test running events command with function command"""
        target_path = "test.txt"
        command_list = ["function", "name() { command; }"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_question_mark(self):
        """Test parsing crontab with question mark"""
        crontab_content = """* * * * * /bin/command1 ?arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "?arg1"])

    def test_parse_atjobs_with_question_mark(self):
        """Test parsing atjobs with question mark"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 ?arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "?arg1"])

    def test_cron_match_with_escape_values(self):
        """Test cron_match with escape values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "\\",
            "hour": "\\",
            "dayofmonth": "\\",
            "month": "\\",
            "dayofweek": "\\",
        }
        # Should fail since values are escapes, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_past_century_end(self):
        """Test at_remain with past century end"""
        now = datetime.datetime.now()
        past_century_end = now.replace(
            year=now.year - 100, month=12, day=31, hour=23, minute=59
        )
        test_job = {"time_stamp": past_century_end}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (past_century_end - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_run_cron_command_with_reserved_command(self):
        """Test running cron command with reserved command"""
        target_path = "test.txt"
        command_list = ["reserved", "command"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_plus(self):
        """Test parsing crontab with plus"""
        crontab_content = """* * * * * /bin/command1 +arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "+arg1"])

    def test_parse_atjobs_with_plus(self):
        """Test parsing atjobs with plus"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 +arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "+arg1"])

    def test_cron_match_with_delete_values(self):
        """Test cron_match with delete values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": "\x7f",
            "hour": "\x7f",
            "dayofmonth": "\x7f",
            "month": "\x7f",
            "dayofweek": "\x7f",
        }
        # Should fail since values are deletes, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_future_century_start(self):
        """Test at_remain with future century start"""
        now = datetime.datetime.now()
        future_century_start = now.replace(
            year=now.year + 100, month=1, day=1, hour=0, minute=0
        )
        test_job = {"time_stamp": future_century_start}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (future_century_start - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_run_cron_command_with_dot_command(self):
        """Test running cron command with dot command"""
        target_path = "test.txt"
        command_list = [".", "command"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_dot_command(self):
        """Test running events command with dot command"""
        target_path = "test.txt"
        command_list = [".", "command"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_comma(self):
        """Test parsing crontab with comma"""
        crontab_content = """* * * * * /bin/command1,arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1,arg1"])

    def test_parse_atjobs_with_comma(self):
        """Test parsing atjobs with comma"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1,arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1,arg1"])

    def test_cron_match_with_space_values(self):
        """Test cron_match with space values"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {
            "minute": " ",
            "hour": " ",
            "dayofmonth": " ",
            "month": " ",
            "dayofweek": " ",
        }
        # Should fail since values are spaces, but shouldn't crash
        # NOTE: tweak cron_match use for missing debug log access in assertLogs
        with self.assertLogs(level="WARNING") as log_capture:
            result = cron_match(
                self.configuration, now, test_job, _warn_mismatch=True
            )
            self.assertFalse(result)
            self.assertTrue(
                any("no cron_match on" in msg for msg in log_capture.output)
            )

    def test_at_remain_with_past_century_start(self):
        """Test at_remain with past century start"""
        now = datetime.datetime.now()
        past_century_start = now.replace(
            year=now.year - 100, month=1, day=1, hour=0, minute=0
        )
        test_job = {"time_stamp": past_century_start}
        remaining = at_remain(self.configuration, now, test_job)
        expected_minutes = (past_century_start - now).total_seconds() // 60
        self.assertEqual(remaining, expected_minutes)

    def test_run_cron_command_with_colon_command(self):
        """Test running cron command with colon command"""
        target_path = "test.txt"
        command_list = [":"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_cron_command_with_bracket_command(self):
        """Test running cron command with bracket command"""
        target_path = "test.txt"
        command_list = ["[", "test", "-f", "file", "]"]
        crontab_entry = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(
                    command_list, target_path, crontab_entry, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_run_events_command_with_bracket_command(self):
        """Test running events command with bracket command"""
        target_path = "test.txt"
        command_list = ["[", "test", "-f", "file", "]"]
        rule = {"run_as": DUMMY_USER_DN}
        with self.assertLogs(level="ERROR") as log_capture:
            with self.assertRaises(Exception):
                run_events_command(
                    command_list, target_path, rule, self.configuration
                )
            self.assertTrue(
                any(
                    "failed to run" in msg or "failed to lookup" in msg
                    for msg in log_capture.output
                )
            )

    def test_parse_crontab_with_less_than(self):
        """Test parsing crontab with less than"""
        crontab_content = """* * * * * /bin/command1 <arg1"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(
            self.configuration, DUMMY_USER_DN, crontab_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "<arg1"])

    def test_parse_atjobs_with_less_than(self):
        """Test parsing atjobs with less than"""
        atjobs_content = """2042-01-01 12:34:56 /bin/command1 <arg1"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(
            self.configuration, DUMMY_USER_DN, atjobs_lines
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["command"], ["/bin/command1", "<arg1"])


class MigLibEvents__legacy_main(MigTestCase):
    """Unit tests for legacy events self-checks"""

    def test_existing_main(self):
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
            raise_on_error_exit.last_print = value

        events_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == "__main__":
    unittest.main()
