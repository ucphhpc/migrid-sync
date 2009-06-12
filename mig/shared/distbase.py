#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# distbase - [insert a few words of module description on this line]
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

"""This module contains various helper functions for distributed
server IO. It is imported and used by the public interface modules.
"""

__version__ = '$Revision: 2084 $'
__revision__ = __version__

# $Id: distbase.py 2084 2007-09-11 08:39:37Z jones $

import sys
import StringIO
import httplib
import urlparse
import time
from urllib import urlencode
from os.path import normpath
from os import getenv, environ

# ###################
# Network settings #
# ###################
# Where to lookup current leader

LEADER_HOST = 'amigos18.diku.dk'

# ports to use for https sessions

HTTPS_CERT_PORT = 443
HTTPS_SID_PORT = 8092
HOME = getenv('HOME')

# Fallback for CGIs where getenv(HOME) doesn't work

if not HOME:
    cgi_path = getenv('SCRIPT_FILENAME')
    if not cgi_path:
        print 'Failed to extract HOME from environment: %s' % environ
        sys.exit(1)
    HOME = cgi_path[:cgi_path.find('/mig/cgi-bin/')]
KEY_DIR = '%s/MiG-certificates' % HOME

# we reuse the apache key/cert without passphrase to avoid
# socket.ssl requesting passphrase from stdin.
# TODO: is it ok to use apache key without passphrase here?
# KEY_PATH = "%s/key.pem" % KEY_DIR

KEY_PATH = '%s/server.key' % KEY_DIR

# CERT_PATH = "%s/cert.pem" % KEY_DIR

CERT_PATH = '%s/server.crt' % KEY_DIR
CA_ID = '/C=DK/ST=Denmark/O=IMADA/OU=MiG/CN=MiGCA'
SERVER_ID_FIELD = '/OU=MiG-Server/'

# Session ID used to access storage functions

BASE_ID = \
    '8440bedf3a96d58360cbe6e825789a6ac4arra56ab1a0803a58e8a2db4f68c9ad'

# Name of the shared pseudo user home accessible by all
# servers through BASE_HOME.

BASE_HOME = 'MiG-Server'

# User agent when putting files - very important to avoid put
# recursion loops

USER_AGENT = 'MiG-distributed-server'

# #################
# Other settings #
# #################
# http codes for success and redirect

HTTP_OK = (200, 201, 204)
HTTP_REDIRECT = (301, 302)

# ###############
# Leader cache #
# ###############
# Limit repeated requests for current leader without missing changes

leader_cache = {}
leader_cache['current'] = None
leader_cache['timestamp'] = None

# Minimum number of seconds between leader probes

leader_cache['interval'] = 10

# ###################
# Public functions #
# ###################


def get_address():
    """lookup local address for use in comparison with leader"""

    import socket
    return socket.gethostbyaddr(socket.gethostname())[-1][0]


def get_leader():
    """Lookup group leader address if not cached"""

    if leader_cache['current'] and time.time()\
         < leader_cache['timestamp'] + leader_cache['interval']:
        return leader_cache['current']

    # TODO: lookup list of possible leaders from www.migrid.org or
    # similar

    host = LEADER_HOST
    port = HTTPS_SID_PORT
    path = '/storage/interface.py'
    arguments = [('function', 'get_leader_ip')]
    (status, data) = http_no_payload(host, port, 'GET', path, arguments)
    if status != 0:
        return None
    data = data.strip()
    if data:
        leader_cache['current'] = data
        leader_cache['timestamp'] = time.time()
    return data


def verify_certificate(ssl_socket):
    try:
        server_id = ssl_socket.server()
    except Exception, err:
        raise Exception('Server certificate extraction failed! %s'
                         % err)
    try:
        ca_id = ssl_socket.issuer()
    except Exception, err:
        raise Exception('CA certificate extraction failed! %s' % err)

    # Debug only print
    # print "Received server certificate data:"
    # print repr(server_id)
    # print "Received CA certificate data:"
    # print repr(ca_id)

    if -1 == server_id.find(SERVER_ID_FIELD):
        raise Exception('Server certificate verification failed!'
                         + '(%s vs. %s)' % (server_id, SERVER_ID_FIELD))
    elif CA_ID != ca_id:
        raise Exception('CA certificate verification failed!'
                         + '(%s vs. %s)' % (server_id, SERVER_ID_FIELD))


def http_no_payload(
    host,
    port,
    method,
    path,
    query=[],
    ):
    """General HTTP operation shared by all functions that operate
    without any data payload.
    HTTPS operation uses key/certificate if port is HTTPS_CERT_PORT.
    """

    max_redirects = 3

    # always remove extra slashes

    location = normpath(path)
    for _ in range(max_redirects):
        if HTTPS_CERT_PORT == port:
            connection = httplib.HTTPSConnection(host, port, KEY_PATH,
                    CERT_PATH)
        else:
            connection = httplib.HTTPSConnection(host, port)

        connection.connect()
        ssl_socket = connection.sock._ssl
        try:
            verify_certificate(ssl_socket)
        except Exception, err:
            http_status = -1
            response = StringIO.StringIO('')
            connection.close()
            break

        # write header

        query_string = '?%s' % urlencode(query).strip()
        if query:
            location += query_string
        connection.putrequest(method, location)
        connection.putheader('User-Agent', USER_AGENT)
        connection.putheader('Connection', 'keep-alive')
        connection.putheader('Keep-Alive', '300')
        connection.endheaders()

        # get response

        response = connection.getresponse()
        http_status = response.status

        if not http_status in HTTP_REDIRECT:
            break

        # Retry with redirection address

        url = response.getheader('location', '')
        connection.close()
        (_, host_port, location, _, _) = urlparse.urlsplit(url)
        if ':' in host_port:
            (host, port) = host_port.split(':', 2)
            port = int(port)
        else:
            host = host_port

    if not http_status in HTTP_OK:
        raise IOError("Error: HTTP %s %s failed! (%d, '%s')" % (method,
                      path, http_status, response.read()))

    # Response contains status code in first line followed by output

    output = StringIO.StringIO(response.read())

    # The above read requires connection to remain open this far

    connection.close()
    status_line = output.readline()
    reply = ''
    try:
        status = int(status_line)
    except ValueError, verr:
        status = 255
        reply = status_line
    reply += output.read()
    output.close()
    return (status, reply)


def http_chmod(
    host,
    port,
    path,
    mode,
    ):
    """Simply use general function"""

    arguments = [('mode', mode)]
    return http_no_payload(host, port, 'CHMOD', path, arguments)


def http_listdir(host, port, path):
    """Simply use general function"""

    return http_no_payload(host, port, 'LISTDIR', path)


def http_mkdir(
    host,
    port,
    path,
    mode,
    ):
    """Simply use general function"""

    arguments = [('mode', mode)]
    return http_no_payload(host, port, 'MKDIR', path, arguments)


def http_remove(host, port, path):
    """Simply use general function"""

    return http_no_payload(host, port, 'REMOVE', path)


def http_rename(
    host,
    port,
    src,
    dst,
    ):
    """Simply use general function"""

    arguments = [('dst', dst)]
    return http_no_payload(host, port, 'RENAME', src, arguments)


def http_rmdir(host, port, path):
    """Simply use general function"""

    return http_no_payload(host, port, 'RMDIR', path)


def http_stat(
    host,
    port,
    path,
    flags,
    ):

    arguments = [('flags', flags)]
    return http_no_payload(host, port, 'STAT', path, arguments)


def http_symlink(
    host,
    port,
    src,
    dst,
    ):

    arguments = [('dst', dst)]
    return http_no_payload(host, port, 'SYMLINK', src, arguments)


def http_walk(
    host,
    port,
    path,
    topdown,
    ):
    """Simply use general function"""

    arguments = [('topdown', topdown)]
    return http_no_payload(host, port, 'WALK', path, arguments)


def http_get(host, port, path):
    """HTTP GET operation slightly different from other functions
    that operate without any data payload.
    HTTPS operation uses key/certificate if port is HTTPS_CERT_PORT.
    """

    method = 'GET'

    # always remove extra slashes

    path = normpath(path)
    if HTTPS_CERT_PORT == port:
        connection = httplib.HTTPSConnection(host, port, KEY_PATH,
                CERT_PATH)
    else:
        connection = httplib.HTTPSConnection(host, port)

    connection.connect()
    ssl_socket = connection.sock._ssl
    try:
        verify_certificate(ssl_socket)
    except Exception, err:
        connection.close()
        raise IOError('Error: HTTPS %s session with %s failed!'
                       % (method, host))

    # write header

    connection.putrequest(method, path)
    connection.putheader('User-Agent', USER_AGENT)
    connection.putheader('Connection', 'keep-alive')
    connection.putheader('Keep-Alive', '300')

    # connection.putheader('Transfer-Encoding', 'chunked')

    connection.endheaders()

    # get response

    response = connection.getresponse()
    status = response.status
    reply = response.read()
    connection.close()

    if not status in HTTP_OK:
        raise IOError('Error: HTTP %s %s failed! (%d, %s)' % (method,
                      path, status, reply))

    return (status, reply)


def http_put(
    host,
    port,
    path,
    data,
    ):
    """HTTP PUT operation quite different from other functions
    that operate without any data payload.
    HTTPS operation uses key/certificate if port is HTTPS_CERT_PORT.
    """

    method = 'PUT'

    # print "DEBUG: inside http_put!"
    # always remove extra slashes

    path = normpath(path)
    if HTTPS_CERT_PORT == port:
        connection = httplib.HTTPSConnection(host, port, KEY_PATH,
                CERT_PATH)
    else:
        connection = httplib.HTTPSConnection(host, port)

    connection.connect()
    ssl_socket = connection.sock._ssl
    try:
        verify_certificate(ssl_socket)
    except Exception, err:
        connection.close()
        raise IOError('Error: HTTPS %s session with %s failed!'
                       % (method, host))

    # write header

    connection.putrequest('PUT', path)
    connection.putheader('User-Agent', USER_AGENT)
    connection.putheader('Connection', 'keep-alive')
    connection.putheader('Keep-Alive', '300')

    # connection.putheader('Transfer-Encoding', 'chunked')

    connection.putheader('Content-Length', str(len(data)))
    connection.endheaders()

    # write body if non-empty

    if data:
        connection.send(data)

    # get response

    response = connection.getresponse()
    status = response.status
    connection.close()

    if not status in HTTP_OK:
        raise IOError('Error: http_put could not put file! %d' % status)

    # print "DEBUG: http_put done!"

    return (status, response.read())


def get_range(
    host,
    port,
    path,
    offset,
    bytes,
    ):
    """Wrapper around http_get to simulate real HTTP GET RANGE"""

    # TODO: get only range

    (status, data) = http_get(host, port, path)
    if -1 == bytes:
        return (status, data[offset:])
    return (status, data[offset:offset + bytes])


def put_range(
    host,
    port,
    path,
    offset,
    bytes,
    data,
    ):
    """Fetch existing file contents and update specified region.
    Insert zero bytes if offset exceeds old data length like local
    write() does.
    """

    # TODO: use real range put when supported

    (_, old_data) = http_get(host, port, path)
    old_length = len(old_data)
    new_length = offset + bytes
    if old_length < new_length:
        old_data += (new_length - old_length) * '\x00'
    new_data = old_data[:offset] + data + old_data[offset + bytes:]
    return http_put(host, port, path, new_data)


def create_session_link(session_id, user):
    """Request the current leader to create a link from the supplied
    session_id to user home.
    """

    leader = get_leader()
    if not leader:
        return (1, 'No leader found!')
    host = leader
    port = HTTPS_SID_PORT
    location = '/storage/interface.py'
    arguments = [('function', 'create_session_link'), ('session_id',
                 session_id), ('user', user)]
    (status, output) = http_no_payload(host, port, 'GET', location,
            arguments)
    output = output.strip()
    return (status, output)


def remove_session_link(session_id, user):
    """Request the current leader to remove the link from the supplied
    session_id to user home.
    """

    leader = get_leader()
    if not leader:
        return (1, 'No leader found!')
    host = leader
    port = HTTPS_SID_PORT
    location = '/storage/interface.py'
    arguments = [('function', 'remove_session_link'), ('session_id',
                 session_id), ('user', user)]
    (status, output) = http_no_payload(host, port, 'GET', location,
            arguments)
    output = output.strip()
    return (status, output)


def open_session(
    path,
    session_type,
    retries=2,
    retry_delay=1,
    ):
    """Request the current leader to open the active session for
    file with supplied path.
    Automatic retry is possible with the help of retries and
    retry_timeout.
    """

    # always remove extra slashes

    path = normpath(path)
    (status, response) = (-1, '')
    for attempt in range(retries + 1):
        leader = get_leader()
        if not leader:
            response += 'Attempt %d failed: No leader found! ' % attempt
            continue
        host = leader
        port = HTTPS_SID_PORT
        location = '/storage/interface.py'
        arguments = [('function', 'open_session'), ('session_id',
                     BASE_ID), ('file_name', path), ('type',
                     session_type)]
        (status, output) = http_no_payload(host, port, 'GET', location,
                arguments)
        output = output.strip()
        if 0 == status:

            # Ignore any previous errors

            response = output
            break
        else:
            response += 'Attempt %d failed: %s\n' % (attempt, output)
            time.sleep(retry_delay)
    return (status, response)


def close_session(
    path,
    session_type,
    retries=2,
    retry_delay=1,
    ):
    """Tell the current leader to close the active session for
    file with supplied path.
    """

    # always remove extra slashes

    path = normpath(path)
    response = ''
    for attempt in range(retries + 1):
        leader = get_leader()
        if not leader:
            response += 'Error in attempt %d: No leader found!\n'\
                 % attempt
            continue
        host = leader
        port = HTTPS_SID_PORT
        location = '/storage/interface.py'
        arguments = [('function', 'close_session'), ('session_id',
                     BASE_ID), ('file_name', path), ('type',
                     session_type)]
        (status, output) = http_no_payload(host, port, 'GET', location,
                arguments)
        output = output.strip()
        if 0 == status:

            # Ignore any previous errors

            response = output
            break
        else:
            response += 'Error in attempt %d: %s\n' % (attempt, output)
            time.sleep(retry_delay)
    return (status, response)


