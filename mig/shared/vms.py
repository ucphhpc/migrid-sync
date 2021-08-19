#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# vms - shared virtual machine functions
#
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from builtins import chr
from builtins import range
from past.builtins import basestring
import datetime
import configparser
import md5
import operator
import os
import shutil
from glob import glob
from tempfile import NamedTemporaryFile

from mig.shared.base import client_id_dir
from mig.shared.defaults import any_vgrid
from mig.shared.fileio import unpickle, remove_rec
from mig.shared.job import new_job

sys_location = 'sys_location.txt'
vm_base = 'vms'


def available_os_list(configuration):
    """Returns a list of available VM OS versions"""
    return [configuration.vm_default_os] + configuration.vm_extra_os


def available_flavor_list(configuration):
    """Returns a list of available VM flavors (package sets)"""
    return [configuration.vm_default_flavor] + configuration.vm_extra_flavors


def available_hypervisor_re_list(configuration):
    """Returns a list of available VM hypervisor runtime envs"""
    return [configuration.vm_default_hypervisor_re] + \
        configuration.vm_extra_hypervisor_re


def available_sys_re_list(configuration):
    """Returns a list of available VM system pack runtime envs"""
    return [configuration.vm_default_sys_re] + configuration.vm_extra_sys_re


def default_vm_specs(configuration):
    """Returns a dictionarydefault VM specs from configuration"""
    specs = {}
    specs['memory'] = 1024
    specs['disk'] = 2
    specs['cpu_count'] = 1
    specs['cpu_time'] = 900
    specs['screen_xres'] = 1024
    specs['screen_yres'] = 768
    specs['screen_bpp'] = 24
    # VM image architecture
    specs['vm_arch'] = 'i386'
    # Resource architecture
    specs['architecture'] = ''
    specs['vgrid'] = [any_vgrid]
    specs['runtime_env'] = []
    specs['notify'] = ['jabber: SETTINGS']
    specs['os'] = configuration.vm_default_os
    specs['flavor'] = configuration.vm_default_flavor
    specs['disk_format'] = configuration.vm_default_disk_format
    specs['hypervisor'] = configuration.vm_default_hypervisor
    specs['hypervisor_re'] = configuration.vm_default_hypervisor_re
    specs['sys_re'] = configuration.vm_default_sys_re
    specs['sys_base'] = configuration.vm_default_sys_base
    specs['user_conf'] = configuration.vm_default_user_conf
    return specs


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
            password += chr(char // 3)
        elif char > 126:
            password += chr(char // 2)
        else:
            password += chr(char)

    return password


def vms_list(client_id, configuration):
    """Returns a list of dicts describing available user virtual machines
    described by the keys from default_vm_specs and the additional fields:

    'name', 'status', 'uuid', 'execution_time' and 'path'

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

    vms_paths = glob(os.path.join(user_home, vm_base, '*', '*.cfg'))

    # List of virtual machines

    vms = []

    for vm_def_path in vms_paths:
        machine = {}
        machine_defaults = default_vm_specs(configuration)
        machine_state = {
            'name': 'UNKNOWN',
            'path': os.path.abspath(vm_def_path),
            'status': 'UNKNOWN',
            'execution_time': 'UNKNOWN',
            'job_id': 'UNKNOWN',
            'uuid': 'UNKNOWN',
        }
        machine.update(machine_defaults)
        machine.update(machine_state)

        # Grab the configuration file defining the machine

        vm_def_base = os.path.basename(os.path.dirname(vm_def_path))

        vm_config = configparser.ConfigParser()
        vm_config.read([vm_def_path])

        machine['name'] = vm_def_base
        # override defaults with conf values
        for key in machine_defaults:
            if vm_config.has_option('MiG', key):
                machine[key] = vm_config.get('MiG', key)
        # vgrid entry must be a list of strings
        if isinstance(machine['vgrid'], basestring):
            machine['vgrid'] = machine['vgrid'].split()

        # All job descriptions associated with this virtual machine

        jobs = []
        match_line = "$VBOXMANAGE -q createvm --name '" + vm_def_base \
            + "' --register"
        # we cannot inspect all mrsl files - filter by year is good guesstimate
        # TODO: mark vms jobs for easy finding without brute force search
        for mrsl_path in glob(os.path.join(mrsl_files_dir, '*_%d_*' %
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
    configuration,
    width,
    height,
    password,
    https_base,
):
    """Generates the html tag needed for loading the vnc applet.
    Takes care of fixing representation of the password.

    You just specifify a jobidentifier and where all happy.
    """

    # New 2.5+ version from http://www.tightvnc.com needed for working keyboard
    # with recent VM images. Please refer to state/wwwpublic/README.vnc for
    # details

    vnc_dir = 'vnc'
    jar_name = 'tightvnc-jviewer.jar'
    code_hook = 'com.glavsoft.viewer.Viewer'
    host_address = '%s' % configuration.vm_proxy_host
    applet_base = os.path.join(configuration.wwwpublic, vnc_dir)
    applet_path = os.path.join(applet_base, jar_name)

    if not os.path.exists(applet_path):

        # Fall back to old 1.3 version served from proxy agent

        vnc_dir = 'tightvnc'
        jar_name = 'VncViewer.jar'
        code_hook = 'VncViewer'
        host_address = '%s:%d' % (configuration.vm_proxy_host,
                                  configuration.vm_applet_port)

    applet = '<APPLET CODE="%s" ARCHIVE="%s" ' % (code_hook, jar_name)
    applet += ' CODEBASE="%s/public/%s/"' % (https_base, vnc_dir)
    applet += ' WIDTH="%d" HEIGHT="%d">' % (width, height)
    applet += '<PARAM NAME="PORT" VALUE="%d">' % configuration.vm_client_port
    applet += '<PARAM NAME="PASSWORD" VALUE="%s">' % password
    applet += '<PARAM NAME="OpenNewWindow" VALUE="no" />'
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
    machine_req,
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

        specs_string = 'action=start;machine_name=%s' % name
        for (key, val) in machine_req.items():
            # Lists of strings must be split into multiple key=val pairs
            if not isinstance(val, basestring) and isinstance(val, list):
                for entry in val:
                    specs_string += ';%s=%s' % (key, entry)
            else:
                specs_string += ';%s=%s' % (key, val)
        link = '<a href="?%s">%s</a>' % (specs_string, content)

    return link


def create_vm(client_id, configuration, machine_name, machine_req):
    """Create virtual machine with machine_name as ID and using optional
    machine_req overrides dictionary to tune the vm. The dictionary includes
    the server configuration options:
    * os
    * flavor
    * disk_format
    * hypervisor
    * hypervisor_re
    * sys_re
    * sys_base
    * user_conf
    and vm specs used for the job description:
    * memory
    * disk
    * cpu_count
    * cpu_time
    * screen_xres
    * screen_yres
    * screen_bpp
    * vm_arch
    * architecture
    * vgrid
    * notify

    Set sys_re and sys_base to use common images from the runtime env
    on the resource or unset both to use a custom image from user home.
    """
    _logger = configuration.logger
    specs = default_vm_specs(configuration)
    specs.update(machine_req)

    # Setup paths - input filter prevents directory traversal

    client_dir = client_id_dir(client_id)
    user_home = os.path.abspath(os.path.join(configuration.user_home,
                                             client_dir))
    user_vms_home = os.path.join(user_home, vm_base)
    vm_home = os.path.join(user_vms_home, machine_name)
    server_vms_builder_home = os.path.join(configuration.server_home,
                                           'vms_builder')
    sys_disk = '%(os)s-%(vm_arch)s-%(flavor)s.%(disk_format)s' % specs
    sys_conf = '%(os)s-%(vm_arch)s-%(flavor)s.cfg' % specs
    data_disk = '%(os)s-%(vm_arch)s-data.%(disk_format)s' % specs
    run_script = 'run%(hypervisor)svm.sh' % specs

    # Create users vms storage

    if not os.path.exists(user_vms_home):
        os.mkdir(user_vms_home)
        shutil.copy(os.path.join(server_vms_builder_home, run_script),
                    user_vms_home + os.sep)

    # Create the vm

    if os.path.exists(vm_home):
        _logger.error("VM %s already exists for %s" % (machine_name,
                                                       client_id))
        return (False, "VM %s already exists!" % machine_name)
    else:
        data_disk_path = os.path.join(server_vms_builder_home, data_disk)
        if not os.path.isfile(data_disk_path):
            _logger.error("Missing data disk: %s" % data_disk_path)
            return (False, "No such data disk: %s" % data_disk)
        os.mkdir(vm_home)
        shutil.copy(data_disk_path, vm_home + os.sep)

        # Use OS image from runtime env resource for performance if possible
        # with fall back to image from user home if custom image

        if specs['sys_re']:
            img_re = specs['sys_re']
            img_location = specs['sys_base']
            sys_conf = 'default.cfg'
        else:
            img_re = ''
            img_location = ''
            sys_disk_path = os.path.join(server_vms_builder_home,
                                         specs['sys_disk'])
            if not os.path.isfile(data_disk_path):
                _logger.error("Missing system disk: %s" % sys_disk_path)
                return (False, "No such system disk: %(sys_disk)s" % specs)
            shutil.copy(sys_disk_path, vm_home + os.sep)

        # Build conf file is always needed for specs like arch, mem and cpu
        # copy default cfg and update with machine_req specs

        shutil.copy(os.path.join(server_vms_builder_home, sys_conf),
                    vm_home + os.sep)
        (edit_status, edit_msg) = edit_vm(client_id, configuration,
                                          machine_name, machine_req)
        location_fd = open(os.path.join(vm_home, sys_location), 'w')
        location_fd.write("%s:%s:%s" % (img_re, img_location, sys_disk))
        location_fd.close()
        return (edit_status, edit_msg)


def edit_vm(client_id, configuration, machine_name, machine_specs):
    """Updates the vm configuration for vm with given machine_name"""

    # Grab the base directory of the user

    client_dir = client_id_dir(client_id)
    user_home = os.path.abspath(os.path.join(configuration.user_home,
                                             client_dir))

    vms_conf_paths = glob(os.path.join(user_home, vm_base, machine_name,
                                       '*.cfg'))

    # Grab the configuration file defining the machine

    for conf_path in vms_conf_paths:
        vm_config = configparser.ConfigParser()
        vm_config.read([conf_path])
        for (key, val) in machine_specs.items():
            if not isinstance(val, basestring) and isinstance(val, list):
                string_val = ''
                for entry in val:
                    string_val += '%s ' % entry
            else:
                string_val = val
            vm_config.set('MiG', key, string_val)
        conf_fd = open(conf_path, 'w')
        vm_config.write(conf_fd)
        conf_fd.close()
    return (True, '')


def delete_vm(client_id, configuration, machine_name):
    """Deletes the vm dir with configuration and images for vm with given
    machine_name"""

    # Grab the base directory of the user

    client_dir = client_id_dir(client_id)
    user_home = os.path.abspath(os.path.join(configuration.user_home,
                                             client_dir))
    vms_machine_path = os.path.join(user_home, vm_base, machine_name)
    msg = ''
    success = remove_rec(vms_machine_path, configuration)
    if not success:
        msg = "Error while removing %s" % machine_name
    return (success, msg)


def enqueue_vm(client_id, configuration, machine_name, machine_req):
    """Submit a machine job based on machine definition file and overrides
    from machine_req.
    Returns the job submit result, a 3-tuple of (status, msg, job_id)
    """

    specs = default_vm_specs(configuration)
    specs.update(machine_req)

    # Setup paths - filter above prevents directory traversal

    client_dir = client_id_dir(client_id)
    user_home = os.path.abspath(os.path.join(configuration.user_home,
                                             client_dir))
    user_vms_home = os.path.join(user_home, vm_base)
    vm_home = os.path.join(user_vms_home, machine_name)
    location_fd = open(os.path.join(vm_home, sys_location), 'r')
    (sys_re, sys_base, sys_disk) = location_fd.read().split(':')
    location_fd.close()
    data_disk = '%(os)s-%(vm_arch)s-data.%(disk_format)s' % specs
    run_script = 'run%(hypervisor)svm.sh' % specs

    specs.update({'name': machine_name, 'data_disk': data_disk, 'run_script':
                  run_script, 'vm_base': vm_base, 'sys_re': sys_re, 'sys_base':
                  sys_base, 'sys_disk': sys_disk})
    if specs['hypervisor_re']:
        specs['runtime_env'].append(specs['hypervisor_re'])
    if specs['sys_re']:
        specs['runtime_env'].append(specs['sys_re'])

    # Generate the mrsl and write to a temp file which is removed on close

    mrsl = mig_vbox_deploy_job(client_id, configuration, machine_name,
                               specs)
    mrsl_fd = NamedTemporaryFile()
    mrsl_fd.write(mrsl)
    mrsl_fd.flush()

    # Submit job and clean up

    res = new_job(mrsl_fd.name, client_id, configuration, False, True)
    mrsl_fd.close()
    return res


def mig_vbox_deploy_job(client_id, configuration, name, machine_req):
    """Deploy a vbox vm on a resource through ordinary job submission.
    The machine_req dictionary can be used to override default settings.

    This method assumes that the system disk, sys_disk, is available in
    sys_base on the resource either through a runtime environment or through
    the user home. If unset it is fetched from user home through INPUTFILES.
    """
    specs = default_vm_specs(configuration)
    specs.update(machine_req)
    architecture_lines = ''
    vgrid_lines = ''
    runtime_env_lines = ''
    notify_lines = ''
    if specs['architecture']:
        architecture_lines = '::ARCHITECTURE::\n%(architecture)s' % specs
    if specs['vgrid']:
        vgrid_lines = '::VGRID::\n%s' % '\n'.join(specs['vgrid'])
    if specs['runtime_env']:
        runtime_env_lines = '::RUNTIMEENVIRONMENT::\n%s' % \
                            '\n'.join(specs['runtime_env'])
    if specs['notify']:
        notify_lines = '::NOTIFY::\n%s' % '\n'.join(specs['notify'])

    specs.update({'name': name, 'architecture_lines': architecture_lines,
                  'vgrid_lines': vgrid_lines, 'runtime_env_lines':
                  runtime_env_lines, 'notify_lines': notify_lines,
                  'effective_disk': specs['disk'] + 1, 'effective_time':
                  specs['cpu_time'] - 30, 'proxy_host':
                  configuration.vm_proxy_host, 'proxy_port':
                  configuration.vm_proxy_port, 'arch_opts': '',
                  'mac': '001122334455'
                  })
    if specs['vm_arch'] == 'i386':
        specs['arch_opts'] = '--pae on'
    else:
        # default NIC is not supported on all 64-bit OSes
        specs['arch_opts'] = '--nictype1 82543GC'
    job = '''::EXECUTE::
# vboxmanage unregister does not always properly remove machine settings file
# and existance prevents next run so make sure we delete it
rm -f "%(user_conf)s/../VirtualBox VMs/%(name)s/%(name)s.vbox"
# Clean environment
rm -rf %(user_conf)s
mkdir %(user_conf)s
mkdir %(user_conf)s/Machines
mkdir %(user_conf)s/HardDisks
'''
    if specs['sys_base']:
        job += "cp %(sys_base)s/%(sys_disk)s %(user_conf)s/HardDisks/%(sys_disk)s"
    # VM requires static MAC to avoid NIC renaming and ioapic for multi-cpu
    job += """
mv %(data_disk)s %(user_conf)s/HardDisks/+JOBID+_%(data_disk)s
# Note: openmedium no longer needed with vbox4.0+
#$VBOXMANAGE -q openmedium disk %(user_conf)s/HardDisks/+JOBID+_%(data_disk)s
#$VBOXMANAGE -q openmedium disk %(user_conf)s/HardDisks/%(sys_disk)s
$VBOXMANAGE -q createvm --name '%(name)s' --register
$VBOXMANAGE -q modifyvm '%(name)s' --nic1 nat --macaddress1 %(mac)s --cpus %(cpu_count)d --memory %(memory)d %(arch_opts)s --hwvirtex on --ioapic on
$VBOXMANAGE -q storagectl '%(name)s' --name 'IDE Controller' --add ide
$VBOXMANAGE -q storageattach '%(name)s' --storagectl 'IDE Controller' --port 0 --device 0 --type hdd --medium %(user_conf)s/HardDisks/'%(sys_disk)s'
$VBOXMANAGE -q storageattach '%(name)s' --storagectl 'IDE Controller' --port 1 --device 0 --type hdd --medium %(user_conf)s/HardDisks/'+JOBID+_%(data_disk)s'
$VBOXMANAGE -q sharedfolder add '%(name)s' --name 'MIG_JOBDIR' --hostpath "$MIG_JOBDIR"
$VBOXMANAGE -q guestproperty set '%(name)s' job_id +JOBID+
$VBOXMANAGE -q guestproperty set '%(name)s' proxy_host %(proxy_host)s
$VBOXMANAGE -q guestproperty set '%(name)s' proxy_port %(proxy_port)d
./%(run_script)s '%(name)s' %(effective_time)d %(screen_xres)d %(screen_yres)d %(screen_bpp)d
$VBOXMANAGE -q sharedfolder remove '%(name)s' --name 'MIG_JOBDIR'
$VBOXMANAGE -q storageattach '%(name)s' --storagectl 'IDE Controller' --port 0 --device 0 --type hdd --medium none
$VBOXMANAGE -q storageattach '%(name)s' --storagectl 'IDE Controller' --port 1 --device 0 --type hdd --medium none
$VBOXMANAGE -q storagectl '%(name)s' --name 'IDE Controller' --remove
# Note: closemedium no longer needed with vbox4.0+
#$VBOXMANAGE -q closemedium disk %(sys_disk)s
#$VBOXMANAGE -q closemedium disk +JOBID+_%(data_disk)s
$VBOXMANAGE -q unregistervm '%(name)s' --delete
mv %(user_conf)s/HardDisks/+JOBID+_%(data_disk)s %(data_disk)s

::INPUTFILES::
%(vm_base)s/%(name)s/%(data_disk)s %(data_disk)s
"""
    if not specs['sys_base']:
        job += """%(vm_base)s/%(name)s/%(sys_disk)s %(sys_disk)s
"""
    job += """
::OUTPUTFILES::
%(data_disk)s %(vm_base)s/%(name)s/%(data_disk)s

::EXECUTABLES::
%(vm_base)s/%(run_script)s %(run_script)s

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
