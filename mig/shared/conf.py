#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# conf - Server configuration handling
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

"""Configuration functions"""

import os
import sys

from shared.fileio import unpickle


def get_configuration_object():
    from shared.configuration import Configuration
    if os.environ.get('MIG_CONF', None):
        config_file = os.environ['MIG_CONF']
    else:
        app_dir = os.path.dirname(sys.argv[0])
        if not app_dir:
            config_file = '../server/MiGserver.conf'
        else:
            config_file = os.path.join(app_dir, '..', 'server', 'MiGserver.conf')
    configuration = Configuration(config_file, False)
    return configuration


def get_resource_configuration(resource_home, unique_resource_name,
                               logger):

    # open the configuration file

    resource_config_file = resource_home + '/' + unique_resource_name\
         + '/config'
    resource_config = unpickle(resource_config_file, logger)
    if not resource_config:
        msg = 'could not unpickle %s' % resource_config_file
        logger.error(msg)
        return (False, msg)
    else:
        return (True, resource_config)


def get_resource_exe(resource_config, exe_name, logger):
    for exe in resource_config['EXECONFIG']:

        # find the right exe entry

        if exe['name'] == exe_name:
            logger.debug('The configuration for %s was found'
                          % exe_name)
            return (True, exe)

    # not found

    msg = 'Error: The configuration for %s was not found!' % exe_name
    logger.error(msg)
    return (False, msg)


def get_resource_all_exes(resource_config, logger):
    msg = ''
    if not resource_config.has_key('EXECONFIG'):
        msg = 'No exe hosts configured!'
        logger.error(msg)
        return (False, msg)
    return (True, resource_config['EXECONFIG'])


def get_all_exe_names(unique_resource_name):
    exe_names = []
    conf = get_configuration_object()
    (status, resource_config) = \
        get_resource_configuration(conf.resource_home,
                                   unique_resource_name, conf.logger)
    if not status:
        return exe_names
    exe_units = resource_config.get('EXECONFIG', [])
    return [exe['name'] for exe in exe_units]
