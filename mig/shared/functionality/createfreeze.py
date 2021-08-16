#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createfreeze - back end for freezing archives
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Creation of frozen archives for write-once files"""

from __future__ import absolute_import

import datetime
import os

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import max_freeze_files, csrf_field, freeze_flavors, \
    keyword_auto, keyword_pending, keyword_final
from mig.shared.fileio import strip_dir, walk
from mig.shared.freezefunctions import create_frozen_archive, published_url, \
    is_frozen_archive
from mig.shared.functional import validate_input_and_cert, REJECT_UNSET
from mig.shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from mig.shared.html import man_base_js, man_base_html, html_post_helper
from mig.shared.init import initialize_main_variables, find_entry
from mig.shared.safeinput import valid_path
from mig.shared.validstring import valid_user_path
from mig.shared.vgrid import in_vgrid_share


def signature():
    """Signature of the main function"""

    defaults = {
        'flavor': ['freeze'],
        'freeze_id': [keyword_auto],
        'freeze_name': [keyword_auto],
        'freeze_description': [''],
        'freeze_publish': [''],
        'freeze_author': [''],
        'freeze_department': [''],
        'freeze_organization': [''],
        'freeze_state': [keyword_auto],
    }
    return ['text', defaults]


def _parse_form_xfer(xfer, user_args, client_id, configuration):
    """Parse xfer request (i.e. copy, move or upload) file/dir entries from
    user_args.
    """
    _logger = configuration.logger
    files, rejected = [], []
    i = 0
    client_dir = client_id_dir(client_id)
    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                                            client_dir)) + os.sep
    xfer_pattern = 'freeze_%s_%%d' % xfer
    for i in xrange(max_freeze_files):
        if xfer_pattern % i in user_args:
            source_path = user_args[xfer_pattern % i][-1].strip()
            source_path = os.path.normpath(source_path).lstrip(os.sep)
            _logger.debug('found %s entry: %s' % (xfer, source_path))
            if not source_path:
                continue
            try:
                valid_path(source_path)
            except Exception as exc:
                rejected.append('invalid path: %s (%s)' % (source_path,
                                                           exc))
                continue
            # IMPORTANT: path must be expanded to abs for proper chrooting
            abs_path = os.path.abspath(
                os.path.join(base_dir, source_path))
            # Prevent out-of-bounds, and restrict some greedy targets
            if not valid_user_path(configuration, abs_path, base_dir, True):
                _logger.error('found illegal directory traversal %s entry: %s'
                              % (xfer, source_path))
                rejected.append('invalid path: %s (%s)' %
                                (source_path, 'illegal path!'))
                continue
            elif os.path.exists(abs_path) and os.path.samefile(abs_path,
                                                               base_dir):
                _logger.warning('refusing archival of entire user home %s: %s'
                                % (xfer, source_path))
                rejected.append('invalid path: %s (%s)' %
                                (source_path, 'entire home not allowed!'))
                continue
            elif in_vgrid_share(configuration, abs_path) == source_path:
                _logger.warning(
                    'refusing archival of entire vgrid shared folder %s: %s' %
                    (xfer, source_path))
                rejected.append('invalid path: %s (%s)' %
                                (source_path, 'entire %s share not allowed!'
                                 % configuration.site_vgrid_label))
                continue

            # expand any dirs recursively
            if os.path.isdir(abs_path):
                for (root, dirnames, filenames) in walk(abs_path):
                    for subname in filenames:
                        abs_sub = os.path.join(root, subname)
                        sub_base = root.replace(abs_path, source_path)
                        sub_path = os.path.join(sub_base, subname)
                        files.append((abs_sub, sub_path.lstrip(os.sep)))
            else:
                files.append((abs_path, source_path.lstrip(os.sep)))
    return (files, rejected)


def parse_form_copy(user_args, client_id, configuration):
    """Parse copy file/dir entries from user_args"""
    return _parse_form_xfer("copy", user_args, client_id, configuration)


def parse_form_move(user_args, client_id, configuration):
    """Parse move file/dir entries from user_args"""
    return _parse_form_xfer("move", user_args, client_id, configuration)


def parse_form_upload(user_args, client_id, configuration):
    """Parse upload file entries from user_args"""
    files, rejected = [], []
    i = 0
    client_dir = client_id_dir(client_id)
    for i in xrange(max_freeze_files):
        if 'freeze_upload_%d' % i in user_args:
            file_item = user_args['freeze_upload_%d' % i]
            filename = user_args.get('freeze_upload_%dfilename' % i,
                                     '')
            if not filename.strip():
                continue
            filename = strip_dir(filename)
            try:
                valid_path(filename)
            except Exception as exc:
                rejected.append('invalid filename: %s (%s)' % (filename, exc))
                continue
            files.append((filename, file_item[0]))
    return (files, rejected)


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    defaults = signature()[1]
    title_entry = find_entry(output_objects, 'title')
    label = "%s" % configuration.site_vgrid_label
    title_entry['text'] = "Create Archive"
    # NOTE: Delay header entry here to include freeze flavor
    # All non-file fields must be validated
    validate_args = dict([(key, user_arguments_dict.get(key, val)) for
                          (key, val) in defaults.items()])
    # IMPORTANT: we must explicitly inlude CSRF token
    validate_args[csrf_field] = user_arguments_dict.get(csrf_field, [
                                                        'AllowMe'])
    (validate_status, accepted) = validate_input_and_cert(
        validate_args,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
    )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    flavor = accepted['flavor'][-1].strip()
    freeze_state = accepted['freeze_state'][-1].strip()

    if not safe_handler(configuration, 'post', op_name, client_id,
                        get_csrf_limit(configuration), accepted):
        output_objects.append(
            {'object_type': 'error_text', 'text': '''Only accepting
CSRF-filtered POST requests to prevent unintended updates'''
             })
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not flavor in freeze_flavors:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid freeze flavor: %s' % flavor})
        return (output_objects, returnvalues.CLIENT_ERROR)
    if not freeze_state in freeze_flavors[flavor]['states'] + [keyword_auto]:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Invalid freeze state: %s' % freeze_state})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title = freeze_flavors[flavor]['createfreeze_title']
    output_objects.append({'object_type': 'header', 'text': title})

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                               '''Freezing archives is disabled on this site.
Please contact the site admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    # jquery support for confirmation on freeze
    (add_import, add_init, add_ready) = man_base_js(configuration, [])
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'html_form',
                           'text': man_base_html(configuration)})

    freeze_id = accepted['freeze_id'][-1].strip()
    freeze_name = accepted['freeze_name'][-1].strip()
    freeze_description = accepted['freeze_description'][-1]
    freeze_author = accepted['freeze_author'][-1].strip()
    freeze_department = accepted['freeze_department'][-1].strip()
    freeze_organization = accepted['freeze_organization'][-1].strip()
    freeze_publish = accepted['freeze_publish'][-1].strip()
    do_publish = (freeze_publish.lower() in ('on', 'true', 'yes', '1'))

    # Share init of base meta with lookup of default state in freeze_flavors
    if not freeze_state or freeze_state == keyword_auto:
        freeze_state = freeze_flavors[flavor]['states'][0]
    freeze_meta = {'ID': freeze_id, 'STATE': freeze_state}

    # New archives must have name and description set
    if freeze_id == keyword_auto:
        logger.debug("creating a new %s archive for %s" % (flavor, client_id))
        if not freeze_name or freeze_name == keyword_auto:
            freeze_name = '%s-%s' % (flavor, datetime.datetime.now())
        if not freeze_description:
            if flavor == 'backup':
                freeze_description = 'manual backup archive created on %s' % \
                                     datetime.datetime.now()
            else:
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'You must provide a description for the archive!'})
                return (output_objects, returnvalues.CLIENT_ERROR)
        if flavor == 'phd' and (not freeze_author or not freeze_department):
            output_objects.append({'object_type': 'error_text', 'text': """
You must provide author and department for the thesis!"""})
            return (output_objects, returnvalues.CLIENT_ERROR)
        freeze_meta.update(
            {'FLAVOR': flavor, 'NAME': freeze_name,
             'DESCRIPTION': freeze_description,
             'AUTHOR': freeze_author, 'DEPARTMENT': freeze_department,
             'ORGANIZATION': freeze_organization, 'PUBLISH': do_publish})
    elif is_frozen_archive(client_id, freeze_id, configuration):
        logger.debug("updating existing %s archive for %s" % (flavor,
                                                              client_id))
        # Update any explicitly provided fields (may be left empty on finalize)
        changes = {}
        if freeze_name and freeze_name != keyword_auto:
            changes['NAME'] = freeze_name
        if freeze_author:
            changes['AUTHOR'] = freeze_author
        if freeze_description:
            changes['DESCRIPTION'] = freeze_description
        if freeze_publish:
            changes['PUBLISH'] = do_publish
        logger.debug("updating existing %s archive for %s with: %s" %
                     (flavor, client_id, changes))
        logger.debug("publish is %s based on %s" %
                     (do_publish, freeze_publish))
        freeze_meta.update(changes)
    else:
        logger.error("no such %s archive for %s: %s" % (flavor, client_id,
                                                        freeze_id))
        output_objects.append({'object_type': 'error_text', 'text': """
Invalid archive ID %s - you must either create a new archive or edit an
existing archive of yours!""" % freeze_id})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Now parse and validate files to archive

    for name in defaults:
        if name in user_arguments_dict:
            del user_arguments_dict[name]

    (copy_files, copy_rejected) = parse_form_copy(user_arguments_dict,
                                                  client_id, configuration)
    (move_files, move_rejected) = parse_form_move(user_arguments_dict,
                                                  client_id, configuration)
    (upload_files, upload_rejected) = parse_form_upload(user_arguments_dict,
                                                        client_id,
                                                        configuration)
    if copy_rejected + move_rejected + upload_rejected:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Errors parsing freeze files: %s' %
                               '\n '.join(copy_rejected + move_rejected +
                                          upload_rejected)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # NOTE: this may be a new or an existing pending archive, and it will fail
    #       if archive is already under update
    (retval, retmsg) = create_frozen_archive(freeze_meta, copy_files,
                                             move_files, upload_files,
                                             client_id, configuration)
    if not retval:
        output_objects.append({'object_type': 'error_text', 'text':
                               'Error creating/updating archive: %s'
                               % retmsg})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Make sure we have freeze_id and other updated fields
    freeze_meta.update(retmsg)
    freeze_id = freeze_meta['ID']
    logger.info("%s: successful for '%s': %s" % (op_name,
                                                 freeze_id, client_id))
    # Return simple status mainly for use in scripting
    output_objects.append({'object_type': 'freezestatus', 'freeze_id': freeze_id,
                           'flavor': flavor, 'freeze_state': freeze_state})
    publish_note = ''
    if freeze_state == keyword_pending:
        publish_hint = 'Preview published archive page in a new window/tab'
        publish_text = 'Preview publishing'
        output_objects.append({'object_type': 'text', 'text': """
Saved *preliminary* %s archive with ID %s . You can continue inspecting and
changing it until you're satisfied, then finalize it for actual persistent
freezing.""" % (flavor, freeze_id)})
    else:
        publish_hint = 'View published archive page in a new window/tab'
        publish_text = 'Open published archive'
        output_objects.append({'object_type': 'text', 'text':
                               'Successfully froze %s archive with ID %s .'
                               % (flavor, freeze_id)})

    if do_publish:
        public_url = published_url(freeze_meta, configuration)
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({
            'object_type': 'link',
            'destination': public_url,
            'class': 'previewarchivelink iconspace genericbutton',
            'title': publish_hint,
            'text': publish_text,
            'target': '_blank',
        })
        output_objects.append({'object_type': 'text', 'text': ''})

    # Always allow show archive
    output_objects.append({
        'object_type': 'link',
        'destination': 'showfreeze.py?freeze_id=%s;flavor=%s' % (freeze_id,
                                                                 flavor),
        'class': 'viewarchivelink iconspace genericbutton',
        'title': 'View details about your %s archive' % flavor,
        'text': 'View details',
    })

    if freeze_state == keyword_pending:
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({
            'object_type': 'link',
            'destination': 'adminfreeze.py?freeze_id=%s' % freeze_id,
            'class': 'editarchivelink iconspace genericbutton',
            'title': 'Further modify your pending %s archive' % flavor,
            'text': 'Edit archive',
        })
        output_objects.append({'object_type': 'text', 'text': ''})
        output_objects.append({'object_type': 'html_form', 'text': """
<br/><hr/><br/>
<p class='warn_message'>IMPORTANT: you still have to explicitly finalize your
archive before you get the additional data integrity/persistance guarantees
like tape archiving.
</p>"""})

        form_method = 'post'
        target_op = 'createfreeze'
        csrf_limit = get_csrf_limit(configuration)
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        helper = html_post_helper('createfreeze', '%s.py' % target_op,
                                  {'freeze_id': freeze_id,
                                   'freeze_state': keyword_final,
                                   'flavor': flavor,
                                   csrf_field: csrf_token})
        output_objects.append({'object_type': 'html_form', 'text': helper})

        output_objects.append({
            'object_type': 'link',
            'destination':
            "javascript: confirmDialog(%s, '%s');" %
            ('createfreeze', 'Really finalize %s?' % freeze_id),
            'class': 'finalizearchivelink iconspace genericbutton',
            'title': 'Finalize %s archive to prevent further changes' % flavor,
            'text': 'Finalize archive',
        })

    return (output_objects, returnvalues.OK)
