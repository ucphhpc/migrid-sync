#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# httpsserver - Shared functions for all HTTPS servers
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

"""Common HTTPS server functions for e.g. strict SSL/TLS setup"""

import ssl
import sys

# Mirror strong ciphers used in Apache
strong_ciphers = "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA"

def hardened_ssl_kwargs(logger):
    """Python 2.7 exposed new arguments to ssl.wrap_socket for allowing more
    fine grained control over the underlying SSL/TLS context creation. We use
    this helper to enable the tightest possible arguments we know for the
    given python version.
    """
    ssl_version = ssl.PROTOCOL_SSLv23

    # Use fine-grained wrap_socket ssl args if python is recent enough (2.7+)
    ssl_kwargs = {}
    if sys.version_info[:2] >= (2, 7):
        ssl_kwargs.update({"ciphers": strong_ciphers})
        logger.info("enforcing strong SSL/TLS connections")
        logger.debug("using SSL/TLS ciphers: %s" % strong_ciphers)
    else:
        logger.warning("Unable to enforce explicit strong TLS connections")
        logger.warning("Upgrade to python 2.7.9+ for maximum security")
    ssl_kwargs.update({"ssl_version": ssl_version})
    logger.debug("using SSL/TLS version: %s (default %s)" % \
                  (ssl_version, ssl.PROTOCOL_SSLv23))
    return ssl_kwargs

def harden_ssl_options(sock, logger, options=None):
    """Python 2.7 SSL/TLS wrapped sockets can be further hardened after
    the call to ssl.wrap_socket.
    We use this helper to tighten the context where possible. In practice that
    is a matter of disabling old SSL protocols and compression in addition to
    enforcing server cipher order precedence in line with testssl.sh
    recommendations.
    """

    # Futher harden connection options if python is recent enough (2.7+)
    if options is None:
        options = 0
        options |= getattr(ssl, 'OP_NO_SSLv2', 0x1000000)
        options |= getattr(ssl, 'OP_NO_SSLv3', 0x2000000)
        options |= getattr(ssl, 'OP_NO_COMPRESSION', 0x20000)
        options |= getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000)
        ssl_ctx = getattr(sock, 'context', None)
    if sys.version_info[:2] >= (2, 7) and ssl_ctx:
        logger.info("enforcing strong SSL/TLS options")
        logger.debug("SSL/TLS options: %s" % options)
        ssl_ctx.options |= options
    else:
        logger.info("can't enforce strong SSL/TLS options")
        logger.warning("Upgrade to python 2.7.9+ for maximum security")
    return sock
