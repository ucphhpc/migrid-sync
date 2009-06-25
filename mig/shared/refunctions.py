#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# refunctions - [insert a few words of module description on this line]
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

"""Runtime Environment functions"""

import os
import datetime

import shared.parser as parser
import shared.rekeywords as rekeywords
from shared.fileio import pickle, unpickle
from shared.validstring import valid_dir_input


def list_runtime_environments(configuration):
    re_list = []
    dir_content = []

    try:
        dir_content = os.listdir(configuration.re_home)
    except Exception:
        if not os.path.isdir(configuration.re_home):
            try:
                os.mkdir(configuration.re_home)
            except Exception, err:
                configuration.logger.info('refunctions.py: not able to create directory %s: %s'
                         % (configuration.re_home, err))

    for entry in dir_content:
        if os.path.isfile(configuration.re_home + entry):

            # entry is a file and hence a re

            re_list.append(entry)
        else:
            configuration.logger.info('%s in %s is not a plain file, move it?'
                     % (entry, configuration.re_home))

    return (True, re_list)


def is_runtime_environment(re_name, configuration):
    if not valid_dir_input(configuration.re_home, re_name):
        configuration.logger.warning("registered possible illegal directory traversal attempt re_name '%s'"
                 % re_name)
        return False
    if os.path.isfile(configuration.re_home + re_name):
        return True
    else:
        return False


def get_re_dict(name, configuration):
    dict = unpickle(configuration.re_home + name, configuration.logger)
    if not dict:
        return (False, 'Could not open runtimeenvironment %s' % name)
    else:
        return (dict, '')


def create_runtimeenv(filename, client_id, configuration):
    result = parser.parse(filename)
    external_dict = rekeywords.get_keywords_dict()

    (status, parsemsg) = parser.check_types(result, external_dict,
            configuration)

    try:
        os.remove(filename)
    except Exception, err:
        msg = \
            'Exception removing temporary runtime environment file %s, %s'\
             % (filename, err)

        # should we exit because of this? o.reply_and_exit(o.ERROR)

    if not status:
        msg = 'Parse failed (typecheck) %s' % parsemsg
        return (False, msg)

    new_dict = {}

    # move parseresult to a dictionary

    for (key, value_dict) in external_dict.iteritems():
        new_dict[key] = value_dict['Value']

    new_dict['CREATOR'] = client_id
    new_dict['CREATED_TIMESTAMP'] = datetime.datetime.now()

    re_name = new_dict['RENAME']

    pickle_filename = configuration.re_home + re_name

    if os.path.exists(pickle_filename):
        msg = \
            "'%s' not created because a runtime environment with the same name exists!"\
             % re_name
        return (False, msg)

    if not pickle(new_dict, pickle_filename, configuration.logger):
        msg = 'Error pickling and/or saving new runtime environment'
        return (False, msg)

    # everything ok

    return (True, '')


def get_active_re_list(re_home):
    result = []
    try:
        re_list = os.listdir(re_home)
        for re in re_list:
            re_version_list = os.listdir(re_home + re)
            maxcounter = -1
            for re_version in re_version_list:
                if -1 != re_version.find('.RE.MiG'):
                    lastdot = re_version.rindex('.RE.MiG')
                    counter = int(re_version[:lastdot])
                    if counter > maxcounter:
                        maxcounter = counter

        if -1 < maxcounter:
            result.append(re + '_' + str(maxcounter))
    except Exception, err:

        return (False,
                'Could not retrieve Runtime environment list! Failure: %s'
                 % str(err), [])

    return (True, 'Active RE list retrieved with success.', result)


