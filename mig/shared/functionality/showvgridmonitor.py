#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# showvgridmonitor - [insert a few words of module description on this line]
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

"""Show the monitor page for requested vgrids - ALL keyword for all allowed vgrids"""

import os
import sys

from shared.vgrid import vgrid_is_owner_or_member, user_allowed_vgrids
from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""
    defaults = {'vgrid_name': ['ALL']}
    return ['html_form', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)
    refresh = '<meta http-equiv="refresh" content="%s">'\
         % configuration.sleep_secs
    output_objects.append({
        'object_type': 'title',
        'text': 'MiG VGrid Monitor',
        'javascript': refresh,
        'bodyfunctions': '',
        })

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    allowed_vgrids = user_allowed_vgrids(configuration, cert_name_no_spaces)
    vgrid_list = accepted['vgrid_name']
    if 'ALL' in accepted['vgrid_name']:
        vgrid_list = [i for i in vgrid_list if 'ALL' != i] + allowed_vgrids

    # Force list to sequence of unique entries
    
    for vgrid_name in set(vgrid_list):
        html = ''
        if not vgrid_is_owner_or_member(vgrid_name, cert_name_no_spaces,
                                        configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'You must be an owner or member of %s vgrid to access the monitor.'
                                   % vgrid_name})
            return (output_objects, returnvalues.CLIENT_ERROR)

        monitor_file = os.path.join(configuration.vgrid_home, vgrid_name,
                                    'monitor.html')
        try:
            monitor_fd = open(monitor_file, 'r')
            past_header = False
            for line in monitor_fd:
                if -1 != line.find('end of raw header'):
                    past_header = True
                    continue
                if not past_header:
                    continue
                if -1 != line.find('begin raw footer:'):
                    break
                html += str(line)
            monitor_fd.close()
        except Exception, exc:
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'Error reading VGrid monitor page (%s)'
                                   % exc})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        output_objects.append({'object_type': 'html_form', 'text': html})
    return (output_objects, returnvalues.OK)


