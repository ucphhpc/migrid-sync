#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vmachines - virtual machine management
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

"""Virtual machine administration back end functionality"""

import time

import shared.returnvalues as returnvalues
from shared import vms
from shared.defaults import any_vgrid
from shared.functional import validate_input_and_cert
from shared.html import render_menu
from shared.init import initialize_main_variables, find_entry
from shared.vgrid import user_allowed_vgrids

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

    machine_name = accepted['machine_name'][-1]
    memory = int(accepted['memory'][-1])
    disk = int(accepted['disk'][-1])
    vgrid = accepted['vgrid']
    architecture = accepted['architecture'][-1]
    cpu_count = int(accepted['cpu_count'][-1])
    cpu_time = int(accepted['cpu_time'][-1])
    os = accepted['os'][-1]
    flavor = accepted['flavor'][-1]
    sys_re = accepted['sys_re'][-1]
    action = accepted['action'][-1]

    machine_req = {'memory': memory, 'disk': disk, 'cpu_count': cpu_count,
                   'cpu_time': cpu_time, 'architecture': architecture,
                   'vgrid': vgrid, 'os': os, 'flavor': flavor, 'sys_re':
                   sys_re}
    
    menu_items = ['vmrequest']

    # Html fragments

    submenu = render_menu(configuration, menu_class='navsubmenu',
                          user_menu=menu_items, hide_default=True)

    welcome_text = 'Welcome to your %s virtual machine management!' % \
                   configuration.short_title
    desc_text = '''<p>On this page you can:
<ul>
    <li>Request Virtual Machines, by clicking on the button above</li>
    <li>See your virtual machines in the list below.</li>
    <li>Start, and connect to your Virtual Machine by clicking on it.</li>
</ul>
</p>'''

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Virtual Machines'
    output_objects.append({'object_type': 'header', 'text':
                           'Virtual Machines'})
    output_objects.append({'object_type': 'html_form', 'text': submenu})
    output_objects.append({'object_type': 'html_form', 'text'
                          : '<p>&nbsp;</p>'})
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : welcome_text})
    output_objects.append({'object_type': 'html_form', 'text'
                          : desc_text})

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
        elif not sys_re in vms.available_sys_re_list(configuration):
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested system pack runtime env not available: %s" % \
                 sys_re})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)

        # TODO: support custom build of machine using shared/vmbuilder.py

        # request for existing pre-built machine

        vms.create_vm(client_id, configuration, machine_name, machine_req)

    (action_status, action_msg, job_id) = (True, '', None)
    if action in ['start', 'stop', 'edit']:
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
    elif action == 'stop':
        
        # TODO: manage stop - use live I/O to create vmname.stop in job dir

        pass

    if not action_status:
        output_objects.append({'object_type': 'error_text', 'text':
                               action_msg})
    
    # List the machines here

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Your machines:'})

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

    # CANCELED/FAILED/FINISHED -> Powered Off
    # QUEUED -> Booting

    if len(machines) > 0:

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
            specs = """<fieldset>
<legend>Specs:</legend><ul>
<form method="post" action="vmachines.py">
<input type="hidden" name="action" value="edit">
<input type="hidden" name="machine_name" value="%(name)s">
<input type="hidden" name="output_format" value="html">

<li><input type="text" readonly name="os" value="%(os)s"> base system</li>
<li><input type="text" readonly name="flavor" value="%(flavor)s"> software flavor</li>
<li><input type="text" readonly name="sys_re" value="%(sys_re)s"> image pack runtime env</li>
<li><input type="text" name="memory" value="%(memory)s"> MB memory</li>
<li><input type="text" readonly name="disk" value="%(disk)s"> GB disk</li>
<li><input type="text" name="cpu_count" value="%(cpu_count)s"> CPU's</li>
<li><select name="architecture">
"""
            for arch in [''] + configuration.architectures:
                select = ''
                if arch == machine_specs['architecture']:
                    select = 'selected'
                specs += "<option %s value='%s'>%s</option>" % (select, arch,
                                                                arch)
            specs += """</select> resource architecture
<li><input type="text" name="cpu_time" value="%(cpu_time)s"> s time slot</li>
<li><select name="vgrid" multiple>"""
            for vgrid_name in [any_vgrid] + \
                    user_allowed_vgrids(configuration, client_id):
                select = ''
                if vgrid_name in machine_specs['vgrid']:
                    select = 'selected'
                specs += "<option %s>%s</option>" % (select, vgrid_name)
            specs += """</select> VGrid(s)</li>"""
            specs += """            
<li><input type="text" readonly value="%(password)s"> as VNC password</li>
<input class="styled_button" type="submit" value="Save">
</form></ul></fieldset>"""
            if machine['status'] == 'EXECUTING' and exec_time > 130:
                machine_image = '<img src="/images/vms/' \
                    + machine_states[machine['status']] + '">'
            elif machine['status'] == 'EXECUTING' and exec_time < 130:
                machine_image = \
                    '<img src="/images/vms/vm_desktop_loading.jpg' \
                    + '">'
            else:
                machine_image = '<img src="/images/vms/' \
                    + machine_states[machine['status']] + '">'
            machine_link = vms.machine_link(machine_image,
                    machine['job_id'], machine['name'], machine['uuid'
                    ], machine['status'], machine_req)

            # Smack all the html together

            pretty_machines += '''
<td style="vertical-align: top;">
<fieldset><legend>%s</legend> %s %s</fieldset>
</td>''' % (machine['name'], machine_link, specs % machine_specs)

        pretty_machines += '</tr></table>'

        output_objects.append({'object_type': 'html_form', 'text'
                              : pretty_machines})
    else:
        output_objects.append(
            {'object_type': 'text', 'text'
             : "You don't have any virtual machines! "
             "Click 'Request Virtual Machine' to become a proud owner :)"
             })

    output_objects.append({'object_type': 'html_form', 'text'
                          : '''<p>
You can manually delete your virtual machines by removing the directory of the
corresponding name in <a href="fileman.py?path=vms/">your vms directory</a>.
</p>'''
                           })
    return (output_objects, status)


