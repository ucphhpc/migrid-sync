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

import datetime
import ConfigParser
import md5
import operator
import os
import re
import shutil
from glob import glob
from tempfile import NamedTemporaryFile

from shared.base import client_id_dir
from shared.defaults import any_vgrid
from shared.fileio import unpickle
from shared.job import new_job

default_os = 'ubuntu-8.10'
default_flavor = 'basic'
default_diskformat = 'vmdk'
default_hypervisor = 'vbox31'
sys_location = 'sys_location.txt'
pre_built_flavors = [default_flavor, 'numpy']


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
      
      The storage of virtual machines are based on xml files (deployed by
      virtualbox)
      or ini files when deployed by MiG. This library supports both and the
      logic is separated into functions where appropriate.
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
        match_line = "$VBOXMANAGE -q createvm --name '" + vm_def_base \
            + "' --register"
        # we cannot inspect all mrsl files - filter by year is good guesstimate
        # TODO: mark vms jobs for easy finding without brute force search
        for mrsl_path in glob(os.path.join(mrsl_files_dir, '*_%d_*' % \
                                           datetime.date.today().year)):
            for line in open(os.path.abspath(mrsl_path), 'r', 1):
                if match_line in line:
                    jobs.append(unpickle(mrsl_path, configuration.logger))

        # Base the state on the latest job.
        #
        # Now determine the state of the jobs.
        # Job status can be one of EXECUTING, CANCELED, FAILED, QUEUED,
        # FINISHED, the machine state mapping is:
        # EXECUTING -> Powered On
        # CANCELED/FAILED/FINISHED -> Powered Off
        # QUEUED -> Booting
        #
        # TODO: 3

        if len(jobs) > 0:
            sorted_jobs = sorted(jobs, key=operator.itemgetter('JOB_ID'))
            last = sorted_jobs[-1]
            machine['status'] = last['STATUS']
            if machine['status'] == 'EXECUTING':
                machine['execution_time'] = last['EXECUTING_TIMESTAMP']
            machine['job_id'] = last['JOB_ID']

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
            '<a href="vmconnect.py?job_id=%s">%s</a>' \
            % (job_id, content)
    elif state == 'QUEUED':
        link = content
    else:

        # Canceled, Finished, Unknown

        link = '<a href="?start=%s">%s</a>' % (name, content)

    return link

def create_vm(client_id, configuration, machine_name,            
              os_name=default_os,
              sys_flavor=default_flavor,
              disk_format=default_diskformat,
              hypervisor=default_hypervisor,
              sys_img_from_re='VBOX3.1-IMAGES-2008-1',
              sys_base='$VBOXIMGDIR',
              ):
    """Create virtual machine with machine_name as ID and using data_disk as
    data image base.
    Set sys_img_from_re and sys_base to use common images from the runtime env
    on the resource or unset both to use a custom image from user home.
    """
    
    # Setup paths - input filter prevents directory traversal

    client_dir = client_id_dir(client_id)
    user_home = os.path.abspath(os.path.join(configuration.user_home,
                                             client_dir))
    user_vms_home = os.path.join(user_home, 'vms')
    vm_home = os.path.join(user_vms_home, machine_name)
    server_vms_builder_home = os.path.join(configuration.server_home,
                                           'vms_builder')
    sys_disk = '%s-%s.%s' % (os_name, sys_flavor, disk_format)
    sys_conf = '%s-%s.cfg' % (os_name, sys_flavor)
    data_disk = '%s-%s.%s' % (os_name, 'data', disk_format)
    run_script='run%svm.sh' % hypervisor

    # Create users vms storage

    if not os.path.exists(user_vms_home):
        os.mkdir(user_vms_home)
        shutil.copy(os.path.join(server_vms_builder_home, run_script),
                    user_vms_home + os.sep)

    # Create the vm

    if not os.path.exists(vm_home):
        os.mkdir(vm_home)
        shutil.copy(os.path.join(server_vms_builder_home, data_disk),
                    vm_home + os.sep)

        # Use OS image from runtime env resource for performance if possible
        # with fall back to image from user home if custom image

        if sys_img_from_re:
            img_re = sys_img_from_re
            img_location = sys_base
            sys_conf = 'default.cfg'
        else:
            img_re = ''
            img_location = ''
            shutil.copy(os.path.join(server_vms_builder_home, sys_disk),
                        vm_home + os.sep)

        # Build conf file is always needed for arch, mem and cpu

        shutil.copy(os.path.join(server_vms_builder_home, sys_conf),
                    vm_home + os.sep)
        location_fd = open(os.path.join(vm_home, sys_location), 'w')
        location_fd.write("%s:%s:%s" % (img_re, img_location, sys_disk))
        location_fd.close()
        
def enqueue_vm(client_id, configuration, machine_name,
               os_name=default_os,
               sys_flavor=default_flavor,
               disk_format=default_diskformat,
               hypervisor=default_hypervisor,
               sys_base='$VBOXIMGDIR',
               user_conf='$VBOXUSERCONF',
               img_dir='vms',
               memory=1024,
               disk=1,
               cpu_count=1,
               cpu_time=900,
               architecture='',
               vgrid=[any_vgrid],
               runtime_env=['VIRTUALBOX-3.1.X-1'],
               notify=['jabber: SETTINGS'],
               ):
    """Submit a machine job based on machine definition file.
    Returns the job submit result, a 3-tuple of (status, msg, job_id)
    """

    # Setup paths - filter above prevents directory traversal

    client_dir = client_id_dir(client_id)
    user_home = os.path.abspath(os.path.join(configuration.user_home,
                                             client_dir))
    user_vms_home = os.path.join(user_home, 'vms')
    vm_home = os.path.join(user_vms_home, machine_name)
    location_fd = open(os.path.join(vm_home, sys_location), 'r')
    (sys_re, sys_base, sys_disk) = location_fd.read().split(':')
    location_fd.close()
    if sys_re:
        runtime_env.append(sys_re)
    data_disk = '%s-data.%s' % (os_name, disk_format)
    run_script='run%svm.sh' % hypervisor

    # Generate the mrsl and write to a temp file which is removed on close

    mrsl = mig_vbox_deployed_job(client_id, configuration, machine_name, sys_disk,
                                 data_disk, run_script, sys_base, user_conf,
                                 img_dir, memory, disk, cpu_count, cpu_time,
                                 architecture, vgrid, runtime_env, notify)
    mrsl_fd = NamedTemporaryFile()
    mrsl_fd.write(mrsl)
    mrsl_fd.flush()

    # Submit job and clean up

    res = new_job(mrsl_fd.name, client_id, configuration, False, True)
    mrsl_fd.close()
    return res

def mig_vbox_deployed_job(
    client_id,
    configuration,
    name,
    sys_disk,
    data_disk,
    run_script,
    sys_base,
    user_conf,
    img_dir,
    memory,
    disk,
    cpu_count,
    cpu_time,
    architecture,
    vgrid,
    runtime_env,
    notify,
    ):
    """This method assumes that the system disk, sys_disk, is available in
    sys_base on the resource either through a runtime environment or through
    the user home. If unset it is fetched from user home through INPUTFILES.
    """
    architecture_lines = ''
    vgrid_lines = ''
    runtime_env_lines = ''
    notify_lines = ''
    if architecture:
        architecture_lines = '::ARCHITECTURE::\n%s' % architecture
    if vgrid:
        vgrid_lines = '::VGRID::\n%s' % '\n'.join(vgrid)
    if runtime_env:
        runtime_env_lines = '::RUNTIMEENVIRONMENT::\n%s' % \
                            '\n'.join(runtime_env)
    if notify:
        notify_lines = '::NOTIFY::\n%s' % '\n'.join(notify)
    
    specs = {'name': name, 'data_disk': data_disk, 'sys_disk': sys_disk,
             'run_script': run_script, 'sys_base': sys_base, 'user_conf': 
             user_conf, 'img_dir': img_dir, 'memory': memory, 'disk': disk,
             'cpu_count': cpu_count, 'cpu_time': cpu_time, 'architecture':
             architecture, 'vgrid': vgrid, 'runtime_env': runtime_env,
             'notify': notify, 'architecture_lines': architecture_lines,
             'vgrid_lines': vgrid_lines, 'runtime_env_lines':
             runtime_env_lines, 'notify_lines': notify_lines,
             'effective_disk': disk + 1, 'effective_time': cpu_time - 30,
             'proxy_host': configuration.vm_proxy_host,
             'proxy_port': configuration.vm_proxy_port,
             }
    job = """::EXECUTE::
rm -rf %(user_conf)s
mkdir %(user_conf)s
mkdir %(user_conf)s/Machines
mkdir %(user_conf)s/HardDisks
"""
    if sys_base:
        job += "cp %(sys_base)s/%(sys_disk)s %(user_conf)s/HardDisks/%(sys_disk)s"
    job += """
mv %(data_disk)s %(user_conf)s/HardDisks/+JOBID+_%(data_disk)s
$VBOXMANAGE -q openmedium disk +JOBID+_%(data_disk)s
$VBOXMANAGE -q openmedium disk %(sys_disk)s
$VBOXMANAGE -q createvm --name '%(name)s' --register
$VBOXMANAGE -q modifyvm '%(name)s' --nic1 nat --memory %(memory)d --pae on --hwvirtex on --ioapic off
$VBOXMANAGE -q storagectl '%(name)s' --name 'IDE Controller' --add ide
$VBOXMANAGE -q storageattach '%(name)s' --storagectl 'IDE Controller' --port 0 --device 0 --type hdd --medium '%(sys_disk)s'
$VBOXMANAGE -q storageattach '%(name)s' --storagectl 'IDE Controller' --port 1 --device 0 --type hdd --medium '+JOBID+_%(data_disk)s'
$VBOXMANAGE -q guestproperty set '%(name)s' job_id +JOBID+
$VBOXMANAGE -q guestproperty set '%(name)s' proxy_host %(proxy_host)s
$VBOXMANAGE -q guestproperty set '%(name)s' proxy_port %(proxy_port)d
./%(run_script)s '%(name)s' %(effective_time)d
$VBOXMANAGE -q storageattach '%(name)s' --storagectl 'IDE Controller' --port 0 --device 0 --type hdd --medium none
$VBOXMANAGE -q storageattach '%(name)s' --storagectl 'IDE Controller' --port 1 --device 0 --type hdd --medium none
$VBOXMANAGE -q storagectl '%(name)s' --name 'IDE Controller' --remove
$VBOXMANAGE -q closemedium disk %(sys_disk)s
$VBOXMANAGE -q closemedium disk +JOBID+_%(data_disk)s
$VBOXMANAGE -q unregistervm '%(name)s' --delete
mv %(user_conf)s/HardDisks/+JOBID+_%(data_disk)s %(data_disk)s

::INPUTFILES::
%(img_dir)s/%(name)s/%(data_disk)s %(data_disk)s
"""
    if not sys_base:
        job += """%(img_dir)s/%(name)s/%(sys_disk)s %(sys_disk)s
"""
    job += """
::OUTPUTFILES::
%(data_disk)s %(img_dir)s/%(name)s/%(data_disk)s

::EXECUTABLES::
%(img_dir)s/%(run_script)s %(run_script)s

::MEMORY::
%(memory)d

::DISK::
%(effective_disk)d

::CPUCOUNT::
%(cpu_count)d

::CPUTIME::
%(cpu_time)d

%(vgrid_lines)s

%(architecture_lines)s

%(runtime_env_lines)s

%(notify_lines)s
"""
    return job % specs
