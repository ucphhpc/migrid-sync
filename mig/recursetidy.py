#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# recursetidy - recursively tidy python code in file tree or archive
# Copyright (C) 2012-2020  Jonas Bardino
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

"""NOTE: should be mostly obsoleted by autopep8, but we keep it for reference.
Clean up an entire tree or archive of python code using PythonTidy from
http://pypi.python.org/pypi/PythonTidy/
Just save the latest version of PythonTidy in ./PythonTidy.py or in your
PYTHONPATH before running this program.
The program tries hard to guess if you want to process a plain file/directory
or an archive and if you want the tidied file(s) in a archive or directory.

Usage:
python recursetidy.py [SOURCE] [DESTINATION] [FILEPATTERN]
SOURCE is a plain python file, a directory structure with some python
files in it, or a zip/tar archive with optional gzip or bzip2 compression.
DESTINATION likewise is one of the previously mentioned archive types or an
existing directory.
The default SOURCE is code.zip and the default DESTINATION is tidied.zip but
just supply arguments to override those.
FILEPATTERN is a UNIX style wildcard pattern of filenames to tidy. The default
'*.py' matches all files with a '.py' extension. Please note that you will
likely need to escape or quote this argument if you want to change it.
"""

import fnmatch
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import time
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


def tidy_recursively(orig_dir, tidied_dir, filter_pattern):
    """Tidy code in src_path recursively using PythonTidy and write results
    accordingly in dst_path.
    The filter_pattern is a Unix shell-style wildcards pattern for files to
    tidy.
    """
    tidied_path_list = []
    for root, _, files in os.walk(orig_dir):
        tidied_root = root.replace(orig_dir, tidied_dir)
        # Make sure tidied parent dir exists
        try:
            os.makedirs(tidied_root)
        except OSError:
            pass
        for name in fnmatch.filter(files, filter_pattern):
            orig_path = os.path.join(root, name)
            tidied_path = os.path.join(tidied_root, name)
            try:
                logging.info("tidy %s into %s" % (orig_path, tidied_path))
                tidy_up(orig_path, tidied_path)
                tidied_path_list.append(tidied_path)
            except Exception as tidy_err:
                logging.error("tidy failed for %s: %s" % (orig_path, tidy_err))
    return tidied_path_list


def tidy_all(src_path, dst_path, filter_pattern):
    """Tidy code in src_path recursively using PythonTidy and write results
    accordingly in dst_path. If src_path is an archive the files are extracted
    to a temporary location first. If the name in dst_path is not an existing
    directory and it resembles an archive name the results are packed
    accordingly.
    The filter_pattern is a Unix shell-style wildcards pattern for files to
    tidy.
    """
    tmp_dir = tempfile.mkdtemp()
    logging.info("Using %s for temporay files" % tmp_dir)
    orig_dir = os.path.join(tmp_dir, 'original')
    tidied_dir = os.path.join(tmp_dir, 'tidied')
    os.mkdir(orig_dir)
    os.mkdir(tidied_dir)
    (zip_target, zip_mode) = check_zip(src_path, "r")
    (tar_target, tar_mode) = check_tar(src_path, "r")
    if os.path.isfile(src_path):
        if zip_target:
            logging.info("Extracting original code from zip archive %s" %
                         src_path)
            arch = zipfile.ZipFile(src_path)
            arch.extractall(orig_dir)
            arch.close()
        elif tar_target:
            logging.info("Extracting original code from tar archive %s" %
                         src_path)
            arch = tarfile.open(src_path)
            arch.extractall(orig_dir)
            arch.close()
        else:
            # We copy file to tmp dir to use walk for all cases
            logging.info("Using a copy of code from file %s" % src_path)
            shutil.copy2(src_path, orig_dir)
    elif os.path.isdir(src_path):
        logging.info("Using code from plain directory %s" % src_path)
        orig_dir = src_path
    else:
        raise ValueError("%s does not exist" % src_path)

    (zip_target, zip_mode) = check_zip(dst_path, "w")
    (tar_target, tar_mode) = check_tar(dst_path, "w")
    if zip_target or tar_target:
        logging.info("Packing tidied code in archive %s" % dst_path)
    elif os.path.isdir(dst_path):
        logging.info("Writing tidied code in directory %s" % dst_path)
        tidied_dir = dst_path
    else:
        raise ValueError("%s not recognised as archive or existing dir" %
                         dst_path)

    tidied_path_list = tidy_recursively(orig_dir, tidied_dir, filter_pattern)

    if zip_target:
        # Force compression
        arch = zipfile.ZipFile(dst_path, zip_mode, zipfile.ZIP_DEFLATED)
        for tidied_path in tidied_path_list:
            rel_path = tidied_path.replace(tidied_dir + os.sep, "")
            arch.write(tidied_path, rel_path)
        arch.close()
    elif tar_target:
        arch = tarfile.open(dst_path, tar_mode)
        for tidied_path in tidied_path_list:
            rel_path = tidied_path.replace(tidied_dir + os.sep, "")
            arch.add(tidied_path, rel_path)
        arch.close()

    # We always only delete the tmp dir to avoid deleting anything in real
    # source directories
    logging.info("Cleaning up tmp files")
    shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    in_path = 'code.zip'
    if sys.argv[1:]:
        in_path = sys.argv[1]
    out_path = 'tidied.zip'
    if sys.argv[2:]:
        out_path = sys.argv[2]
    target_pattern = "*.py"
    if sys.argv[3:]:
        target_pattern = sys.argv[3]
    default_level = logging.INFO
    default_format = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(level=default_level, format=default_format)
    if os.path.exists(out_path) and os.path.samefile(in_path, out_path):
        logging.error("same source and destination unsupported: %s" % in_path)
        sys.exit(1)
    try:
        before_tidy = time.time()
        tidy_all(in_path, out_path, target_pattern)
        after_tidy = time.time()
        logging.info("finished in %.1f seconds" % (after_tidy - before_tidy))
    except Exception as err:
        logging.error("%s" % err)
        sys.exit(1)
    logging.shutdown()
