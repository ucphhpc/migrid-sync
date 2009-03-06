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


def handle_package_upload(file_name, remote_filename, cert_name_no_spaces, configuration, submit_mrslfiles):
    """ A file package was uploaded (eg. .zip file). Extract the content and
    submit mrsl files if submit_mrsl_files is True
    """
    base_dir = os.path.abspath(os.path.dirname(file_name)) + os.sep
    
    msg = ""
    mrslfiles_to_parse = []
    # Handle .zip file
    if file_name.upper().endswith(".ZIP"):
        msg += ".ZIP file '%s' received, it was specified that it should be extracted!\n" % remote_filename       
        try:
            zip_object = zipfile.ZipFile(file_name, "r")
        except Exception, e:
            msg += "Could not open zipfile! %s" % e
            return (False, msg)
    
        for zip_entry in zip_object.infolist():
            msg += "Extracting: %s\n" % zip_entry.filename
            # write zip_entry to disk
            local_zip_entry_name = os.path.abspath(base_dir + zip_entry.filename)
            if not valid_user_path(local_zip_entry_name, base_dir):
                msg += "Are you trying to circumvent permissions on the file system? Do not use .. in the path string!"
                return (False, msg)
        
            # create sub dir if it does not exist
            zip_entry_dir = os.path.dirname(local_zip_entry_name)
        
            if not os.path.isdir(zip_entry_dir):
                msg += "creating dir %s\n" % zip_entry_dir 
                try:
                    os.mkdir(zip_entry_dir, 0777)
                except Exception, e:
                    msg += "error creating directory %s" % e
                    return(False, msg)

            # TODO: can we detect and ignore symlinks?
            # Zip format is horribly designed/documented:
            # http://www.pkware.com/documents/casestudies/APPNOTE.TXT
            # I haven't managed to find a way to detect symlinks. Thus
            # they are simply created as files containing the name they
            # were supposed to link to: This is inconsistent but safe :-S

            # write file - symbolic links are written as files! (good for security)
            if not write_file(zip_object.read(zip_entry.filename), local_zip_entry_name, configuration.logger) and not os.path.exists(zip_object.filename):
                msg += "error writing file in memory to disk: %s" % zip_entry.filename
                return(False, msg)

            # get the size as the OS sees it
            try:
                msg += "Size: %s\n" % os.path.getsize(local_zip_entry_name)
            except Exception, e:
                msg += "File seems to be saved, but could not get file size %s\n" % e
                return(False, msg)
                 
            # Check if the extension is .mRSL
            if local_zip_entry_name.upper().endswith(".MRSL"):
                # A .mrsl file was included in the package!
                mrslfiles_to_parse.append(local_zip_entry_name)

    # Handle .tar.gz and tar.bz2 files
    elif file_name.upper().endswith(".TAR.GZ") or file_name.upper().endswith(".TGZ") or file_name.upper().endswith(".TAR.BZ2"):
        if file_name.upper().endswith(".TAR.GZ") or file_name.upper().endswith(".TGZ"):
            msg += ".TAR.GZ file '%s' received, it was specified that it should be extracted!\n" % remote_filename
            try:
                tar_object = tarfile.open(file_name, "r:gz")
                tar_file_content = tarfile.TarFile.gzopen(file_name)
            except Exception, e:
                msg += "Could not open .tar.gz file! %s\n" % e
                return (False, msg)
        elif file_name.upper().endswith(".TAR.BZ2"):
            msg += ".TAR.BZ2 file '%s' received, it was specified that it should be extracted!\n" % remote_filename
            try:
                tar_object = tarfile.open(file_name, "r:bz2")
                tar_file_content = tarfile.TarFile.bz2open(file_name)
            except Exception, e:
                msg += "Could not open .tar.bz2 file! %s\n" % e
                return (False, msg)
        else:
            msg += "Internal error, should not be able to enter this else!!"
            return(False, msg)
        
        for tar_entry in tar_object:
            msg += "Extracting: %s\n" % tar_entry.name
            # write tar_entry to disk
            local_tar_entry_name = os.path.abspath(base_dir + tar_entry.name)

            if not valid_user_path(local_tar_entry_name, base_dir):
                msg += "Are you trying to circumvent permissions on the file system? Do not use .. in the path string!\n"
                return (False, msg)
        
            # create sub dir if it does not exist
            tar_entry_dir = os.path.dirname(local_tar_entry_name)
        
            if not os.path.isdir(tar_entry_dir):
                msg += "creating dir %s\n" % tar_entry_dir 
                try:
                    os.mkdir(tar_entry_dir, 0777)
                except Exception, e:
                    msg += "error creating directory %s\n" % e
                    return(False, msg)
            if not tar_entry.isreg():
                # not a regular file - symlinks are ignored to avoid illegal access
                msg += "skipping %s: not a file or directory!\n" % tar_entry.name
                continue 

            # write file!
            if not write_file(tar_file_content.extractfile(tar_entry).read(), local_tar_entry_name, configuration.logger):
                msg += "error writing file in memory to disk %s\n" % e
                return(False, msg)

            # get the size as the OS sees it
            try:
                msg += "Size: %s\n" % os.path.getsize(local_tar_entry_name)
            except Exception, e:
                msg += "File seems to be saved, but could not get file size %s\n" % e
                return(False, msg)
                 
            # Check if the extension is .mRSL
            if (local_tar_entry_name.upper().endswith(".MRSL")):
                # A .mrsl file was included in the package!
                mrslfiles_to_parse.append(local_tar_entry_name)

    # submit mrsl files to the parser. It should be done from within this function to 
    # keep the right order if multiple files are created in the html form. 
    submitstatuslist = []
    if submit_mrslfiles:
        uploaddir = configuration.user_home + cert_name_no_spaces + os.sep                
        for mrslfile in mrslfiles_to_parse:
            (status, parse_msg, job_id) = new_job(mrslfile, cert_name_no_spaces, configuration, False, True)
            relative_filename = os.sep + mrslfile.replace(uploaddir, "")                                                                                             
            submitstatus = {"object_type":"submitstatus", "name":relative_filename}
            if not status:
                submitstatus["status"] = False 
                submitstatus["job_id"] = job_id      
                submitstatus["message"] = parse_msg      
                #msg += "<H2>Failure</H2><BR>\n"
                #msg += parse_msg
                #return(False, msg)
            else:
                submitstatus["status"] = True                                                                                                                
                submitstatus["job_id"] = job_id    
            #msg += "<H2>%s Success</H2><BR>\n" % mrslfile
            #msg += parse_msg 
            submitstatuslist.append(submitstatus)
    return (True, submitstatuslist)
