#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jupyter - User menu over the available jupyter services
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

"""
A page for dislaying available jupyter services,
provides a list of buttons based on services defined in the
 configuration.jupyter_services
"""
from __future__ import absolute_import

from mig.shared import returnvalues

from mig.shared.init import find_entry, initialize_main_variables
from mig.shared.functional import validate_input_and_cert
from mig.shared.html import man_base_js


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['jupyter', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""
    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
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
    if not configuration.site_enable_jupyter:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'The Jupyter service is not enabled on the system'})
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
                for options in configuration.jupyter_services]

    # Show jupyter services menu
    (add_import, add_init, add_ready) = man_base_js(configuration, [])

    add_ready += '''
        /* NOTE: requires managers CSS fix for proper tab bar height */
        $(".jupyter-tabs").tabs();
    '''

    title_entry = find_entry(output_objects, 'title')
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'header',
                           'text': 'Select a Jupyter Service'})

    fill_helpers = {
        'jupyter_tabs': ''.join(['<li><a href="#%s-tab">%s</a></li>' %
                                 (service['name'], service['name'])
                                 for service in services])
    }

    output_objects.append({'object_type': 'html_form', 'text': '''
    <div id="wrap-tabs" class="jupyter-tabs">
    <ul>
    %(jupyter_tabs)s
    </ul>
    ''' % fill_helpers})

    for service in services:
        output_objects.append({'object_type': 'html_form',
                               'text': '''
        <div id="%s-tab">
        ''' % (service['name'])})

        if service['description']:
            output_objects.append({'object_type': 'sectionheader',
                                   'text': 'Service Description'})
        output_objects.append({'object_type': 'html_form', 'text': '''
        <div class="jupyter-description">
        <p>%s</p>
        </div>
        ''' % service['description']})
        output_objects.append({'object_type': 'html_form', 'text': '''
        <br/>
        '''})

        output_service = {'object_type': 'service',
                          'name': "Start %s" % service['name'],
                          'targetlink': 'reqjupyterservice.py?service=%s'
                          % service['name']}
        output_objects.append(output_service)
        output_objects.append({'object_type': 'html_form', 'text': '''
        </div>
        '''})
    output_objects.append({'object_type': 'html_form', 'text': '''
    </div>
    </div>
    '''})

    return (output_objects, returnvalues.OK)
