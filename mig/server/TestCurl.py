#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# TestCurl - [insert a few words of module description on this line]
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

#
# Test pycurl HTTPS transfers with default Nordugrid certificates.
# Connect to HTTPS server at mig-1.imada.sdu.dk and retrieve list of MiG files
#

import sys
import pycurl
import StringIO
import os
import pwd

http_success = 200


def GetFile():

    # Defaults

    url = 'cgi-bin/ls.py'
    base_dir = '.'

    # Just using default NorduGRID certificates for now

    os.environ['HOME'] = pwd.getpwuid(os.geteuid())[5]
    globus_dir = os.path.expanduser('~/.globus')
    cert_dir = globus_dir
    server_cert = cert_dir + '/usercert.pem'
    server_key = cert_dir + '/userkey.pem'
    passwd = ''
    MiGServer = 'https://mig-1.imada.sdu.dk'
    port = '8092'

    if len(sys.argv) > 1:
        passwd = sys.argv[1]

    data = StringIO.StringIO()

    # Init cURL (not strictly necessary, but for symmetry with cleanup)

    pycurl.global_init(pycurl.GLOBAL_SSL)
    print 'cURL:\t\t', pycurl.version
    curl = pycurl.Curl()
    curl.setopt(pycurl.HTTPHEADER, ['User-Agent: MiG HTTP GET'])
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.URL, MiGServer + ':' + port + '/' + url)
    curl.setopt(pycurl.WRITEFUNCTION, data.write)
    curl.setopt(pycurl.NOSIGNAL, 1)

    # Uncomment to get verbose cURL output including SSL negotiation

    curl.setopt(curl.VERBOSE, 1)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)

    # curl.setopt(curl.PORT, port)

    curl.setopt(curl.SSLCERT, server_cert)
    curl.setopt(curl.SSLKEY, server_key)
    if passwd:
        curl.setopt(curl.SSLKEYPASSWD, passwd)

    # Path to CA certificates (NorduGRID default certificate path)

    curl.setopt(curl.CAPATH, '/etc/grid-security/certificates')

    # TODO: Should not be necessary but mig-1 host cert has wrong subject (vcr)

    curl.setopt(curl.SSL_VERIFYHOST, 1)

    # Uncomment if server identity can't be verified from local hostcert or CA cert

    curl.setopt(curl.SSL_VERIFYPEER, 0)

    print 'fetching:\t', url
    print 'cert:\t\t', server_cert
    print 'key:\t\t', server_key
    print 'passwd:\t\t', passwd

    # Clean up after cURL

    try:
        curl.perform()
    except pycurl.error, e:
        print 'cURL command failed!:'

        # error is a (errorcode, errormsg) tuple

        print e[1]
        return False

    status = curl.getinfo(pycurl.HTTP_CODE)
    print 'HTTP code:\t', status

    curl.close()
    pycurl.global_cleanup()

    if status == http_success:
        print '--- MiG files ---'
        print data.getvalue()
        print '--- Done ---'
        ret = True
    else:
        print 'Server returned HTTP code %d, expected %d' % (status,
                http_success)
        ret = 1

        data.close()

        return True


# end GetFile


def PutFile():
    srcdir = '.'
    filename = 'testfile'
    protocol = 'https'
    host = 'mig-1.imada.sdu.dk'
    port = ''

    filepath = srcdir + '/' + filename
    try:
        inputfile = open(filepath, 'rb')
    except:
        print 'Error: Failed to open %s for reading!' % filepath
        return (False, 'Invalid filename!')

    # Set size of file to be uploaded.

    size = os.path.getsize(filepath)

    if port:
        url = '%s://%s:%s/%s' % (protocol, host, port, filename)
    else:
        url = '%s://%s/%s' % (protocol, host, filename)

    # TODO: change to 'real' server certs
    # Just using default NorduGRID certificates for now

    os.environ['HOME'] = pwd.getpwuid(os.geteuid())[5]
    globus_dir = os.path.expanduser('~/.globus')
    cert_dir = globus_dir
    server_cert = cert_dir + '/usercert.pem'
    server_key = cert_dir + '/userkey.pem'
    passwd_file = 'cert_pass'

    passwd = ''
    try:
        pw_file = open(passwd_file, 'r')
        passwd = pw_file.readline().strip()
        pw_file.close()
    except:
        print 'Failed to read password from file!'
        return ''

    # Store output in memory

    output = StringIO.StringIO()

    # Init cURL (not strictly necessary, but for symmetry with cleanup)

    pycurl.global_init(pycurl.GLOBAL_SSL)

    curl = pycurl.Curl()
    curl.setopt(pycurl.HTTPHEADER, ['User-Agent: MiG HTTP PUT'])
    curl.setopt(pycurl.PUT, 1)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEFUNCTION, output.write)
    curl.setopt(pycurl.NOSIGNAL, 1)

    # Uncomment to get verbose cURL output including SSL negotiation

    curl.setopt(curl.VERBOSE, 1)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)

    # curl.setopt(curl.PORT, port)

    curl.setopt(pycurl.INFILE, inputfile)
    curl.setopt(pycurl.INFILESIZE, size)

    if protocol == 'https':
        curl.setopt(curl.SSLCERT, server_cert)
        curl.setopt(curl.SSLKEY, server_key)
        if passwd:
            curl.setopt(curl.SSLKEYPASSWD, passwd)

        # Path to CA certificates (NorduGRID default certificate path)

        curl.setopt(curl.CAPATH, '/etc/grid-security/certificates')

        # TODO: Should not be necessary but mig-1 host cert has wrong subject (vcr)

        curl.setopt(curl.SSL_VERIFYHOST, 1)

        # Uncomment if server identity can't be verified from local hostcert or CA cert

        curl.setopt(curl.SSL_VERIFYPEER, 0)

    # TODO: uncomment the following to actually execute upload

    try:
        curl.perform()
    except pycurl.error, e:

        # pycurl.error is an (errorcode, errormsg) tuple

        print 'Error: cURL command failed! %s' % e[1]
        return (404, 'Error!')

    status = curl.getinfo(pycurl.HTTP_CODE)

    # print "HTTP code:\t", status

    # Clean up after cURL

    curl.close()
    pycurl.global_cleanup()

    if status == http_success:
        print 'PUT request succeeded'

        # Go to start of buffer

        output.seek(0)
        msg = output.readlines()
        print msg
    else:
        print 'Warning: Server returned HTTP code %d, expected %d'\
             % (status, http_success)

    inputfile.close()
    output.close()

    # TODO: real curl PUT request
    # TMP!

    server_status = (200, 'Success')

    return server_status


# end PutFile

GetFile()

PutFile()

sys.exit(0)
