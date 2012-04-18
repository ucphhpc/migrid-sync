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
from shared.functional import validate_input_and_cert
from shared.html import render_menu
from shared.init import initialize_main_variables, find_entry

def signature():
    """Signature of the main function"""

    defaults = {
        'start': [''],
        'stop': [''],
        'machine_name': [''],
        'machine_request': ['0'],
        'machine_type': [''],
        'pre_built': [''],
        'machine_arch': [''],
        'machine_cpu': [''],
        'machine_ram': [''],
        'machine_partition': [''],
        'machine_software': [''],
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

    machine_request = (accepted['machine_request'][-1] == '1')
    machine_name = accepted['machine_name'][-1]
    pre_built = accepted['pre_built'][-1]
    start = accepted['start'][-1]
    stop = accepted['stop'][-1]

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

    if machine_request:
        if not machine_name:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested build without machine name"})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)            
        elif not pre_built in vms.pre_built_flavors:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 "requested pre-built flavor not available: %s" % pre_built})
            status = returnvalues.CLIENT_ERROR
            return (output_objects, status)

        # TODO: support custom build og machine

        # request for existing pre-built machine

        vms.create_vm(client_id, configuration, machine_name,
                      sys_flavor=pre_built)

    (action_status, action_msg, job_id) = (True, '', None)
    if start:
        (action_status, action_msg, job_id) = \
                        vms.enqueue_vm(client_id, configuration, start)
    elif stop:

        # TODO: manage stop

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

        # Create a pretty list with start/stop/connect links

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

            specs = """<fieldset><legend>Specs:</legend>
<ul><li>Memory: %s</li><li>Cpu's: %s</li><li>Arch: %s</li>
<li>Password: %s</li></ul>
</fieldset>""" % (machine['memory'], machine['cpu_count'],
                  machine['arch'], password)
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
                    ], machine['status'])

            # Smack all the html together

            pretty_machines += '''
<td style="vertical-align: top;">
<fieldset><legend>%s</legend> %s %s</fieldset>
</td>''' % (machine['name'], machine_link, specs)

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


