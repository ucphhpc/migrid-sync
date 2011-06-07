#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rangefileaccess - [insert a few words of module description on this line]
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

# Minimum intrusion Grid
# Martin Rehr, 2006

"""CGI module that enables MiG jobs to perform ranged GET/PUT and
DELETE http requests.
NOTE: ranges (filepositions) are handled according to the w3c HTTP
standard rfc2616.
"""

import cgi
import cgitb
cgitb.enable()
import os
import sys

# import urllib

# MiG imports

from shared.base import client_id_dir
from shared.scriptinput import fieldstorage_to_dict
from shared.cgishared import init_cgiscript_possibly_with_cert


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
    except Exception, err:
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

    # o.logger.debug("file_start: " + str(file_startpos))
    # o.logger.debug("file_end: " + str(file_endpos))
    # o.logger.debug("filelen: " + str(filelen))
    # o.logger.debug("datalen: " + str(datalen))

    # Note that we do not use CGIOutput for data, due to performance issues,
    # We do however use the cgi protocol: status + \n + data
    # If seek fails, abort.

    try:
        filehandle.seek(file_startpos, 0)
    except Exception, err:
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
    except Exception, err:
        o.out("""
Reading File: '%s' failed: %s
""" % (err,
              fileinfo_dict['path']))
        read_status = False

    # If close fails, do nothing

    try:
        filehandle.close()
    except Exception, err:
        o.out("Closing File: '%s' failed: %s\n" % (err,
              fileinfo_dict['path']))
        read_status = False

    # if read_status:
    #    o.logger.debug("\nFile: '%s' <- %s bytes read successfully." % (fileinfo_dict["path"],str(datalen)))

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
    except Exception, err:
        content_length = 0

    local_path = fileinfo_dict['base_path'] + fileinfo_dict['path']

    # If file exists we update it, otherwise it is created.

    if os.path.isfile(local_path):

        # o.logger.debug("opening 'r+b': " + local_path)

        try:
            filehandle = open(local_path, 'r+b')
        except Exception, err:
            o.out('\n%s' % err)
            return False
    else:
        try:
            filehandle = open(local_path, 'w+b')
        except Exception, err:

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

        # o.logger.debug("file_start: " + str(file_startpos))
        # o.logger.debug("file_end: " + str(file_endpos))
        # o.logger.debug("content: " + str(content_length))
        # o.logger.debug("datalen: " + str(datalen))

        try:
            filehandle.seek(file_startpos, 0)
            filehandle.write(sys.stdin.read(datalen))
        except Exception, err:
            o.out('\n%s' % err)
            return False

        try:
            filehandle.close()
        except Exception, err:
            o.out('\n%s' % err)
            return False

    o.logger.info("\nFile: '%s' <- %s bytes written successfully. %s"
                   % (fileinfo_dict['path'], datalen, fileinfo_dict))
    return True


# ## Main ###

(logger, configuration, client_id, o) = \
    init_cgiscript_possibly_with_cert()
client_dir = client_id_dir(client_id)

# Debug info
# logger.debug("REQUEST_METHOD: " + str(os.getenv("REQUEST_METHOD")))
# logger.debug("CONTENT_LENGTH: " + str(os.getenv("CONTENT_LENGTH")))
# logger.debug("CONTENT TYPE: " + str(os.getenv("CONTENT_TYPE")))
# logger.debug("QUERY_STRING: " + str(os.getenv("QUERY_STRING")))
# logger.debug("REQUEST_URI: " + urllib.unquote(str(os.getenv("REQUEST_URI"))))

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

fileinfo_dict = cgi.parse(sys.stdin)

# Simply use the first of the provided values

for (key, value_list) in fileinfo_dict.items():
    fileinfo_dict[key] = value_list[0]

# Backwards compatibility

if fileinfo_dict.has_key('filename'):
    fileinfo_dict['path'] = fileinfo_dict['filename']

if not fileinfo_dict.has_key('path'):

    # Check if path was in querystring.

    o.out('No path provided, unable to process file!')
    o.reply_and_exit(o.ERROR)

logger.info('rangefileaccess on %s (%s)' % (fileinfo_dict['path'],
            fileinfo_dict))

if client_id:

    # logger.debug("Certificate found as a user cert: " + client_id)

    fileinfo_dict['base_path'] = \
        os.path.normpath(os.path.join(configuration.user_home,
                         client_dir)) + os.sep
elif fileinfo_dict.has_key('iosessionid'):

    fileinfo_dict['base_path'] = configuration.webserver_home\
         + fileinfo_dict['iosessionid'] + '/'
else:

    o.out('No certificate found and no iosessionid provided, unable to process file!'
          )
    o.reply_and_exit(o.ERROR)

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
    except Exception, err:

        # o.logger.debug("\nFile: '" + fileinfo_dict["path"] + "' <- not deleted: %s" % err)

        o.reply_and_exit(o.ERROR)
else:
    o.internal("REQUEST_METHOD: '" + str(action) + "' <- NOT supportet."
               )
    o.reply_and_exit(o.ERROR)

