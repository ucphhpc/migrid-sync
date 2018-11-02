#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# uploadchunked - Chunked and efficient file upload back end
# Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter
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

"""Chunked file upload back end:
Implicitly operates on upload tmp dir for all operations to keep partial
uploads separated from other user files. It is left to the client to send
chunks in any order and then call move explicitly after the upload has
finished.
Multiple files can upload chunks in parallel but the chunks of individual
files must be non-overlapping to guarantee race-free writing.
"""

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import upload_block_size, upload_tmp_dir, csrf_field
from shared.fileio import strip_dir, write_chunk, delete_file, move, \
    get_file_size, makedirs_rec, check_write_access
from shared.functional import validate_input
from shared.handlers import safe_handler, get_csrf_limit, make_csrf_token
from shared.gdp import get_project_from_client_id, project_log
from shared.init import initialize_main_variables, find_entry
from shared.parseflags import in_place, verbose
from shared.safeinput import valid_path
from shared.sharelinks import extract_mode_id
from shared.validstring import valid_user_path

# The input argument for fileupload files

files_field = 'files[]'
filename_field = '%sfilename' % files_field
dest_field = 'current_dir'
manual_validation = [files_field, filename_field]


def signature():
    """Signature of the main function"""

    defaults = {'action': ['status'], 'current_dir': [upload_tmp_dir],
                'flags': [''], 'share_id': ['']}
    return ['html_form', defaults]


def extract_chunk_region(configuration):
    """Read chunk range from HTTP headers in os.environ.

    Example range declaration from os.environ:
    'HTTP_CONTENT_RANGE': 'bytes 8000000-14145972/14145973'
    """
    content_length = int(os.environ.get("CONTENT_LENGTH", -1))
    content_range = os.environ.get("HTTP_CONTENT_RANGE", '').strip()
    configuration.logger.info("found content_range: '%s'" % content_range)
    if content_range.startswith("bytes "):
        raw_range = content_range.replace("bytes ", "").split('/')[0]
        range_parts = raw_range.split('-')
        chunk_first, chunk_last = int(range_parts[0]), int(range_parts[1])
    else:
        configuration.logger.info("No valid content range found - using 0")
        if content_length > upload_block_size:
            configuration.logger.error("Should have range!\n%s" % os.environ)
        chunk_first, chunk_last = 0, -1
    return (chunk_first, chunk_last)


def parse_form_upload(user_args, user_id, configuration, base_dir, dst_dir,
                      reject_write=False):
    """Parse upload file and chunk entries from user_args. Chunk limits are
    extracted from content-range http header in environment.
    Existing files are automatically taken from upload_tmp_dir and uploads go
    into dst_dir inside base_dir.
    The optional reject_write argument is used for delayed refusal if someone
    tries to upload to a read-only sharelink.
    """
    files, rejected = [], []
    logger = configuration.logger
    rel_dst_dir = dst_dir.replace(base_dir, '')

    # TODO: we only support single filename and chunk for now; extend?
    # for name_index in xrange(max_upload_files):
    #    if user_args.has_key(filename_field) and \
    #           len(user_args[filename_field]) > name_index:
    for name_index in [0]:
        if user_args.has_key(filename_field):
            if isinstance(user_args[filename_field], basestring):
                filename = user_args[filename_field]
            else:
                filename = user_args[filename_field][name_index]
            logger.info('found name: %s' % filename)
        else:
            # No more files
            break
        if not filename.strip():
            continue
        if reject_write:
            rejected.append((filename, 'read-only share: upload refused!'))
            continue
        try:
            filename = strip_dir(filename)
            valid_path(filename)
        except Exception, exc:
            logger.error('invalid filename: %s' % filename)
            rejected.append((filename, 'invalid filename: %s (%s)'
                             % (filename, exc)))
            continue
        rel_path = os.path.join(rel_dst_dir, filename)
        # IMPORTANT: path must be expanded to abs for proper chrooting
        abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
        if not valid_user_path(configuration, abs_path, dst_dir, True):
            logger.error('%s tried to access restricted path %s ! (%s)'
                         % (user_id, abs_path, dst_dir))
            rejected.append("Invalid path (%s expands to an illegal path)"
                            % filename)
            continue

        # for chunk_index in xrange(max_upload_chunks):
        #    if user_args.has_key(files_field) and \
        #           len(user_args[files_field]) > chunk_index:
        for chunk_index in [0]:
            if user_args.has_key(files_field):
                chunk = user_args[files_field][chunk_index]
            else:
                break
            configuration.logger.debug('find chunk range: %s' % filename)
            (chunk_first, chunk_last) = extract_chunk_region(configuration)
            if len(chunk) > upload_block_size:
                configuration.logger.error('skip bigger than allowed chunk')
                continue
            elif chunk_last < 0:
                chunk_last = len(chunk) - 1
            files.append((rel_path, (chunk, chunk_first, chunk_last)))
    return (files, rejected)


def main(client_id, user_arguments_dict, environ=None):
    """Main function used by front end"""

    if environ is None:
        environ = os.environ

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    logger.info('Extracting input in %s' % op_name)
    status = returnvalues.OK
    defaults = signature()[1]

    logger.info('Extracted input in %s: %s' % (op_name,
                                               user_arguments_dict.keys()))

    # All non-file fields must be validated
    validate_args = dict([(key, user_arguments_dict.get(key, val)) for
                          (key, val) in user_arguments_dict.items() if not key
                          in manual_validation])
    # IMPORTANT: we must explicitly inlude CSRF token
    validate_args[csrf_field] = user_arguments_dict.get(csrf_field, [''])
    (validate_status, accepted) = validate_input(
        validate_args,
        defaults,
        output_objects,
        allow_rejects=False,
    )
    if not validate_status:
        logger.error('%s validation failed: %s (%s)'
                     % (op_name, validate_status, accepted))
        return (accepted, returnvalues.CLIENT_ERROR)

    logger.info('validated input in %s: %s' % (op_name, validate_args.keys()))

    action = accepted['action'][-1]
    current_dir = os.path.normpath(accepted['current_dir'][-1].lstrip(os.sep))
    flags = ''.join(accepted['flags'])
    share_id = accepted['share_id'][-1]
    output_format = accepted['output_format'][-1]

    if action != "status":
        if not safe_handler(configuration, 'post', op_name, client_id,
                            get_csrf_limit(configuration), accepted):
            output_objects.append(
                {'object_type': 'error_text', 'text': '''Only accepting
                CSRF-filtered POST requests to prevent unintended updates'''
                 })
            return (output_objects, returnvalues.CLIENT_ERROR)

    reject_write = False
    uploaded = []
    header_item = {'object_type': 'header', 'text': ''}
    # Always include a files reply even if empty
    output_objects.append(header_item)
    output_objects.append({'object_type': 'uploadfiles', 'files': uploaded})

    # Either authenticated user client_id set or sharelink ID
    if client_id:
        user_id = client_id
        target_dir = client_id_dir(client_id)
        base_dir = configuration.user_home
        redirect_name = configuration.site_user_redirect
        redirect_path = redirect_name
        id_args = ''
        page_title = 'Upload to User Directory: %s' % action
        userstyle = True
        widgets = True
    elif share_id:
        try:
            (share_mode, _) = extract_mode_id(configuration, share_id)
        except ValueError, err:
            logger.error('%s called with invalid share_id %s: %s' %
                         (op_name, share_id, err))
            output_objects.append(
                {'object_type': 'error_text',
                 'text': 'Invalid sharelink ID: %s' % share_id})
            return (output_objects, returnvalues.CLIENT_ERROR)
        # TODO: load and check sharelink pickle (currently requires client_id)
        user_id = 'anonymous user through share ID %s' % share_id
        # NOTE: we must return uploaded reply so we delay read-only failure
        if share_mode == 'read-only':
            logger.error('%s called without write access: %s'
                         % (op_name, accepted))
            reject_write = True
        target_dir = os.path.join(share_mode, share_id)
        base_dir = configuration.sharelink_home
        redirect_name = 'share_redirect'
        redirect_path = os.path.join(redirect_name, share_id)
        id_args = 'share_id=%s;' % share_id
        page_title = 'Upload to Shared Directory: %s' % action
        userstyle = False
        widgets = False
    else:
        logger.error('%s called without proper auth: %s' % (op_name, accepted))
        output_objects.append({'object_type': 'error_text',
                               'text': 'Authentication is missing!'
                               })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(base_dir, target_dir)) + os.sep
    # Cache and destination dir with trailing slash
    cache_dir = os.path.join(base_dir, upload_tmp_dir, '')

    if in_place(flags):
        dst_dir = base_dir
    else:
        dst_dir = cache_dir

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = header_item['text'] = page_title
    title_entry['skipwidgets'] = not widgets
    title_entry['skipuserstyle'] = not userstyle

    # Input validation assures target_dir can't escape base_dir
    if not os.path.isdir(base_dir):
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'Invalid client/sharelink id!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if verbose(flags):
        for flag in flags:
            output_objects.append({'object_type': 'text',
                                   'text': '%s using flag: %s'
                                   % (op_name, flag)})

    logger.info('parsing upload form in %s' % op_name)

    # Now parse and validate files to archive
    # ... this includes checking for illegal directory traversal attempts

    for name in defaults.keys():
        if user_arguments_dict.has_key(name):
            del user_arguments_dict[name]

    try:
        (upload_files, upload_rejected) = parse_form_upload(
            user_arguments_dict, user_id, configuration, base_dir, dst_dir,
            reject_write)
    except Exception, exc:
        logger.error('error extracting required fields: %s' % exc)
        return (output_objects, returnvalues.CLIENT_ERROR)

    if upload_rejected:
        logger.error('Rejecting upload with: %s' % upload_rejected)
        output_objects.append({'object_type': 'error_text',
                               'text': 'Errors parsing upload files: %s'
                               % '\n '.join(["%s %s" % pair for pair in
                                             upload_rejected])})
        for (rel_path, err) in upload_rejected:
            uploaded.append(
                {'object_type': 'uploadfile', 'name': rel_path, 'size': -1,
                 "error": "upload rejected: %s" % err})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if not makedirs_rec(cache_dir, configuration):
        output_objects.append(
            {'object_type': 'error_text',
             'text': "Problem creating temporary upload dir"})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if action == "status" and not upload_files:
        # Default to entire cache dir
        upload_files = [(os.path.join(upload_tmp_dir, i), '') for i in
                        os.listdir(cache_dir)]
    elif not upload_files:
        logger.error('Rejecting upload with: %s' % upload_files)
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'No files included to upload!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    logger.info('Filtered input validated with result: %s' % accepted)

    if verbose(flags):
        output_objects.append(
            {'object_type': 'text', 'text': 'Uploading file chunk(s)'})

    logger.info('Looping through files: %s'
                % ' '.join([i[0] for i in upload_files]))

    del_url = "uploadchunked.py?%soutput_format=%s;action=delete;" \
        + "%s=%s;%s=%s;%s=%s"
    move_url = "uploadchunked.py?%soutput_format=%s;action=move;" \
        + "%s=%s;%s=%s;%s=%s;%s=%s"

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    target_op = op_name
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)

    # Please refer to https://github.com/blueimp/jQuery-File-Upload/wiki/Setup
    # for details about the status reply format in the uploadfile output object

    # All actions automatically take place relative to dst_dir. We only use
    # current_dir in move operation where it is the destination.
    if action == 'delete':
        for (rel_path, chunk_tuple) in upload_files:
            abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
            deleted = delete_file(abs_path, logger)
            # Caller looks just for filename here since it is always relative
            uploaded.append({'object_type': 'uploadfile',
                             os.path.basename(rel_path): deleted})
        logger.info('delete done: %s' % ' '.join([i[0] for i in upload_files]))
        return (output_objects, status)
    elif action == 'status':
        # Status automatically takes place relative to dst_dir
        for (rel_path, chunk_tuple) in upload_files:
            abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
            file_entry = {'object_type': 'uploadfile', 'name': rel_path}
            file_entry['size'] = get_file_size(abs_path, logger)
            # NOTE: normpath+lstrip to avoid leading // and thus no base URL
            # NOTE: normpath to fix e.g. leading // which prevents base URL
            file_entry['url'] = os.path.normpath("/%s/%s"
                                                 % (redirect_path.lstrip('/'),
                                                    rel_path))
            if current_dir == upload_tmp_dir:
                file_entry["deleteType"] = "POST"
                file_entry["deleteUrl"] = del_url % \
                    (id_args, output_format,
                     filename_field,
                     os.path.basename(rel_path),
                     files_field, "dummy", csrf_field,
                     csrf_token)
            uploaded.append(file_entry)
        logger.info('status done: %s' % ' '.join([i[0] for i in upload_files]))
        return (output_objects, status)
    elif action == 'move':
        # Move automatically takes place relative to dst_dir and current_dir
        for (rel_path, chunk_tuple) in upload_files:
            abs_src_path = os.path.abspath(os.path.join(base_dir, rel_path))
            # IMPORTANT: path must be expanded to abs for proper chrooting
            dest_dir = os.path.abspath(os.path.join(base_dir, current_dir))
            dest_path = os.path.join(dest_dir, os.path.basename(rel_path))
            rel_dst = dest_path.replace(base_dir, '')
            if not valid_user_path(configuration, dest_path, base_dir, True):
                logger.error('%s tried to %s move to restricted path %s ! (%s)'
                             % (user_id, op_name, dest_path, current_dir))
                output_objects.append(
                    {'object_type': 'error_text',
                     'text': "Invalid destination "
                     "(%s expands to an illegal path)"
                     % current_dir})
                moved = False
            elif not check_write_access(dest_path, parent_dir=True):
                logger.warning('%s called without write access: %s'
                               % (op_name, dest_path))
                output_objects.append(
                    {'object_type': 'error_text', 'text':
                     'cannot move "%s": inside a read-only location!'
                     % rel_dst})
                moved = False
            else:
                try:
                    makedirs_rec(dest_dir, configuration)
                    move(abs_src_path, dest_path)
                    moved = True
                except Exception, exc:
                    logger.error('could not move %s to %s: %s'
                                 % (abs_src_path, dest_path, exc))
                    moved = False
            file_entry = {'object_type': 'uploadfile', rel_path: moved}
            if moved:
                file_entry['name'] = rel_dst
                file_entry['size'] = get_file_size(dest_path, logger)
                # NOTE: normpath+lstrip to avoid leading // and thus no base URL
                file_entry['url'] = os.path.normpath("/%s/%s"
                                                     % (redirect_path.lstrip('/'),
                                                        rel_dst))

                if configuration.site_enable_gdp:
                    gdp_project = get_project_from_client_id(configuration,
                                                             client_id)
                    msg = "'%s'" % rel_dst[len(gdp_project)+1:]
                    project_log(configuration, 'https', client_id, 'wrote',
                                msg, user_addr=environ['REMOTE_ADDR'])

            uploaded.append(file_entry)
        logger.info('move done: %s' % ' '.join([i[0] for i in upload_files]))
        return (output_objects, status)
    elif action != 'put':
        output_objects.append(
            {'object_type': 'error_text',
             'text': 'Invalid action: %s!' % action})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Handle actual uploads (action == 'put')

    # Put automatically takes place relative to dst_dir
    for (rel_path, chunk_tuple) in upload_files:
        logger.info('handling %s chunk %s' % (rel_path, chunk_tuple[1:]))
        (chunk, offset, chunk_last) = chunk_tuple
        chunk_size = len(chunk)
        range_size = 1 + chunk_last - offset
        abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
        if not os.path.isdir(os.path.dirname(abs_path)):
            output_objects.append({'object_type': 'error_text',
                                   'text': "cannot write: no such file or directory:"
                                   " %s)" % rel_path})
            return (output_objects, returnvalues.CLIENT_ERROR)

        file_entry = {'object_type': 'uploadfile', 'name': rel_path}
        logger.debug('write %s chunk of size %d' % (rel_path, chunk_size))
        if chunk_size == range_size and \
                write_chunk(abs_path, chunk, offset, logger, 'r+b'):
            if verbose(flags):
                output_objects.append({'object_type': 'text',
                                       'text': 'wrote chunk %s at %d'
                                       % (chunk_tuple[1:], offset)})
            logger.info('wrote %s chunk at %s' % (abs_path, chunk_tuple[1:]))
            file_entry["size"] = os.path.getsize(abs_path)
            # NOTE: normpath+lstrip to avoid leading // and thus no base URL
            file_entry["url"] = os.path.normpath("/%s/%s"
                                                 % (redirect_path.lstrip('/'),
                                                    rel_path))
            if current_dir == upload_tmp_dir:
                file_entry["deleteType"] = "POST"
                file_entry["deleteUrl"] = del_url % \
                    (id_args, output_format,
                     filename_field,
                     os.path.basename(rel_path),
                     files_field, "dummy", csrf_field,
                     csrf_token)
            else:
                file_entry["moveType"] = "POST"
                file_entry["moveDest"] = current_dir
                file_entry["moveUrl"] = move_url % \
                    (id_args, output_format,
                     filename_field,
                     os.path.basename(rel_path),
                     files_field, "dummy", dest_field,
                     current_dir, csrf_field,
                     csrf_token)
        else:
            logger.error('could not write %s chunk %s (%d vs %d)'
                         % (abs_path, chunk_tuple[1:], chunk_size, range_size))
            output_objects.append({'object_type': 'error_text',
                                   'text': 'failed to write chunk %s at %d'
                                   % (chunk_tuple[1:], offset)})
            file_entry["error"] = "failed to write chunk %s - try again" \
                                  % (chunk_tuple[1:], )

        uploaded.append(file_entry)

    logger.info('put done: %s (%s)' % (' '.join([i[0] for i in upload_files]),
                                       uploaded))
    return (output_objects, status)
