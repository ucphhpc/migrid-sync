#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resadm - Resource administration functions mostly for remote command execution
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

"""Resource administration - mostly remote command execution"""

import os
import subprocess
import tempfile
import fcntl
import time

# MiG imports

from shared.conf import get_resource_configuration, get_resource_exe, \
    get_resource_store, get_configuration_object
from shared.fileio import unpickle
from shared.ssh import execute_on_resource, execute_on_exe, execute_on_store, \
    copy_file_to_exe, copy_file_to_resource

ssh_error_code = 255
ssh_error_msg = \
    ''' (%d means that an error occurred in the ssh login to the
resource - this is typically a matter of problems with the ssh host key or login
with ssh key from the MiG server to the resource frontend or from the resource frontend
to the execution node. Please check that you can login all the way through to the execution
node without interactive input)'''\
     % ssh_error_code
ssh_status_msg = \
    ' (0 means OK, 1 or other positive values generally indicate a problem)'


def put_fe_pgid(
    resource_home,
    unique_resource_name,
    pgid,
    logger,
    sandbox=False,
    ):
    """Write front end PGID in resource home"""

    msg = ''

    # Please note that base_dir must end in slash to avoid access to other
    # resource dirs when own name is a prefix of another resource name

    base_dir = os.path.abspath(os.path.join(resource_home,
                               unique_resource_name)) + os.sep

    # There should not be more than one running FE on each resource
    # A "FE.PGID" file in the resource's home directory means that
    # the FE is running.

    pgid_path = os.path.join(base_dir, 'FE.PGID')

    if not os.path.exists(pgid_path):

        # The pgid_path is only created the first time the FE
        # is started. Thus the minor race where two such processes
        # get here at once (race between open+truncate and
        # locking) can be ignored.

        pgid_file = open(pgid_path, 'w')
        pgid_file.write('stopped\n')
        pgid_file.flush()
        pgid_file.close()

    try:
        pgid_file = open(pgid_path, 'r+')
        fcntl.flock(pgid_file, fcntl.LOCK_EX)
        old_pgid = pgid_file.readline().strip()
        pgid_file.seek(0, 0)
        if not old_pgid.isdigit():
            pgid_file.write(pgid + '\n')
            pgid_file.flush()
        fcntl.flock(pgid_file, fcntl.LOCK_UN)
        pgid_file.close()
        if old_pgid.isdigit():
            raise Exception('FE already started')
        msg = "FE pgid: '%s' wrote for %s" % (pgid,
                unique_resource_name)
        status = True
    except:
        msg = 'FE: %s already started.' % unique_resource_name
        status = False

    return (status, msg)


def put_exe_pgid(
    resource_home,
    unique_resource_name,
    exe_name,
    pgid,
    logger,
    sandbox=False,
    ):
    """Write exe PGID file in resource home and stop exe if requested"""

    msg = ''

    # Please note that base_dir must end in slash to avoid access to other
    # resource dirs when own name is a prefix of another resource name

    base_dir = os.path.abspath(os.path.join(resource_home,
                                            unique_resource_name)) + os.sep

    # The exe node script has already been started on resource, so we
    # better get the PGID no matter what.
    # If resource EXE PGID has status stopped, we must write PGID and
    # then call the resource EXE stop command to make sure the EXE
    # node stops.
    # This is required to avoid 'races', as it is the FE that sends
    # the PGID to us and not the EXE node.

    pgid_path = os.path.abspath(os.path.join(base_dir, 'EXE_' + exe_name
                                 + '.PGID'))
    status = False
    try:

        # PGID file *must* exists since start exe creates it

        pgid_file = open(pgid_path, 'r+')

        # Get exclusive lock over pgid_path

        fcntl.flock(pgid_file, fcntl.LOCK_EX)
        pgid_file.seek(0, 0)
        old_pgid = pgid_file.readline().strip()
        pgid_file.truncate(0)
        pgid_file.seek(0, 0)
        pgid_file.write(pgid + '\n')
        pgid_file.flush()
        os.fsync(pgid_file.fileno())

        msg = "pgid: '%s' put for %s %s" % (pgid, unique_resource_name,
                exe_name)

        if not sandbox and 'stopped' == old_pgid:
            msg += "Resource: '" + unique_resource_name\
                 + "' EXE node: '" + exe_name\
                 + "' has been stopped, kill EXE script."
            resource_exe_action(
                unique_resource_name,
                exe_name,
                resource_home,
                'stop',
                logger,
                False,
                )

        # Don't release lock until stop is executed

        fcntl.flock(pgid_file, fcntl.LOCK_UN)
        pgid_file.close()
        status = True
    except Exception, err:
        msg = 'File: %s could not be read/written: %s' % (pgid_path,
                err)
        status = False

    return (status, msg)


def start_resource_exe_if_continuous(
    unique_resource_name,
    finished_exe,
    resource_home,
    logger,
    lock_pgid_file=True,
    ):
    """If the resource is marked as continuous, then start the exe"""

    found = False

    # open the resources configuration

    resource_configuration_file = resource_home + '/'\
         + unique_resource_name + '/config'
    resource_dict = unpickle(resource_configuration_file, logger)

    if not resource_dict:
        return (False, 'Failed to unpack resource configuration!')
    if not resource_dict.has_key('SANDBOX'):
        resource_dict['SANDBOX'] = 0

    if resource_dict['SANDBOX'] == 1:
        return (True, '')

    for exe in resource_dict['EXECONFIG']:
        if exe['name'] == finished_exe:
            found = True

            # Handle old typo gracefully

            if exe.has_key('continuous'):
                continuous = exe['continuous']
            else:
                continuous = exe['continious']
            if continuous:
                logger.info('Continuous: trying to restart the exe by SSH %s %s'
                             % (unique_resource_name, finished_exe))

                # start_resource_exe returns a tuple with status as first entry

                (stat, err) = start_resource_exe(
                    unique_resource_name,
                    finished_exe,
                    resource_home,
                    -1,
                    logger,
                    lock_pgid_file,
                    )
                if not stat:
                    err_msg = 'start_resource_exe failed %s %s: %s'\
                         % (unique_resource_name, finished_exe, err)
                    logger.error(err_msg)
                    return (False, err_msg)
            else:
                logger.debug('Continuous is False in configuration for %s %s'
                              % (unique_resource_name, finished_exe))
            break
    if not found:
        err_msg = \
            'start_resource_exe_if_continuous could not find %s %s'\
             % (unique_resource_name, finished_exe)
        logger.error(err_msg)
        return (False, err_msg)
    else:
        return (True, '')


def atomic_resource_exe_restart(
    unique_resource_name,
    exe_name,
    configuration,
    logger,
    ):
    """Atomic version of exe node restart needed for consistent
    clean up.
    """

    resource_home = configuration.resource_home

    pgid_path = os.path.join(resource_home, unique_resource_name, 'EXE_'
                              + exe_name + '.PGID')

    # Lock pgid file

    if os.path.exists(pgid_path):
        pgid_file = open(pgid_path, 'r')
    else:
        return (False, 'No pgid_path found! File %s' % pgid_path)

    fcntl.flock(pgid_file, fcntl.LOCK_EX)
    pgid_file.seek(0, 0)
    pgid = pgid_file.readline().strip()
    exit_status = True
    exit_msg = ''
    if pgid.isdigit():

        # Stop the resource executing the job

        logger.info('atomic restart: stopping %s %s'
                     % (unique_resource_name, exe_name))
        (stop_status, stop_msg) = resource_exe_action(
            unique_resource_name,
            exe_name,
            resource_home,
            'stop',
            logger,
            False,
            )
        if stop_status:
            logger.info('atomic restart: starting %s %s'
                         % (unique_resource_name, exe_name))
            (exit_status, exit_msg) = \
                start_resource_exe_if_continuous(unique_resource_name,
                    exe_name, resource_home, logger, False)
        else:
            logger.info('atomic restart: not starting stopped %s %s: %s'
                         % (unique_resource_name, exe_name, stop_msg))

    pgid_file.flush()
    fcntl.flock(pgid_file, fcntl.LOCK_UN)
    pgid_file.close()

    return (exit_status, exit_msg)


def fill_frontend_script(
    filehandle,
    https_sid_url,
    unique_resource_name,
    resource_config,
    ):
    """Fill in frontend template"""

    msg = ''

    try:
        os.write(filehandle, '#!/bin/bash\n')
        os.write(filehandle, 'migserver=' + https_sid_url + '\n')
        os.write(filehandle, 'unique_resource_name='
                  + unique_resource_name + '\n')
        os.write(filehandle, 'frontendlog='
                  + resource_config['FRONTENDLOG'] + '\n')
        os.write(filehandle, 'curllog=' + resource_config['CURLLOG']
                  + '\n')

        if resource_config.has_key('SANDBOX'):
            os.write(filehandle, 'sandbox='
                      + str(resource_config['SANDBOX']) + '\n')
            if resource_config['SANDBOX'] == 1:

                # resource is a sandbox

                if not resource_config.has_key('SANDBOXKEY'):
                    return (False,
                            'Resource error, SANDBOX flag is true but SANDBOXKEY was not found!'
                            )
                else:
                    os.write(filehandle, 'sandboxkey='
                              + str(resource_config['SANDBOXKEY'])
                              + '\n')
        else:
            os.write(filehandle, 'sandbox=0\n')

        # append frontend_script.sh

        newhandle = open('../resource/frontend_script.sh', 'r')
        os.write(filehandle, newhandle.read())
        newhandle.close()
        return (True, '')
    except Exception, err:
        msg = \
            'Error: could not write frontend script file for some reason %s'\
             % err

        # logger.error("could not write frontend script file (%s)" % err)

        return (False, msg)


def fill_exe_node_script(
    filehandle,
    resource_config,
    exe,
    cputime,
    name,
    ):
    """Fill ANY_node_script template"""

    try:
        if cputime == -1:
            walltime = exe['cputime']
        else:
            walltime = str(cputime)
        configuration = get_configuration_object()
        empty_job_name = configuration.empty_job_name

        os.write(filehandle, '#!/bin/bash\n')
        os.write(filehandle, '#\n')
        os.write(filehandle, "empty_job_name='%s'\n" % empty_job_name)
        os.write(filehandle, 'exe=' + exe['name'] + '\n')
        os.write(filehandle, 'nodecount=' + exe['nodecount'] + '\n')
        os.write(filehandle, 'cputime=' + str(walltime) + '\n')

        # For backwards compatibility

        execution_precondition = ''
        if exe.has_key('execution_precondition'):
            execution_precondition = exe['execution_precondition']
        os.write(filehandle, 'execution_precondition='
                  + execution_precondition + '\n')
        os.write(filehandle, 'prepend_execute=' + exe['prepend_execute']
                  + '\n')
        os.write(filehandle, 'exehostlog=' + exe['exehostlog'] + '\n')
        os.write(filehandle, 'joblog=' + exe['joblog'] + '\n')
        os.write(filehandle, 'frontend_user='
                  + resource_config['MIGUSER'] + '\n')
        os.write(filehandle, 'frontend_node='
                  + resource_config['FRONTENDNODE'] + '\n')
        os.write(filehandle, 'frontend_dir='
                  + resource_config['RESOURCEHOME'] + '\n')
        os.write(filehandle, 'execution_user=' + exe['execution_user']
                  + '\n')
        os.write(filehandle, 'execution_node=' + exe['execution_node']
                  + '\n')
        os.write(filehandle, 'execution_dir=' + exe['execution_dir']
                  + '\n')
        admin_email = ''
        if resource_config.has_key('ADMINEMAIL'):
            admin_email = resource_config['ADMINEMAIL']
        os.write(filehandle, "admin_email='%s'\n" % admin_email)
        execution_delay_command = ''
        if resource_config.has_key('LRMSDELAYCOMMAND'):
            execution_delay_command = resource_config['LRMSDELAYCOMMAND'
                    ]
        os.write(filehandle, "execution_delay_command='%s'\n"
                  % execution_delay_command)
        submit_job_command = ''
        if resource_config.has_key('LRMSSUBMITCOMMAND'):
            submit_job_command = resource_config['LRMSSUBMITCOMMAND']
        os.write(filehandle, "submit_job_command='%s'\n"
                  % submit_job_command)
        remove_job_command = ''
        if resource_config.has_key('LRMSREMOVECOMMAND'):
            remove_job_command = resource_config['LRMSREMOVECOMMAND']
        os.write(filehandle, "remove_job_command='%s'\n"
                  % remove_job_command)
        query_done_command = ''
        if resource_config.has_key('LRMSDONECOMMAND'):
            query_done_command = resource_config['LRMSDONECOMMAND']
        os.write(filehandle, "query_done_command='%s'\n"
                  % query_done_command)

        # Backward compatible test for shared_fs - fall back to scp

        if exe.get('shared_fs', True):
            os.write(filehandle, "copy_command='cp'\n")
            os.write(filehandle, 'copy_frontend_prefix=""\n')
            os.write(filehandle, 'copy_execution_prefix=""\n')
            os.write(filehandle, "move_command='mv -f'\n")
        else:
            os.write(filehandle, "copy_command='scp -B'\n")
            os.write(filehandle,
                     'copy_frontend_prefix="${frontend_user}@${frontend_node}:"\n'
                     )
            os.write(filehandle,
                     'copy_execution_prefix="${execution_user}@${execution_node}:"\n'
                     )
            os.write(filehandle, "move_command='scp -B -r'\n")

        # append ANY_node_script!

        newhandle = open('../resource/%s_node_script.sh' % name, 'r')
        os.write(filehandle, newhandle.read())
        newhandle.close()
        return (True, '')
    except Exception, err:
        return (False, 'could not write exe node script file: %s' % err)


def fill_master_node_script(
    filehandle,
    resource_config,
    exe,
    cputime,
    ):
    """Fill in master_node_script template"""

    return fill_exe_node_script(filehandle, resource_config, exe,
                                cputime, 'master')


def get_frontend_script(unique_resource_name, logger):
    """Create frontend_script"""

    msg = ''

    configuration = get_configuration_object()

    (status, resource_config) = \
        get_resource_configuration(configuration.resource_home,
                                   unique_resource_name, logger)
    if not status:
        msg = 'No resouce_config for: ' + "'" + unique_resource_name\
             + "'\n"
        return (False, msg)

    # Generate newest version of frontend_script.sh
    # Put unique_resource_name and the URL of the MiG server in the script
    # Securely open a temporary file in resource_dir
    # Please note that mkstemp uses os.open() style rather than open()

    try:
        resource_dir = os.path.join(configuration.resource_home,
                                    unique_resource_name)

        (filehandle, local_filename) = \
            tempfile.mkstemp(dir=resource_dir, text=True)

        (status, msg) = fill_frontend_script(filehandle,
                configuration.migserver_https_url,
                unique_resource_name, resource_config)
        if not status:
            return (False, msg)

        os.lseek(filehandle, 0, 0)
        fe_script = os.read(filehandle, os.path.getsize(local_filename))
        os.close(filehandle)
        os.remove(local_filename)
        logger.debug('got frontend script %s', local_filename)
        return (True, fe_script)
    except Exception, err:

        msg = 'could not get frontend script (%s)' % err
        logger.error(msg)
        return (False, msg)


def get_master_node_script(unique_resource_name, exe_name, logger):
    """Create master_node_script"""

    msg = ''

    configuration = get_configuration_object()

    (status, resource_config) = \
        get_resource_configuration(configuration.resource_home,
                                   unique_resource_name, logger)
    if not status:
        msg = "No resouce_config for: '" + unique_resource_name + "'\n"
        return (False, msg)

    (status, exe) = get_resource_exe(resource_config, exe_name, logger)
    if not status:
        msg = "No exe found: '%s' in resource config for: '%s'"\
             % (exe_name, unique_resource_name)

        return (False, msg)

    # Add values from resource config to the top of master_node_script.sh

    try:
        resource_dir = os.path.join(configuration.resource_home,
                                    unique_resource_name)

        (filehandle, local_filename) = \
            tempfile.mkstemp(dir=resource_dir, text=True)
        (status, msg) = fill_exe_node_script(filehandle,
                resource_config, exe, -1, 'master')

        if not status:
            return (False, msg)

        os.lseek(filehandle, 0, 0)
        exe_script = os.read(filehandle,
                             os.path.getsize(local_filename))
        os.close(filehandle)
        os.remove(local_filename)
        logger.debug('got master node script %s', local_filename)
        return (True, exe_script)
    except Exception, err:

        msg = 'could not get master node script script (%s)' % err
        logger.error(msg)
        return (False, msg)


def get_node_kind(start_cmd):
    """Extract kind of node from start_cmd string"""

    if -1 != start_cmd.find('leader_node_script'):
        return 'leader'
    elif -1 != start_cmd.find('dummy_node_script'):
        return 'dummy'
    else:
        return 'master'


def start_resource_exe(
    unique_resource_name,
    exe_name,
    resource_home,
    cputime,
    logger,
    lock_pgid_file=True,
    ):
    """Start exe node"""

    msg = ''

    (status, resource_config) = \
        get_resource_configuration(resource_home, unique_resource_name,
                                   logger)
    if not status:
        msg += "No resouce_config for: '" + unique_resource_name + "'\n"
        return (False, msg)

    (status, exe) = get_resource_exe(resource_config, exe_name, logger)
    if not status:
        msg = "No EXE config for: '" + unique_resource_name + "' EXE: '"\
             + exe_name + "'"
        return (False, msg)

    # write PGID file

    pgid_path = os.path.join(resource_home, unique_resource_name, 'EXE_'
                              + exe_name + '.PGID')

    try:
        if not os.path.exists(pgid_path):

            # The pgid_path is only created the first time the exe
            # is started. Thus the minor race where two such processes
            # get here at once (race between open+truncate and
            # locking) can be ignored.

            pgid_file = open(pgid_path, 'w')
            pgid_file.write('stopped\n')
            pgid_file.close()

        pgid_file = open(pgid_path, 'r+')
        if lock_pgid_file:
            fcntl.flock(pgid_file, fcntl.LOCK_EX)
        pgid_file.seek(0, 0)
        pgid = pgid_file.readline().strip()
        if lock_pgid_file:
            fcntl.flock(pgid_file, fcntl.LOCK_UN)

        if 'starting' == pgid or pgid.isdigit():
            msg = "Resource: '%s' EXE: '%s' already started."\
                 % (unique_resource_name, exe_name)
            logger.error(msg)
            return (False, msg)
        elif 'stopped' != pgid and 'finished' != pgid:
            msg = 'pgid has unexpected value during exe start: %s'\
                 % pgid
            logger.error(msg)
            return (False, msg)

        # We know pgid is stopped or finished!

        if lock_pgid_file:
            fcntl.flock(pgid_file, fcntl.LOCK_EX)
        pgid_file.truncate(0)
        pgid_file.seek(0, 0)
        pgid_file.write('starting\n')
        pgid_file.flush()
        if lock_pgid_file:
            fcntl.flock(pgid_file, fcntl.LOCK_UN)
        pgid_file.close()
    except Exception, err:
        err_msg = "File: '%s' could not be accessed: %s" % (pgid_path,
                err)
        logger.error(err_msg)
        msg += err_msg
        return (False, msg)

    # remove jobrequest_pending lockfile

    jobrequest_lock_file = '%s/%s/jobrequest_pending.%s'\
         % (resource_home, unique_resource_name, exe_name)
    try:
        os.remove(jobrequest_lock_file)
    except OSError, ose:

        # only accept no such file errors - meaning lock wasn't there

        if ose.errno != 2:
            logger.error('removing %s failed: %s'
                          % (jobrequest_lock_file, ose))
    except Exception, err:
        logger.error('removing %s failed: %s' % (jobrequest_lock_file,
                     err))

    # create needed dirs on resource frontend and exe

    create_dirs = 'mkdir -p %s' % exe['execution_dir']
    if exe.get('shared_fs', True):
        (create_status, create_err) = execute_on_resource(create_dirs,
                False, resource_config, logger)
    else:
        (create_status, create_err) = execute_on_exe(create_dirs, False,
                resource_config, exe, logger)

    if 0 != create_status:
        msg += '\ncreate exe node dirs returned %s (command %s): %s'\
             % (create_status, create_dirs, create_err)
        logger.error('failed to create execution dir on resource: %s'
                      % create_err)

    # add values from resource config to the top of
    # %(exe_kind)s_node_script.sh and copy it to exe

    exe_kind = get_node_kind(exe['start_command'])
    try:

        # Securely open a temporary file in resource_dir
        # Please note that mkstemp uses os.open() style rather
        # than open()

        resource_dir = os.path.join(resource_home, unique_resource_name)
        (filehandle, local_filename) = \
            tempfile.mkstemp(dir=resource_dir, text=True)
        (rv, msg) = fill_exe_node_script(filehandle, resource_config,
                exe, cputime, exe_kind)
        if not rv:
            logger.error('fill %s node script failed: %s' % (exe_kind,
                         err))
            return (False, msg)
        os.close(filehandle)

        logger.info('wrote %s script into %s' % (exe_kind,
                    local_filename))
    except Exception, err:
        msg += '\n%s' % err
        logger.error("couldn't write %s node script file: %s"
                      % (exe_kind, err))
        return (False, msg)

    exe_node_script_name = '%s_node_script_%s.sh' % (exe_kind, exe_name)
    (copy_status, copy_msg) = copy_file_to_exe(local_filename,
            exe_node_script_name, resource_config, exe_name, logger)
    if not copy_status:
        logger.error(copy_msg)
        return (False, copy_msg)

    # execute start command

    logger.info('starting command')
    command = exe['start_command']
    (exit_code, executed_command) = execute_on_resource(command, True,
            resource_config, logger)
    logger.info('command started')

    msg += executed_command + '\n' + command + ' returned '\
         + str(exit_code)

    if exit_code == ssh_error_code:
        msg += ssh_error_msg
        return (False, msg)
    else:
        msg += ssh_status_msg
        return (True, msg)


def start_resource_store(
    unique_resource_name,
    store_name,
    resource_home,
    cputime,
    logger,
    lock_pgid_file=True,
    ):
    """Start store node"""

    msg = ''

    configuration = get_configuration_object()
    (status, resource_config) = \
        get_resource_configuration(resource_home, unique_resource_name,
                                   logger)
    if not status:
        msg += "No resouce_config for: '" + unique_resource_name + "'\n"
        return (False, msg)

    (status, store) = get_resource_store(resource_config, store_name, logger)
    if not status:
        msg = "No STORE config for: '" + unique_resource_name + "' STORE: '"\
             + store_name + "'"
        return (False, msg)

    # create needed dirs on resource frontend and store

    create_dirs = 'mkdir -p %(storage_dir)s' % store
    if store.get('shared_fs', True):
        (create_status, create_err) = execute_on_resource(create_dirs,
                False, resource_config, logger)
    else:
        (create_status, create_err) = execute_on_store(create_dirs, False,
                resource_config, store, logger)

    if 0 != create_status:
        msg += '\ncreate store node dirs returned %s (command %s): %s'\
             % (create_status, create_dirs, create_err)
        logger.error('failed to create storage dir on resource: %s'
                      % create_err)

    status = True
    if 'sftp' == store['storage_protocol']:
        sshfs_options = ['-o reconnect', '-C']
        setup = {'mount_point': os.path.join(resource_home, unique_resource_name, store_name)}
        setup.update(resource_config)
        setup.update(store)
        try:
            os.mkdir(setup['mount_point'])
        except:
            pass

        for vgrid in store['vgrid']:
            vgrid_link = os.path.join(configuration.vgrid_files_home, vgrid, "%s_%s" % \
                                      (unique_resource_name, store_name))
            try:
                os.symlink(setup['mount_point'], vgrid_link)
            except Exception, exc:
                status = False
                msg += ' failed to link %s into %s: %s. ' % (setup['mount_point'], vgrid_link, exc)

        if not store.get('shared_fs', True):

            # execute start command to prepare remote tunnel or mount

            command = store['start_command']
            logger.info('running start command on front end: %s' % command)
            (exit_code, executed_command) = execute_on_resource(command, True,
                                                                resource_config, logger)
            if exit_code == ssh_error_code:
                status = False
                msg += ssh_error_msg
            else:
                msg += ssh_status_msg
            sshfs_options.append("-o ssh_command='ssh -o Port=%(SSHPORT)d -o User=%(MIGUSER)s %(HOSTURL)s ssh'" % setup)

        setup['options'] = ' '.join(sshfs_options)
        command = 'sshfs %(storage_user)s@%(storage_node)s:%(storage_dir)s %(mount_point)s %(options)s' % \
                  setup
        logger.info('running mount command on server: %s' % command)
        msg += 'mounting with %s. ' % command
        proc = subprocess.Popen(command, shell=True, bufsize=0, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        exit_code = proc.wait()
        output =  proc.stdout.read()
        msg += '%s returned %s ' % (command, exit_code)
        if exit_code > 0:
            status = False
            msg += '(non-zero indicates error during mount). %s . ' % output
        else:
            msg += '(0 means success). '
    else:
        status = False
        msg += 'unsupported storage_protocol: %(storage_protocol)s' % store

    return (status, msg)


def start_resource_frontend(unique_resource_name, configuration,
                            logger):
    """Start resource front end"""

    return start_resource(unique_resource_name,
                          configuration.resource_home,
                          configuration.migserver_https_url, logger)


def start_resource(
    unique_resource_name,
    resource_home,
    https_sid_url,
    logger,
    ):
    """Start resource frontend"""

    msg = ''

    (status, resource_config) = \
        get_resource_configuration(resource_home, unique_resource_name,
                                   logger)
    if not status:
        msg += "No resouce_config for: '" + unique_resource_name + "'\n"
        return (False, msg)

    pgid_path = os.path.join(resource_home, unique_resource_name, 'FE.PGID')
    if os.path.exists(pgid_path):
        try:

            # determine if fe runs by finding out if pgid is numerical

            pgid_file = open(pgid_path, 'r')
            fcntl.flock(pgid_file, fcntl.LOCK_EX)
            pgid = pgid_file.readline().strip()
            fcntl.flock(pgid_file, fcntl.LOCK_UN)
            pgid_file.close()
            if pgid.isdigit():
                raise Exception('FE already started')
        except Exception, exc:
            msg += str(exc)
            return (False, msg)

    # make sure newest version of frontend_script.sh is on the
    # resource and put unique_resource_name and the URL of the MiG
    # server in the script.
    # Securely open a temporary file in resource_dir
    # Please note that mkstemp uses os.open() style rather than open()

    try:
        resource_dir = os.path.join(resource_home, unique_resource_name)
        (filehandle, local_filename) = \
            tempfile.mkstemp(dir=resource_dir, text=True)
        (rv, msg) = fill_frontend_script(filehandle, https_sid_url,
                unique_resource_name, resource_config)
        if not rv:
            return (False, msg)
        os.close(filehandle)
        logger.debug('wrote frontend script %s', local_filename)
    except Exception, err:
        logger.error('could not write frontend script (%s)', err)
        return (False, msg)

    # create needed dirs on resource frontend

    create_dirs = 'mkdir -p %s' % resource_config['RESOURCEHOME']
    (create_status, executed_command) = \
        execute_on_resource(create_dirs, False, resource_config, logger)

    if create_status != 0:
        msg += ' create frontend dirs returned %s. ' % create_status

    copy_status = copy_file_to_resource(local_filename,
            'frontend_script.sh', resource_config, logger)

    # Remove temporary file no matter what copy returned

    try:
        if os.path.isfile(local_filename):
            os.remove(local_filename)
    except Exception, err:
        logger.error('Could not remove %s (%s)', local_filename, err)

    if copy_status:
        msg += 'copy of frontend_script.sh was successfull!\n'
    else:

        # logger.info("copy of frontend_script.sh was successfull!")

        msg += 'copy of frontend_script.sh was NOT successfull!\n'

        # logger.error("copy of frontend_script.sh was NOT successfull!")

        return (False, msg)

    command = 'cd %s; chmod +x frontend_script.sh; ./frontend_script.sh'\
         % resource_config['RESOURCEHOME']
    (exit_code, executed_command) = execute_on_resource(command, False,
            resource_config, logger)

    msg += executed_command + '\n' + command + ' returned '\
         + str(exit_code)

    if exit_code == ssh_error_code:
        msg += ssh_error_msg
        return (False, msg)
    else:
        msg += ssh_status_msg
        return (True, msg)


def resource_fe_action(
    unique_resource_name,
    exe_name,
    resource_home,
    action,
    logger,
    ):
    """This function handles status and stop for resource FE's"""

    msg = ''

    if not action in ['status', 'stop', 'clean']:
        msg = 'Unknown action: %s' % action
        return (False, msg)

    (status, resource_config) = \
        get_resource_configuration(resource_home, unique_resource_name,
                                   logger)
    if not status:
        msg = "No configfile for: '" + unique_resource_name + "'"
        return (False, msg)

    pgid_path = os.path.join(resource_home, unique_resource_name,
                             'FE.PGID')

    if action == 'clean':
        fe_running = True
        try:

            # determine if fe runs by finding out if pgid is numerical

            pgid_file = open(pgid_path, 'r')
            fcntl.flock(pgid_file, fcntl.LOCK_EX)
            pgid = pgid_file.readline().strip()
            fcntl.flock(pgid_file, fcntl.LOCK_UN)
            pgid_file.close()
            if not pgid.isdigit():
                raise Exception('FE already stopped')
        except:
            fe_running = False

        if fe_running:
            return (False,
                    'Please stop the frontend before calling clean.')

        command = 'rm -rf %s' % resource_config['RESOURCEHOME']
        (exit_code, executed_command) = execute_on_resource(command,
                False, resource_config, logger)

        msg += executed_command + '\n' + command + ' returned '\
             + str(exit_code)

        if exit_code == ssh_error_code:
            msg += ssh_error_msg
            return (False, msg)
        else:
            msg += ssh_status_msg
            return (True, msg)

    try:
        pgid_file = open(pgid_path, 'r')
        fcntl.flock(pgid_file, fcntl.LOCK_EX)
        pgid = pgid_file.readline().strip()
        fcntl.flock(pgid_file, fcntl.LOCK_UN)
        pgid_file.close()

        if not pgid.isdigit():
            raise Exception('FE already stopped')

        if action == 'status':
            command = 'if [ \\`ps -o pid= -g ' + pgid\
                 + ' | wc -l \\` -eq 0 ];then exit 1; else exit 0;fi'
            (exit_code, executed_command) = \
                execute_on_resource(command, False, resource_config,
                                    logger)
            msg = executed_command + '\n' + command + ' returned '\
                 + str(exit_code)

            if exit_code == ssh_error_code:
                msg += ssh_error_msg
                return (False, msg)
            else:
                msg += ssh_status_msg
                return (True, msg)
        elif action == 'stop':

            # Try pkill if ordinary kill doesn't work (-PGID not
            # always supported)

            command = 'kill -9 -' + pgid + ' || pkill -9 -g ' + pgid\
                 + " \.\*"
            (exit_code, executed_command) = \
                execute_on_resource(command, False, resource_config,
                                    logger)
            msg = executed_command + '\n' + command + ' returned '\
                 + str(exit_code)

            # 0 Means FE killed, 1 means process' with PGID not
            # found, which means FE already dead.

            if exit_code == ssh_error_code:
                msg += ssh_error_msg
                return (False, msg)
            else:
                try:
                    pgid_file = open(pgid_path, 'r+')
                    fcntl.flock(pgid_file, fcntl.LOCK_EX)
                    pgid_file.write('stopped')
                    pgid_file.flush()
                    fcntl.flock(pgid_file, fcntl.LOCK_UN)
                    pgid_file.close()
                except Exception, err:
                    logger.error("Could not update pgid file: '"
                                  + pgid_path + "'")

                msg += ssh_status_msg
                return (True, msg)
    except Exception, err:

        # msg = "FE.PGID could not be read and the status of the frontend is therefore unknown. Could not perform requested action, try (re)starting the frontend"

        msg = 'Frontend is stopped'
        if 'stop' == action:
            return (True, msg)
        elif 'status' == action:
            return (True, msg)


def resource_exe_action(
    unique_resource_name,
    exe_name,
    resource_home,
    action,
    logger,
    lock_pgid_file=True,
    ):
    """This function handles status and stop for exes.
    If then parameter lock_pgid_file is False, the calling function
    must handle locking of the 'pgid_path'.
    """

    msg = ''

    if not action in ['status', 'stop', 'clean']:
        msg = 'Unknown action: %s' % action
        return (False, msg)

    (status, resource_config) = \
        get_resource_configuration(resource_home, unique_resource_name,
                                   logger)
    if not status:
        msg = "No configfile for: '" + unique_resource_name + "'"
        return (False, msg)

    (status, exe) = get_resource_exe(resource_config, exe_name, logger)
    if not status:
        msg = "No EXE config for: '" + unique_resource_name + "' EXE: '"\
             + exe_name + "'"
        return (False, msg)

    pgid_path = os.path.join(resource_home, unique_resource_name, 'EXE_'
                              + exe_name + '.PGID')
    try:
        pgid_file = open(pgid_path, 'r+')
    except IOError:
        msg = 'No PGID file - EXE node never started.'
        if 'status' == action:
            return (False, msg)
        elif 'clean' == action:
            return (True, msg)
        elif 'stop' == action:
            return (True, msg)

    try:

        # Get exclusive lock over pgid_path

        if lock_pgid_file:
            fcntl.flock(pgid_file, fcntl.LOCK_EX)

        if 'status' == action:
            pgid_file.seek(0, 0)
            pgid = pgid_file.readline().strip()
            if 'stopped' == pgid:
                return (True,
                        "Exe is not running (pgid on server is 'stopped')"
                        )
            elif 'finished' == pgid and exe['continious']:
                return (True,
                        "Exe is running (pgid on server is '%s' and exe continious is '%s')"
                         % (pgid, exe['continious']))
            elif 'finished' == pgid and not exe['continious']:
                return (True,
                        "Exe is not running (pgid on server is '%s' and exe continious is '%s')"
                         % (pgid, exe['continious']))
            elif 'starting' == pgid:

                # use pgid file on exe and run status command based on that value

                command = exe['status_command']
                command = command.replace('$mig_exe_pgid',
                        "\\\\\`cat %s/%s \\\\\`" % (exe['execution_dir'
                        ], '%s.pgid' % exe['name']))
            elif pgid.isdigit():

                # use exe_pgid and run status command based on that value

                command = exe['status_command']
            else:
                logger.error('status exe in unexpected state in resadm if else!'
                             )
                return (False,
                        'status exe in unexpected state in resadm if else!'
                        )
        elif 'clean' == action:

            pgid_file.seek(0, 0)
            pgid = pgid_file.readline().strip()
            command = exe['clean_command']
        elif 'stop' == action:
            num_of_retries = 5
            sleep_time = 5

            # If PGID has status starting, the MiG server is
            # waiting for the FE to send the PGID of the
            # execution node, we will wait
            # 'num_of_retries*sleep_time' to see if the PGID
            # shows up.

            pgid = 'not set'
            for _ in range(num_of_retries):
                pgid_file.seek(0, 0)
                pgid = pgid_file.readline().strip()
                if 'starting' == pgid:
                    if lock_pgid_file:
                        fcntl.flock(pgid_file, fcntl.LOCK_UN)

                    # We need to close and open fileobject,
                    # in order to get it to re-read the file into its
                    # buffer.
                    # if this turns out to be a performance problem.
                    # replace all the highlevel file operations with
                    # lowlevel 'os.' fileoperations

                    pgid_file.close()
                    time.sleep(sleep_time)
                    pgid_file = open(pgid_path, 'r+')

                    if lock_pgid_file:
                        fcntl.flock(pgid_file, fcntl.LOCK_EX)

            # now find out if pgid has been received or it is still "starting"

            if 'stopped' == pgid or 'finished' == pgid:
                return (True, 'Exe is not running, pgid status is %s'
                         % pgid)
            elif pgid.isdigit():
                command = exe['stop_command']
            elif 'starting' == pgid:

                # read pgid on resource

                command = exe['stop_command']
                command = command.replace('$mig_exe_pgid',
                        "\\\\\`cat %s/%s \\\\\`" % (exe['execution_dir'
                        ], '%s.pgid' % exe['name']))
            else:

                return (False,
                        'stop exe error in resadm.py - pgid in unexpected state: %s!'
                         % pgid)

        # Now insert PGID and run ssh command

        command = command.replace('$mig_exe_pgid', pgid)
        (exit_code, executed_command) = execute_on_resource(command,
                False, resource_config, logger)

        msg = executed_command + '\n' + command + ' returned '\
             + str(exit_code)

        if exit_code == ssh_error_code:
            msg += ssh_error_msg
            return (False, msg)
        else:
            msg += ssh_status_msg
            status = True
            if 'stop' == action:
                pgid_file.seek(0, 0)
                pgid_file.write('stopped\n')

        pgid_file.flush()
        if lock_pgid_file:
            fcntl.flock(pgid_file, fcntl.LOCK_UN)
        pgid_file.close()

        return (status, msg)
    except Exception, err:
        err_msg = action + " of '" + unique_resource_name + "' EXE '"\
             + exe_name + "' failed: " + str(err)
        logger.error(err_msg)
        return (False, err_msg)


def clean_resource_exe(
    unique_resource_name,
    exe_name,
    resource_home,
    logger,
    ):
    """Clean exe node"""

    (status, msg) = resource_exe_action(unique_resource_name, exe_name,
            resource_home, 'clean', logger)
    return (status, msg)


def status_resource_exe(
    unique_resource_name,
    exe_name,
    resource_home,
    logger,
    ):
    """Get exe node status"""

    (status, msg) = resource_exe_action(unique_resource_name, exe_name,
            resource_home, 'status', logger)
    return (status, msg)


def stop_resource_exe(
    unique_resource_name,
    exe_name,
    resource_home,
    logger,
    ):
    """Stop exe node"""

    (status, msg) = resource_exe_action(unique_resource_name, exe_name,
            resource_home, 'stop', logger)
    return (status, msg)


def restart_resource_exe(
    unique_resource_name,
    exe_name,
    resource_home,
    cputime,
    logger,
    ):
    """Restart exe node"""

    (stop_status, stop_msg) = stop_resource_exe(unique_resource_name,
            exe_name, resource_home, logger)
    (start_status, start_msg) = \
        start_resource_exe(unique_resource_name, exe_name,
                           resource_home, cputime, logger)
    return (stop_status and start_status, '%s; %s' % (stop_msg,
            start_msg))


def resource_store_action(
    unique_resource_name,
    store_name,
    resource_home,
    action,
    logger,
    lock_pgid_file=True,
    ):
    """This function handles status and stop for stores"""

    msg = ''

    if not action in ['status', 'stop', 'clean']:
        msg = 'Unknown action: %s' % action
        return (False, msg)

    configuration = get_configuration_object()
    (status, resource_config) = \
        get_resource_configuration(resource_home, unique_resource_name,
                                   logger)
    if not status:
        msg = "No configfile for: '" + unique_resource_name + "'"
        return (False, msg)

    (status, store) = get_resource_store(resource_config, store_name, logger)
    if not status:
        msg = "No STORE config for: '" + unique_resource_name + "' STORE: '"\
             + store_name + "'"
        return (False, msg)

    status = True
    if 'sftp' == store['storage_protocol']:
        setup = {'mount_point': os.path.join(resource_home, unique_resource_name, store_name)}
        if action in ['stop', 'clean']:
            if os.path.ismount(setup['mount_point']):
                for vgrid in store['vgrid']:
                    vgrid_link = os.path.join(configuration.vgrid_files_home, vgrid, "%s_%s" % \
                                              (unique_resource_name, store_name))
                    try:
                        os.remove(vgrid_link)
                    except Exception, exc:
                        msg += ' failed to unlink %s: %s. ' % (vgrid_link, exc)

                command = 'fusermount -u %(mount_point)s' % setup
                parts = command.split()
                msg += 'unmounting with %s. ' % command
                proc = subprocess.Popen(command, shell=True, bufsize=0, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
                exit_code = proc.wait()
                output =  proc.stdout.read()

                msg += '%s returned %s ' % (command, exit_code)

                if exit_code > 0:
                    status = False
                    msg += '(non-zero indicates unmount problems). %s. ' % output
                else:
                    msg += '(0 means success). '
            else:
                msg += 'already unmounted'

            if not store.get('shared_fs', True):

                # execute stop/clean command to clean up remote tunnel or mount

                command = store['%s_command' % action]
                (exit_code, executed_command) = execute_on_resource(command, True,
                                                                        resource_config, logger)
                if exit_code == ssh_error_code:
                    status = False
                    msg += ssh_error_msg
                else:
                    msg += ssh_status_msg
        elif 'status' == action:
            if os.path.ismount(setup['mount_point']):
                msg += 'storage is mounted'
            else:
                msg += 'storage is not mounted'
    else:
        status = False
        msg += 'unsupported storage_protocol: %(storage_protocol)s' % store
    return (status, msg)


def clean_resource_store(
    unique_resource_name,
    store_name,
    resource_home,
    logger,
    ):
    """Clean store node"""

    (status, msg) = resource_store_action(unique_resource_name, store_name,
            resource_home, 'clean', logger)
    return (status, msg)


def status_resource_store(
    unique_resource_name,
    store_name,
    resource_home,
    logger,
    ):
    """Get store node status"""

    (status, msg) = resource_store_action(unique_resource_name, store_name,
            resource_home, 'status', logger)
    return (status, msg)


def stop_resource_store(
    unique_resource_name,
    store_name,
    resource_home,
    logger,
    ):
    """Stop store node"""

    (status, msg) = resource_store_action(unique_resource_name, store_name,
            resource_home, 'stop', logger)
    return (status, msg)


def restart_resource_store(
    unique_resource_name,
    store_name,
    resource_home,
    cputime,
    logger,
    ):
    """Restart store node"""

    (stop_status, stop_msg) = stop_resource_store(unique_resource_name,
            store_name, resource_home, logger)
    (start_status, start_msg) = \
        start_resource_store(unique_resource_name, store_name,
                           resource_home, cputime, logger)
    return (stop_status and start_status, '%s; %s' % (stop_msg,
            start_msg))


def get_sandbox_exe_stop_command(
    sandbox_home,
    sandboxkey,
    exe_name,
    logger,
    ):

    # open the resources configuration

    resource_configuration_file = sandbox_home + '/' + sandboxkey\
         + '/config'
    resource_dict = unpickle(resource_configuration_file, logger)
    if not resource_dict:
        return (False,
                'Could not unpickle resource configuration file: '
                 + resource_configuration_file)

    (status, exe) = get_resource_exe(resource_dict, exe_name, logger)
    if not status:
        msg = "No EXE config for: '"\
             + resource_dict['UNIQUE_RESOURCE_NAME'] + "' EXE: '"\
             + exe_name + "'"
        return (False, msg)

    stop_command = exe['stop_command']

    # Lock pgid file

    pgid_path = os.path.join(sandbox_home, sandboxkey, 'EXE_' + exe_name
                              + '.PGID')
    if os.path.exists(pgid_path):
        pgid_file = open(pgid_path, 'r')
        fcntl.flock(pgid_file, fcntl.LOCK_EX)
        pgid_file.seek(0, 0)
        pgid = pgid_file.readline().strip()
        fcntl.flock(pgid_file, fcntl.LOCK_UN)
        pgid_file.close()
        stop_command = stop_command.replace('$mig_exe_pgid', pgid)
        return (True, stop_command)
    else:
        msg = 'No pgid_path found! File %s' % pgid_path
        return (False, msg)


def status_resource_frontend(unique_resource_name, configuration,
                             logger):
    """Get status for resource front end"""

    return status_resource(unique_resource_name,
                           configuration.resource_home, logger)


def status_resource(unique_resource_name, resource_home, logger):
    """Get status of resource front end"""

    (status, msg) = resource_fe_action(unique_resource_name, '',
            resource_home, 'status', logger)
    return (status, msg)


def clean_resource_frontend(unique_resource_name, resource_home,
                            logger):
    """Clean resource front end"""

    (status, msg) = resource_fe_action(unique_resource_name, '',
            resource_home, 'clean', logger)
    return (status, msg)


def stop_resource_frontend(unique_resource_name, configuration, logger):
    """Stop resource front end"""

    return stop_resource(unique_resource_name,
                         configuration.resource_home, logger)


def stop_resource(unique_resource_name, resource_home, logger):
    """Stop resource front end"""

    (status, msg) = resource_fe_action(unique_resource_name, '',
            resource_home, 'stop', logger)
    return (status, msg)


def restart_resource_frontend(unique_resource_name, configuration,
                              logger):
    """Restart resource front end"""

    return restart_resource(unique_resource_name,
                            configuration.resource_home,
                            configuration.migserver_https_url, logger)


def restart_resource(
    unique_resource_name,
    resource_home,
    https_sid_url,
    logger,
    ):
    """Restart resource front end"""

    (stop_status, stop_msg) = stop_resource(unique_resource_name,
            resource_home, logger)
    (start_status, start_msg) = start_resource(unique_resource_name,
            resource_home, https_sid_url, logger)

    return (stop_status and start_status, '%s; %s' % (stop_msg,
            start_msg))


