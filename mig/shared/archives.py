#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# archives - zip/tar packing and unpacking helpers
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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
from __future__ import absolute_import

import os
import zipfile
import tarfile

from .shared.base import client_id_dir, invisible_path, force_utf8
from .shared.fileio import write_file
from .shared.job import new_job
from .shared.safeinput import valid_user_path_name


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
    status = True

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

        msg += "Received '%s' for unpacking. " % relative_src
        try:
            zip_object = zipfile.ZipFile(real_src, 'r', allowZip64=True)
        except Exception as exc:
            logger.error("open zip failed: %s" % exc)
            msg += 'Could not open zipfile: %s! ' % exc
            return (False, msg)

        logger.info("unpack entries of %s to %s" % \
                                  (real_src, real_dst))
        for zip_entry in zip_object.infolist():
            entry_filename = force_utf8(zip_entry.filename)
            msg += 'Extracting: %s . ' % entry_filename

            # write zip_entry to disk

            # IMPORTANT: we must abs-expand for valid_user_path_name check
            #            otherwise it will incorrectly fail on e.g. abc/
            #            dir entry in archive
            local_zip_entry_name = os.path.join(real_dst, entry_filename)
            valid_status, valid_err = valid_user_path_name(
                entry_filename, os.path.abspath(local_zip_entry_name),
                base_dir)
            if not valid_status:
                status = False
                msg += "Filename validation error: %s! " % valid_err
                continue

            # create sub dir(s) if missing

            zip_entry_dir = os.path.dirname(local_zip_entry_name)

            if not os.path.isdir(zip_entry_dir):
                msg += 'Creating dir %s . ' % entry_filename
                try:
                    os.makedirs(zip_entry_dir, 0o775)
                except Exception as exc:
                    logger.error("create directory failed: %s" % exc)
                    msg += 'Error creating directory: %s! ' % exc
                    status = False
                    continue

            if os.path.isdir(local_zip_entry_name):
                logger.debug("nothing more to do for dir entry: %s" % \
                            local_zip_entry_name)
                continue

            try:
                zip_data = zip_object.read(zip_entry.filename)
            except Exception as exc:
                logger.error("read data in %s failed: %s" % \
                             (zip_entry.filename, exc))
                msg += 'Error reading %s :: %s! ' % (zip_entry.filename, exc)
                status = False
                continue
            
            # TODO: can we detect and ignore symlinks?
            # Zip format is horribly designed/documented:
            # http://www.pkware.com/documents/casestudies/APPNOTE.TXT
            # I haven't managed to find a way to detect symlinks. Thus
            # they are simply created as files containing the name they
            # were supposed to link to: This is inconsistent but safe :-S

            # write file - symbolic links are written as files! (good for
            # security).

            # NB: Needs to use undecoded filename here

            if not write_file(zip_data, local_zip_entry_name, logger) and \
                   not os.path.exists(local_zip_entry_name):
                msg += 'Error unpacking %s to disk! ' % entry_filename
                status = False
                continue

            # get the size as the OS sees it

            try:
                __ = os.path.getsize(local_zip_entry_name)
            except Exception as exc:
                logger.warning("unpack may have failed: %s" % exc)
                msg += \
                    'File %s unpacked, but could not get file size %s! '\
                     % (entry_filename, exc)
                status = False
                continue

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
            msg += "Received '%s' for unpacking. " % relative_src
            try:
                tar_object = tarfile.open(real_src, 'r:gz')
                tar_file_content = tarfile.TarFile.gzopen(real_src)
            except Exception as exc:
                logger.error("open tar gz failed: %s" % exc)
                msg += 'Could not open .tar.gz file: %s! ' % exc
                return (False, msg)
        elif real_src_lower.endswith('.tar.bz2') or \
                 real_src_lower.endswith('.tbz'):
            msg += "Received '%s' for unpacking. " % relative_src
            try:
                tar_object = tarfile.open(real_src, 'r:bz2')
                tar_file_content = tarfile.TarFile.bz2open(real_src)
            except Exception as exc:
                logger.error("open tar bz failed: %s" % exc)
                msg += 'Could not open .tar.bz2 file: %s! ' % exc
                return (False, msg)
        else:
            try:
                tar_object = tarfile.open(real_src, 'r')
                tar_file_content = tarfile.TarFile.open(real_src)
            except Exception as exc:
                logger.error("open tar failed: %s" % exc)
                msg += 'Could not open .tar file: %s! ' % exc
                return (False, msg)

        logger.info("unpack entries of %s to %s" % \
                                  (real_src, real_dst))
        for tar_entry in tar_object:
            entry_filename = force_utf8(tar_entry.name)
            msg += 'Extracting: %s . ' % entry_filename

            # write tar_entry to disk

            # IMPORTANT: we must abs-expand for valid_user_path_name check
            #            otherwise it will incorrectly fail on e.g. abc/
            #            dir entry in archive
            local_tar_entry_name = os.path.join(real_dst, entry_filename)
            valid_status, valid_err = valid_user_path_name(
                entry_filename, os.path.abspath(local_tar_entry_name),
                base_dir)
            if not valid_status:
                status = False
                msg += "Filename validation error: %s! " % valid_err
                continue

            # Found empty dir - make sure  dirname doesn't strip to parent

            if tar_entry.isdir():
                logger.debug("empty dir %s - include in parent creation" % \
                            local_tar_entry_name)
                local_tar_entry_name += os.sep

            # create sub dir(s) if missing

            tar_entry_dir = os.path.dirname(local_tar_entry_name)

            if not os.path.isdir(tar_entry_dir):
                logger.debug("make tar parent dir: %s" % tar_entry_dir)
                msg += 'Creating dir %s . ' % entry_filename
                try:
                    os.makedirs(tar_entry_dir, 0o775)
                except Exception as exc:
                    logger.error("create directory failed: %s" % exc)
                    msg += 'Error creating directory %s! ' % exc
                    status = False
                    continue

            if tar_entry.isdir():

                # directory created above - nothing more to do

                continue

            elif not tar_entry.isfile():

                # not a regular file - symlinks are ignored to avoid illegal
                # access

                msg += 'Skipping %s: not a regular file or directory! ' % \
                       entry_filename
                status = False
                continue

            # write file!
            # NB: Need to user undecoded filename here

            if not write_file(tar_file_content.extractfile(tar_entry).read(),
                              local_tar_entry_name,
                              logger):
                msg += 'Error unpacking file %s to disk! ' % entry_filename
                status = False
                continue

            # get the size as the OS sees it

            try:
                __ = os.path.getsize(local_tar_entry_name)
            except Exception as exc:
                logger.warning("file save may have failed: %s" % exc)
                msg += \
                    'File %s unpacked, but could not get file size %s! ' % \
                    (entry_filename, exc)
                status = False
                continue

            # Check if the extension is .mRSL

            if local_tar_entry_name.upper().endswith('.MRSL'):

                # A .mrsl file was included in the package!

                mrslfiles_to_parse.append(local_tar_entry_name)
    else:
        logger.error("Unpack called on unsupported archive: %s" % real_src)
        msg += "Unknown/unsupported archive format: %s" % relative_src
        return (False, msg)        

    if not status:
        msg = """Unpacked archive with one or more errors: 
%s""" % msg
        return (status, msg)
    
    # submit mrsl files to the parser. It should be done from within this
    # function to keep the right order if multiple files are created in the
    # html form.

    submitstatuslist = []
    if configuration.site_enable_jobs and submit_mrslfiles:

        # Please note that base_dir must end in slash to avoid access to other
        # user dirs when own name is a prefix of another user name

        base_dir = \
            os.path.abspath(os.path.join(configuration.user_home,
                            client_dir)) + os.sep
        for mrslfile in mrslfiles_to_parse:
            (job_status, parse_msg, job_id) = new_job(mrslfile, client_id,
                    configuration, False, True)
            relative_filename = os.sep + mrslfile.replace(base_dir, '')
            submitstatus = {'object_type': 'submitstatus',
                            'name': relative_filename}
            if not job_status:
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
    return (status, submitstatuslist)


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
    traversal attempts *before* getting here.
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
    traversal attempts *before* getting here.
    """
    logger = configuration.logger
    msg = ''
    status = True
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
        logger.debug("make zip parent dir: %s" % zip_entry_dir)
        msg += 'Creating dir %s . ' % zip_entry_dir
        try:
            os.makedirs(zip_entry_dir, 0o775)
        except Exception as exc:
            logger.error("create directory failed: %s" % exc)
            msg += 'Error creating parent directory %s! ' % exc
            return (False, msg)

    real_dst_lower = real_dst.lower()
    real_src_dir = os.path.dirname(real_src)
    open_mode = "w"
    if real_dst_lower.endswith('.zip'):

        # Handle .zip file

        msg += "Requested packing of %s in %s . " % (src, dst)
        try:
            # Force compression and allow files bigger than 2GB
            pack_file = zipfile.ZipFile(real_dst, open_mode,
                                        zipfile.ZIP_DEFLATED, allowZip64=True)
        except Exception as exc:
            logger.error("create zip failed: %s" % exc)
            msg += 'Could not create zipfile: %s! ' % exc
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
                    msg += 'Skipping destination file %s . ' % dst
                    continue
                logger.debug("pack file %s" % relative_target)
                try:
                    pack_file.write(real_target, relative_target)
                except Exception as exc:
                    logger.error('write of %s failed: %s' % \
                                 (real_target, exc))
                    msg += 'Failed to write file %s . ' % relative_target
                    status = False
                    continue
                    
            if not files and not invisible_path(relative_root):
                logger.debug("pack dir %s" % relative_root)
                try:
                    dir_info = zipfile.ZipInfo(relative_root + os.sep)
                    pack_file.writestr(dir_info, '')
                except Exception as exc:
                    logger.error('write of %s failed: %s' % \
                                 (real_target, exc))
                    msg += 'Failed to write dir %s . ' % relative_root
                    status = False
                    continue
        pack_file.close()

        # Verify CRC

        try:
            pack_file = zipfile.ZipFile(real_dst, 'r', allowZip64=True)
            pack_file.testzip()
            pack_file.close()
        except Exception as exc:
            logger.error("verify zip failed: %s" % exc)
            msg += "Could not open and verify zip file: %s! " % exc
            status = False
    elif real_dst_lower.endswith('.tar') or \
             real_dst_lower.endswith('.tar.gz') or \
             real_dst_lower.endswith('.tgz') or \
             real_dst_lower.endswith('.tar.bz2') or \
             real_dst_lower.endswith('.tbz'):

        # Handle possibly compressed .tar files
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
        except Exception as exc:
            logger.error("create tar (%s) failed: %s" % (open_mode, exc))
            msg += 'Could not open .tar file: %s! ' % exc
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
                    msg += 'Skipping destination file %s . ' % dst
                    continue
                logger.debug("pack file %s" % entry)
                try:
                    pack_file.add(real_target, relative_target, recursive=False)
                except Exception as exc:
                    logger.error('write of %s failed: %s' % \
                                 (real_target, exc))
                    msg += 'Failed to write file %s . ' % relative_target
                    status = False
                    continue
                    
            if not files and not invisible_path(relative_root):
                logger.debug("pack dir %s" % relative_root)
                try:
                    pack_file.add(root, relative_root, recursive=False)
                except Exception as exc:
                    logger.error('write of %s failed: %s' % \
                                 (real_target, exc))
                    msg += 'Failed to write dir %s . ' % relative_root
                    status = False
                    continue
                    
        pack_file.close()
    else:
        logger.error("Pack called with unsupported archive format: %s" % dst)
        msg += "Unknown/unsupported archive format: %s" % dst
        return (False, msg)

    if status:
        msg += 'Wrote archive in file %s . ' % dst
    else:
        msg = """Packed archive with one or more errors:
 %s""" % msg

    return (status, msg)
