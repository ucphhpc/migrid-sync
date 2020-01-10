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
     update_cloud_instance_keys, create_cloud_instance, delete_cloud_instance, \
     web_access_cloud_instance, cloud_access_allowed, cloud_login_username, \
     cloud_ssh_login_help, cloud_build_instance_id, cloud_split_instance_id, \
     cloud_load_instance, cloud_save_instance, cloud_purge_instance, \
     cloud_edit_actions, cloud_manage_actions
from shared.defaults import session_id_bytes, keyword_all
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import safe_handler, get_csrf_limit
from shared.init import find_entry, initialize_main_variables
from shared.pwhash import generate_random_ascii
from shared.settings import load_cloud
from shared.ssh import generate_ssh_rsa_key_pair
from shared.useradm import get_full_user_map

valid_actions = cloud_edit_actions + cloud_manage_actions

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

def _ssh_help(configuration, client_id, cloud_id, cloud_dict,
              instance_id):
    """Wrap the call to ssh login helper using saved info for instance_id"""
    label = cloud_dict.get('INSTANCE_LABEL', 'UNKNOWN')
    address = cloud_dict.get('INSTANCE_SSH_IP', '')
    port = cloud_dict.get('INSTANCE_SSH_PORT', '')
    image = cloud_dict.get('INSTANCE_IMAGE', 'UNKNOWN')
    msg = cloud_ssh_login_help(configuration, client_id, cloud_id, label,
                               address, port, image)
    # Wrap lines as html
    return msg.replace('\n', '<br/>')


def signature():
    """Signature of the main function"""
    defaults = {
        'service': REJECT_UNSET,
        'instance_id': [],
        'instance_label': [],
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

    output_objects.append({'object_type': 'header',
                           'text': 'Cloud Instance Management'})

    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    # Optional limitation of cload access vgrid permission
    if not user_dict or not cloud_access_allowed(configuration, user_dict):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "You don't have permission to access the cloud facilities on "
             "this site"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    return_status = returnvalues.OK
    action = accepted['action'][-1]
    # NOTE: instance_X may be empty list - fall back to empty string
    instance_id = ([''] + accepted['instance_id'])[-1]
    instance_label = ([''] + accepted['instance_label'])[-1]
    instance_image = ([''] + accepted['instance_image'])[-1]
    cloud_id = accepted['service'][-1]
    service = {k: v for options in configuration.cloud_services
               for k, v in options.items()
               if options['service_name'] == cloud_id}

    if not service:
        valid_services = [options['service_name']
                          for options in configuration.cloud_services]
        output_objects.append(
            {'object_type': 'error_text',
             'text': '%s is not among the valid cloud services: %s' % \
             (cloud_id, ', '.join(valid_services))})
        return (output_objects, returnvalues.CLIENT_ERROR)

    valid_service = valid_cloud_service(configuration, service)
    if not valid_service:
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'The service %s appears to be misconfigured, '
             'please contact a system administrator about this issue'
             % cloud_id}
        )
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not action in valid_actions:
        output_objects.append(
            {'object_type': 'error_text', 'text': '%s is not a valid action '
             'allowed actions include %s' % (action, ', '.join(valid_actions))
             })
        return (output_objects, returnvalues.CLIENT_ERROR)
    elif action in cloud_edit_actions:
        if not safe_handler(configuration, 'post', op_name, client_id,
                            get_csrf_limit(configuration), accepted):
            output_objects.append(
                {'object_type': 'error_text', 'text': '''Only accepting
                CSRF-filtered POST requests to prevent unintended updates'''
                 })
            return (output_objects, returnvalues.CLIENT_ERROR)

    allowed_images = service.get('service_allowed_images', keyword_all)
    if allowed_images != keyword_all and instance_image and \
           not instance_image in allowed_images:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "You don't have permission to create %s images on %s" % \
             cloud_id
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    cloud_flavor = service.get("service_flavor", "openstack")
    user_home_dir = os.path.join(configuration.user_home, client_dir)

    client_email = extract_field(client_id, 'email')
    if not client_email:
        logger.error("could not extract client email for %s!" % client_id)
        output_objects.append({
            'object_type': 'error_text', 'text':
            "No client ID found - can't continue"})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    ssh_auth_msg = "Login requires your private key for your public key:"
    instance_missing_msg = "Found no '%s' instance at %s. Please contact a " \
                           + "site administrator if it should be there."

    _label = instance_label
    if instance_id and not _label:
        _, _label, _ = cloud_split_instance_id(configuration, client_id,
                                               instance_id)
        
    if "create" == action:    
        # Load all instances and make sure none contains label in ID
        saved_instances = cloud_load_instance(configuration, client_id,
                                              cloud_id, keyword_all)
        for (saved_id, instance) in saved_instances.items():
            if instance_label == instance.get('INSTANCE_LABEL', saved_id):
                logger.error("Refused %s re-create %s cloud instance %s!" % \
                                      (client_id, cloud_id, instance_label))
                output_objects.append({
                    'object_type': 'error_text', 'text':
                    "You already have an instance with the label '%s'!" % \
                    instance_label})
                return (output_objects, returnvalues.CLIENT_ERROR)
        max_user_instances = int(service.get('service_max_user_instances', -1))
        if max_user_instances > 0 and \
               len(saved_instances) >= max_user_instances:
            logger.error("Refused %s create additional %s cloud instances!" % \
                                      (client_id, cloud_id))
            output_objects.append({
                'object_type': 'error_text', 'text':
                "You already have the maximum allowed %s instances (%d)!" % \
                (cloud_id, max_user_instances)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        if not instance_label:
            logger.error("Refused %s create unlabelled %s cloud instance!" % \
                         (client_id, cloud_id))
            output_objects.append({
                'object_type': 'error_text', 'text':
                "No instance label provided!"})
            return (output_objects, returnvalues.CLIENT_ERROR)

        (img_status, img_list) = list_cloud_images(
            configuration, client_id, cloud_id, cloud_flavor)
        if not img_status or not img_list:
            logger.error("No valid images found for %s in %s" % \
                         (client_id, cloud_id))
            output_objects.append({
                'object_type': 'error_text', 'text':
                "No valid images found!"})
            return (output_objects, returnvalues.CLIENT_ERROR)

        if not instance_image:
            instance_image = img_list[0]
            logger.info("No image specified - using first for %s in %s: %s" % \
                        (client_id, cloud_id, instance_image))

        for (img_name, img_id, img_alias) in img_list:
            if instance_image == img_name:
                image_id = img_id
                break

        if not image_id:
            logger.error("No matching image ID found for %s in %s: %s" % \
                         (client_id, cloud_id, instance_image))
            output_objects.append({
                'object_type': 'error_text', 'text':
                "No such  image found: %s" % instance_image})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # TODO: remove this direct key injection if we can delay it
        cloud_settings = load_cloud(client_id, configuration)
        raw_keys = cloud_settings.get('authkeys', '').split('\n')
        auth_keys = [i.split('#', 1)[0].strip() for i in raw_keys]
        auth_keys = [i for i in auth_keys if i]
        if not auth_keys:
            logger.error("No cloud pub keys setup for %s - refuse create" % \
                         client_id)
            output_objects.append({
                'object_type': 'error_text', 'text':
                """
You haven't provided any valid ssh pub key(s) for cloud instance login, which
is stricly required for all use. Please do so before you try again.
            """})
            output_objects.append({
                'object_type': 'link', 'destination': 'setup.py?topic=cloud',
                'text': 'Open cloud setup', 'class': 'cloudsetuplink iconspace',
                'title': 'open cloud setup', 'target': '_blank'})
            return (output_objects, returnvalues.CLIENT_ERROR)

        logger.debug("Continue create for %s with auth_keys: %s" % \
                     (client_id, auth_keys))

        # Create a new internal keyset and session id
        (priv_key, pub_key) = generate_ssh_rsa_key_pair(encode_utf8=True)
        session_id = generate_random_ascii(session_id_bytes,
                                           charset='0123456789abcdef')
        # We make sure to create instance with a globally unique ID on the
        # cloud while only showing the requested instance_label to the user.
        instance_id = cloud_build_instance_id(configuration, client_email,
                                              instance_label, session_id)
        # TODO: make more fields flexible/conf
        cloud_dict = {
            'INSTANCE_ID': instance_id,
            'INSTANCE_LABEL': instance_label,
            'INSTANCE_IMAGE': instance_image,
            'IMAGE_ID': image_id,
            'AUTH_KEYS': auth_keys,
            'USER_CERT': client_id,
            'INSTANCE_PRIVATE_KEY': priv_key,
            'INSTANCE_PUBLIC_KEY': pub_key,
            # don't need fraction precision, also not all systems provide fraction
            # precision.
            'CREATED_TIMESTAMP': int(time.time()),
            # Init unset ssh address and leave for floating IP assigment below
            'INSTANCE_SSH_IP': '',
            'INSTANCE_SSH_PORT': 22,
            }
        (action_status, action_msg) = create_cloud_instance(
            configuration, client_id, cloud_id, cloud_flavor, instance_id,
            image_id, auth_keys)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, instance_label, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # On success the action_msg contains the assigned floating IP address
        instance_ssh_fqdn = action_msg
        cloud_dict['INSTANCE_SSH_IP'] = instance_ssh_fqdn
        if not cloud_save_instance(configuration, client_id, cloud_id,
                                   instance_id, cloud_dict):
            logger.error("save new %s cloud instance %s for %s failed" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Error saving your %s cloud instance setup' % cloud_id
                })
            return (output_objects, returnvalues.SYSTEM_ERROR)
            
        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, instance_label, cloud_id, "success")})
        output_objects.append({
            'object_type': 'html_form', 'text': _ssh_help(
                configuration, client_id, cloud_id, cloud_dict, instance_id)})
    
    elif "delete" == action:
        saved_instance = cloud_load_instance(configuration, client_id,
                                             cloud_id, instance_id)
        if not saved_instance:
            logger.error("no saved %s cloud instance %s for %s to delete" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (_label, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)

        (action_status, action_msg) = delete_cloud_instance(
            configuration, client_id, cloud_id, cloud_flavor, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, _label, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        if not cloud_purge_instance(configuration, client_id, cloud_id,
                                    instance_id):
            logger.error("purge %s cloud instance %s for %s failed" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Error deleting your %s cloud instance setup' % \
                cloud_id
                })
            return (output_objects, returnvalues.SYSTEM_ERROR)
            
        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, _label, cloud_id, "success")})
    
    elif "status" == action:
        saved_instance = cloud_load_instance(configuration, client_id,
                                             cloud_id, instance_id)
        if not saved_instance:
            logger.error("no saved %s cloud instance %s for %s to query" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (_label, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        (action_status, action_msg) = status_of_cloud_instance(
            configuration, client_id, cloud_id, cloud_flavor, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, _label, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, _label, cloud_id, action_msg)})

        # Show web console and ssh details if running
        if action_msg in ('ACTIVE', 'RUNNING'):
            (console_status, console_msg) = web_access_cloud_instance(
                configuration, client_id, cloud_id, cloud_flavor, instance_id)
            if not console_status:
                logger.error("%s cloud instance %s console for %s failed: %s" \
                             % (cloud_id, instance_id, client_id, console_msg))
                output_objects.append({
                    'object_type': 'error_text',
                    'text': 'Failed to get instance %s at %s console: %s' % \
                    (_label, cloud_id, console_msg)})
                return (output_objects, returnvalues.SYSTEM_ERROR)
            output_objects.append({
                'object_type': 'link', 'destination': console_msg,
                'text': 'Open web console', 'class': 'consolelink iconspace',
                'title': 'open web console', 'target': '_blank'})
            output_objects.append({'object_type': 'text', 'text': ''})

            output_objects.append({
                'object_type': 'html_form', 'text': _ssh_help(
                    configuration, client_id, cloud_id, saved_instance,
                    instance_id)})

        output_objects.append({'object_type': 'text', 'text': ''})

    elif "start" == action:
        saved_instance = cloud_load_instance(configuration, client_id,
                                             cloud_id, instance_id)
        if not saved_instance:
            logger.error("no saved %s cloud instance %s for %s to start" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (_label, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        (action_status, action_msg) = start_cloud_instance(
            configuration, client_id, cloud_id, cloud_flavor, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, _label, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, _label, cloud_id, "success")})
        output_objects.append({
            'object_type': 'html_form', 'text': _ssh_help(
                configuration, client_id, cloud_id, saved_instance,
                instance_id)})

    elif action in ("softrestart", "hardrestart"):
        boot_strength = action.replace("restart", "").upper()
        saved_instance = cloud_load_instance(configuration, client_id,
                                             cloud_id, instance_id)
        if not saved_instance:
            logger.error("no saved %s cloud instance %s for %s to restart" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (_label, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        (action_status, action_msg) = restart_cloud_instance(
            configuration, client_id, cloud_id, cloud_flavor, instance_id,
            boot_strength)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, _label, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, _label, cloud_id, "success")})
        output_objects.append({
            'object_type': 'html_form', 'text': _ssh_help(
                configuration, client_id, cloud_id, saved_instance,
                instance_id)})

    elif "stop" == action:
        saved_instance = cloud_load_instance(configuration, client_id,
                                             cloud_id, instance_id)
        if not saved_instance:
            logger.error("no saved %s cloud instance %s for %s to %s" % \
                         (cloud_id, instance_id, client_id, action))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (_label, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
            
        (action_status, action_msg) = stop_cloud_instance(
            configuration, client_id, cloud_id, cloud_flavor, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, _label, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, _label, cloud_id, "success")})

    elif "webaccess" == action:
        saved_instance = cloud_load_instance(configuration, client_id,
                                             cloud_id, instance_id)
        if not saved_instance:
            logger.error("no saved %s cloud instance %s for %s to query" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (_label, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)
            
        (action_status, action_msg) = web_access_cloud_instance(
            configuration, client_id, cloud_id, cloud_flavor, instance_id)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, _label, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s" % \
            (action, _label, cloud_id)})
        output_objects.append({
            'object_type': 'link', 'destination': action_msg,
            'text': 'Open web console', 'class': 'consolelink iconspace',
            'title': 'open web console', 'target': '_blank'})
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({
            'object_type': 'html_form', 'text': _ssh_help(
                configuration, client_id, cloud_id, saved_instance,
                instance_id)})

    elif "updatekeys" == action:
        saved_instance = cloud_load_instance(configuration, client_id,
                                             cloud_id, instance_id)
        if not saved_instance:
            logger.error("no saved %s cloud instance %s for %s to update" % \
                         (cloud_id, instance_id, client_id))
            output_objects.append(
                {'object_type': 'error_text', 'text': instance_missing_msg % \
                 (_label, cloud_id)})
            return (output_objects, returnvalues.CLIENT_ERROR)

        cloud_settings = load_cloud(client_id, configuration)
        auth_keys = cloud_settings.get('authkeys', '').split('\n')
        (action_status, action_msg) = update_cloud_instance_keys(
            configuration, client_id, cloud_id, cloud_flavor, instance_id,
            auth_keys)
        if not action_status:
            logger.error("%s %s cloud instance %s for %s failed: %s" % \
                         (action, cloud_id, instance_id, client_id,
                          action_msg))
            output_objects.append({
                'object_type': 'error_text',
                'text': 'Your %s instance %s at %s did not succeed: %s' % \
                (action, _label, cloud_id, action_msg)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({
            'object_type': 'text', 'text': "%s instance %s at %s: %s" % \
            (action, _label, cloud_id, "success")})
        output_objects.append({
            'object_type': 'html_form', 'text': _ssh_help(
                configuration, client_id, cloud_id, saved_instance,
                instance_id)})
        output_objects.append({
            'object_type': 'text', 'text': ssh_auth_msg})
        for pub_key in auth_keys:
            output_objects.append({
                'object_type': 'text', 'text': pub_key})

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
