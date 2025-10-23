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
    USERID, VGRIDS, check_resources_modified, check_vgrid_access, \
    check_vgrids_modified, fill_placeholder_cache, force_update_resource_map, \
    force_update_user_map, force_update_vgrid_map, get_re_provider_map, \
    get_resource_map, get_user_map, get_vgrid_map, get_vgrid_map_vgrids, \
    is_vgrid_parent_placeholder, load_resource_map, load_user_map, \
    load_vgrid_map, mark_vgrid_modified, refresh_resource_map, \
    refresh_user_map, refresh_vgrid_map, res_vgrid_access, \
    reset_resources_modified, reset_vgrids_modified, resources_using_re, \
    unmap_inheritance, unmap_resource, unmap_vgrid, user_allowed_res_confs, \
    user_allowed_res_exes, user_allowed_res_stores, user_allowed_res_units, \
    user_allowed_user_confs, user_owned_res_exes, user_owned_res_stores, \
    user_vgrid_access, user_visible_res_confs, user_visible_res_exes, \
    user_visible_res_stores, user_visible_user_confs, vgrid_inherit_map
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
            # Make sure conf has one valid field
            config = {'HOSTURL': res_name,
                      'EXECONFIG': [{'name': 'exe', 'vgrid': ['Generic']}],
                      'STORECONFIG': [{'name': 'exe', 'vgrid': ['Generic']}]
                      }
        saved = pickle(config, res_config_path, self.logger)
        self.assertTrue(saved)

    def before_each(self):
        """Create test environment for vgridaccess tests"""
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

    def test_force_update_user_map(self):
        """Simple test that user map refresh completes"""
        user_map_before = get_user_map(self.configuration)
        self.assertFalse(user_map_before)
        self._provision_test_user(self, self.TEST_USER_DN)
        updated_users = force_update_user_map(self.configuration)
        self.assertTrue(updated_users)
        self.assertNotEqual(user_map_before, updated_users)

    def test_force_update_resource_map(self):
        """Simple test that resource map refresh completes"""
        res_map_before = get_resource_map(self.configuration)
        self.assertFalse(res_map_before)
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        updated_res = force_update_resource_map(self.configuration)
        self.assertTrue(updated_res)
        self.assertNotEqual(len(res_map_before), len(updated_res))

    def test_force_update_vgrid_map(self):
        """Simple test that vgrid map refresh completes"""
        # Only (implicit) default vgrid in vgrid map before init
        vgrid_map_before = get_vgrid_map(self.configuration)
        self.assertEqual(len(vgrid_map_before.get(VGRIDS, [])), 1)
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        updated_vgrid = force_update_vgrid_map(self.configuration)
        self.assertTrue(updated_vgrid)
        self.assertNotEqual(len(vgrid_map_before.get(VGRIDS, [])),
                            len(updated_vgrid.get(VGRIDS, [])))

    def test_refresh_user_map(self):
        """Minimal test for user map refresh functionality"""
        self._provision_test_user(self, self.TEST_USER_DN)
        user_map = refresh_user_map(self.configuration)
        self.assertIn(self.TEST_USER_DN, user_map)

    def test_refresh_resource_map(self):
        """Minimal test for resource map refresh functionality"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        res_map = refresh_resource_map(self.configuration)
        self.assertIn(self.TEST_RESOURCE_ID, res_map)

    def test_refresh_vgrid_map(self):
        """Minimal test for vgrid map refresh functionality"""
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        vgrid_map = refresh_vgrid_map(self.configuration)
        self.assertIn(self.test_vgrid, vgrid_map.get(VGRIDS, []))

    def test_get_user_map(self):
        """Minimal test for user map refresh functionality"""
        self._provision_test_user(self, self.TEST_USER_DN)
        force_update_user_map(self.configuration)
        user_map = get_user_map(self.configuration)
        self.assertIn(self.TEST_USER_DN, user_map)

    def test_get_resource_map(self):
        """Minimal test for user map refresh functionality"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        force_update_resource_map(self.configuration)
        resource_map = get_resource_map(self.configuration)
        self.assertIn(self.TEST_RESOURCE_ID, resource_map)

    def test_get_vgrid_map(self):
        """Minimal test for user map refresh functionality"""
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        force_update_vgrid_map(self.configuration)
        vgrid_map = get_vgrid_map(self.configuration)
        self.assertIn(self.test_vgrid, vgrid_map.get(VGRIDS, []))

    def test_load_user_map(self):
        """Basic test for direct user map loading"""
        # Get empty map initially
        user_map, map_stamp = load_user_map(self.configuration)
        self.assertEqual(user_map, {})
        # Add test user
        self._provision_test_user(self, self.TEST_USER_DN)
        force_update_user_map(self.configuration)
        # Verify updated map contains user
        updated_map, updated_stamp = load_user_map(self.configuration)
        self.assertIn(self.TEST_USER_DN, updated_map)

    def test_load_resource_map(self):
        """Basic test for direct resource map loading"""
        # Get empty map initially
        res_map, map_stamp = load_resource_map(self.configuration)
        self.assertEqual(res_map, {})
        # Add test resource
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        force_update_resource_map(self.configuration)
        # Verify updated map contains resource after refresh
        res_map, map_stamp = load_resource_map(self.configuration)
        self.assertIn(self.TEST_RESOURCE_ID, res_map)

    def test_load_vgrid_map(self):
        """Basic test for direct vgrid map loading"""
        # Get map with at least 'Generic' vgrid
        vgrid_map, map_stamp = load_vgrid_map(self.configuration)
        self.assertIn('Generic', vgrid_map.get(VGRIDS, {}))
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        force_update_vgrid_map(self.configuration)
        # Verify updated map contains vgrid after refresh
        vgrid_map, map_stamp = load_vgrid_map(self.configuration)
        self.assertIn(self.test_vgrid, vgrid_map.get(VGRIDS, {}))

    def test_get_vgrid_map_vgrids(self):
        """Test get_vgrid_map_vgrids returns vgrid list"""
        vgrid_list = get_vgrid_map_vgrids(self.configuration)
        self.assertTrue(isinstance(vgrid_list, list))
        self.assertEqual(['Generic'], vgrid_list)

    def test_user_owned_res_exes(self):
        """Test user_owned_res_exes returns owned execution nodes"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        force_update_resource_map(self.configuration)
        owned = user_owned_res_exes(self.configuration, self.TEST_OWNER_DN)
        self.assertTrue(isinstance(owned, dict))
        self.assertIn(self.TEST_RESOURCE_ALIAS, owned)

    def test_user_owned_res_stores(self):
        """Test user_owned_res_stores returns owned storage nodes"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        force_update_resource_map(self.configuration)
        owned = user_owned_res_stores(self.configuration, self.TEST_OWNER_DN)
        self.assertTrue(isinstance(owned, dict))
        self.assertIn(self.TEST_RESOURCE_ALIAS, owned)

    def test_user_allowed_res_units(self):
        """Test user_allowed_res_units returns allowed units"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        force_update_vgrid_map(self.configuration)
        force_update_resource_map(self.configuration)
        allowed = user_allowed_res_units(
            self.configuration, self.TEST_OWNER_DN, "exe")
        self.assertTrue(isinstance(allowed, dict))
        self.assertIn(self.TEST_RESOURCE_ALIAS, allowed)

    def test_user_allowed_res_exes(self):
        """Test user_allowed_res_exes returns allowed exes"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        force_update_vgrid_map(self.configuration)
        force_update_resource_map(self.configuration)
        allowed = user_allowed_res_exes(self.configuration, self.TEST_OWNER_DN)
        self.assertTrue(isinstance(allowed, dict))
        self.assertIn(self.TEST_RESOURCE_ALIAS, allowed)

    def test_user_allowed_res_stores(self):
        """Test user_allowed_res_stores returns allowed stores"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        force_update_vgrid_map(self.configuration)
        force_update_resource_map(self.configuration)
        allowed = user_allowed_res_stores(
            self.configuration, self.TEST_OWNER_DN)
        self.assertTrue(isinstance(allowed, dict))
        self.assertIn(self.TEST_RESOURCE_ALIAS, allowed)

    def test_user_visible_res_exes(self):
        """Test user_visible_res_exes returns visible exes"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        force_update_vgrid_map(self.configuration)
        force_update_resource_map(self.configuration)
        visible = user_visible_res_exes(self.configuration, self.TEST_OWNER_DN)
        self.assertTrue(isinstance(visible, dict))
        self.assertIn(self.TEST_RESOURCE_ALIAS, visible)

    def test_user_visible_res_stores(self):
        """Test user_visible_res_stores returns visible stores"""
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        force_update_vgrid_map(self.configuration)
        force_update_resource_map(self.configuration)
        visible = user_visible_res_stores(
            self.configuration, self.TEST_OWNER_DN)
        self.assertTrue(isinstance(visible, dict))
        self.assertIn(self.TEST_RESOURCE_ALIAS, visible)

    def test_user_allowed_user_confs(self):
        """Test user_allowed_user_confs returns allowed user confs"""
        self._provision_test_user(self, self.TEST_OWNER_DN)
        self._provision_test_user(self, self.TEST_USER_DN)
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN],
                           [self.TEST_USER_DN])
        force_update_vgrid_map(self.configuration)
        force_update_user_map(self.configuration)
        allowed = user_allowed_user_confs(
            self.configuration, self.TEST_OWNER_DN)
        self.assertTrue(isinstance(allowed, dict))
        self.assertIn(self.TEST_USER_UUID, allowed)
        self.assertIn(self.TEST_OWNER_UUID, allowed)

    def test_fill_placeholder_cache(self):
        """Test fill_placeholder_cache populates cache"""
        cache = {}
        fill_placeholder_cache(self.configuration, cache, [self.test_vgrid])
        self.assertIn(self.test_vgrid, cache)

    def test_is_vgrid_parent_placeholder(self):
        """Test is_vgrid_parent_placeholder detection"""
        test_path = os.path.join(self.configuration.user_home, 'testvgrid')
        result = is_vgrid_parent_placeholder(self.configuration, test_path,
                                             test_path)
        self.assertIsNone(result)

    def test_check_vgrids_modified_initial(self):
        """Verify initial state of modified vgrids list is empty"""
        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertEqual(modified, ['ALL'])
        reset_vgrids_modified(self.configuration)
        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertEqual(modified, [])

    def test_resources_using_re_notfound(self):
        """Test RE with no assigned resources returns empty list"""
        # Nonexistent RE should have no resources
        res_list = resources_using_re(self.configuration, 'NoSuchRE')
        self.assertEqual(res_list, [])

    def test_vgrid_inherit_map_single(self):
        """Test inheritance mapping with single vgrid"""
        test_settings = [('vgrid_name', self.test_vgrid),
                         ('hidden', True)]
        test_map = {
            VGRIDS: {
                self.test_vgrid: {
                    SETTINGS: test_settings,
                    OWNERS: [self.TEST_OWNER_DN]
                }
            }
        }
        inherited_map = vgrid_inherit_map(self.configuration, test_map)
        vgrid_data = inherited_map.get(VGRIDS, {})
        self.assertTrue(self.test_vgrid in vgrid_data)
        settings_dict = dict(vgrid_data[self.test_vgrid][SETTINGS])
        self.assertIs(type(settings_dict), dict)
        self.assertEqual(settings_dict.get('hidden'), True)

    def test_check_vgrids_modified(self):
        """Minimal test for vgrid modified tracking"""
        # Initially ALL marked modified until cache init
        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertEqual(modified, ['ALL'])
        # Reset and check ALL gone
        reset_vgrids_modified(self.configuration)
        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertEqual(modified, [])
        # Mark modified
        mark_vgrid_modified(self.configuration, self.test_vgrid)
        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertIn(self.test_vgrid, modified)
        # Reset and check gone again
        reset_vgrids_modified(self.configuration)
        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertNotIn(self.test_vgrid, modified)

    def test_user_vgrid_access(self):
        """Minimal test for user vgrid participation"""
        # Start with global access to default vgrid
        allowed_vgrids = user_vgrid_access(self.configuration,
                                           self.TEST_USER_DN)
        self.assertTrue('Generic' in allowed_vgrids)
        self.assertTrue(len(allowed_vgrids), 1)
        # Create private vgrid
        self._provision_test_user(self, self.TEST_OWNER_DN)
        self._create_vgrid(self.test_vgrid, [self.TEST_OWNER_DN])
        # Refresh maps to reflect new content
        force_update_vgrid_map(self.configuration)
        allowed_vgrids = user_vgrid_access(self.configuration,
                                           self.TEST_OWNER_DN)
        self.assertIn(self.test_vgrid, allowed_vgrids)

    def test_res_vgrid_access(self):
        """Minimal test for resource vgrid participation"""
        # Only Generic access initially
        allowed_vgrids = res_vgrid_access(
            self.configuration, self.TEST_RESOURCE_ID)
        self.assertEqual(allowed_vgrids, ['Generic'])
        # Add to vgrid
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, resources=[self.TEST_RESOURCE_ID])
        # Refresh maps to reflect new content
        force_update_vgrid_map(self.configuration)
        allowed = res_vgrid_access(self.configuration, self.TEST_RESOURCE_ID)
        self.assertIn(self.test_vgrid, allowed)

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
        updated_vgrid_map = force_update_vgrid_map(self.configuration)
        # Check vgrid map contains resource entry
        vgrid_data = updated_vgrid_map.get(VGRIDS, {})
        top_vgrid_data = vgrid_data.get(self.test_vgrid, {})
        top_vgrid_res = top_vgrid_data.get(RESOURCES, [])
        self.assertTrue(self.TEST_RESOURCE_ID in top_vgrid_res)

        # Check resource map contains resource entry
        updated_res_map = force_update_resource_map(self.configuration)
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

    def test_unmap_inheritance(self):
        """Test unmap_inheritance clears inherited mappings"""
        self._create_vgrid(self.test_vgrid, owners=[self.TEST_OWNER_DN])
        sub_vgrid = os.path.join(self.test_vgrid, 'subvgrid')
        self._create_vgrid(sub_vgrid)

        # Force refresh of cached map
        updated_map = force_update_vgrid_map(self.configuration)

        # Unmap and verify mark modified
        unmap_inheritance(self.configuration, self.test_vgrid,
                          self.TEST_OWNER_DN)

        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertEqual(modified, [self.test_vgrid, sub_vgrid])

    def test_user_map_fields(self):
        """Verify user map includes complete profile/settings data"""
        # First add a couple of test users
        self._provision_test_user(self, self.TEST_OWNER_DN)
        self._provision_test_user(self, self.TEST_USER_DN)
        # Force fresh user map
        initial_vgrid_map = force_update_vgrid_map(self.configuration)
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

        initial_vgrid_map = force_update_vgrid_map(self.configuration)
        # Check vgrid map contains resource entry
        vgrid_data = initial_vgrid_map.get(VGRIDS, {})
        top_vgrid_data = vgrid_data.get(self.test_vgrid, {})
        top_vgrid_res = top_vgrid_data.get(RESOURCES, [])
        self.assertTrue(self.TEST_RESOURCE_ID in top_vgrid_res)

        # Check resource map contains resource entry
        initial_map = force_update_resource_map(self.configuration)
        self.assertIn(self.TEST_RESOURCE_ID, initial_map)

        # Remove resource assignment from vgrid
        status, msg = vgrid_set_entities(self.configuration, self.test_vgrid,
                                         'resources', [], allow_empty=True)
        self.assertTrue(status, msg)

        updated_vgrid_map = force_update_vgrid_map(self.configuration)
        # Check vgrid map no longer contains resource entry
        vgrid_data = updated_vgrid_map.get(VGRIDS, {})
        top_vgrid_data = vgrid_data.get(self.test_vgrid, {})
        top_vgrid_res = top_vgrid_data.get(RESOURCES, [])
        self.assertFalse(self.TEST_RESOURCE_ID in top_vgrid_res)

        # Verify resource still in resource map
        updated_map = force_update_resource_map(self.configuration)
        self.assertIn(self.TEST_RESOURCE_ID, updated_map)

    def test_non_recursive_inheritance(self):
        """Verify non-recursive map excludes nested vgrids"""
        # Create parent+child vgrids
        parent_vgrid = 'parent'
        self._create_vgrid(parent_vgrid, [self.TEST_OWNER_DN])
        child_vgrid = os.path.join(parent_vgrid, 'child')
        self._create_vgrid(child_vgrid, None, [self.TEST_MEMBER_DN])

        # Force update to avoid auto caching and get non-recursive map
        vgrid_map = force_update_vgrid_map(self.configuration)
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

        initial_vgrid_map = force_update_vgrid_map(self.configuration)

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

        initial_vgrid_map = force_update_vgrid_map(self.configuration)

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

    def test_user_allowed_res_confs(self):
        """Minimal test for user_allowed_res_confs"""
        # Create test user and add test resource to vgrid
        self._provision_test_user(self, self.TEST_OWNER_DN)
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        self._create_vgrid(self.test_vgrid, owners=[self.TEST_OWNER_DN],
                           resources=[self.TEST_RESOURCE_ID])
        force_update_vgrid_map(self.configuration)
        force_update_resource_map(self.configuration)
        # Owner should be allowed access
        allowed = user_allowed_res_confs(self.configuration,
                                         self.TEST_OWNER_DN)
        self.assertIn(self.TEST_RESOURCE_ALIAS, allowed)

    def test_user_visible_res_confs(self):
        """Minimal test for user_visible_res_confs"""
        # Owner should see owned resources even without vgrid access
        self._create_resource(self.TEST_RESOURCE_ID, [self.TEST_OWNER_DN])
        force_update_resource_map(self.configuration)
        visible = user_visible_res_confs(
            self.configuration, self.TEST_OWNER_DN)
        self.assertIn(self.TEST_RESOURCE_ALIAS, visible)

    def test_user_visible_user_confs(self):
        """Minimal test for user_visible_user_confs"""
        # Owner should see themselves in auto map
        self._provision_test_user(self, self.TEST_OWNER_DN)
        force_update_user_map(self.configuration)
        visible = user_visible_user_confs(
            self.configuration, self.TEST_OWNER_DN)
        self.assertIn(self.TEST_OWNER_UUID, visible)

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

    def test_unmap_resource(self):
        """Test unmap_resource marks resource modified"""
        mod_list, mod_stamp = check_resources_modified(self.configuration)
        self.assertNotIn(self.TEST_RESOURCE_ID, mod_list)

        # Unmap and verify mark modified
        unmap_resource(self.configuration, self.TEST_RESOURCE_ID)

        mod_list, mod_stamp = check_vgrids_modified(self.configuration)
        self.assertIn(self.TEST_RESOURCE_ID, mod_list)
        # TODO: fix and enable next
        # mod_list, mod_stamp = check_resources_modified(self.configuration)
        # self.assertIn(self.TEST_RESOURCE_ID, mod_list)

    def test_check_vgrids_modified_initial(self):
        """Verify initial state of modified vgrids list is empty"""
        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertEqual(modified, ['ALL'])
        reset_vgrids_modified(self.configuration)
        modified, stamp = check_vgrids_modified(self.configuration)
        self.assertEqual(modified, [])

    def test_resources_using_re_notfound(self):
        """Test RE with no assigned resources returns empty list"""
        # Nonexistent RE should have no resources
        res_list = resources_using_re(self.configuration, 'NoSuchRE')
        self.assertEqual(res_list, [])

    def test_vgrid_inherit_map_single(self):
        """Test inheritance mapping with single vgrid"""
        test_settings = [('vgrid_name', self.test_vgrid),
                         ('description', 'Test description')]
        test_map = {
            VGRIDS: {
                self.test_vgrid: {
                    SETTINGS: test_settings
                }
            }
        }
        inherited_map = vgrid_inherit_map(self.configuration, test_map)
        settings_dict = dict(inherited_map[VGRIDS][self.test_vgrid][SETTINGS])
        self.assertEqual(settings_dict['description'], 'Test description')

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
