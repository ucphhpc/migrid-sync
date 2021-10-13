#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rangefileaccess - read or write byte range inside file
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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

# Minimum intrusion Grid
# Martin Rehr, 2006

"""CGI module that enables MiG jobs to perform ranged GET/PUT and
DELETE http requests.
NOTE: ranges (filepositions) are handled according to the w3c HTTP
standard rfc2616.
"""

from __future__ import absolute_import

import cgi
import os
import sys
# only enable for debugging
# import cgitb
# cgitb.enable()

from mig.shared.cgishared import init_cgiscript_possibly_with_cert
from mig.shared.base import client_id_dir, invisible_path
from mig.shared.functional import validate_input, REJECT_UNSET
from mig.shared.validstring import valid_user_path


def signature():
    """Signature of the main function"""

    defaults = {
        'path': REJECT_UNSET,
        'filename': [''],
        'iosessionid': [''],
        'file_startpos': [-1],
        'file_endpos': [-1],
    }
    return ['', defaults]


def get(o, fileinfo_dict):

    # Convert file_startpos to int

    try:
        file_startpos = int(fileinfo_dict['file_startpos'])
    except:
        file_startpos = -1

    # Convert file_startend to int

    try:
        file_endpos = int(fileinfo_dict['file_endpos'])
    except:
        file_endpos = -1

    local_path = fileinfo_dict['base_path'] + fileinfo_dict['path']

    # If file exists open it.
    # o.logger.debug("opening 'rb': " + local_path)

    try:
        filelen = os.path.getsize(local_path)
        filehandle = open(local_path, 'rb')
    except Exception as err:
        o.out('%s' % err)
        return False

    if file_startpos == -1:
        file_startpos = 0

    if file_endpos == -1:
        file_endpos = filelen - 1

    if file_endpos > filelen - 1:
        file_endpos = filelen - 1

    # Startpos is after end of file

    if file_startpos >= filelen:
        o.out('file_startpos: %s after end of file: %s '
              % (file_startpos, filelen))
        return False
    elif file_startpos > file_endpos:

        # Apache handles 'file_startpos>file_endpos' by serving the whole file
        # Due to compatibility, so do we.

        file_startpos = 0
        file_endpos = filelen - 1

    datalen = file_endpos - file_startpos + 1

    # Note that we do not use CGIOutput for data, due to performance issues,
    # We do however use the cgi protocol: status + \n + data
    # If seek fails, abort.

    try:
        filehandle.seek(file_startpos, 0)
    except Exception as err:
        o.out("Seeking File: '%s' failed: %s\n" % (err,
                                                   fileinfo_dict['path']))
        return False

    # If write fails, do nothing, it's up to the client,
    # to find out how many bytes were actually sent to him.

    read_status = True
    try:

        # Write status

        sys.stdout.write('0\n')
        sys.stdout.flush()

        # Write data in chuncks of 'block_size'
        # This is done as large files will fill up the buffers
        # and use up the servers memory, if flush'es are not made frequently

        block_size = 65536

        bytes_left = datalen
        while bytes_left > 0:
            if bytes_left < block_size:
                block_size = bytes_left
            sys.stdout.write(filehandle.read(block_size))
            sys.stdout.flush()
            bytes_left -= block_size
    except Exception as err:
        o.out("""
Reading File: '%s' failed: %s
""" % (err,
              fileinfo_dict['path']))
        read_status = False

    # If close fails, do nothing

    try:
        filehandle.close()
    except Exception as err:
        o.out("Closing File: '%s' failed: %s\n" % (err,
                                                   fileinfo_dict['path']))
        read_status = False

    return read_status


def put(o, fileinfo_dict):

    # Convert file_startpos to int

    try:
        file_startpos = int(fileinfo_dict['file_startpos'])
    except:
        file_startpos = -1

    # Convert file_startend to int

    try:
        file_endpos = int(fileinfo_dict['file_endpos'])
    except:
        file_endpos = -1

    # Convert content_length to int

    try:
        content_length = int(os.getenv('CONTENT_LENGTH'))
    except Exception as err:
        content_length = 0

    local_path = fileinfo_dict['base_path'] + fileinfo_dict['path']

    # If file exists we update it, otherwise it is created.

    if os.path.isfile(local_path):

        # o.logger.debug("opening 'r+b': " + local_path)

        try:
            filehandle = open(local_path, 'r+b')
        except Exception as err:
            o.out('\n%s' % err)
            return False
    else:
        try:
            filehandle = open(local_path, 'w+b')
        except Exception as err:

            # o.logger.debug("opening 'w+b': " + local_path)

            o.out('\n%s' % err)
            return False

    # If content_length is 0, we do nothing
    # and an empty file is created if file doesn't exist.

    datalen = 0
    if content_length > 0:
        if file_startpos == -1 and file_endpos != -1:

            # If file_startpos not given use fileend_pos and content_length

            file_startpos = (file_endpos - content_length) - 1
        elif file_startpos != -1 and file_endpos == -1 or file_startpos\
                != -1 and file_endpos - file_startpos > content_length - 1:

            # If file_endpos not given or file_endpos exceeds the amount
            # of data retrieved, use filestart_pos and content_length

            file_endpos = (file_startpos + content_length) - 1
        elif file_startpos == -1 and file_endpos == -1:

            # Write the whole file

            file_startpos = 0
            file_endpos = content_length - 1

        datalen = file_endpos - file_startpos + 1

        try:
            filehandle.seek(file_startpos, 0)
            filehandle.write(sys.stdin.read(datalen))
        except Exception as err:
            o.out('\n%s' % err)
            return False

        try:
            filehandle.close()
        except Exception as err:
            o.out('\n%s' % err)
            return False

    o.logger.info("\nFile: '%s' <- %s bytes written successfully. %s"
                  % (fileinfo_dict['path'], datalen, fileinfo_dict))
    return True

# TODO: port to new functionality backend structure with standard validation

# ## Main ###


(logger, configuration, client_id, o) = \
    init_cgiscript_possibly_with_cert()

if configuration.site_enable_gdp:
    o.out('Not available on this site!')
    o.reply_and_exit(o.CLIENT_ERROR)

client_dir = client_id_dir(client_id)

# Check we are using GET, PUT or DELETE method

valid_methods = ['GET', 'PUT', 'DELETE']
action = os.getenv('REQUEST_METHOD')
if not action in valid_methods:
    o.out('Invalid HTTP method (use one of %s)!'
          % ', '.join(valid_methods))
    o.reply_and_exit(o.ERROR)

# General fieldstorage parsing doesn't work for upload!
# Generate fileinfo_dict from query string - this is dictionary on the form
# {"variablename1":[value1, value2, .. ], }

raw_fileinfo_dict = cgi.parse(sys.stdin)

#logger.debug("parsing input: %s" % raw_fileinfo_dict)

defaults = signature()[1]
output_objects = []
# IMPORTANT: validate all input args before doing ANYTHING with them!
(validate_status, accepted) = validate_input(
    raw_fileinfo_dict,
    defaults,
    output_objects,
    allow_rejects=False,
    # NOTE: path cannot use wildcards here
    typecheck_overrides={},
)
if not validate_status:
    logger.error("input validation for %s failed: %s" %
                 (client_id, accepted))
    o.out('Invalid input arguments received!')
    o.reply_and_exit(o.ERROR)

# Simply use the first of the provided values
fileinfo_dict = {}
for (key, value_list) in accepted.items():
    fileinfo_dict[key] = value_list[0]

# Backwards compatibility

if fileinfo_dict.get('filename', ''):
    fileinfo_dict['path'] = fileinfo_dict['filename']


if 'path' not in fileinfo_dict:

    # Check if path was in querystring.

    o.out('No path provided, unable to process file!')
    o.reply_and_exit(o.ERROR)

logger.info('rangefileaccess on %s (%s)' % (fileinfo_dict['path'],
                                            fileinfo_dict))

if client_id:

    # logger.debug("Certificate found as a user cert: " + client_id)

    fileinfo_dict['base_path'] = \
        os.path.normpath(os.path.join(configuration.user_home,
                                      client_dir))
elif 'iosessionid' in fileinfo_dict:

    fileinfo_dict['base_path'] = configuration.webserver_home + \
        fileinfo_dict['iosessionid']
else:

    o.out('No certificate found and no iosessionid provided, unable to process file!'
          )
    o.reply_and_exit(o.ERROR)


# Please note that base_dir must end in slash to avoid access to other
# user dirs when own name is a prefix of another user name

base_dir = fileinfo_dict['base_path'] = fileinfo_dict['base_path'] + os.sep

# Check directory traversal attempts before actual handling to avoid
# leaking information about file system layout while allowing
# consistent error messages
path = fileinfo_dict['path']
unfiltered_match = [base_dir + os.sep + fileinfo_dict['path']]
match = []
for server_path in unfiltered_match:
    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_path = os.path.abspath(server_path)
    if not valid_user_path(configuration, abs_path, base_dir, True):
        logger.warning('%s tried to access restricted path %s ! (%s)'
                       % (client_id, abs_path, path))
        o.out('Access to %s is prohibited!' % fileinfo_dict['path'])
        o.reply_and_exit(o.CLIENT_ERROR)


if action == 'GET':
    status = get(o, fileinfo_dict)

    # if status, we have already written to the client, see get method.

    if not status:
        o.reply_and_exit(o.ERROR)
elif action == 'PUT':

    status = put(o, fileinfo_dict)

    if status == True:
        o.reply_and_exit(o.OK)
    else:
        o.reply_and_exit(o.ERROR)
elif action == 'DELETE':

    try:
        local_path = fileinfo_dict['base_path'] + fileinfo_dict['path']
        os.remove(local_path)

        # o.logger.debug("\nFile: '" + fileinfo_dict["path"] + "' <- deleted successfully.")

        o.reply_and_exit(o.OK)
    except Exception as err:

        # o.logger.debug("\nFile: '" + fileinfo_dict["path"] + "' <- not deleted: %s" % err)

        o.reply_and_exit(o.ERROR)
else:
    o.internal("REQUEST_METHOD: %r <- NOT supported." % action)
    o.reply_and_exit(o.ERROR)
