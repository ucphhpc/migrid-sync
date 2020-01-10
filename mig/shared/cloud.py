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

import base64
import hashlib
import json
import os
import re
import socket
import sys
import time

try:
    import openstack
except ImportError, err:
    openstack = None
try:
    import requests
except ImportError, err:
    requests = None

from shared.base import force_utf8, force_utf8_rec, client_id_dir
from shared.defaults import keyword_all
from shared.fileio import pickle, unpickle, acquire_file_lock, \
     release_file_lock
from shared.safeeval import subprocess_call

# Internal helper to map individual operations to flavored cloud functions
__cloud_helper_map = {"openstack": None}
# How long and often to poll during wait for instance creation and destruction
__max_wait_secs = 120
__poll_delay_secs = 3

cloud_manage_actions = ['start', 'softrestart', 'hardrestart',
                        'status', 'stop', 'webaccess']
cloud_edit_actions = ['updatekeys', 'create', 'delete']
jumphost_manage_key_actions = ['add', 'remove']


def __bail_out_openstack(*args, **kwargs):
    """Helper for dynamic bail out on actual use"""
    raise Exception("cloud functions require openstackclient")


def __require_openstack(func):
    """Internal helper to verify openstack module availability on use"""
    if openstack is None:
        return __bail_out_openstack
    return func

def __bail_out_requests(*args, **kwargs):
    """Helper for dynamic bail out on actual use"""
    raise Exception("cloud functions require requests")


def __require_requests(func):
    """Internal helper to verify requests module availability on use"""
    if requests is None:
        return __bail_out_requests
    return func


def __wait_available(configuration, client_id, cloud_id, cloud_flavor,
                     instance):
    """Wait for instance to be truly available after create"""
    # TODO: lookup the openstack client V3 version of the utils.wait_for_X
    _logger = configuration.logger
    try:
        for i in xrange(__max_wait_secs / __poll_delay_secs):
            status, msg = status_of_cloud_instance(configuration, client_id,
                                                   cloud_id, cloud_flavor,
                                                   force_utf8(instance.name))
            if 'active' == msg.lower():
                _logger.info("%s cloud instance %s is ready" % (cloud_id,
                                                                instance))
                return True
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
    return False


def __wait_gone(configuration, client_id, cloud_id, cloud_flavor, instance):
    """Wait for instance to be truly gone after delete"""
    _logger = configuration.logger
    try:
        for i in xrange(__max_wait_secs / __poll_delay_secs):
            status, msg = status_of_cloud_instance(configuration, client_id,
                                                   cloud_id, cloud_flavor,
                                                   force_utf8(instance.name))
            if not status:
                _logger.info("%s cloud instance %s is gone" % (cloud_id,
                                                               instance))
                return True
            time.sleep(__poll_delay_secs)
        _logger.warning("gave up waiting for %s instance %s disappearing" %
                        (cloud_id, instance))
    except Exception, exc:
        _logger.warning("wait gone for %s cloud instance %s failed: %s" %
                        (cloud_id, instance, exc))
    return False


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
    service = cloud_find_service(configuration, cloud_id)
    if not service:
        _logger.warning("no matching service %s" % cloud_id)
        return (False, [])
    img_list = []
    for image in conn.image.images():
        image_name = force_utf8(image.name)
        image_id = force_utf8(image.id)
        image_alias = service['service_image_alias_map'].get(image_name,
                                                             image_name)
        img_list.append((image_name, image_id, image_alias))
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
                                     boot_strength):
    """Reboot provided cloud instance. Use SOFT or HARD as boot_strength"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("restart %s cloud instance %s for %s %s" % \
                 (cloud_id, instance_id, client_id, boot_strength))
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
            _logger.error("%s failed to %s restart %s cloud instance: %s" %
                          (client_id, boot_strength, instance_id, msg))
        else:
            _logger.info("%s %s restarted cloud %s instance %s" %
                         (client_id, boot_strength, cloud_id, instance_id))
    except openstack.exceptions.ConflictException, ose:
        status = False
        msg = "instance restart err - not already running!"
        _logger.error("%s restart on stopped %s cloud instance %s" %
                      (client_id, instance_id, ose))
    except Exception, exc:
        status = False
        msg = "instance restarted failed!"
        _logger.error("%s failed to %s restart %s cloud instance: %s" %
                      (client_id, boot_strength, instance_id, exc))

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


@__require_openstack
def openstack_status_all_cloud_instances(configuration, client_id, cloud_id,
                                         instance_id_list, fields):
    """Find requested status fields for all specified user cloud instances"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("status all %s cloud instances %s for %s" %
                 (cloud_id, ', '.join(instance_id_list), client_id))
    err_dict = {'success': False, 'msg': 'cloud status failed!'}
    err_dict.update(dict([(i, "UNKNOWN") for i in fields]))
    instance_map = {}
    # Init to error and override with actual values (needs by-value copy)
    status_dict = dict([(i, err_dict.copy()) for i in instance_id_list])
    conn = openstack_cloud_connect(configuration, cloud_id)
    if conn is None:
        return status_dict

    # Special value parsing required for these fields
    lookup_map = {'public_ip': 'addresses', 'public_fqdn': 'addresses'}
    try:
        # Extract corresponding cloud status objects
        for server in conn.compute.servers():
            instance_id = force_utf8(server.name)
            if instance_id in instance_id_list:
                instance_map[instance_id] = server

        for instance_id in instance_id_list:
            instance = instance_map.get(instance_id, None)
            if not instance:
                status = False
                msg = "failed to locate %s cloud instance %s" % \
                      (cloud_id, instance_id)
                _logger.error("%s failed to locate %s cloud instance %s: %s" %
                              (client_id, cloud_id, instance_id, msg))
                status_dict[instance_id]['msg'] = msg
                continue
            #_logger.debug("%s status all for cloud %s instance %s: %s" % \
            #              (client_id, cloud_id, instance_id, instance))
            for name in fields:
                lookup_name = lookup_map.get(name, name)
                raw_val = getattr(instance, lookup_name, "UNKNOWN")
                if isinstance(raw_val, dict):
                    field_val = force_utf8_rec(raw_val)
                    # NOTE: addresses format is something along the lines of:
                    # {NETWORK_ID: [
                    #   {..., 'addr': INT_IP, 'OS-EXT-IPS:type': 'fixed'},
                    #   {..., 'addr': EXT_IP, 'OS-EXT-IPS:type': 'floating'}
                    # ]}
                    if name == 'public_ip':
                        address_entries = field_val.values()
                        for entry in address_entries:
                            if entry and entry[-1] and \
                                'floating' in entry[-1].values():
                                field_val = entry[-1].get('addr', 'UNKNOWN')
                                break
                    elif name == 'public_fqdn':
                        address_entries = field_val.values()
                        for entry in address_entries:
                            if entry and entry[-1] and \
                                'floating' in entry[-1].values():
                                addr = entry[-1].get('addr', '')
                                field_val = cloud_fqdn_from_ip(configuration,
                                                               addr)[0]
                                break
                    else:
                        _logger.warning("no converter for status field %s" % \
                                        name)
                        field_val = "%s" % field_val
                else:
                    field_val = force_utf8(raw_val)
                status_dict[instance_id][name] = field_val
                status_dict[instance_id]['success'] = True
                status_dict[instance_id]['msg'] = ''
    
        _logger.debug("%s status all for cloud %s instances %s: %s" %
                      (client_id, cloud_id, ', '.join(instance_id_list),
                       status_dict))
    except Exception, exc:
        _logger.error("%s failed status all for %s cloud: %s" %
                      (client_id, cloud_id, exc))
    return status_dict


@__require_requests
@__require_openstack
def openstack_web_access_cloud_instance(configuration, client_id, cloud_id,
                                        instance_id):
    """Web console access URL for cloud instance"""
    cloud_flavor = "openstack"
    _logger = configuration.logger
    _logger.info("console for %s cloud instance %s for %s" %
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
        # TODO: openstack does not expose console URL - manual request for now
        #console_url = force_utf8(instance.get_console_url())

        web_auth = conn.authorize()

        server = conn.compute.find_server(instance_id)
        API_ENDPOINT = "https://os208.hpc.ku.dk:8774/v2.1/servers/%s/action" \
                       % server.id
        body = '{"os-getVNCConsole":{"type": "novnc"}}'
        HEADERS = {}
        HEADERS['X-Auth-Token'] = web_auth
        HEADERS['Content-type'] = "application/json"
        response = requests.post(API_ENDPOINT, headers=HEADERS, data=body, verify=True)
        response_dict = force_utf8_rec(response.json())
        _logger.info("%s web console response: %s" % (client_id, response_dict))
        console_url = response_dict.get('console', {}).get('url', '')
        if console_url:
            msg = console_url
            _logger.info("%s web console for cloud %s instance %s: %s" %
                         (client_id, cloud_id, instance_id, msg))
        else:
            _logger.error("%s failed web console for %s cloud instance %s" \
                          % (client_id, cloud_id, instance_id))

    except Exception, exc:
        status = False
        msg = "instance web console access failed!"
        _logger.error("%s failed web console for %s cloud instance %s: %s" %
                      (client_id, cloud_id, instance_id, exc))
    return (status, msg)


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

    # We read defaults from configuration service section
    service = cloud_find_service(configuration, cloud_id)
    if not service:
        _logger.warning("no matching service %s" % cloud_id)
        return (False, [])
    # Default key if user doesn't give one
    key_id = lookup_user_service_value(configuration, client_id, service,
                                       "service_key_id")
    # Optional jump host for ssh login to instances
    jump_host = cloud_login_jump_host(configuration, client_id, cloud_id)
    jump_host_addr, jump_host_user = jump_host["fqdn"], jump_host["user"]
    # The rest are likely needed for creation to succeed
    flavor_id = lookup_user_service_value(configuration, client_id, service,
                                          "service_flavor_id")
    network_id = lookup_user_service_value(configuration, client_id, service,
                                           "service_network_id")
    sec_group_id = lookup_user_service_value(configuration, client_id,
                                             service, "service_sec_group_id")
    floating_network_id = lookup_user_service_value(
        configuration, client_id, service, "service_floating_network_id")
    availability_zone = lookup_user_service_value(
        configuration, client_id, service, "service_availability_zone")
    mandatory_settings = [flavor_id, network_id, sec_group_id,
                          floating_network_id, availability_zone]

    _logger.debug("create instance for %s with mandatory settings: %s" % \
                  (client_id, mandatory_settings))

    if "UNKNOWN" in mandatory_settings:
        _logger.warning("Found unknown mandatory cloud service setting(s): %s"
                        % mandatory_settings)
        _logger.warning("%s create %s cloud instance %s will likely fail" % \
                        (client_id, cloud_id, instance_id))
        
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

        if not cloud_add_jump_host_key(configuration, client_id, cloud_id,
                                       auth_keys):
            status = False
            msg = "failed to add %s cloud %s instance ssh jump keys" % \
                  (cloud_id, instance_id)
            _logger.error("%s %s " % (client_id, msg))
            return (status, msg)
        
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
                "status_all_cloud_instances": openstack_status_all_cloud_instances,
                "web_access_cloud_instance": openstack_web_access_cloud_instance,
                "update_cloud_instance_keys": openstack_update_cloud_instance_keys,
                "create_cloud_instance": openstack_create_cloud_instance,
                "delete_cloud_instance": openstack_delete_cloud_instance,
            }
        return __cloud_helper_map[cloud_flavor][operation]
    else:
        raise ValueError("No such cloud flavor: %s" % cloud_flavor)


def cloud_find_service(configuration, cloud_id):
    """Find cloud_id service section settings in configuration"""
    _logger = configuration.logger
    for service in configuration.cloud_services:
        if service['service_name'] == cloud_id:
            return service
    _logger.error("no such cloud service found: %s (%s)" % \
                  (cloud_id, configuration.cloud_services))
    return None

def cloud_build_instance_id(configuration, client_email, instance_label,
                            session_id):
    """Build the standard instance_id from client_email, instance_label and
    session_id.
    """
    _logger = configuration.logger
    _logger.debug("build instance id from %s %s %s" % \
                  (client_email, instance_label, session_id))
    instance_id = "%s:%s:%s" % (client_email, instance_label, session_id)
    return instance_id

def cloud_split_instance_id(configuration, client_id, instance_id):
    """Extract the instance_id parts of a full instance_id"""
    # format is user_email:instance_label:session_id
    _logger = configuration.logger
    _logger.debug("split instance id %s" % instance_id)
    client_email, instance_label, session_id = instance_id.split(':')
    return (client_email, instance_label, session_id)

def cloud_fqdn_from_ip(configuration, ip_addr):
    """Lookup host FQDN list from ip_addr"""
    _logger = configuration.logger
    fqdn = [ip_addr]
    if not ip_addr:
        return [ip_addr]
    try:
        fqdn = socket.gethostbyaddr(ip_addr)
    except Exception, exc:
        _logger.warning("could not resolve IP addresss %s to FQDN: %s" % \
                        (ip_addr, exc))
    return fqdn

def cloud_access_allowed(configuration, user_dict):
    """Check if user with user_dict is allowed to access site cloud features"""
    _logger = configuration.logger
    for (key, val) in configuration.site_cloud_access:
        if not re.match(val, user_dict.get(key, 'NO SUCH FIELD')):
            return False
    return True

def _get_instance_state_path(configuration, client_id, cloud_id):
    """Return the path where client_id stores a pickled dict of all personal
    cloud_id instances.
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    state_path = os.path.join(configuration.user_settings, client_dir,
                              cloud_id + '.state')
    return state_path

def cloud_load_instance(configuration, client_id, cloud_id, instance_id):
    """Load saved instance dictionary for client_id on cloud_id with
    concurrency support.
    Call with keyword_all as instance_id to extract all saved instances.
    """
    _logger = configuration.logger
    state_path = _get_instance_state_path(configuration, client_id, cloud_id)
    lock_path = "%s.lock" % state_path
    state_lock = acquire_file_lock(lock_path, False)
    saved_instances = unpickle(state_path, _logger)
    release_file_lock(state_lock)
    if not saved_instances:
        saved_instances = {}
    if instance_id == keyword_all:
        return saved_instances
    return saved_instances.get(instance_id, {})

def cloud_save_instance(configuration, client_id, cloud_id, instance_id,
                        instance_dict):
    """Save cloud instance dictionary for client_id on cloud_id with
    concurrency support.
    """
    _logger = configuration.logger
    save_status = False
    state_path = _get_instance_state_path(configuration, client_id, cloud_id)
    lock_path = "%s.lock" % state_path
    state_lock = acquire_file_lock(lock_path, True)
    saved_instances = unpickle(state_path, _logger)
    if not saved_instances:
        saved_instances = {}
    saved_instances[instance_id] = instance_dict
    if pickle(saved_instances, state_path, _logger):
        save_status = True
        _logger.info("saved new %s cloud instance %s for %s" % \
                     (cloud_id, instance_id, client_id))
    else:
        _logger.error("save new %s cloud instance %s for %s failed" % \
                      (cloud_id, instance_id, client_id))
    release_file_lock(state_lock)
    return save_status

def cloud_purge_instance(configuration, client_id, cloud_id,
                                instance_id):
    """Purge saved cloud instance dictionary for client_id on cloud_id with
    concurrency support.
    """
    _logger = configuration.logger
    delete_status = False
    state_path = _get_instance_state_path(configuration, client_id, cloud_id)
    lock_path = "%s.lock" % state_path
    state_lock = acquire_file_lock(lock_path, True)
    saved_instances = unpickle(state_path, _logger)
    if saved_instances and saved_instances.get(instance_id, False):
        del saved_instances[instance_id]
        if pickle(saved_instances, state_path, _logger):
            delete_status = True
            _logger.info("deleted %s cloud instance %s for %s" % \
                         (cloud_id, instance_id, client_id))
        else:
            _logger.error("delete %s cloud instance %s for %s failed" % \
                          (cloud_id, instance_id, client_id))
    else:
        _logger.error("no such %s cloud instance %s for %s to delete" % \
                      (cloud_id, instance_id, client_id))
            
    release_file_lock(state_lock)
    return delete_status


def cloud_login_username(configuration, cloud_id, instance_image):
    """Find the username for ssh login to instance_image on cloud_id.
    Uses any configured username exceptions from service confs and defaults
    to the instance_image name otherwise.
    """
    _logger = configuration.logger
    _logger.debug("find jump host for %s" %  cloud_id)
    username = instance_image
    user_map = {}
    service = cloud_find_service(configuration, cloud_id)
    if not service:
        _logger.warning("no matching service %s" % cloud_id)
        return instance_image
    user_map = service['service_user_map']
    username = user_map.get(instance_image, instance_image)
    _logger.debug("found instance image username %s for %s (%s)" % \
                  (username, instance_image, user_map))
    return username

    
def lookup_user_value_in_map(configuration, client_id, service_default,
                              override_map):
    """Helper to looup a service conf value for client_id based on the common
    structure with a service_default value and a map of user overrides.
    """
    _logger = configuration.logger
    _logger.debug("lookup user setting for %s: %s %s" % \
                  (client_id, service_default, override_map))
    for (key, val) in override_map.items():
        # Use regexp search here to match on sub-strings without anchoring
        if re.search(key, client_id):
            _logger.debug("found override %s for %s" % (val, client_id))
            return val
    _logger.debug("using default %s for %s" % (service_default, client_id))
    return service_default

def lookup_user_service_value(configuration, client_id, service, setting):
    """Lookup a user setting in service conf using the default and override
    map structure.
    """
    _logger = configuration.logger
    _logger.debug("lookup service setting %s for %s: %s" % (setting, client_id,
                                                            service))
    default = service[setting]
    overrides = service["%s_map" % setting]
    return lookup_user_value_in_map(configuration, client_id, default,
                                    overrides)

def _get_encoder(configuration, coding):
    """"""
    coding_map = {"base16": base64.b16encode, "base32": base64.b32encode,
                  "base64": base64.b64encode}
    if not coding in coding_map.keys():
        raise ValueError("invalid coding value: %s (allowed: %s)" % \
                         (coding, ', '.join(coding_map.keys())))
    return coding_map[coding]
    
    
def _get_jump_host(configuration, client_id, cloud_id, manage=False):
    """Return any configured ssh jump host ssh details including address, port
    and username for client_id on cloud_id. If the optional manage arg is set
    the two additional manage key script and coding settings are added.
    """
    _logger = configuration.logger
    jump_host = {}
    service = cloud_find_service(configuration, cloud_id)
    if not service:
        _logger.warning("no matching service %s" % cloud_id)
        return jump_host
    addr = lookup_user_service_value(configuration, client_id, service,
                                     'service_jumphost_address')
    jump_host['address'] = jump_host['fqdn'] = addr
    jump_host['fqdn'] = cloud_fqdn_from_ip(configuration, addr)[0]
    jump_host['user'] = lookup_user_service_value(
        configuration, client_id, service, 'service_jumphost_user')
    # TODO: support jumphost port with port map override?
    if manage:
        for name in ('manage_keys_script', 'manage_keys_coding'):
            jump_host[name] = service['service_jumphost_%s' % name]
    _logger.debug("found jump host for %s on %s: %s" % \
                  (client_id, cloud_id, jump_host))
    return jump_host

def cloud_login_jump_host(configuration, client_id, cloud_id):
    """Return any configured ssh jump host ssh login details including
    address, port and username for client_id on cloud_id.
    """
    return _get_jump_host(configuration, client_id, cloud_id, False)

def cloud_manage_jump_host(configuration, client_id, cloud_id):
    """Return any configured ssh jump host ssh manage details including
    manage script, network encoding, address, port and username for client_id
    on cloud_id.
    """
    return _get_jump_host(configuration, client_id, cloud_id, True)

def _manage_jump_host_keys(configuration, client_id, cloud_id, action,
                           auth_keys, ignore_disabled=True):
    """Manage the given auth_keys as allowed jump host ssh key for client_id"""
    _logger = configuration.logger
    _logger.info("%s jump host key(s) for %s on %s" % (action, client_id,
                                                       cloud_id))
    jump_host = cloud_manage_jump_host(configuration, client_id, cloud_id)
    if not jump_host['fqdn']:
        if ignore_disabled:
            return True
        else:
            _logger.warning("no jump host configured for %s" % cloud_id)
            return False

    if not action in jumphost_manage_key_actions:
        _logger.error("invalid manage jump host keys action: %s" % action)
        return False
    
    # Sanitize keys to avoid malicious or broken key entries 
    sanitized_keys = []
    for pub_key in auth_keys:
        sanitized = pub_key.strip()
        sanitized = sanitized.split('\n')[0].strip()
        if sanitized:
            sanitized_keys.append(sanitized)
    # Build non-interactive ssh command to insert pub key on jump host
    ssh_cmd = ['ssh']
    if jump_host['user']:
        ssh_cmd.append('-oUser=%(user)s' % jump_host)
    ssh_cmd.append("%(fqdn)s" % jump_host)
    # NOTE: remote script should restrict key access to reduce abuse risk with
    # command="/bin/false",no-pty,no-agent-forwarding,no-X11-forwarding PUBKEY
    # We wrap the complex input args as baseX to avoid any nasty shell effects
    encoder = _get_encoder(configuration, jump_host['manage_keys_coding'])
    ssh_cmd += [jump_host['manage_keys_script'], action,
                jump_host['manage_keys_coding'], encoder(client_id)]
    ssh_cmd += [encoder(sanitized) for sanitized in sanitized_keys]
    _logger.info("%s jump host keys with command:\n%s" % (action, ssh_cmd))
    retval = subprocess_call(ssh_cmd)
    if retval != 0:
        _logger.error("%s jump host keys failed with exit code %d" % (action,
                                                                      retval))
        return False
    _logger.info("%s jump host keys done" % action)
    return True


def cloud_add_jump_host_key(configuration, client_id, cloud_id, auth_keys,
                            ignore_disabled=True):
    """Add the given auth_keys as allowed jump host ssh key for client_id"""
    return _manage_jump_host_keys(configuration, client_id, cloud_id, 'add',
                                  auth_keys, ignore_disabled)

def cloud_remove_jump_host_key(configuration, client_id, cloud_id, auth_keys,
                            ignore_disabled=True):
    """Remove the given auth_keys as allowed jump host ssh key for client_id"""
    return _manage_jump_host_keys(configuration, client_id, cloud_id, 'remove',
                                  auth_keys, ignore_disabled)


def cloud_ssh_login_help(configuration, client_id, cloud_id, label, address,
                         port, image):
    """Return complete ssh login instructions for saved cloud_dict instance on
    cloud_id.
    """
    _logger = configuration.logger
    base_msg = """You can connect with ssh as user %s on host %s and port %d.
    """
    jump_msg = """Please note that you MUST explicitly ssh jump through host
%(fqdn)s as user %(user)s to reach the instance.
    """
    jump_host = cloud_login_jump_host(configuration, client_id, cloud_id)
    fqdn = cloud_fqdn_from_ip(configuration, address)[0]
    username = cloud_login_username(configuration, cloud_id, image)
    msg = base_msg  % (username, fqdn, port)
    jump_opt = ''
    ssh_config = """Host %s
HostName %s 
User %s
# Path to your ssh private key matching pub key set on your Cloud Setup page
IdentityFile ~/.ssh/id_rsa
IdentitiesOnly yes
""" % (label, fqdn, username)
    if jump_host['fqdn']:
        msg += jump_msg % jump_host
        jump_opt = "-J%(user)s@%(fqdn)s" % jump_host
        ssh_config += """ProxyJump %(user)s@%(fqdn)s
        """ % jump_host
    msg += """Example explicit ssh command:
ssh %s %s@%s
    """ % (jump_opt, username, fqdn)
    msg += """
Alternatively you can add something like:
%s
to your ~/.ssh/config to allow the simple ssh command:
ssh %s
    """ % (ssh_config, label)

    return msg


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


def status_all_cloud_instances(configuration, client_id, cloud_id, cloud_flavor,
                             instance_id_list, fields=['status']):
    """Status of all provided cloud instances"""
    _logger = configuration.logger
    _logger.info("status all %s cloud instances %s for %s" %
                 (cloud_id, ', '.join(instance_id_list), client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "status_all_cloud_instances")
    return helper(configuration, client_id, cloud_id, instance_id_list, fields)


def web_access_cloud_instance(configuration, client_id, cloud_id, cloud_flavor,
                              instance_id):
    """Web access for cloud instance"""
    _logger = configuration.logger
    _logger.info("web access %s cloud instance %s for %s" %
                 (cloud_id, instance_id, client_id))
    helper = __get_cloud_helper(configuration, cloud_flavor,
                                "web_access_cloud_instance")
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
    cloud_id = 'MIST'
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

    print cloud_login_jump_host(conf, client_id, cloud_id)
    service = cloud_find_service(conf, cloud_id)
    print lookup_user_service_value(conf, client_id, service,
                                    'service_sec_group_id')
    print lookup_user_service_value(conf, client_id, service,
                                    'service_key_id')
    #print cloud_add_jump_host_key(conf, client_id, cloud_id, auth_keys)
    #print cloud_remove_jump_host_key(conf, client_id, cloud_id, auth_keys)
    
    # TODO: load yaml from custom location or inline
    print "calling cloud operations for %s in %s with instance %s" % \
          (client_id, cloud_id, instance_id)
    img_list = list_cloud_images(conf, client_id, cloud_id, cloud_flavor)
    print img_list
    image_id = ''
    for (img_name, img_id, img_alias) in img_list:
        if instance_image == img_name:
            image_id = img_id

    if not reuse_instance:
        print create_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                    instance_id, image_id, auth_keys)
        # Start happens automatically on create
        time.sleep(5)
    print status_of_cloud_instance(conf, client_id, cloud_id, cloud_flavor,
                                   instance_id)
    print status_all_cloud_instances(conf, client_id, cloud_id, cloud_flavor,
                                   [instance_id])
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
