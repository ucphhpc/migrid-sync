#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# pubvgridprojects - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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

import os

import shared.returnvalues as returnvalues
from shared.functional import validate_input
from shared.init import initialize_main_variables


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['linklist', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'header', 'text'
                          : 'Public project links'})

    vgrid_public_base = configuration.vgrid_public_base
    linklist = []
    for public_vgrid_dir in os.listdir(vgrid_public_base):
        if os.path.exists(os.path.join(vgrid_public_base,
                          public_vgrid_dir, '.enable_public_page')):

            # public project listing is enabled, link to the vgrid's public page

            new_link = {'object_type': 'link',
                        'text': public_vgrid_dir,
                        'destination': '%s/vgrid/%s'\
                         % (configuration.migserver_http_url,
                        public_vgrid_dir)}
            linklist.append(new_link)
    output_objects.append({'object_type': 'linklist', 'links'
                          : linklist})

    return (output_objects, returnvalues.OK)


