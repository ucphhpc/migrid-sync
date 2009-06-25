#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgrid - helper functions related to VGrid actions
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

"""VGrid specific helper functions"""

import os
import fnmatch

from shared.listhandling import list_items_in_pickled_list
from shared.validstring import valid_dir_input
from shared.findtype import is_user, is_resource

default_vgrid = 'Generic'
any_vgrid = 'ANY'


def vgrid_is_default(vgrid):
    """Check if supplied vgrid matches any of the names
    associated with the default vgrid"""

    if not vgrid or vgrid.upper() == default_vgrid.upper():
        return True
    else:
        return False


def vgrid_is_owner_or_member(vgrid_name, client_id,
                             configuration):
    """Combines owner and member check"""

    if vgrid_is_owner(vgrid_name, client_id, configuration)\
         or vgrid_is_member(vgrid_name, client_id,
                            configuration):
        return True
    else:
        return False


def vgrid_is_cert_in_list(
    vgrid_name,
    client_id,
    group,
    configuration,
    ):
    """Return True if specified client_id is in group
    ('owners', 'members', 'resources') of vgrid.
    Please note that client_id is a misleading name when
    called for resources, where it is actually the unique resource ID.
    """

    # Get the list of entities of specified type (group) in vgrid (vgrid_name)

    (status, entries) = vgrid_list(vgrid_name, group, configuration)

    if not status:
        configuration.logger.error('status not True in vgrid_is_cert_in_list: %s'
                                    % entries)
        return False

    for entry in entries:

        # Use fnmatch to accept direct hits as well as wild card matches

        if fnmatch.fnmatch(client_id, entry):
            return True
    return False


def vgrid_is_owner(vgrid_name, client_id, configuration):
    """Check if client_id is an owner of vgrid_name. Please note
    that noone is an owner of the default vgrid.
    """

    if vgrid_is_default(vgrid_name):
        return False
    return vgrid_is_cert_in_list(vgrid_name, client_id,
                                 'owners', configuration)


def vgrid_is_member(vgrid_name, client_id, configuration):
    """Check if client_id is a member of vgrid_name. Please note
    that everyone is a member of the Generic vgrid.
    """

    # anyone is member of default VGrid

    if vgrid_is_default(vgrid_name):
        return True
    return vgrid_is_cert_in_list(vgrid_name, client_id,
                                 'members', configuration)


def vgrid_is_resource(vgrid_name, client_id, configuration):
    """Check if client_id is a resource in vgrid_name. Please note
    that everyone is a member of the Generic vgrid.
    """

    if vgrid_is_default(vgrid_name):
        return True
    return vgrid_is_cert_in_list(vgrid_name, client_id,
                                 'resources', configuration)


def vgrid_list_subvgrids(vgrid_name, configuration):
    """Return list of subvgrids of vgrid_name"""

    result_list = []
    (status, all_vgrids_list) = vgrid_list_vgrids(configuration)
    if not status:
        return (False, 'could not get list of all vgrids on server')
    for vgrid in all_vgrids_list:
        if vgrid.startswith(vgrid_name) and vgrid_name != vgrid:
            result_list.append(vgrid)
    return (True, result_list)


def vgrid_list_vgrids(configuration):
    """List all vgrids and sub-vgrids created on the system"""

    vgrids_list = []
    for (root, dirs, _) in os.walk(configuration.vgrid_home):

        # skip all dot dirs - they are from repos etc and _not_ vgrids

        if root.find(os.sep + '.') != -1:
            continue
        dirs = [name for name in dirs if not name.startswith('.')]

        for directory in dirs:

            # strip vgrid_home prefix to get entire vgrid name (/dalton/dk/imada)

            complete_vgrid_location = os.path.join(root, directory)
            vgrid_name_without_location = \
                complete_vgrid_location.replace(configuration.vgrid_home,
                    '', 1)

            vgrids_list.append(vgrid_name_without_location)
    return (True, vgrids_list)


def init_vgrid_script_add_rem(
    vgrid_name,
    client_id,
    subject,
    subject_type,
    configuration,
    ):
    """Initialize vgrid specific add and remove scripts"""

    msg = ''
    if not vgrid_name:
        msg += 'Please specify vgrid_name in the querystring'
        return (False, msg, None)

    if not subject:
        msg += 'Please provide the name of the %s' % subject_type
        return (False, msg, None)

    if not valid_dir_input(configuration.vgrid_home, vgrid_name):
        msg += 'Illegal vgrid_name: %s' % vgrid_name
        return (False, msg, None)

    if not vgrid_is_owner(vgrid_name, client_id,
                          configuration):
        msg += 'You must be an owner of the %s vgrid to add/remove %s'\
             % (vgrid_name, subject_type)
        return (False, msg, None)

    if subject_type == 'member' or subject_type == 'owner':
        if not is_user(subject, configuration.user_home):
            msg += '%s is not a valid MiG user!' % subject
            return (False, msg, None)
    elif subject_type == 'resource':
        if not is_resource(subject, configuration.resource_home):
            msg += '%s is not a valid MiG resource' % subject
            msg += \
                ' (OK, if removing or if e.g. the resource creation is pending)'
    else:
        msg += 'unknown subject type in init_vgrid_script_add_rem'
        return (False, msg, [])

    return (True, msg, [])


def init_vgrid_script_list(vgrid_name, client_id,
                           configuration):
    """Helper for vgrid scripts"""

    msg = ''
    if not vgrid_name:
        msg += 'Please specify vgrid_name in the query string'
        return (False, msg, None)

    if not valid_dir_input(configuration.vgrid_home, vgrid_name):
        msg += 'Illegal vgrid_name: %s' % vgrid_name
        return (False, msg, None)

    if not vgrid_is_owner_or_member(vgrid_name, client_id,
                                    configuration):
        msg += 'Failure: You must be an owner or member of '\
             + vgrid_name\
             + ' vgrid to get a list of members/owners/resources'
        return (False, msg, None)

    return (True, msg, [])


def vgrid_list(vgrid_name, group, configuration):
    """Shared helper function to get a list of group entities in vgrid"""

    if group == 'owners':
        name = 'owners'
    elif group == 'members':
        name = 'members'
    elif group == 'resources':
        name = 'resources'
    else:
        return (False, "vgrid_list: unknown 'group'")
    vgrid_parts = vgrid_name.split('/')
    vgrid_dir = ''
    output = []
    for sub_vgrid in vgrid_parts:
        vgrid_dir += '/' + sub_vgrid
        owners_path = configuration.vgrid_home + '/' + vgrid_dir + '/'\
             + name
        (status, msg) = list_items_in_pickled_list(owners_path,
                configuration.logger)
        if status:

            # msg is a list

            output.extend(msg)
        else:
            return (False, msg)
    return (True, output)


def job_fits_res_vgrid(job_vgrid_list, res_vgrid_list):
    """Used by job_fits_resource() in scheduler.
    Return fit status and name of first vgrid from
    res_vgrid_listthat is compatible with a vgrid
    in job_vgrid_list. The returned name is None if
    no compatible match was found.
    """

    for job_vgrid in job_vgrid_list:
        for res_vgrid in res_vgrid_list:
            if vgrid_request_and_job_match(res_vgrid, job_vgrid):
                return (True, res_vgrid)
    return (False, None)


def vgrid_request_and_job_match(resource_vgrid, job_vgrid):
    """Compares resource_vgrid and job_vgrid.
    Return True if job_vgrid fits resource_vgrid.
    A job submitted to a vgrid must be executed by a
    resource from the vgrid.
    """

    resource_vgrid_list = resource_vgrid.split('/')
    job_vgrid_list = job_vgrid.split('/')

    # Default VGrid specified in both job and resource

    if vgrid_is_default(resource_vgrid) and vgrid_is_default(job_vgrid):
        return True

    # allow: resource DALTON, job DALTON/DK

    for (resource_elem, job_elem) in zip(resource_vgrid_list,
            job_vgrid_list):
        if not resource_elem == job_elem:
            return False
    return True


def user_allowed_vgrids(configuration, client_id):
    """Return a list of all VGrids that the user with
    client_id is allowed to access. I.e. the VGrids
    that the user is member or owner of.
    """

    allowed = []
    (status, all_vgrids) = vgrid_list_vgrids(configuration)
    if not status:
        return allowed
    for vgrid in all_vgrids:
        if vgrid_is_owner_or_member(vgrid, client_id,
                                    configuration):
            allowed.append(vgrid)
    return allowed


