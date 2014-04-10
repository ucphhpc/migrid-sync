#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# vmconnect - connect to virtual machine
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Virtual machine connection back end functionality"""

import shared.returnvalues as returnvalues
from shared import vms
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
from shared.settings import load_settings


def signature():
    """Signature of the main function"""

    defaults = {'job_id': ['']}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    output_objects.append({'object_type': 'header', 'text':
                           '%s Virtual Desktop' % configuration.short_title})
    status = returnvalues.OK
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

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Virtual Machines'

    if not configuration.site_enable_vmachines:
        output_objects.append({'object_type': 'text', 'text':
                               '''Virtual machines are disabled on this site.
Please contact the Grid admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    settings_dict = load_settings(client_id, configuration)
    if not settings_dict or not settings_dict.has_key('VNCDISPLAY'):
        logger.info('Settings dict does not have VNCDISPLAY key - using default'
                    )
        (vnc_display_width, vnc_display_height) = (1024, 768)
    else:
        (vnc_display_width, vnc_display_height) = settings_dict['VNCDISPLAY']

    # Make room for vnc control menu
    
    vnc_menu_height = 24
    vnc_display_height += vnc_menu_height
    password = vms.vnc_jobid(accepted['job_id'][0])

    # Do an "intoN" then map to acsii

    output_objects.append({'object_type': 'html_form', 'text'
                          : vms.popup_snippet() + vms.vnc_applet(
                               configuration,
                               vnc_display_width,
                               vnc_display_height,
                               password,
                               )})

    return (output_objects, status)


