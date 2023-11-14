#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# vmrequest - request new virtual machine
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared import vms
from mig.shared.defaults import csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    output_objects.append({'object_type': 'header', 'text':
                           '%s Request Virtual Machine' %
                           configuration.short_title})
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

    if not configuration.site_enable_vmachines:
        output_objects.append({'object_type': 'text', 'text':
                               """Virtual machine use is disabled on this site.
Please contact the %s site support (%s) if you think it should be enabled.
""" % (configuration.short_title, configuration.support_email)})
        return (output_objects, returnvalues.OK)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'vmachines'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    build_form = '''
<form method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="output_format" value="html">
<input type="hidden" name="action" value="create">
''' % fill_helpers
    build_form += '''
<table style="margin: 0px; width: 100%;">
<tr>
  <td style="width: 20%;">Machine name</td>
  <td>
  <input type="text" name="machine_name" size="30" value="MyVirtualDesktop">
  </td>
</tr>
</table>

<fieldset>
<legend><input type="radio" name="machine_type" value="pre" checked="checked">Prebuilt</legend>
<table>
<tr>
  <td style="width: 20%;">Choose a OS version</td>
  <td>

<select name="os">
'''
    for val in vms.available_os_list(configuration):
        build_form += '<option value="%s">%s</option>\n' % \
                      (val, val.capitalize())
    build_form += '''
</select>

  </td>
</tr>
<tr>
  <td>Choose a machine image</td>
  <td>

<select name="flavor">
'''
    for flavor in vms.available_flavor_list(configuration):
        build_form += '<option value="%s">%s</option>\n' % \
                      (flavor, flavor.capitalize())
    build_form += """
</select>

  </td>
</tr>
<tr>
  <td>Select a runtime environment providing the chosen OS and
flavor combination.
For Ubuntu systems you can typically just use a runtime env from the same year,
like VBOX3.1-IMAGES-2010-1 for ubuntu-10.* versions.</td>
  <td>

<input type="hidden" name="hypervisor_re" value="%s">
<select name="sys_re">
""" % configuration.vm_default_hypervisor_re
    for sys_re in vms.available_sys_re_list(configuration):
        build_form += '<option value="%s">%s</option>\n' % \
                      (sys_re, sys_re)
    build_form += '''
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
  <td style="width: 20%;">Software</td>
  <td>
<input type=text size=80 name="machine_software" readonly
value="iptables acpid x11vnc xorg gdm xfce4 gcc make netsurf python-openssl" />
  </td>
</tr>
</table>

</fieldset>
<input type="submit" value="Submit machine request!">

</form>
'''
    output_objects.append({'object_type': 'html_form', 'text': build_form})
    return (output_objects, status)
