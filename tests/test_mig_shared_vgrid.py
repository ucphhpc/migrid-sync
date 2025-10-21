# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_vgrid - unit tests for vgrid helper functions
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Unit tests for vgrid helper module"""

import os
import time
import unittest

from mig.shared.base import client_id_dir
from mig.shared.serial import dump
from mig.shared.vgrid import get_vgrid_workflow_jobs, legacy_main, \
    vgrid_add_entities, vgrid_add_members, vgrid_add_owners, \
    vgrid_add_workflow_jobs, vgrid_allow_restrict_write, vgrid_exists, \
    vgrid_is_default, vgrid_is_member, vgrid_is_owner, \
    vgrid_is_owner_or_member, vgrid_list, vgrid_list_parents, \
    vgrid_list_subvgrids, vgrid_list_vgrids, vgrid_match_resources, \
    vgrid_nest_sep, vgrid_remove_entities, vgrid_restrict_write, \
    vgrid_set_entities, vgrid_settings
from tests.support import MigTestCase, ensure_dirs_exist, testmain


class TestMigSharedVgrid(MigTestCase):
    """Unit tests for vgrid helpers"""
    # Standard user IDs following X.500 DN format
    TEST_OWNER_DN = \
        '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test Owner/'\
        'emailAddress=owner@example.com'
    TEST_MEMBER_DN = \
        '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test Member/'\
        'emailAddress=member@example.com'
    TEST_OUTSIDER_DN = \
        '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test Outsider/'\
        'emailAddress=outsider@example.com'
    TEST_RESOURCE_DN = 'test.example.org'
    TEST_OWNER_DIR = \
        '+C=DK+ST=NA+L=NA+O=Test_Org+OU=NA+CN=Test_Owner+'\
        'emailAddress=owner@example.com'
    TEST_JOB_ID = '12345667890'

    def _provide_configuration(self):
        """Return configuration to use"""
        return 'testconfig'

    def before_each(self):
        """Create test environment for vgrid tests"""

        # Setup configuration
        ensure_dirs_exist(self.configuration.vgrid_home)
        ensure_dirs_exist(self.configuration.vgrid_files_home)
        ensure_dirs_exist(self.configuration.vgrid_files_writable)
        ensure_dirs_exist(self.configuration.vgrid_files_readonly)
        ensure_dirs_exist(self.configuration.mrsl_files_dir)
        ensure_dirs_exist(self.configuration.workflows_home)
        ensure_dirs_exist(self.configuration.workflows_db_home)
        self.configuration.site_vgrid_label = 'VGridLabel'
        self.configuration.vgrid_owners = 'owners.pck'
        self.configuration.vgrid_members = 'members.pck'
        self.configuration.vgrid_resources = 'resources.pck'
        self.configuration.vgrid_settings = 'settings.pck'
        self.configuration.vgrid_workflow_job_queue = 'jobqueue.pck'
        self.configuration.site_enable_workflows = True

        # Default vgrid for comparison
        self.default_vgrid = 'Generic'

        # Create test vgrid structure using ensure_dirs_exist
        self.test_vgrid = 'testvgrid'
        self.test_vgrid_path = os.path.join(
            self.configuration.vgrid_home, self.test_vgrid)
        ensure_dirs_exist(self.test_vgrid_path)
        vgrid_add_owners(self.configuration, self.test_vgrid,
                         [self.TEST_OWNER_DN])
        vgrid_add_members(self.configuration, self.test_vgrid, [])

        # Nested sub-VGrid
        self.test_subvgrid = os.path.join(self.test_vgrid, 'subvgrid')
        self.test_subvgrid_path = os.path.join(
            self.configuration.vgrid_home, self.test_subvgrid)
        ensure_dirs_exist(self.test_subvgrid_path)
        vgrid_add_owners(self.configuration, self.test_vgrid, [])
        vgrid_add_members(self.configuration, self.test_vgrid, [])
        vgrid_add_workflow_jobs(self.configuration, self.test_vgrid, [])

    def test_vgrid_is_default(self):
        """Test default vgrid detection"""
        # Positive case
        self.assertTrue(vgrid_is_default('Generic'))
        self.assertTrue(vgrid_is_default(None))
        self.assertTrue(vgrid_is_default(''))

        # Negative cases
        self.assertFalse(vgrid_is_default(self.test_vgrid))
        self.assertFalse(vgrid_is_default(self.test_subvgrid))
        self.assertFalse(vgrid_is_default('MiG'))

    def test_vgrid_exists(self):
        """Test vgrid existence checks"""
        # Existing vgrid
        self.assertTrue(vgrid_exists(self.configuration, 'Generic'))
        self.assertTrue(vgrid_exists(self.configuration, None))
        self.assertTrue(vgrid_exists(self.configuration, ''))
        self.assertTrue(vgrid_exists(self.configuration, self.test_vgrid))
        self.assertTrue(vgrid_exists(self.configuration, self.test_subvgrid))

        # Non-existent vgrid
        self.assertFalse(vgrid_exists(self.configuration, 'no_such_vgrid'))
        self.assertFalse(vgrid_exists(self.configuration, 'no_such_vgrid/sub'))

        # Parent exists but not child - yet, vgrid_exists defaults to recursive
        # and allow_missing so it will return True for ALL subvgrids of vgrids.
        missing_child = os.path.join(self.test_subvgrid, 'missing_child')
        self.assertTrue(vgrid_exists(self.configuration, missing_child))

    def test_vgrid_list_vgrids(self):
        """Test vgrid listing with various scopes"""
        # Default include
        status, all_vgrids = vgrid_list_vgrids(self.configuration)
        self.assertTrue(status)
        self.assertIn(self.default_vgrid, all_vgrids)
        self.assertIn(self.test_vgrid, all_vgrids)
        self.assertIn(self.test_subvgrid, all_vgrids)

        # Exclude default
        status, no_default = vgrid_list_vgrids(self.configuration,
                                               include_default=False)
        self.assertTrue(status)
        self.assertNotIn(self.default_vgrid, no_default)
        self.assertIn(self.test_vgrid, no_default)

        # Root filtering
        status, root_vgrids = vgrid_list_vgrids(self.configuration,
                                                root_vgrid=self.test_vgrid)
        self.assertTrue(status)
        self.assertIn(self.test_subvgrid, root_vgrids)
        self.assertNotIn(self.test_vgrid, root_vgrids)

    def test_vgrid_add_remove_entities(self):
        """Test entity management in vgrid"""
        # Test adding owner
        added, msg = vgrid_add_entities(self.configuration, self.test_vgrid,
                                        'owners', [self.TEST_OWNER_DN])
        self.assertTrue(added, msg)
        time.sleep(0.1)  # Ensure timestamp changes

        # Verify existence
        self.assertTrue(vgrid_is_owner(self.test_vgrid, self.TEST_OWNER_DN,
                                       self.configuration))

        # Test removal without and with allow empty in turn
        removed, msg = vgrid_remove_entities(self.configuration, self.test_vgrid,
                                             'owners', [self.TEST_OWNER_DN], False)
        self.assertFalse(removed, msg)
        self.assertTrue(vgrid_is_owner(self.test_vgrid, self.TEST_OWNER_DN,
                                       self.configuration))
        removed, msg = vgrid_remove_entities(self.configuration, self.test_vgrid,
                                             'owners', [self.TEST_OWNER_DN], True)
        self.assertTrue(removed, msg)
        self.assertFalse(vgrid_is_owner(self.test_vgrid, self.TEST_OWNER_DN,
                                        self.configuration))

    def test_vgrid_settings_inheritance(self):
        """Test vgrid setting inheritance"""
        # Parent settings
        parent_settings = [('vgrid_name', self.test_vgrid),
                           ('write_shared_files', 'None')]
        added, msg = vgrid_add_entities(self.configuration, self.test_vgrid,
                                        'settings', parent_settings)
        self.assertTrue(added, msg)

        # Verify inheritance
        status, settings = vgrid_settings(self.test_subvgrid, self.configuration,
                                          recursive=True, as_dict=True)
        self.assertTrue(status)
        self.assertEqual(settings.get('write_shared_files'), 'None')

    def test_vgrid_permission_checks(self):
        """Test owner/member permission verification"""
        # Setup owners and members
        added, msg = vgrid_add_entities(self.configuration, self.test_vgrid,
                                        'owners', [self.TEST_OWNER_DN])
        self.assertTrue(added, msg)
        time.sleep(0.1)
        added, msg = vgrid_add_entities(self.configuration, self.test_vgrid,
                                        'members', [self.TEST_MEMBER_DN])
        self.assertTrue(added, msg)
        time.sleep(0.1)

        # Verify owner permissions
        self.assertTrue(vgrid_is_owner(self.test_vgrid, self.TEST_OWNER_DN,
                                       self.configuration))
        self.assertTrue(vgrid_is_owner_or_member(self.test_vgrid, self.TEST_OWNER_DN,
                                                 self.configuration))

        # Verify member permissions
        self.assertTrue(vgrid_is_member(self.test_vgrid, self.TEST_MEMBER_DN,
                                        self.configuration))
        self.assertTrue(vgrid_is_owner_or_member(self.test_vgrid, self.TEST_MEMBER_DN,
                                                 self.configuration))

        # Verify non-member
        self.assertFalse(vgrid_is_owner_or_member(self.test_vgrid, self.TEST_OUTSIDER_DN,
                                                  self.configuration))

    def test_workflow_job_management(self):
        """Test workflow job queue handling"""
        job_entry = {
            'client_id': self.TEST_OWNER_DN,
            'job_id': self.TEST_JOB_ID
        }
        job_dir = os.path.join(self.configuration.mrsl_files_dir,
                               self.TEST_OWNER_DIR)
        ensure_dirs_exist(job_dir)
        job_path = os.path.join(job_dir, '%s.mRSL' % self.TEST_JOB_ID)
        dump({'job_id': self.TEST_JOB_ID, 'EXECUTE': 'uptime'}, job_path)

        # Add job
        status, msg = vgrid_add_entities(self.configuration, self.test_vgrid,
                                         'jobqueue', [job_entry])
        self.assertTrue(status, msg)

        # TODO: adjust function to consistent return API? tuple vs list now.
        # List jobs
        result = get_vgrid_workflow_jobs(self.configuration,
                                         self.test_vgrid, True)
        if isinstance(result, tuple):
            status, msg = result
            jobs = []
        else:
            status, msg = True, ''
            jobs = result
        self.assertTrue(status)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['job_id'], self.TEST_JOB_ID)

        # TODO: adjust function to consistent return API? tuple vs list now.
        # Remove job
        result = vgrid_remove_entities(self.configuration, self.test_vgrid,
                                       'jobqueue', [job_entry], True)
        if isinstance(result, tuple):
            status, msg = result
            jobs = []
        else:
            status, msg = True, ''
            jobs = result
        self.assertTrue(status, msg)

        # TODO: adjust function to consistent return API? tuple vs list now.
        # Verify removal
        result = get_vgrid_workflow_jobs(self.configuration,
                                         self.test_vgrid, True)
        if isinstance(result, tuple):
            status, msg = result
            jobs = []
        else:
            status, msg = True, ''
            jobs = result
        self.assertTrue(status)
        self.assertEqual(len(jobs), 0)

    def test_vgrid_list_subvgrids(self):
        """Test retrieving subvgrids of given vgrid"""
        status, subvgrids = vgrid_list_subvgrids(self.test_vgrid,
                                                 self.configuration)
        self.assertTrue(status)
        self.assertEqual(subvgrids, [self.test_subvgrid])

    def test_vgrid_list_parents(self):
        """Test listing parent vgrids (root first)"""
        parents = vgrid_list_parents(self.test_subvgrid, self.configuration)
        expected = [self.test_vgrid]
        self.assertEqual(parents, expected)

    def test_vgrid_match_resources(self):
        """Test resource filtering for vgrid"""
        test_resources = ['res1', 'res2', 'invalid_res', self.TEST_RESOURCE_DN]
        added, msg = vgrid_add_entities(self.configuration, self.test_vgrid,
                                        'resources', [self.TEST_RESOURCE_DN])
        self.assertTrue(added, msg)

        matched = vgrid_match_resources(self.test_vgrid, test_resources,
                                        self.configuration)
        self.assertEqual(matched, [self.TEST_RESOURCE_DN])

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires read-only mount")
    def test_vgrid_allow_restrict_write(self):
        """Test write restriction validation logic"""
        # Create parent-child structure
        parent_write_setting = [('write_shared_files', 'none')]
        added, msg = vgrid_add_entities(self.configuration, self.test_vgrid,
                                        'settings', parent_write_setting)
        self.assertTrue(added, msg)

        # Child tries to set write_shared_files to "members"
        result = vgrid_allow_restrict_write(self.test_subvgrid, 'members',
                                            self.configuration,
                                            auto_migrate=True)
        self.assertFalse(result)

        # Valid case: parent allows writes, child sets to "none"
        parent_write_setting = [('write_shared_files', 'members')]
        vgrid_set_entities(self.configuration, self.test_vgrid,
                           'settings', parent_write_setting, True)

        result = vgrid_allow_restrict_write(self.test_subvgrid, 'none',
                                            self.configuration,
                                            auto_migrate=True)
        self.assertTrue(result)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires read-only mount")
    def test_vgrid_restrict_write(self):
        """Test write restriction enforcement"""
        # Setup test share
        test_share = os.path.join(self.configuration.vgrid_files_home,
                                  self.test_vgrid)
        ensure_dirs_exist(test_share)

        # Migrate to restricted mode
        result = vgrid_restrict_write(self.test_vgrid, 'none',
                                      self.configuration, auto_migrate=True)
        self.assertTrue(result)

        # Verify symlink points to readonly
        flat_vgrid = self.test_vgrid.replace('/', vgrid_nest_sep)
        read_path = os.path.join(self.configuration.vgrid_files_readonly,
                                 flat_vgrid)
        self.assertEqual(os.path.realpath(test_share),
                         os.path.realpath(read_path))

    def test_vgrid_settings_scopes(self):
        """Test different vgrid settings lookup scopes"""
        # Local settings only
        local_settings = [('vgrid_name', self.test_subvgrid),
                          ('description', 'test subvgrid'),
                          ('write_shared_files', 'members'),
                          ]
        added, msg = vgrid_add_entities(self.configuration, self.test_subvgrid,
                                        'settings', local_settings)
        self.assertTrue(added, msg)

        # Check recursive vs direct
        status, recursive_settings = vgrid_settings(
            self.test_subvgrid, self.configuration, recursive=True, as_dict=True)
        self.assertTrue(status)
        status, direct_settings = vgrid_settings(
            self.test_subvgrid, self.configuration, recursive=False, as_dict=True)
        self.assertTrue(status)
        self.assertEqual(direct_settings['description'], 'test subvgrid')
        self.assertIn('write_shared_files', recursive_settings)  # Inherited

    def test_vgrid_add_owner_rank(self):
        """Test owner ranking/ordering functionality"""
        new_owner = '/C=DK/CN=New Owner'
        added, msg = vgrid_add_owners(
            self.configuration,
            self.test_vgrid,
            [new_owner],
            rank=0  # Add as first owner
        )
        self.assertTrue(added, msg)

        owners = vgrid_list(self.test_vgrid, 'owners', self.configuration)[1]
        self.assertEqual(owners[0], new_owner)

    # TODO: adjust API to allow enabling the next test
    @unittest.skipIf(True, "requires tweaking of funcion")
    def test_workflow_job_priority(self):
        """Test workflow job queue ordering and limits"""
        # Create max jobs + 1
        job_entries = [
            {'client_id': self.TEST_OWNER_DN, 'job_id': str(i)}
            for i in range(101)
        ]
        added, msg = vgrid_add_workflow_jobs(
            self.configuration,
            self.test_vgrid,
            job_entries
        )
        self.assertTrue(added, msg)

        status, jobs = vgrid_list(
            self.test_vgrid, 'jobqueue', self.configuration)
        self.assertTrue(status)
        # Should stay at max 100 by removing oldest
        self.assertEqual(len(jobs), 100)
        self.assertEqual(jobs[-1]['job_id'], '100')  # Newest at end


class TestMigSharedVgrid__main(MigTestCase):
    """Unit tests for vgrid self-checks"""

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

        legacy_main(_exit=raise_on_error_exit, _print=record_last_print)


if __name__ == '__main__':
    testmain()
