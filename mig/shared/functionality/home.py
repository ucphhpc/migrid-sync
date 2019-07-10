#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# home - home page
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


"""Home page generator"""


import shared.returnvalues as returnvalues
from shared.functional import validate_input
from shared.init import initialize_main_variables


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['text', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(
        user_arguments_dict,
        defaults,
        output_objects,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'header', 'text': '%s Home' %
                           configuration.short_title})
    output_objects.append({'object_type': 'text', 'text': '''
%s home page''' % configuration.short_title})

    return (output_objects, returnvalues.OK)
