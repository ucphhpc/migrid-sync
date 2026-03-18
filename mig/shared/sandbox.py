#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandbox - shared sandbox helpers
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

import os
import tempfile

from mig.shared.base import hexlify
from mig.shared.conf import get_configuration_object
from mig.shared.defaults import default_vgrid, keyword_auto
from mig.shared.fileio import make_symlink, write_named_tempfile
from mig.shared.resource import create_resource
from mig.shared.serial import load, dump

sandbox_db_name = 'sandbox_users.pkl'


def load_sandbox_db(configuration=None):
    """Read in the sandbox DB dictionary:
    Format is {username: (password, [list_of_resources])}
    """

    if not configuration:
        configuration = get_configuration_object()
    sandbox_db_path = os.path.join(configuration.sandbox_home,
                                   sandbox_db_name)
    sandbox_db = load(sandbox_db_path)
    return sandbox_db


def save_sandbox_db(sandbox_db, configuration=None):
    """Read in the sandbox DB dictionary:
    Format is {username: (password, [list_of_resources])}
    """

    if not configuration:
        configuration = get_configuration_object()
    sandbox_db_path = os.path.join(configuration.sandbox_home,
                                   sandbox_db_name)
    dump(sandbox_db, sandbox_db_path)


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


def create_sss_resource(
    sandboxkey,
    cputime,
    memory,
    hd_size,
    net_bw,
    vgrid_list,
    configuration,
    logger,
):

    resource_name = 'sandbox'
    unique_host_name = "%s.%s" % (resource_name, keyword_auto)

    # create a resource configuration string that we can write to a file

    exe_name = 'localhost'
    res_conf_string = \
        """\
::MIGUSER::
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
True

::SANDBOXKEY::
%s

::ARCHITECTURE::
X86

::NODECOUNT::
1

::RUNTIMEENVIRONMENT::


::HOSTKEY::


::FRONTENDNODE::
localhost

::FRONTENDLOG::
/opt/mig/MiG/mig_frontend/frontendlog

::EXECONFIG::
name=%s
nodecount=1
cputime=%d
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
vgrid=%s

"""\
    % (
        resource_name,
        keyword_auto,
        memory,
        int(hd_size // 1000),
        net_bw,
        int(net_bw // 2),
        sandboxkey,
        exe_name,
        cputime,
        unique_host_name,
        unique_host_name,
        ', '.join(vgrid_list),
    )

    # write the conf string to a temporary conf file
    # create_resource removes the tempfile automatically

    pending_file = write_named_tempfile(configuration, res_conf_string)

    (status, id_msg) = create_resource(configuration, sandboxkey,
                                       resource_name, pending_file)
    if not status:
        return (False, '%s (%s)' % (id_msg, pending_file))

    # Create PGID file in resource_home

    resource_identifier = id_msg
    unique_resource_name = "%s.%d" % (resource_name, resource_identifier)

    exe_pgid_file = configuration.resource_home + unique_resource_name\
        + os.sep + 'EXE_%s.PGID' % exe_name
    try:
        fd = open(exe_pgid_file, 'w')
        fd.write('stopped')
        fd.close()
    except Exception as exc:
        return (False, "%s" % exc)

    return (True, "%s.%d" % (resource_name, resource_identifier))

