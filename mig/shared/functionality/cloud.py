
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cloud - user control for the available cloud services
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

"""A page for dislaying and managing available cloud instances. Provides a
list of tabs/buttons based on cloud services defined in the
configuration.cloud_services entries.
"""

import os

import shared.returnvalues as returnvalues

from shared.base import client_id_dir
from shared.fileio import unpickle
from shared.functional import validate_input_and_cert
from shared.init import find_entry, initialize_main_variables
from shared.html import man_base_js


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['cloud', defaults]


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

    logger.debug("User: %s executing %s", client_id, op_name)
    if not configuration.site_enable_cloud:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'The cloud service is not enabled on the system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not configuration.site_enable_sftp_subsys and not \
            configuration.site_enable_sftp:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'The required sftp service is not enabled on the system'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    services = [{'object_type': 'service',
                 'name': options['service_name'],
                 'description': options.get('service_desc', '')}
                for options in configuration.cloud_services]

    # Show cloud services menu
    (add_import, add_init, add_ready) = man_base_js(configuration, [])

    add_ready += '''
        /* NOTE: requires managers CSS fix for proper tab bar height */
        $(".cloud-tabs").tabs();
    '''

    title_entry = find_entry(output_objects, 'title')
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'header',
                           'text': 'Select a Cloud Service'})

    fill_helpers = {
        'cloud_tabs': ''.join(['<li><a href="#%s-tab">%s</a></li>' %
                               (service['name'], service['name'])
                               for service in services])
    }

    output_objects.append({'object_type': 'html_form', 'text': '''
    <div id="wrap-tabs" class="cloud-tabs">
    <ul>
    %(cloud_tabs)s
    </ul>
    ''' % fill_helpers})

    action_list = [('start', 'Start'), ('status', 'Status of'),
                   ('restart', 'Restart'), ('stop', 'Stop'),
                   ('create', 'Create'), ('delete', 'Delete')]
    for service in services:
        # TODO: add a true ID instead?
        cloud_id = service['name']
        output_objects.append({'object_type': 'html_form',
                               'text': '''
        <div id="%s-tab">
        ''' % (service['name'])})

        if service['description']:
            output_objects.append({'object_type': 'sectionheader',
                                   'text': 'Service Description'})
        output_objects.append({'object_type': 'html_form', 'text': '''
        <div class="cloud-description">
        <span>%s</span>
        </div>
        ''' % service['description']})
        output_objects.append({'object_type': 'html_form', 'text': '''
        <br/>
        '''})

        # Users store a pickled dict of all personal instances
        cloud_instance_state_path = os.path.join(configuration.user_settings,
                                                 client_dir,
                                                 cloud_id + '.state')
        # Manage existing instances
        saved_instances = unpickle(cloud_instance_state_path, logger)
        if not saved_instances:
            saved_instances = {}
        for (instance_id, instance_dict) in saved_instances.items():
            logger.debug("Management entries for %s %s cloud instance %s" % \
                         (client_id, cloud_id, instance_id))

            output_objects.append({'object_type': 'html_form', 'text': """
            <div class='cloud-management'>
            <h3>%s</h3>
            """ % instance_id})
            for (action, title) in action_list:
                query = 'action=%s;service=%s;instance_id=%s' % \
                        (action, cloud_id, instance_id)
                if 'create' == action:
                    continue

                if 'delete' == action:
                    # TODO: add confirm dialog
                    pass

                url = 'reqcloudservice.py?%s' % query
                output_service = {
                    'object_type': 'service',
                    'name': "%s %s instance" % (title, service['name']),
                    'targetlink': url
                    }
                output_objects.append(output_service)
            output_objects.append({'object_type': 'html_form', 'text': """
            </div>
            """})

        logger.debug("Create new %s %s cloud instance" % \
                         (client_id, cloud_id))

        output_objects.append({'object_type': 'html_form', 'text': """
            <div class='cloud-instance-create'>
            <div class='cloud-management'>
            <h3>Create a new %s cloud instance</h3>
            """ % cloud_id})
        # Create new instance
        for (action, title) in action_list:
            if 'create' != action:
                    continue
            # TODO: let user select image
            instance_id, instance_image = "", ""
            query = 'action=%s;service=%s;instance_id=%s' % \
                    (action, cloud_id, instance_id)
            query += ';instance_image=%s' % instance_image
            url = 'reqcloudservice.py?%s' % query
            output_service = {
                'object_type': 'service',
                'name': "%s %s instance" % (title, service['name']),
                'targetlink': url
                }
            output_objects.append(output_service)

        output_objects.append({'object_type': 'html_form', 'text': '''
        </div>
        '''})
    output_objects.append({'object_type': 'html_form', 'text': '''
    </div>
    </div>
    '''})

    return (output_objects, returnvalues.OK)
