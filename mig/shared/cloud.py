#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cloud - Helper functions for the cloud service
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Cloud service helper functions"""

import hashlib
import os
import re
import sys
import time

try:
    import openstack
except ImportError, err:
    openstack = None

from shared.base import force_utf8
from shared.defaults import keyword_all

# Internal helper to map individual operations to flavored cloud functions
__cloud_helper_map = {"openstack": None}
# How long and often to poll during wait for instance creation and destruction
__max_wait_secs = 120
__poll_delay_secs = 3

cloud_manage_actions = ['start', 'restart', 'status', 'stop']
cloud_edit_actions = ['updatekeys', 'create', 'delete']


def __bail_out_openstack(*args, **kwargs):
    """Helper for dynamic bail out on actual use"""
    raise Exception("cloud functions require openstackclient")


def __require_openstack(func):
    """Internal helper to verify openstack module availability on use"""
    if openstack is None:
        return __bail_out_openstack
    return func


def __wait_available(configuration, client_id, cloud_id, cloud_flavor,
                     instance):
    """Wait for instance to be truly available after create"""
    # TODO: lookup the openstack client V3 version of the utils.wait_for_X
    _logger = configuration.logger
    available = False
    try:
        for i in xrange(__max_wait_secs / __poll_delay_secs):
            status, msg = status_of_cloud_instance(configuration, client_id,
                                                   cloud_id, cloud_flavor,
                                                   force_utf8(instance.name))
            if 'active' == msg.lower():
                _logger.info("%s cloud instance %s is ready" % (cloud_id,
                                                                instance))
                available = True
                break
            elif 'error' == msg.lower():
                raise Exception("ERROR status found - giving up")
            else:
                _logger.debug("wait for %s cloud instance %s: %s" %
                              (cloud_id, instance, msg))
                time.sleep(__poll_delay_secs)
        _logger.warning("gave up waiting for %s instance %s appearing" %
                        (cloud_id, instance))
    except Exception, exc:
        _logger.warning("wait available for %s cloud instance %s failed: %s"
                        % (cloud_id, instance, exc))
    return available


def __wait_gone(configuration, client_id, cloud_id, cloud_flavor, instance):
    """Wait for instance to be truly gone after delete"""
    _logger = configuration.logger
    gone = False
    try:
        for i in xrange(__max_wait_secs / __poll_delay_secs):
            status, msg = status_of_cloud_instance(configuration, client_id,
                                                   cloud_id, cloud_flavor,
                                                   force_utf8(instance.name))
            if not status:
                _logger.info("%s cloud instance %s is gone" % (cloud_id,
                                                               instance))
                gone = True
                break
            time.sleep(__poll_delay_secs)
        _logger.warning("gave up waiting for %s instance %s disappearing" %
                        (cloud_id, instance))
    except Exception, exc:
        _logger.warning("wait gone for %s cloud instance %s failed: %s" %
                        (cloud_id, instance, exc))
        time.sleep(5)
    return gone


@__require_openstack
def openstack_cloud_connect(configuration, cloud_id):
    """Shared helper to connect to the cloud with basic setup handled"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("connect to %s" % cloud_id)
    # TODO: we should either edit cloud.yaml ID to fit or introduce service id
    internal_id = cloud_id.lower()
    try:
        conn = openstack.connect(cloud=internal_id)
        openstack.enable_logging(debug=False)
        _logger.info("connected to %s" % cloud_id)
    except Exception, exc:
        _logger.error("connect to %s failed: %s" % (cloud_id, exc))
        return None
    return conn


@__require_openstack
def openstack_list_cloud_images(configuration, client_id, cloud_id):
    """Fetch the list of available cloud images"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("list %s cloud images for %s" % (cloud_id, client_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])
    img_list = []
    for image in conn.image.images():
        img_list.append((force_utf8(image.name), force_utf8(image.id)))
    return (True, img_list)


@__require_openstack
def openstack_start_cloud_instance(configuration, client_id, cloud_id, instance_id):
    """Start provided cloud instance"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("start %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                        client_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])

    status, msg = True, ''
    try:
        instance = conn.compute.find_server(instance_id)
        if not instance:
            status = False
            msg = "failed to locate %s cloud instance %s" % \
                  (cloud_id, instance_id)
            _logger.error("%s failed to locate %s cloud instance %s: %s" %
                          (client_id, cloud_id, instance_id, msg))
            return (status, msg)
        msg = conn.compute.start_server(instance)
        if msg:
            status = False
            msg = force_utf8(msg)
            _logger.error("%s failed to start %s cloud instance: %s" %
                          (client_id, instance_id, msg))
        else:
            _logger.info("%s started cloud %s instance %s" %
                         (client_id, cloud_id, instance_id))
    except openstack.exceptions.ConflictException, ose:
        status = False
        msg = "instance start failed - already started!"
        _logger.error("%s failed to start %s cloud instance %s again" %
                      (client_id, instance_id, ose))
    except Exception, exc:
        status = False
        msg = "instance start failed!"
        _logger.error("%s failed to start %s cloud instance: %s" %
                      (client_id, instance_id, exc))

    return (status, msg)


@__require_openstack
def openstack_stop_cloud_instance(configuration, client_id, cloud_id, instance_id):
    """Stop provided cloud instance"""
    _logger = configuration.logger
    _logger.info("stop %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                       client_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])

    status, msg = True, ''
    try:
        instance = conn.compute.find_server(instance_id)
        if not instance:
            status = False
            msg = "failed to locate %s cloud instance %s" % \
                  (cloud_id, instance_id)
            _logger.error("%s failed to locate %s cloud instance %s: %s" %
                          (client_id, cloud_id, instance_id, msg))
            return (status, msg)
        msg = conn.compute.stop_server(instance)
        if msg:
            status = False
            msg = force_utf8(msg)
            _logger.error("%s failed to stop %s cloud instance: %s" %
                          (client_id, instance_id, msg))
        else:
            _logger.info("%s stopped cloud %s instance %s" %
                         (client_id, cloud_id, instance_id))
    except openstack.exceptions.ConflictException, ose:
        status = False
        msg = "instance stop failed - not started!"
        _logger.error("%s failed to stop %s cloud instance: %s" %
                      (client_id, instance_id, ose))
    except Exception, exc:
        status = False
        msg = "instance stop failed!"
        _logger.error("%s failed to stop %s cloud instance: %s" %
                      (client_id, instance_id, exc))
    return (status, msg)


@__require_openstack
def openstack_restart_cloud_instance(configuration, client_id, cloud_id, instance_id,
                                     boot_strength="HARD"):
    """Reboot provided cloud instance. Use SOFT or HARD as boot_strength"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("restart %s cloud instance %s for %s" % (cloud_id,
                                                          instance_id,
                                                          client_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])

    status, msg = True, ''
    try:
        instance = conn.compute.find_server(instance_id)
        if not instance:
            status = False
            msg = "failed to locate %s cloud instance %s" % \
                  (cloud_id, instance_id)
            _logger.error("%s failed to locate %s cloud instance %s: %s" %
                          (client_id, cloud_id, instance_id, msg))
            return (status, msg)
        msg = conn.compute.reboot_server(instance, boot_strength)
        if msg:
            status = False
            msg = force_utf8(msg)
            _logger.error("%s failed to restart %s cloud instance: %s" %
                          (client_id, instance_id, msg))
        else:
            _logger.info("%s restarted cloud %s instance %s" %
                         (client_id, cloud_id, instance_id))
    except Exception, exc:
        status = False
        msg = "instance restarted failed!"
        _logger.error("%s failed to restart %s cloud instance: %s" %
                      (client_id, instance_id, exc))

    return (status, msg)


@__require_openstack
def openstack_status_of_cloud_instance(configuration, client_id, cloud_id,
                                       instance_id):
    """Status of provided cloud instance"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("status of %s cloud instance %s for %s" %
                 (cloud_id, instance_id, client_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])

    status, msg = True, ''
    try:
        instance = None
        for server in conn.compute.servers():
            if force_utf8(server.name) == instance_id:
                instance = server
                break

        #instance = conn.compute.find_server(instance_id)
        if not instance:
            status = False
            msg = "failed to locate %s cloud instance %s" % \
                  (cloud_id, instance_id)
            _logger.error("%s failed to locate %s cloud instance %s: %s" %
                          (client_id, cloud_id, instance_id, msg))
            return (status, msg)
        status_msg = force_utf8(instance.status)
        if status_msg:
            msg = status_msg
            _logger.info("%s status for cloud %s instance %s" %
                         (client_id, cloud_id, status_msg))
        else:
            _logger.error("%s failed status for %s cloud instance: %s" %
                          (client_id, instance_id, status_msg))

    except Exception, exc:
        status = False
        msg = "instance status failed!"
        _logger.error("%s failed status for %s cloud instance: %s" %
                      (client_id, instance_id, exc))
    return (status, msg)
    # _logger.info("%s status of cloud %s instance %s: %s (%s)" % \
    #                 (client_id, cloud_id, instance_id, instance, dir(instance)))
    # _logger.info("%s status of cloud %s instance %s: %s" % \
    #                 (client_id, cloud_id, instance_id, instance.status))
    # return (status, instance.status)


@__require_openstack
def openstack_register_cloud_keys(configuration, client_id, cloud_id,
                                  auth_keys):
    """Register ssh keys for user and named cloud"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("register %s cloud ssh keys for %s" % (cloud_id, client_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])

    status, msg = True, ''
    try:
        _logger.debug("register %s cloud ssh key for %s" %
                      (cloud_id, client_id))
        # Register current keys
        for pub_key in auth_keys:
            pub_key = pub_key.strip()
            if not pub_key:
                continue
            # Build a unique ID to identify this key
            user_key = "%s : %s" % (client_id, pub_key)
            key_id = hashlib.sha256(user_key).hexdigest()

            # TODO: more carefully clean up old keys?
            if not conn.search_keypairs(key_id):
                _logger.info("register %s cloud ssh key for %s: %s" %
                             (cloud_id, client_id, key_id))
                conn.create_keypair(key_id, pub_key)
            else:
                _logger.info("already done for %s cloud ssh key for %s: %s" %
                             (cloud_id, client_id, key_id))
    except Exception, exc:
        status = False
        msg = "key registration failed!"
        _logger.error("%s failed to register %s cloud ssh key: %s" %
                      (client_id, cloud_id, exc))
    return (status, msg)


@__require_openstack
def openstack_update_cloud_instance_keys(configuration, client_id, cloud_id,
                                         instance_id, auth_keys):
    """Update ssh keys for user and named cloud instance"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("update %s cloud ssh keys for %s on %s" %
                 (cloud_id, client_id, instance_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])

    status, msg = True, ''
    try:
        instance = conn.compute.find_server(instance_id)
        if not instance:
            status = False
            msg = "failed to locate %s cloud instance %s" % \
                  (cloud_id, instance_id)
            _logger.error("%s failed to locate %s cloud instance %s" %
                          (client_id, cloud_id, instance_id))
            return (status, msg)
        _logger.debug("update %s cloud ssh key for %s on %s" %
                      (cloud_id, client_id, instance_id))
        # Insert current keys
        for pub_key in auth_keys:
            pub_key = pub_key.strip()
            if not pub_key:
                continue
            # Build a unique ID to identify this key
            user_key = "%s : %s" % (client_id, pub_key)
            key_id = hashlib.sha256(user_key).hexdigest()
            _logger.info("update %s cloud ssh key for %s: %s" %
                         (cloud_id, client_id, key_id))

            # TODO: more carefully clean up old keys?
            if not conn.search_keypairs(key_id):
                conn.create_keypair(key_id, pub_key)
            # TODO: figure out how to assign the keypair here!!
    except Exception, exc:
        status = False
        msg = "key update failed!"
        _logger.error("%s failed to update %s cloud ssh key for %s: %s" %
                      (client_id, cloud_id, instance_id, exc))
    return (status, msg)


@__require_openstack
def openstack_create_cloud_instance(configuration, client_id, cloud_id,
                                    instance_id, image_id, auth_keys=[]):
    """Create named cloud instance for user"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("create %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                         client_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])

    status, msg = True, ''

    # TODO: move to args or conf

    flavor_id = '176b73c9-1644-46c6-9c64-90bd73e92492'
    network_id = 'b562785d-5286-4c3d-a834-13ab427af920'
    key_id = 'erda-keypair'
    sec_group_id = '3ed57f38-7f2d-4541-8241-849377f495bd'
    floating_network_id = 'ecee5c29-037a-4225-a2df-6412674e8fb5'
    availability_zone = 'NFS'

    public_network = "130.225.104.0/24"

    if auth_keys:
        openstack_register_cloud_keys(configuration, client_id, cloud_id,
                                      auth_keys)
        # Build a unique ID to identify the first key
        user_key = "%s : %s" % (client_id, auth_keys[0])
        key_id = hashlib.sha256(user_key).hexdigest()
        _logger.info("%s registering key %s for %s instance %s" %
                     (client_id, key_id, cloud_id, instance_id))

    try:
        instance = conn.compute.find_server(instance_id)
        if instance:
            status = False
            msg = "%s cloud instance %s already exists!" % \
                  (cloud_id, instance_id)
            _logger.error("%s refusing to create %s cloud instance %s again" %
                          (client_id, cloud_id, instance_id))
            return (status, msg)
        instance = conn.create_server(instance_id, image=image_id,
                                      availability_zone=availability_zone,
                                      key_name=key_id, flavor=flavor_id,
                                      network=network_id,
                                      security_groups=sec_group_id)
        if not instance:
            status = False
            msg = force_utf8("%s" % instance)
            _logger.error("%s failed to create %s cloud instance: %s" %
                          (client_id, instance_id, msg))

        if not __wait_available(configuration, client_id, cloud_id,
                                cloud_flavor, instance):
            status = False
            msg = "failed to create %s cloud instance %s" % (cloud_id,
                                                             instance_id)
            _logger.error(msg)

            _logger.info("cleaning up after failed %s cloud instance %s" % \
                         (cloud_id, instance_id))
            try:
                instance = conn.compute.find_server(instance_id)
                msg = conn.compute.delete_server(instance)
                if msg:
                    raise Exception(force_utf8(msg))
            except Exception, exc:
                _logger.error("%s failed to clean up %s cloud instance: %s" % \
                              (client_id, instance_id, exc))
            return (status, msg)

        # Create floating IP from public network
        floating_ip = conn.network.create_ip(
            floating_network_id=floating_network_id)
        if not floating_ip:
            status = False
            msg = force_utf8("%s" % floating_ip)
            _logger.error("%s failed to create %s cloud instance ip: %s" %
                          (client_id, instance_id, msg))
            return (status, msg)

        # Add floating IP to instance
        conn.compute.add_floating_ip_to_server(
            instance.id, floating_ip.floating_ip_address)
        if not floating_ip.floating_ip_address:
            status = False
            msg = force_utf8("%s" % floating_ip.floating_ip_address)
            _logger.error("%s failed to create %s cloud instance float ip: %s"
                          % (client_id, instance_id, msg))
            return (status, msg)
        msg = force_utf8(floating_ip.floating_ip_address)
        _logger.info("%s created cloud %s instance %s with floating IP %s" %
                     (client_id, cloud_id, instance_id, msg))
    except Exception, exc:
        status = False
        msg = "instance creation failed!"
        _logger.error("%s failed to create %s cloud instance: %s" %
                      (client_id, instance_id, exc))
    return (status, msg)


@__require_openstack
def openstack_delete_cloud_instance(configuration, client_id, cloud_id,
                                    instance_id, allow_missing=True):
    """Delete provided cloud instance"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("delete %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                         client_id))
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return (False, [])

    status, msg = True, ''
    try:
        instance = conn.compute.find_server(instance_id)
        if instance:
            msg = conn.compute.delete_server(instance)
            if msg:
                msg = force_utf8(msg)
                status = False
                _logger.error("%s failed to delete %s cloud instance: %s" % \
                              (client_id, instance_id, msg))
                return (status, msg)
        
            if not __wait_gone(configuration, client_id, cloud_id,
                               cloud_flavor,
                               instance):
                msg = "failed to delete %s cloud instance %s" % (cloud_id,
                                                                 instance_id)
                status = False
                _logger.error(msg)
                return (status, msg)

            removed = conn.delete_unattached_floating_ips(retry=1)
            if removed < 1:
                # Possibly failed removal is not critical 
                _logger.warning("%s failed to free IP for %s cloud instance: %s" % \
                                (client_id, instance_id, removed))
            _logger.info("%s deleted cloud %s instance %s" % \
                         (client_id, cloud_id, instance_id))
        elif allow_missing:
            # Silently accept local delete if instance is already gone
            msg = "deleted reference to missing %s cloud instance %s" % \
                  (cloud_id, instance_id)
            _logger.info("%s %s" % (client_id, msg))
        else:
            status = False
            msg = "failed to locate %s cloud instance %s" % \
                  (cloud_id, instance_id)
            _logger.error("%s failed to locate %s cloud instance %s" %
                          (client_id, cloud_id, instance_id))
    except Exception, exc:
        status = False
        msg = "instance deletion failed!"
        _logger.error("%s failed to delete %s cloud instance: %s" %
                      (client_id, instance_id, exc))
    return (status, msg)


def __get_cloud_helper(configuration, cloud_flavor, operation):
    """Returns the proper helper operation function for the requested
    cloud_flavor.
    """
    if "openstack" == cloud_flavor:
        # Init on first use
        if not __cloud_helper_map["openstack"]:
            __cloud_helper_map["openstack"] = {
                "check_cloud_available": openstack_cloud_connect,
                "list_cloud_images": openstack_list_cloud_images,
                "start_cloud_instance": openstack_start_cloud_instance,
                "restart_cloud_instance": openstack_restart_cloud_instance,
                "status_of_cloud_instance": openstack_status_of_cloud_instance,
                "stop_cloud_instance": openstack_stop_cloud_instance,
                "update_cloud_instance_keys": openstack_update_cloud_instance_keys,
                "create_cloud_instance": openstack_create_cloud_instance,
                "delete_cloud_instance": openstack_delete_cloud_instance,
            }
        return __cloud_helper_map[cloud_flavor][operation]
    else:
        raise ValueError("No such cloud flavor: %s" % cloud_flavor)


def cloud_access_allowed(configuration, user_dict):
    """Check if user with user_dict is allowed to access site cloud features"""
    for (key, val) in configuration.site_cloud_access:
        if not re.match(val, user_dict.get(key, 'NO SUCH FIELD')):
            return False
    return True


def check_cloud_available(configuration, client_id, cloud_id, cloud_flavor):
    """Make sure cloud is available"""
    _logger = configuration.logger
    _logger.info("check %s cloud available" % cloud_id)
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "check_cloud_available")
    try:
        helper(configuration, cloud_id)
        return True
    except Exception, exc:
        _logger.error("%s cloud available check failed: %s" % (cloud_id, exc))
        return False


def list_cloud_images(configuration, client_id, cloud_id, cloud_flavor):
    """Fetch the list of available cloud images"""
    _logger = configuration.logger
    _logger.info("list %s cloud images for %s" % (cloud_id, client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "list_cloud_images")
    return helper(configuration, client_id, cloud_id)


def start_cloud_instance(configuration, client_id, cloud_id, cloud_flavor,
                         instance_id):
    """Start provided cloud instance"""
    _logger = configuration.logger
    _logger.info("start %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                        client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "start_cloud_instance")
    return helper(configuration, client_id, cloud_id, instance_id)


def stop_cloud_instance(configuration, client_id, cloud_id, cloud_flavor,
                        instance_id):
    """Stop provided cloud instance"""
    _logger = configuration.logger
    _logger.info("stop %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                       client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "stop_cloud_instance")
    return helper(configuration, client_id, cloud_id, instance_id)


def restart_cloud_instance(configuration, client_id, cloud_id, cloud_flavor,
                           instance_id, boot_strength="HARD"):
    """Reboot provided cloud instance. Use SOFT or HARD as boot_strength"""
    _logger = configuration.logger
    _logger.info("restart %s cloud instance %s for %s" % (cloud_id,
                                                          instance_id,
                                                          client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "restart_cloud_instance")
    return helper(configuration, client_id, cloud_id, instance_id, boot_strength)


def status_of_cloud_instance(configuration, client_id, cloud_id, cloud_flavor,
                             instance_id):
    """Status of provided cloud instance"""
    _logger = configuration.logger
    _logger.info("status of %s cloud instance %s for %s" %
                 (cloud_id, instance_id, client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "status_of_cloud_instance")
    return helper(configuration, client_id, cloud_id, instance_id)


def update_cloud_instance_keys(configuration, client_id, cloud_id,
                               cloud_flavor, instance_id, auth_keys):
    """Update ssh keys for cloud instance"""
    _logger = configuration.logger
    _logger.info("update %s cloud ssh keys for %s on %s" %
                 (cloud_id, client_id, instance_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "update_cloud_instance_keys")
    return helper(configuration, client_id, cloud_id, instance_id, auth_keys)


def create_cloud_instance(configuration, client_id, cloud_id, cloud_flavor,
                          instance_id, image_id, auth_keys=[]):
    """Create named cloud instance for user"""
    _logger = configuration.logger
    _logger.info("create %s cloud %s instance %s for %s" %
                 (cloud_id, image_id, instance_id, client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "create_cloud_instance")
    return helper(configuration, client_id, cloud_id, instance_id,
                  image_id, auth_keys)


def delete_cloud_instance(configuration, client_id, cloud_id, cloud_flavor,
                          instance_id):
    """Delete provided cloud instance"""
    _logger = configuration.logger
    _logger.info("delete %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                         client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "delete_cloud_instance")
    return helper(configuration, client_id, cloud_id, instance_id)


if __name__ == "__main__":
    from shared.conf import get_configuration_object
    from shared.settings import load_cloud
    conf = get_configuration_object()
    client_id = '/C=DK/ST=NA/L=NA/O=NBI/OU=NA/CN=Jonas Bardino/emailAddress=bardino@nbi.ku.dk'
    cloud_id = 'mist'
    cloud_flavor = 'openstack'
    instance_id = 'My-Misty-Test-42'
    instance_image = 'cirrossdk'

    reuse_instance = False
    restart_instance = False
    if sys.argv[1:]:
        reuse_instance = (sys.argv[1].lower() in ['1', 'true', 'yes'])
    if sys.argv[2:]:
        restart_instance = (sys.argv[2].lower() in ['1', 'true', 'yes'])

    cloud_settings = load_cloud(client_id, conf)
    auth_keys = cloud_settings['authkeys'].split('\n')

    # TODO: load yaml from custom location or inline
    print "calling cloud operations for %s in %s with instance %s" % \
          (client_id, cloud_id, instance_id)
    img_list = list_cloud_images(conf, client_id, cloud_id, cloud_flavor)
    print img_list
    image_id = ''
    for (name, val) in img_list:
        if instance_image == name:
            image_id = val

    if not reuse_instance:
        print create_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                    instance_id, image_id, auth_keys)
        # Start happens automatically on create
        time.sleep(5)
    print status_of_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                   instance_id)
    print update_cloud_instance_keys(conf, client_id, cloud_id, cloud_flavor,
                                     instance_id, auth_keys)
    if restart_instance:
        print restart_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                     instance_id)
        time.sleep(5)
        print stop_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                  instance_id)
        time.sleep(5)
        print status_of_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                       instance_id)
        time.sleep(5)
        print start_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                   instance_id)
        time.sleep(5)
        print stop_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                  instance_id)
        time.sleep(5)
    if not reuse_instance:
        print delete_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                    instance_id)
        time.sleep(5)
    print "done with cloud operations for %s in %s" % (client_id, cloud_id)
    sys.exit(0)
