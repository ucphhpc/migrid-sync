#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# upload - [insert a few words of module description on this line]
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

import os

# package handling

import zipfile
import tarfile

from shared.validstring import valid_user_path
from shared.fileio import write_file
from shared.job import new_job
from shared.useradm import client_id_dir


def handle_package_upload(
    real_path,
    relative_path,
    client_id,
    configuration,
    submit_mrslfiles,
    dest_path,
    ):
    """ A file package was uploaded (eg. .zip file). Extract the content and
    submit mrsl files if submit_mrsl_files is True
    """

    client_dir = client_id_dir(client_id)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    # Unpack in same directory unless dest_path is given
    
    if not dest_path:
        dest_path = os.path.abspath(os.path.dirname(real_path)) + os.sep
    else:
        dest_path = os.path.abspath(dest_path) + os.sep
    
    msg = ''
    mrslfiles_to_parse = []

    # Handle .zip file

    if real_path.upper().endswith('.ZIP'):
        msg += \
            ".ZIP file '%s' received, it was specified that it should be extracted!\n"\
             % relative_path
        try:
            zip_object = zipfile.ZipFile(real_path, 'r')
        except Exception, exc:
            msg += 'Could not open zipfile! %s' % exc
            return (False, msg)

        for zip_entry in zip_object.infolist():
            msg += 'Extracting: %s\n' % zip_entry.filename

            # write zip_entry to disk

            local_zip_entry_name = os.path.join(dest_path, zip_entry.filename)
            if not valid_user_path(local_zip_entry_name, base_dir):
                msg += \
                    'Are you trying to circumvent permissions on the file system? Do not use .. in the path string!'
                return (False, msg)

            # create sub dir(s) if missing

            zip_entry_dir = os.path.dirname(local_zip_entry_name)

            if not os.path.isdir(zip_entry_dir):
                msg += 'creating dir %s\n' % zip_entry_dir
                try:
                    os.makedirs(zip_entry_dir, 0777)
                except Exception, exc:
                    msg += 'error creating directory %s' % exc
                    return (False, msg)

            # TODO: can we detect and ignore symlinks?
            # Zip format is horribly designed/documented:
            # http://www.pkware.com/documents/casestudies/APPNOTE.TXT
            # I haven't managed to find a way to detect symlinks. Thus
            # they are simply created as files containing the name they
            # were supposed to link to: This is inconsistent but safe :-S

            # write file - symbolic links are written as files! (good for security)

            if not write_file(zip_object.read(zip_entry.filename),
                              local_zip_entry_name,
                              configuration.logger)\
                 and not os.path.exists(zip_object.filename):
                msg += 'error writing file in memory to disk: %s'\
                     % zip_entry.filename
                return (False, msg)

            # get the size as the OS sees it

            try:
                msg += 'Size: %s\n'\
                     % os.path.getsize(local_zip_entry_name)
            except Exception, exc:
                msg += \
                    'File seems to be saved, but could not get file size %s\n'\
                     % exc
                return (False, msg)

            # Check if the extension is .mRSL

            if local_zip_entry_name.upper().endswith('.MRSL'):

                # A .mrsl file was included in the package!

                mrslfiles_to_parse.append(local_zip_entry_name)
    elif real_path.upper().endswith('.TAR.GZ')\
         or real_path.upper().endswith('.TGZ')\
         or real_path.upper().endswith('.TAR.BZ2'):

    # Handle .tar.gz and tar.bz2 files

        if real_path.upper().endswith('.TAR.GZ')\
             or real_path.upper().endswith('.TGZ'):
            msg += \
                ".TAR.GZ file '%s' received, it was specified that it should be extracted!\n"\
                 % relative_path
            try:
                tar_object = tarfile.open(real_path, 'r:gz')
                tar_file_content = tarfile.TarFile.gzopen(real_path)
            except Exception, exc:
                msg += 'Could not open .tar.gz file! %s\n' % exc
                return (False, msg)
        elif real_path.upper().endswith('.TAR.BZ2'):
            msg += \
                ".TAR.BZ2 file '%s' received, it was specified that it should be extracted!\n"\
                 % relative_path
            try:
                tar_object = tarfile.open(real_path, 'r:bz2')
                tar_file_content = tarfile.TarFile.bz2open(real_path)
            except Exception, exc:
                msg += 'Could not open .tar.bz2 file! %s\n' % exc
                return (False, msg)
        else:
            msg += \
                'Internal error, should not be able to enter this else!!'
            return (False, msg)

        for tar_entry in tar_object:
            msg += 'Extracting: %s\n' % tar_entry.name

            # write tar_entry to disk

            local_tar_entry_name = os.path.abspath(base_dir
                     + tar_entry.name)

            if not valid_user_path(local_tar_entry_name, base_dir):
                msg += \
                    'Are you trying to circumvent permissions on the file system? Do not use .. in the path string!\n'
                return (False, msg)

            # create sub dir(s) if missing

            tar_entry_dir = os.path.dirname(local_tar_entry_name)

            if not os.path.isdir(tar_entry_dir):
                msg += 'creating dir %s\n' % tar_entry_dir
                try:
                    os.makedirs(tar_entry_dir, 0777)
                except Exception, exc:
                    msg += 'error creating directory %s\n' % exc
                    return (False, msg)
            if not tar_entry.isreg():

                # not a regular file - symlinks are ignored to avoid illegal access

                msg += 'skipping %s: not a file or directory!\n'\
                     % tar_entry.name
                continue

            # write file!

            if not write_file(tar_file_content.extractfile(tar_entry).read(),
                              local_tar_entry_name,
                              configuration.logger):
                msg += 'error writing file in memory to disk %s\n' % e
                return (False, msg)

            # get the size as the OS sees it

            try:
                msg += 'Size: %s\n'\
                     % os.path.getsize(local_tar_entry_name)
            except Exception, exc:
                msg += \
                    'File seems to be saved, but could not get file size %s\n'\
                     % exc
                return (False, msg)

            # Check if the extension is .mRSL

            if local_tar_entry_name.upper().endswith('.MRSL'):

                # A .mrsl file was included in the package!

                mrslfiles_to_parse.append(local_tar_entry_name)

    # submit mrsl files to the parser. It should be done from within this function to
    # keep the right order if multiple files are created in the html form.

    submitstatuslist = []
    if submit_mrslfiles:

        # Please note that base_dir must end in slash to avoid access to other
        # user dirs when own name is a prefix of another user name

        base_dir = \
            os.path.abspath(os.path.join(configuration.user_home,
                            client_dir)) + os.sep
        for mrslfile in mrslfiles_to_parse:
            (status, parse_msg, job_id) = new_job(mrslfile, client_id,
                    configuration, False, True)
            relative_filename = os.sep + mrslfile.replace(base_dir, '')
            submitstatus = {'object_type': 'submitstatus',
                            'name': relative_filename}
            if not status:
                submitstatus['status'] = False
                submitstatus['job_id'] = job_id
                submitstatus['message'] = parse_msg
            else:

                # msg += "<h2>Failure</h2><br>\n"
                # msg += parse_msg
                # return(False, msg)

                submitstatus['status'] = True
                submitstatus['job_id'] = job_id

            # msg += "<h2>%s Success</h2><br>\n" % mrslfile
            # msg += parse_msg

            submitstatuslist.append(submitstatus)
    return (True, submitstatuslist)


