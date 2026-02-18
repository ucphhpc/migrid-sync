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

from mig.lib.events import parse_crontab, cron_match, parse_atjobs, at_remain, \
    get_path_expand_map, get_time_expand_map, load_crontab, load_atjobs, \
    parse_crontab_contents, parse_atjobs_contents, parse_and_save_crontab, \
    parse_and_save_atjobs, run_cron_command, run_events_command, \
    main as events_main
from mig.shared.base import distinguished_name_to_user
from tests.support import MigTestCase, ensure_dirs_exist

DUMMY_USER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
DUMMY_FULL_NAME = "Test User"
DUMMY_ORGANIZATION = "Test Org"
DUMMY_EMAIL = "test@example.com"
DUMMY_SKIP_EMAIL = ''
DUMMY_CLIENT_DIR = '+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@example.com'
DUMMY_CRON_JOB = {'command': ['touch', 'test.txt'], 'run_as': DUMMY_USER_DN}
DUMMY_CRONTAB_NAME = 'crontab'
DUMMY_ATJOBS_NAME = 'atjobs'
DUMMY_CRONTAB_CONTENT = """* * * * * /bin/test_command
30 2 * * * /usr/bin/another_command"""
DUMMY_ATJOBS_CONTENT = """2042-01-01 12:34:56 /bin/future_command"""


class MigLibEvents(MigTestCase):
    """Unit tests for events helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

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
        crontab_path = os.path.join(self.configuration.user_settings,
                                    DUMMY_CLIENT_DIR, DUMMY_CRONTAB_NAME)
        os.makedirs(os.path.dirname(crontab_path), exist_ok=True)
        with open(crontab_path, 'w') as fd:
            fd.write(DUMMY_CRONTAB_CONTENT)

        crontab = load_crontab(DUMMY_USER_DN, self.configuration)
        self.assertIn('* * * * * /bin/test_command', crontab)

    def test_load_atjobs(self):
        """Test loading atjobs from file"""
        atjobs_path = os.path.join(self.configuration.user_settings,
                                   DUMMY_CLIENT_DIR, DUMMY_ATJOBS_NAME)
        os.makedirs(os.path.dirname(atjobs_path), exist_ok=True)
        with open(atjobs_path, 'w') as fd:
            fd.write(DUMMY_ATJOBS_CONTENT)

        atjobs = load_atjobs(DUMMY_USER_DN, self.configuration)
        self.assertIn('2042-01-01 12:34:56 /bin/future_command', atjobs)

    def test_parse_crontab_contents(self):
        """Test parsing crontab content lines"""
        crontab_lines = DUMMY_CRONTAB_CONTENT.splitlines()
        parsed = parse_crontab_contents(self.configuration, DUMMY_USER_DN,
                                        crontab_lines)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['command'], ['/bin/test_command'])

    def test_parse_atjobs_contents(self):
        """Test parsing atjobs content lines"""
        atjobs_lines = DUMMY_ATJOBS_CONTENT.splitlines()
        parsed = parse_atjobs_contents(self.configuration, DUMMY_USER_DN,
                                       atjobs_lines)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['command'], ['/bin/future_command'])

    def test_parse_and_save_crontab(self):
        """Test parsing and saving crontab"""
        crontab = DUMMY_CRONTAB_CONTENT
        status, msg = parse_and_save_crontab(crontab, DUMMY_USER_DN,
                                             self.configuration)
        self.assertTrue(status)
        self.assertIn('valid crontab entries', msg)

    def test_parse_and_save_atjobs(self):
        """Test parsing and saving atjobs"""
        atjobs = DUMMY_ATJOBS_CONTENT
        status, msg = parse_and_save_atjobs(atjobs, DUMMY_USER_DN,
                                            self.configuration)
        self.assertTrue(status)
        self.assertIn('valid atjobs entries', msg)

    def test_cron_match(self):
        """Test cron time matching"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {'minute': '*', 'hour': '*',
                    'dayofmonth': '*', 'month': '*', 'dayofweek': '*'}
        self.assertTrue(cron_match(self.configuration, now, test_job))

    def test_at_remain(self):
        """Test at job remaining time calculation"""
        now = datetime.datetime.now()
        future_time = now + datetime.timedelta(minutes=30)
        test_job = {'time_stamp': future_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, 30)

    def test_get_path_expand_map(self):
        """Test path expansion map generation"""
        trigger_path = '/test/path/file.txt'
        rule = {'vgrid_name': 'test', 'run_as': DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, 'modified')
        self.assertIn('+TRIGGERPATH+', expanded)
        self.assertEqual(expanded['+TRIGGERPATH+'], trigger_path)

    def test_get_time_expand_map(self):
        """Test time expansion map generation"""
        timestamp = datetime.datetime(2023, 1, 2, 9, 2)
        rule = {'run_as': DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertIn('+SCHEDYEAR+', expanded)
        self.assertEqual(expanded['+SCHEDYEAR+'], '2023')

    def test_run_cron_command(self):
        """Test running cron command"""
        target_path = 'test.txt'
        command_list = ['touch', target_path]
        crontab_entry = {'run_as': DUMMY_USER_DN}
        try:
            run_cron_command(command_list, target_path, crontab_entry,
                             self.configuration)
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command(self):
        """Test running events command"""
        target_path = 'test.txt'
        command_list = ['touch', target_path]
        rule = {'run_as': DUMMY_USER_DN}
        try:
            run_events_command(command_list, target_path, rule,
                               self.configuration)
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_parse_valid_crontab_file(self):
        """Test parsing valid crontab file"""
        crontab_path = os.path.join(self.configuration.user_settings,
                                    DUMMY_CLIENT_DIR, DUMMY_CRONTAB_NAME)
        os.makedirs(os.path.dirname(crontab_path), exist_ok=True)
        with open(crontab_path, 'w') as fd:
            fd.write(DUMMY_CRONTAB_CONTENT)

        parsed = parse_crontab(self.configuration, DUMMY_USER_DN, crontab_path)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['command'], ['/bin/test_command'])

    def test_parse_empty_crontab_file(self):
        """Test parsing empty crontab file"""
        crontab_path = os.path.join(self.configuration.user_settings,
                                    DUMMY_CLIENT_DIR, DUMMY_CRONTAB_NAME)
        os.makedirs(os.path.dirname(crontab_path), exist_ok=True)
        open(crontab_path, 'a').close()  # Create empty file

        parsed = parse_crontab(self.configuration, DUMMY_USER_DN, crontab_path)
        self.assertEqual(parsed, [])

    def test_parse_valid_atjobs_file(self):
        """Test parsing valid atjobs file"""
        atjobs_path = os.path.join(self.configuration.user_settings,
                                   DUMMY_CLIENT_DIR, DUMMY_ATJOBS_NAME)
        os.makedirs(os.path.dirname(atjobs_path), exist_ok=True)
        with open(atjobs_path, 'w') as fd:
            fd.write(DUMMY_ATJOBS_CONTENT)

        parsed = parse_atjobs(self.configuration, DUMMY_USER_DN, atjobs_path)
        self.assertEqual(len(parsed), 1)
        self.assertTrue(parsed[0]['time_stamp'] > datetime.datetime.now())

    def test_parse_empty_atjobs_file(self):
        """Test parsing empty atjobs file"""
        atjobs_path = os.path.join(self.configuration.user_settings,
                                   DUMMY_CLIENT_DIR, DUMMY_ATJOBS_NAME)
        os.makedirs(os.path.dirname(atjobs_path), exist_ok=True)
        open(atjobs_path, 'a').close()  # Create empty file

        parsed = parse_atjobs(self.configuration, DUMMY_USER_DN, atjobs_path)
        self.assertEqual(parsed, [])

    def test_cron_match_current_minute(self):
        """Test cron_match identifies current time match"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_job = {'minute': '*', 'hour': '*',
                    'day': '*', 'month': '*', 'dayofweek': '*',
                    'dayofmonth': '*'}
        self.assertTrue(cron_match(self.configuration, now, test_job))

    def test_cron_match_specific_time(self):
        """Test cron_match rejects non-matching time"""
        now = datetime.datetime.now().replace(hour=3, minute=15, second=0, microsecond=0)
        test_job = {'minute': '30', 'hour': '2',
                    'dayofmonth': '*', 'month': '*', 'dayofweek': '*'}
        self.assertFalse(cron_match(self.configuration, now, test_job))

    def test_at_remain_past_job(self):
        """Test at_remain with past job"""
        now = datetime.datetime.now()
        past_time = now - datetime.timedelta(minutes=30)
        test_job = {'time_stamp': past_time}
        remaining = at_remain(self.configuration, now, test_job)
        self.assertEqual(remaining, -30)

    def test_get_path_expand_map_with_special_chars(self):
        """Test path expansion with special characters"""
        trigger_path = '/test/path/file with spaces.txt'
        rule = {'vgrid_name': 'test', 'run_as': DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, 'modified')
        self.assertIn('+TRIGGERFILENAME+', expanded)
        self.assertEqual(expanded['+TRIGGERFILENAME+'], 'file with spaces.txt')

    def test_get_time_expand_map_edge_cases(self):
        """Test time expansion with edge cases"""
        timestamp = datetime.datetime(2023, 12, 31, 23, 59)
        rule = {'run_as': DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded['+SCHEDDAY+'], '31')
        self.assertEqual(expanded['+SCHEDMONTH+'], '12')
        self.assertEqual(expanded['+SCHEDHOUR+'], '23')
        self.assertEqual(expanded['+SCHEDMINUTE+'], '59')

    def test_run_cron_command_with_invalid_command(self):
        """Test running cron command with invalid command"""
        target_path = 'test.txt'
        command_list = ['invalid_command', target_path]
        crontab_entry = {'run_as': DUMMY_USER_DN}
        with self.assertLogs(level='DEBUG') as log_capture:
            with self.assertRaises(Exception):
                run_cron_command(command_list, target_path, crontab_entry,
                                 self.configuration)
            self.assertTrue(
                any('failed to run' in msg or 'failed to lookup' in msg
                    for msg in log_capture.output))

    def test_run_events_command_with_invalid_command(self):
        """Test running events command with invalid command"""
        command_list = ['invalid_command', 'test']
        target_path = '/test/path'
        rule = {'run_as': DUMMY_USER_DN}
        with self.assertLogs(level='ERROR') as log_capture:
            with self.assertRaises(Exception):
                run_events_command(command_list, target_path, rule,
                                   self.configuration)
            self.assertTrue(
                any('failed to run' in msg or 'failed to lookup' in msg
                    for msg in log_capture.output))

    def test_cron_match_edge_cases(self):
        """Test cron_match with edge case times"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_cases = [
            ({'minute': '0', 'hour': '0', 'dayofmonth': '1', 'month': '1', 'dayofweek': '0'},
             now.replace(hour=0, minute=0, day=1, month=1)),
            ({'minute': '59', 'hour': '23', 'dayofmonth': '31', 'month': '12', 'dayofweek': '6'},
             now.replace(hour=23, minute=59, day=31, month=12)),
        ]
        for job, match_time in test_cases:
            self.assertEqual(cron_match(self.configuration, match_time, job),
                             match_time == now)

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
            test_job = {'time_stamp': future_time}
            remaining = at_remain(self.configuration, now, test_job)
            self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_empty_path(self):
        """Test path expansion with empty path"""
        trigger_path = ''
        rule = {'vgrid_name': 'test', 'run_as': DUMMY_USER_DN}
        with self.assertRaises(ValueError):
            expanded = get_path_expand_map(trigger_path, rule, 'modified')

    def test_get_time_expand_map_leap_year(self):
        """Test time expansion with leap year"""
        timestamp = datetime.datetime(2024, 2, 29, 12, 0)  # Leap day
        rule = {'run_as': DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded['+SCHEDDAY+'], '29')
        self.assertEqual(expanded['+SCHEDMONTH+'], '02')
        self.assertEqual(expanded['+SCHEDYEAR+'], '2024')

    def test_run_cron_command_with_special_chars(self):
        """Test running cron command with special characters"""
        target_path = 'test file with spaces.txt'
        command_list = ['touch', target_path]
        crontab_entry = {'run_as': DUMMY_USER_DN}
        try:
            run_cron_command(command_list, target_path, crontab_entry,
                             self.configuration)
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command_with_special_chars(self):
        """Test running events command with special characters"""
        target_path = 'test file with spaces.txt'
        command_list = ['touch', target_path]
        rule = {'run_as': DUMMY_USER_DN}
        try:
            run_events_command(command_list, target_path, rule,
                               self.configuration)
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_parse_crontab_with_comments(self):
        """Test parsing crontab with comments"""
        crontab_content = """# This is a comment
* * * * * /bin/test_command
# Another comment
30 2 * * * /usr/bin/another_command"""
        crontab_lines = crontab_content.splitlines()
        parsed = parse_crontab_contents(self.configuration, DUMMY_USER_DN,
                                        crontab_lines)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['command'], ['/bin/test_command'])

    def test_parse_atjobs_with_comments(self):
        """Test parsing atjobs with comments"""
        atjobs_content = """# This is a comment
2042-01-01 12:34:56 /bin/future_command
# Another comment"""
        atjobs_lines = atjobs_content.splitlines()
        parsed = parse_atjobs_contents(self.configuration, DUMMY_USER_DN,
                                       atjobs_lines)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['command'], ['/bin/future_command'])

    def test_cron_match_with_wildcards(self):
        """Test cron_match with various wildcard combinations"""
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        test_cases = [
            ({'minute': '*', 'hour': '*', 'dayofmonth': '*', 'month': '*', 'dayofweek': '*'},
             True),
            ({'minute': '15', 'hour': '*', 'dayofmonth': '*', 'month': '*', 'dayofweek': '*'},
             now.minute == 15),
            ({'minute': '*', 'hour': '3', 'dayofmonth': '*', 'month': '*', 'dayofweek': '*'},
             now.hour == 3),
            ({'minute': '*', 'hour': '*', 'dayofmonth': '15', 'month': '*', 'dayofweek': '*'},
             now.day == 15),
            ({'minute': '*', 'hour': '*', 'dayofmonth': '*', 'month': '6', 'dayofweek': '*'},
             now.month == 6),
            ({'minute': '*', 'hour': '*', 'dayofmonth': '*', 'month': '*', 'dayofweek': '0'},
             now.weekday() == 0),
        ]
        for job, expected in test_cases:
            self.assertEqual(cron_match(
                self.configuration, now, job), expected)

    @unittest.skip("enable next if ever relevant - fails with TypeError")
    def test_at_remain_with_timezones(self):
        """Test at_remain with different timezones"""
        now = datetime.datetime.now()
        test_cases = [
            (now.astimezone(datetime.timezone.utc) +
             datetime.timedelta(minutes=30), 30),
            (now.astimezone(datetime.timezone.utc) -
             datetime.timedelta(minutes=30), -30),
        ]
        for future_time, expected_minutes in test_cases:
            test_job = {'time_stamp': future_time}
            remaining = at_remain(self.configuration, now, test_job)
            self.assertEqual(remaining, expected_minutes)

    def test_get_path_expand_map_with_relative_path(self):
        """Test path expansion with relative path"""
        trigger_path = '../relative/path/file.txt'
        rule = {'vgrid_name': 'test', 'run_as': DUMMY_USER_DN}
        expanded = get_path_expand_map(trigger_path, rule, 'modified')
        self.assertEqual(expanded['+TRIGGERPATH+'],
                         '../relative/path/file.txt')
        self.assertEqual(expanded['+TRIGGERFILENAME+'], 'file.txt')
        self.assertEqual(expanded['+TRIGGERPREFIX+'], 'file')
        self.assertEqual(expanded['+TRIGGEREXTENSION+'], '.txt')

    def test_get_time_expand_map_with_milliseconds(self):
        """Test time expansion with milliseconds"""
        timestamp = datetime.datetime(2023, 1, 2, 9, 2, 30, 123456)
        rule = {'run_as': DUMMY_USER_DN}
        expanded = get_time_expand_map(timestamp, rule)
        self.assertEqual(expanded['+SCHEDSECOND+'], '30')
        self.assertEqual(expanded['+SCHEDMINUTE+'], '02')
        self.assertEqual(expanded['+SCHEDHOUR+'], '09')
        self.assertEqual(expanded['+SCHEDDAY+'], '02')
        self.assertEqual(expanded['+SCHEDMONTH+'], '01')
        self.assertEqual(expanded['+SCHEDYEAR+'], '2023')
        self.assertEqual(expanded['+SCHEDDAYOFWEEK+'], '0')

    def test_run_cron_command_with_long_command(self):
        """Test running cron command with long command"""
        target_path = 'test.txt'
        long_command = ['touch'] + ['arg'] * 100
        command_list = long_command
        crontab_entry = {'run_as': DUMMY_USER_DN}
        try:
            run_cron_command(command_list, target_path, crontab_entry,
                             self.configuration)
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_cron_command raised an exception: %s" % exc)

    def test_run_events_command_with_long_command(self):
        """Test running events command with long command"""
        target_path = 'test.txt'
        long_command = ['touch'] + ['arg'] * 100
        command_list = long_command
        rule = {'run_as': DUMMY_USER_DN}
        try:
            run_events_command(command_list, target_path, rule,
                               self.configuration)
            self.assertTrue(True)  # If no exception, test passes
        except Exception as exc:
            self.fail("run_events_command raised an exception: %s" % exc)

    def test_parse_crontab_with_invalid_lines(self):
        """Test parsing crontab with invalid lines"""
        crontab_content = """* * * * * /bin/test_command
invalid line
30 2 * * * /usr/bin/another_command"""
        crontab_lines = crontab_content.splitlines()
        with self.assertLogs(level='WARNING') as log_capture:
            parsed = parse_crontab_contents(self.configuration, DUMMY_USER_DN,
                                            crontab_lines)
            self.assertEqual(len(parsed), 2)
            self.assertTrue(any('Skip invalid crontab line' in msg
                                for msg in log_capture.output))

    def test_parse_atjobs_with_invalid_lines(self):
        """Test parsing atjobs with invalid lines"""
        atjobs_content = """2042-01-01 12:34:56 /bin/future_command
invalid line
2042-01-02 12:34:56 /bin/another_command"""
        atjobs_lines = atjobs_content.splitlines()
        with self.assertLogs(level='WARNING') as log_capture:
            parsed = parse_atjobs_contents(self.configuration, DUMMY_USER_DN,
                                           atjobs_lines)
            self.assertEqual(len(parsed), 2)
            self.assertTrue(any('Skip invalid atjobs line' in msg
                                for msg in log_capture.output))


class MigLibEvents__legacy_main(MigTestCase):
    """Unit tests for legacy events self-checks"""

    def test_existing_main(self):
        def raise_on_error_exit(exit_code):
            if exit_code != 0:
                if raise_on_error_exit.last_print is not None:
                    identifying_message = raise_on_error_exit.last_print
                else:
                    identifying_message = 'unknown'
                raise AssertionError(
                    'failure in unittest/testcore: %s' % (identifying_message,))
        raise_on_error_exit.last_print = None

        def record_last_print(value):
            raise_on_error_exit.last_print = value

        events_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == '__main__':
    unittest.main()
