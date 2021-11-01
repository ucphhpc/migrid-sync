#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmvgridowner - remove a vgrid owner
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Remove an owner from a given vgrid"""
from __future__ import absolute_import

import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import csrf_field, keyword_members
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit
from mig.shared.html import html_post_helper
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.parseflags import force
from mig.shared.useradm import get_full_user_map
from mig.shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
    vgrid_is_member, vgrid_owners, vgrid_members, vgrid_resources, \
    vgrid_list_subvgrids, vgrid_remove_owners, vgrid_list_parents, \
    allow_owners_adm, vgrid_settings, vgrid_manage_allowed, \
    vgrid_rm_tracker_admin, vgrid_rm_share, vgrid_rm_web_folders, \
    vgrid_rm_files, vgrid_inherit_files, vgrid_rm_entry
from mig.shared.vgridaccess import unmap_vgrid, unmap_inheritance


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'cert_id': REJECT_UNSET,
                'flags': []}
    return ['text', defaults]


def rm_tracker_admin(configuration, cert_id, vgrid_name, tracker_dir,
                     output_objects):
    """Remove Trac issue tracker owner"""
    _logger = configuration.logger

    (success, msg) = vgrid_rm_tracker_admin(
        configuration, vgrid_name, cert_id, tracker_dir)
    if not success:
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'Could not remove %s tracker admin rights: %s' % (cert_id, msg)
             })

    return success


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Remove %s Owner" % label
    output_objects.append({'object_type': 'header', 'text':
                           'Remove %s Owner' % label})
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    vgrid_name = accepted['vgrid_name'][-1]
    flags = ''.join(accepted['flags'])
    cert_id = accepted['cert_id'][-1]
    cert_dir = client_id_dir(cert_id)
    # inherited vgrid membership
    inherit_vgrid_member = False

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # always allow owner to remove self
    if client_id != cert_id:

        user_map = get_full_user_map(configuration)
        user_dict = user_map.get(client_id, None)
        # Optional site-wide limitation of manage vgrid permission
        if not user_dict or \
                not vgrid_manage_allowed(configuration, user_dict):
            logger.warning("user %s is not allowed to manage vgrids!" %
                           client_id)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'Only privileged users can manage %ss' % label})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # make sure vgrid settings allow this owner to edit other owners
        (allow_status, allow_msg) = allow_owners_adm(configuration, vgrid_name,
                                                     client_id)
        if not allow_status:
            output_objects.append({'object_type': 'error_text', 'text':
                                   allow_msg})
            return (output_objects, returnvalues.CLIENT_ERROR)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, _) = \
        init_vgrid_script_add_rem(vgrid_name, client_id, cert_id,
                                  'owner', configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text': msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't remove if not already an owner

    if not vgrid_is_owner(vgrid_name, cert_id, configuration):
        logger.warning('%s is not allowed to remove owner %s from %s' %
                       (client_id, cert_id, vgrid_name))
        output_objects.append({'object_type': 'error_text', 'text':
                               '%s is not an owner of %s or a parent %s.' %
                               (cert_id, vgrid_name, label)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # we need the local owners file to detect inherited ownerships

    (owners_status, owners_direct) = vgrid_owners(vgrid_name, configuration,
                                                  False)
    (all_status, owners) = vgrid_owners(vgrid_name, configuration, True)
    if not owners_status or not all_status:
        logger.error('Error loading owners for %s: %s / %s'
                     % (vgrid_name, owners_direct, owners))
        output_objects.append(
            {'object_type': 'error_text', 'text':
             'An internal error occurred, error conditions have been logged.'})
        output_objects.append({'object_type': 'text', 'text': '''
         You can help us fix the problem by notifying the administrators
         via mail about what you wanted to do when the error happened.'''})
        return (output_objects, returnvalues.CLIENT_ERROR)

    logger.info('%s removing owner %s from %s' % (client_id, cert_id,
                                                  vgrid_name))

    # find out whether to just remove an owner or delete the whole thing.
    # ask about delete if last or no direct owners.

    if len(owners_direct) > 1:

        logger.debug('Removing %s, one of several owners, from %s.' %
                     (cert_id, vgrid_name))

        if not (cert_id in owners_direct):

            # the owner owns an upper vgrid, ownership is inherited
            # cannot remove, not last (inherited) owner

            logger.warning('Cannot delete: Inherited ownership.' +
                           '\n Owners: %s,\n Direct owners: %s.'
                           % (owners, owners_direct))
            output_objects.append({'object_type': 'error_text', 'text':
                                   '''%s is owner of a parent %s.
Owner removal has to be performed at the topmost vgrid''' %
                                   (cert_id, label)})
            return (output_objects, returnvalues.CLIENT_ERROR)

        else:

            # Remove any tracker admin rights

            if configuration.trac_admin_path:
                public_tracker_dir = \
                    os.path.abspath(os.path.join(
                        configuration.vgrid_public_base, vgrid_name,
                        '.vgridtracker'))
                private_tracker_dir = \
                    os.path.abspath(os.path.join(
                        configuration.vgrid_private_base, vgrid_name,
                        '.vgridtracker'))
                vgrid_tracker_dir = \
                    os.path.abspath(os.path.join(
                        configuration.vgrid_files_home, vgrid_name,
                        '.vgridtracker'))
                for tracker_dir in [public_tracker_dir, private_tracker_dir,
                                    vgrid_tracker_dir]:
                    if not rm_tracker_admin(configuration, cert_id,
                                            vgrid_name, tracker_dir,
                                            output_objects):
                        return (output_objects, returnvalues.SYSTEM_ERROR)

            user_dir = os.path.abspath(os.path.join(configuration.user_home,
                                                    cert_dir)) + os.sep

            # Do not touch vgrid share if still a member of a parent vgrid

            if vgrid_is_member(vgrid_name, cert_id, configuration):
                # list is in top-down order
                parent_vgrids = vgrid_list_parents(vgrid_name, configuration)
                inherit_vgrid_member = vgrid_name
                for parent in parent_vgrids:
                    if vgrid_is_member(parent, cert_id, configuration,
                                       recursive=False):
                        inherit_vgrid_member = parent
                        break
                output_objects.append(
                    {'object_type': 'text', 'text':
                     '''NOTE: %s is still a member of parent %s %s.
Preserving access to corresponding %s.''' % (cert_id, label,
                                             inherit_vgrid_member, label)})
            else:
                (success, msg) = vgrid_rm_share(configuration,
                                                vgrid_name,
                                                user_dir)
                if not success:
                    logger.error('Could not remove share link: %s.' % msg)
                    output_objects.append({'object_type': 'error_text', 'text':
                                           'Could not remove share links: %s.'
                                           % msg})
                    return (output_objects, returnvalues.SYSTEM_ERROR)

            # unlink shared web folders

            (success, msg) = vgrid_rm_web_folders(
                configuration, vgrid_name, user_dir)

            if not success:
                logger.error('Could not remove web links: %s.' % msg)
                output_objects.append({'object_type': 'error_text', 'text':
                                       'Could not remove web links: %s.'
                                       % msg})
                return (output_objects, returnvalues.SYSTEM_ERROR)

            # remove user from saved owners list
            (rm_status, rm_msg) = vgrid_remove_owners(configuration,
                                                      vgrid_name,
                                                      [cert_id])
            if not rm_status:
                output_objects.append({'object_type': 'error_text', 'text':
                                       '%s of owners of %s'
                                       % (rm_msg, vgrid_name)})
                return (output_objects, returnvalues.SYSTEM_ERROR)

            # Any parent vgrid membership is left untouched here as we only
            # force a normal refresh in unmap_inheritance
            unmap_inheritance(configuration, vgrid_name, cert_id)

            output_objects.append({'object_type': 'text', 'text':
                                   '%s successfully removed as owner of %s!'
                                   % (cert_id, vgrid_name)})
            output_objects.append({'object_type': 'link', 'destination':
                                   'adminvgrid.py?vgrid_name=%s'
                                   % vgrid_name,
                                   'text': 'Back to administration for %s'
                                   % vgrid_name})
            return (output_objects, returnvalues.OK)

    else:

        # no more direct owners - we try to remove this VGrid

        logger.debug('Leave %s from %s with no more direct owners: delete' %
                     (vgrid_name, cert_id))

        if not force(flags):
            output_objects.append({'object_type': 'text', 'text': '''
No more direct owners of %s - leaving will result in the %s getting
deleted. Please use either of the links below to confirm or cancel.
''' % (vgrid_name, label)})
            # Reuse csrf token from this request
            target_op = 'rmvgridowner'
            js_name = target_op
            csrf_token = accepted[csrf_field][-1]
            helper = html_post_helper(js_name, '%s.py' % target_op,
                                      {'vgrid_name': vgrid_name,
                                       'cert_id': cert_id, 'flags': 'f',
                                       csrf_field: csrf_token})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            output_objects.append({'object_type': 'link', 'destination':
                                   "javascript: %s();" % js_name, 'class':
                                   'removelink iconspace', 'text':
                                   'Really leave and delete %s' % vgrid_name})
            output_objects.append({'object_type': 'text', 'text': ''})
            output_objects.append({'object_type': 'link', 'destination':
                                   'adminvgrid.py?vgrid_name=%s' % vgrid_name,
                                   'text': 'Back to administration for %s'
                                   % vgrid_name})
            return (output_objects, returnvalues.OK)

        # check if any resources participate or sub-vgrids depend on this one

        (list_status, subs) = vgrid_list_subvgrids(vgrid_name, configuration)

        if not list_status:
            logger.error('Error loading sub-vgrid for %s: %s)' % (vgrid_name,
                                                                  subs))
            output_objects.append({'object_type': 'error_text', 'text': '''
An internal error occurred, error conditions have been logged.'''})
            output_objects.append({'object_type': 'text', 'text': '''
You can help us fix the problem by notifying the administrators
via mail about what you wanted to do when the error happened.'''})
            return (output_objects, returnvalues.CLIENT_ERROR)

        if subs:
            logger.debug('Cannot delete: still has sub-vgrids: %s' % subs)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s has one or more child %ss and cannot be deleted.' %
                 (vgrid_name, label)})
            output_objects.append(
                {'object_type': 'text', 'text': '''To leave (and delete) %s
first remove all its children: %s.''' % (vgrid_name, ', '.join(subs))})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # we consider the local members and resources here, not inherited ones

        (member_status, members_direct) = vgrid_members(vgrid_name,
                                                        configuration,
                                                        False)
        (resource_status, resources_direct) = vgrid_resources(vgrid_name,
                                                              configuration,
                                                              False)
        if not member_status or not resource_status:
            logger.warning('failed to load %s members or resources: %s %s'
                           % (vgrid_name, members_direct, resources_direct))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'could not load %s members or resources for %s.' %
                 (label, vgrid_name)})
            return (output_objects, returnvalues.SYSTEM_ERROR)
        if resources_direct:
            logger.debug('Cannot delete: still has direct resources %s.'
                         % resources_direct)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s still has resources and cannot be deleted.' % vgrid_name})
            output_objects.append({'object_type': 'text', 'text': '''
To leave (and delete) %s, first remove the participating resources.'''
                                   % vgrid_name})

            return (output_objects, returnvalues.CLIENT_ERROR)

        if members_direct:

            logger.debug('Cannot delete: still has direct members %s.'
                         % members_direct)
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 '%s still has members and cannot be deleted.' % vgrid_name})
            output_objects.append({'object_type': 'text', 'text': '''
To leave (and delete) %s, first remove all members.'''
                                   % vgrid_name})

            return (output_objects, returnvalues.CLIENT_ERROR)

        # Deleting write restricted VGrid is not allowed

        (load_status, saved_settings) = vgrid_settings(vgrid_name,
                                                       configuration,
                                                       recursive=True,
                                                       as_dict=True)
        if not load_status:
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'failed to load saved %s settings' % vgrid_name})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # NOTE: legacy vgrids may have setting False to mean full write
        if saved_settings.get('write_shared_files', keyword_members) not in \
                [False, keyword_members]:
            logger.warning("%s can't delete vgrid %s - write limited!"
                           % (client_id, vgrid_name))
            output_objects.append(
                {'object_type': 'error_text', 'text': """You can't delete
write-restricted %ss - first remove any write restrictions for shared files
on the admin page and then try again.""" % label})
            return (output_objects, returnvalues.CLIENT_ERROR)

        # When reaching here, OK to remove the VGrid.
        #   if top-level: unlink, remove all files and directories,
        #   in all cases: remove configuration entry for the VGrid
        #   unlink and move new-style vgrid sub dir to parent

        logger.info('Deleting %s and all related data as requested by %s' %
                    (vgrid_name, cert_id))

        if (cert_id in owners_direct):

            # owner owns this vgrid, direct ownership

            logger.debug('%s looks like a top-level vgrid.' % vgrid_name)
            logger.debug('Deleting all related files.')

            user_dir = os.path.abspath(os.path.join(configuration.user_home,
                                                    cert_dir)) + os.sep
            (share_lnk, share_msg) = vgrid_rm_share(
                configuration, vgrid_name, user_dir)
            (web_lnk, web_msg) = vgrid_rm_web_folders(
                configuration, vgrid_name, user_dir)
            (files_act, files_msg) = vgrid_rm_files(configuration, vgrid_name)
        else:

            # owner owns some parent vgrid - ownership is only inherited

            logger.debug('%s looks like a sub-vgrid, ownership inherited.' %
                         vgrid_name)
            logger.debug('Only removing entry, leaving files in place.')
            share_lnk, share_msg = True, ''
            web_lnk, web_msg = True, ''
            (files_act, files_msg) = vgrid_inherit_files(
                configuration, vgrid_name)
        (removed, entry_msg) = vgrid_rm_entry(configuration, vgrid_name)

        output_objects.append({'object_type': 'text', 'text':
                               '%s has been removed with last owner.'
                               % vgrid_name})

        output_objects.append({'object_type': 'link',
                               'destination': 'vgridman.py',
                               'text': 'Back to the overview.'})

        if not share_lnk or not web_lnk or not files_act or not removed:
            err = '\n'.join([share_msg, web_msg, files_msg, entry_msg])
            logger.error('Errors while removing %s:\n%s.' % (vgrid_name, err))

            output_objects.append({'object_type': 'error_text', 'text': '''
An internal error occurred, error conditions have been logged.'''})
            output_objects.append({'object_type': 'text', 'text': '''
You can help us fix the problem by notifying the administrators
via mail about what you wanted to do when the error happened.'''})
            return (output_objects, returnvalues.CLIENT_ERROR)

        else:

            # Remove vgrid from vgrid cache (after deleting all)
            unmap_vgrid(configuration, vgrid_name)
            return (output_objects, returnvalues.OK)
