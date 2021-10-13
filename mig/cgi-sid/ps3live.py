#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ps3live - PS3 live resource handler
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
import os
import tempfile
# Only enable for debug
#import cgitb
# cgitb.enable()

from mig.shared import confparser
from mig.shared.cgishared import init_cgiscript_possibly_with_cert, \
    cgiscript_header
from mig.shared.defaults import default_vgrid
from mig.shared.fileio import make_symlink
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.resadm import fill_frontend_script, fill_master_node_script, \
    get_resource_exe, get_frontend_script, get_master_node_script
from mig.shared.resource import create_resource_home
from mig.shared.sandbox import get_resource_name
from mig.shared.scriptinput import fieldstorage_to_dict


def signature():
    """Signature of the main function"""

    defaults = {
        'action': REJECT_UNSET,
        'debug': [''],
    }
    return ['', defaults]


def create_ps3_resource(configuration, sandboxkey):
    resource_name = 'ps3live'
    mig_user = 'mig'
    hosturl = 'ps3live'
    resource_home = '/opt/mig/data/MiG/mig_frontend/'
    script_language = 'sh'
    ssh_port = 22
    memory = 128

    # disk = 0.064

    disk = 0
    cpucount = 1
    sandbox = True
    arch = 'PS3'
    nodecount = 1
    hostkey = ''
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
    exe_status_command = 'NA'
    exe_stop_command = 'kill -9 -$mig_exe_pgid'
    exe_clean_command = 'NA'
    exe_continuous = False
    exe_shared_fs = True
    exe_vgrid = default_vgrid

    result = create_resource_home(configuration, sandboxkey, resource_name)

    if not result[0]:
        o.out(result[1])
        cgiscript_header()
        o.reply_and_exit(o.ERROR)

    resource_identifier = result[1]
    unique_resource_name = "%s.%d" % (resource_name, resource_identifier)

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
        resource_identifier,
        resource_home,
        script_language,
        ssh_port,
        memory,
        disk,
        cpucount,
        sandbox,
        sandboxkey,
        arch,
        nodecount,
        hostkey,
        frontend_node,
        frontend_log,
        exe_name,
        exe_nodecount,
        exe_cputime,
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
        exe_continuous,
        exe_shared_fs,
        exe_vgrid,
    )

    # write the conf string to a conf file

    conf_file_src = os.path.join(configuration.resource_home,
                                 unique_resource_name, 'config.MiG')
    try:
        fd = open(conf_file_src, 'w')
        fd.write(res_conf_string)
        fd.close()
    except Exception as e:
        o.out(e)
        o.reply_and_exit(o.ERROR)

    # parse and pickle the conf file

    (status, msg) = confparser.run(configuration, conf_file_src, "%s.%d" %
                                   (resource_name, resource_identifier))

    if not status:
        o.out(msg, conf_file_src)
        o.reply_and_exit(o.ERROR)

    # Create PGID file in resource_home, this is needed for timeout/kill of jobs

    exe_pgid_file = os.path.join(configuration.resource_home,
                                 unique_resource_name,
                                 'EXE_%s.PGID' % exe_name)
    try:
        fd = open(exe_pgid_file, 'w')
        fd.write('stopped')
        fd.close()
    except Exception as e:
        o.out(e)
        o.reply_and_exit(o.ERROR)

    return "%s.%d" % (resource_name, resource_identifier)


def get_ps3_resource(configuration):
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

        unique_resource_name = create_ps3_resource(configuration, sandboxkey)
        log_msg = log_msg + ' Created resource: %s'\
            % unique_resource_name

        # Make symbolic link from
    # sandbox_home/sandboxkey to resource_home/resource_name

        sandbox_link = configuration.sandbox_home + sandboxkey
        resource_path = os.path.abspath(os.path.join(configuration.resource_home,
                                                     unique_resource_name))

        make_symlink(resource_path, sandbox_link, logger)
    else:
        (status, unique_resource_name) = get_resource_name(sandboxkey,
                                                           logger)
        if not status:
            return (False, unique_resource_name)

    # If resource has a jobrequest pending, remove it.

    job_pending_file = os.path.join(configuration.resource_home,
                                    unique_resource_name,
                                    'jobrequest_pending.ps3')

    if os.path.exists(job_pending_file):
        os.remove(job_pending_file)

    log_msg = log_msg + ', Remote IP: %s, Key: %s'\
        % (os.getenv('REMOTE_ADDR'), sandboxkey)

    o.internal('''
%s
''' % log_msg)

    return (True, unique_resource_name)

# TODO: port to new functionality backend structure with standard validation

# ## Main ###


(logger, configuration, client_id, o) = \
    init_cgiscript_possibly_with_cert()

if configuration.site_enable_gdp or not configuration.site_enable_sandboxes \
        or not configuration.site_enable_jobs:
    o.out('Not available on this site!')
    o.reply_and_exit(o.CLIENT_ERROR)

# Check we are using GET method

if os.getenv('REQUEST_METHOD') != 'GET':

    # Request method is not GET

    cgiscript_header()
    o.out('You must use HTTP GET!')
    o.reply_and_exit(o.ERROR)

# Make sure that we're called with HTTPS.

if "%s" % os.getenv('HTTPS') != 'on':
    o.out('Please use HTTPS with session id for authenticating job requests!'
          )
    cgiscript_header()
    o.reply_and_exit(o.ERROR)

fieldstorage = cgi.FieldStorage()
user_arguments_dict = fieldstorage_to_dict(fieldstorage)
defaults = signature()[1]
output_objects = []
# IMPORTANT: validate all input args before doing ANYTHING with them!
(validate_status, accepted) = validate_input(
    user_arguments_dict,
    defaults,
    output_objects,
    allow_rejects=False,
    # NOTE: path cannot use wildcards here
    typecheck_overrides={},
)
if not validate_status:
    logger.error("input validation for %s failed: %s" %
                 (client_id, accepted))
    o.out('Invalid input arguments received!')
    o.reply_and_exit(o.ERROR)

action = accepted['action'][-1]
debug = accepted['debug'][-1]
if action == 'get_frontend_script':
    (status, msg) = get_ps3_resource(configuration)
    if status:
        (status, msg) = get_frontend_script(msg, logger)
elif action == 'get_master_node_script':
    (status, msg) = get_ps3_resource(configuration)
    if status:
        (status, msg) = get_master_node_script(msg, 'localhost', logger)
elif action == 'get_resourcename':
    (status, msg) = get_ps3_resource(configuration)
else:
    status = False
    msg = 'Unknown action: %s' % action

# Get a resource for the connection client.

o.out(msg)
if status:
    o.reply_and_exit(o.OK)
else:
    o.reply_and_exit(o.ERROR)
