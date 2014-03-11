#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# uploadchunked - Chunked and efficient file upload back end
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Chunked file upload back end"""

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import max_upload_files, max_upload_chunks, \
     upload_block_size, upload_tmp_dir
from shared.fileio import strip_dir, write_chunk
from shared.functional import validate_input_and_cert
from shared.handlers import correct_handler
from shared.init import initialize_main_variables
from shared.safeinput import valid_path
from shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {
        }
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

def parse_form_upload(user_args, client_id, configuration):
    """Parse upload file and chunk entries from user_args. Chunk limits are
    extracted from content-range http header in environment.
    """
    files, rejected = [], []

    # TMP! only support single filename and chunk for now
    #for name_index in xrange(max_upload_files):
    #    if user_args.has_key('files[]filename') and \
    #           len(user_args['files[]filename']) > name_index:
    for name_index in [0]:
        if user_args.has_key('files[]filename'):
            filename = user_args['files[]filename']
        else:
            # No more files
            break
        #for chunk_index in xrange(max_upload_chunks):
        #    if user_args.has_key('files[]') and \
        #           len(user_args['files[]']) > chunk_index:
        for chunk_index in [0]:
            if user_args.has_key('files[]'):
                chunk = user_args['files[]'][chunk_index]
            else:
                break
            if not filename.strip():
                continue
            (chunk_first, chunk_last) = extract_chunk_region(configuration)
            if len(chunk) > upload_block_size:
                configuration.logger.error('skip bigger than allowed chunk')
                continue
            elif chunk_last < 0:
                chunk_last = len(chunk) - 1
            filename = strip_dir(filename)
            try:
                valid_path(filename)
            except Exception, exc:
                rejected.append('invalid filename: %s (%s)' % (filename, exc))
                continue
            files.append((filename, (chunk, chunk_first, chunk_last)))
    return (files, rejected)

def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    logger.info('Extracting input in %s' % op_name)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
    defaults = signature()[1]
    
    logger.info('Extracted input in %s: %s' % (op_name,
                                               user_arguments_dict.keys()))

    # All non-file fields must be validated
    validate_args = dict([(key, user_arguments_dict.get(key, val)) for \
                         (key, val) in defaults.items()])
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

    logger.info('validated input in %s: %s' % (op_name, validate_args.keys()))

    if not correct_handler('POST'):
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : 'Only accepting POST requests to prevent unintended updates'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    logger.info('parsing upload form in %s' % op_name)

    # Now parse and validate files to archive

    for name in defaults.keys():
        if user_arguments_dict.has_key(name):
            del user_arguments_dict[name]

    (upload_files, upload_rejected) = parse_form_upload(user_arguments_dict,
                                                        client_id,
                                                        configuration)
    if upload_rejected:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Errors parsing upload files: %s' % \
                               '\n '.join(upload_rejected)})
        return (output_objects, returnvalues.CLIENT_ERROR)
    if not upload_files:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'No files included to upload!'})
        return (output_objects, returnvalues.CLIENT_ERROR)

    logger.info('Filtered input validated with result: %s' % accepted)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir, upload_tmp_dir)) + os.sep

    if not os .path.isdir(base_dir):
        try:
            os.makedirs(base_dir)
        except Exception, exc:
            logger.error('%s could not create upload tmp dir %s ! (%s)'
                         % (op_name, base_dir, exc))
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : "Problem creating temporary upload dir"})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'header', 'text'
                          : 'Uploading file chunk(s)'})

    # Check directory traversal attempts before actual handling to avoid
    # leaking information about file system layout while allowing consistent
    # error messages

    logger.info('Looping through files: %s' % \
                ' '.join([i[0] for i in upload_files]))
    chunk_no = 0
    uploaded = []
    for (rel_path, chunk_tuple) in upload_files:
        logger.info('handling %s chunk no %d' % (rel_path, chunk_no))
        (chunk, offset, chunk_last) = chunk_tuple
        chunk_size = len(chunk)
        range_size = 1 + chunk_last - offset
        real_path = os.path.realpath(os.path.join(base_dir, rel_path))

        if not valid_user_path(real_path, base_dir, True):
            logger.warning('%s tried to %s restricted path %s ! (%s)'
                           % (client_id, op_name, real_path, rel_path))
            output_objects.append(
                {'object_type': 'error_text', 'text'
                 : "Invalid destination (%s expands to an illegal path)" % \
                 rel_path})
            return (output_objects, returnvalues.CLIENT_ERROR)

        if not os.path.isdir(os.path.dirname(real_path)):
            output_objects.append({'object_type': 'error_text', 'text'
                                   : "cannot write: no such file or directory:"
                                   " %s)" % rel_path})
            return (output_objects, returnvalues.CLIENT_ERROR)

        logger.info('write %s chunk of size %d' % (rel_path, len(chunk)))
        if chunk_size == range_size and \
               write_chunk(real_path, chunk, offset, logger, 'r+b'):
            output_objects.append({'object_type': 'text', 'text'
                                   : 'wrote chunk %d at %d' % \
                                   (chunk_no, offset)})
            logger.info('wrote %s chunk no %d' % (real_path, chunk_no))
            uploaded.append(
                {'object_type': 'uploadfile', 'name': rel_path,
                 "size": os.path.getsize(real_path), "url": 
                 os.path.join("/cert_redirect", upload_tmp_dir, rel_path),
                 })
            chunk_no += 1
        else:
            logger.error('could not write %s chunk no %d (%d vs %d)' % \
                         (real_path, chunk_no, chunk_size, range_size))
            output_objects.append({'object_type': 'error_text', 'text'
                                   : 'failed to write chunk %d at %d' % \
                                   (chunk_no, offset)})
            uploaded.append(
                {'object_type': 'uploadfile', 'name': rel_path,
                 "error": "failed to write chunk %d - try again" % chunk_no})

    output_objects.append({'object_type': 'uploadfiles', 'files': uploaded})

    logger.info('done')
    return (output_objects, status)
