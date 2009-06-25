#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# livedisplaysfunctions - [insert a few words of module description on this line]
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

# TODO: lock access to dict since multiple threads can access this lib simultaniously

import os

from shared.fileio import pickle, unpickle
from shared.conf import get_configuration_object


def initialize_and_get_display_dict_filename(configuration, logger):
    filename = configuration.mig_server_home + os.sep\
         + 'livedisplaysdict'
    if os.path.isfile(filename):
        return (True, filename)
    logger.info('display dict file %s not found, pickling a new with {} as only content'
                 % filename)

    dict = {}
    pickle_status = pickle(dict, filename, logger)
    if not pickle_status:
        return (False, 'could not pickle %s when initializing'
                 % filename)
    return (True, filename)


def get_users_display_number(client_id, configuration,
                             logger):
    (init_ret, filename) = \
        initialize_and_get_display_dict_filename(configuration, logger)
    if not init_ret:
        return (False, 'could not initialize')

    (key, value) = get_users_display_dict(client_id,
            configuration, logger)
    logger.error('karlsen debug: %s' % key)
    logger.error('karlsen debug: %s' % value)

    if not key:
        logger.error(value)
        return False
    return key


def get_users_display_dict(client_id, configuration, logger):
    (init_ret, filename) = \
        initialize_and_get_display_dict_filename(configuration, logger)
    if not init_ret:
        return (False, 'could not initialize')

    dict = unpickle(filename, logger)
    if dict == False:
        return (False, 'could not unpickle %s' % filename)

    for (key, value) in dict.items():
        if value['client_id'] == client_id:
            return (key, value)

    # not found, client_id does not have a live display

    return (-1, -1)


def set_user_display_inactive(
    client_id,
    display_number,
    configuration,
    logger,
    ):

    (init_ret, filename) = \
        initialize_and_get_display_dict_filename(configuration, logger)
    if not init_ret:
        return (False, 'could not initialize')

    current_display = get_users_display_number(client_id,
            configuration, logger)
    if not current_display:
        return (False,
                'could not remove active display since no entry was found for %s'
                 % client_id)

    if current_display == -1:
        return (False,
                'user %s does not have a display registered, unable to inactivate any display'
                 % client_id)

    if current_display != display_number:
        return (False,
                'user %s had display %s registered in dict, but specified display_number in set_user_display_inactive was %s'
                 % (client_id, current_display,
                display_number))

    # remove entry from dict and pickle it

    dict = unpickle(filename, logger)
    if dict == False:
        return (False, 'could not unpickle %s' % filename)

    if not dict.has_key(display_number):
        return (False, 'display %s not found in dict' % display_number)
    try:
        del dict[display_number]
    except Exception, e:
        return (False,
                'exception trying to remove %s from display dict. Exception %s'
                 % (display_number, e))

    pickle_status = pickle(dict, filename, logger)

    if not pickle_status:
        return (False, 'could not pickle %s when removing %s'
                 % (filename, display_number))
    return (True, '')


def get_dict_from_display_number(display_number, configuration, logger):
    (init_ret, filename) = \
        initialize_and_get_display_dict_filename(configuration, logger)
    if not init_ret:
        return (False, 'could not initialize')

    dict = unpickle(filename, logger)
    if dict == False:
        print 'dict is %s false' % dict
        return (False, 'could not unpickle %s' % filename)

    if dict.has_key(display_number):
        return (display_number, dict[display_number])
    else:
        return (True, -1)


def set_user_display_active(
    client_id,
    display_number,
    vnc_port,
    password,
    configuration,
    logger,
    ):

    (init_ret, filename) = \
        initialize_and_get_display_dict_filename(configuration, logger)
    if not init_ret:
        return (False, 'could not initialize')

    (dis_ret, dis_dict) = get_dict_from_display_number(display_number,
            configuration, logger)
    if not dis_ret:
        return (False, 'dict error, %s' % dis_dict)
    if dis_dict != -1:
        if dis_dict['client_id'] != client_id:

        # display occupied by another user!

            return (False, 'display %s already in use by another user!'
                     % display_number)

    # getting here means display is free or used by client_id

    dict = unpickle(filename, logger)
    if dict == False:
        return (False, 'could not unpickle %s' % filename)

    current_display = get_users_display_number(client_id,
            configuration, logger)
    if not current_display:

    # register display

        dict[display_number] = \
            {'client_id': client_id,
             'vnc_port': vnc_port, 'password': password}
        pickle_status = pickle(dict, filename, logger)

        if not pickle_status:
            return (False, 'could not pickle %s when adding %s'
                     % (filename, dict[display_number]))
        logger.info('successfuly registered that display %s is in use by %s in %s'
                     % (display_number, client_id, filename))
        return (True, '')

    if current_display != display_number and current_display != -1:

    # problems..

        return (False,
                'set_user_display_active met a conflict, can not set display %s when user already has %s registered'
                 % (display_number, current_display))
    else:

    # add display to dict

        dict[display_number] = \
            {'client_id': client_id,
             'vnc_port': vnc_port, 'password': password}
        pickle_status = pickle(dict, filename, logger)

        if not pickle_status:
            return (False, 'could not pickle %s when adding %s'
                     % (filename, dict[display_number]))

        logger.info('successfuly registered that display %s is in use by %s in %s %s'
                     % (display_number, client_id, dict,
                    filename))
        return (True, '')


# test of functions

if "__main__" == __name__:
    print '*** Testing livedisplayfunctions ***'

    # from shared.cgishared import init_cgiscript_possibly_with_cert
    # (logger, configuration, client_id, o) = init_cgiscript_possibly_with_cert()

    client_id = 'Henrik_Hoey_Karlsen3'
    configuration = get_configuration_object()
    logger = configuration.logger
    (stat, msg) = get_users_display_dict(client_id,
            configuration, logger)
    print 'users_display_dict status: %s, msg: %s' % (stat, msg)
