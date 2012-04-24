#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# vmrequest - request new virtual machine
# Copyright (C) 2003-2012  The MiG Project lead by Brian Vinter
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

"""Virtual machine request back end functionality"""

import shared.returnvalues as returnvalues
from shared import vms
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
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
    output_objects.append({'object_type': 'header', 'text':
                           '%s Request Virtual Machine' % \
                           configuration.short_title})
    if not configuration.site_enable_vmachines:
        output_objects.append({'object_type': 'error_text', 'text':
                               "Virtual machines are disabled on this server"})
        status = returnvalues.CLIENT_ERROR
        return (output_objects, status)

    build_form = """
<form method="post" action="vmachines.py">
<input type="hidden" name="output_format" value="html">
<input type="hidden" name="action" value="create">

<table style="margin: 10px; width: 96%;">
<tr>
  <td width="200">Machine name</td>
  <td>
  <input type="text" name="machine_name" size="30" value="MyVirtualDesktop">
  </td>
</tr>
</table>

<fieldset>
<legend><input type="radio" name="machine_type" value="pre" checked="checked">Prebuilt</legend>
<table>
<tr>
  <td width="200">Choose a OS version</td>
  <td>
  
<select name="os">
"""
    for os in vms.available_os_list(configuration):
        build_form += '<option value="%s">%s</option>\n' % \
                      (os, os.capitalize())
    build_form += """
</select>

  </td>
</tr>
<tr>
  <td width="200">Choose a machine image</td>
  <td>
  
<select name="flavor">
"""
    for flavor in vms.available_flavor_list(configuration):
        build_form += '<option value="%s">%s</option>\n' % \
                      (flavor, flavor.capitalize())
    build_form += """
</select>

  </td>
</tr>
<tr>
  <td width="200">Select a runtime environment providing the chosen OS and
flavor combination.
For Ubuntu systems you can typically just use a runtime env from the same year,
like VBOX3.1-IMAGES-2010-1 for ubuntu-10.* versions.</td>
  <td>
  
<select name="sys_re">
"""
    for sys_re in vms.available_sys_re_list(configuration):
        build_form += '<option value="%s">%s</option>\n' % \
                      (sys_re, sys_re)
    build_form += """
</select>

  </td>
</tr>
</table>

</fieldset>

<fieldset>
<legend><input type="radio" name="machine_type" value="custom" disabled>Custom:</legend>
<span class="warningtext">Custom builds are currently unavailable.</span>
<table>
<tr>
  <td width="200">Software</td>
  <td>
<textarea cols=40 name="machine_software" readonly>
iptables, acpid, x11vnc, xorg, gdm, xfce4, gcc, make, netsurf, python-openssl
</textarea>
  </td>
</tr>
</table>

</fieldset>
<input type="submit" value="Submit machine request!">

</form>
"""
    output_objects.append({'object_type': 'html_form', 'text': build_form})
    return (output_objects, status)
