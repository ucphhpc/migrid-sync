#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandbox - shared sandbox helpers
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

"""Sandbox functions"""

import os
import pickle
from binascii import hexlify

# MiG imports

from conf import get_configuration_object
from shared.fileio import make_symlink
from shared.resource import create_resource
import shared.confparser as confparser

sandbox_db_name = 'sandbox_users.pkl'


def load_sandbox_db(configuration=None):
    """Read in the sandbox DB dictionary:
    Format is {username: (password, [list_of_resources])}
    """

    if not configuration:
        configuration = get_configuration_object()
    sandbox_db_path = os.path.join(configuration.sandbox_home,
                                   sandbox_db_name)
    db_fd = open(sandbox_db_path, 'rb')
    sandbox_db = pickle.load(db_fd)
    db_fd.close()
    return sandbox_db


def save_sandbox_db(sandbox_db, configuration=None):
    """Read in the sandbox DB dictionary:
    Format is {username: (password, [list_of_resources])}
    """

    if not configuration:
        configuration = get_configuration_object()
    sandbox_db_path = os.path.join(configuration.sandbox_home,
                                   sandbox_db_name)
    db_fd = open(sandbox_db_path, 'wb')
    pickle.dump(sandbox_db, db_fd)
    db_fd.close()


def get_resource_name(sandboxkey, logger):
    configuration = get_configuration_object()

    # Retrieve resource_name from sandboxkey symbolic link

    sandbox_link = configuration.sandbox_home + sandboxkey

    if os.path.exists(sandbox_link):
        unique_resource_name = \
            os.path.basename(os.path.realpath(sandbox_link))
        return (True, unique_resource_name)
    else:
        msg = 'Remote IP: %s, No sandbox with sandboxkey: %s'\
             % (os.getenv('REMOTE_ADDR'), sandboxkey)
        logger.error(msg)
        return (False, msg)


def create_oneclick_resource(
    sandboxkey,
    cputime,
    configuration,
    logger,
    ):

    resource_name = 'oneclick'

    result = create_resource(resource_name, sandboxkey,
                             configuration.resource_home, logger)

    if not result[0]:
        return (False, result[1])

    resource_identifier = result[2]
    unique_resource_name = resource_name + '.'\
         + str(resource_identifier)

    # create a resource configuration string that we can write to a file

    exe_name = 'jvm'
    res_conf_string = \
        """\
::MIGUSER::
N/A

::HOSTURL::
oneclick

::HOSTIDENTIFIER::
%s

::RESOURCEHOME::
N/A

::SCRIPTLANGUAGE::
java

::SSHPORT::
-1

::MEMORY::
128

::DISK::
10

::CPUCOUNT::
1

::SANDBOX::
1

::SANDBOXKEY::
%s    
    
::ARCHITECTURE::
X86

::PLATFORM::
ONE-CLICK

::NODECOUNT::
1

::HOSTKEY::
N/A

::FRONTENDNODE::
N/A

::FRONTENDLOG::
N/A

::EXECONFIG::
name=%s
nodecount=1
cputime=%s
execution_precondition=N/A
prepend_execute=N/A
exehostlog=N/A
joblog=N/A
execution_user=N/A
execution_node=N/A
execution_dir=N/A
start_command=N/A
status_command=N/A
stop_command=N/A
clean_command=N/A
continuous=False
shared_fs=False
vgrid=Generic
    """\
         % (result[2], sandboxkey, exe_name, cputime)

    # write the conf string to a conf file

    conf_file_src = configuration.resource_home + unique_resource_name\
         + os.sep + 'config.MiG'
    try:
        fd = open(conf_file_src, 'w')
        fd.write(res_conf_string)
        fd.close()
    except Exception, exc:
        return (False, str(exc))

    # parse and pickle the conf file

    (status, msg) = confparser.run(conf_file_src, resource_name + '.'
                                    + str(resource_identifier))

    if not status:
        return (False, '%s (%s)' % (msg, conf_file_src))

    # Create PGID file in resource_home

    exe_pgid_file = configuration.resource_home + unique_resource_name\
         + os.sep + 'EXE_%s.PGID' % exe_name
    try:
        fd = open(exe_pgid_file, 'w')
        fd.write('stopped')
        fd.close()
    except Exception, exc:
        return (False, str(exc))

    return (True, resource_name + '.' + str(resource_identifier))


def get_resource(client_id, configuration, logger):
    cookie = None
    sandboxkey = None
    cputime = 1000000
    log_msg = 'oneclick:'

    __MIG_ONECLICK_COOKIE__ = 'MiGOneClickSandboxKey'

    # If user with identifing cookie use cookie infomation

    if os.getenv('HTTP_COOKIE') and os.getenv('HTTP_COOKIE'
            ).count(__MIG_ONECLICK_COOKIE__) > 0:
        cookie_arr = os.getenv('HTTP_COOKIE').split(';')
        for elm in cookie_arr:
            if elm.count(__MIG_ONECLICK_COOKIE__) > 0:
                sandboxkey = elm.split('=')[1]
                break

    # If we don't know user, generate an identification key
    # and a new resource for him.
    # The key is send to him as a cookie

    if not sandboxkey or not os.path.exists(configuration.sandbox_home
             + sandboxkey):

        # Generate key, and set cookie

        sandboxkey = hexlify(open('/dev/urandom').read(32))
        cookie = 'Set-Cookie: ' + __MIG_ONECLICK_COOKIE__ + '='\
             + sandboxkey + '; '\
             + 'expires=Thu 31-Jan-2099 12:00:00 GMT; path=/; '\
             + 'domain=' + configuration.server_fqdn + '; secure'

        # Create resource

        (status, msg) = create_oneclick_resource(sandboxkey, cputime,
                configuration, logger)
        if not status:
            return (status, msg)
        resource_name = msg
        log_msg += ' Created resource: %s' % resource_name

        # Make symbolic link from
        # sandbox_home/sandboxkey to resource_home/resource_name

        sandbox_link = configuration.sandbox_home + sandboxkey
        resource_path = os.path.abspath(configuration.resource_home
                 + resource_name)

        make_symlink(resource_path, sandbox_link, logger)
    else:

        # Retrieve resource_name from sandboxkey symbolic link

        sandbox_link = configuration.sandbox_home + sandboxkey
        resource_name = os.path.basename(os.path.realpath(sandbox_link))

    # If resource has a jobrequest pending, remove it.

    job_pending_file = configuration.resource_home + resource_name\
         + os.sep + 'jobrequest_pending.jvm'
    if os.path.exists(job_pending_file):
        os.remove(job_pending_file)

    log_msg += ', Remote IP: %s, Key: %s' % (os.getenv('REMOTE_ADDR'),
            sandboxkey)

    # Make symbolic link from webserver_home to javabin_home

    codebase_link = configuration.webserver_home + sandboxkey\
         + '.oneclick'
    codebase_path = os.path.abspath(configuration.javabin_home)

    # Remove symbolic link if it allready exists.
    # This must be done in a try/catch as the symlink,
    # may be a dead link and 'if os.path.exists(linkloc):'
    # will then return false, even though the link exists.

    try:
        os.remove(codebase_link)
    except:
        pass

    make_symlink(codebase_path, codebase_link, logger)

    logger.info(log_msg)

    return (True, (sandboxkey, resource_name, cookie, cputime))


