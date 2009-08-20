#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ps3live - [insert a few words of module description on this line]
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

# Martin Rehr 27/03/2007

import cgi
import cgitb
cgitb.enable()
import os
import tempfile

from shared.cgishared import init_cgiscript_possibly_with_cert, \
    cgiscript_header
from shared.fileio import make_symlink
from shared.resource import create_resource
from shared.sandbox import get_resource_name
from shared.resadm import get_frontend_script, get_master_node_script
from shared.resadm import fill_frontend_script, \
    fill_master_node_script, get_resource_exe
from shared.vgrid import default_vgrid
import shared.confparser as confparser


def create_ps3_resource(sandboxkey):
    resource_name = 'ps3live'
    mig_user = 'mig'
    hosturl = 'ps3live'
    resource_home = '/opt/mig/data/MiG/mig_frontend/'
    script_language = 'sh'
    ssh_port = -1
    memory = 128

    # disk = 0.064

    disk = 0
    cpucount = 1
    sandbox = True
    arch = 'PS3'
    nodecount = 1
    hostkey = 'N/A'
    frontend_node = 'localhost'

    frontend_log = '/dev/null'
    if debug:
        frontend_log = '/opt/mig/data/MiG/mig_frontend/frontendlog'

    exe_name = 'localhost'
    exe_nodecount = 1
    exe_cputime = 100000
    exe_execution_precondition = '""'
    exe_prepend_execute = '""'

    exe_exehostlog = '/dev/null'
    if debug:
        exe_exehostlog = '/opt/mig/data/MiG/mig_exe/exechostlog'

    exe_joblog = '/dev/null'
    if debug:
        exe_joblog = '/opt/mig/data/MiG/mig_exe/joblog'

    exe_execution_user = 'mig'
    exe_execution_node = 'localhost'
    exe_execution_dir = '/opt/mig/data/MiG/mig_exe/'
    exe_start_command = \
        'cd /opt/mig/data/MiG/mig_exe/; chmod 700 master_node_script_ps3.sh; ./master_node_script_ps3.sh'
    exe_status_command = 'N/A'
    exe_stop_command = 'kill -9 -$mig_exe_pgid'
    exe_clean_command = 'N/A'
    exe_continuous = False
    exe_shared_fs = True
    exe_vgrid = default_vgrid

    result = create_resource(resource_name, sandboxkey,
                             configuration.resource_home, logger)

    if not result[0]:
        o.out(result[1])
        cgiscript_header()
        o.reply_and_exit(o.ERROR)

    resource_identifier = result[2]
    unique_resource_name = resource_name + '.'\
         + str(resource_identifier)

    # create a resource configuration string that we can write to a file

    res_conf_string = \
        """ \
::MIGUSER::
%s

::HOSTURL::
%s

::HOSTIDENTIFIER::
%s

::RESOURCEHOME::
%s

::SCRIPTLANGUAGE::
%s

::SSHPORT::
%s

::MEMORY::
%s

::DISK::
%s

::CPUCOUNT::
%s

::SANDBOX::
%s

::SANDBOXKEY::
%s    
    
::ARCHITECTURE::
%s

::NODECOUNT::
%s

::RUNTIMEENVIRONMENT::

::HOSTKEY::
%s

::FRONTENDNODE::
%s

::FRONTENDLOG::
%s

::EXECONFIG::
name=%s
nodecount=%s
cputime=%s
execution_precondition=%s
prepend_execute=%s
exehostlog=%s
joblog=%s
execution_user=%s
execution_node=%s
execution_dir=%s
start_command=%s
status_command=%s
stop_command=%s
clean_command=%s
continuous=%s
shared_fs=%s
vgrid=%s"""\
         % (
        mig_user,
        hosturl,
        result[2],
        resource_home,
        script_language,
        str(ssh_port),
        str(memory),
        str(disk),
        str(cpucount),
        str(sandbox),
        sandboxkey,
        arch,
        str(nodecount),
        hostkey,
        frontend_node,
        frontend_log,
        exe_name,
        str(exe_nodecount),
        str(exe_cputime),
        exe_execution_precondition,
        exe_prepend_execute,
        exe_exehostlog,
        exe_joblog,
        exe_execution_user,
        exe_execution_node,
        exe_execution_dir,
        exe_start_command,
        exe_status_command,
        exe_stop_command,
        exe_clean_command,
        str(exe_continuous),
        str(exe_shared_fs),
        exe_vgrid,
        )

    # write the conf string to a conf file

    conf_file_src = configuration.resource_home + unique_resource_name\
         + os.sep + 'config.MiG'
    try:
        fd = open(conf_file_src, 'w')
        fd.write(res_conf_string)
        fd.close()
    except Exception, e:
        o.out(e)
        o.reply_and_exit(o.ERROR)

    # parse and pickle the conf file

    (status, msg) = confparser.run(conf_file_src, resource_name + '.'
                                    + str(resource_identifier))
    if not status:
        o.out(msg, conf_file_src)
        o.reply_and_exit(o.ERROR)

    # Create PGID file in resource_home, this is needed for timeout/kill of jobs

    exe_pgid_file = configuration.resource_home + unique_resource_name\
         + os.sep + 'EXE_%s.PGID' % exe_name
    try:
        fd = open(exe_pgid_file, 'w')
        fd.write('stopped')
        fd.close()
    except Exception, e:
        o.out(e)
        o.reply_and_exit(o.ERROR)

    return resource_name + '.' + str(resource_identifier)


def get_ps3_resource():
    log_msg = 'ps3live'

    # Identify sandboxkey

    sandboxkey = fieldstorage.getfirst('sandboxkey', None)
    if not sandboxkey:

        # No sandboxkey provided,

        log_msg = log_msg + ', Remote IP: %s, provided no sandboxkey.'\
             % os.getenv('REMOTE_ADDR')

        return (False, log_msg)

    if not os.path.exists(configuration.sandbox_home + sandboxkey):

        # Create resource

        unique_resource_name = create_ps3_resource(sandboxkey)
        log_msg = log_msg + ' Created resource: %s'\
             % unique_resource_name

        # Make symbolic link from
    # sandbox_home/sandboxkey to resource_home/resource_name

        sandbox_link = configuration.sandbox_home + sandboxkey
        resource_path = os.path.abspath(configuration.resource_home
                 + unique_resource_name)

        make_symlink(resource_path, sandbox_link, logger)
    else:
        (status, unique_resource_name) = get_resource_name(sandboxkey,
                logger)
        if not status:
            return (False, unique_resource_name)

    # If resource has a jobrequest pending, remove it.

    job_pending_file = configuration.resource_home\
         + unique_resource_name + os.sep + 'jobrequest_pending.ps3'

    if os.path.exists(job_pending_file):
        os.remove(job_pending_file)

    log_msg = log_msg + ', Remote IP: %s, Key: %s'\
         % (os.getenv('REMOTE_ADDR'), sandboxkey)

    o.internal('''
%s
''' % log_msg)

    return (True, unique_resource_name)


# ## Main ###
# Get Quirystring object

fieldstorage = cgi.FieldStorage()
(logger, configuration, client_id, o) = \
    init_cgiscript_possibly_with_cert()

# Check we are using GET method

if os.getenv('REQUEST_METHOD') != 'GET':

    # Request method is not GET

    cgiscript_header()
    o.out('You must use HTTP GET!')
    o.reply_and_exit(o.ERROR)

# Make sure that we're called with HTTPS.

if str(os.getenv('HTTPS')) != 'on':
    o.out('Please use HTTPS with session id for authenticating job requests!'
          )
    cgiscript_header()
    o.reply_and_exit(o.ERROR)

action = fieldstorage.getfirst('action', None)
debug = fieldstorage.getfirst('debug', None)
if action == 'get_frontend_script':
    (status, msg) = get_ps3_resource()
    if status:
        (status, msg) = get_frontend_script(msg, logger)
elif action == 'get_master_node_script':
    (status, msg) = get_ps3_resource()
    if status:
        (status, msg) = get_master_node_script(msg, 'localhost', logger)
elif action == 'get_resourcename':
    (status, msg) = get_ps3_resource()
else:
    status = False
    msg = 'Unknown action: %s' % action

# Get a resource for the connection client.

o.out(msg)
if status:
    o.reply_and_exit(o.OK)
else:
    o.reply_and_exit(o.ERROR)
