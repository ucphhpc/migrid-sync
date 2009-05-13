#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgridadmin - [insert a few words of module description on this line]
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

"""VGrid administration back end functionality"""

import os
import sys

import shared.returnvalues as returnvalues
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.parseflags import verbose
from shared.init import initialize_main_variables
from shared.validstring import valid_user_path
from shared.vgrid import vgrid_list_vgrids, vgrid_is_owner, \
    vgrid_is_member, vgrid_is_owner_or_member


def signature():
    """Signature of the main function"""
    defaults = {}
    return ['vgrids', defaults]


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)
    status = returnvalues.OK
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        cert_name_no_spaces,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    owner_of_a_vgrid = False
    member_of_a_vgrid = False

    (stat, list) = vgrid_list_vgrids(configuration)
    if not stat:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of vgrids.'})

    # Iterate through jobs and print details for each

    owner_list = {'object_type': 'vgrid_list', 'vgrids': []}
    member_list = {'object_type': 'vgrid_list', 'vgrids': []}
    for vgrid_name in list:
        if not vgrid_is_owner_or_member(vgrid_name,
                cert_name_no_spaces, configuration):
            continue

        vgrid_obj = {'object_type': 'vgrid', 'name': vgrid_name}
        vgrid_obj['enterprivatelink'] = {'object_type': 'link',
                'destination': '../vgrid/%s/' % vgrid_name,
                'text': 'Enter'}
        vgrid_obj['privatewikilink'] = {'object_type': 'link',
                'destination': '/vgridwiki/%s' % vgrid_name,
                'text': 'Private'}
        vgrid_obj['privatemonitorlink'] = {'object_type': 'link',
                'destination': '/cgi-bin/showvgridmonitor.py?vgrid_name=%s'\
                 % vgrid_name, 'text': 'Private'}
        vgrid_obj['enterpubliclink'] = {'object_type': 'link',
                'destination': '%s/vgrid/%s/'\
                 % (configuration.migserver_http_url, vgrid_name),
                'text': 'Enter'}
        vgrid_obj['publicwikilink'] = {'object_type': 'link',
                'destination': '%s/vgridpublicwiki/%s'\
                 % (configuration.migserver_http_url, vgrid_name),
                'text': 'Public'}
        if vgrid_is_owner(vgrid_name, cert_name_no_spaces,
                          configuration):
            vgrid_obj['administratelink'] = {'object_type': 'link',
                    'destination': '/cgi-bin/adminvgrid.py?vgrid_name=%s'\
                     % vgrid_name, 'text': 'Administrate'}
            vgrid_obj['editprivatelink'] = {'object_type': 'link',
                    'destination': '/cgi-bin/editor.py?path=private_base/%s/index.html'\
                     % vgrid_name, 'text': 'Edit'}
            vgrid_obj['editpubliclink'] = {'object_type': 'link',
                    'destination': '/cgi-bin/editor.py?path=public_base/%s/index.html'\
                     % vgrid_name, 'text': 'Edit'}
            owner_list['vgrids'].append(vgrid_obj)
        elif vgrid_is_member(vgrid_name, cert_name_no_spaces,
                             configuration):

            member_list['vgrids'].append(vgrid_obj)

    output_objects.append({'object_type': 'title', 'text': 'MiG VGrids'
                          })
    output_objects.append({'object_type': 'header', 'text': 'MiG VGrids'
                          })
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'VGrid owner'})
    output_objects.append({'object_type': 'text', 'text'
                          : 'List of vgrids where you are registered as owner:'
                          })

    output_objects.append(owner_list)
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'VGrid member'})
    output_objects.append({'object_type': 'text', 'text'
                          : 'List of vgrids where you are registered as member:'
                          })
    output_objects.append(member_list)

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'VGrid Totals'})
    output_objects.append({'object_type': 'link', 'text'
                          : 'View a multi VGrid monitor with all the resources you can access'
                          , 'destination'
                          : '/cgi-bin/showvgridmonitor.py?vgrid_name=ALL'})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'VGrid request'})
    output_objects.append({'object_type': 'link', 'text'
                          : 'Request ownership or membership of an existing VGrid'
                          , 'destination'
                          : '/cgi-bin/vgridmemberrequest.py'})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Create VGrid'})
    output_objects.append({'object_type': 'html_form', 'text'
                          : '''<form method="get" action="/cgi-bin/createvgrid.py">
    <input type="text" size=40 name="vgrid_name">
    <input type="hidden" name="output_format" value="html">
    <input type="submit" value="Create vgrid">
    </form>
    <br>
    '''})

    # print "DEBUG: %s" % output_objects

    return (output_objects, status)


