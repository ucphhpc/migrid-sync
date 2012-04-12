#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# vms - shared virtual machine functions
#
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

"""A collection of functions for doing various stuff specific for the use
virtual  machines, creation of mRSL for start, grabbing status, listing
machines etc.
"""

import os
import ConfigParser
import re
import md5
import shutil
from glob import glob
from string import Template

from shared.base import client_id_dir
from shared.fileio import unpickle
from shared.job import new_job


def vnc_jobid(job_id='Unknown'):
    """
    1: Job identifier = 64_5_30_2009__10_10_15_localhost.0

    2: Md5 sum (16bytes) 32 char hex. string = 01b19818762fbaf81693001639b1379c

    3: Lower to (8bytes) 16 char hex. string: 01 b1 98 18 76 2f ba f8

    4: Convert to user inputable ascii table characters:

        Ascii table offset by 64 + [0-16]
  
    This methods provides 127^8 identifiers.
    """

    job_id_digest = md5.new(job_id).hexdigest()[:16]  # 2
    password = ''
    for i in range(0, len(job_id_digest), 2):  # 3, 4

        char = 32 + int(job_id_digest[i:i + 2], 16)
        if char > 251:
            password += chr(char / 3)
        elif char > 126:
            password += chr(char / 2)
        else:
            password += chr(char)

    return password

def vms_list(client_id, configuration):
    """Returns a list of dicts describing users available virtual machines
    described by following keys:
 
    'name', 'ram', 'state'
 
    NOTE:

      The current state management does not fully exploit the powers of the
      grid, it only allows one 'instance' of the virtual machine to be
      running. But in practice a user could fairly use multiple instances
      of the same virtual machine. Using this basic model is feasible
      since the job submission is controlled via the web interface. It
      will however break if the user manually submits her own job.
      
      Currently two ways of deploying machines to resources exist:
      - By using VirtualBox frontend (work of Tomas)
      - By using webinterface (work of Simon)
      
      The storage of virtual machines are based on xml files (deployed by virtualbox)
      or ini files when deployed by MiG. This library supports both and the logic
      is separeted into functions where appropriate.
    """

    # Grab the base directory of the user

    client_dir = client_id_dir(client_id)
    user_home = os.path.abspath(os.path.join(configuration.user_home,
                                             client_dir))
    mrsl_files_dir = os.path.abspath(os.path.join(configuration.mrsl_files_dir,
                                                  client_dir))

    # Append the virtual machine directory

    vms_paths = glob(os.path.join(user_home, 'vms', '*', '*.cfg'))

    # List of virtual machines

    vms = []

    for vm_def_path in vms_paths:

        machine = {
            'name': 'UNKNOWN',
            'path': os.path.abspath(vm_def_path),
            'status': 'UNKNOWN',
            'execution_time': 'UNKNOWN',
            'job_id': 'UNKNOWN',
            'memory': 'UNKNOWN',
            'cpu_count': 'UNKNOWN',
            'arch': 'UNKNOWN',
            'uuid': 'UNKNOWN',
            }

        # Grab the configuration file defining the machine

        vm_def_base = os.path.basename(os.path.dirname(vm_def_path))

        vm_config = ConfigParser.ConfigParser()
        vm_config.read([vm_def_path])

        machine['name'] = vm_def_base
        machine['memory'] = vm_config.get('DEFAULT', 'mem')
        machine['cpu_count'] = vm_config.get('DEFAULT', 'cpus')
        machine['arch'] = vm_config.get('DEFAULT', 'arch')

        # All job descriptions associated with this virtual machine

        jobs = []
        match_line = 'VBoxManage createvm -name "' + vm_def_base \
            + '" -register'
        for stuff in glob(os.path.join(mrsl_files_dir, '*')):
            for line in open(os.path.abspath(stuff), 'r', 1):

                if match_line in line:
                    jobs.append(unpickle(stuff, configuration.logger))
                    break

        # Base the state on the latest job.
        #
        # Now determine the state of the jobs.
        # Job status can be one of EXECUTING, CANCELED, QUEUED, FINISHED, the
        # machine state mapping is:
        # EXECUTING -> Powered On
        # CANCELED/FINISHED -> Powered Off
        # QUEUED -> Booting
        #
        # TODO: 3

        if len(jobs) > 0:
            machine['status'] = jobs[len(jobs) - 1]['STATUS']
            if machine['status'] == 'EXECUTING':
                machine['execution_time'] = jobs[len(jobs)
                        - 1]['EXECUTING_TIMESTAMP']
            machine['job_id'] = jobs[len(jobs) - 1]['JOB_ID']

        vms.append(machine)

    return vms

def vnc_applet(
    proxy_host,
    proxy_port,
    applet_port,
    width,
    height,
    password,
    ):
    """Generates the html tag needed for loading the vnc applet.
    Takes care of fixing representation of the password.
 
    You just specifify a jobidentifier and where all happy.
    """

    applet = """<APPLET CODE="VncViewer" ARCHIVE="VncViewer.jar" """
    applet += ' CODEBASE="http://%s:%d/tightvnc/"' % (proxy_host,
            applet_port)
    applet += ' WIDTH="%d" HEIGHT="%d">' % (width, height)
    applet += '<PARAM NAME="PORT" VALUE="%d">' % proxy_port
    applet += '<PARAM NAME="PASSWORD" VALUE="%s">' % password

    # applet += "<PARAM NAME=\"Encoding\" VALUE=\"Raw\">"

    applet += '</APPLET>'

    return applet

def popup_snippet():
    """Just a simple piece of js to popup a window"""

    return """
    <script>
    function vncClientPopup() {
    var win = window.open("", "win", "menubar=no,toolbar=no");
    
    win.document.open("text/html", "replace");
    win.document.write('<HTML><HEAD><TITLE>MiG Remote Access</TITLE></HEAD><BODY>%s</BODY></HTML>');
    win.document.close();
    }
    </script>"""


def machine_link(
    content,
    job_id,
    name,
    uuid,
    state,
    ):
    """A convenience functions for creating links to 'stop/stop/connect'.
    Depending on the machine state.
    """

    link = ''

    if state == 'EXECUTING':
        link = \
            '<a href="/cgi-bin/vmachines_connect.py?job_id=%s">%s</a>' \
            % (job_id, content)
    elif state == 'QUEUED':
        link = content
    else:

        # Canceled, Finished, Unknown

        link = '<a href="?start=%s">%s</a>' % (name, content)

    return link

def create_vm(client_id, configuration, machine_name):
    """Create virtual machine"""
    
    client_dir = client_id_dir(client_id)

    # Primitive sanitize of machine name
    # Only allow A-z and numbers and no longer than 30 chars

    machine_name = re.sub('[^A-Za-z0-9]*', '', machine_name)[:30]

    # Setup paths - filter above prevents directory traversal

    user_home = os.path.abspath(os.path.join(configuration.user_home,
                                             client_dir))
    user_vms_home = os.path.join(user_home, 'vms')
    vm_home = os.path.join(user_vms_home, machine_name)
    server_vms_home = os.path.join(configuration.server_home, 'vms')
    server_vms_builder_home = os.path.join(configuration.server_home,
                                           'vms_builder')

    # Create users vms storage

    if not os.path.exists(user_vms_home):
        os.mkdir(user_vms_home)
        shutil.copy(os.path.join(server_vms_home, 'runvm.sh'),
                    user_vms_home + os.sep)

    # Create the vm

    if not os.path.exists(vm_home):
        os.mkdir(vm_home)
        shutil.copy(os.path.join(server_vms_builder_home, 'machine.cfg'),
                    vm_home + os.sep)
        shutil.copy(os.path.join(server_vms_builder_home, 'data.vmdk'),
                    vm_home + os.sep)
        open(os.path.join(vm_home, 'sys_plain.remote'), 'a')


def enqueue_vm(client_id, configuration, machine_name):
    """Submit a machine job based on machine definition file"""

    filename = '/tmp/thisisatest.mrsl'

    # Generate the mrsl

    mrsl = mig_deployed_job(machine_name)
    mrsl_fd = open(filename, 'w', 0)
    mrsl_fd.write(mrsl)
    mrsl_fd.close()

    # Find the machine the given name

    return new_job(filename, client_id, configuration, False, True)


def mig_deployed_job(
    name='Unknown',
    data_disk='data.vmdk',
    sys_disk='plain.vmdk',
    memory=1024,
    cpu_count=1,
    cpu_time=900,
    ):
    """This method assumes that the system disk is registered on the
    resource.
    """

    mrsl = \
        Template("""::EXECUTE::                  
rm -rf ~/.VirtualBox
mkdir ~/.VirtualBox
mkdir ~/.VirtualBox/Machines
mkdir ~/.VirtualBox/HardDisks
cp ~/vbox_disks/plain.vmdk ~/.VirtualBox/HardDisks/plain.vmdk
mv data.vmdk ~/.VirtualBox/HardDisks/+JOBID+_data.vmdk
VBoxManage openmedium disk +JOBID+_data.vmdk
VBoxManage openmedium disk plain.vmdk
VBoxManage createvm -name "$NAME" -register
VBoxManage modifyvm "$NAME" -nic1 nat
VBoxManage modifyvm "$NAME" -memory $MEMORY
VBoxManage modifyvm "$NAME" -pae on
VBoxManage modifyvm "$NAME" -hwvirtex on
VBoxManage modifyvm "$NAME" -ioapic off
VBoxManage modifyvm "$NAME" -hda "plain.vmdk"
VBoxManage modifyvm "$NAME" -hdb "+JOBID+_data.vmdk"
VBoxManage guestproperty set "$NAME" job_id +JOBID+
./runvm.sh $NAME 780
VBoxManage modifyvm $NAME -hda none
VBoxManage modifyvm $NAME -hdb none
VBoxManage closemedium disk +JOBID+_data.vmdk
VBoxManage unregistervm $NAME -delete
mv ~/.VirtualBox/HardDisks/+JOBID+_data.vmdk data.vmdk

::INPUTFILES::
vms/$NAME/data.vmdk data.vmdk

::OUTPUTFILES::
data.vmdk vms/$NAME/data.vmdk

::EXECUTABLES::
vms/runvm.sh runvm.sh

::MEMORY::
$MEMORY

::CPUTIME::
900

::ARCHITECTURE::
AMD64

::VGRID::
Generic

::NOTIFY::
jabber: SETTINGS

""")
    return mrsl.substitute(NAME=name, CPU_COUNT=cpu_count,
                           MEMORY=memory)


