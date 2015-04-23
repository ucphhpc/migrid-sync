#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# archives - zip/tar packing and unpacking helpers
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

"""Helpers for zip/tar archive packing and unpacking"""

import os
import zipfile
import tarfile

from shared.base import client_id_dir, invisible_path
from shared.fileio import write_file
from shared.job import new_job
from shared.safeinput import valid_user_path_name


def handle_package_upload(
    real_src,
    relative_src,
    client_id,
    configuration,
    submit_mrslfiles,
    dst,
    ):
    """A file package was uploaded (eg. .zip file). Extract the content and
    submit mrsl files if submit_mrsl_files is True.
    """
    logger = configuration.logger
    msg = ''
    logger.info("handle_package_upload %s %s %s" % \
                (real_src, relative_src, dst))

    client_dir = client_id_dir(client_id)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    # Unpack in same directory unless real_dst is given

    if not dst:
        real_dst = os.path.abspath(os.path.dirname(real_src))
    elif os.path.isabs(dst):
        real_dst = os.path.abspath(dst)
    else:
        real_dst = os.path.join(base_dir, dst)
    real_dst += os.sep
    mrslfiles_to_parse = []

    real_src_lower = real_src.lower()
    if real_src_lower.endswith('.zip'):

        # Handle .zip file

        msg += """.zip file '%s' received, it was specified that it should be
extracted!
""" % relative_src
        try:
            zip_object = zipfile.ZipFile(real_src, 'r')
        except Exception, exc:
            logger.error("open zip failed: %s" % exc)
            msg += 'Could not open zipfile! %s' % exc
            return (False, msg)

        logger.info("unpack entries of %s to %s" % \
                                  (real_src, real_dst))
        for zip_entry in zip_object.infolist():
            msg += 'Extracting: %s\n' % zip_entry.filename

            # write zip_entry to disk

            local_zip_entry_name = os.path.join(real_dst, zip_entry.filename)
            valid_status, valid_err = valid_user_path_name(
                zip_entry.filename, local_zip_entry_name, base_dir)
            if not valid_status:
                return (valid_status, valid_err)

            # create sub dir(s) if missing

            zip_entry_dir = os.path.dirname(local_zip_entry_name)

            if not os.path.isdir(zip_entry_dir):
                msg += 'creating dir %s\n' % zip_entry_dir
                try:
                    os.makedirs(zip_entry_dir, 0775)
                except Exception, exc:
                    logger.error("create directory failed: %s" % exc)
                    msg += 'error creating directory %s' % exc
                    return (False, msg)

            if os.path.isdir(local_zip_entry_name):
                logger.info("nothing more to do for dir entry: %s" % \
                            local_zip_entry_name)
                continue

            # TODO: can we detect and ignore symlinks?
            # Zip format is horribly designed/documented:
            # http://www.pkware.com/documents/casestudies/APPNOTE.TXT
            # I haven't managed to find a way to detect symlinks. Thus
            # they are simply created as files containing the name they
            # were supposed to link to: This is inconsistent but safe :-S

            # write file - symbolic links are written as files! (good for
            # security)

            if not not write_file(zip_object.read(zip_entry.filename),
                              local_zip_entry_name,
                              logger)\
                 and not os.path.exists(zip_object.filename):
                msg += 'error writing file in memory to disk: %s'\
                     % zip_entry.filename
                return (False, msg)

            # get the size as the OS sees it

            try:
                msg += 'Size: %s\n'\
                     % os.path.getsize(local_zip_entry_name)
            except Exception, exc:
                logger.warning("unpack may have failed: %s" % exc)
                msg += \
                    'File seems to be saved, but could not get file size %s\n'\
                     % exc
                return (False, msg)

            # Check if the extension is .mRSL

            if local_zip_entry_name.upper().endswith('.MRSL'):

                # A .mrsl file was included in the package!

                mrslfiles_to_parse.append(local_zip_entry_name)
    elif real_src_lower.endswith('.tar') or \
             real_src_lower.endswith('.tar.gz') or \
             real_src_lower.endswith('.tgz') or \
             real_src_lower.endswith('.tar.bz2')  or \
             real_src_lower.endswith('.tbz'):

        # Handle possibly compressed .tar files
        
        if real_src_lower.endswith('.tar.gz') or \
               real_src_lower.endswith('.tgz'):
            msg += """.tar.gz file '%s' received, it was specified that it
should be extracted!
""" % relative_src
            try:
                tar_object = tarfile.open(real_src, 'r:gz')
                tar_file_content = tarfile.TarFile.gzopen(real_src)
            except Exception, exc:
                logger.error("open tar gz failed: %s" % exc)
                msg += 'Could not open .tar.gz file! %s\n' % exc
                return (False, msg)
        elif real_src_lower.endswith('.tar.bz2') or \
                 real_src_lower.endswith('.tbz'):
            msg += """.tar.bz2 file '%s' received, it was specified that it
should be extracted!
""" % relative_src
            try:
                tar_object = tarfile.open(real_src, 'r:bz2')
                tar_file_content = tarfile.TarFile.bz2open(real_src)
            except Exception, exc:
                logger.error("open tar bz failed: %s" % exc)
                msg += 'Could not open .tar.bz2 file! %s\n' % exc
                return (False, msg)
        else:
            try:
                tar_object = tarfile.open(real_src, 'r')
                tar_file_content = tarfile.TarFile.open(real_src)
            except Exception, exc:
                logger.error("open tar failed: %s" % exc)
                msg += 'Could not open .tar file! %s\n' % exc
                return (False, msg)

        logger.info("unpack entries of %s to %s" % \
                                  (real_src, real_dst))
        for tar_entry in tar_object:
            msg += 'Extracting: %s\n' % tar_entry.name

            # write tar_entry to disk

            local_tar_entry_name = os.path.join(real_dst, tar_entry.name)

            valid_status, valid_err = valid_user_path_name(
                tar_entry.name, local_tar_entry_name, base_dir)
            if not valid_status:
                return (valid_status, valid_err)

            # Found empty dir - make sure  dirname doesn't strip to parent

            if tar_entry.isdir():
                logger.info("empty dir %s - include in parent creation" % \
                            local_tar_entry_name)
                local_tar_entry_name += os.sep

            # create sub dir(s) if missing

            tar_entry_dir = os.path.dirname(local_tar_entry_name)

            if not os.path.isdir(tar_entry_dir):
                logger.info("make tar parent dir: %s" % tar_entry_dir)
                msg += 'creating dir %s\n' % tar_entry_dir
                try:
                    os.makedirs(tar_entry_dir, 0775)
                except Exception, exc:
                    logger.error("create directory failed: %s" % exc)
                    msg += 'error creating directory %s\n' % exc
                    return (False, msg)
            if not tar_entry.isfile():

                # not a regular file - symlinks are ignored to avoid illegal
                # access

                msg += 'skipping %s: not a file or directory!\n'\
                     % tar_entry.name
                continue

            # write file!

            if not write_file(tar_file_content.extractfile(tar_entry).read(),
                              local_tar_entry_name,
                              logger):
                msg += 'error writing file in memory to disk\n'
                return (False, msg)

            # get the size as the OS sees it

            try:
                msg += 'Size: %s\n'\
                     % os.path.getsize(local_tar_entry_name)
            except Exception, exc:
                logger.warning("file save may have failed: %s" % exc)
                msg += \
                    'File seems to be saved, but could not get file size %s\n'\
                     % exc
                return (False, msg)

            # Check if the extension is .mRSL

            if local_tar_entry_name.upper().endswith('.MRSL'):

                # A .mrsl file was included in the package!

                mrslfiles_to_parse.append(local_tar_entry_name)

    # submit mrsl files to the parser. It should be done from within this
    # function to keep the right order if multiple files are created in the
    # html form.

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


def unpack_archive(
    configuration,
    client_id,
    src,
    dst,
    ):
    """Inside the user home of client_id: unpack the src zip or tar
    archive into the dst dir. Both src and dst are expected to be relative
    paths.
    Please note that src and dst should be checked for illegal directory
    traversal attempts before getting here.
    """
    client_dir = client_id_dir(client_id)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep
    real_src = os.path.join(base_dir, src.lstrip(os.sep))
    return handle_package_upload(real_src, src, client_id,
                                 configuration, False, dst)


def pack_archive(
    configuration,
    client_id,
    src,
    dst,
    ):
    """Inside the user home of client_id: pack the src_path into a zip or tar
    archive in dst. Both src and dst are expected to be relative
    paths.
    Please note that src and dst should be checked for illegal directory
    traversal attempts before getting here.
    """
    logger = configuration.logger
    msg = ''
    client_dir = client_id_dir(client_id)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep
    real_src = os.path.join(base_dir, src.lstrip(os.sep))
    real_dst = os.path.join(base_dir, dst.lstrip(os.sep))

    # Pack in same path with zip extension unless dst is given
    
    if not dst:
        real_dst = real_src + '.zip'

    # create sub dir(s) if missing

    zip_entry_dir = os.path.dirname(real_dst)
    if not os.path.isdir(zip_entry_dir):
        logger.info("make zip parent dir: %s" % zip_entry_dir)
        msg += 'creating dir %s\n' % zip_entry_dir
        try:
            os.makedirs(zip_entry_dir, 0775)
        except Exception, exc:
            logger.error("create directory failed: %s" % exc)
            msg += 'error creating directory %s' % exc
            return (False, msg)
    
    real_dst_lower = real_dst.lower()
    real_src_dir = os.path.dirname(real_src)
    if real_dst_lower.endswith('.zip'):

        # Handle .zip file

        msg += ".zip file '%s' requested" % dst
        try:
            # Force compression
            pack_file = zipfile.ZipFile(real_dst, 'w', zipfile.ZIP_DEFLATED)
        except Exception, exc:
            logger.error("create zip failed: %s" % exc)
            msg += 'Could not create zipfile! %s' % exc
            return (False, msg)

        if os.path.isdir(real_src):
            walker = os.walk(real_src)
        else:
            (root, filename) = os.path.split(real_src)
            walker = ((root + os.sep, [], [filename]), )
        for (root, _, files) in walker:
            relative_root = root.replace(real_src_dir + os.sep, '')
            for entry in files:
                real_target = os.path.join(root, entry)
                relative_target = os.path.join(relative_root,
                                               entry)
                if invisible_path(real_target):
                    logger.warning('skipping hidden file: %s' \
                                                 % real_target)
                    continue
                elif real_dst == real_target:
                    msg += 'skipping destination file %s' % dst
                    continue
                logger.info("pack file %s" % relative_target)
                pack_file.write(real_target, relative_target)
            if not files and not invisible_path(relative_root):
                logger.info("pack dir %s" % relative_root)
                dir_info = zipfile.ZipInfo(relative_root + os.sep)
                pack_file.writestr(dir_info, '')
        pack_file.close()

        # Verify CRC

        try:
            pack_file = zipfile.ZipFile(real_dst, 'r')
            pack_file.testzip()
            pack_file.close()
        except Exception, exc:
            logger.error("verify zip failed: %s" % exc)
            msg += "Could not open and verify zip file: %s" % exc
    elif real_dst_lower.endswith('.tar') or \
             real_dst_lower.endswith('.tar.gz') or \
             real_dst_lower.endswith('.tgz') or \
             real_dst_lower.endswith('.tar.bz2') or \
             real_dst_lower.endswith('.tbz'):

        # Handle possibly compressed .tar files
        open_mode = "w"
        if real_dst_lower.endswith('.tar.gz') or \
               real_dst_lower.endswith('.tgz'):
            open_mode += ':gz'
        elif real_dst_lower.endswith('.tar.bz2') or \
               real_dst_lower.endswith('.tbz'):
            open_mode += ':bz2'
        else:
            # uncompressed tar
            pass
            
        try:
            pack_file = tarfile.open(real_dst, open_mode)
        except Exception, exc:
            logger.error("create tar (%s) failed: %s" % (open_mode, exc))
            msg += 'Could not open .tar file! %s\n' % exc
            return (False, msg)

        logger.info("pack entries of %s to %s" % \
                                  (real_src, real_dst))

        if os.path.isdir(real_src):
            walker = os.walk(real_src)
        else:
            (root, filename) = os.path.split(real_src)
            walker = ((root + os.sep, [], [filename]), )
        for (root, _, files) in walker:
            relative_root = root.replace(real_src_dir + os.sep, '')
            for entry in files:
                real_target = os.path.join(root, entry)
                relative_target = os.path.join(relative_root, entry)
                if invisible_path(real_target):
                    logger.warning('skipping hidden file: %s' \
                                                 % real_target)
                    continue
                elif real_dst == real_target:
                    msg += 'skipping destination file %s' % dst
                    continue
                logger.info("pack file %s" % entry)
                pack_file.add(real_target, relative_target, recursive=False)
            if not files and not invisible_path(relative_root):
                logger.info("pack dir %s" % relative_root)
                pack_file.add(root, relative_root, recursive=False)
        pack_file.close()

    msg += 'wrote archive in file %s' % dst
    return (True, msg)
