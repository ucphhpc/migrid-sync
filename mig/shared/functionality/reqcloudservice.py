#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# reqcloudservice - Redirect the user to a backend cloud service host
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

"""Backend for cloud instance management"""

import os
import re
import sys
import time

import shared.returnvalues as returnvalues
from shared.base import client_id_dir, extract_field
from shared.cloud import list_cloud_images, status_of_cloud_instance, \
     start_cloud_instance, restart_cloud_instance, stop_cloud_instance, \
     create_cloud_instance, delete_cloud_instance
from shared.defaults import session_id_bytes
from shared.fileio import pickle, unpickle
from shared.init import find_entry, initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.pwhash import generate_random_ascii
from shared.ssh import generate_ssh_rsa_key_pair

valid_actions = ('create', 'delete', 'start', 'restart', 'stop', 'status')

def cloud_host(configuration, output_objects, user, url):
    """
    Returns the users cloud openstack host
    :param configuration: the MiG Configuration object
    :param output_objects:
    :param user: the user identifier used in the Remote-User header to
    authenticate against the cloud server
    :param url: the target url of the cloud host
    :return: output_objects and a 200 OK status for the webserver to return
    to the client
    """
    _logger = configuration.logger
    _logger.info("User: %s finished, redirecting to the cloud host at: %s"
                 % (user, url))
    headers = [('Location', url), ('Remote-User', user)]
    output_objects.append({'object_type': 'start', 'headers': headers})
    return (output_objects, returnvalues.OK)


def valid_cloud_service(configuration, service):
    """
    Function that validates that the passed service is correctly structured.
    :param configuration: the MiG Configuration object
    :param service: a service dictionary object that describes a cloud service
    """
    _logger = configuration.logger
    if not isinstance(service, dict):
        _logger.error('The cloud service %s has an incorrect structure %s,'
                      ' requires dictionary' % (service, type(service)))
        return False

    if 'service_name' not in service:
        _logger.error(
            "The cloud service %s is missing a required service_name key"
            % service)
        return False

    if 'service_hosts' not in service:
        _logger.error(
            "The cloud service %s is missing a required hosts key"
            % service)
        return False
    return True


def signature():
    """Signature of the main function"""
    defaults = {
        'service': REJECT_UNSET,
        'instance_id': [],
        'instance_image': [],
        'action': ['status']
    }
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )

    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    logger.debug("User: %s executing %s" % (client_id, op_name))
    if not configuration.site_enable_cloud:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'The cloud service is not enabled on the system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    return_status = returnvalues.OK
    action = accepted['action'][-1]
    # NOTE: instance_id/image may be empty list - fall back to empty string
    instance_id = ([''] + accepted['instance_id'])[-1]
    instance_image = ([''] + accepted['instance_image'])[-1]
    requested_service = accepted['service'][-1]
    service = {k: v for options in configuration.cloud_services
               for k, v in options.items()
               if options['service_name'] == requested_service}

    if not service:
        valid_services = [options['name']
                          for options in configuration.cloud_services]
        output_objects.append(
            {'object_type': 'error_text',
             'text': '%s is not a valid cloud service, '
             'allowed include %s' % (requested_service, valid_services)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    valid_service = valid_cloud_service(configuration, service)
    if not valid_service:
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'The service %s appears to be misconfigured, '
             'please contact a system administrator about this issue'
             % requested_service}
        )
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # TODO: split into edit and query actions and add POST checks for edit
    if not action in valid_actions:
        output_objects.append(
            {'object_type': 'error_text', 'text': '%s is not a valid action '
             'allowed actions include %s' % (action, ', '.join(valid_actions))
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    user_home_dir = os.path.join(configuration.user_home, client_dir)

    # Users store a pickled dict of all personal instances
    cloud_instance_state_path = os.path.join(configuration.user_settings,
                                             client_dir, requested_service + '.state')
    # TODO: lookup proper ID instead of name.lower()
    cloud_id = requested_service.lower()
    instance_ssh_fqdn = configuration.user_cloud_ssh_address
    instance_ssh_port = configuration.user_cloud_ssh_port

    client_email = extract_field(client_id, 'email')
    if not client_email:
        logger.error("could not extract client email for %s!" % client_id)
        output_objects.append({
            'object_type': 'error_text', 'text':
            "No client ID found - can't continue"})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    ssh_connect_msg = "You can connect to it with ssh on host %s and " + \
                      "port %d"
    instance_missing_msg = "Found no '%s' instance at %s. Please contact a " \
                           + "site administrator if it should be there."
    
    if "create" == action:
        saved_instances = unpickle(cloud_instance_state_path, logger)
        if not saved_instances:
            saved_instances = {}
        if saved_instances.get(instance_id, None):
            logger.error("Refused %s re-create %s cloud instance %s!" % \
                         (client_id, cloud_id, instance_id))
            output_objects.append({
                'object_type': 'error_text', 'text':
                "You already have an instance with that ID!"})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        if not instance_image:
            instance_image = list_cloud_images(configuration, client_id,
                                               cloud_id)[0]
            logger.info("No image specified - using first for %s in %s: %s" % \
                         (client_id, cloud_id, instance_image))
            
        # Create a new keyset and session id
        (priv_key, pub_key) = generate_ssh_rsa_key_pair(encode_utf8=True)
        session_id = generate_random_ascii(2*session_id_bytes,
                                           charset='0123456789abcdef')
        instance_id = "%s_%s_%s" % (client_email, instance_image, session_id)
        # TODO: make more fields flexible/conf
        cloud_dict = {
            'INSTANCE_ID': instance_id,
            'SESSIONID': session_id,
            'USER_CERT': client_id,
            'INSTANCE_PRIVATE_KEY': priv_key,
            'INSTANCE_PUBLIC_KEY': pub_key,
            # don't need fraction precision, also not all systems provide fraction
            # precision.
            'CREATED_TIMESTAMP': int(time.time()),
            'INSTANCE_SSH_IP': instance_ssh_fqdn,
            'INSTANCE_SSH_PORT': instance_ssh_port,
            'INSTANCE_IMAGE': instance_image
            }
        (action_status, action_msg) = create_cloud_instance(configuration, client_id,
                                              cloud_id, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, instance_id, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # On success the action_msg contains the assigned floating IP address
        instance_ssh_fqdn = action_msg
        cloud_dict['INSTANCE_SSH_IP'] = instance_ssh_fqdn
        saved_instances[instance_id] = cloud_dict
        if not pickle(saved_instances, cloud_instance_state_path, logger):
            logger.error("pickle new %s cloud instance %s for %s failed" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Error saving your %s cloud instance setup' % cloud_id
                })
            return (output_objects, returnvalues.SYSTEM_ERROR)
            
        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, instance_id, cloud_id, "success")})
        output_objects.append({
            'object_type': 'text', 'text': ssh_connect_msg % \
            (instance_ssh_fqdn, instance_ssh_port)})
    
    elif "delete" == action:
        saved_instances = unpickle(cloud_instance_state_path, logger)
        if not saved_instances or not saved_instances.get(instance_id, None):
            logger.error("no saved %s cloud instance %s for %s to delete" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (instance_id, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)

        (action_status, action_msg) = delete_cloud_instance(configuration, client_id,
                                              cloud_id, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, instance_id, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        del saved_instances[instance_id]
        if not pickle(saved_instances, cloud_instance_state_path, logger):
            logger.error("pickle removed %s cloud instance %s for %s failed" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Error updating your %s cloud instance setup' % cloud_id
                })
            return (output_objects, returnvalues.SYSTEM_ERROR)
            
        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, instance_id, cloud_id, "success")})
    
    elif "status" == action:
        saved_instances = unpickle(cloud_instance_state_path, logger)
        if not saved_instances or not saved_instances.get(instance_id, None):
            logger.error("no saved %s cloud instance %s for %s to query" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (instance_id, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        (action_status, action_msg) = status_of_cloud_instance(
            configuration, client_id, cloud_id, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, instance_id, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        cloud_dict = saved_instances.get(instance_id, {})
        instance_ssh_fqdn = cloud_dict.get('INSTANCE_SSH_IP', 'UNKNOWN')
        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, instance_id, cloud_id, action_msg)})
        output_objects.append({
            'object_type': 'text', 'text': ssh_connect_msg % \
            (instance_ssh_fqdn, instance_ssh_port)})

    elif "start" == action:
        saved_instances = unpickle(cloud_instance_state_path, logger)
        if not saved_instances or not saved_instances.get(instance_id, None):
            logger.error("no saved %s cloud instance %s for %s to start" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (instance_id, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        (action_status, action_msg) = start_cloud_instance(
            configuration, client_id, cloud_id, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, instance_id, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        cloud_dict = saved_instances.get(instance_id, {})
        instance_ssh_fqdn = cloud_dict.get('INSTANCE_SSH_IP', 'UNKNOWN')
        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, instance_id, cloud_id, "success")})
        output_objects.append({
            'object_type': 'text', 'text': ssh_connect_msg % \
            (instance_ssh_fqdn, instance_ssh_port)})

    elif "restart" == action:
        saved_instances = unpickle(cloud_instance_state_path, logger)
        if not saved_instances or not saved_instances.get(instance_id, None):
            logger.error("no saved %s cloud instance %s for %s to restart" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (instance_id, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        (action_status, action_msg) = restart_cloud_instance(configuration, client_id,
                                            cloud_id, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, instance_id, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        cloud_dict = saved_instances.get(instance_id, {})
        instance_ssh_fqdn = cloud_dict.get('INSTANCE_SSH_IP', 'UNKNOWN')
        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, instance_id, cloud_id, "success")})
        output_objects.append({
            'object_type': 'text', 'text': ssh_connect_msg % \
            (instance_ssh_fqdn, instance_ssh_port)})

    elif "stop" == action:
        saved_instances = unpickle(cloud_instance_state_path, logger)
        if not saved_instances or not saved_instances.get(instance_id, None):
            logger.error("no saved %s cloud instance %s for %s to %s" % \
                         (cloud_id, instance_id, client_id, action))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (instance_id, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
            
        (action_status, action_msg) = stop_cloud_instance(configuration, client_id,
                                            cloud_id, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, instance_id, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, instance_id, cloud_id, "success")})

    else:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Unknown action: %s' % action})
        return_status = returnvalues.CLIENT_ERROR

    output_objects.append({'object_type': 'link',
                           'destination': 'cloud.py',
                           'class': 'backlink iconspace',
                           'title': 'Go back to cloud management',
                           'text': 'Back to cloud management'})
    return (output_objects, return_status)
        

if __name__ == "__main__":
    if not os.environ.get('MIG_CONF', ''):
        conf_path = os.path.join(os.path.dirname(sys.argv[0]),
                                 '..', '..', 'server', 'MiGserver.conf')
        os.environ['MIG_CONF'] = conf_path

    client_id = ' ME '
    cloud_is = 'mist'
    instance_id = 'My-Misty-Test-01'
    action = 'status'
    if sys.argv[1:]:
        client_id = sys.argv[1]
    if sys.argv[2:]:
        cloud_id = sys.argv[2]
    if sys.argv[3:]:
        instance_id = sys.argv[3]
    if sys.argv[4:]:
        action = sys.argv[4]
    print main(client_id, {'cloud_id': cloud_id, 'instance_id': instance_id,
                           'action': action})
    exit(0)
