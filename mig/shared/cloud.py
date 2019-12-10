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

import os
import sys
import time

try:
    import openstack
except ImportError, err:
    print 'WARNING: import failed: %s' % err
    openstack = None

from shared.defaults import keyword_all

def __check_openstack(func):
    """Internal helper to verify openstack module availability before use"""
    if openstack is None:
        raise Exception("cloud functions require openstackclient")
    return func

def __wait_available(configuration, client_id, cloud_id, instance_id):
    """Wait for instance_id to be truly available after create"""
    # TODO: lookup the openstack client V3 version of the utils.wait_for_X
    try:
        utils.wait_for_status(cloud_id, instance_id)
    except Exception, exc:
        print "Error: wait failed: %s" % exc
        time.sleep(5)
    return True

def __wait_gone(configuration, client_id, cloud_id, instance_id):
    """Wait for instance_id to be truly gone after delete"""
    try:
        utils.wait_for_delete(cloud_id, instance_id)
    except Exception, exc:
        print "Error: wait failed: %s" % exc
        time.sleep(5)

    return True

def cloud_connect(configuration, cloud_id):
    """Shared helper to connect to the cloud with basic setup handled"""
    _logger = configuration.logger
    _logger.info("connect to %s" % cloud_id)
    conn = openstack.connect(cloud=cloud_id)
    openstack.enable_logging(debug=False)
    return (_logger, conn)

@__check_openstack
def list_cloud_images(configuration, client_id, cloud_id):
    """Fetch the list of available cloud images"""
    _logger, conn = cloud_connect(configuration, cloud_id)
    _logger.info("list %s cloud images for %s" % (cloud_id, client_id))

    img_list = []
    for image in conn.image.images():
        img_list.append(image.name)
    return img_list

@__check_openstack
def start_cloud_instance(configuration, client_id, cloud_id, instance_id):
    """Start provided cloud instance"""
    _logger, conn = cloud_connect(configuration, cloud_id)
    _logger.info("start %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                        client_id))

    status, msg = True, ''
    server = conn.compute.find_server(instance_id)
    if not server:
        status = False
        _logger.error("%s failed to locate %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)
    msg = conn.compute.start_server(server)
    if msg:
        status = False
        _logger.error("%s failed to start %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
    else:
        _logger.info("%s started cloud %s instance %s" % \
                     (client_id, cloud_id, instance_id))
    return (status, msg)

@__check_openstack
def stop_cloud_instance(configuration, client_id, cloud_id, instance_id):
    """Stop provided cloud instance"""
    _logger, conn = cloud_connect(configuration, cloud_id)
    _logger.info("stop %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                       client_id))

    status, msg = True, ''
    server = conn.compute.find_server(instance_id)
    if not server:
        status = False
        _logger.error("%s failed to locate %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)
    msg = conn.compute.stop_server(server)
    if msg:
        status = False
        _logger.error("%s failed to stop %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
    else:
        _logger.info("%s stopped cloud %s instance %s" % \
                     (client_id, cloud_id, instance_id))
    return (status, msg)

@__check_openstack
def restart_cloud_instance(configuration, client_id, cloud_id, instance_id,
                           boot_strength="HARD"):
    """Reboot provided cloud instance. Use SOFT or HARD as boot_strength"""
    _logger, conn = cloud_connect(configuration, cloud_id)
    _logger.info("restart %s cloud instance %s for %s" % (cloud_id,
                                                          instance_id,
                                                          client_id))

    status, msg = True, ''
    server = conn.compute.find_server(instance_id)
    if not server:
        status = False
        _logger.error("%s failed to locate %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)
    msg = conn.compute.reboot_server(server, boot_strength)
    if msg:
        status = False
        _logger.error("%s failed to restart %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
    else:
        _logger.info("%s restarted cloud %s instance %s" % \
                     (client_id, cloud_id, instance_id))

    return (status, msg)

@__check_openstack
def create_cloud_instance(configuration, client_id, cloud_id, instance_id):
    """Create named cloud instance for user"""
    _logger, conn = cloud_connect(configuration, cloud_id)
    _logger.info("create %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                         client_id))

    status, msg = True, ''

    # TODO: move to args or conf
    image_id = '15403ba1-89d8-429a-a670-1f72d8faf6ca'
    flavor_id = '176b73c9-1644-46c6-9c64-90bd73e92492'
    network_id = 'b562785d-5286-4c3d-a834-13ab427af920'
    key_pair_id = 'erda-keypair'
    sec_group_id = '3ed57f38-7f2d-4541-8241-849377f495bd'
    floating_network_id = 'ecee5c29-037a-4225-a2df-6412674e8fb5'
    availability_zone = 'NFS'

    public_network = "130.225.104.0/24"

    server = conn.create_server(instance_id, image=image_id,
                                availability_zone=availability_zone,
                                key_name=key_pair_id, flavor=flavor_id,
                                network=network_id,
                                security_groups=sec_group_id)
    if not server:
        status = False
        msg = "%s" % server
        _logger.error("%s failed to create %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)

    # Create floating IP from public network
    floating_ip = conn.network.create_ip(floating_network_id=floating_network_id)
    if not floating_ip:
        status = False
        msg = "%s" % floating_ip
        _logger.error("%s failed to create %s cloud instance ip: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)

    __wait_available(configuration, client_id, cloud_id, instance_id)

    # Add floating IP to instance
    conn.compute.add_floating_ip_to_server(
        server.id, floating_ip.floating_ip_address)
    if not floating_ip.floating_ip_address:
        status = False
        _logger.error("%s failed to create %s cloud instance float ip: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)

    _logger.info("%s created cloud %s instance %s" % \
                     (client_id, cloud_id, instance_id))
    return (status, msg)


@__check_openstack
def delete_cloud_instance(configuration, client_id, cloud_id, instance_id):
    """Delete provided cloud instance"""
    _logger, conn = cloud_connect(configuration, cloud_id)
    _logger.info("delete %s cloud instance %s for %s" % (cloud_id, instance_id,
                                                         client_id))

    status, msg = True, ''
    server = conn.compute.find_server(instance_id)
    if not server:
        status = False
        _logger.error("%s failed to locate %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)
    msg = conn.compute.delete_server(server)
    if msg:
        status = False
        _logger.error("%s failed to delete %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)
    
    __wait_gone(configuration, client_id, cloud_id, instance_id)
    msg = conn.delete_unattached_floating_ips(retry=1)
    if msg:
        status = False
        _logger.error("%s failed to free IP for %s cloud instance: %s" % \
                      (client_id, instance_id, msg))
        return (status, msg)

    _logger.info("%s created cloud %s instance %s" % \
                     (client_id, cloud_id, instance_id))
    return (status, msg)

if __name__ == "__main__":
    from shared.conf import get_configuration_object
    conf = get_configuration_object()
    client_id = ' ME '
    cloud_id = 'mist'
    instance_id = 'My-Misty-Test-42'
    # TODO: load yaml from custom location or inline
    print "calling cloud operations for %s in %s with instance %s" % \
          (client_id, cloud_id, instance_id)
    print list_cloud_images(conf, client_id, cloud_id)
    print create_cloud_instance(conf, client_id, cloud_id, instance_id)
    # Start happens automatically on create
    time.sleep(5)
    print restart_cloud_instance(conf, client_id, cloud_id, instance_id)
    time.sleep(5)
    print stop_cloud_instance(conf, client_id, cloud_id, instance_id)
    time.sleep(5)
    print start_cloud_instance(conf, client_id, cloud_id, instance_id)
    time.sleep(5)
    print stop_cloud_instance(conf, client_id, cloud_id, instance_id)
    time.sleep(5)
    print delete_cloud_instance(conf, client_id, cloud_id, instance_id)

