#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cgishared - cgi helper function
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

"""Common cgi functions"""

import sys

from shared.cgioutput import CGIOutput
from shared.conf import get_configuration_object
from shared.httpsclient import extract_client_id


def cgiscript_header(header_info=None, content_type='text/html'):
    """Output header used by CGI scripts before any output"""

    # first header line

    print 'Content-Type: %s' % content_type

    if header_info:

        # header_info is '\n' seperated

        header_array = header_info.split('\n')
        for header_line in header_array:
            print header_line

    # blank line, end of headers

    print ''


def init_cgi_script_with_cert(print_header=True, content_type='text/html'):
    """Prepare for CGI script with client certificate"""

    if print_header:
        cgiscript_header(content_type=content_type)

    configuration = get_configuration_object()
    logger = configuration.logger
    out = CGIOutput(logger)

    # get DN of user currently logged in

    client_id = extract_client_id(configuration)
    if not client_id:
        msg = 'No client ID available from SSL env - not authenticated!'
        logger.error(msg)
        out.out(msg)
        out.reply_and_exit(out.ERROR)

    logger.info('script: %s cert: %s' % (sys.argv[0], client_id))
    return (logger, configuration, client_id, out)


def init_cgiscript_possibly_with_cert(print_header=True,
                                      content_type='text/html'):
    """Prepare for CGI script with optional client certificate"""

    # script used by 'requestnewjob' and 'put' where certs are not
    # required for resources with sessionid

    if print_header:
        cgiscript_header(content_type=content_type)

    configuration = get_configuration_object()
    logger = configuration.logger
    out = CGIOutput(logger)

    # get DN of user currently logged in

    client_id = extract_client_id(configuration)
    if not client_id:
        logger.debug('(No client ID available in SSL session)')

    logger.info('script: %s cert: %s' % (sys.argv[0], client_id))
    return (logger, configuration, client_id, out)
