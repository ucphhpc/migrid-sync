#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ssh - remote command wrappers using ssh/scp
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

"""SSH based remote operations"""

from __future__ import print_function
from __future__ import absolute_import

from builtins import oct
from builtins import range
from io import BytesIO as LegacyStringIO
import base64
import os
import sys
import tempfile

# NOTE: we would prefer the modern io.BytesIO but it fails in python2 during
#       rsa_key.write_private_key(string_io_obj) with a Paramiko error:
#       TypeError: 'unicode' does not have the buffer interface
try:
    from cStringIO import StringIO as LegacyStringIO
except ImportError:
    from io import BytesIO as LegacyStringIO

try:
    import paramiko
except ImportError:
    # Paramiko not available - imported fom griddaemons so fail gracefully
    paramiko = None

from mig.shared.base import client_id_dir, force_utf8
from mig.shared.conf import get_resource_exe, get_configuration_object
from mig.shared.defaults import ssh_conf_dir
from mig.shared.safeeval import subprocess_popen, subprocess_pipe


def parse_pub_key(public_key):
    """Parse public_key string to paramiko key.
    Throws exception if key is broken.
    """
    if paramiko is None:
        raise Exception("You need paramiko to use ssh with public keys")
    public_key_elms = public_key.split(' ')

    # Either we have 'from' or 'ssh-' as first element

    if len(public_key_elms) > 0 and \
            public_key_elms[0].startswith('ssh-'):
        ssh_type_idx = 0
    elif len(public_key_elms) > 1 and \
            public_key_elms[1].startwith('ssh-'):
        ssh_type_idx = 1
    else:
        msg = 'Invalid ssh public key: (%s)' % public_key
        raise ValueError(msg)

    head, tail = public_key.split(' ')[ssh_type_idx:2+ssh_type_idx]
    bits = base64.b64decode(tail)
    msg = paramiko.Message(bits)
    if head == 'ssh-rsa':
        parse_key = paramiko.RSAKey
    elif head == 'ssh-dss':
        parse_key = paramiko.DSSKey
    elif head == 'ssh-ecdsa':
        parse_key = paramiko.ECDSAKey
    elif head == 'ssh-ed25519':
        # NOTE: this may or may not be supported depending on paramiko stack
        parse_key = getattr(paramiko, 'Ed25519Key', paramiko.RSAKey)
    else:
        # Try RSA for unknown key types
        parse_key = paramiko.RSAKey
    return parse_key(msg)


def default_ssh_options(close_stdin=False, x_forward=False):
    """Default list of options for ssh connections"""

    options = []
    if close_stdin:
        # No stdin, to let ssh exit cleanly
        options.append('-n')
    if x_forward:
        options.append('-X')

    # No interaction
    options += ['-o', 'BatchMode=yes']

    # We need fault tolerance but can't block e.g. grid_script for long

    options += ['-o', 'ConnectionAttempts=2']
    options += ['-o', 'ConnectTimeout=10']
    return options


def copy_file_to_resource(
    local_path,
    dest_path,
    resource_config,
    logger,
):
    """Copy local_path to dest_path relative to resource home on resource
    using scp.
    """

    configuration = get_configuration_object()
    local_filename = os.path.basename(local_path)
    multiplex = '0'
    if 'SSHMULTIPLEX' in resource_config:
        multiplex = "%(SSHMULTIPLEX)s" % resource_config
    hostkey = resource_config['HOSTKEY']
    host = resource_config['HOSTURL']
    identifier = resource_config['HOSTIDENTIFIER']
    unique_id = '%s.%s' % (host, identifier)
    res_dir = os.path.join(configuration.resource_home, unique_id)
    port = resource_config['SSHPORT']
    user = resource_config['MIGUSER']

    if dest_path.startswith(os.sep):
        logger.warning('copy_file_to_resource: force relative dest path!'
                       )
        dest_path = dest_path.lstrip(os.sep)

    # create known-hosts file with only the resources hostkey (could
    # this be avoided and just passed as an argument?)

    try:

        # TODO: no need to write this known host file again every time!
        #       keep it in res_dir and only write if config is newer

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
    except Exception as err:
        logger.error('could not write single_known_hosts %s (%s)'
                     % (host, err))

    options = default_ssh_options()
    if '0' != multiplex:
        options += ['-o', 'ControlPath=%s/ssh-multiplexing' % res_dir]
    options += ['-o', 'Port=%s' % port, '-o', 'CheckHostIP=yes',
                '-o', 'StrictHostKeyChecking=yes']
    if hostkey:
        options += ['-o', 'UserKnownHostsFile=' + key_path]

    abs_dest_path = os.path.join(resource_config['RESOURCEHOME'], dest_path)
    scp_command_list = ['scp'] + options + [local_path] + \
                       ['%s@%s:%s' % (user, host, abs_dest_path)]
    scp_command = ' '.join(scp_command_list)
    logger.debug('running command: %s' % scp_command)
    # NOTE: we use scp command list here to avoid shell requirement
    scp_proc = subprocess_popen(scp_command_list,
                                stdin=open("/dev/null", "r"),
                                stdout=open("/dev/null", "w"),
                                stderr=subprocess_pipe,
                                )
    status = scp_proc.wait()
    _, err_msg = scp_proc.communicate()

    # Remove temp file no matter what scp_command returned

    try:
        os.remove(key_path)
    except Exception as err:
        logger.error('could not remove %s (%s)' % (key_path, err))

    if status != 0:

        # File was not sent!! Take action

        logger.error('%s returned %s: %s' % (scp_command, status, err_msg))
        err_path = '%s/scp.err' % configuration.log_dir
        try:
            err_fd = open(err_path, 'a')
            err_fd.write(err_msg)
            err_fd.close()
        except Exception as exc:
            logger.error("failed to write scp err log: %s" % exc)

        return False

    logger.debug('scp %s to %s succeeded' % (local_filename, host))
    return True


def copy_file_to_exe(
    local_path,
    dest_path,
    resource_config,
    exe_name,
    logger,
):
    """Copy local_path to dest_path relative to execution_dir on
    exe_name. This needs to go through the resource front end using scp
    and the copy method to the exe depends on the shared fs setting.
    """

    local_filename = os.path.basename(local_path)
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

    copy_attempts = 3
    for attempt in range(copy_attempts):
        copy_status = copy_file_to_resource(local_path, dest_path,
                                            resource_config, logger)
        if not copy_status:
            logger.warning('scp of %s failed in attempt %d of %d'
                           % (local_path, attempt, copy_attempts))
        else:
            break

    # Remove temporary file no matter what scp returned

    try:
        os.remove(local_path)
    except Exception as err:
        logger.error('Could not remove %s (%s)' % (local_path, err))

    if copy_status:
        logger.debug('scp of %s was successful.' % local_path)
    else:
        logger.error('scp of %s was NOT successful!' % local_path)
        msg += 'scp of %s was NOT successful!\n' % local_filename
        return (False, msg)

    # copy file to exe - trailing slash is important

    if 'shared_fs' in exe and exe['shared_fs']:
        ssh_command = 'cp %s %s/' % \
                      (os.path.join(resource_config['RESOURCEHOME'],
                                    dest_path), exe['execution_dir'])
    else:

        # We do not have exe host keys and don't really care about auth there

        ssh_command = 'scp %s %s %s@%s:%s/' % \
                      (' '.join(default_ssh_options()),
                       os.path.join(resource_config['RESOURCEHOME'],
                                    dest_path), exe['execution_user'],
                       exe['execution_node'], exe['execution_dir'])

    copy_attempts = 3
    for attempt in range(copy_attempts):
        (status, executed_command) = execute_on_resource(ssh_command, False,
                                                         resource_config,
                                                         logger)
        if status != 0:
            logger.warning('copy of %s to exe failed (%d) in attempt %d of %d'
                           % (local_path, status, attempt, copy_attempts))
        else:
            break

    if 0 != status:
        logger.error('%s not copied to exe!' % local_path)
        logger.error('failed copy command was:\n%s' % executed_command)
        msg += '%s not copied to exe:\n%s\nexit code %s' % \
               (local_filename, executed_command, status)
        return (False, msg)
    else:
        logger.debug('%s copied to exe' % local_path)
        return (True, '')


def execute_on_resource(
    command,
    background,
    resource_config,
    logger,
):
    """Execute command on resource.
    IMPORTANT: we expect command to be trusted here. I.e. it must contain
    *only* hard-coded strings and variables we already parsed and sanitized,
    like resource conf values and strictly verified user input. This was
    verified to be the case on January 8, 2016. Please keep it so!
    """

    configuration = get_configuration_object()
    hostkey = resource_config['HOSTKEY']
    host = resource_config['HOSTURL']
    port = resource_config['SSHPORT']
    user = resource_config['MIGUSER']
    job_type = 'batch'
    if 'JOBTYPE' in resource_config:
        job_type = resource_config['JOBTYPE']
    multiplex = '0'
    if 'SSHMULTIPLEX' in resource_config:
        multiplex = "%(SSHMULTIPLEX)s" % resource_config

    # Use manually added SSHMULTIPLEXMASTER variable to only run master
    # from sessions initiated by grid_sshmux.py: There's a race in the
    # handling of ControlMaster=auto in openssh-4.3 resulting in error:
    # ControlSocket $SOCKET already exists
    # (see http://article.gmane.org/gmane.network.openssh.devel/13839)

    multiplex_master = False
    if 'SSHMULTIPLEXMASTER' in resource_config:
        multiplex_master = bool(resource_config['SSHMULTIPLEXMASTER'])
    identifier = resource_config['HOSTIDENTIFIER']
    unique_id = '%s.%s' % (host, identifier)
    res_dir = os.path.join(configuration.resource_home, unique_id)

    # fname should be unique to avoid race conditions, since several
    # cgi-scripts may run at the same time due to a multi process
    # or multi thread web server

    try:

        # TODO: no need to write this known host file again every time!
        #       keep it in res_dir and only write if config is newer

        # Securely open a temporary file in resource dir
        # Please note that mkstemp uses os.open() style rather
        # than open()

        (filehandle, key_path) = tempfile.mkstemp(dir=res_dir,
                                                  text=True)
        os.write(filehandle, hostkey)
        os.close(filehandle)
        logger.debug('wrote hostkey %s to %s' % (hostkey, key_path))
    except Exception as err:
        logger.error('could not write tmp host key file (%s)' % err)
        return (-1, '')

    # Only enable X forwarding for interactive resources (i.e. job_type
    # 'interactive' or 'all')

    x_fwd = False
    if 'batch' != job_type.lower():
        x_fwd = True

    options = default_ssh_options(close_stdin=True, x_forward=x_fwd)
    options += ['-o', 'Port=%s' % port, '-o', 'CheckHostIP=yes',
                '-o', 'StrictHostKeyChecking=yes']

    if hostkey:
        options += ['-o', 'UserKnownHostsFile=%s' % key_path]

    if '0' != multiplex:
        options += ['-o', 'ControlPath=%s/ssh-multiplexing' % res_dir]

        # Only open a new control socket if explicitly told so:
        # All other invocations will reuse it if possible.

        if multiplex_master:
            options += ['-o', 'ControlMaster=yes']

    redirect, batch = [], []
    redirect.append('1> /dev/null')
    redirect.append('2> /dev/null')
    if background:
        batch.append('&')

    # IMPORTANT: careful with the ssh_command line!
    # removing explicit bash or changing escapes breaks resource management

    remote_command = ["bash", "-c", "'%s %s'" % (command, ' '.join(batch))]

    ssh_command_list = ['ssh'] + options + ['%s@%s' % (user, host)] + \
        remote_command + ['%s' % ' '.join(redirect)]
    ssh_command = ' '.join(ssh_command_list)
    logger.debug('running command: %s' % ssh_command_list)
    # NOTE: we use ssh command list here to avoid shell requirement
    ssh_proc = subprocess_popen(ssh_command_list,
                                stdin=open("/dev/null", "r"),
                                stdout=subprocess_pipe,
                                stderr=subprocess_pipe
                                )
    status = ssh_proc.wait()
    out_msg, err_msg = ssh_proc.communicate()

    logger.debug('command out: %s' % out_msg)
    logger.debug('command err: %s' % err_msg)

    logger.debug('cleaning up after command')

    # Remove temp file no matter what ssh command returned

    try:
        os.remove(key_path)
    except Exception as err:
        logger.error('Could not remove hostkey file %s: %s'
                     % (key_path, err))

    if 0 != status:

        # Command was not executed with return code 0!! Take action

        logger.error('%s returned %s:\n%s' % (ssh_command, status, err_msg))
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
    """Execute command (through resource) on exe.
    Please see the note in execute_on_resource!
    """

    node = exe_config['execution_node']
    user = exe_config['execution_user']
    options = default_ssh_options(close_stdin=True, x_forward=True)

    # This command should already be properly escaped by the apostrophes
    # in the execute_on_resource call

    # TODO: it would make sense to move bash call into nested command
    # when called through execute_on_resource, but the following fails.
    #redirect, batch = [], []
    ##redirect.append('< /dev/null')
    #redirect.append('1> /dev/null')
    #redirect.append('2> /dev/null')
    # if background:
    #    batch.append('&')
    # ssh_command = "ssh %s %s@%s bash -c '%s %s' %s" % (' '.join(options), user,
    #        node, command, ' '.join(batch), ' '.join(redirect))

    ssh_command = 'ssh %s %s@%s "%s"' % (' '.join(options), user,
                                         node, command)
    logger.debug(ssh_command)
    return execute_on_resource(ssh_command, background,
                               resource_config, logger)


def execute_on_store(
    command,
    background,
    resource_config,
    store_config,
    logger,
):
    """Execute command (through resource) on store.
    Please see the note in execute_on_resource!
    """

    node = store_config['storage_node']
    user = store_config['storage_user']
    options = default_ssh_options(close_stdin=True, x_forward=True)

    # This command should already be properly escaped by the apostrophes
    # in the execute_on_resource call

    ssh_command = 'ssh %s %s@%s "%s"' % (' '.join(options), user,
                                         node, command)
    logger.debug(ssh_command)
    return execute_on_resource(ssh_command, background,
                               resource_config, logger)


def generate_ssh_rsa_key_pair(size=2048, public_key_prefix='',
                              public_key_postfix='', encode_utf8=False):
    """Generates ssh rsa key pair"""

    if paramiko is None:
        raise Exception("You need paramiko to provide the ssh/sftp service")
    rsa_key = paramiko.RSAKey.generate(size)

    string_io_obj = LegacyStringIO()
    rsa_key.write_private_key(string_io_obj)

    private_key = string_io_obj.getvalue()
    public_key = ("%s ssh-rsa %s %s" % (public_key_prefix,
                                        rsa_key.get_base64(),
                                        public_key_postfix)).strip()
    if encode_utf8:
        private_key = force_utf8(private_key)
        public_key = force_utf8(public_key)

    return (private_key, public_key)


def tighten_key_perms(configuration, client_id, keys_dirname=ssh_conf_dir):
    """Make sure permissions on client home and keys_dirname there are tight
    enough for sshd not to complain. In practice umask 022 or larger must be
    enforced all the way up to first root owned parent dir.
    """
    _logger = configuration.logger
    client_dir = client_id_dir(client_id)
    # NOTE: first remove any trailing slashes for dirname to be consistent
    user_base_dir = configuration.user_home.rstrip(os.sep)
    state_base_dir = os.path.dirname(user_base_dir)
    user_home_dir = os.path.join(user_base_dir, client_dir)
    user_ssh_dir = os.path.join(user_home_dir, keys_dirname)

    # Check for correct permissions (umask >= 022) on ssh dir and parents
    check_dirs = [state_base_dir, user_base_dir, user_home_dir, user_ssh_dir]
    fixed_dirs = []
    for path in check_dirs:
        # check perms and limit if needed
        if os.path.exists(path) and os.stat(path).st_mode & 0o22:
            old_perm = os.stat(path).st_mode & 0o777
            limit_perm = old_perm & 0o755
            _logger.warning("%s has invalid ssh permissions %s, reset to %s"
                            % (path, oct(old_perm), oct(limit_perm)))
            os.chmod(path, limit_perm)
            fixed_dirs.append(path)
    return fixed_dirs


if __name__ == "__main__":
    from mig.shared.conf import get_resource_configuration
    unique_resource_name = 'localhost.0'
    exe_name = 'localhost'
    if sys.argv[1:]:
        unique_resource_name = sys.argv[1]
    if sys.argv[2:]:
        exe_name = sys.argv[2]
    print("running ssh unit tests against %s" % unique_resource_name)
    configuration = get_configuration_object()
    logger = configuration.logger
    filename = '/tmp/localdummy'
    dummy_fd = open(filename, "w")
    dummy_fd.write("sample text\n")
    dummy_fd.close()
    res_path = 'res-' + os.path.basename(filename)
    exe_path = 'exe-' + os.path.basename(filename)
    (res_status, resource_config) = \
        get_resource_configuration(configuration.resource_home,
                                   unique_resource_name, logger)
    (exe_status, exe_config) = get_resource_exe(
        resource_config, exe_name, logger)
    if not res_status:
        print("Failed to extract resource config for %s: %s" %
              (unique_resource_name, resource_config))
        sys.exit(1)
    if not exe_status:
        print("Failed to extract exe config for %s: %s" %
              (exe_name, exe_config))
        sys.exit(1)
    copy_res = copy_file_to_resource(filename, res_path, resource_config,
                                     logger)
    print("copy %s to %s on %s success: %s" % (filename, res_path,
                                               unique_resource_name, copy_res))
    command = "ls"
    print("Execute %s on %s" % (command, unique_resource_name))
    (exec_res, exec_msg) = execute_on_resource(command, False, resource_config,
                                               logger)
    print(" success: %s\n%s" % (exec_res, exec_msg))
    command = "uname -a && sleep 13"
    print("bg exec %s on %s" % (command, unique_resource_name))
    (exec_res, exec_msg) = execute_on_resource(command, True, resource_config,
                                               logger)
    print(" success: %s\n%s" % (exec_res, exec_msg))

    command = "mkdir -p %s" % exe_config['execution_dir']
    print("Execute %s on %s_%s" % (command, unique_resource_name,
                                   exe_config['name']))
    (exec_res, exec_msg) = execute_on_exe(command, False, resource_config,
                                          exe_config, logger)
    print(" success: %s\n%s" % (exec_res, exec_msg))
    copy_res = copy_file_to_exe(filename, exe_path, resource_config, exe_name,
                                logger)
    print("copy %s to %s on %s success: %s" % (filename, exe_path,
                                               unique_resource_name, copy_res))
    command = "ls"
    print("Execute %s on %s" % (command, unique_resource_name))
    (exec_res, exec_msg) = execute_on_exe(command, False, resource_config,
                                          exe_config, logger)
    print(" success: %s\n%s" % (exec_res, exec_msg))
    command = "uname -a && sleep 13"
    print("bg exec %s on %s_%s" % (command, unique_resource_name, exe_name))
    (exec_res, exec_msg) = execute_on_exe(command, True, resource_config,
                                          exe_config, logger)
    print(" success: %s\n%s" % (exec_res, exec_msg))

    # NOTE: emulate res adm status with conf calls on resource *FE*
    command = "%(status_command)s" % exe_config
    command = command.replace('$mig_exe_pgid', "$(cat %s/%s)" %
                              (exe_config['execution_dir'], '%s.pgid' %
                               exe_config['name']))
    print("Execute %s on %s" % (command, unique_resource_name))
    (exec_res, exec_msg) = execute_on_resource(command, False, resource_config,
                                               logger)
    print(" success: %s\n%s" % (exec_res, exec_msg))
