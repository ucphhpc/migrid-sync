#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vms - A "library" of functions for doing various stuff specific for the use
#       virtual machines, creation of mRsl for start, grabbing status, listing machines etc.
#
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

import os, ConfigParser, re, md5, shutil
from glob import glob
from shared.fileio import unpickle
from shared.init import initialize_main_variables
from shared.job import new_job
from string import Template

(configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)

"""
1: Job identifier = 64_5_30_2009__10_10_15_localhost.0

2: Md5 sum (16bytes) 32 char hex. string = 01b19818762fbaf81693001639b1379c

3: Lower to (8bytes) 16 char hex. string: 01 b1 98 18 76 2f ba f8

4: Convert to user inputable ascii table characters:

	Ascii table offset by 64 + [0-16]
  
  This methods provides 127^8 identifiers.
"""
def vnc_jobid(job_id='Unknown'):
  
  job_id_digest = md5.new(job_id).hexdigest()[:16]  # 2
  password = ''
  for i in range(0, len(job_id_digest), 2):         # 3, 4
    
    char = 32 + int(job_id_digest[i:i+2], 16)
    if char > 251:
      password += chr(char/3)
    elif char > 126:
      password += chr(char/2)
    else:
      password += chr(char)
  
  return password

"""

 vmslist,
 
 Returns a list of dicts describing users available virtual machines
 described by following keys:
 
 'name', 'ram', 'state'
 
 NOTE:

      The current state management does not fully exploit the powers of the
      grid, it only allows one "instance" of the virtual machine to be
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
def vms_list(cert_name_no_spaces):
        
    # Grab the base directory of the user
    user_home = os.path.abspath(configuration.user_home + os.sep
                                + cert_name_no_spaces) + os.sep
    mrsl_files_dir = os.path.abspath(configuration.mrsl_files_dir + os.sep
                                + cert_name_no_spaces) + os.sep
    
    # Append the virtual machine directory
    vms_paths = glob(user_home + 'vms' + os.sep + '*/*.cfg')

    # List of virtual machines
    vms = []
    
    for vm_def_path in vms_paths:
        
        vm = {'name'    : 'UNKNOWN',
              'path'    : os.path.abspath(vm_def_path),
              'status'  : 'UNKNOWN',
              'execution_time' : 'UNKNOWN',
              'job_id'  : 'UNKNOWN',
              'memory'  : 'UNKNOWN',
              'cpu_count':'UNKNOWN',
              'arch'     :'UNKNOWN',
              'uuid'    : 'UNKNOWN'}
          
        # Grab the configuration file defining the vm
        vm_def_base = os.path.basename(os.path.dirname(vm_def_path))
        
        vm_config = ConfigParser.ConfigParser()
        vm_config.read([vm_def_path])

        vm['name']      = vm_def_base
        vm['memory']    = vm_config.get('DEFAULT', 'mem')
        vm['cpu_count'] = vm_config.get('DEFAULT', 'cpus')
        vm['arch'] = vm_config.get('DEFAULT', 'arch')
                  
        # All job descriptions associated with this virtual machine
        jobs = []
        match_line = 'VBoxManage createvm -name "'+vm_def_base+'" -register'
        for stuff in glob(mrsl_files_dir+'*'):
          for line in open(os.path.abspath(stuff), 'r', 1):
            
            if match_line in line:
              jobs.append(unpickle(stuff, logger))
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
          vm['status'] = jobs[len(jobs)-1]['STATUS']
          if vm['status'] == 'EXECUTING':
            vm['execution_time'] = jobs[len(jobs)-1]['EXECUTING_TIMESTAMP']
          vm['job_id'] = jobs[len(jobs)-1]['JOB_ID']
        
        vms.append(vm)
    
    return vms  

def vms_list_old(cert_name_no_spaces):
        
    # Grab the base directory of the user
    user_home = os.path.abspath(configuration.user_home + os.sep
                                + cert_name_no_spaces) + os.sep
    mrsl_files_dir = os.path.abspath(configuration.mrsl_files_dir + os.sep
                                + cert_name_no_spaces) + os.sep
    
    # Append the virtual machine directory
    # Tomas style
    vms_paths = glob(user_home +'*.xml')
    
    # New approach
    vms_paths += glob(user_home + 'vms' + os.sep + '*/*.cfg')

    regex_machine   = re.compile(r"""Machine .* name="([a-zA-Z0-9]+)_?.*" OSType="(.*)" .*""")
    regex_memory    = re.compile(r"""Memory RAMSize="([0-9]+)\"""")
    regex_cpu_count = re.compile(r"""CPU count="([0-9]+)\"""")

    vms = [] # List of virtual machines
    for vm_def_path in vms_paths:
        
        vm = {'name'    : 'UNKNOWN',
              'path'    : os.path.abspath(vm_def_path),
              'specs'   : None,
              'status'  : None,
              'job_id'  : None,
              'uuid'    : 'UNKNOWN'}
        
        specs = {'os_type': 'UNKNOWN', 'memory' : 'UNKNOWN', 'cpu_count':'UNKNOWN'}
                
        # Grab the xml file defining the vm
        vm_def_base = os.path.basename(vm_def_path) # TODO: 1
        vm['job_id'] = vm_def_base
        # Grab machine specifications, TODO: 2
        for xmlline in open(os.path.abspath(vm_def_path),'r',1):
          
          name_and_ostype = regex_machine.search(xmlline)          
          if name_and_ostype:
            vm['name']        = name_and_ostype.group(1)
            specs['os_type']  = name_and_ostype.group(2)            
          
          memory = regex_memory.search(xmlline)
          if memory:
            specs['memory'] = memory.group(1)
            
          cpu_count = regex_cpu_count.search(xmlline)
          if cpu_count:
            specs['cpu_count'] = cpu_count.group(1)
          
        vm['specs'] = specs
          
        # All job descriptions associated with this virtual machine
        jobs = []
        for stuff in glob(mrsl_files_dir+'*'):
          for line in open(os.path.abspath(stuff), 'r', 1):
            
            if vm_def_base in line:
              jobs.append(unpickle(stuff, logger))
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
        vm['status'] = jobs[len(jobs)-1]['STATUS']
        vm['job_id'] = jobs[len(jobs)-1]['JOB_ID']
        
        # Todo: grab machine details such as ram from machine definition
        
        vms.append(vm)
    
    return vms  

"""
 vnc_applet,
 
 Generates the html tag needed for loading the vnc applet.
 Takes care of fixing representation of the password.
 
 You just specifify a jobidentifier and where all happy.
 
"""
def vnc_applet(proxy_host, proxy_port, applet_port, width, height, password):
  
  applet = """<APPLET CODE="VncViewer" ARCHIVE="VncViewer.jar" """
  applet += " CODEBASE=\"http://%s:%d/tightvnc/\"" % (proxy_host, applet_port)
  applet += " WIDTH=\"%d\" HEIGHT=\"%d\">" % (width, height)
  applet += "<PARAM NAME=\"PORT\" VALUE=\"%d\">" % (proxy_port)
  applet += "<PARAM NAME=\"PASSWORD\" VALUE=\"%s\">" % (password)
#  applet += "<PARAM NAME=\"Encoding\" VALUE=\"Raw\">"
  applet += "</APPLET>"
  
  return applet

"""
 popup_snippet,
 
 Just a simple piece of js to popup a window.

"""
def popup_snippet():
    
  return """
    <script>
    function vncClientPopup() {
    var win = window.open("", "win", "menubar=no,toolbar=no");
    
    win.document.open("text/html", "replace");
    win.document.write('<HTML><HEAD><TITLE>MiG Remote Access</TITLE></HEAD><BODY>%s</BODY></HTML>');
    win.document.close();
    }
    </script>"""    
    
"""
  A convenience functions for creating links to "stop/stop/connect".
  Depending on the machine state.
"""
def machine_link(content, job_id, name, uuid, state):
  
  link = ''
  
  if state ==  'EXECUTING':
    link = '<a href="/cgi-bin/vmachines_connect.py?job_id=%s">%s</a>' % (job_id, content)
  elif state == 'QUEUED':
    link = content
  else: # Canceled, Finished, Unknown
    link = '<a href="?start=%s">%s</a>' % (name, content)

  return link

"""
  Submit a machine job based on machine definition file.
  
  TODO: defensive stuff...
  
"""
def enqueue_machine(cert_name_no_spaces, machine_uuid):
  
  filename = '/tmp/detteerentest.mrls'
  
  # Generate the mrls
  mrls = machine_job('MyVirtualMachine')
  fh = open(filename,'w',0)
  fh.write(mrls)
  fh.close()
    
  # Find the machine the given name
  return new_job(
    filename,
    cert_name_no_spaces,
    configuration,
    False,
    True,
    )

def create_vm(cert_name_no_spaces, machine_name):
  
  # Primitive sanitize of machine name
  # Only allow A-z and numbers and no longer than 30 chars
  machine_name = re.sub('[^A-Za-z0-9]*', '', machine_name)[:30]
  
  # Setup paths  
  user_vms_home = os.path.abspath(configuration.user_home + os.sep
                                + cert_name_no_spaces) + os.sep + 'vms' + os.sep
  vm_home = user_vms_home+machine_name+os.sep
  server_vms_home = os.path.abspath(configuration.server_home + os.sep + 'vms' + os.sep)
  server_vms_builder_home = os.path.abspath(configuration.server_home + os.sep + 'vms_builder' + os.sep)

  # Create users vms storage
  if not os.path.exists(user_vms_home):
    os.mkdir(user_vms_home)
    shutil.copy(server_vms_home+os.sep+'runvm.sh', user_vms_home+os.sep)
  
  # Create the vm
  if not os.path.exists(vm_home):
    os.mkdir(vm_home)
    shutil.copy(server_vms_builder_home+os.sep+'machine.cfg', vm_home+os.sep)
    shutil.copy(server_vms_builder_home+os.sep+'data.vmdk', vm_home+os.sep)
    open(vm_home+os.sep+'sys_plain.remote', 'a')

def enqueue_vm(cert_name_no_spaces, machine_name):
  filename = '/tmp/detteerentest.mrls'
  
  # Generate the mrls
  mrls = mig_deployed_job(machine_name)
  fh = open(filename,'w',0)
  fh.write(mrls)
  fh.close()
    
  # Find the machine the given name
  return new_job(
    filename,
    cert_name_no_spaces,
    configuration,
    False,
    True,
    )

"""
This method assumes that the system disk is registered on the resource.
"""
def mig_deployed_job(name='Unknown',
                     data_disk='data.vmdk',
                     sys_disk='plain.vmdk',
                     memory=1024,
                     cpu_count=1,
                     cpu_time=900):

  mrsl = Template("""::EXECUTE::                  
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
  return mrsl.substitute(NAME=name, CPU_COUNT=cpu_count, MEMORY=memory)