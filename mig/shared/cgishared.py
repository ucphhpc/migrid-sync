#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cgishared - [insert a few words of module description on this line]
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

"""Common cgi functions"""

import os
import sys

from shared.cgioutput import CGIOutput
from shared.conf import get_configuration_object


def print_cgiscript_init(header_info=None, content_type='text/html'):

    # first header line

    print 'Content-Type: %s' % content_type

    if header_info:

        # header_info is '\n' seperated

        header_array = header_info.split('\n')
        for header_line in header_array:
            print header_line

    # blank line, end of headers

    print ''


def init_cgi_script_with_cert(print_header=True):
    if print_header:
        print_cgiscript_init()

    configuration = get_configuration_object()
    logger = configuration.logger
    o = CGIOutput(logger)

    # get CN of user currently logged in

    common_name = str(os.getenv('SSL_CLIENT_S_DN_CN'))
    if common_name == 'None':
        o.out('No client CN available from SSL session - not authenticated?!'
              )
        o.reply_and_exit(o.ERROR)

    cert_name_no_spaces = common_name.replace(' ', '_')
    o.internal('script: %s cert: %s' % (sys.argv[0],
               cert_name_no_spaces))
    return (logger, configuration, cert_name_no_spaces, o)


def init_cgiscript_possibly_with_cert(print_header=True,
        content_type='text/html'):

    # script used by 'requestnewjob' and 'put' where certs are not
    # required for resources with sessionid

    if print_header:
        print_cgiscript_init(content_type=content_type)

    configuration = get_configuration_object()
    logger = configuration.logger
    o = CGIOutput(logger)

    # get CN of user currently logged in

    common_name = str(os.getenv('SSL_CLIENT_S_DN_CN'))
    if common_name == 'None':
        o.internal('(No client CN available in SSL session)')

    cert_name_no_spaces = common_name.replace(' ', '_')
    o.internal('script: %s cert: %s' % (sys.argv[0],
               cert_name_no_spaces))

    return (logger, configuration, cert_name_no_spaces, o)


