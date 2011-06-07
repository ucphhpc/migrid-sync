#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rmvgridowner - remove a vgrid owner
# Copyright (C) 2003-2010  The MiG Project lead by Brian Vinter
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

import os
from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.fileio import remove_rec, unpickle
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.handlers import correct_handler
from shared.html import html_post_helper
from shared.init import initialize_main_variables
from shared.parseflags import force
from shared.vgrid import init_vgrid_script_add_rem, vgrid_is_owner, \
       vgrid_owners, vgrid_list_subvgrids, vgrid_remove_owners
from shared.vgridaccess import unmap_vgrid

def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET, 'cert_id': REJECT_UNSET,
                'flags': []}
    return ['text', defaults]

def unlink_shared_folders(user_dir, vgrid):
    """Utility function to remove links to shared vgrid folders.

    user_dir: the full path to the user home where deletion should happen

    vgrid: the name of the vgrid to delete   

    Returns boolean success indicator and potential messages as a pair.

    Note: Removed links are hard-coded (as in other modules)
        user_dir/vgrid
        user_dir/private_base/vgrid
        user_dir/public_base/vgrid
    In case of a sub-vgrid, enclosing empty directories are removed as well.
    """

    success = True
    msg = ""

    for infix in ["", "private_base", "public_base"]:
        path = os.path.join(user_dir, infix, vgrid)
        try:
            if os.path.exists(path):
                os.remove(path)
                path = os.path.dirname(path)
                if os.path.isdir(path) and os.listdir(path) == []: 
                    os.removedirs(path)
        except Exception, err:
            success = False
            msg += "\nCould not remove link %s: %s" % (path, err)

    return (success, msg[1:])

def abandon_vgrid_files(vgrid, configuration):
    """Remove all files which belong to the given VGrid (parameter).
    This corresponds to the functionality in createvgrid.py, but we 
    can make our life easy by removing recursively, using a function
    in fileio.py for this purpose. The VGrid is assumed to be abandoned entirely.
    The function recursively removes the following directories: 
            configuration.vgrid_public_base/<vgrid>
            configuration.vgrid_private_base/<vgrid>
            configuration.vgrid_files_home/<vgrid>
    and the soft link (if it is a link, not a directory)
            configuration.wwwpublic/vgrid/<vgrid>

    vgrid: The name of the Vgrid to delete
    configuration: to determine the location of the directories 


    Note: the entry for the VGrid itself, configuration.vgrid_home/<vgrid>
            is removed separately, see remove_vgrid_entry
    Returns: Success indicator and potential messages.
    """

    configuration.logger.debug('Deleting all files for VGrid %s' % vgrid)
    success = True
    msg = ""

    # removing this soft link may fail, since it is a directory for sub-VGrids
    
    try:
        os.remove(os.path.join(configuration.wwwpublic, 'vgrid', vgrid))
    except Exception, err:
        configuration.logger.debug(
            'not removing soft link to public VGrid pages for %s: %s' % \
            (vgrid, err))
        pass

    for prefix in [configuration.vgrid_public_base, 
                   configuration.vgrid_private_base, 
                   configuration.vgrid_files_home]:
        success_here = remove_rec(os.path.join(prefix, vgrid), configuration)
        if not success_here:
            msg += "Error while removing %s." % os.path.join(prefix, vgrid)
            success = False

    configuration.logger.debug('Messages: %s.' % msg)

    return (success, msg)

def remove_vgrid_entry(vgrid, configuration):
    """Remove an entry for a VGrid in the vgrid configuration directory.
            configuration.vgrid_home/<vgrid>

    The VGrid contents (shared files and web pages) are assumed to either 
    be abandoned entirely, or become subdirectory of another vgrid (for 
    sub-vgrids). Wiki and SCM are deleted as well, as they would  be unusable
    and undeletable.

    vgrid: the name of the VGrid to delete
    configuration: to determine configuration.vgrid_home

    Returns: Success indicator and potential messages.
    """

    configuration.logger.debug('Removing entry for VGrid %s' % vgrid)

    msg = ''
    success = remove_rec(os.path.join(configuration.vgrid_home, vgrid),
                         configuration)
    if not success:

        configuration.logger.debug('Error while removing %s.' % vgrid)
        msg += "Error while removing entry for %s." % vgrid

    else:

        for prefix in [ configuration.vgrid_public_base, 
                        configuration.vgrid_private_base, 
                        configuration.vgrid_files_home]:

            # delete public, member, and owner wikis and scms
            # we just remove and do not check success for these

            if configuration.moin_share and configuration.moin_etc:
                remove_rec(os.path.join(prefix, vgrid, '.vgridwiki'),
                           configuration)

            if configuration.hg_path and configuration.hgweb_path:
                remove_rec(os.path.join(prefix, vgrid, '.vgridscm'), 
                           configuration)

    return (success, msg)


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
    defaults = signature()[1]
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

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    vgrid_name = accepted['vgrid_name'][-1]
    flags = ''.join(accepted['flags'])
    cert_id = accepted['cert_id'][-1]
    cert_dir = client_id_dir(cert_id)

    # Validity of user and vgrid names is checked in this init function so
    # no need to worry about illegal directory traversal through variables

    (ret_val, msg, ret_variables) = \
        init_vgrid_script_add_rem(vgrid_name, client_id, cert_id,
                                  'owner', configuration)
    if not ret_val:
        output_objects.append({'object_type': 'error_text', 'text'
                              : msg})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # don't remove if not already an owner

    if not vgrid_is_owner(vgrid_name, cert_id, configuration):
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s is not an owner of %s or a parent vgrid.'
                               % (cert_id, vgrid_name)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # vgrid dirs when own name is a prefix of another name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                               vgrid_name)) + os.sep

    # we need the local owners file to detect inherited ownerships

    owners_file = os.path.join(base_dir, 'owners')
    owners_direct = unpickle(owners_file, configuration.logger)

    (status, owners) = vgrid_owners(vgrid_name, configuration)

    if not status:
        logger.error('Error loading owners for %s: %s'
                     % (vgrid_name, owners))
        output_objects.append({'object_type': 'error_text', 'text'
         : 'An internal error occurred, error conditions have been logged.'})
        output_objects.append({'object_type': 'text', 'text'
         : '''
         You can help us fix the problem by notifying the administrators
         via mail about what you wanted to do when the error happened.'''})
        return (output_objects, returnvalues.CLIENT_ERROR)
    
    # find out whether to just remove an owner or delete the whole thing

    if len(owners) > 1:
        
        logger.debug('Removing %s, one of several owners, from %s.' % 
                     (cert_id, vgrid_name))

        if not (cert_id in owners_direct):

            # the owner owns an upper vgrid, ownership is inherited
            # cannot remove, not last (inherited) owner

            logger.debug('Cannot delete: Inherited ownership.' + 
                         '\n Owners: %s,\n Direct owners: %s.' 
                         % (owners, owners_direct))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : '''%s is owner of a parent vgrid. 
Owner removal has to be performed at the topmost vgrid''' % cert_id})
            return (output_objects, returnvalues.CLIENT_ERROR)

        else:
            
            # unlink shared folders (web pages and files)

            user_dir = os.path.abspath(os.path.join(configuration.user_home,
                                                    cert_dir)) + os.sep
            (success, msg) = unlink_shared_folders(user_dir, vgrid_name)
            if not success: 
                logger.error('Could not remove links: %s.' % msg)
                output_objects.append({'object_type': 'error_text', 'text'
                                       : 'Could not remove links: %s.' 
                                         % msg})
                return (output_objects, returnvalues.SYSTEM_ERROR)

            # remove user from pickled list
            # remove this owner, also from the owners file
            (rm_status, rm_msg) = vgrid_remove_owners(configuration, vgrid_name,
                                                     [cert_id])
            if not rm_status:
                output_objects.append({'object_type': 'error_text', 'text'
                                       : '%s of owners of %s' 
                                       % (rm_msg, vgrid_name)})
                return (output_objects, returnvalues.SYSTEM_ERROR)

            output_objects.append({'object_type': 'text', 'text'
                          : '%s successfully removed as owner of %s!'
                           % (cert_id, vgrid_name)})
            output_objects.append({'object_type': 'link', 'destination':
                           'adminvgrid.py?vgrid_name=%s' % vgrid_name, 'text':
                           'Back to administration for %s' % vgrid_name})
            return (output_objects, returnvalues.OK)

    else:
        
        # the last owner wants to leave, we try to remove this VGrid
        # implies cert_id == client_id. 

        logger.debug('Last owner %s wants to leave %s. Attempting deletion' %
                     (cert_id, vgrid_name))

        if not force(flags):
            output_objects.append({'object_type': 'text', 'text' : '''
You are the last owner of %s - leaving will result in the vgrid getting
deleted. Please use either of the links below to confirm or cancel.
''' % vgrid_name})
            js_name = 'rmvgridowner%s' % hexlify(vgrid_name)
            helper = html_post_helper(js_name, 'rmvgridowner.py',
                                      {'vgrid_name': vgrid_name,
                                       'cert_id': client_id, 'flags': 'f'})
            output_objects.append({'object_type': 'html_form', 'text': helper})
            output_objects.append({'object_type': 'link', 'destination':
                                   "javascript: %s();" % js_name, 'class':
                                   'removelink', 'text':
                                   'Really leave and delete %s' % vgrid_name})
            output_objects.append({'object_type': 'text', 'text' : ''})
            output_objects.append({'object_type': 'link', 'destination':
                                   'adminvgrid.py?vgrid_name=%s' % vgrid_name,
                                   'text': 'Back to administration for %s'
                                   % vgrid_name})
            return (output_objects, returnvalues.OK)

        # check if any resources participate or sub-vgrids depend on this one

        (status, subs) = vgrid_list_subvgrids(vgrid_name, configuration)

        if not status:
            logger.error('Error loading sub-vgrids for %s: %s)'
                         % (vgrid_name, subs))
            output_objects.append({'object_type': 'error_text', 'text' : '''
An internal error occurred, error conditions have been logged.'''})
            output_objects.append({'object_type': 'text', 'text' : '''
You can help us fix the problem by notifying the administrators
via mail about what you wanted to do when the error happened.'''})
            return (output_objects, returnvalues.CLIENT_ERROR)

        if len(subs) > 0:

            logger.debug('Cannot delete: still has sub-vgrids %s.'
                         % subs)
            output_objects.append({'object_type': 'error_text', 'text' : \
    '%s has sub-structures and cannot be deleted.' % vgrid_name})
            output_objects.append({'object_type': 'text', 'text' : '''
To leave (and delete) %s, first remove its sub-structures: %s.'''
                                      % (vgrid_name, ', '.join(subs))})

            return (output_objects, returnvalues.CLIENT_ERROR)

        # we consider the local members and resources here, not inherited ones
        
        members_direct   = unpickle(os.path.join(base_dir, 'members'), 
                                    configuration.logger)
        resources_direct = unpickle(os.path.join(base_dir, 'resources'), 
                                    configuration.logger)

        if len(resources_direct) > 0:

            logger.debug('Cannot delete: still has direct resources %s.'
                         % resources_direct)
            output_objects.append({'object_type': 'error_text', 'text' : \
    '%s still has resources and cannot be deleted.' % vgrid_name})
            output_objects.append({'object_type': 'text', 'text' : '''
To leave (and delete) %s, first remove the participating resources.'''
                                      % vgrid_name})

            return (output_objects, returnvalues.CLIENT_ERROR)

        if len(members_direct) > 0:

            logger.debug('Cannot delete: still has direct members %s.'
                         % members_direct)
            output_objects.append({'object_type': 'error_text', 'text' : \
    '%s still has members and cannot be deleted.' % vgrid_name})
            output_objects.append({'object_type': 'text', 'text' : '''
To leave (and delete) %s, first remove all members.'''
                                      % vgrid_name})

            return (output_objects, returnvalues.CLIENT_ERROR)

        # When reaching here, OK to remove the VGrid.
        #   if top-level: unlink, remove all files and directories, 
        #   in all cases: remove configuration entry for the VGrid

        if (cert_id in owners_direct):

            # owner owns an upper vgrid, ownership is inherited

            logger.debug('%s looks like a top-level vgrid.'
                         % vgrid_name)
            logger.debug('Deleting all related files.')

            user_dir = os.path.abspath(os.path.join(configuration.user_home,
                                                    cert_dir)) + os.sep
            (unlinked, msg1)  = unlink_shared_folders(user_dir, vgrid_name)

            (abandoned, msg2) = abandon_vgrid_files(vgrid_name, configuration)

        else:

            # owner owns an upper vgrid, ownership is inherited

            logger.debug('%s looks like a sub-vgrid, ownership inherited.'
                         % vgrid_name)
            logger.debug('Only removing entry, leaving files in place.')
            unlinked = True
            abandoned = True
            msg1 = ''
            msg2 = ''

        (removed, msg3) = remove_vgrid_entry(vgrid_name, configuration)

        output_objects.append({'object_type': 'text', 'text'
                                   : '%s has been removed with last owner.'
                                      % vgrid_name})

        output_objects.append({'object_type': 'link', 
                               'destination': 'vgridadmin.py', 
                               'text': 'Back to the overview.'})

        if not unlinked or not abandoned or not removed:

            logger.error('Errors while removing %s:\n%s.'
                         % (vgrid_name, '\n'.join([msg1,msg2,msg3])))

            output_objects.append({'object_type': 'error_text', 'text' : '''
An internal error occurred, error conditions have been logged.'''})
            output_objects.append({'object_type': 'text', 'text' : '''
You can help us fix the problem by notifying the administrators
via mail about what you wanted to do when the error happened.'''})
            return (output_objects, returnvalues.CLIENT_ERROR)

        else:

            # Remove vgrid from vgrid cache (after deleting all)
            unmap_vgrid(configuration, vgrid_name)
            return (output_objects, returnvalues.OK)
