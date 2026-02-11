# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_lib_cron - unit tests for cron helper functions
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

"""Unit tests for cron helper functions"""

import datetime
import os
import shutil
import time
import unittest
from unittest.mock import patch, MagicMock

import mig.lib.cron
from mig.lib.cron import MiGCrontabEventHandler, parse_crontab, cron_match, \
    parse_atjobs, at_remain, monitor, run_handler, stop_handler, stop_running, \
    all_crontabs, all_atjobs, shared_state
from tests.support import MigTestCase, ensure_dirs_exist

DUMMY_USER_DN = '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/emailAddress=test@example.com'
DUMMY_FULL_NAME = "Test User"
DUMMY_ORGANIZATION = "Test Org"
DUMMY_EMAIL = "test@example.com"
DUMMY_SKIP_EMAIL = ''
DUMMY_CLIENT_DIR = '+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_User+emailAddress=test@example.com'
DUMMY_CRON_JOB = {'command': ['echo', 'test'], 'run_as': DUMMY_USER_DN,
                  # 'minute': '*', 'hour': '*', 'dayofmonth': '*', 'month': '*',
                  # 'dayofweek': '*'
                  }
DUMMY_CRONTAB_NAME = 'crontab'
DUMMY_ATJOBS_NAME = 'atjobs'
DUMMY_CRONTAB_CONTENT = """* * * * * /bin/test_command
30 2 * * * /usr/bin/another_command"""
DUMMY_ATJOBS_CONTENT = """2042-01-01 12:34:56 /bin/future_command"""


class MigLibCron(MigTestCase):
    """Unit tests for cron helper functions"""

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def before_each(self):
        """Set up test configuration and reset state before each test"""

        # Pass configuration and logger to cron module
        mig.lib.cron.configuration = self.configuration
        mig.lib.cron.logger = self.configuration.logger

        # Enable cron in configuration
        self.configuration.site_enable_crontab = True

        ensure_dirs_exist(self.configuration.user_db_home)
        ensure_dirs_exist(self.configuration.user_home)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.user_cache)
        ensure_dirs_exist(self.configuration.mig_system_files)

        # Prepare user DB with a single dummy user for all tests
        self._provision_test_user(self, DUMMY_USER_DN)

        # Clear global state
        global stop_running
        stop_running.clear()

    def test_stop_handler_signal(self):
        """Test stop_handler() sets global stop_running flag"""
        stop_handler(None, None)
        self.assertTrue(stop_running.is_set())

    def test_global_state_reset(self):
        """Test global stop_running is reset between tests"""
        global stop_running
        self.assertFalse(stop_running.is_set())

    def test_run_handler_valid_job(self):
        """Test run_handler creates worker for valid job and doesn't crash"""
        timestamp = datetime.datetime.now()
        caught = None
        try:
            run_handler(self.configuration, DUMMY_USER_DN, timestamp,
                        DUMMY_CRON_JOB)
        except Exception as exc:
            caught = exc
        self.assertEqual(caught, None)

    def test_parse_valid_crontab(self):
        """Test parsing of valid crontab content"""
        # Create dummy crontab file
        crontab_path = os.path.join(self.configuration.user_settings,
                                    DUMMY_CLIENT_DIR, DUMMY_CRONTAB_NAME)
        os.makedirs(os.path.dirname(crontab_path), exist_ok=True)
        with open(crontab_path, 'w') as f:
            f.write(DUMMY_CRONTAB_CONTENT)

        parsed = parse_crontab(self.configuration, DUMMY_USER_DN, crontab_path)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['command'], ['/bin/test_command'])

    def test_parse_empty_crontab(self):
        """Test handling of empty crontab file"""
        crontab_path = os.path.join(self.configuration.user_settings,
                                    DUMMY_CLIENT_DIR, DUMMY_CRONTAB_NAME)
        os.makedirs(os.path.dirname(crontab_path), exist_ok=True)
        open(crontab_path, 'a').close()  # Create empty file

        parsed = parse_crontab(self.configuration, DUMMY_USER_DN, crontab_path)
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
                    'day': '*', 'month': '*', 'dayofweek': '*',
                    'dayofmonth': '*'}
        self.assertFalse(cron_match(self.configuration, now, test_job))

    def test_event_handler_file_created(self):
        """Test event handler triggers on file creation"""
        handler = MiGCrontabEventHandler(patterns=['*%s' % DUMMY_CRONTAB_NAME])
        test_path = os.path.join(self.configuration.user_settings,
                                 DUMMY_CLIENT_DIR, DUMMY_CRONTAB_NAME)

        # Simulate file creation event
        handler.on_created(MagicMock(
            event_type='created',
            src_path=test_path,
            is_directory=False
        ))

        # Verify path was registered in global state
        self.assertIn(test_path, all_crontabs)

    def test_parse_atjobs_future_job(self):
        """Test parse_atjobs recognizes future jobs"""
        # Create dummy atjobs file
        atjobs_path = os.path.join(self.configuration.user_settings,
                                   DUMMY_CLIENT_DIR, DUMMY_ATJOBS_NAME)
        os.makedirs(os.path.dirname(atjobs_path), exist_ok=True)
        with open(atjobs_path, 'w') as f:
            f.write(DUMMY_ATJOBS_CONTENT)

        parsed = parse_atjobs(self.configuration, DUMMY_USER_DN, atjobs_path)
        self.assertEqual(len(parsed), 1)
        self.assertTrue(parsed[0]['time_stamp'] > datetime.datetime.now())


if __name__ == '__main__':
    unittest.main()
