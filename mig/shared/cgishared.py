#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# cgishared - cgi helper function
# Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

from __future__ import print_function
from __future__ import absolute_import

import os

from mig.shared.base import requested_backend
from mig.shared.cgioutput import CGIOutput
from mig.shared.conf import get_configuration_object
from mig.shared.httpsclient import extract_client_id


def cgiscript_header(header_info=None, content_type='text/html'):
    """Output header used by CGI scripts before any output"""

    # first header line

    print('Content-Type: %s' % content_type)

    if header_info:

        # header_info is '\n' seperated

        header_array = header_info.split('\n')
        for header_line in header_array:
            print(header_line)

    # blank line, end of headers

    print('')


def init_cgiscript_possibly_with_cert(print_header=True,
                                      content_type='text/html'):
    """Prepare for CGI script with optional client certificate. Only used from
    some of the cgi scripts still on the legacy-form like requestnewjob and
    put. I.e. scripts where certs are not required due to use of sessionid.
    """

    # Always rely on os.environ here since only called from cgi scripts
    environ = os.environ

    if print_header:
        cgiscript_header(content_type=content_type)

    configuration = get_configuration_object()
    logger = configuration.logger
    out = CGIOutput(logger)

    # get DN of user currently logged in

    client_id = extract_client_id(configuration, environ)
    if not client_id:
        logger.debug('(No client ID available in SSL session)')

    logger.info('script: %s cert: %s' %
                (requested_backend(environ, strip_ext=False), client_id))
    return (logger, configuration, client_id, out)
