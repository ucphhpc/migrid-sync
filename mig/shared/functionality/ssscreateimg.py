#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# ssscreateimg - Back end to SSS zip generator
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

"""This script generates a sandbox image"""

from __future__ import absolute_import

from builtins import range
import os
import time
import tempfile
import shutil
import fcntl

from mig.shared import resadm, returnvalues
from mig.shared.base import hexlify
from mig.shared.conf import get_resource_configuration, get_resource_exe
from mig.shared.defaults import default_vgrid
from mig.shared.fileio import make_symlink, write_zipfile, copy
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.init import initialize_main_variables
from mig.shared.sandbox import load_sandbox_db, save_sandbox_db, \
    create_sss_resource
from mig.shared.safeeval import subprocess_call
from mig.shared.vgridaccess import get_vgrid_map_vgrids

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
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    output_objects.append({'object_type': 'header', 'text': '%s Screen Saver Sandbox Download' %
                           configuration.short_title})
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
    cputime = 1000000
    sandboxkey = hexlify(open('/dev/urandom').read(32))
    ip_address = 'UNKNOWN'
    if 'REMOTE_ADDR' in os.environ:
        ip_address = os.environ['REMOTE_ADDR']

    if not configuration.site_enable_sandboxes:
        output_objects.append({'object_type': 'text', 'text':
                               '''Sandbox resources are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    if not safe_handler(configuration, 'post', op_name, username,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # check that requested image format is valid

    if not image_format in ['raw', 'qcow', 'cow', 'qcow2', 'vmdk']:
        output_objects.append({'object_type': 'error_text', 'text': 'Unsupported image format: %s'
                               % image_format})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # check that requested vgrids are valid - anybody can offer their sandbox
    # for a vgrid but it is still left to the vgrid owners to explicitly
    # accept all resources

    all_vgrids = get_vgrid_map_vgrids(configuration)
    for vgrid in vgrid_list:
        if not vgrid in all_vgrids:
            output_objects.append({'object_type': 'error_text', 'text': 'Failed to validate %s %s: %s'
                                   % (configuration.site_vgrid_label, vgrid,
                                      all_vgrids)})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # Load the user file

    try:
        userdb = load_sandbox_db(configuration)
    except Exception as exc:
        output_objects.append({'object_type': 'error_text', 'text': 'Failed to read login info: %s'
                               % exc})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if username not in userdb or userdb[username][PW] != password:
        output_objects.append({'object_type': 'error_text', 'text': 'Wrong username or password - please go back and try again...'
                               })
        output_objects.append({'object_type': 'link', 'destination': 'ssslogin.py', 'text': 'Retry login'
                               })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # provide a resource name

    resource_name = 'sandbox'

    logger.info('''Generating %s linux sandbox dist with hd size %s and mem
%s for user %s from %s running OS %s ....''' % (configuration.short_title,
                                                hd_size, memory, username,
                                                ip_address, operating_system))

    (create_status, unique_host_name) = create_sss_resource(
        sandboxkey, cputime, memory, hd_size, net_bw, vgrid_list,
        configuration, logger)
    if create_status:
        logger.info('Created sandbox resource configuration')
    else:
        output_objects.append({'object_type': 'error_text', 'text':
                               unique_host_name})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    host_url, resource_identifier = unique_host_name.rsplit('.', 1)

    # add the resource to the list of the users resources

    userdb[username][1].append(unique_host_name)

    try:
        save_sandbox_db(userdb, configuration)
    except Exception as exc:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Could not update sandbox database: %s' % exc
                               })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.debug('building resource specific files for %s'
                 % unique_host_name)

    # create sandboxlink

    sandbox_link = configuration.sandbox_home + sandboxkey
    resource_path = os.path.abspath(configuration.resource_home
                                    + unique_host_name)
    make_symlink(resource_path, sandbox_link, logger)

    # change dir to sss_home

    old_path = os.getcwd()

    # log_dir = "log/"

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
                               "No 'localhost' EXE config for: '%s'" %
                               unique_host_name})
        return (output_objects, returnvalues.SYSTEM_ERROR)

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
    except Exception as err:
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
    except Exception as err:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Creating script failed: %s' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # change directory to sss_home and mount hd image in order to copy
    # the FE-script and masternode script to the hd

    logger.debug('modifying hda image for this sandbox')

    mnt_path = os.path.join(configuration.sss_home, 'mnt')

    lock_path = os.path.join(configuration.sss_home, 'lockfile.txt')
    if not os.path.isfile(lock_path):
        try:
            touch_lockfile = open(lock_path, 'w')
            touch_lockfile.write('this is the lockfile')
            touch_lockfile.close()
        except Exception as exc:
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not create lock file: %s' % exc})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    # ## Enter critical region ###

    lockfile = open(lock_path, 'r+')
    fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)

    # unmount leftover disk image mounts if any

    if os.path.ismount(mnt_path):
        logger.warning('unmounting leftover mount point')
        # NOTE: we don't need explicit shell here
        subprocess_call('sync')
        subprocess_call(['umount', mnt_path])
        subprocess_call('sync')

    # create individual key files

    try:
        key_path = os.path.join(configuration.sss_home, 'keyfile')
        server_path = os.path.join(configuration.sss_home, 'serverfile')
        fd = open(key_path, 'w')
        fd.write(sandboxkey)
        fd.close()
        fd = open(server_path, 'w')
        fd.write(configuration.migserver_https_sid_url)
        fd.close()
    except Exception as err:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Creating script failed: %s' % msg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # use a disk of the requested size

    src_path = os.path.join(configuration.sss_home, 'MiG-SSS',
                            'hda_' + hd_size + '.img')
    dst_path = os.path.join(configuration.sss_home, 'MiG-SSS', 'hda.img')
    copy(src_path, dst_path)

    # mount hda and copy scripts to it

    logger.info('calling mount %s' % mnt_path)
    # NOTE: we don't need explicit shell here
    subprocess_call(['mount', mnt_path])

    for i in range(60):
        if not os.path.ismount(mnt_path):
            logger.warning('waiting for mount point to appear...')
            time.sleep(1)

    if not os.path.ismount(mnt_path):
        output_objects.append({'object_type': 'error_text', 'text':
                               'Failed to mount sandbox disk image!'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    failed = False
    try:

        # save master_node_script to hd image

        master_dst = os.path.join(mnt_path, 'mig', 'MiG', 'mig_exe',
                                  'master_node_script_localhost.sh')
        shutil.copyfile(mns_fname, master_dst)

        # save frontend_script to hd image

        fe_dst = os.path.join(mnt_path, 'mig', 'MiG', 'mig_frontend',
                              'frontend_script.sh')
        shutil.copyfile(fes_fname, fe_dst)

        # copy the sandboxkey to the keyfile:

        key_dst = os.path.join(mnt_path, 'mig', 'etc', 'keyfile')
        shutil.copyfile(os.path.join(configuration.sss_home, 'keyfile'),
                        key_dst)
        server_dst = os.path.join(mnt_path, 'mig', 'etc', 'serverfile')
        shutil.copyfile(os.path.join(configuration.sss_home, 'serverfile'),
                        server_dst)
    except Exception as err:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Failed to customize image: %s'
                               % err})
        failed = True

    # unmount disk image

    # NOTE: we don't need explicit shell here
    subprocess_call('sync')
    subprocess_call(['umount', mnt_path])
    subprocess_call('sync')

    for i in range(60):
        if os.path.ismount(mnt_path):
            logger.warning('waiting for mount point to disappear...')
            time.sleep(1)

    if failed:
        return (output_objects, returnvalues.SYSTEM_ERROR)

    logger.debug('finished modifying hda image')

    # Optional conversion to requested disk image format

    if 'raw' != image_format:
        logger.debug('Converting disk image to %s format' % image_format)
        image_path = os.path.join(configuration.sss_home, 'MiG-SSS', 'hda.img')
        tmp_path = image_path + '.' + image_format
        command_list = ['qemu-img', 'convert', '-f raw', image_path, '-O',
                        image_format, tmp_path]
        command = ' '.join(command_list)
        # NOTE: we use command list to avoid shell requirement here
        subprocess_call(command_list)
        os.remove(image_path)
        os.rename(tmp_path, image_path)
        logger.debug('converted hda image to %s format' % image_format)

    zip_path = os.path.join(configuration.sss_home,
                            'MiG-SSS_%d' % resource_identifier + '.zip')
    iso_path = os.path.join(configuration.sss_home, 'MiG-SSS', 'MiG.iso')
    img_path = os.path.join(configuration.sss_home, 'MiG-SSS', 'hda.img')
    xsss_path = os.path.join(configuration.sss_home, 'MiG-SSS', 'mig_xsss.py')
    readme_path = os.path.join(configuration.sss_home, 'MiG-SSS', 'readme.txt')
    setup_path = os.path.join(configuration.sss_home, 'MiG-SSS',
                              'MiG-SSS_Setup.exe')
    service_path = os.path.join(configuration.sss_home, 'MiG-SSS',
                                'MiG-SSS-Service_Setup.exe')
    if operating_system == 'linux':

        # Put all linux-related files in a zip archive

        (zip_status, zip_msg) = write_zipfile(zip_path,
                                              [iso_path, img_path, xsss_path,
                                               readme_path],
                                              'MiG-SSS')
        if not zip_status:
            logger.error('Failed to create zip file: %s' % zip_msg)

    else:

        if win_solution == 'screensaver':

            # Put all win-related files in the archive (do not store dir
            # name: -j)

            (zip_status, zip_msg) = write_zipfile(zip_path, [setup_path,
                                                             iso_path,
                                                             img_path], '')
        else:

            # windows service

            (zip_status, zip_msg) = write_zipfile(zip_path, [service_path,
                                                             iso_path,
                                                             img_path], '')

    # ## Leave critical region ###

    lockfile.close()  # unlocks lockfile

    logger.info('Created image and packed files in zip for download')

    # Everything went as planned - switch to raw output for download

    file_size = os.stat(zip_path).st_size
    headers = [('Content-Type', 'application/zip'),
               ('Content-Type', 'application/force-download'),
               ('Content-Type', 'application/octet-stream'),
               ('Content-Type', 'application/download'),
               ('Content-Disposition', 'attachment; filename=%s' %
                os.path.basename(zip_path)),
               ('Content-Length', '%s' % file_size)]
    output_objects = [{'object_type': 'start', 'headers': headers}]
    fd = open(zip_path, 'rb')
    output_objects.append({'object_type': 'binary', 'data': fd.read()})
    fd.close()
    os.remove(zip_path)
    return (output_objects, returnvalues.OK)
