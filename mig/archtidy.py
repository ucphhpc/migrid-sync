#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# archtidy - tidy an entire archive of python code files
# Copyright (C) 2012  Jonas Bardino
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

"""Clean up an entire archive of python code using PythonTidy from
http://pypi.python.org/pypi/PythonTidy/
Just save the latest version of PythonTidy in ./PythonTidy.py or in your
PYTHONPATH before running archtidy.
"""

import os
import sys
import subprocess
import tempfile
import time
import logging
import tarfile
import zipfile
from PythonTidy import tidy_up


def check_zip(path, mode_prefix):
    """Return a tuple with a boolean to indicate if path is a zip file and a
    mode suitable for zipfile opening.
    """
    status = False
    mode = mode_prefix
    if path.endswith('.zip'):
        status = True
    return (status, mode)

def check_tar(path, mode_prefix):
    """Return a tuple with a boolean to indicate if path is a tar file of some
    kind and a mode suitable for tarfile opening with expected compression
    type.
    """
    status = False
    plain_exts = [".tar"]
    gz_exts = [".tgz", ".tar.gz"]
    bz_exts = [".tbz", ".tbz2", ".tar.bz", "tar.bz2"]
    all_exts = plain_exts + gz_exts + bz_exts
    mode = mode_prefix
    # Extension matches any of the tar extensions
    status = (True in [path.endswith(ext) for ext in all_exts])
    if True in [path.endswith(ext) for ext in gz_exts]:
        mode += ':gz'
    elif True in [path.endswith(ext) for ext in bz_exts]:
        mode += ':bz2'
    return (status, mode)

def tidy_archive(src_path, dst_path, logging):
    """Unpack files from archive in src_path, run PythonTidy on each file and
    write the tidied files to a new archive in dst_path.
    """
    tmp_dir = tempfile.mkdtemp()
    logging.info("Using %s for temporay files" % tmp_dir)
    orig_dir = os.path.join(tmp_dir, 'original')
    tidied_dir = os.path.join(tmp_dir, 'tidied')
    os.mkdir(orig_dir)
    os.mkdir(tidied_dir)
    tidied_path_list = []
    (zip_src, zip_mode) = check_zip(src_path, "r")
    (tar_src, tar_mode) = check_tar(src_path, "r")
    logging.info("Extracting original code from archive %s" % in_path)
    logging.info("modes %s %s" % (zip_mode, tar_mode))
    if zip_src:
        src_arch = zipfile.ZipFile(src_path)
        src_arch.extractall(orig_dir)
        src_arch.close()
    elif tar_src:
        src_arch = tarfile.open(src_path)
        src_arch.extractall(orig_dir)
        src_arch.close()
    else:
        raise ValueError("unknown input archive type: %s" % src_path)

    for root, dirs, files in os.walk(tmp_dir):
        for name in files:
            orig_path = os.path.join(root, name)
            tidied_path = orig_path.replace(orig_dir, tidied_dir)
            try:
                tidy_up(orig_path, tidied_path)
                tidied_path_list.append(tidied_path)
            except Exception, exc:
                logger.error("tidy failed for %s: %s" % (orig_path, exc))
    
    (zip_dst, zip_mode) = check_zip(src_path, "w")
    (tar_dst, tar_mode) = check_tar(src_path, "w")
    logging.info("Packing tidied code in archive %s" % out_path)
    if zip_dst:
        dst_arch = zipfile.ZipFile(dst_path, zip_mode)
        for tidied_path in tidied_path_list:
            rel_path = tidied_path.replace(tmp_dir + os.sep, "")
            dst_arch.write(tidied_path, rel_path)
        dst_arch.close()
    elif tar_dst:
        dst_arch = tarfile.open(dst_path, tar_mode)
        for tidied_path in tidied_path_list:
            rel_path = tidied_path.replace(tmp_dir + os.sep, "")
            dst_arch.add(tidied_path, rel_path)
        dst_arch.close()
    else:
        raise ValueError("unknown output archive type: %s" % src_path)

    logging.info("Cleaning up tmp files")
    for root, dirs, files in os.walk(tmp_dir, topdown=False):
        for name in files:
            tmp_path = os.path.join(root, name)
            os.remove(tmp_path)
        for name in dirs:
            tmp_path = os.path.join(root, name)
            os.rmdir(tmp_path)
    os.rmdir(tmp_dir)

        
if __name__ == "__main__":
    in_path = 'code.zip'
    if sys.argv[1:]:
        in_path = sys.argv[1]
    out_path = 'tidied-%s' % in_path
    if sys.argv[2:]:
        out_path = sys.argv[2]
    default_level = logging.INFO
    default_format = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(level=default_level, format=default_format)
    if os.path.exists(out_path) and os.path.samefile(in_path, out_path):
        logging.error("same source and destination: %s" % in_path)
        sys.exit(1)
    try:
        before_tidy = time.time()
        tidy_archive(in_path, out_path, logging)
        after_tidy = time.time()
        logging.info("Finished n %.1f seconds" % (after_tidy - before_tidy))
    except Exception, exc:
        logging.error("Error during tidy: %s" % exc)
        sys.exit(1)
    logging.shutdown()

