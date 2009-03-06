#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vgrid - [insert a few words of module description on this line]
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

import os

from shared.listhandling import list_items_in_pickled_list
from shared.validstring import valid_dir_input
from shared.findtype import is_user, is_resource

default_vgrid = "Generic"
any_vgrid = "ANY"

def vgrid_is_default(vgrid):
    """Check if supplied vgrid matches any of the names
    associated with the default vgrid"""
    if not vgrid or vgrid.upper() == default_vgrid.upper():
        return True
    else:
        return False

def vgrid_is_owner_or_member(vgrid_name, cert_name_no_spaces, configuration):   
    if vgrid_is_owner(vgrid_name, cert_name_no_spaces, configuration) or vgrid_is_member(vgrid_name, cert_name_no_spaces, configuration):
        return True
    else:
        return False

"""def vgrid_does_exist(vgrid_name, configuration):
    # does vgrid exist? A valid vgrid must have at least a single owner
    (status, list) = vgrid_list(vgrid_name, "owners", configuration)
    if status == False:
        return False
    elif len(list) == 0:
        return False
    else:
        return True
"""

def vgrid_is_cert_in_list(vgrid_name, cert_name_no_spaces, group, configuration):
    """Return True if specified cert_name_no_spaces is in group
    ('owners', 'members', 'resources') of vgrid.
    """
    (status, list) = vgrid_list(vgrid_name, group, configuration)
    
    if not status:
        # error
        configuration.logger.error("status not True in vgrid_is_cert_in_list: %s" % list)
        return False

    if cert_name_no_spaces in list:
        return True
    else:
        return False
    
def vgrid_is_owner(vgrid_name, cert_name_no_spaces, configuration):
    """Check if cert_name_no_spaces is an owner of vgrid_name. Please note
    that noone is an owner of the default vgrid.
    """
    if vgrid_is_default(vgrid_name):
        return False
    return vgrid_is_cert_in_list(vgrid_name, cert_name_no_spaces, "owners", configuration)

def vgrid_is_member(vgrid_name, cert_name_no_spaces, configuration):
    """Check if cert_name_no_spaces is a member of vgrid_name. Please note
    that everyone is a member of the Generic vgrid.
    """
    # anyone is member of default VGrid
    if vgrid_is_default(vgrid_name):
        return True
    return vgrid_is_cert_in_list(vgrid_name, cert_name_no_spaces, "members", configuration)

def vgrid_is_resource(vgrid_name, cert_name_no_spaces, configuration):
    # all resources are in default VGrid
    if vgrid_is_default(vgrid_name):
        return True
    return vgrid_is_cert_in_list(vgrid_name, cert_name_no_spaces, "resources", configuration)

def vgrid_list_subvgrids(vgrid_name, configuration):
    # return list of subvgrids of vgrid_name
    result_list = []
    (status, all_vgrids_list) = vgrid_list_vgrids(configuration)
    if not status:
        return (False, "could not get list of all vgrids on server")
    for vgrid in all_vgrids_list:
        if vgrid.startswith(vgrid_name) and vgrid_name != vgrid:
            result_list.append(vgrid)
    return (True, result_list)
    
def vgrid_list_vgrids(configuration):
    # list all vgrids and sub-vgrids created on the system
    vgrids_list = []
    for root, dirs, files in os.walk(configuration.vgrid_home):
        for directory in dirs:
            
            ### old check, can be removed when all vgrids on all MiG servers are created with the new vgrid scripts
            if directory == "public_base" or directory == "private_base":
                continue
            ###
            
            #  without vgrid_home location, but the entire vgrid name (dalton/dk/imada)
            complete_vgrid_location = os.path.join(root, directory)
            vgrid_name_without_location = complete_vgrid_location.replace(configuration.vgrid_home, "", 1) 
            
            ### old check, can be removed when all vgrids on all MiG servers are created with the new vgrid scripts 
            if vgrid_name_without_location.find("public_base") != -1 or vgrid_name_without_location.find("private_base") != -1:
                continue
            ###
            
            vgrids_list.append(vgrid_name_without_location)
    return (True, vgrids_list)

def init_vgrid_script_add_rem(vgrid_name, cert_name_no_spaces, subject, subject_type, configuration):
    """Initialize vgrid specific add and remove scripts"""
    msg = ""
    if not vgrid_name:
        msg += "Please specify vgrid_name in the querystring"
        return (False, msg, None)
                
    if not subject:
        msg += "Please provide the name of the %s" % subject_type
        return (False, msg, None)

    if not valid_dir_input(configuration.vgrid_home, vgrid_name):
        msg += "Illegal vgrid_name: %s" % vgrid_name
        return (False, msg, None)

    if not vgrid_is_owner(vgrid_name, cert_name_no_spaces, configuration):
        msg += "You must be an owner of the %s vgrid to add/remove %s" % (vgrid_name, subject_type)
        return (False, msg, None)

    if subject_type == "member" or subject_type == "owner":
        if not is_user(subject, configuration.user_home):
            msg += "%s is not a valid MiG user!" % subject
            return (False, msg, None)
    elif subject_type == "resource":
        if not is_resource(subject, configuration.resource_home):
            msg += "%s is not a valid MiG resource (OK, if removing or if e.g. the resource creation is pending)" % subject
            # return (False, msg, None)
    else:
        msg += "unknown subject type in init_vgrid_script_add_rem"
        return (False, msg, [])
                        
    return (True, msg, [])

def init_vgrid_script_list(vgrid_name, cert_name_no_spaces, configuration):
    msg = ""
    if not vgrid_name:
        msg += "Please specify vgrid_name in the querystring"
        return (False, msg, None)

    if not valid_dir_input(configuration.vgrid_home, vgrid_name):
        msg += "Illegal vgrid_name: %s" % vgrid_name
        return (False, msg, None)

    if not vgrid_is_owner_or_member(vgrid_name, cert_name_no_spaces, configuration):
        msg += "Failure: You must be an owner or member of %s vgrid to get a list of members/owners/resources" % vgrid_name
        return (False, msg, None)
    
    return (True, msg, [])
            
def vgrid_list(vgrid_name, group, configuration):
    if group == "owners":
        file = "owners"
    elif group == "members":
        file = "members"
    elif group == "resources":
        file = "resources"
    else:
        return (False, "vgrid_list: unknown 'group'")
    vgrid_list = vgrid_name.split("/")
    vgrid_dir = ""
    output = []
    for sub_vgrid in vgrid_list:        
        vgrid_dir += "/" + sub_vgrid
        owners_file = configuration.vgrid_home + "/" + vgrid_dir + "/" + file
        (status, msg) = list_items_in_pickled_list(owners_file, configuration.logger)
        if status:
            #msg is a list
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
                return True, res_vgrid
    return False, None

def vgrid_request_and_job_match(resource_vgrid, job_vgrid):
    """Compares resource_vgrid and job_vgrid.
    Return True if job_vgrid fits resource_vgrid.
    A job submitted to a vgrid must be executed by a
    resource from the vgrid.
    """
    resource_vgrid_list = resource_vgrid.split("/")
    job_vgrid_list = job_vgrid.split("/")

    # Default VGrid specified in both job and resource
    if vgrid_is_default(resource_vgrid) and vgrid_is_default(job_vgrid):
        return True
    
    # allow: resource DALTON, job DALTON/DK
    for resource_elem, job_elem in zip(resource_vgrid_list, job_vgrid_list):
        if not resource_elem == job_elem:
            return False
    return True

def user_allowed_vgrids(configuration, cert_name_no_spaces):
    """Return a list of all VGrids that the user with
    cert_name_no_spaces is allowed to access. I.e. the VGrids
    that the user is member or owner of.
    """
    allowed = []
    (status, all_vgrids) = vgrid_list_vgrids(configuration)
    if not status:
        return allowed
    for vgrid in all_vgrids:
        if vgrid_is_owner_or_member(vgrid, cert_name_no_spaces,
                                    configuration):
            allowed.append(vgrid)
    return allowed
