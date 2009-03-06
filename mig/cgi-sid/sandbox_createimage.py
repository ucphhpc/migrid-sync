#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandbox_createimage - [insert a few words of module description on this line]
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

'''This script generates a sandbox image '''
import os
import cgi
import cgitb
cgitb.enable()
import tempfile
import shutil
from binascii import hexlify
import pickle
import fcntl
import time

import shared.confparser as confparser
import shared.resadm as resadm
from shared.cgishared import init_cgiscript_possibly_with_cert
from shared.resource import create_resource, remove_resource
from shared.conf import get_resource_configuration, get_resource_exe
from shared.fileio import make_symlink

#print "Content-Type: txt/html"
#print

# optional certificate
(logger, configuration, cert_name_no_spaces, o) = \
         init_cgiscript_possibly_with_cert(False, "application/zip")
sandboxdb_file = configuration.sandbox_home + os.sep + "sandbox_users.pkl"
#sandboxdb_file = "sandbox_users.pkl"
# Load the user file
fd = open(sandboxdb_file, 'rb')
userdb = pickle.load(fd)
fd.close()

# initiate form and read hd size and memory values
form = cgi.FieldStorage()
username = form.getfirst("username", "").strip()
# password = form.getfirst("password","").strip()
hd_size = form.getfirst("hd_size", "").strip()
net_bw = form.getfirst("net_bw", "").strip()
memory = form.getfirst("memory", "").strip()
operating_system = form.getfirst("operating_system", "").strip()
win_solution = form.getfirst("win_solution", "").strip()
ip_address = "UNKNOWN"
if os.environ.has_key("REMOTE_ADDR"):
    ip_address = os.environ["REMOTE_ADDR"]

# check that hd size and memory are integers
try: 
    _ = int(hd_size) + int(memory) + int(net_bw)
except Exception, err:
    o.client(err)
    o.reply_and_exit(o.CLIENT_ERROR)

# provide a resource name
resource_name = "sandbox"

o.internal('Generating MiG linux sandbox dist with hd size ' + \
            hd_size + ' and mem ' + memory + ' for user ' + \
            username + ' from ' + ip_address + ' running OS ' + \
           operating_system + '....')
# Send a request for creating the resource
(status, msg, resource_identifier) = create_resource(
    resource_name, "SANDBOX_" + username, configuration.resource_home,
    logger)
o.out(msg)

if status:
    o.client("\n - you might need to do a SSH to the resource before" \
             "starting the resource to get it in known_hosts!" \
             "\n (this is because SSH hostkey checking is disabled)")     
else:
    (status2, msg) = remove_resource(configuration.resource_home,
                                     resource_name,
                                     resource_identifier)
    o.out(msg)
    o.reply_and_exit(o.CLIENT_ERROR)

unique_host_name = resource_name + '.' + str(resource_identifier)
# add the resource to the list of the users resources

userdb[username][1].append(unique_host_name)
fd = open(sandboxdb_file, 'wb')
pickle.dump(userdb, fd)
fd.close()

sandboxkey = hexlify(open("/dev/urandom").read(32))
# create sandboxlink
sandbox_link = configuration.sandbox_home + sandboxkey
resource_path = os.path.abspath(configuration.resource_home + unique_host_name)
make_symlink(resource_path, sandbox_link, logger)

# change dir to sss_home  
old_path = os.getcwd()
os.chdir(configuration.sss_home)
# log_dir = "log/"

# create a resource configuration string that we can write to a file
res_conf_string = """::MIGUSER::
mig

::HOSTURL::
%s

::HOSTIDENTIFIER::
%s

::RESOURCEHOME::
/opt/mig/MiG/mig_frontend/

::SCRIPTLANGUAGE::
sh

::SSHPORT::
22

::MEMORY::
%s

::DISK::
%s

::MAXDOWNLOADBANDWIDTH::
%s

::MAXUPLOADBANDWIDTH::
%s

::CPUCOUNT::
1

::SANDBOX::
1

::SANDBOXKEY::
%s

::ARCHITECTURE::
X86

::NODECOUNT::
1

::RUNTIMEENVIRONMENT::
name: LIBPYTHON2.4

::HOSTKEY::
N/A

::FRONTENDNODE::
localhost

::FRONTENDLOG::
/opt/mig/MiG/mig_frontend/frontendlog

::EXECONFIG::
name=localhost
nodecount=1
cputime=1000000
execution_precondition=''
prepend_execute=""
exehostlog=/opt/mig/MiG/mig_exe/exechostlog
joblog=/opt/mig/MiG/mig_exe/joblog
execution_user=mig
execution_node=localhost
execution_dir=/opt/mig/MiG/mig_exe/
start_command=cd /opt/mig/MiG/mig_exe/; chmod 700 master_node_script_%s.sh; ./master_node_script_%s.sh
status_command=exit \\\\\`ps -o pid= -g $mig_exe_pgid | wc -l \\\\\`
stop_command=kill -9 -$mig_exe_pgid
clean_command=true
continuous=False
shared_fs=True
vgrid=Generic

""" % (resource_name, resource_identifier, memory, int(hd_size)/1000,
       net_bw, str(int(net_bw)/2), sandboxkey, unique_host_name, unique_host_name) 

# write the conf string to a conf file 
conf_file_src = configuration.resource_home+unique_host_name + \
                os.sep + "config.MiG"
try:
    fd = open(conf_file_src, "w")
    fd.write(res_conf_string)
    fd.close()
except Exception, err:
    o.client(err)
    o.reply_and_exit(o.CLIENT_ERROR)
    
# parse and pickle the conf file
(status, msg) = confparser.run(conf_file_src, resource_name + "." + \
                               str(resource_identifier))
if not status:
    o.out(msg, conf_file_src)
    o.reply_and_exit(o.ERROR)

# read pickled resource conf file (needed to create
# master_node_script.sh)
msg = ""
(status, resource_config) = get_resource_configuration(
    configuration.resource_home, unique_host_name, logger)
if not resource_config:
    msg += "No resouce_config for: '" +  unique_host_name + "'\n"
    o.out(msg)
    o.reply_and_exit(o.ERROR)
    
# read pickled exe conf file (needed to create master_node_script.sh)
(status, exe) = get_resource_exe(resource_config, "localhost", logger)
if not exe:
    msg = "No EXE config for: '" + unique_host_name + \
          "' EXE: localhost'"  
    o.out(msg)
    o.reply_and_exit(o.ERROR)
    
# HACK: a PGID file is required in the resource home directory
# write the conf string to a conf file 
pgid_file = configuration.resource_home+unique_host_name + \
                os.sep + "EXE_Uid.PGID"
try:
    fd = open(pgid_file, "w")
    fd.write("")
    fd.close()
except Exception, err:
    o.client(err)
    o.reply_and_exit(o.CLIENT_ERROR)

#and another pgid file... dont know which one is being used...
pgid_file = configuration.resource_home+unique_host_name + \
                os.sep + "EXE_localhost.PGID"
try:
    fd = open(pgid_file, "w")
    fd.write("")
    fd.close()
except Exception, err:
    o.client(err)
    o.reply_and_exit(o.CLIENT_ERROR)


os.chdir(old_path)

# create master_node_script
try:
    # Securely open a temporary file in resource_dir
    resource_dir = configuration.resource_home + os.sep + \
                   unique_host_name
    master_node_script_file, mns_fname = tempfile.mkstemp(
        dir=resource_dir, text=True)
    (rv, msg) = resadm.fill_master_node_script(
        master_node_script_file, resource_config, exe, 1000)
    if not rv:
        o.out(msg)
        o.reply_and_exit(o.ERROR)
    os.close(master_node_script_file)
    logger.debug("wrote master node script %s", mns_fname)
except Exception, err:
    o.out("could not write master node script file (%s)" % err)
    o.reply_and_exit(o.ERROR)

# create front_end_script
try:
    resource_dir = configuration.resource_home + os.sep + \
                   unique_host_name
    fe_script_file, fes_fname = tempfile.mkstemp(dir=resource_dir,
                                                 text=True)
    (rv, msg) = resadm.fill_frontend_script(
        fe_script_file, configuration.migserver_https_url,
        unique_host_name, resource_config)
    
    if not rv:
        o.out(msg)
        o.reply_and_exit(o.ERROR)
    
    os.close(fe_script_file)
    logger.debug("wrote frontend script %s", fes_fname)
except Exception, err:
    o.out("I could could not write frontend script file (%s)" % err)
    o.reply_and_exit(o.ERROR)

# change directory to sss_home and mount hd image in order to copy
# the FE-script and masternode script to the hd
os.chdir(configuration.sss_home)

FILE = "lockfile.txt"
if not os.path.isfile(FILE):
    if not os.path.exists(FILE):
        try:
            touch_lockfile = open(FILE, "w")
            touch_lockfile.write("this is the lockfile")
            touch_lockfile.close()
        except Exception, exc:
            o.out("coult not create lockfile!")
            o.reply_and_exit(o.CLIENT_ERROR)
    else:
        o.out("%s exists but is not a file!" % FILE)
        o.reply_and_exit(o.CLIENT_ERROR)
        
### Enter critical region ###
lockfile = open(FILE, "r+")
fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)

#unmount leftover disk image mounts if any
os.system("sync")
os.system('umount mnt')
os.system("sync")

# use a disk of the requested size
command = "cp MiG-SSS" + os.sep + "hda_" + hd_size + \
          ".img MiG-SSS" + os.sep + "hda.img"
os.system(command)

# mount hda and copy scripts to it
os.system('mount mnt')
#time.sleep(120)

try:
    # save master_node_script to hd image
    shutil.copyfile(
      mns_fname, "mnt/mig/MiG/mig_exe/master_node_script_localhost.sh")  

    # save frontend_script to hd image
    shutil.copyfile(fes_fname,
      "mnt/mig/MiG/mig_frontend/frontend_script.sh")  
except Exception, err:
    o.client(err)
    #unmount disk image
    os.system("sync")
    os.system('umount mnt')
    os.system("sync")
    o.reply_and_exit(o.CLIENT_ERROR)
                           
# copy the sandboxkey to the keyfile:
try:
    fd = open("keyfile", "w")
    fd.write(sandboxkey)
    fd.close()
except Exception, err:
    o.client(err)
    #unmount disk image
    os.system("sync")
    os.system('umount mnt')
    os.system("sync")
    o.reply_and_exit(o.CLIENT_ERROR)

try:
    shutil.copyfile("keyfile", "mnt/mig/etc/keyfile")  
except Exception, err:
    o.client(err)
    #unmount disk image
    os.system("sync")
    os.system('umount mnt')
    os.system("sync")
    o.reply_and_exit(o.CLIENT_ERROR)
                            
#unmount disk image
os.system("sync")
os.system('umount mnt')
os.system("sync")

# Convert the hda to vmdk - no longer needed! (04.2008)
#os.system('/usr/local/bin/qemu-img ' \
#          'convert MiG-SSS/hda.img -O vmdk MiG-SSS/hda.vmdk')

# Copy one of the vmx files according to the specified memory requirement: - no longer needed! (04.2008)
#command = "cp MiG-SSS" + os.sep + "MiG_" + memory + ".vmx MiG-SSS" + \
#          os.sep + "MiG.vmx"
#os.system(command)

dlfilename = 'MiG-SSS_' + str(resource_identifier) + '.zip'
if operating_system == "linux":
    # Put all linux-related files in a zip archive
    os.system('/usr/bin/zip '+ dlfilename + ' MiG-SSS/MiG.iso ' \
              'MiG-SSS/hda.img ' \
              'MiG-SSS/mig_xsss.py MiG-SSS/readme.txt')     

else:
    if win_solution == "screensaver":
        # Put all win-related files in the archive (do not store dir
        # name: -j)
        os.system('/usr/bin/zip -j ' + dlfilename + ' MiG-SSS/MiG-SSS_Setup.exe ' \
              'MiG-SSS/hda.img MiG-SSS/MiG.iso')
    else: #windows service
        os.system('/usr/bin/zip -j ' + dlfilename + ' MiG-SSS/MiG-SSS-Service_Setup.exe ' \
              'MiG-SSS/hda.img MiG-SSS/MiG.iso')
        

### Leave critical region ###
lockfile.close() # unlocks lockfile

file_size = os.stat(dlfilename).st_size
# print header:
print "Content-Type: application/zip"
print "Content-Type: application/force-download"
print "Content-Type: application/octet-stream"
print "Content-Type: application/download"
print "Content-Disposition: attachment; filename="+dlfilename+""
print "Content-Length: %s" % file_size
print #blank line, end of header

fd = open(dlfilename, 'r')
print fd.read()
fd.close()
os.system('rm -f ' + dlfilename)
