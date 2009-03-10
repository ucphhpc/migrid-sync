#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# redb - [insert a few words of module description on this line]
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

# Minimum Intrusion Grid

# Script version (automagically updated by cvs)

""" Show all available runtime environments """

__version__ = '$Revision: 1548 $'

# $Id: redb.py 1548 2006-10-12 10:51:53Z karlsen $

from shared.refunctions import list_runtime_environments, get_re_dict
from shared.functionality.showre import build_reitem_object_from_re_dict
from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    defaults = {}
    return ['runtimeenvironments', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Runtime Environments'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Runtime Environments'})

    output_objects.append({'object_type': 'link', 'destination'
                          : 'adminre.py', 'text'
                          : 'Create a new runtime environment'})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Existing runtime environments'})

    (status, ret) = list_runtime_environments(configuration)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : ret})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    runtimeenvironments = []
    for single_re in ret:
        (re_dict, msg) = get_re_dict(single_re, configuration)
        if not re_dict:
            output_objects.append({'object_type': 'error_text', 'text'
                                  : msg})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        runtimeenvironments.append(build_reitem_object_from_re_dict(re_dict))
    output_objects.append({'object_type': 'runtimeenvironments',
                          'runtimeenvironments': runtimeenvironments})
    return (output_objects, returnvalues.OK)


