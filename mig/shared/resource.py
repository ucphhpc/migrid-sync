#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resource - [insert a few words of module description on this line]
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

"""Resource configuration functions"""

import os

from shared.fileio import pickle
from shared.confparser import get_resource_config_dict, run
from shared.useradm import client_id_dir


def create_resource(
    resource_name,
    client_id,
    resource_home,
    logger,
    ):

    status = True

    names = os.listdir(resource_home)

    # This is a bit dangerous, but if all administrators use this script to
    # create resources it should not be a problem.

    maxcounter = -1
    for direntry in names:
        lastdot = direntry.rindex('.')
        if direntry[:lastdot] == resource_name:
            counter = int(direntry[lastdot + 1:])
            if counter > maxcounter:
                maxcounter = counter

    resource_identifier = maxcounter + 1
    unique_resource_name = resource_name + '.'\
         + str(resource_identifier)
    newdir = resource_home + unique_resource_name
    try:
        os.mkdir(newdir)
    except Exception, err:

        msg = 'could not create: %s\n' % newdir
        status = False

    owner_list = []
    owner_list.append(client_id)
    owner_file = resource_home + unique_resource_name + '/owners'
    status = pickle(owner_list, owner_file, logger)
    if status == False:
        msg = 'could not pickle: %s\n' % owner_file
        status = False

    # Tell if any errors was encountered

    if status:
        msg = \
            "Resource '%s' was successfully created (%s added as the owner)"\
             % (unique_resource_name, client_id)
    else:

        # msg += """\n\n\Tell resource owner: You should also verify that you have the needed directories %s and %s. If not, you can create the
        # directories by running the following command on the frontend: <BR>mkdir -p %s
        # and this command on the execution unit: <BR>%s
        # """ % ("a", "b", "c", "d")
        # if len(resource_configfile):

        msg = \
            "Resource '%s' was NOT successfully created. Please take a look at the lines above- there should be some error output"\
             % unique_resource_name

    return (status, msg, resource_identifier)


def remove_resource(resource_home, resource_name, resource_identifier):
    msg = "\nRemoving host: '%s.%s'" % (resource_name,
            resource_identifier)

    resource_path = resource_home + resource_name + '.'\
         + str(resource_identifier)

    for (root, dirs, files) in os.walk(resource_path):
        for file in files:
            try:
                os.remove(os.path.join(root, file))
            except Exception, err:
                msg += "\n  Could'nt remove file: '%s'. Failure: %s"\
                     % (os.path.join(root, file), err)
    try:
        os.rmdir(resource_path)
    except Exception, err:
        msg += "\n  Could not remove dir: '%s' Failure: %s"\
             % (resource_path, err)
        return (False, msg)

    return (True, msg)


def create_new_resource_configuration(
    resource_name,
    client_id,
    resource_home,
    resource_pending,
    resource_identifier,
    resource_configfile,
    ):

    msg = \
        "\nTrying to create configuration for new resource: '%s.%s' from file: '%s'"\
         % (resource_name, str(resource_identifier),
            resource_configfile)
    client_dir = client_id_dir(client_id)

    pending_file = os.path.join(resource_pending, client_dir, resource_configfile)
    tmpfile = os.path.join(resource_pending, client_dir, resource_configfile + '.tmp')
    new_configfile = os.path.join(resource_home, resource_name + '.'\
         + str(resource_identifier), 'config.MiG')

    if not os.path.exists(pending_file):
        msg += """
Failure:
  File: '%s' doesn't exist."""\
             % pending_file
        return (False, msg)

    (status, conf_msg, config_dict) = \
        get_resource_config_dict(pending_file)
    if not status:
        msg += '\n%s' % conf_msg
        return (False, msg)

    if not config_dict['HOSTURL'] == resource_name:
        msg += \
            """
Failure:
  resource_name: '%s'
  does'nt match hosturl: '%s'
  in configfile: '%s'"""\
             % (resource_name, config_dict['HOSTURL'], pending_file)
        return (False, msg)

    try:
        fr = open(pending_file, 'r')
        fw = open(tmpfile, 'w')
        readline = fr.readline()
        while len(readline) > 0:
            fw.write(readline.replace('$HOSTIDENTIFIER',
                     str(resource_identifier)))
            readline = fr.readline()
        fw.close()
        fr.close()
    except Exception, err:

        msg += \
            'Failed to apply hostidentifier to configfile. Failure: %s'\
             % err
        return (False, msg)

    (status, run_msg) = run(tmpfile, resource_name + '.'
                             + str(resource_identifier))
    msg += '\n' + run_msg
    if not status:
        return (False, msg)

    # truncate old conf with new accepted file

    try:
        os.rename(tmpfile, new_configfile)
    except Exception, err:
        msg += '\nAccepted config, but failed to save it! Failed:%s'\
             % err
        return (False, msg)

    try:
        os.remove(pending_file)
    except Exception, err:
        msg += \
            '\nAccepted config and saved it, but failed to remove pending file! Failed:%s'\
             % err
        return (False, msg)

    msg += '\nNew configfile successfully applied.'
    return (True, msg)


