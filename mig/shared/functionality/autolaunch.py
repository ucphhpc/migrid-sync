#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# autolaunch - auto launch configured user default page or site landing page
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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


"""Redirector for saved user default page or site lading page"""
from __future__ import absolute_import


from .shared import returnvalues
from .shared.functional import validate_input_and_cert
from .shared.init import initialize_main_variables
from .shared.html import themed_styles, themed_scripts, menu_items
from .shared.settings import load_settings


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(
        client_id, op_header=False, op_title=False, op_menu=client_id)
    # IMPORTANT: no title in init above so we MUST call it immediately here
    #            or basic styling will break e.g. on crashes.
    styles = themed_styles(configuration)
    scripts = themed_scripts(configuration, logged_in=False)
    output_objects.append(
        {'object_type': 'title', 'text': 'Auto Launch',
         'skipmenu': True, 'style': styles, 'script': scripts})
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

    user_settings = load_settings(client_id, configuration)
    # NOTE: loaded settings may be the boolean False rather than dict here
    if not user_settings:
        user_settings = {}

    default_page = user_settings.get('DEFAULT_PAGE', None)
    if default_page and default_page in menu_items:
        redirect_location = menu_items[default_page]['url']
    else:
        redirect_location = configuration.site_landing_page
    headers = [('Status', '302 Moved'),
               ('Location', redirect_location)]
    logger.debug("user settings and site landing page gave %s" %
                 redirect_location)
    output_objects.append({'object_type': 'start', 'headers': headers})
    output_objects.append({'object_type': 'script_status'})

    return (output_objects, returnvalues.OK)
