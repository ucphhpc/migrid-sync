#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ssh - remote command wrappers using ssh/scp
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

"""SSH based remote operations"""

import os
import tempfile

from shared.conf import get_resource_exe, get_configuration_object


def copy_file_to_resource(
    filename,
    dest_path,
    resource_config,
    logger,
    ):
    """Copy filename to dest_path relative to resource home on resource
    using scp.
    """

    configuration = get_configuration_object()
    multiplex = '0'
    if resource_config.has_key('SSHMULTIPLEX'):
        multiplex = str(resource_config['SSHMULTIPLEX'])
    hostkey = resource_config['HOSTKEY']
    host = resource_config['HOSTURL']
    identifier = resource_config['HOSTIDENTIFIER']
    unique_id = '%s.%s' % (host, identifier)
    res_dir = configuration.resource_home + os.sep + unique_id
    port = resource_config['SSHPORT']
    user = resource_config['MIGUSER']

    if dest_path.startswith(os.sep):
        logger.warning('copy_file_to_resource: force relative dest path!'
                       )
        dest_path = dest_path.lstrip(os.sep)

    # create known-hosts file with only the resources hostkey (could
    # this be avoided and just passed as an argument?)

    try:

        # Securely open a temporary file in resource dir
        # Please note that mkstemp uses os.open() style rather
        # than open()

        (filehandle, key_path) = tempfile.mkstemp(dir=res_dir,
                text=True)
        os.write(filehandle, hostkey)
        os.close(filehandle)
        logger.debug('single_known_hosts for %s written in %s' % (host,
                     key_path))
        logger.debug('value %s' % hostkey)
    except Exception, err:
        logger.error('could not write single_known_hosts %s (%s)'
                      % (host, err))

    options = []
    if '0' != multiplex:
        options.append('-o ControlPath=%s/ssh-multiplexing' % res_dir)
    options.append('-o Port=%s' % port)
    options.append('-o StrictHostKeyChecking=yes')
    options.append('-o BatchMode=yes')
    options.append('-o CheckHostIP=yes')

    # We need fault tolerance but can't block e.g. grid_script for long

    options.append('-o ConnectionAttempts=2')
    options.append('-o ConnectTimeout=30')
    if hostkey:
        options.append('-o UserKnownHostsFile=' + key_path)

    command = 'scp %s %s %s@%s:%s >> /dev/null 2>> %s/last-scp.err' % (
        ' '.join(options),
        filename,
        user,
        host,
        os.path.join(resource_config['RESOURCEHOME'], dest_path),
        os.environ['HOME'],
        )

    logger.debug(command)
    status = os.system(command) >> 8

    # Remove temp file no matter what command returned

    try:
        os.remove(key_path)
    except Exception, err:
        logger.error('could not remove %s (%s)' % (key_path, err))

    if status != 0:

        # File was not sent!! Take action

        logger.error(command)
        logger.error('scp return code: %s %s' % (status, host))
        return False

    logger.info('scp ok %s' % host)
    return True


def copy_file_to_exe(
    local_filename,
    dest_path,
    resource_config,
    exe_name,
    logger,
    ):
    """Copy local_filename to dest_path relative to execution_dir on
    exe_name. This needs to go through the resource front end using scp
    and the copy method to the exe depends on the shared fs setting.
    """

    msg = ''
    unique_resource_name = resource_config['HOSTURL'] + '.'\
         + resource_config['HOSTIDENTIFIER']
    (status, exe) = get_resource_exe(resource_config, exe_name, logger)
    if not status:
        msg = "No EXE config for: '" + unique_resource_name + "' EXE: '"\
             + exe_name + "'"
        return (False, msg)

    if dest_path.startswith(os.sep):
        logger.warning('copy_file_to_exe: force relative dest path!')
        dest_path = dest_path.lstrip(os.sep)

    # copy file to frontend

    copy_attempts = 5
    for attempt in range(copy_attempts):
        copy_status = copy_file_to_resource(local_filename, dest_path,
                resource_config, logger)
        if not copy_status:
            logger.warning('scp of file failed in attempt %d of %d'
                            % (attempt, copy_attempts))
        else:
            break

    # Remove temporary file no matter what scp returned

    try:
        os.remove(local_filename)
    except Exception, err:
        logger.error('Could not remove %s (%s)' % (local_filename, err))

    if copy_status:
        msg += 'scp of file was successful!\n'
        logger.info('scp of file was successful!')
    else:
        msg += 'scp of file was NOT successful!\n'
        logger.error('scp of file was NOT successful!')
        return (False, msg)

    # copy file to exe

    if exe.has_key('shared_fs') and exe['shared_fs']:
        ssh_command = 'cp '\
             + os.path.join(resource_config['RESOURCEHOME'], dest_path)\
             + ' ' + exe['execution_dir']
    else:

        # We do not have exe host keys and don't really care about auth there

        ssh_command = \
            'scp -o ConnectTimeout=15 -o ConnectionAttempts=2 ' + ' '\
             + os.path.join(resource_config['RESOURCEHOME'], dest_path)\
             + ' ' + exe['execution_user'] + '@' + +exe['execution_node'
                ] + ':' + exe['execution_dir']

    copy_attempts = 5
    for attempt in range(copy_attempts):
        (status, executed_command) = execute_on_resource(ssh_command,
                False, resource_config, logger)
        if status != 0:
            logger.warning('copy of file to exe failed (%d) in attempt %d of %d'
                            % (status, attempt, copy_attempts))
        else:
            break

    msg += executed_command + '\n'

    if 0 != status:
        logger.error('file not copied to exe!')
        msg += 'file not copied to exe!\n'
        return (False, msg)
    else:
        logger.info('file copied to exe')
        msg += 'file copied to exe\n'
        return (True, '')


def execute_on_resource(
    command,
    background,
    resource_config,
    logger,
    ):
    """Execute command on resource"""

    configuration = get_configuration_object()
    hostkey = resource_config['HOSTKEY']
    host = resource_config['HOSTURL']
    port = resource_config['SSHPORT']
    user = resource_config['MIGUSER']
    job_type = 'batch'
    if resource_config.has_key('JOBTYPE'):
        job_type = resource_config['JOBTYPE']
    multiplex = '0'
    if resource_config.has_key('SSHMULTIPLEX'):
        multiplex = str(resource_config['SSHMULTIPLEX'])

    # Use manually added SSHMULTIPLEXMASTER variable to only run master
    # from sessions initiated by ssh_multiplex.py: There's a race in the
    # handling of ControlMaster=auto in openssh-4.3 resulting in error:
    # ControlSocket $SOCKET already exists
    # (see http://article.gmane.org/gmane.network.openssh.devel/13839)

    multiplex_master = False
    if resource_config.has_key('SSHMULTIPLEXMASTER'):
        multiplex_master = bool(resource_config['SSHMULTIPLEXMASTER'])
    identifier = resource_config['HOSTIDENTIFIER']
    unique_id = '%s.%s' % (host, identifier)
    res_dir = configuration.resource_home + os.sep + unique_id

    # fname should be unique to avoid race conditions, since several
    # cgi-scripts may run at the same time due to a multi process
    # or multi thread web server

    try:

        # Securely open a temporary file in resource dir
        # Please note that mkstemp uses os.open() style rather
        # than open()

        (filehandle, key_path) = tempfile.mkstemp(dir=res_dir,
                text=True)
        os.write(filehandle, hostkey)
        os.close(filehandle)
        logger.debug('wrote hostkey %s to %s' % (hostkey, key_path))
    except Exception, err:
        logger.error('could not write tmp host key file (%s)' % err)
        return (-1, '')

    options = []

    # Only enable X forwarding for interactive resources (i.e. job_type
    # 'interactive' or 'all')

    if 'batch' != job_type.lower():
        options.append('-X')
    options.append('-o Port=%s' % port)
    options.append('-o BatchMode=yes')
    options.append('-o CheckHostIP=yes')
    options.append('-o StrictHostKeyChecking=yes')

    # We need fault tolerance but can't block e.g. grid_script for long

    options.append('-o ConnectionAttempts=2')
    options.append('-o ConnectTimeout=30')
    if hostkey:
        options.append('-o UserKnownHostsFile=%s' % key_path)

    if '0' != multiplex:
        options.append('-o ControlPath=%s/ssh-multiplexing' % res_dir)

        # Only open a new control socket if explicitly told so:
        # All other invocations will reuse it if possible.

        if multiplex_master:
            options.append('-o ControlMaster=yes')

    batch = []
    batch.append('1> /dev/null')
    batch.append('2> /dev/null')
    if background:
        batch.append('&')

    ssh_command = 'ssh %s %s@%s "bash -c \'%s %s\'"'\
         % (' '.join(options), user, host, command, ' '.join(batch))
    logger.debug(ssh_command)
    status = os.system(ssh_command) >> 8

    # Remove temp file no matter what ssh command returned

    try:
        os.remove(key_path)
    except Exception, err:
        logger.error('Could not remove hostkey file %s: %s'
                      % (key_path, err))

    if 0 != status:

        # Command was not executed with return code 0!! Take action

        logger.error('%s EXITED WITH STATUS: %s' % (ssh_command,
                     status))
        return (status, ssh_command)

    logger.debug('Remote execution ok: %s' % ssh_command)
    return (status, ssh_command)


def execute_on_exe(
    command,
    background,
    resource_config,
    exe_config,
    logger,
    ):
    """Execute command (through resource) on exe"""

    node = exe_config['execution_node']
    user = exe_config['execution_user']
    options = []
    options.append('-X')
    options.append('-o BatchMode=yes')

    # We need fault tolerance but can't block e.g. grid_script for long

    options.append('-o ConnectionAttempts=2')
    options.append('-o ConnectTimeout=30')
    batch = []
    batch.append('1> /dev/null')
    batch.append('2> /dev/null')
    ssh_command = "ssh %s %s@%s \'%s %s\'" % (' '.join(options), user,
            node, command, ' '.join(batch))
    logger.debug(ssh_command)
    return execute_on_resource(ssh_command, background,
                               resource_config, logger)


def execute_remote_ssh(
    remote_port,
    remote_hostkey,
    remote_username,
    remote_hostname,
    ssh_command,
    logger,
    ssh_background,
    resource_dir='/tmp',
    ):
    """Wrap old style ssh calls to use new version"""

    resource_config = {
        'SSHPORT': remote_port,
        'HOSTKEY': remote_hostkey,
        'MIGUSER': remote_username,
        'HOSTURL': remote_hostname,
        }
    return execute_on_resource(ssh_command, ssh_background,
                               resource_config, logger)


