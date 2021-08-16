
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cloud - user control for the available cloud services
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.cloud import check_cloud_available, allowed_cloud_images, \
    status_all_cloud_instances, cloud_access_allowed, cloud_edit_actions, \
    cloud_load_instance
from mig.shared.defaults import csrf_field, keyword_all
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import find_entry, initialize_main_variables
from mig.shared.html import man_base_js, man_base_html, html_post_helper
from mig.shared.useradm import get_full_user_map


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

    services = configuration.cloud_services

    # Show cloud services menu
    (add_import, add_init, add_ready) = man_base_js(configuration, [])

    add_init += '''
    function get_instance_id() {
        console.log("in get_instance_id");
        console.log("found val: "+$("#select-instance-id").val());
        return $("#select-instance-id").val();
    }
    function get_instance_label() {
        console.log("in get_instance_label");
        console.log("found val: "+$("#select-instance-id > option:selected").text());
        return $("#select-instance-id > option:selected").text();
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
                               (service['service_name'],
                                service['service_title'])
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

    action_list = [('start', 'Start'), ('stop', 'Stop'),
                   ('softrestart', 'Soft boot'), ('hardrestart', 'Hard boot'),
                   ('status', 'Status'),
                   # NOTE: expose console on status page
                   #('webaccess', 'Console'),
                   ('updatekeys', 'Set keys on'),
                   ('create', 'Create'), ('delete', 'Delete')]
    # Delete instance form helper shared for all cloud services
    helper = html_post_helper("%s" % target_op, '%s.py' % target_op,
                              {'instance_id': '__DYNAMIC__',
                               'service': '__DYNAMIC__',
                               'action': 'delete',
                               csrf_field: csrf_token})
    output_objects.append({'object_type': 'html_form', 'text': helper})

    for service in services:
        logger.debug("service: %s" % service)
        cloud_id = service['service_name']
        cloud_title = service['service_title']
        rules_of_conduct = service['service_rules_of_conduct']
        cloud_flavor = service.get("service_provider_flavor", "openstack")

        output_objects.append({'object_type': 'html_form',
                               'text': '''
        <div id="%s-tab">
        ''' % cloud_id})

        if service['service_desc']:
            output_objects.append({'object_type': 'sectionheader',
                                   'text': 'Service Description'})
        output_objects.append({'object_type': 'html_form', 'text': '''
        <div class="cloud-description">
        <span>%s</span>
        </div>
        ''' % service['service_desc']})
        output_objects.append({'object_type': 'html_form', 'text': '''
        <br/>
        '''})

        if not check_cloud_available(configuration, client_id, cloud_id,
                                     cloud_flavor):
            logger.error("Failed to connect to cloud: %s" % cloud_id)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'The %s cloud service is currently unavailable' %
                 cloud_title})
            output_objects.append({'object_type': 'html_form', 'text': '''
        </div>
            '''})
            status = returnvalues.SYSTEM_ERROR
            continue

        # Lookup user-specific allowed images (colon-separated image names)
        allowed_images = allowed_cloud_images(configuration, client_id,
                                              cloud_id, cloud_flavor)
        if not allowed_images:
            output_objects.append({
                'object_type': 'error_text', 'text':
                    "No valid instance images for %s" % cloud_title})
            output_objects.append({'object_type': 'html_form', 'text': '''
        </div>
            '''})
            continue

        fill_helpers.update({'cloud_id': cloud_id, 'cloud_title': cloud_title,
                             'target_op': target_op,
                             'rules_of_conduct': rules_of_conduct})

        delete_html = ""
        # Manage existing instances
        saved_instances = cloud_load_instance(configuration, client_id,
                                              cloud_id, keyword_all)

        saved_fields = ['INSTANCE_IMAGE']
        instance_fields = ['public_fqdn', 'status']
        status_map = status_all_cloud_instances(
            configuration, client_id, cloud_id, cloud_flavor,
            list(saved_instances), instance_fields)

        # TODO: halfwidth styling does not really work on select elements
        delete_html += """
    <div class='cloud-instance-delete fillwidth'>
        <h3>Permanently delete a %(cloud_title)s cloud instance</h3>
        <form class='delete-cloud-instance' target='#'>
            <p class='cloud-instance-input fillwidth'>
            <label class='fieldlabel halfwidth'>Instance</label>
            <span class='halfwidth'>
            <select id='select-instance-id'
            class='styled-select html-select halfwidth padspace'
            name='instance_id'>
        """ % fill_helpers

        output_objects.append({'object_type': 'html_form', 'text': """
        <div class='cloud-management fillwidth'>
        <h3>Manage %(cloud_title)s instances</h3>
        <br/>
        <div class='cloud-instance-grid'>
        <div class='cloud-instance-grid-left'>
        <label class='fieldlabel fieldheader'>Name</label>
        </div>
        <div class='cloud-instance-grid-middle'>
        <label class='fieldlabel fieldheader'>Instance Details</label>
        </div>
        <div class='cloud-instance-grid-right'>
        <label class='fieldlabel fieldheader'>Actions</label>
        </div>
            """ % fill_helpers})
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
                if field == 'INSTANCE_IMAGE':
                    for (img_name, _, img_alias) in allowed_images:
                        if img_name == field_val:
                            field_val = img_alias
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
            output_objects.append(
                {'object_type': 'html_form', 'text': instance_html})
            for (action, title) in action_list:
                if action in cloud_edit_actions:
                    continue
                query = 'action=%s;service=%s;instance_id=%s' % \
                        (action, cloud_id, instance_id)
                url = 'reqcloudservice.py?%s' % query
                # output_service = {
                #    'object_type': 'service',
                #    'name': "%s" % title,
                #    'targetlink': url
                # }
                # output_objects.append(output_service)
                output_objects.append({
                    'object_type': 'link', 'destination': url, 'text': title,
                    'class': 'ui-button',
                    'title': '%s %s' % (title, instance_label)})

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
            <input type='submit' value='Delete Instance' onClick='javascript:confirmDialog(%(target_op)s, \"Really permanently delete your %(cloud_title)s \"+get_instance_label()+\" instance including all local data?\", undefined, {instance_id: get_instance_id(), service: \"%(cloud_id)s\"}); return false;' />
            </p>
        </form>
    </div>
        """ % fill_helpers

        # Create new instance
        create_html = """
    <div class='cloud-instance-create fillwidth'>
        <h3>Create a new %(cloud_title)s cloud instance</h3>
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
        for (image_name, _, image_alias) in allowed_images:
            create_html += """<option value='%s'>%s</option>
            """ % (image_name, image_alias)
        create_html += """
            </select>
            </span>
            </p>
            <p class='cloud-instance-input fillwidth'>
            <label class='fieldlabel halfwidth'>
            Accept <a href='%(rules_of_conduct)s'>Cloud Rules of Conduct</a>
            </label>
            <span class='halfwidth'>
            <label class='switch'>
            <input type='checkbox' mandatory name='accept_terms'>
            <span class='slider round'></span></label>
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
