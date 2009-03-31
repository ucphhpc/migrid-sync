#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminvgrid - [insert a few words of module description on this line]
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

""" List owners, members, res's and show html controls to administrate a vgrid """

from shared.validstring import valid_dir_input
from shared.vgrid import vgrid_list
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    defaults = {'vgrid_name': REJECT_UNSET}
    return ['html_form', defaults]


def create_html(vgrid_name, configuration):
    out = '<H3>Owners</H3>'

    # list owners

    (status, msg) = vgrid_list(vgrid_name, 'owners', configuration)
    if not status:
        return (False, msg)

    if len(msg) <= 0:
        out += \
            'No owners found! This could indicate a problem since it is not allowed to remove the last owner of a vgrid!'
    else:
        out += \
            """<form method="get" action="/cgi-bin/rmvgridowner.py">
        <input type="hidden" name="vgrid_name" value="%s">
        """\
             % vgrid_name

        out += 'Current owners of %s:' % vgrid_name
        out += '<table class="vgridowner"><th>Remove</th><th>Owner</th>'
        for elem in msg:
            if elem != '':
                out += \
                    "<tr><td><input type=radio name='cert_name' value='%s'></td><td>%s</td></tr>"\
                     % (elem, elem)
        out += '</table>'
        out += \
            """<input type="submit" value="Remove owner(s)">
        </form>
        """

    out += \
        """<form method="get" action="/cgi-bin/addvgridowner.py">
    <input type="hidden" name="vgrid_name" value="%s">
    <input type="text" size=40 name="cert_name">
    <input type="submit" value="Add vgrid owner">
    </form>
    <HR>
    <H2>Members</H2>"""\
         % vgrid_name

    # list members

    (status, msg) = vgrid_list(vgrid_name, 'members', configuration)
    if not status:
        return (False, msg)

    if len(msg) <= 0:
        out += 'No members found!<BR>'
    else:
        out += \
            """<form method="get" action="/cgi-bin/rmvgridmember.py">
        <input type="hidden" name="vgrid_name" value="%s">
        """\
             % vgrid_name

        out += 'Current members of %s:' % vgrid_name
        out += '<table class="vgridmember"><th>Remove</th><th>Member</th>'
        for elem in msg:
            out += \
                "<tr><td><input type=radio name='cert_name' value='%s'></td><td>%s</td></tr>"\
                 % (elem, elem)
        out += '</table>'

        out += \
            """<input type="submit" value="Remove member(s)">
        </form>
        """
    out += \
        """<form method="get" action="/cgi-bin/addvgridmember.py">
    <input type="hidden" name="vgrid_name" value="%s">
    <input type="text" size=40 name="cert_name">
    <input type="submit" value="Add vgrid member">
    </form>
    <HR>
    <H2>Resources</H2>"""\
         % vgrid_name

    # list resources

    (status, msg) = vgrid_list(vgrid_name, 'resources', configuration)
    if not status:
        return (False, msg)

    if len(msg) <= 0:
        out += 'No resources found!<BR>'
    else:
        out += \
            """<form method="get" action="/cgi-bin/rmvgridres.py">
        <input type="hidden" name="vgrid_name" value="%s">
        """\
             % vgrid_name

        out += 'Current resources of %s:' % vgrid_name
        out += '<table class="vgridresource"><th>Remove</th><th>Resource</th></tr>'
        for elem in msg:
            out += \
                "<tr><td><input type=radio name='unique_resource_name' value='%s'></td><td>%s</td></tr>"\
                 % (elem, elem)
        out += '</table>'

        out += \
            """<input type="submit" value="Remove resource(s)">
        </form>
        """
    out += \
        """<form method="get" action="/cgi-bin/addvgridres.py">
    <input type="hidden" name="vgrid_name" value="%s">
    <input type="text" size=40 name="unique_resource_name">
    <input type="submit" value="Add vgrid resource">
    </form>
    """\
         % vgrid_name

    return (True, out)


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
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
    vgrid_name = accepted['vgrid_name'][-1]

    output_objects.append({'object_type': 'header', 'text'
                          : "Administrate vgrid '%s'" % vgrid_name})

    (ret, msg) = create_html(vgrid_name, configuration)
    if not ret:
        output_objects.append({'object_type': 'error_text', 'text': '%s'
                               % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    output_objects.append({'object_type': 'html_form', 'text': msg})
    return (output_objects, returnvalues.OK)


