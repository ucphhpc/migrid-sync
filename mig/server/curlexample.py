#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# curlexample - [insert a few words of module description on this line]
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

from __future__ import print_function
import StringIO
import os
import sys
import pwd

import pycurl

server_section = 'serverstatus'
http_success = 200


def get_data(
    protocol,
    host,
    port,
    rel_path,
    cert,
    key,
    ca_dir,
    ca_file,
    passphrase_file='',
    ):

    if port:
        url = '%s://%s:%s/%s' % (protocol, host, port, rel_path)
    else:
        url = '%s://%s/%s' % (protocol, host, rel_path)

    passphrase = ''
    if passphrase_file:
        try:
            pp_file = open(passphrase_file, 'r')
            passphrase = pp_file.readline().strip()
            pp_file.close()
        except:
            print('Failed to read passprase from %s', passphrase_file)
            return None

    # Store output in memory

    output = StringIO.StringIO()

    # Init cURL (not strictly necessary, but for symmetry with cleanup)

    pycurl.global_init(pycurl.GLOBAL_SSL)

    curl = pycurl.Curl()
    curl.setopt(pycurl.HTTPHEADER, ['User-Agent: MiG HTTP GET'])
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEFUNCTION, output.write)
    curl.setopt(pycurl.NOSIGNAL, 1)

    # Uncomment to get verbose cURL output including SSL negotiation

    curl.setopt(curl.VERBOSE, 1)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)
    if protocol == 'https':
        curl.setopt(curl.SSLCERT, cert)
        curl.setopt(curl.SSLKEY, key)
        if passphrase:
            curl.setopt(curl.SSLKEYPASSWD, passphrase)

        # Path to CA certificates

        if ca_dir:
            curl.setopt(curl.CAPATH, ca_dir)
        elif ca_file:

            # We use our own demo CA file specified in the configuration for now

            curl.setopt(curl.CAINFO, ca_file)

        # Workaround for broken host certificates:
        # ###################################################
        # Do not use this, but fix host cert + CA instead! #
        # ###################################################
        # VERIFYHOST should be 2 (default) unless remote cert can not be
        # verified using CA cert.
        # curl.setopt(curl.SSL_VERIFYHOST,1)
        # Similarly VERIFYPEER will then probably need to be set to 0
        # curl.setopt(curl.SSL_VERIFYPEER,0)

        # TODO: Should not be necessary but mig-1 host cert has wrong subject (vcr)

        curl.setopt(curl.SSL_VERIFYHOST, 1)

        # Uncomment if server identity can't be verified from local hostcert or CA cert

        curl.setopt(curl.SSL_VERIFYPEER, 0)

    try:
        print('get_data: fetch %s', url)
        curl.perform()
    except pycurl.error as e:

        # pycurl.error is an (errorcode, errormsg) tuple

        print('cURL command failed! %s', e[1])
        return ''

    http_status = curl.getinfo(pycurl.HTTP_CODE)

    # Clean up after cURL

    curl.close()
    pycurl.global_cleanup()

    server_status = ''

    if http_status == http_success:

        # Go to start of buffer

        output.seek(0)
        try:
            server_status = output.readlines()
        except:
            print('Failed to parse server status')
            return None
    else:
        print('Server returned HTTP code %d, expected %d', http_status, \
            http_success)
        return None

    output.close()

    return server_status


# end get_data

# Main

home = os.path.expanduser('~')
response = get_data(
    'https',
    'mig-1.imada.sdu.dk',
    '',
    '/cgi-bin/allstatus.py?with_html=false',
    home + '/.globus/usercert.pem',
    home + '/.globus/userkey.pem',
    '',
    home + '/.MiG/cacert.pem',
    home + '/.MiG/pp.txt',
    )

print(response)

sys.exit(0)
