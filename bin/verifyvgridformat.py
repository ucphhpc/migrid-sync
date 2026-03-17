#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# verifyvgridformat - helper to verify vgrid format
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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

"""Helper to verify MiG vgrid format"""

from __future__ import print_function

import getopt
import os
import sys
import time

from mig.shared.conf import get_configuration_object
from mig.shared.fileio import walk
from mig.shared.vgrid import vgrid_flat_name


def usage(name=sys.argv[0]):
    """Usage help"""
    print(
        """Usage:
%(name)s [OPTIONS]
Where OPTIONS may be one or more of:
   -h|--help                    Show this help
   -v|--verbose                 Verbose output
   -c PATH|--config=PATH        Path to config file
   -n NAME|--name=NAME          Only verify specific vgrid
"""
        % {"name": name},
        file=sys.stderr,
    )


def verify_vgrid_format(configuration, vgrid_name=None, verbose=False):
    """Verify vgrid format"""
    retval = True
    vgrid_mapping = {}
    basepath = configuration.vgrid_home

    # Check if vgrid_name is defined and if it's a valid vgrid

    if vgrid_name is not None:
        basepath = os.path.join(configuration.vgrid_home, vgrid_name)
        owners_filepath = os.path.join(basepath, "owners")
        if not os.path.isfile(owners_filepath):
            print("Invalid vgrid: %r" % vgrid_name)
            return False
        vgrid_mapping[vgrid_name] = vgrid_flat_name(vgrid_name, configuration)

    # Walk basepath to search for sub-vgrids

    for root, dirs, _ in walk(basepath, topdown=True):
        for dirent in dirs:
            vgrid_dirpath = os.path.join(root, dirent)
            owners_filepath = os.path.join(vgrid_dirpath, "owners")
            if os.path.isfile(owners_filepath):
                vgrid = vgrid_dirpath[len(configuration.vgrid_home) :]
                vgrid_mapping[vgrid] = vgrid_flat_name(vgrid, configuration)

    # Check vgrid format

    old_format_vgrids = {}
    for vgrid_name in vgrid_mapping:
        vgrid_name_arr = vgrid_name.split(os.sep)
        topvgrid = vgrid_name_arr[0]
        topvgrid_files_home = os.path.join(
            configuration.vgrid_files_home, topvgrid
        )
        vgrid_files_home = os.path.join(
            configuration.vgrid_files_home, vgrid_name
        )
        if not os.path.islink(vgrid_files_home):
            print(
                "vgrid: %r is using legacy format: %r"
                % (vgrid_name, vgrid_files_home)
            )
            old_format_vgrids[vgrid_name] = vgrid_mapping[vgrid_name]
        elif os.path.islink(topvgrid_files_home):
            curr_vgrid = topvgrid
            for subvgrid in vgrid_name_arr[1:]:
                curr_path = os.path.join(
                    configuration.vgrid_files_writable,
                    vgrid_flat_name(curr_vgrid, configuration),
                )
                vgrid_files_path = os.path.join(
                    configuration.vgrid_files_writable, curr_path, subvgrid
                )
                if os.path.islink(vgrid_files_path):
                    vgrid_files_dirpath = os.readlink(vgrid_files_path)
                    if not os.path.isdir(vgrid_files_dirpath):
                        print(
                            "vgrid: %r found dead dir link: %r -> %r"
                            % (
                                vgrid_name,
                                vgrid_files_path,
                                vgrid_files_dirpath,
                            )
                        )
                    vgrid_files_path = vgrid_files_dirpath
                if not os.path.isdir(vgrid_files_path):
                    print(
                        "vgrid: %r is missing data path: %r"
                        % (vgrid_name, vgrid_files_path)
                    )
                    old_format_vgrids[vgrid_name] = vgrid_mapping[vgrid_name]
                curr_vgrid = os.path.join(curr_vgrid, subvgrid)
        else:
            retval = False
            print("Missing vgrid files for: %r" % vgrid_name)

        if verbose and vgrid_name not in old_format_vgrids:
            print("vgrid: %r is up to date" % vgrid_name)

    # Show reformat suggestions if in verbose mode

    if verbose:
        for vgrid_name in old_format_vgrids:
            vgrid_name_arr = vgrid_name.split(os.sep)
            print(
                "vgrid: %r commands for reformatting to current format"
                % vgrid_name
            )
            topvgrid = vgrid_name_arr[0]
            vgrid_oldpath = os.path.join(
                configuration.vgrid_files_home, topvgrid
            )
            vgrid_newpath = os.path.join(
                configuration.vgrid_files_writable, topvgrid
            )
            # NOTE: topvgrid might be on correct format
            if not (
                os.path.islink(vgrid_oldpath) and os.path.isdir(vgrid_newpath)
            ):
                print("mv %r -> %r" % (vgrid_oldpath, vgrid_newpath))
                print(
                    "cd %r && ln -s %r ."
                    % (configuration.vgrid_files_home, vgrid_newpath)
                )
            curr_vgrid = topvgrid
            for subvgrid in vgrid_name_arr[1:]:
                curr_path = os.path.join(
                    configuration.vgrid_files_writable,
                    vgrid_flat_name(curr_vgrid, configuration),
                )
                vgrid_oldpath = os.path.join(curr_path, subvgrid)
                vgrid_newpath = os.path.join(
                    configuration.vgrid_files_writable,
                    vgrid_flat_name(
                        os.path.join(curr_vgrid, subvgrid), configuration
                    ),
                )
                # NOTE: Parent vgrid might be on correct format
                if os.path.islink(vgrid_oldpath) and os.path.isdir(
                    vgrid_newpath
                ):
                    if not os.readlink(vgrid_oldpath) == vgrid_newpath:
                        print(
                            "vgrid: %r found link mismatch: %r -> %r"
                            % (
                                curr_vgrid,
                                vgrid_oldpath,
                                os.readlink(vgrid_oldpath),
                            )
                            + ", expected: %r -> %r"
                            % (
                                vgrid_oldpath,
                                vgrid_newpath,
                            )
                        )
                else:
                    print("mv %r -> %r" % (vgrid_oldpath, vgrid_newpath))
                    print("cd %r && ln -s %r ." % (curr_path, vgrid_newpath))

                curr_vgrid = os.path.join(curr_vgrid, subvgrid)

    return retval


def main():
    """Create backup on target side"""
    conf_file = "/etc/lustrebackup.conf"
    verbose = False
    vgrid_name = None
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "hvac:n:", ["help", "verbose", "config=", "name="]
        )
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
                return 1
            elif opt in ("-v", "--verbose"):
                verbose = True
            elif opt in ("-c", "--config"):
                conf_file = arg
            elif opt in ("-n", "--name"):
                vgrid_name = arg
    except Exception as err:
        print(err, file=sys.stderr)
        usage()
        return 1

    configuration = get_configuration_object(
        config_file=conf_file, skip_log=True, disable_auth_log=True
    )
    if not configuration:
        print(
            "Failed to start %r with config: %r" % (sys.argv[0], conf_file),
            file=sys.stderr,
        )
        return 1

    logger = configuration.logger
    msg = "Starting %r with config: %r" % (sys.argv[0], conf_file)
    logger.info(msg)
    if verbose:
        print(msg)

    t1 = time.time()
    status = verify_vgrid_format(
        configuration, vgrid_name=vgrid_name, verbose=verbose
    )
    t2 = time.time()

    if status:
        retval = 0
        msg = "Verify vgrid format finished in %d seconds with status: %s" % (
            (t2 - t1),
            status,
        )
        logger.info(msg)
        if verbose:
            print(msg)
    else:
        retval = 1
        msg = "Verify vgrid format failed in %d seconds with status: %s" % (
            (t2 - t1),
            status,
        )
        logger.error(msg)
        if verbose:
            print(msg)

    return retval


if __name__ == "__main__":
    retval = main()
    sys.exit(retval)
