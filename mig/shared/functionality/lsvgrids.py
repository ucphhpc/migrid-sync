#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# lsvgrids - simple list of vgrids optionally filtered to ones with access
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

"""List all vgrid names under given vgrid_name - leave empty for all. The
optional allowed_only argument is used to limit the list to ones with access.
"""

from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.functional import validate_input_and_cert
from mig.shared.init import initialize_main_variables
from mig.shared.vgrid import vgrid_list_vgrids, user_allowed_vgrids


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': [''], 'allowed_only': ['True']}
    return ['list', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
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

    root_vgrid = accepted['vgrid_name'][-1]
    allowed_only = (accepted['allowed_only'][-1].lower() in ('true', 'yes'))

    # NOTE: no general access check here as we only list public vgrid names

    if allowed_only:
        list_status = True
        msg = user_allowed_vgrids(configuration, client_id, inherited=True)
    else:
        (list_status, msg) = vgrid_list_vgrids(configuration,
                                               include_default=(
                                                   not root_vgrid),
                                               root_vgrid=root_vgrid)

    if not list_status:
        output_objects.append({'object_type': 'error_text', 'text': '%s'
                               % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'list', 'list': msg})
    return (output_objects, returnvalues.OK)
