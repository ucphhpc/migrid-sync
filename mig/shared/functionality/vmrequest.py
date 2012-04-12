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
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_title=False)

    status = returnvalues.OK
    defaults = {}
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

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Request Virtual Machine'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Request Virtual Machine'})

    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<form method="post" action="/cgi-bin/vmachines.py">
<input type="hidden" name="output_format" value="html">
<input type="hidden" name="machine_request" value="1">

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
  <td width="200">Choose a machine</td>
  <td>
  
<select name="pre_built">
<option value="plain">Basic</option>
<option value="matlab">Matlab</option>
</select>

  </td>
</tr>
</table>

</fieldset>

<fieldset>
<legend><input type="radio" name="machine_type" value="custom">Custom:</legend>
<table>

<tr>
  <td width="200">Architecture</td>
  <td>
  <select name="machine_arch">
  <option value="32">32bit</option>
  <option value="64">64bit</option>
  </select>
  </td>
</tr>

<tr>
  <td width="200">Ram</td>
  <td>
  <select name="machine_ram">
  <option value="256">256</option>
  <option value="512">512</option>
  <option value="1024">1024</option>
  <option value="2048">2048</option>
  <option value="4096">4096</option>
  </select>
  </td>
</tr>

<tr>
  <td width="200">CPUs</td>
  <td>
  <select name="machine_cpu">
  <option value="1">1</option>
  <option value="2">2</option>
  <option value="4">4</option>
  </select>
  </td>
</tr>

<tr>
  <td width="200">Software</td>
  <td>
<textarea cols=40 name="machine_software">
iptables, acpid, x11vnc, xorg, gdm, xfce4, gcc, make, dillo, python-openssl
</textarea>
  </td>
</tr>
</table>

</fieldset>
<input type="submit" value="Submit machine request!">

</form>
    """})

    return (output_objects, status)


