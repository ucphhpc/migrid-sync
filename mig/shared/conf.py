#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# conf - Server configuration handling
# Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

from __future__ import absolute_import

import os
import sys

from mig.shared.fileio import unpickle


def get_configuration_object(config_file=None, skip_log=False,
                             disable_auth_log=False):
    """Simple helper to call the general configuration init. Optional skip_log
    and disable_auth_log arguments are passed on to allow skipping the default
    log initialization and disabling auth log for unit tests.
    """
    from mig.shared.configuration import Configuration
    if config_file:
        _config_file = config_file
    elif os.environ.get('MIG_CONF', None):
        _config_file = os.environ['MIG_CONF']
    else:
        app_dir = os.path.dirname(sys.argv[0])
        if not app_dir:
            _config_file = '../server/MiGserver.conf'
        else:
            _config_file = os.path.join(app_dir, '..', 'server',
                                        'MiGserver.conf')
    configuration = Configuration(_config_file, False, skip_log,
                                  disable_auth_log)
    return configuration


def get_resource_configuration(resource_home, unique_resource_name,
                               logger):
    """Load a resource configuration from file"""

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


def get_resource_fields(resource_home, unique_resource_name, fields, logger):
    """Return a dictionary mapping fields to resource_config values.
    Missing fields are left out of the result dictionary.
    """
    results = {}
    (status, resource_config) = \
        get_resource_configuration(resource_home,
                                   unique_resource_name, logger)
    if not status:
        return results
    for name in fields:
        res_val = resource_config.get(name, '__UNSET__')
        if res_val != '__UNSET__':
            results[name] = res_val
    return results


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
    if 'EXECONFIG' not in resource_config:
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
    # filter any bogus exes without name
    exe_units = [exe for exe in exe_units if exe['name']]
    return [exe['name'] for exe in exe_units]


def get_all_exe_vgrids(unique_resource_name):
    """Return a dictionary mapping exe names to assigned vgrids"""
    exe_vgrids = {}
    conf = get_configuration_object()
    (status, resource_config) = \
        get_resource_configuration(conf.resource_home,
                                   unique_resource_name, conf.logger)
    if not status:
        return exe_vgrids
    exe_units = resource_config.get('EXECONFIG', [])
    # filter any bogus exes without name
    exe_units = [exe for exe in exe_units if exe['name']]
    exe_vgrids = dict([(exe['name'], exe['vgrid']) for exe in exe_units])
    return exe_vgrids


def get_resource_store(resource_config, store_name, logger):
    for store in resource_config['STORECONFIG']:

        # find the right store entry

        if store['name'] == store_name:
            logger.debug('The configuration for %s was found'
                         % store_name)
            return (True, store)

    # not found

    msg = 'Error: The configuration for %s was not found!' % store_name
    logger.error(msg)
    return (False, msg)


def get_resource_all_stores(resource_config, logger):
    msg = ''
    if 'STORECONFIG' not in resource_config:
        msg = 'No store hosts configured!'
        logger.error(msg)
        return (False, msg)
    return (True, resource_config['STORECONFIG'])


def get_all_store_names(unique_resource_name):
    store_names = []
    conf = get_configuration_object()
    (status, resource_config) = \
        get_resource_configuration(conf.resource_home,
                                   unique_resource_name, conf.logger)
    if not status:
        return store_names
    store_units = resource_config.get('STORECONFIG', [])
    # filter any bogus stores without name
    store_units = [store for store in store_units if store['name']]
    return [store['name'] for store in store_units]


def get_all_store_vgrids(unique_resource_name):
    """Return a dictionary mapping store names to assigned vgrids"""
    store_vgrids = {}
    conf = get_configuration_object()
    (status, resource_config) = \
        get_resource_configuration(conf.resource_home,
                                   unique_resource_name, conf.logger)
    if not status:
        return store_vgrids
    store_units = resource_config.get('STORECONFIG', [])
    # filter any bogus stores without name
    store_units = [store for store in store_units if store['name']]
    store_vgrids = dict([(store['name'], store['vgrid'])
                        for store in store_units])
    return store_vgrids
