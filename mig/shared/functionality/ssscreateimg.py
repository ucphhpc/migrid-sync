#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ssscreateimg - Back end to SSS zip generator
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

"""This script generates a sandbox image"""

import os
import time
import tempfile
import shutil
from binascii import hexlify
import fcntl

import shared.confparser as confparser
import shared.resadm as resadm
import shared.returnvalues as returnvalues
from shared.conf import get_resource_configuration, get_resource_exe
from shared.fileio import make_symlink
from shared.functional import validate_input, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.resource import create_resource, remove_resource
from shared.sandbox import load_sandbox_db, save_sandbox_db
from shared.vgrid import vgrid_list_vgrids, default_vgrid

# sandbox db has the format: {username: (password, [list_of_resources])}

PW, RESOURCES = 0, 1


def signature():
    """Signature of the main function"""

    defaults = {'username': REJECT_UNSET,
                'password': REJECT_UNSET,
                'hd_size': REJECT_UNSET,
                'image_format': ['raw'],
                'net_bw': REJECT_UNSET,
                'memory': REJECT_UNSET,
                'operating_system': [''],
                'win_solution': [''],
                'vgrid': [default_vgrid]}
    return ['zip', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_menu=client_id)

    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Screen Saver Sandbox Download'})

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    username = accepted['username'][-1]
    password = accepted['password'][-1]
    hd_size = accepted['hd_size'][-1]
    image_format = accepted['image_format'][-1]
    net_bw = accepted['net_bw'][-1]
    memory = accepted['memory'][-1]
    operating_system = accepted['operating_system'][-1]
    win_solution = accepted['win_solution'][-1]
    vgrid_list = accepted['vgrid']
    ip_address = 'UNKNOWN'
    if os.environ.has_key('REMOTE_ADDR'):
        ip_address = os.environ['REMOTE_ADDR']

    # check that requested image format is valid

    if not image_format in ['raw', 'qcow', 'cow', 'qcow2', 'vmdk']:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Unsupported image format: %s'
                               % image_format})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # check that requested vgrids are valid - anybody can offer their sandbox
    # for a vgrid but it is still left to the vgrid owners to explicitly
    # accept all resources

    (vg_status, all_vgrids) = vgrid_list_vgrids(configuration)
    for vgrid in vgrid_list:
        if not vg_status or not vgrid in all_vgrids:
            output_objects.append({'object_type': 'error_text', 'text'
                              : 'Failed to validate VGrid %s: %s'
                               % (vgrid, all_vgrids)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # Load the user file

    try:
        userdb = load_sandbox_db(configuration)
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Failed to read login info: %s'
                               % exc})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not userdb.has_key(username) or userdb[username][PW] != password:
        output_objects.append({'object_type': 'error_text', 'text'
                               : 'Wrong username or password - please go back and try again...'
                               })
        output_objects.append({'object_type': 'link', 'destination'
                               : 'ssslogin.py', 'text': 'Retry login'
                               })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # provide a resource name

    resource_name = 'sandbox'

    logger.info('''Generating MiG linux sandbox dist with hd size %s and mem
%s for user %s from %s running OS %s ....''' % (hd_size, memory, username,
                                                ip_address, operating_system))

    # Send a request for creating the resource

    (create_status, msg, resource_identifier) = create_resource(
        resource_name, 'SANDBOX_' + username, configuration.resource_home,
                                                         logger)
    if create_status:
        output_objects.append({'object_type': 'text', 'text': msg})
        logger.info('Created MiG sandbox resource request')
    else:
        output_objects.append({'object_type': 'error_text', 'text': msg})
        (remove_status, msg) = remove_resource(configuration.resource_home,
                                               resource_name,
                                               resource_identifier)
        output_objects.append({'object_type': 'text', 'text': msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    unique_host_name = resource_name + '.' + str(resource_identifier)

    # add the resource to the list of the users resources

    userdb[username][1].append(unique_host_name)

    try:
        save_sandbox_db(userdb, configuration)
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Could not update sandbox database: %s' % exc
                               })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.debug('building resource specific files for %s'
                 % unique_host_name)

    sandboxkey = hexlify(open('/dev/urandom').read(32))

    # create sandboxlink

    sandbox_link = configuration.sandbox_home + sandboxkey
    resource_path = os.path.abspath(configuration.resource_home
                                    + unique_host_name)
    make_symlink(resource_path, sandbox_link, logger)

    # change dir to sss_home
    
    old_path = os.getcwd()

    #TODO: We can not rely on chdir to work consistently!
    
    os.chdir(configuration.sss_home)

    # log_dir = "log/"

    # create a resource configuration string that we can write to a file

    res_conf_string = \
    """::MIGUSER::
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
vgrid=%s

"""\
    % (
        resource_name,
        resource_identifier,
        memory,
        int(hd_size) / 1000,
        net_bw,
        str(int(net_bw) / 2),
        sandboxkey,
        unique_host_name,
        unique_host_name,
        ', '.join(vgrid_list),
        )

    # write the conf string to a conf file

    conf_file_src = os.path.join(configuration.resource_home,
                                 unique_host_name, 'config.MiG')
    try:
        fd = open(conf_file_src, 'w')
        fd.write(res_conf_string)
        fd.close()
        logger.debug('wrote conf: %s' % res_conf_string)
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text': err})
        return (output_objects, returnvalues.SYSTEM_ERROR)


    # parse and pickle the conf file

    (status, msg) = confparser.run(conf_file_src, resource_name + '.'
                                   + str(resource_identifier))
    logger.debug('res conf parser returned: %s' % status)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text': msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # read pickled resource conf file (needed to create
    # master_node_script.sh)

    msg = ''
    (status, resource_config) = \
             get_resource_configuration(configuration.resource_home,
                                        unique_host_name, logger)
    logger.debug('got resource conf %s' % resource_config)
    if not resource_config:
        output_objects.append({'object_type': 'error_text', 'text':
                               "No resouce_config for: '%s'" % unique_host_name})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # read pickled exe conf file (needed to create master_node_script.sh)

    (status, exe) = get_resource_exe(resource_config, 'localhost', logger)
    if not exe:
        output_objects.append({'object_type': 'error_text', 'text':
                               "No 'localhost' EXE config for: '%s'" % \
                               unique_host_name})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # HACK: a PGID file is required in the resource home directory
    # write the conf string to a conf file

    
    pgid_file = os.path.join(configuration.resource_home, unique_host_name,
                             'EXE_localhost.PGID')
    try:
        fd = open(pgid_file, 'w')
        fd.write('')
        fd.close()
        logger.debug('wrote fake pgid file %s' % pgid_file)
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text': err})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    os.chdir(old_path)

    resource_dir = os.path.join(configuration.resource_home, unique_host_name)

    # create master_node_script

    try:

        # Securely open a temporary file in resource_dir

        (master_node_script_file, mns_fname) = \
                                  tempfile.mkstemp(dir=resource_dir,
                                                   text=True)
        (master_status, msg) = resadm.fill_master_node_script(
            master_node_script_file, resource_config, exe, 1000)
        if not master_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Filling script failed: %s' % msg})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        os.close(master_node_script_file)
        logger.debug('wrote master node script %s' % mns_fname)
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text':
                                   'Creating script failed: %s' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # create front_end_script

    try:
        (fe_script_file, fes_fname) = tempfile.mkstemp(dir=resource_dir,
                                                       text=True)
        (fe_status, msg) = resadm.fill_frontend_script(
            fe_script_file, configuration.migserver_https_sid_url,
            unique_host_name, resource_config)

        if not fe_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Filling script failed: %s' % msg})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        os.close(fe_script_file)
        logger.debug('wrote frontend script %s' % fes_fname)
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text':
                                   'Creating script failed: %s' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # change directory to sss_home and mount hd image in order to copy
    # the FE-script and masternode script to the hd

    logger.debug('modifying hda image for this sandbox')

    os.chdir(configuration.sss_home)

    lock_path = os.path.join(configuration.sss_home, 'lockfile.txt')
    if not os.path.isfile(lock_path):
        try:
            touch_lockfile = open(lock_path, 'w')
            touch_lockfile.write('this is the lockfile')
            touch_lockfile.close()
        except Exception, exc:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create lock file: %s' % exc})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # ## Enter critical region ###

    lockfile = open(lock_path, 'r+')
    fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)

    # unmount leftover disk image mounts if any

    if os.path.ismount('mnt'):
        logger.warning('unmounting leftover mount point')
        os.system('sync')
        os.system('umount mnt')
        os.system('sync')

    # create individual key files

    try:
        fd = open('keyfile', 'w')
        fd.write(sandboxkey)
        fd.close()
        fd = open('serverfile', 'w')
        fd.write(configuration.migserver_https_sid_url)
        fd.close()
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text':
                                   'Creating script failed: %s' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)


    # use a disk of the requested size

    src_path = os.path.join('MiG-SSS', 'hda_' + hd_size + '.img')
    dst_path = os.path.join('MiG-SSS', 'hda.img')
    command = 'cp -f %s %s' % (src_path, dst_path)
    os.system(command)

    # mount hda and copy scripts to it

    os.system('mount mnt')

    for i in range(60):
        if not os.path.ismount('mnt'):
            logger.warning('waiting for mount point to appear...')
            time.sleep(1)

    if not os.path.ismount('mnt'):
        output_objects.append({'object_type': 'error_text', 'text':
                               'Failed to mount sandbox disk image!'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    failed = False
    try:

        # save master_node_script to hd image

        master_dst = os.path.join('mnt', 'mig', 'MiG', 'mig_exe',
                                  'master_node_script_localhost.sh')
        shutil.copyfile(mns_fname, master_dst)

        # save frontend_script to hd image

        fe_dst = os.path.join('mnt', 'mig', 'MiG', 'mig_frontend',
                                  'frontend_script.sh')
        shutil.copyfile(fes_fname, fe_dst)

        # copy the sandboxkey to the keyfile:

        key_dst = os.path.join('mnt', 'mig', 'etc', 'keyfile')
        shutil.copyfile('keyfile', key_dst)
        server_dst = os.path.join('mnt', 'mig', 'etc', 'serverfile')
        shutil.copyfile('serverfile', server_dst)
    except Exception, err:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Failed to customize image: %s' \
                               % err})
        failed = True

    # unmount disk image

    os.system('sync')
    os.system('umount mnt')
    os.system('sync')    

    for i in range(60):
        if os.path.ismount('mnt'):
            logger.warning('waiting for mount point to disappear...')
            time.sleep(1)

    if failed:
        return (output_objects, returnvalues.SYSTEM_ERROR)


    logger.debug('finished modifying hda image')

    # Optional conversion to requested disk image format

    if 'raw' != image_format:
        logger.debug('Converting disk image to %s format' % image_format)
        image_path = os.path.join('MiG-SSS', 'hda.img')
        tmp_path = image_path + '.' + image_format
        command = 'qemu-img convert -f raw ' + image_path + ' -O '\
                  + image_format + ' ' + tmp_path
        os.system(command)
        os.remove(image_path)
        os.rename(tmp_path, image_path)
        logger.debug('converted hda image to %s format' % image_format)

    file_name = 'MiG-SSS_' + str(resource_identifier) + '.zip'
    if operating_system == 'linux':

        # Put all linux-related files in a zip archive

        os.system('/usr/bin/zip ' + file_name
                  + ' MiG-SSS/MiG.iso MiG-SSS/hda.img MiG-SSS/mig_xsss.py MiG-SSS/readme.txt'
                  )
    else:

        if win_solution == 'screensaver':
            
            # Put all win-related files in the archive (do not store dir
            # name: -j)
            
            os.system('/usr/bin/zip -j ' + file_name
                      + ' MiG-SSS/MiG-SSS_Setup.exe MiG-SSS/hda.img MiG-SSS/MiG.iso'
                      )
        else:

            # windows service
            
            os.system('/usr/bin/zip -j ' + file_name
                      + ' MiG-SSS/MiG-SSS-Service_Setup.exe MiG-SSS/hda.img MiG-SSS/MiG.iso'
                      )

    # ## Leave critical region ###

    lockfile.close()  # unlocks lockfile

    logger.info('Created image and packed files in zip for download')


    ### Everything went as planned - switch to raw output for download

    file_size = os.stat(file_name).st_size
    headers = [('Content-Type', 'application/zip'),
               ('Content-Type', 'application/force-download'),
               ('Content-Type', 'application/octet-stream'),
               ('Content-Type', 'application/download'),
               ('Content-Disposition', 'attachment; filename=%s' % file_name),
               ('Content-Length', '%s' % file_size)]
    output_objects = [{'object_type': 'start', 'headers': headers}]
    fd = open(file_name, 'rb')
    output_objects.append({'object_type': 'binary', 'data': fd.read()})
    fd.close()
    os.system('rm -f ' + file_name)
    return (output_objects, returnvalues.OK)
