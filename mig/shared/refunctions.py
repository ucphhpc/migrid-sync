#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# refunctions - runtime environment functions
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

import base64
import datetime
import fcntl
import os
import time

import shared.rekeywords as rekeywords
import shared.parser as parser
from shared.serial import load, dump

WRITE_LOCK = 'write.lock'

def list_runtime_environments(configuration):
    """Find all runtime environments"""
    re_list = []
    dir_content = []

    try:
        dir_content = os.listdir(configuration.re_home)
    except Exception:
        if not os.path.isdir(configuration.re_home):
            try:
                os.mkdir(configuration.re_home)
            except Exception, err:
                configuration.logger.info(
                    'refunctions.py: not able to create directory %s: %s'
                    % (configuration.re_home, err))
                return (False, "runtime env setup is broken")
            dir_content = []

    for entry in dir_content:

        # Skip dot files/dirs and the write lock

        if (entry.startswith('.')) or (entry == WRITE_LOCK):
            continue
        if os.path.isfile(os.path.join(configuration.re_home, entry)):

            # entry is a file and hence a runtime environment

            re_list.append(entry)
        else:
            configuration.logger.warning(
                '%s in %s is not a plain file, move it?'
                % (entry, configuration.re_home))

    return (True, re_list)


def is_runtime_environment(re_name, configuration):
    """Check that re_name is an existing runtime environment"""
    if os.path.isfile(os.path.join(configuration.re_home, re_name)):
        return True
    else:
        return False


def get_re_dict(name, configuration):
    """Helper to extract a saved runtime environment"""
    re_dict = load(os.path.join(configuration.re_home, name))
    if not re_dict:
        return (False, 'Could not open runtime environment %s' % name)
    else:
        return (re_dict, '')

def delete_runtimeenv(re_name, configuration):
    """Delete an existing runtime environment"""
    status, msg = True, ""
    # Lock the access to the runtime env files, so that deletion is done
    # with exclusive access.
    lock_path = os.path.join(configuration.re_home, WRITE_LOCK)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    filename = os.path.join(configuration.re_home, re_name)
    if os.path.isfile(filename):
        try:
            os.remove(filename)
        except Exception, err:
            msg = "Exception during deletion of runtime enviroment '%s': %s"\
                  % (re_name, err)
            status = False
    else:
        msg = "Tried to delete non-existing runtime enviroment '%s'" % re_name
        configuration.logger.warning(msg)
        status = False
    lock_handle.close()
    return (status, msg)
    
def create_runtimeenv(filename, client_id, configuration):
    """Create a new runtime environment"""
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

    re_filename = os.path.join(configuration.re_home, re_name)

    # Lock the access to the runtime env files, so that creation is done
    # with exclusive access.
    lock_path = os.path.join(configuration.re_home, WRITE_LOCK)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

    status, msg = True, ''
    if os.path.exists(re_filename):
        status = False
        msg = \
            "can not recreate existing runtime environment '%s'!" % re_name

    try:
        dump(new_dict, re_filename)
    except Exception, err:
        status = False
        msg = 'Internal error saving new runtime environment: %s' % err

    lock_handle.close()
    return (status, msg)

def update_runtimeenv_owner(re_name, old_owner, new_owner, configuration):
    """Update owner on an existing runtime environment if existing owner
    matches old_owner.
    """
    status, msg = True, ""
    # Lock the access to the runtime env files, so that edit is done
    # with exclusive access.
    lock_path = os.path.join(configuration.re_home, WRITE_LOCK)
    lock_handle = open(lock_path, 'a')
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    re_filename = os.path.join(configuration.re_home, re_name)
    try:
        re_dict = load(re_filename)
        if re_dict['CREATOR'] == old_owner:
            re_dict['CREATOR'] = new_owner
            dump(re_dict, re_filename)
        else:
            status = False
    except Exception, err:
        msg = "Failed to edit owner of runtime enviroment '%s': %s" % \
              (re_name, err)
        configuration.logger.warning(msg)
        status = False
    lock_handle.close()
    return (status, msg)
    
def build_reitem_object(configuration, re_dict):
    """Build a runtimeenvironment object based on input re_dict"""

    software_list = []
    soft = re_dict['SOFTWARE']
    if len(soft) > 0:
        for software_item in soft:
            if software_item['url'].find('://') < 0:
                software_item['url'] = 'http://%(url)s' % software_item
            software_list.append({
                'object_type': 'software',
                'name': software_item['name'],
                'icon': software_item['icon'],
                'url': software_item['url'],
                'description': software_item['description'],
                'version': software_item['version'],
                })

    # anything specified?

    testprocedure = ''
    if len(re_dict['TESTPROCEDURE']) > 0:
        base64string = ''
        for stringpart in re_dict['TESTPROCEDURE']:
            base64string += stringpart
        testprocedure = base64.decodestring(base64string)

    verifystdout = ''
    if len(re_dict['VERIFYSTDOUT']) > 0:
        for string in re_dict['VERIFYSTDOUT']:
            verifystdout += string

    verifystderr = ''
    if len(re_dict['VERIFYSTDERR']) > 0:
        for string in re_dict['VERIFYSTDERR']:
            verifystderr += string

    verifystatus = ''
    if len(re_dict['VERIFYSTATUS']) > 0:
        for string in re_dict['VERIFYSTATUS']:
            verifystatus += string

    environments = []
    env = re_dict['ENVIRONMENTVARIABLE']
    if len(env) > 0:
        for environment_item in env:
            environments.append({
                'object_type': 'environment',
                'name': environment_item['name'],
                'example': environment_item['example'],
                'description': environment_item['description'],
                })
    created_timetuple = re_dict['CREATED_TIMESTAMP'].timetuple()
    created_asctime = time.asctime(created_timetuple)
    created_epoch = time.mktime(created_timetuple)
    return {
        'object_type': 'runtimeenvironment',
        'name': re_dict['RENAME'],
        'description': re_dict['DESCRIPTION'],
        'creator': re_dict['CREATOR'],
        'created': "<div class='sortkey'>%d</div>%s" % (created_epoch,
                                                        created_asctime),
        'job_count': '(not implemented yet)',
        'testprocedure': testprocedure,
        'verifystdout': verifystdout,
        'verifystderr': verifystderr,
        'verifystatus': verifystatus,
        'environments': environments,
        'software': software_list,
        }

