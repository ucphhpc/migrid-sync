# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_vgridaccess - unit tests for vgridaccess helper functions
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Unit tests for vgridaccess helper module"""

import os
import time
import unittest

from mig.shared.fileio import pickle, read_file
from mig.shared.vgrid import vgrid_list, vgrid_set_entities, vgrid_settings
from mig.shared.vgridaccess import CONF, MEMBERS, OWNERS, RESOURCES, SETTINGS, \
    USERID, VGRIDS, check_vgrid_access, check_vgrids_modified, \
    force_update_resource_map, force_update_user_map, force_update_vgrid_map, \
    get_re_provider_map, get_resource_map, get_user_map, get_vgrid_map, \
    load_resource_map, refresh_vgrid_map, resources_using_re, unmap_vgrid, \
    user_vgrid_access, vgrid_inherit_map
from tests.support import MigTestCase, ensure_dirs_exist, testmain


class TestMigSharedVgridAccess(MigTestCase):
    """Unit tests for vgridaccess related helper functions"""

    TEST_USER_DN = \
        '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test User/'\
        'emailAddress=test@example.com'
    TEST_OWNER_DN = \
        '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test Owner/'\
        'emailAddress=owner@example.org'
    TEST_MEMBER_DN = \
        '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test Member/'\
        'emailAddress=member@example.org'
    TEST_OUTSIDER_DN = \
        '/C=DK/ST=NA/L=NA/O=Test Org/OU=NA/CN=Test Outsider/'\
        'emailAddress=outsider@example.com'
    TEST_RESOURCE_ID = 'test.example.org.0'

    TEST_OWNER_UUID = 'ff326a2b984828d9b32077c9b0b35a05'
    TEST_USER_UUID = '707a2213995b4fb385793b5a7cb82a18'
    TEST_RESOURCE_ALIAS = '0835f310d6422c36e33eeb7d0d3e9cf5'

    def _provide_configuration(self):
        """Prepare isolated test config"""
        return 'testconfig'

    def _create_vgrid(self, vgrid_name, owners=None, members=None,
                      resources=None, settings=None):
        """Helper to create valid skeleton vgrid for testing"""
        vgrid_path = os.path.join(self.configuration.vgrid_home, vgrid_name)
        ensure_dirs_exist(vgrid_path)
        if owners is None:
            owners = []
        # Add vgrid owners
        status, msg = vgrid_set_entities(self.configuration, vgrid_name,
                                         'owners', owners, allow_empty=True)
        self.assertTrue(status, msg)
        if members is not None:
            status, msg = vgrid_set_entities(self.configuration, vgrid_name,
                                             'members', members,
                                             allow_empty=False)
            self.assertTrue(status, msg)
        if resources is not None:
            status, msg = vgrid_set_entities(self.configuration, vgrid_name,
                                             'resources', resources,
                                             allow_empty=False)
            self.assertTrue(status, msg)
        if settings is not None:
            status, msg = vgrid_set_entities(self.configuration, vgrid_name,
                                             'settings', settings,
                                             allow_empty=False)
            self.assertTrue(status, msg)

    def _create_resource(self, res_name, owners, config=None):
        """Helper to create valid skeleton resource for testing"""
        res_path = os.path.join(self.configuration.resource_home, res_name)
        res_owners_path = os.path.join(res_path, 'owners')
        res_config_path = os.path.join(res_path, 'config')
        # Add resource skeleton with owners
        ensure_dirs_exist(res_path)
        if owners is None:
            owners = []
        saved = pickle(owners, res_owners_path, self.logger)
        self.assertTrue(saved)
        if config is None:
            config = {}
        saved = pickle(config, res_config_path, self.logger)
        self.assertTrue(saved)

    def before_each(self):
        """Create test environment for vgridaccess tests"""
        self._provision_test_user(self, self.TEST_OWNER_DN)
        ensure_dirs_exist(self.configuration.mig_system_files)
        ensure_dirs_exist(self.configuration.mig_system_run)
        ensure_dirs_exist(self.configuration.user_home)
        ensure_dirs_exist(self.configuration.user_settings)
        ensure_dirs_exist(self.configuration.vgrid_home)
        ensure_dirs_exist(self.configuration.resource_home)
        # Start with empty maps
        force_update_vgrid_map(self.configuration, clean=True)
        force_update_user_map(self.configuration, clean=True)
        force_update_resource_map(self.configuration, clean=True)

        self.test_vgrid = 'testvgrid'

    def test_vgrid_map_refresh(self):
        """Verify vgrid map refresh captures changes"""
        # We always init empty maps
        initial_map = get_vgrid_map(self.configuration, recursive=False)
        self.assertFalse(self.test_vgrid in initial_map.get(VGRIDS, {}))

        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        # Force refresh map
        updated_map = force_update_vgrid_map(self.configuration)
        vgrids = updated_map.get(VGRIDS, {})
        self.assertTrue(self.test_vgrid in vgrids)
        self.assertEqual(vgrids[self.test_vgrid]
                         [OWNERS], [self.TEST_OWNER_DN])

    def test_user_map_access(self):
        """Test user permissions through cached access maps"""
        # Add user as member
        self._create_vgrid(self.test_vgrid, owners=[self.TEST_OWNER_DN],
                           members=[self.TEST_MEMBER_DN])
        force_update_vgrid_map(self.configuration)
        # Verify member access
        allowed = check_vgrid_access(self.configuration, self.TEST_MEMBER_DN,
                                     self.test_vgrid)
        self.assertTrue(allowed)

    def test_resource_map_update(self):
        """Verify resource visibility in cache"""
        # Check cached resource map does not yet contain entry
        cached_map, map_stamp = load_resource_map(self.configuration,
                                                  caching=True)
        self.assertFalse(cached_map, map_stamp)
        self.assertFalse(self.TEST_RESOURCE_ID in cached_map)

        # Add vgrid with assigned resource
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, owners=[self.TEST_OWNER_DN],
                           resources=[self.TEST_RESOURCE_ID])
        updated_vgrid_map = force_update_vgrid_map(self.configuration,
                                                   clean=True)
        # Check vgrid map contains resource entry
        vgrid_data = updated_vgrid_map.get(VGRIDS, {})
        top_vgrid_data = vgrid_data.get(self.test_vgrid, {})
        top_vgrid_res = top_vgrid_data.get(RESOURCES, [])
        self.assertTrue(self.TEST_RESOURCE_ID in top_vgrid_res)

        # Check resource map contains resource entry
        updated_res_map = force_update_resource_map(self.configuration,
                                                    clean=True)
        # Check resource map contains entry
        self.assertTrue(self.TEST_RESOURCE_ID in updated_res_map)

    def test_settings_inheritance(self):
        """Test inherited settings propagation through cached maps"""
        # Create top and sub vgrids with 'hidden' setting on top vgrid
        top_settings = [('vgrid_name', self.test_vgrid),
                        ('hidden', True)]
        self._create_vgrid(self.test_vgrid, owners=[self.TEST_OWNER_DN],
                           settings=top_settings)
        sub_vgrid = os.path.join(self.test_vgrid, 'subvgrid')
        self._create_vgrid(sub_vgrid)

        # Force refresh of cached map
        updated_map = force_update_vgrid_map(self.configuration)

        # Retrieve vgrid data from cached map
        vgrid_data = updated_map.get(VGRIDS, {})
        self.assertTrue(vgrid_data)

        # Retrieve top vgrid settings from cached map
        top_vgrid_data = vgrid_data.get(self.test_vgrid, {})
        self.assertTrue(top_vgrid_data)
        # Convert settings list of tuples to dict
        top_settings_dict = dict(top_vgrid_data.get(SETTINGS, []))
        self.assertTrue(top_settings_dict)

        # Verify hidden setting in cache
        self.assertEqual(top_settings_dict.get('hidden'), True)

        # Retrieve sub vgrid settings from cached map
        sub_vgrid_data = vgrid_data.get(sub_vgrid, {})
        # Convert settings list of tuples to dict
        sub_settings_dict = dict(sub_vgrid_data.get(SETTINGS, []))

        # Verify hidden setting unset without inheritance
        self.assertFalse(sub_settings_dict.get('hidden'))

        inherited_map = vgrid_inherit_map(self.configuration, updated_map)
        vgrid_data = inherited_map.get(VGRIDS, {})
        self.assertTrue(vgrid_data)

        # Retrieve sub vgrid settings from cached map
        sub_vgrid_data = vgrid_data.get(sub_vgrid, {})
        # Convert settings list of tuples to dict
        sub_settings_dict = dict(sub_vgrid_data.get(SETTINGS, []))

        # Verify hidden setting inheritance
        self.assertEqual(sub_settings_dict.get('hidden'), True)

    def test_user_map_fields(self):
        """Verify user map includes complete profile/settings data"""
        # First add a couple of test users
        self._provision_test_user(self, self.TEST_OWNER_DN)
        self._provision_test_user(self, self.TEST_USER_DN)
        # Force fresh user map
        initial_vgrid_map = force_update_vgrid_map(self.configuration,
                                                   clean=True)
        user_map = force_update_user_map(self.configuration)
        test_owner = user_map.get(self.TEST_OWNER_DN, {})
        self.assertEqual(test_owner.get(USERID), self.TEST_OWNER_UUID)
        self.assertTrue(isinstance(test_owner.get(CONF), dict))
        test_user = user_map.get(self.TEST_USER_DN, {})
        self.assertEqual(test_user.get(USERID), self.TEST_USER_UUID)
        self.assertTrue(isinstance(test_user.get(CONF), dict))

    def test_resource_revoked_access(self):
        """Verify resource removal propagates through cached maps"""
        # First add resource and vgrid
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, owners=[self.TEST_OWNER_DN],
                           resources=[self.TEST_RESOURCE_ID])

        initial_vgrid_map = force_update_vgrid_map(self.configuration,
                                                   clean=True)
        # Check vgrid map contains resource entry
        vgrid_data = initial_vgrid_map.get(VGRIDS, {})
        top_vgrid_data = vgrid_data.get(self.test_vgrid, {})
        top_vgrid_res = top_vgrid_data.get(RESOURCES, [])
        self.assertTrue(self.TEST_RESOURCE_ID in top_vgrid_res)

        # Check resource map contains resource entry
        initial_map = force_update_resource_map(self.configuration,
                                                clean=True)
        self.assertIn(self.TEST_RESOURCE_ID, initial_map)

        # Remove resource assignment from vgrid
        status, msg = vgrid_set_entities(self.configuration, self.test_vgrid,
                                         'resources', [], allow_empty=True)
        self.assertTrue(status, msg)

        updated_vgrid_map = force_update_vgrid_map(self.configuration,
                                                   clean=True)
        # Check vgrid map no longer contains resource entry
        vgrid_data = updated_vgrid_map.get(VGRIDS, {})
        top_vgrid_data = vgrid_data.get(self.test_vgrid, {})
        top_vgrid_res = top_vgrid_data.get(RESOURCES, [])
        self.assertFalse(self.TEST_RESOURCE_ID in top_vgrid_res)

        # Verify resource still in resource map
        updated_map = force_update_resource_map(self.configuration,
                                                clean=True)
        self.assertIn(self.TEST_RESOURCE_ID, updated_map)

    def test_non_recursive_inheritance(self):
        """Verify non-recursive map excludes nested vgrids"""
        # Create parent+child vgrids
        parent_vgrid = 'parent'
        self._create_vgrid(parent_vgrid, [self.TEST_OWNER_DN])
        child_vgrid = os.path.join(parent_vgrid, 'child')
        self._create_vgrid(child_vgrid, None, [self.TEST_MEMBER_DN])

        # Force update to avoid auto caching and get non-recursive map
        vgrid_map = force_update_vgrid_map(self.configuration,
                                           clean=True)
        vgrid_map = get_vgrid_map(self.configuration, recursive=False)
        # Parent should appear
        self.assertIn(parent_vgrid, vgrid_map.get(VGRIDS, {}))
        # Child should still appear when non-recursive but just not inherit
        self.assertIn(child_vgrid, vgrid_map.get(VGRIDS, {}))
        # Check owners and members to verify they aren't inherited
        self.assertEqual(vgrid_map[VGRIDS][parent_vgrid][OWNERS],
                         [self.TEST_OWNER_DN])
        self.assertEqual(len(vgrid_map[VGRIDS][parent_vgrid][MEMBERS]), 0)
        self.assertEqual(len(vgrid_map[VGRIDS][child_vgrid][OWNERS]), 0)
        self.assertEqual(vgrid_map[VGRIDS][child_vgrid][MEMBERS],
                         [self.TEST_MEMBER_DN])

    def test_hidden_setting_propagation(self):
        """Verify hidden=True propagates to not infect parent settings"""
        parent_vgrid = 'parent'
        self._create_vgrid(parent_vgrid, [self.TEST_OWNER_DN])
        child_vgrid = os.path.join(parent_vgrid, 'child')
        self._create_vgrid(child_vgrid, [self.TEST_OWNER_DN],
                           settings=[('vgrid_name', child_vgrid),
                                     ('hidden', True)])

        # Verify parent remains visible in cache
        updated_map = force_update_vgrid_map(self.configuration)
        parent_data = updated_map.get(VGRIDS, {}).get(parent_vgrid, {})
        parent_settings = dict(parent_data.get(SETTINGS, []))
        self.assertNotEqual(parent_settings.get('hidden'), True)

    def test_default_vgrid_access(self):
        """Verify special access rules for default vgrid"""
        self._create_vgrid(self.test_vgrid, owners=[self.TEST_OWNER_DN],
                           members=[self.TEST_MEMBER_DN])

        initial_vgrid_map = force_update_vgrid_map(self.configuration,
                                                   clean=True)

        # Even non-member should have access to default vgrid
        participant = check_vgrid_access(self.configuration,
                                         self.TEST_OUTSIDER_DN,
                                         'Generic')
        self.assertFalse(participant)
        allowed_vgrids = user_vgrid_access(self.configuration,
                                           self.TEST_OUTSIDER_DN)
        self.assertTrue('Generic' in allowed_vgrids)

        # Invalid vgrid should not allow any participation or access
        participant = check_vgrid_access(self.configuration, self.TEST_MEMBER_DN,
                                         'invalid-vgrid-name')
        self.assertFalse(participant)
        allowed_vgrids = user_vgrid_access(self.configuration,
                                           self.TEST_MEMBER_DN)
        self.assertFalse('invalid-vgrid-name' in allowed_vgrids)

    def test_general_vgrid_access(self):
        """Verify general access rules for vgrids"""
        self._create_vgrid(self.test_vgrid, owners=[self.TEST_OWNER_DN],
                           members=[self.TEST_MEMBER_DN])

        initial_vgrid_map = force_update_vgrid_map(self.configuration,
                                                   clean=True)

        # Test vgrid must allow owner and members access
        allowed = check_vgrid_access(self.configuration, self.TEST_OWNER_DN,
                                     self.test_vgrid)
        self.assertTrue(allowed)
        allowed_vgrids = user_vgrid_access(self.configuration,
                                           self.TEST_OWNER_DN)
        self.assertTrue(self.test_vgrid in allowed_vgrids)

        allowed = check_vgrid_access(self.configuration, self.TEST_MEMBER_DN,
                                     self.test_vgrid)
        self.assertTrue(allowed)
        allowed_vgrids = user_vgrid_access(self.configuration,
                                           self.TEST_MEMBER_DN)
        self.assertTrue(self.test_vgrid in allowed_vgrids)

        # Test vgrid must reject allow outsider access
        allowed = check_vgrid_access(self.configuration, self.TEST_OUTSIDER_DN,
                                     self.test_vgrid)
        self.assertFalse(allowed)
        allowed_vgrids = user_vgrid_access(self.configuration,
                                           self.TEST_OUTSIDER_DN)
        self.assertFalse(self.test_vgrid in allowed_vgrids)

    def test_get_re_provider_map(self):
        """Test RE provider map includes test resource"""
        test_re = 'Python'
        res_config = {'RUNTIMEENVIRONMENT': [(test_re, '/python/path')]}
        self._create_resource(self.TEST_RESOURCE_ID, [
                              self.TEST_OWNER_DN], res_config)

        # Update maps to include new resource
        force_update_resource_map(self.configuration)

        # Verify RE appears in provider mapping
        re_map = get_re_provider_map(self.configuration)
        self.assertIn(test_re, re_map)
        self.assertIn(self.TEST_RESOURCE_ALIAS, re_map[test_re])

    def test_resources_using_re(self):
        """Test finding resources with specific runtime environment"""
        test_re = 'Bash'
        res_config = {'RUNTIMEENVIRONMENT': [(test_re, '/bash/path')]}
        self._create_resource(self.TEST_RESOURCE_ID, [
                              self.TEST_OWNER_DN], res_config)

        # Refresh resource map
        force_update_resource_map(self.configuration)

        # Verify resource appears in RE-specific results
        res_list = resources_using_re(self.configuration, test_re)
        self.assertIn(self.TEST_RESOURCE_ALIAS, res_list)

    def test_unmap_vgrid(self):
        """Verify unmapping marks vgrid modified for update in cached data"""
        mod_list, mod_stamp = check_vgrids_modified(self.configuration)
        self.assertNotIn(self.test_vgrid, mod_list)

        # Unmap and verify mark modified
        unmap_vgrid(self.configuration, self.test_vgrid)

        mod_list, mod_stamp = check_vgrids_modified(self.configuration)
        self.assertIn(self.test_vgrid, mod_list)

    def test_access_nonexistent_vgrid(self):
        """Ensure checks fail cleanly for non-existent vgrid"""
        allowed = check_vgrid_access(self.configuration, self.TEST_MEMBER_DN,
                                     'no-such-vgrid')
        self.assertFalse(allowed)

        # Should not appear in allowed vgrids
        allowed_vgrids = user_vgrid_access(
            self.configuration, self.TEST_MEMBER_DN)
        self.assertFalse('no-such-vgrid' in allowed_vgrids)

    def test_empty_member_access(self):
        """Verify members-only vgrid rejects outsiders"""
        self._create_vgrid(self.test_vgrid, [], [self.TEST_MEMBER_DN])
        force_update_vgrid_map(self.configuration)

        # Outsider should be blocked despite no owners
        allowed = check_vgrid_access(self.configuration, self.TEST_OUTSIDER_DN,
                                     self.test_vgrid)
        self.assertFalse(allowed)


if __name__ == '__main__':
    testmain()
