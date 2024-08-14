# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# test_mig_shared_cloud - unit test of the corresponding mig shared module
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

"""Unit tests for the migrid module pointed to in the filename"""

import os
import sys
import time
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from tests.support import TEST_OUTPUT_DIR, MigTestCase, FakeConfiguration, \
    cleanpath, testmain
from mig.shared.cloud import cloud_access_allowed, cloud_load_instance, \
    cloud_save_instance, cloud_purge_instance, allowed_cloud_images

DUMMY_USER = 'dummy-user'
DUMMY_SETTINGS_DIR = 'dummy_user_settings'
DUMMY_SETTINGS_PATH = os.path.join(TEST_OUTPUT_DIR, DUMMY_SETTINGS_DIR)
DUMMY_CLOUD = "CLOUD"
DUMMY_FLAVOR = 'openstack'
DUMMY_LABEL = 'dummy-label'
DUMMY_IMAGE = 'dummy-image'
DUMMY_HEX_ID = 'deadbeef-dead-beef-dead-beefdeadbeef'

DUMMY_CLOUD_SPEC = {'service_title': 'CLOUDTITLE', 'service_name': 'CLOUDNAME',
                    'service_desc': 'A Cloud for migrid site',
                    'service_provider_flavor': 'openstack',
                    'service_hosts': 'https://myopenstack-cloud.org:5000/v3',
                    'service_rules_of_conduct': 'rules-of-conduct.pdf',
                    'service_max_user_instances': '0',
                    'service_max_user_instances_map': {DUMMY_USER: '1'},
                    'service_allowed_images': DUMMY_IMAGE,
                    'service_allowed_images_map': {DUMMY_USER: 'ALL'},
                    'service_user_map': {DUMMY_IMAGE, 'user'},
                    'service_image_alias_map': {DUMMY_IMAGE.lower():
                                                DUMMY_IMAGE},
                    'service_flavor_id': DUMMY_HEX_ID,
                    'service_flavor_id_map': {DUMMY_USER: DUMMY_HEX_ID},
                    'service_network_id': DUMMY_HEX_ID,
                    'service_key_id_map': {},
                    'service_sec_group_id': DUMMY_HEX_ID,
                    'service_floating_network_id': DUMMY_HEX_ID,
                    'service_availability_zone': 'myopenstack',
                    'service_jumphost_address': 'jumphost.somewhere.org',
                    'service_jumphost_user': 'cloud',
                    'service_jumphost_manage_keys_script':
                    'cloud_manage_keys.py',
                    'service_jumphost_manage_keys_coding': 'base16',
                    'service_network_id_map': {},
                    'service_sec_group_id_map': {},
                    'service_floating_network_id_map': {},
                    'service_availability_zone_map': {},
                    'service_jumphost_address_map': {},
                    'service_jumphost_user_map': {}}
DUMMY_CONF = FakeConfiguration(user_settings=DUMMY_SETTINGS_PATH,
                               site_cloud_access=[('distinguished_name', '.*')],
                               cloud_services=[DUMMY_CLOUD_SPEC])

DUMMY_INSTANCE_ID = '%s:%s:%s' % (DUMMY_USER, DUMMY_LABEL, DUMMY_HEX_ID)
DUMMY_INSTANCE_DICT = {
    DUMMY_INSTANCE_ID: {
        'INSTANCE_LABEL': DUMMY_LABEL,
        'INSTANCE_IMAGE': DUMMY_IMAGE,
        'INSTANCE_ID': DUMMY_INSTANCE_ID,
        'IMAGE_ID': DUMMY_IMAGE,
        'CREATED_TIMESTAMP': "%d" % time.time(),
        'USER_CERT': DUMMY_USER
    }
}


class MigSharedCloud(MigTestCase):
    """Wrap unit tests for the corresponding module"""

    def test_cloud_save_load(self):
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)

        save_status = cloud_save_instance(DUMMY_CONF, DUMMY_USER, DUMMY_CLOUD,
                                          DUMMY_LABEL, DUMMY_INSTANCE_DICT)
        self.assertTrue(save_status)

        saved_path = os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER,
                                  '%s.state' % DUMMY_CLOUD)
        self.assertTrue(os.path.exists(saved_path))

        instance = cloud_load_instance(DUMMY_CONF, DUMMY_USER,
                                       DUMMY_CLOUD, DUMMY_LABEL)
        # NOTE: instance should be a non-empty dict at this point
        self.assertTrue(isinstance(instance, dict))
        # print(instance)
        self.assertTrue(DUMMY_INSTANCE_ID in instance)
        instance_dict = instance[DUMMY_INSTANCE_ID]
        self.assertEqual(instance_dict['INSTANCE_LABEL'], DUMMY_LABEL)
        self.assertEqual(instance_dict['INSTANCE_IMAGE'], DUMMY_IMAGE)
        self.assertEqual(instance_dict['INSTANCE_ID'], DUMMY_INSTANCE_ID)
        self.assertEqual(instance_dict['IMAGE_ID'], DUMMY_IMAGE)
        self.assertEqual(instance_dict['USER_CERT'], DUMMY_USER)

    @unittest.skip('Work in progress - currently requires remote openstack')
    def test_cloud_allowed_images(self):
        os.makedirs(os.path.join(DUMMY_SETTINGS_PATH, DUMMY_USER))
        cleanpath(DUMMY_SETTINGS_DIR, self)

        allowed_images = allowed_cloud_images(DUMMY_CONF, DUMMY_USER,
                                              DUMMY_CLOUD, DUMMY_FLAVOR)
        self.assertTrue(isinstance(allowed_images, list))
        print(allowed_images)
        self.assertTrue(DUMMY_IMAGE in allowed_images)


if __name__ == '__main__':
    testmain()
