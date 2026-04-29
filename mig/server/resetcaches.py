#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resetcaches - (re)set vgrid/user/resource map caches in state mig_system_X
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""(Re)set vgrid/user/resource map caches in state mig_system_X"""

import getopt
import os
import sys


from mig.shared.conf import get_configuration_object
from mig.shared.fileio import delete_file
from mig.shared.vgridaccess import refresh_vgrid_map, refresh_user_map, \
    refresh_resource_map


def refresh_maps(configuration, map_list, verbose, force=False, allow_missing=True):
    """Make sure one or more of vgrid, user and resource maps are refreshed"""
    _logger = configuration.logger
    status = True

    for map_name in map_list:
        for root in (configuration.mig_system_files, configuration.mig_system_run):
            for ext in ('map', 'lock', 'modified'):
                sub_path = os.path.join(root, "%s.%s" % (map_name, ext))
                if verbose:
                    print("Removing %s" % sub_path)
                status = delete_file(
                    sub_path, _logger, allow_missing=allow_missing)
                if not status and not force:
                    return status
        if map_name == 'vgrid':
            if not refresh_vgrid_map(configuration) and not force:
                return status
        elif map_name == 'user':
            if not refresh_user_map(configuration) and not force:
                return status
        elif map_name == 'resource':
            if not refresh_resource_map(configuration) and not force:
                return status
        else:
            raise ValueError("unsupported map: %s" % map_name)
    return status


def usage(name='resetcaches.py'):
    """Usage help"""

    print("""(Re)set vgrid, user and resource map caches.
Usage:
%(name)s [OPTIONS] [MAP_NAME ...]
Where OPTIONS may be one or more of:
   -c CONF_FILE        Use CONF_FILE as server configuration
   -f                  Force operations to continue past errors
   -h                  Show this help
   -v                  Verbose output
and MAP_NAME one or more of vgrid, user and resource.
""" % {'name': name})


if '__main__' == __name__:
    conf_path = None
    force = False
    verbose = False
    opt_args = 'c:fhv'
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], opt_args)
    except getopt.GetoptError as err:
        print('Error: ', err.msg)
        usage()
        sys.exit(1)

    for (opt, val) in opts:
        if opt == '-c':
            conf_path = val
        elif opt == '-f':
            force = True
        elif opt == '-h':
            usage()
            sys.exit(0)
        elif opt == '-v':
            verbose = True
        else:
            print('Error: %s not supported!' % opt)

    if conf_path and not os.path.isfile(conf_path):
        print('Failed to read configuration file: %s' % conf_path)
        sys.exit(1)

    if verbose:
        if conf_path:
            os.environ['MIG_CONF'] = conf_path
            print('using configuration in %s' % conf_path)
        else:
            print('using configuration from MIG_CONF (or default)')

    configuration = get_configuration_object(skip_log=True)
    if args:
        map_list = args
    else:
        map_list = ['vgrid', 'user', 'resource']

    if not refresh_maps(configuration, map_list, verbose, force):
        print("Failed to refresh %s map(s) - force may be needed?" %
              ', '.join(map_list))
        sys.exit(1)

    if verbose:
        print("Refreshed %s maps" % ', '.join(map_list))

    sys.exit(0)
