
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
from shared.cloud import check_cloud_available, list_cloud_images, \
     status_all_cloud_instances, cloud_access_allowed, cloud_edit_actions
from shared.defaults import csrf_field
from shared.fileio import unpickle
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.init import find_entry, initialize_main_variables
from shared.html import man_base_js, man_base_html, html_post_helper
from shared.useradm import get_full_user_map


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

    status = returnvalues.OK
    user_map = get_full_user_map(configuration)
    user_dict = user_map.get(client_id, None)
    # Optional limitation of cloud access permission
    if not user_dict or not cloud_access_allowed(configuration, user_dict):
        output_objects.append(
            {'object_type': 'error_text', 'text':
             "You don't have permission to access the cloud facilities on "
             "this site"})
        return (output_objects, returnvalues.CLIENT_ERROR)

    services = [{'object_type': 'service',
                 'name': options['service_name'],
                 'description': options.get('service_desc', '')}
                for options in configuration.cloud_services]

    # Show cloud services menu
    (add_import, add_init, add_ready) = man_base_js(configuration, [])

    add_init += '''
    function get_instance_id() {
        console.log("in get_instance_id");
        console.log("found val: "+$("#select-instance-id").val());
        return $("#select-instance-id").val();
    }
    '''
    add_ready += '''
        /* NOTE: requires managers CSS fix for proper tab bar height */
        $(".cloud-tabs").tabs();
    '''

    title_entry = find_entry(output_objects, 'title')
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

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

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'site': configuration.short_title,
                    'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'reqcloudservice'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    action_list = [('status', 'Status'), ('start', 'Start'),
                   ('restart', 'Restart'), ('stop', 'Stop'),
                   ('updatekeys', 'Set keys on'), ('create', 'Create'),
                   ('delete', 'Delete')]
    for service in services:
        cloud_id = service['name']
        cloud_flavor = service.get("service_provider_flavor", "openstack")

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

        if not check_cloud_available(configuration, client_id, cloud_id,
                                     cloud_flavor):
            logger.error("Failed to connect to cloud: %s" % cloud_id)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'The %s cloud service is currently unavailable' % cloud_id})
            output_objects.append({'object_type': 'html_form', 'text': '''
        </div>
            '''})
            status = returnvalues.SYSTEM_ERROR
            continue

        (img_status, img_list) = list_cloud_images(
            configuration, client_id, cloud_id, cloud_flavor)
        if not img_status or not img_list:
            logger.error("No valid images found for %s in %s: %s" %
                         (client_id, cloud_id, img_list))
            output_objects.append({
                'object_type': 'error_text', 'text':
                    "No valid instance images for %s" % cloud_id})
            output_objects.append({'object_type': 'html_form', 'text': '''
        </div>
            '''})
            continue

        # Users store a pickled dict of all personal instances per cloud
        cloud_instance_state_path = os.path.join(configuration.user_settings,
                                                 client_dir,
                                                 cloud_id + '.state')
        fill_helpers.update({'cloud_id': cloud_id, 'target_op': target_op})

        delete_html = ""
        # Manage existing instances
        saved_instances = unpickle(cloud_instance_state_path, logger)
        if not saved_instances:
            saved_instances = {}

        saved_fields = ['INSTANCE_IMAGE']
        instance_fields = ['public_ip', 'status']
        status_map = status_all_cloud_instances(
            configuration, client_id, cloud_id, cloud_flavor,
            saved_instances.keys(), instance_fields)

        # Delete instance form helper
        helper = html_post_helper(target_op, '%s.py' % target_op,
                                  {'instance_id': '__DYNAMIC__',
                                   'service': '%s' % cloud_id,
                                   'action': 'delete',
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})

        # TODO: halfwidth styling does not really work on select elements
        delete_html += """
    <div class='cloud-instance-delete fillwidth'>
        <h3>Permanently delete a %(cloud_id)s cloud instance</h3>
        <form class='delete-cloud-instance' target='#'>
            <p class='cloud-instance-input fillwidth'>
            <label class='fieldlabel halfwidth'>Instance</label>
            <span class='halfwidth'>
            <select id='select-instance-id'
            class='styled-select html-select halfwidth padspace'
            name='instance_id'>
        """

        output_objects.append({'object_type': 'html_form', 'text': """
        <div class='cloud-management fillwidth'>
        <h3>Manage %s instances</h3>
        <div class='cloud-instance-grid'>
            """ % cloud_id})
        for (instance_id, instance_dict) in saved_instances.items():
            instance_label = instance_dict.get('INSTANCE_LABEL', instance_id)
            logger.debug("Management entries for %s %s cloud instance %s" %
                         (client_id, cloud_id, instance_id))
            instance_html = """
        <div class='cloud-instance-grid-left'>
        <label class='fieldlabel'>%s</label>
        </div>
        <div class='cloud-instance-grid-middle'>
            """ % instance_label
            for field in saved_fields:
                field_val = saved_instances[instance_id].get(field, "-")
                instance_html += """
            <span class='fieldstatus entry leftpad'>%s</span>
            """ % field_val
            for field in instance_fields:
                field_val = status_map[instance_id].get(field, "-")
                instance_html += """
            <span class='fieldstatus entry leftpad'>%s</span>
            """ % field_val
            instance_html += """
        </div>
        <div class='cloud-instance-grid-right'>
            """
            output_objects.append({'object_type': 'html_form', 'text': instance_html})
            for (action, title) in action_list:
                if action in cloud_edit_actions:
                    continue
                query = 'action=%s;service=%s;instance_id=%s' % \
                        (action, cloud_id, instance_id)
                url = 'reqcloudservice.py?%s' % query
                output_service = {
                    'object_type': 'service',
                    'name': "%s" % title,
                    'targetlink': url
                }
                output_objects.append(output_service)
            output_objects.append({'object_type': 'html_form', 'text': """
        </div>        
            """})
            delete_html += """<option value='%s'>%s</option>
            """ % (instance_id, instance_label)

        output_objects.append({'object_type': 'html_form', 'text': """
        </div>
        </div>
        """})

        delete_html += """
            </select>
            </span>
            </p>
            <p class='fillwidth'>
            <input type='submit' value='Delete Instance' onClick='javascript:confirmDialog(%(target_op)s, \"Really permanently delete instance?\", undefined, {instance_id: get_instance_id()}); return false;' />
            </p>
        </form>
    </div>
        """

        # Create new instance
        create_html = """
    <div class='cloud-instance-create fillwidth'>
        <h3>Create a new %(cloud_id)s cloud instance</h3>
        <form class='create_cloud_instance' method='%(form_method)s' action='%(target_op)s.py'>
            <input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
            <input type='hidden' name='service' value='%(cloud_id)s' />
            <input type='hidden' name='action' value='create' />
            <p class='cloud-instance-input fillwidth'>
            <label class='fieldlabel halfwidth'>Label</label>
            <span class='halfwidth'>
            <input class='halfwidth padspace' type='text' name='instance_label' value='' />
            </span>
            </p>
            <p class='cloud-instance-input fillwidth'>
            <label class='fieldlabel halfwidth'>Image</label>
            <span class='halfwidth'>
            <select class='styled-select html-select halfwidth padspace' name='instance_image'>
            """
        for (image_name, _) in img_list:
            create_html += """<option value='%s'>%s</option>
            """ % (image_name, image_name)
        create_html += """
            </select>
            </span>
            </p>
            <p class='fillwidth'>
            <input type='submit' value='Create Instance' />
            </p>
        </form>
    </div>    
        """
        output_objects.append({'object_type': 'html_form', 'text':
                               create_html % fill_helpers})

        if saved_instances:
            output_objects.append({'object_type': 'html_form', 'text':
                                   delete_html % fill_helpers})

        output_objects.append({'object_type': 'html_form', 'text': '''
        </div>
            '''})

    output_objects.append({'object_type': 'html_form', 'text': '''
    </div>
    '''})

    return (output_objects, status)
