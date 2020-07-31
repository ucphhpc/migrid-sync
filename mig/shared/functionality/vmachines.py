#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vmachines - virtual machine management
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

"""Virtual machine administration back end functionality"""
from __future__ import absolute_import

import os
import time
from binascii import hexlify

from mig.shared import returnvalues
from mig.shared import vms
from mig.shared.defaults import any_vgrid, csrf_field
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from mig.shared.html import render_menu, confirm_js, confirm_html, \
    html_post_helper
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.vgridaccess import user_vgrid_access

list_actions = ['show', '']
edit_actions = ['create', 'start', 'stop', 'edit', 'delete']
allowed_actions = list(set(list_actions + edit_actions))


def signature():
    """Signature of the main function"""

    defaults = {
        'action': [''],
        'machine_name': [''],
        'machine_type': [''],
        'machine_partition': [''],
        'machine_software': [''],
        'os': [''],
        'flavor': [''],
        'hypervisor_re': [''],
        'sys_re': [''],
        # Resource native architecture requirement (not vm architecture)
        'architecture': [''],
        'cpu_count': ['1'],
        'cpu_time': ['900'],
        'memory': ['1024'],
        'disk': ['2'],
        'vgrid': ['ANY'],
    }
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)

    output_objects.append({'object_type': 'header', 'text':
                           'Virtual Machines'})
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

    machine_name = accepted['machine_name'][-1].strip()
    memory = int(accepted['memory'][-1])
    disk = int(accepted['disk'][-1])
    vgrid = [name.strip() for name in accepted['vgrid']]
    architecture = accepted['architecture'][-1].strip()
    cpu_count = int(accepted['cpu_count'][-1])
    cpu_time = int(accepted['cpu_time'][-1])
    op_sys = accepted['os'][-1].strip()
    flavor = accepted['flavor'][-1].strip()
    hypervisor_re = accepted['hypervisor_re'][-1].strip()
    sys_re = accepted['sys_re'][-1].strip()
    action = accepted['action'][-1].strip()

    if action in edit_actions and \
        not safe_handler(configuration, 'post', op_name, client_id,
                         get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Virtual Machines'

    # jquery support for confirmation on delete:
    (add_import, add_init, add_ready) = confirm_js(configuration)

    add_ready += '''
          $(".vm-tabs").tabs();
    '''
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready
    output_objects.append({'object_type': 'html_form',
                           'text': confirm_html(configuration)})

    if not configuration.site_enable_vmachines:
        output_objects.append({'object_type': 'text', 'text':
                               '''Virtual machines are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    machine_req = {'memory': memory, 'disk': disk, 'cpu_count': cpu_count,
                   'cpu_time': cpu_time, 'architecture': architecture,
                   'vgrid': vgrid, 'os': op_sys, 'flavor': flavor,
                   'hypervisor_re': hypervisor_re, 'sys_re': sys_re}

    menu_items = ['vmrequest']

    # Html fragments

    submenu = render_menu(configuration, menu_class='navsubmenu',
                          base_menu=[], user_menu=menu_items)

    welcome_text = 'Welcome to your %s virtual machine management!' % \
                   configuration.short_title
    desc_text = '''On this page you can:
<ul>
    <li>Request Virtual Machines, by clicking on the button above</li>
    <li>See your virtual machines in the list below.</li>
    <li>Start, and connect to your Virtual Machine by clicking on it.</li>
    <li>Edit or delete your Virtual Machine from the Advanced tab.</li>
</ul>
'''

    output_objects.append({'object_type': 'html_form',
                           'text': '''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="40" rows="4" id="confirm_input" style="display:none;"></textarea>
 </div>
'''})

    output_objects.append({'object_type': 'html_form', 'text': submenu})
    output_objects.append(
        {'object_type': 'html_form', 'text': '<p>&nbsp;</p>'})
    output_objects.append(
        {'object_type': 'sectionheader', 'text': welcome_text})
    output_objects.append({'object_type': 'html_form', 'text': desc_text})

    user_vms = vms.vms_list(client_id, configuration)
    if action == 'create':
        if not configuration.site_enable_vmachines:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "Virtual machines are disabled on this server"})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)
        if not machine_name:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested build without machine name"})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)
        elif machine_name in [vm["name"] for vm in user_vms]:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested machine name '%s' already exists!" % machine_name})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)
        elif not flavor in vms.available_flavor_list(configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested pre-built flavor not available: %s" % flavor})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)
        elif not hypervisor_re in \
                vms.available_hypervisor_re_list(configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested hypervisor runtime env not available: %s" %
                 hypervisor_re})
        elif not sys_re in vms.available_sys_re_list(configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested system pack runtime env not available: %s" %
                 sys_re})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)

        # TODO: support custom build of machine using shared/vmbuilder.py

        # request for existing pre-built machine

        logger.debug("create new vm: %s" % machine_req)
        (create_status, create_msg) = vms.create_vm(client_id, configuration,
                                                    machine_name, machine_req)
        if not create_status:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested virtual machine could not be created: %s" %
                 create_msg})
            status = returnvalues.SYSTEM_ERROR
            return (output_objects, status)

    (action_status, action_msg, job_id) = (True, '', None)
    if action in ['start', 'stop', 'edit', 'delete']:
        if not configuration.site_enable_vmachines:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "Virtual machines are disabled on this server"})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)
    if action == 'start':
        machine = {}
        for entry in user_vms:
            if machine_name == entry['name']:
                for name in machine_req.keys():
                    if isinstance(entry[name], basestring) and \
                            entry[name].isdigit():
                        machine[name] = int(entry[name])
                    else:
                        machine[name] = entry[name]
                break
        (action_status, action_msg, job_id) = \
            vms.enqueue_vm(client_id, configuration, machine_name,
                           machine)
    elif action == 'edit':
        if not machine_name in [vm['name'] for vm in user_vms]:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "No such virtual machine: %s" % machine_name})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)
        (action_status, action_msg) = \
            vms.edit_vm(client_id, configuration, machine_name,
                        machine_req)
    elif action == 'delete':
        if not machine_name in [vm['name'] for vm in user_vms]:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "No such virtual machine: %s" % machine_name})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)
        (action_status, action_msg) = \
            vms.delete_vm(client_id, configuration, machine_name)
    elif action == 'stop':

        # TODO: manage stop - use live I/O to create vmname.stop in job dir

        pass

    if not action_status:
        output_objects.append({'object_type': 'error_text', 'text':
                               action_msg})

    # List the machines here

    output_objects.append(
        {'object_type': 'sectionheader', 'text': 'Your machines:'})

    # Grab the vms available for the user

    machines = vms.vms_list(client_id, configuration)

    # Visual representation mapping of the machine state

    machine_states = {
        'EXECUTING': 'vm_running.jpg',
        'CANCELED': 'vm_off.jpg',
        'FAILED': 'vm_off.jpg',
        'FINISHED': 'vm_off.jpg',
        'UNKNOWN': 'vm_off.jpg',
        'QUEUED': 'vm_booting.jpg',
        'PARSE': 'vm_booting.jpg',
    }

    # Empirical upper bound on boot time in seconds used to decide between
    # desktop init and ready states

    boot_secs = 130

    # CANCELED/FAILED/FINISHED -> Powered Off
    # QUEUED -> Booting

    if len(machines) > 0:

        form_method = 'post'
        csrf_limit = get_csrf_limit(configuration)
        fill_helpers = {'form_method': form_method,
                        'csrf_field': csrf_field,
                        'csrf_limit': csrf_limit}
        target_op = 'vmachines'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op,
                             'csrf_token': csrf_token})
        # Create a pretty list with start/edit/stop/connect links

        pretty_machines = \
            '<table style="border: 0; background: none;"><tr>'
        side_by_side = 3  # How many machines should be shown in a row?

        col = 0
        for machine in machines:

            # Machines on a row

            if col % side_by_side == 0:
                pretty_machines += '</tr><tr>'
            col += 1

            # Html format machine specifications in a fieldset

            password = 'UNKNOWN'
            exec_time = 0
            if machine['job_id'] != 'UNKNOWN' and \
                    machine['status'] == 'EXECUTING':

                # TODO: improve on this time selection...
                # ... in distributed there is no global clock!

                exec_time = time.time() - 3600 \
                    - time.mktime(machine['execution_time'])
                password = vms.vnc_jobid(machine['job_id'])

            machine_specs = {}
            machine_specs.update(machine)
            machine_specs['password'] = password
            show_specs = """<fieldset>
<legend>VM Specs:</legend><ul class="no-bullets">
<li><input type="text" readonly value="%(os)s"> base system</li>
<li><input type="text" readonly value="%(flavor)s"> software flavor</li>
<li><input type="text" readonly value="%(memory)s"> MB memory</li>
<li><input type="text" readonly value="%(disk)s"> GB disk</li>
<li><input type="text" readonly value="%(cpu_count)s"> CPU's</li>
<li><input type="text" readonly value="%(vm_arch)s"> architecture</li>
"""
            if password != 'UNKNOWN':
                show_specs += """            
<li><input type="text" readonly value="%(password)s"> as VNC password</li>
"""
            show_specs += """            
</form></ul></fieldset>"""
            edit_specs = """<fieldset>
<legend>Edit VM Specs:</legend><ul class="no-bullets">
<form method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="action" value="edit">
""" % fill_helpers
            edit_specs += """
<input type="hidden" name="machine_name" value="%(name)s">
<input type="hidden" name="output_format" value="html">

<li><input type="text" readonly name="os" value="%(os)s"> base system</li>
<li><input type="text" readonly name="flavor" value="%(flavor)s"> software flavor</li>
<li><input type="text" readonly name="hypervisor_re" value="%(hypervisor_re)s"> hypervisor runtime env</li>
<li><input type="text" readonly name="sys_re" value="%(sys_re)s"> image pack runtime env</li>
<li><input type="text" name="memory" value="%(memory)s"> MB memory</li>
<li><input type="text" name="disk" value="%(disk)s"> GB disk</li>
<li><input type="text" name="cpu_count" value="%(cpu_count)s"> CPU's</li>
<li><select name="architecture">
"""
            for arch in [''] + configuration.architectures:
                select = ''
                if arch == machine_specs['architecture']:
                    select = 'selected'
                edit_specs += "<option %s value='%s'>%s</option>" % (select, arch,
                                                                     arch)
            edit_specs += """</select> resource architecture
<li><input type="text" name="cpu_time" value="%(cpu_time)s"> s time slot</li>
<li><select name="vgrid" multiple>"""
            for vgrid_name in [any_vgrid] + \
                    user_vgrid_access(configuration, client_id):
                select = ''
                if vgrid_name in machine_specs['vgrid']:
                    select = 'selected'
                edit_specs += "<option %s>%s</option>" % (select, vgrid_name)
            edit_specs += """</select> %s(s)</li>""" % \
                          configuration.site_vgrid_label
            if password != 'UNKNOWN':
                edit_specs += """
<li><input type="text" readonly value="%(password)s"> as VNC password</li>
"""
            edit_specs += """
<input class="styled_button" type="submit" value="Save Changes">
</form>"""
            js_name = 'deletevm%s' % hexlify("%(name)s" % machine_specs)
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'machine_name': machine_specs['name'],
                                       'action': 'delete',
                                       csrf_field: csrf_token})
            edit_specs += helper
            edit_specs += """<input class="styled_button" type="submit"
value="Delete Machine" onClick="javascript: confirmDialog(%s, '%s');" >
""" % (js_name, "Really permanently delete %(name)s VM?" % machine_specs)
            edit_specs += """</ul></fieldset>"""
            if machine['status'] == 'EXECUTING' and exec_time > boot_secs:
                machine_image = '<img src="/images/vms/' \
                    + machine_states[machine['status']] + '">'
            elif machine['status'] == 'EXECUTING' and exec_time < boot_secs:
                machine_image = \
                    '<img src="/images/vms/vm_desktop_loading.jpg' \
                    + '">'
            else:
                machine_image = '<img src="/images/vms/' \
                    + machine_states[machine['status']] + '">'
            machine_link = vms.machine_link(machine_image,
                                            machine['job_id'],
                                            machine['name'], machine['uuid'],
                                            machine['status'], machine_req)

            # Smack all the html together

            fill_dict = {}
            fill_dict.update(machine)
            fill_dict['link'] = machine_link
            fill_dict['show_specs'] = show_specs % machine_specs
            fill_dict['edit_specs'] = edit_specs % machine_specs
            pretty_machines += '''
<td style="vertical-align: top;">
<fieldset><legend>%(name)s</legend>
<div id="%(name)s-tabs" class="vm-tabs">
<ul>
<li><a href="#%(name)s-overview">Overview</a></li>
<li><a href="#%(name)s-edit">Advanced</a></li>
</ul>
<div id="%(name)s-overview">
<p>%(link)s</p>
%(show_specs)s
</div>
<div id="%(name)s-edit">
%(edit_specs)s
</div>
</div>
</fieldset>
</td>''' % fill_dict

        pretty_machines += '</tr></table>'

        output_objects.append(
            {'object_type': 'html_form', 'text': pretty_machines})
    else:
        output_objects.append(
            {'object_type': 'text', 'text': "You don't have any virtual machines! "
             "Click 'Request Virtual Machine' to become a proud owner :)"
             })

    return (output_objects, status)
