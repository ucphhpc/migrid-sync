#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# --- BEGIN_HEADER ---
#
# url - url helper functions
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""Url functions"""

from __future__ import absolute_import

try:
    from builtins import range
    from future import standard_library
    standard_library.install_aliases()
except Exception as exc:
    print("Could not init compatibility modules!")
    exit(1)

import ast
import base64
import os
import sys

# NOTE: moved to urllib.parse in python3 and are re-exposed with future.
#       Other modules should import helpers from here for consistency.
# TODO: handle the unicode returned by python3 and future versions!
#       Perhaps switch to suggested "easiest option" from
#       http://python-future.org/compatible_idioms.html#urllib-module
#       once we have unicode/bytecode mix-up sorted out.
if sys.version_info[0] >= 3:
    from urllib.parse import quote, unquote, urlencode, parse_qs, parse_qsl, \
        urlsplit, urlparse
    from urllib.request import urlopen, FancyURLopener
else:
    from urllib import quote, unquote, urlencode, urlopen, FancyURLopener
    from urlparse import parse_qs, parse_qsl, urlsplit, urlparse

try:
    from mig.shared.defaults import csrf_field
    from mig.shared.handlers import get_csrf_limit
    from mig.shared.pwhash import make_csrf_token, make_csrf_trust_token
except ImportError as ioe:
    print("Could not import mig modules!")
    exit(1)


def base32urlencode(
    configuration,
    url,
    query_dict=None,
    remove_padding=True,
):
    """Returns base32 urlencoded representation of
    *url* and *query_dict*
    NOTE: base32 uses the alpha-numeric alphabet in order to make the encoded url
          shared.functional.validate_input compliant
    NOTE: *use_padding=False* removes '=' in order to make the encoded url
          shared.functional.validate_input compliant
    NOTE: Look at base32urldecode for re-padding
    """

    src_url = url
    if query_dict is not None:
        src_url = '%s?%s' % (src_url, urlencode(query_dict))

    # base32 encode and remove padding '='
    # Receiver is expected to pad before decode

    result = base64.b32encode(src_url)

    if remove_padding:
        result = result.replace('=', '')

    return result


def base32urldecode(configuration, encoded_url,
                    strip_query_arguments=True):
    """Returns decoded url and query dict, if *strip_query_arguments* is True,
    then the query arguments are removed from returned url
    """

    # If padding was removed (see base32urlencode) then re-add before decoding:
    # https://tools.ietf.org/html/rfc3548 :
    # (1) the final quantum of encoding input is an integral multiple of 40
    # bits; here, the final unit of encoded output will be an integral
    # multiple of 8 characters with no "=" padding,

    padding = ''
    encoded_url_len = len(encoded_url)
    if encoded_url_len % 8 != 0:
        padlen = 8 - encoded_url_len % 8
        padding = ''.join('=' for i in range(padlen))
    decoded_url = base64.b32decode('%s%s' % (encoded_url, padding))
    if strip_query_arguments:
        result_url = decoded_url.split('?')[0]
    else:
        result_url = decoded_url
    query_dict = \
        dict(parse_qsl(urlsplit(decoded_url).query))

    # Regenerate query_dict value lists from their string representatives

    for (key, value) in query_dict.items():
        try:
            query_dict[key] = ast.literal_eval(value)
        except ValueError as exc:
            raise ValueError('Invalid formated input: %s -> %s, error: %s'
                             % (key, value, exc))

    return (result_url, query_dict)


def openid_autologout_url(
    configuration,
    openid_identity,
    client_id,
    return_url,
    return_query_dict=None,
):
    """Generates OpenID logout URL.
    OpenID logout consists of two steps:
    1) OpenID server: expire session
    2) OpenID server: redirect after session expire
    The OpenID server always returns to autologout.py which then redirects
    to *return_url*.
    """

    _logger = configuration.logger

    # Add CSRF trust token to query_dict, needed at autologout.py for URL and
    # query args validation

    if return_query_dict is None:
        csrf_query_dict = {}
    else:
        csrf_query_dict = return_query_dict.copy()

    csrf_limit = get_csrf_limit(configuration)
    trust_token = make_csrf_trust_token(configuration, 'get', return_url,
                                        csrf_query_dict, client_id,
                                        csrf_limit)
    csrf_query_dict[csrf_field] = ['%s' % trust_token]
    encoded_redirect_to = base32urlencode(configuration, return_url,
                                          csrf_query_dict)

    # OpenID server always returns to autologout.py which then redirects
    # to return_url

    oid_return_to = '%s/%s?redirect_to=%s' \
        % (return_url[:return_url.rfind('/')], 'autologout.py',
           encoded_redirect_to)

    oid_logout_url = \
        os.path.join(os.path.dirname(os.path.dirname(openid_identity)),
                     'logout?return_to=%s' % oid_return_to)

    return oid_logout_url


def openid_basic_logout_url(
    configuration,
    openid_identity,
    return_url,
):
    """Generates basic OpenID logout URL to expire session OpenID session
    then redirect to *return_url*.
    """

    _logger = configuration.logger

    # OpenID server always returns to autologout.py which then redirects
    # to return_url

    oid_logout_url = \
        os.path.join(os.path.dirname(os.path.dirname(openid_identity)),
                     'logout?return_to=%s' % return_url)
    _logger.debug("basic openid logout url: %s" % oid_logout_url)
    return oid_logout_url
