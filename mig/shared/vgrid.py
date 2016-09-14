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

from shared.defaults import default_vgrid, keyword_all, csrf_field
from shared.findtype import is_user, is_resource
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.listhandling import list_items_in_pickled_list
from shared.modified import mark_vgrid_modified
from shared.serial import load, dump
from shared.validstring import valid_dir_input

# Default value for integer limits in vgrid settings
default_vgrid_settings_limit = 42

def vgrid_add_remove_table(client_id,
                           vgrid_name, 
                           item_string, 
                           script_suffix, 
                           configuration,
                           extra_fields=[],
                           filter_items=[]):
    """Create a table of owners/members/resources/triggers (item_string),
    allowing to remove one item by selecting (radio button) and calling a
    script, and a form to add a new entry.
    Used from vgrid admin and workflows.

    Arguments: vgrid_name, the vgrid to operate on
               item_string, one of owner, member, resource, trigger
               script_suffix, will be prepended with 'add' and 'rm' for forms
               configuration, for loading the list of current items 
               extra_fields, additional input fields for some item forms
               filter_items, list of found item IDs to filter from results 

    Returns: (Bool, list of output_objects)
    """

    out = []

    if not item_string in ['owner', 'member', 'resource', 'trigger']:
        out.append({'object_type': 'error_text', 'text': 
                    'Internal error: Unknown item type %s.' % item_string
                    })
        return (False, out)

    optional = False

    # Default to dynamic input fields, and override for triggers
    
    id_html_tr = '''<tr><td>
          <div id="dyn%sspares">
          <!-- placeholder for dynamic add %s fields -->
      </div>
      </td></tr>
    ''' % (item_string, item_string)
    
    if item_string == 'resource':
        id_field = 'unique_resource_name'
        optional = True
    elif item_string == 'trigger':
        id_field = 'rule_id'
        optional = True
        id_html_tr = '''<tr>
        <td>ID</td><td>
        <input class="fillwidth padspace" type="text" size=70 name="%s" />
        </td>
        </tr>
        ''' % id_field
    else:
        id_field = 'cert_id'

    id_note_tr = ""
    if item_string in ['owner', 'member']:
        openid_add = ""
        if configuration.user_openid_providers:
            openid_add = "either the OpenID alias or "    
        id_note_tr = """
      <tr>
      <td>
Note: %ss are specified with %s the Distinguished Name (DN) of the user. If in
doubt, just let the user request access and accept it with the
<span class='addlink'></span>-icon in the Pending Requests table below.
      </td>
      </tr>
""" % (item_string, openid_add)

    # read list of current items and create form to remove one

    (list_status, inherit) = vgrid_list(vgrid_name, '%ss' % item_string,
                                        configuration, recursive=True,
                                        allow_missing=optional,
                                        filter_entries=filter_items)
    if not list_status:
        out.append({'object_type': 'error_text', 'text': inherit})
        return (False, out)
    (list_status, direct) = vgrid_list(vgrid_name, '%ss' % item_string,
                                       configuration, recursive=False,
                                       allow_missing=optional,
                                       filter_entries=filter_items)
    if not list_status:
        out.append({'object_type': 'error_text', 'text': direct})
        return (False, out)

    extra_titles_html = ''
    for (field, _) in extra_fields:
        extra_titles_html += '<th>%s</th>' % field.replace('_', ' ').title()

    fill_helpers = {'item': item_string, 'vgrid': vgrid_name, 'extra_titles':
                    extra_titles_html, 'vgrid_label':
                    configuration.site_vgrid_label}
    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers.update({'form_method': form_method, 'csrf_field': csrf_field,
                         'csrf_limit': csrf_limit})

    # success, so direct and inherit are lists of unique user/res/trigger IDs
    extras = [i for i in inherit if not i in direct]
    if extras:
        table = '''
        <br />
        Inherited %(item)ss of %(vgrid)s:
        <table class="vgrid%(item)s">
          <thead><tr><th></th><th>%(item)s</th>%(extra_titles)s</thead>
          <tbody>
''' % fill_helpers

        for elem in extras:
            extra_fields_html = ''
            if isinstance(elem, dict) and elem.has_key(id_field):
                for (field, _) in extra_fields:
                    val = elem.get(field, '')
                    if isinstance(val, bool):
                        val = str(val)
                    elif not isinstance(val, basestring):
                        val = ' '.join(val)
                    extra_fields_html += '<td>%s</td>' % val
                table += \
"""          <tr><td></td><td>%s</td>%s</tr>""" % (elem[id_field],
                                                   extra_fields_html)
            elif elem:
                table += \
"          <tr><td></td><td>%s</td></tr>"\
                     % elem
        table += '''
        </tbody></table>
'''
        out.append({'object_type': 'html_form', 'text': table})

    # TODO: add remove vgrid button if only inherited owners
    if direct:
        target_op = 'rm%s' % script_suffix
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

        form = '''
      <form method="%(form_method)s" action="%(target_op)s.py">
        <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
        <input type="hidden" name="vgrid_name" value="%(vgrid)s" />
        Current %(item)ss of %(vgrid)s:
        <table class="vgrid%(item)s">
          <thead><tr><th>Remove</th><th>%(item)s</th>%(extra_titles)s</thead>
          <tbody>
''' % fill_helpers

        for elem in direct:
            extra_fields_html = ''
            if isinstance(elem, dict) and elem.has_key(id_field):
                for (field, _) in extra_fields:
                    val = elem.get(field, '')
                    if isinstance(val, bool):
                        val = str(val)
                    elif not isinstance(val, basestring):
                        val = ' '.join(val)
                    extra_fields_html += '<td>%s</td>' % val
                form += \
"""          <tr><td><input type=radio name='%s' value='%s' /></td>
                 <td>%s</td>%s</tr>""" % (id_field, elem[id_field],
                 elem[id_field], extra_fields_html)
            elif elem:
                form += \
"""          <tr><td><input type=radio name='%s' value='%s' /></td>
                 <td>%s</td></tr>""" % (id_field, elem, elem)

        form += '''
        </tbody></table>
        <input type="submit" value="Remove %(item)s" />
      </form>
''' % fill_helpers
                    
        out.append({'object_type': 'html_form', 'text': form})

    # form to add a new item

    extra_fields_html = ''
    for (field, limit) in extra_fields:
        extra_fields_html += '<tr><td>%s</td><td>' % \
                             field.replace('_', ' ').title()
        if isinstance(limit, basestring):
            add_html = '%s' % limit
        elif limit == None:
            add_html = '''
        <input class="fillwidth padspace" type="text" size=70 name="%s" />
        ''' % field
        else:
            multiple = ''
            if keyword_all in limit:
                multiple = 'multiple'
            add_html = '<select %s name="%s">' % (multiple, field)
            for val in limit:
                add_html += '<option value="%s">%s</option>' % (val, val)
            add_html += '</select>'
        extra_fields_html += add_html + '</td></tr>'

    fill_helpers.update({'id_note_tr': id_note_tr,
                         'id_html_tr': id_html_tr,
                         'extra_fields': extra_fields_html
                         })
    target_op = 'add%s' % script_suffix
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    out.append({'object_type': 'html_form', 'text': '''
      <form method="%(form_method)s" action="%(target_op)s.py">
      <fieldset>
      <legend>Add %(vgrid_label)s %(item)s</legend>
      <input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
      <input type="hidden" name="vgrid_name" value="%(vgrid)s" />
      <table>
      %(id_note_tr)s
      %(id_html_tr)s
      <tr><td>
      %(extra_fields)s<br />
      </td></tr>
      <tr><td>
      <input type="submit" value="Add %(item)s" />
      </td></tr>
      </table>
      </fieldset>
      </form>
''' % fill_helpers})
    
    return (True, out)


def vgrid_is_default(vgrid):
    """Check if supplied vgrid matches any of the names
    associated with the default vgrid"""

    if not vgrid or vgrid.upper() == default_vgrid.upper():
        return True
    else:
        return False


def vgrid_is_owner_or_member(vgrid_name, client_id, configuration):
    """Combines owner and member check"""

    if vgrid_is_owner(vgrid_name, client_id, configuration) or \
           vgrid_is_member(vgrid_name, client_id, configuration):
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
    allow_missing=False
    ):
    """Return True if specified entity_id is in group
    ('owners', 'members', 'resources', 'triggers', 'settings', 'sharelinks', 
    'imagesettings') of vgrid.
    If recursive is True the entities from parent vgrids will be included. The
    optional dict_field is used to check against the trigger case where entries
    are dicts rather than raw strings.
    The allow_missing flag can be used to let the listing proceed even if one
    or more parent vgrids don't have the particular entity group file.
    """

    # Get the list of entities of specified type (group) in vgrid (vgrid_name)

    (status, entries) = vgrid_list(vgrid_name, group, configuration, recursive,
                                   allow_missing)

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


def vgrid_is_trigger(vgrid_name, rule_id, configuration, recursive=True,
                     allow_missing=True):
    """Check if rule_id is a trigger in vgrid_name. We allow missing
    parent pickle to support autonomous multi-frontend systems.
    """

    return vgrid_is_entity_in_list(vgrid_name, rule_id, 'triggers',
                                   configuration, recursive, 'rule_id',
                                   allow_missing)


def vgrid_is_trigger_owner(vgrid_name, rule_id, client_id, configuration,
                           recursive=True, allow_missing=True):
    """Check if rule_id is a trigger in vgrid_name with client_id as rule
    owner. We allow missing parent pickle to support autonomous multi-frontend
    systems.
    """

    (status, entries) = vgrid_list(vgrid_name, 'triggers', configuration,
                                   recursive, allow_missing)

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
                

def vgrid_is_setting(vgrid_name, option_id, configuration, recursive=True,
                     allow_missing=True):
    """Check if option_id is a setting in vgrid_name. We allow missing
    parent pickle to support autonomous multi-frontend systems.
    """

    return vgrid_is_entity_in_list(vgrid_name, option_id, 'settings',
                                   configuration, recursive, 'option_id',
                                   allow_missing)

def vgrid_is_sharelink(vgrid_name, option_id, configuration, recursive=True,
                       allow_missing=True):
    """Check if option_id is a sharelink in vgrid_name. We allow missing
    parent pickle to support autonomous multi-frontend systems.
    """

    return vgrid_is_entity_in_list(vgrid_name, option_id, 'sharelinks',
                                   configuration, recursive, 'option_id',
                                   allow_missing)

def vgrid_is_imagesetting(vgrid_name, option_id, configuration, recursive=True,
                          allow_missing=True):
    """Check if option_id is a imagesetting in vgrid_name. We allow missing
    parent pickle to support autonomous multi-frontend systems.
    """

    return vgrid_is_entity_in_list(vgrid_name, option_id, 'imagesettings',
                                   configuration, recursive, 'option_id',
                                   allow_missing)

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
    elif subject_type == 'request':
        vgrid_base = os.path.join(configuration.vgrid_home, vgrid_name)
        if not valid_dir_input(vgrid_base, subject):
            msg += 'Illegal subject: %s' % subject
            return (False, msg, None)
    elif subject_type in ('trigger', 'settings', ):
        # Rules are checked later
        pass
    elif subject_type in ('sharelinks', ):
        # No direct access to vgrid sharelinks (implicit with create/remove)
        pass
    elif subject_type in ('imagesettings', ):
        # No direct access to vgrid imagesettings (implicit with create/remove)
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
             + ' vgrid to get a list of members/owners/resources/triggers/settings/sharelinks/imagesettings'
        return (False, msg, None)

    return (True, msg, [])


def vgrid_list(vgrid_name, group, configuration, recursive=True,
               allow_missing=False, filter_entries=[]):
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
    elif group == 'imagesettings':
        name = configuration.vgrid_imagesettings
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
                # We allow filtering e.g. system triggers here
                for filter_item in filter_entries:
                    if isinstance(filter_item, tuple):
                        (key, val) = filter_item
                        msg = [entry for entry in msg if not \
                               re.match(val, entry[key])]
                    else:
                        msg = [entry for entry in msg if not \
                               re.match(filter_item, entry)]

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
    if not isinstance(output, basestring) and as_dict:
        output = dict(output)
    return (status, output)

def vgrid_sharelinks(vgrid_name, configuration, recursive=True,
                     allow_missing=True):
    """Extract sharelinks list for a vgrid"""
    return vgrid_list(vgrid_name, 'sharelinks', configuration, recursive,
                      allow_missing)

def vgrid_imagesettings(vgrid_name, configuration, recursive=True,
                     allow_missing=True):
    """Extract imagesettings list for a vgrid"""
    return vgrid_list(vgrid_name, 'imagesettings', configuration, recursive,
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
    elif kind == 'imagesettings':
        entity_filename = configuration.vgrid_imagesettings
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

def vgrid_add_imagesettings(configuration, vgrid_name, id_list, update_id=None):
    """Append id_list to pickled list of imagesettings for vgrid_name"""
    return vgrid_add_entities(configuration, vgrid_name, 'imagesettings',
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
    elif kind == 'imagesettings':
        entity_filename = configuration.vgrid_imagesettings
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

def vgrid_remove_imagesettings(configuration, vgrid_name, id_list,
                          allow_empty=True):
    """Remove id_list from pickled list of imagesettings for vgrid_name"""
    return vgrid_remove_entities(configuration, vgrid_name, 'imagesettings',
                                 id_list, allow_empty, dict_field='imagesetting_id')

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
    elif kind == 'imagesettings':
        entity_filename = configuration.vgrid_imagesettings
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

def vgrid_set_imagesettings(configuration, vgrid_name, id_list, allow_empty=False):
    """Set list of imagesettings for given vgrid"""
    return vgrid_set_entities(configuration, vgrid_name, 'imagesettings',
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

def __in_vgrid_special(configuration, path, vgrid_special_base):
    """Helper function to detect subvgrid public/private web hosting dirs and
    vgrid shares.
    Checks if path is really inside a vgrid special folder with home in
    vgrid_special_base, and returns the name of the deepest such sub-vgrid it
    is inside if so.
    """
    vgrid_path = None
    vgrid_home = configuration.vgrid_home
    real_path = os.path.realpath(path)
    configuration.logger.debug("in vgrid special %s vs %s" % \
                               (real_path, vgrid_special_base))
    if real_path.startswith(vgrid_special_base):
        vgrid_path = real_path.replace(vgrid_special_base, '').lstrip(os.sep)
        while vgrid_path != os.sep:
            if os.path.isdir(os.path.join(vgrid_home, vgrid_path)):
                configuration.logger.debug("in vgrid special found %s" % \
                                           vgrid_path)
                break
            vgrid_path = os.path.dirname(vgrid_path)
    return vgrid_path

def in_vgrid_share(configuration, path):
    """Checks if path is inside a vgrid share and returns the name of the
    deepest such sub-vgrid it is inside if so.
    """
    return __in_vgrid_special(configuration, path,
                              configuration.vgrid_files_home)

def in_vgrid_priv_web(configuration, path):
    """Checks if path is inside a vgrid priv web dir and returns the name of
    the deepest such sub-vgrid it is inside if so.
    """
    return __in_vgrid_special(configuration, path,
                              configuration.vgrid_private_base)

def in_vgrid_pub_web(configuration, path):
    """Checks if path is inside a vgrid pub web dir and returns the name of
    the deepest such sub-vgrid it is inside if so.
    """
    return __in_vgrid_special(configuration, path,
                              configuration.vgrid_public_base)

def _shared_allow_adm(configuration, vgrid_name, client_id, target):
    """Check if client_id is allowed to edit target values for vgrid_name. This
    requires that client_id is an owner of vgrid_name and that any saved vgrid
    settings for that vgrid don't restrict administration to only a subset of
    owners excluding client_id.
    """
    _logger = configuration.logger
    (owners_status, owners) = vgrid_owners(vgrid_name, configuration)
    if not owners_status:
        _logger.error("failed to load owners for %s: %s" % (vgrid_name,
                                                            owners))
        return (False, 'could not load owners list')
    (load_status, settings) = vgrid_settings(vgrid_name, configuration,
                                             as_dict=True)
    if not load_status:
        _logger.error("failed to load settings for %s: %s" % (vgrid_name,
                                                              settings))
        return (False, 'could not load settings')
    restrict_adm = settings.get('restrict_%s_adm' % target,
                                default_vgrid_settings_limit)
    if restrict_adm > 0 and not client_id in owners[:restrict_adm]:
        _logger.error("%s is not allowed to admin %s for %s: %s (%s)" % \
                      (client_id, target, vgrid_name, owners, settings))
        msg = '%s settings only allow the first %d owner(s) to edit %s' % \
              (configuration.site_vgrid_label, restrict_adm, target)
        return (False, msg)
    _logger.debug("%s is allowed to admin %s for %s: %s (%s)" % \
                      (client_id, target, vgrid_name, owners, settings))
    return (True, '')

def allow_settings_adm(configuration, vgrid_name, client_id):
    """Check if client_id is allowed to edit settings for vgrid"""
    return _shared_allow_adm(configuration, vgrid_name, client_id, 'settings')

def allow_owners_adm(configuration, vgrid_name, client_id):
    """Check if client_id is allowed to edit owners for vgrid"""
    return _shared_allow_adm(configuration, vgrid_name, client_id, 'owners')

def allow_members_adm(configuration, vgrid_name, client_id):
    """Check if client_id is allowed to edit members for vgrid"""
    return _shared_allow_adm(configuration, vgrid_name, client_id, 'members')

def allow_resources_adm(configuration, vgrid_name, client_id):
    """Check if client_id is allowed to edit resources for vgrid"""
    return _shared_allow_adm(configuration, vgrid_name, client_id, 'resources')
