#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgrid - helper functions related to VGrid actions
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

"""VGrid specific helper functions"""

import fnmatch
import os
import re

from shared.defaults import default_vgrid
from shared.findtype import is_user, is_resource
from shared.listhandling import list_items_in_pickled_list
from shared.modified import mark_vgrid_modified
from shared.serial import load, dump
from shared.validstring import valid_dir_input


def vgrid_is_default(vgrid):
    """Check if supplied vgrid matches any of the names
    associated with the default vgrid"""

    if not vgrid or vgrid.upper() == default_vgrid.upper():
        return True
    else:
        return False


def vgrid_is_owner_or_member(vgrid_name, client_id, configuration):
    """Combines owner and member check"""

    if vgrid_is_owner(vgrid_name, client_id, configuration)\
         or vgrid_is_member(vgrid_name, client_id, configuration):
        return True
    else:
        return False

def vgrid_allowed(client_id, allowed_pattern):
    """Helper function to check if client_id is allowed using
    allowed_pattern list.
    """
    for pattern in allowed_pattern:

        # Use fnmatch to accept direct hits as well as wild card matches

        if fnmatch.fnmatch(client_id, pattern):
            return True
    return False

def vgrid_is_entity_in_list(
    vgrid_name,
    entity_id,
    group,
    configuration,
    recursive,
    dict_field=False,
    ):
    """Return True if specified entity_id is in group
    ('owners', 'members', 'resources', 'triggers', 'settings', 'sharelinks') of
    vgrid.
    If recursive is True the entities from parent vgrids will be included. The
    optional dict_field is used to check against the trigger case where entries
    are dicts rather than raw strings.
    """

    # Get the list of entities of specified type (group) in vgrid (vgrid_name)

    (status, entries) = vgrid_list(vgrid_name, group, configuration, recursive)

    if not status:
        configuration.logger.error(
            'unexpected status in vgrid_is_entity_in_list: %s' % entries)
        return False

    if dict_field:
        entries = [i[dict_field] for i in entries]
        
    return vgrid_allowed(entity_id, entries)

def vgrid_is_owner(vgrid_name, client_id, configuration, recursive=True):
    """Check if client_id is an owner of vgrid_name. Please note
    that nobody owns the default vgrid.
    """

    if vgrid_is_default(vgrid_name):
        return False
    return vgrid_is_entity_in_list(vgrid_name, client_id, 'owners',
                                   configuration, recursive)


def vgrid_is_member(vgrid_name, client_id, configuration, recursive=True):
    """Check if client_id is a member of vgrid_name. Please note
    that everybody is a member of the default vgrid.
    """

    if vgrid_is_default(vgrid_name):
        return True
    return vgrid_is_entity_in_list(vgrid_name, client_id, 'members',
                                   configuration, recursive)


def vgrid_is_resource(vgrid_name, res_id, configuration, recursive=True):
    """Check if res_id is a resource in vgrid_name. Please note
    that everyone is a member of the default vgrid.
    They still explicitly have to sign up to accept jobs
    from it, though.
    """

    if vgrid_is_default(vgrid_name):
        return True
    return vgrid_is_entity_in_list(vgrid_name, res_id, 'resources',
                                   configuration, recursive)


def vgrid_is_trigger(vgrid_name, rule_id, configuration, recursive=True):
    """Check if rule_id is a trigger in vgrid_name"""

    return vgrid_is_entity_in_list(vgrid_name, rule_id, 'triggers',
                                   configuration, recursive, 'rule_id')


def vgrid_is_trigger_owner(vgrid_name, rule_id, client_id, configuration,
                           recursive=True):
    """Check if rule_id is a trigger in vgrid_name with client_id as rule
    owner.
    """

    (status, entries) = vgrid_list(vgrid_name, 'triggers', configuration, recursive)

    if not status:
        configuration.logger.error(
            'unexpected status in vgrid_is_trigger_owner: %s' % entries)
        return False

    for rule_dict in entries:
        if rule_dict['rule_id'] == rule_id:
            if rule_dict['run_as'] == client_id:
                return True
            else:
                return False

    # No such trigger

    return False
                

def vgrid_is_setting(vgrid_name, option_id, configuration, recursive=True):
    """Check if option_id is a setting in vgrid_name"""

    return vgrid_is_entity_in_list(vgrid_name, option_id, 'settings',
                                   configuration, recursive, 'option_id')

def vgrid_is_sharelink(vgrid_name, option_id, configuration, recursive=True):
    """Check if option_id is a sharelink in vgrid_name"""

    return vgrid_is_entity_in_list(vgrid_name, option_id, 'sharelinks',
                                   configuration, recursive, 'option_id')


def vgrid_list_subvgrids(vgrid_name, configuration):
    """Return list of subvgrids of vgrid_name"""

    result_list = []
    (status, all_vgrids_list) = vgrid_list_vgrids(configuration)

    if not status:

        return (False, 'could not get list of all vgrids on server')

    for vgrid in all_vgrids_list:

        # sub-vgrids have a prefix vgrid_name + os.sep.
        # os.sep has been added to filter out siblings with this prefix.

        if vgrid.startswith(vgrid_name + os.sep):
            result_list.append(vgrid)

    return (True, result_list)


def vgrid_list_parents(vgrid_name, configuration):
    """Return list of parent vgrids of vgrid_name listed with root first"""

    result_list = []
    parts = vgrid_name.split(os.sep)
    for i in xrange(len(parts)-1):
        vgrid = (os.sep).join(parts[:i+1])
        result_list.append(vgrid)
    return result_list


def vgrid_list_vgrids(configuration):
    """List all vgrids and sub-vgrids created on the system"""

    vgrids_list = []
    for (root, dirs, _) in os.walk(configuration.vgrid_home):

        # skip all dot dirs - they are from repos etc and _not_ vgrids

        if root.find(os.sep + '.') != -1:
            continue
        dirs = [name for name in dirs if not name.startswith('.')]

        for directory in dirs:

            # strip vgrid_home prefix to get entire vgrid name (/diku/sub/grid)

            complete_vgrid_location = os.path.join(root, directory)
            vgrid_name_without_location = \
                complete_vgrid_location.replace(configuration.vgrid_home,
                    '', 1)

            vgrids_list.append(vgrid_name_without_location)
    if not default_vgrid in vgrids_list:
        vgrids_list.append(default_vgrid)
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

    if subject_type == 'member' or subject_type == 'owner':
        if not is_user(subject, configuration.mig_server_home):
            msg += '%s is not a valid %s user!' % \
                    (subject, configuration.short_title)
            return (False, msg, None)
    elif subject_type == 'resource':
        if not is_resource(subject, configuration.resource_home):
            msg += '%s is not a valid %s resource' % \
                    (subject, configuration.short_title)
            msg += \
                ' (OK, if removing or e.g. the resource creation is pending)'
    elif subject_type in ('trigger', 'settings', ):
        # Rules are checked later
        pass
    elif subject_type in ('sharelinks', ):
        # No direct access to vgrid sharelinks (implicit with create/remove)
        pass
    else:
        msg += 'unknown subject type in init_vgrid_script_add_rem'
        return (False, msg, [])

    # special case: members may terminate own membership

    if (subject_type == 'member') and (client_id == subject) \
        and (vgrid_is_member(vgrid_name, subject, configuration)):

        return (True, msg, [])

    # special case: members may remove own triggers and add new ones

    if (subject_type == 'trigger') and \
           (not vgrid_is_trigger(vgrid_name, subject, configuration) or \
            vgrid_is_trigger_owner(vgrid_name, subject, client_id,
                                   configuration)):
        return (True, msg, [])

    # otherwise: only owners may add or remove:

    if not vgrid_is_owner(vgrid_name, client_id, configuration):
        msg += 'You must be an owner of the %s vgrid to modify %s' % \
               (vgrid_name, subject_type)
        return (False, msg, None)

    return (True, msg, [])


def init_vgrid_script_list(vgrid_name, client_id, configuration):
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
             + ' vgrid to get a list of members/owners/resources/triggers/settings/sharelinks'
        return (False, msg, None)

    return (True, msg, [])


def vgrid_list(vgrid_name, group, configuration, recursive=True,
               allow_missing=False):
    """Shared helper function to get a list of group entities in vgrid. The
    optional recursive argument is used to switch between direct vgrid and
    recursive vgrid operation including entities from parent vgrids.
    If allow_missing is set a missing entity file does not prevent success or
    change the output list.
    """
    if group == 'owners':
        name = configuration.vgrid_owners
    elif group == 'members':
        name = configuration.vgrid_members
    elif group == 'resources':
        name = configuration.vgrid_resources
    elif group == 'triggers':
        name = configuration.vgrid_triggers
    elif group == 'settings':
        name = configuration.vgrid_settings
    elif group == 'sharelinks':
        name = configuration.vgrid_sharelinks
    else:
        return (False, "vgrid_list: unknown group: '%s'" % group)
    if recursive:
        vgrid_parts = vgrid_name.split('/')
    else:
        vgrid_parts = [vgrid_name]
    vgrid_dir = ''
    output = []
    for sub_vgrid in vgrid_parts:
        vgrid_dir = os.path.join(vgrid_dir, sub_vgrid)
        name_path = os.path.join(configuration.vgrid_home, vgrid_dir, name)
        (status, msg) = list_items_in_pickled_list(name_path,
                configuration.logger, allow_missing)
        if status:

            # msg is a list

            # We sometimes find singleton lists containing an empty
            # string. Reason is historic python type confusion(tm),
            # namely using the empty list as an error indicator, on
            # the way down through listhandling, fileio, and serial.
            # The empty lists are put in at createvgrid.py.

            if msg != ['']:
                output.extend(msg)
        elif allow_missing and not os.path.exists(name_path):
            continue
        else:
            return (False, msg)
    return (True, output)

def vgrid_owners(vgrid_name, configuration, recursive=True):
    """Extract owners list for a vgrid"""
    return vgrid_list(vgrid_name, 'owners', configuration, recursive)

def vgrid_members(vgrid_name, configuration, recursive=True):
    """Extract members list for a vgrid"""
    return vgrid_list(vgrid_name, 'members', configuration, recursive)

def vgrid_resources(vgrid_name, configuration, recursive=True):
    """Extract resources list for a vgrid"""
    return vgrid_list(vgrid_name, 'resources', configuration, recursive)

def vgrid_triggers(vgrid_name, configuration, recursive=True,
                   allow_missing=True):
    """Extract triggers list for a vgrid"""
    return vgrid_list(vgrid_name, 'triggers', configuration, recursive,
                      allow_missing)

def vgrid_settings(vgrid_name, configuration, recursive=True, allow_missing=True,
                   as_dict=False):
    """Extract settings list for a vgrid"""
    (status, output)= vgrid_list(vgrid_name, 'settings', configuration,
                                 recursive, allow_missing)
    if not isinstance(output, basestring):
        output = dict(output)
    return (status, output)

def vgrid_sharelinks(vgrid_name, configuration, recursive=True,
                     allow_missing=True):
    """Extract sharelinks list for a vgrid"""
    return vgrid_list(vgrid_name, 'sharelinks', configuration, recursive,
                      allow_missing)

def vgrid_match_resources(vgrid_name, resources, configuration):
    """Return a list of resources filtered to only those allowed in
    the provided vgrid.
    """

    match = []
    for entry in resources:
        if entry in match:
            continue
        if vgrid_is_resource(vgrid_name, entry, configuration):
            match.append(entry)
    return match
    

def job_fits_res_vgrid(job_vgrid_list, res_vgrid_list):
    """Used to find match between job and resource vgrids.
    Return a 3-tuple of boolean fit status and the first job and resource
    vgrid names that are compatible. A job vgrid matches parent resource
    vgrids due to inheritance so it is useful to get both names back. The
    returned names are None if no compatible match was found.
    """

    for job_vgrid in job_vgrid_list:
        for res_vgrid in res_vgrid_list:
            if vgrid_request_and_job_match(res_vgrid, job_vgrid):
                return (True, job_vgrid, res_vgrid)
    return (False, None, None)


def vgrid_request_and_job_match(resource_vgrid, job_vgrid):
    """Compares resource_vgrid and job_vgrid.
    Return True if job_vgrid fits resource_vgrid.
    A job submitted to a vgrid must be executed by a
    resource from that vgrid or a parent vgrid.
    """

    resource_vgrid_list = resource_vgrid.split('/')
    job_vgrid_list = job_vgrid.split('/')

    # Default VGrid specified in both job and resource

    if vgrid_is_default(resource_vgrid) and vgrid_is_default(job_vgrid):
        return True

    # allow: resource DALTON, job DALTON/DK

    for (resource_elem, job_elem) in zip(resource_vgrid_list,
            job_vgrid_list):
        if resource_elem != job_elem:
            return False
    return True

def user_allowed_vgrids(configuration, client_id, inherited=False):
    """Return a list of all VGrids that the user with
    client_id is allowed to access. I.e. the VGrids
    that the user is member or owner of.
    The optional inherited argument is used to add any parent vgrids to match
    inherited access to resources in parent vgrids.
    """

    allowed = []
    (status, all_vgrids) = vgrid_list_vgrids(configuration)
    if not status:
        return allowed
    for vgrid in all_vgrids:
        if vgrid_is_owner_or_member(vgrid, client_id, configuration):
            if inherited:
                allowed += vgrid_list_parents(vgrid, configuration)
            allowed.append(vgrid)
    return allowed

def res_allowed_vgrids(configuration, client_id):
    """Return a list of all VGrids that the resource with
    client_id is allowed to access. I.e. the VGrids
    that the resource is member of.
    Please note that the private (non-anonymized) ID is expected here.
    """

    allowed = []
    (status, all_vgrids) = vgrid_list_vgrids(configuration)
    if not status:
        return allowed
    for vgrid in all_vgrids:
        if vgrid_is_resource(vgrid, client_id, configuration):
            allowed.append(vgrid)
    return allowed

def vgrid_access_match(configuration, job_owner, job, res_id, res):
    """Match job and resource vgrids and include access control.
    The job_owner and res_id are used directly in vgrid access checks
    so it is important that res_id is on the private (not anonymized)
    form.
    """
    # Keep trying with job_fits_res_vgrid until a valid vgrid is found
    # or it gives up. In the common case with many correctly configured
    # vgrids, this lazy strategy is far more efficient than checking all
    # vgrids requested every time.
    job_req = [i for i in job.get('VGRID', [])]
    res_req = [i for i in res.get('VGRID', [])]
    while True:
        answer = (found, best_job, best_res) = job_fits_res_vgrid(job_req,
                                                                  res_req)
        if not found:
            configuration.logger.info('no valid vgrid found!')
            break
        configuration.logger.info('test if best vgrids %s , %s are valid' % \
                                  (best_job, best_res))
        if not vgrid_is_owner_or_member(best_job, job_owner, configuration):
            configuration.logger.info('del invalid vgrid %s from job (%s)' % \
                                      (best_job, job_owner))
            job_req = [i for i in job_req if i != best_job]
        if not vgrid_is_resource(best_res, res_id, configuration):
            configuration.logger.info('del invalid vgrid %s from res (%s)' \
                                      % (best_res, res_id))
            res_req = [i for i in res_req if i != best_res]
        else:
            break
    return answer

def vgrid_add_entities(configuration, vgrid_name, kind, id_list, update_id=None):
    """Append list of IDs to pickled list of kind for vgrid_name"""

    if kind == 'owners':
        entity_filename = configuration.vgrid_owners
    elif kind == 'members':
        entity_filename = configuration.vgrid_members
    elif kind == 'resources':
        entity_filename = configuration.vgrid_resources
    elif kind == 'triggers':
        entity_filename = configuration.vgrid_triggers
    elif kind == 'settings':
        entity_filename = configuration.vgrid_settings
    elif kind == 'sharelinks':
        entity_filename = configuration.vgrid_sharelinks
    else:
        return (False, "vgrid_add_entities: unknown kind: '%s'" % kind)

    entity_filepath = os.path.join(configuration.vgrid_home, vgrid_name, 
                                   entity_filename)
    try:
        if os.path.exists(entity_filepath):
            entities = load(entity_filepath)
        else:
            entities = []
            log_msg = "creating missing file: '%s'" % (entity_filepath)
            configuration.logger.info(log_msg)

        if update_id is None:
            configuration.logger.info("adding new %s: %s" % (kind, id_list))
            entities += [i for i in id_list if not i in entities]
        else:
            # A trigger with same id exists and needs to be updated
            updating = [i[update_id] for i in id_list]
            entities = [i for i in entities if not i[update_id] in updating]
            configuration.logger.info("adding updated %s: %s (%s)" % \
                                      (kind, id_list, entities))
            entities += id_list
        dump(entities, entity_filepath)
        mark_vgrid_modified(configuration, vgrid_name)
        return (True, '')
    except Exception, exc:
        return (False, "could not add %s for %s: %s" % (kind, vgrid_name, exc))

def vgrid_add_owners(configuration, vgrid_name, id_list):
    """Append id_list to pickled list of owners for vgrid_name"""
    return vgrid_add_entities(configuration, vgrid_name, 'owners',
                              id_list)

def vgrid_add_members(configuration, vgrid_name, id_list):
    """Append id_list to pickled list of members for vgrid_name"""
    return vgrid_add_entities(configuration, vgrid_name, 'members',
                              id_list)

def vgrid_add_resources(configuration, vgrid_name, id_list):
    """Append id_list to pickled list of resources for vgrid_name"""
    return vgrid_add_entities(configuration, vgrid_name, 'resources',
                              id_list)

def vgrid_add_triggers(configuration, vgrid_name, id_list, update_id=None):
    """Append id_list to pickled list of triggers for vgrid_name"""
    return vgrid_add_entities(configuration, vgrid_name, 'triggers',
                              id_list, update_id)

def vgrid_add_settings(configuration, vgrid_name, id_list, update_id=None):
    """Append id_list to pickled list of settings for vgrid_name"""
    return vgrid_add_entities(configuration, vgrid_name, 'settings',
                              id_list, update_id)

def vgrid_add_sharelinks(configuration, vgrid_name, id_list, update_id=None):
    """Append id_list to pickled list of sharelinks for vgrid_name"""
    return vgrid_add_entities(configuration, vgrid_name, 'sharelinks',
                              id_list, update_id)

def vgrid_remove_entities(configuration, vgrid_name, kind, id_list,
                          allow_empty, dict_field=False):
    """Remove list of IDs from pickled list of kind for vgrid_name.
    The allow_empty argument can be used to prevent removal of e.g. the last
    owner.
    Use the dict_field if the entries are dictionaries and the id_list should
    be matched against dict_field in each of them. 
    """

    if kind == 'owners':
        entity_filename = configuration.vgrid_owners
    elif kind == 'members':
        entity_filename = configuration.vgrid_members
    elif kind == 'resources':
        entity_filename = configuration.vgrid_resources
    elif kind == 'triggers':
        entity_filename = configuration.vgrid_triggers
    elif kind == 'settings':
        entity_filename = configuration.vgrid_settings
    elif kind == 'sharelinks':
        entity_filename = configuration.vgrid_sharelinks
    else:
        return (False, "vgrid_remove_entities: unknown kind: '%s'" % kind)
    
    entity_filepath = os.path.join(configuration.vgrid_home, vgrid_name, 
                                   entity_filename)

    # Force raw string to list to avoid nasty silent substring matching below
    # I.e. removing abc.def.0 would also remove def.0
    
    if isinstance(id_list, basestring):
        id_list = [id_list]
        
    try:
        entities = load(entity_filepath)
        if dict_field:
            entities = [i for i in entities if not i[dict_field] in id_list]
        else:
            entities = [i for i in entities if not i in id_list]
        if not entities and not allow_empty:
            raise ValueError("not allowed to remove last entry of %s" % kind)
        dump(entities, entity_filepath)
        mark_vgrid_modified(configuration, vgrid_name)
        return (True, '')
    except Exception, exc:
        return (False, "could not remove %s for %s: %s" % (kind, vgrid_name,
                                                           exc))

def vgrid_remove_owners(configuration, vgrid_name, id_list, allow_empty=False):
    """Remove id_list from pickled list of owners for vgrid_name"""
    return vgrid_remove_entities(configuration, vgrid_name, 'owners',
                                 id_list, allow_empty)

def vgrid_remove_members(configuration, vgrid_name, id_list, allow_empty=True):
    """Remove id_list from pickled list of members for vgrid_name"""
    return vgrid_remove_entities(configuration, vgrid_name, 'members',
                                 id_list, allow_empty)

def vgrid_remove_resources(configuration, vgrid_name, id_list,
                           allow_empty=True):
    """Remove id_list from pickled list of resources for vgrid_name"""
    return vgrid_remove_entities(configuration, vgrid_name, 'resources',
                                 id_list, allow_empty)

def vgrid_remove_triggers(configuration, vgrid_name, id_list,
                           allow_empty=True):
    """Remove id_list from pickled list of triggers for vgrid_name"""
    return vgrid_remove_entities(configuration, vgrid_name, 'triggers',
                                 id_list, allow_empty, dict_field='rule_id')

def vgrid_remove_settings(configuration, vgrid_name, id_list,
                          allow_empty=True):
    """Remove id_list from pickled list of settings for vgrid_name"""
    return vgrid_remove_entities(configuration, vgrid_name, 'settings',
                                 id_list, allow_empty, dict_field='option_id')

def vgrid_remove_sharelinks(configuration, vgrid_name, id_list,
                          allow_empty=True):
    """Remove id_list from pickled list of sharelinks for vgrid_name"""
    return vgrid_remove_entities(configuration, vgrid_name, 'sharelinks',
                                 id_list, allow_empty, dict_field='share_id')

def vgrid_set_entities(configuration, vgrid_name, kind, id_list, allow_empty):
    """Set kind list to provided id_list for given vgrid. The allow_empty
    argument cam be used to e.g. prevent empty owners lists.
    """

    if kind == 'owners':
        entity_filename = configuration.vgrid_owners
    elif kind == 'members':
        entity_filename = configuration.vgrid_members
    elif kind == 'resources':
        entity_filename = configuration.vgrid_resources
    elif kind == 'triggers':
        entity_filename = configuration.vgrid_triggers
    elif kind == 'settings':
        entity_filename = configuration.vgrid_settings
    elif kind == 'sharelinks':
        entity_filename = configuration.vgrid_sharelinks
    else:
        return (False, "vgrid_set_entities: unknown kind: '%s'" % kind)

    entity_filepath = os.path.join(configuration.vgrid_home, vgrid_name, 
                                   entity_filename)

    try:
        if not id_list and not allow_empty:
            raise ValueError("not allowed to set empty list of %s" % kind)
        dump(id_list, entity_filepath)
        mark_vgrid_modified(configuration, vgrid_name)
        return (True, '')
    except Exception, exc:
        return (False, "could not set %s for %s: %s" % (kind, vgrid_name, exc))

def vgrid_set_owners(configuration, vgrid_name, id_list, allow_empty=False):
    """Set list of owners for given vgrid"""
    return vgrid_set_entities(configuration, vgrid_name, 'owners',
                              id_list, allow_empty)

def vgrid_set_members(configuration, vgrid_name, id_list, allow_empty=True):
    """Set list of members for given vgrid"""
    return vgrid_set_entities(configuration, vgrid_name, 'members',
                              id_list, allow_empty)

def vgrid_set_resources(configuration, vgrid_name, id_list, allow_empty=True):
    """Set list of resources for given vgrid"""
    return vgrid_set_entities(configuration, vgrid_name, 'resources',
                              id_list, allow_empty)

def vgrid_set_triggers(configuration, vgrid_name, id_list, allow_empty=True):
    """Set list of triggers for given vgrid"""
    return vgrid_set_entities(configuration, vgrid_name, 'triggers',
                              id_list, allow_empty)

def vgrid_set_settings(configuration, vgrid_name, id_list, allow_empty=False):
    """Set list of settings for given vgrid"""
    return vgrid_set_entities(configuration, vgrid_name, 'settings',
                              id_list, allow_empty)

def vgrid_set_sharelinks(configuration, vgrid_name, id_list, allow_empty=False):
    """Set list of sharelinks for given vgrid"""
    return vgrid_set_entities(configuration, vgrid_name, 'sharelinks',
                              id_list, allow_empty)

def validated_vgrid_list(configuration, job_dict):
    """Grabs VGRID field value from job_dict if available and makes sure that
    it is a non-empty list of strings.
    Fall back to [default_vgrid] if either of the legacy/bogus cases
    - empty string or None
    - no vgrid set
    Convert other plain strings to list format.
    """
    job_vgrids = job_dict.get('VGRID', None)
    if not job_vgrids:
        job_vgrids = [default_vgrid]
    if isinstance(job_vgrids, basestring):
        job_vgrids = [job_vgrids]
    return job_vgrids

def vgrid_create_allowed(configuration, user_dict):
    """Check if user with user_dict is allowed to create vgrid_name based on
    optional configuration limits.
    """
    for (key, val) in configuration.site_vgrid_creators:
        if not re.match(val, user_dict.get(key, 'NO SUCH FIELD')):
            return False
    return True

def in_vgrid_share(configuration, path):
    """Checks if path is inside a vgrid share and return the deepest such
    sub-vgrid it is inside if so.
    """
    vgrid_path = None
    vgrid_files_home = configuration.vgrid_files_home
    vgrid_home = configuration.vgrid_home
    real_path = os.path.realpath(path)
    configuration.logger.debug("in_vgrid_share %s vs %s" % (real_path,
                                                            vgrid_files_home))
    if real_path.startswith(vgrid_files_home):
        vgrid_path = real_path.replace(vgrid_files_home, '').lstrip(os.sep)
        while vgrid_path != os.sep:
            if os.path.isdir(os.path.join(vgrid_home, vgrid_path)):
                configuration.logger.debug("in_vgrid_share found %s" % vgrid_path)
                break
            vgrid_path = os.path.dirname(vgrid_path)
    return vgrid_path
