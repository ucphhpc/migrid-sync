#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# tlsserver - Shared functions for all SSL/TLS-secured servers
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""Common HTTPS/WebDAVS/FTPS server functions for e.g. SSL/TLS setup with
strong security settings.
"""

from __future__ import absolute_import

import ssl
import sys

from mig.shared.defaults import keyword_auto, STRONG_TLS_CIPHERS, \
    STRONG_TLS_LEGACY_CURVES


def hardened_ssl_context(configuration, keyfile, certfile, dhparamsfile=None,
                         ciphers=keyword_auto, curve_priority=keyword_auto,
                         allow_pre_tlsv13=True, allow_renegotiation=False,
                         ):
    """Build and return a hardened native SSL context to apply to a socket"""
    _logger = configuration.logger
    # NOTE: auto select best ciphers and curves unless specificly requested
    if ciphers is keyword_auto:
        _logger.debug("Auto select strong ciphers")
        ciphers = STRONG_TLS_CIPHERS
    if curve_priority is keyword_auto:
        # TODO: switch to STRONG_TLS_CURVES once Python gains support (3.15+)
        _logger.debug("Auto select strong legacy TLS curves without PQC")
        curve_priority = STRONG_TLS_LEGACY_CURVES
    _logger.info("enforcing strong SSL/TLS connections")
    _logger.debug("using SSL/TLS ciphers: %s" % ciphers)
    _logger.debug("using SSL/TLS curves: %s" % curve_priority)
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_ctx.load_cert_chain(certfile, keyfile)
    ssl_options = 0
    # NOTE: Override a number of weak and insecure legacy configurations
    #       Please keep updated based on e.g. Mozilla server recommendations:
    #       https://wiki.mozilla.org/Security/Server_Side_TLS
    ssl_options |= getattr(ssl, 'OP_NO_SSLv2', 0x1000000)
    ssl_options |= getattr(ssl, 'OP_NO_SSLv3', 0x2000000)
    ssl_options |= getattr(ssl, 'OP_NO_TLSv1', 0x4000000)
    ssl_options |= getattr(ssl, 'OP_NO_TLSv1_1', 0x10000000)
    # NOTE: refuse slightly dated TLS 1.2 protocol unless allow_pre_tlsv13
    if not allow_pre_tlsv13:
        if getattr(ssl, 'HAS_TLSv1_3', False):
            ssl_options |= getattr(ssl, 'OP_NO_TLSv1_2', 0x8000000)
            ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        else:
            _logger.warning("won't disable TLS 1.2 without TLS 1.3 support")
    # NOTE: refuse client TLS renegotiation unless allow_renegotiation
    if not allow_renegotiation:
        ssl_options |= getattr(ssl, 'OP_NO_RENEGOTIATION', 0x40000000)
    # NOTE: recommended hardening against various potential weaknesses
    ssl_options |= getattr(ssl, 'OP_NO_COMPRESSION', 0x20000)
    ssl_options |= getattr(ssl, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000)
    ssl_options |= getattr(ssl, 'OP_SINGLE_ECDH_USE', 0x80000)
    ssl_options |= getattr(ssl, 'OP_SINGLE_DH_USE', 0x100000)
    if sys.version_info[:2] >= (3, 7) and ssl_ctx:
        _logger.info("enforcing strong SSL/TLS options")
        _logger.debug("SSL/TLS options: %s" % ssl_options)
        ssl_ctx.options |= ssl_options
    else:
        _logger.info("can't enforce strong SSL/TLS options")
        _logger.warning("Upgrade to at least python 3.7+ for best security")

    pfs_available = False
    if dhparamsfile:
        try:
            ssl_ctx.load_dh_params(dhparamsfile)
            pfs_available = True
        except Exception:
            _logger.warning("Could not load optional dhparams from %s" %
                            dhparamsfile)
            _logger.info("""You can create a suitable dhparams file with:
openssl dhparam 2048 -out %s""" % dhparamsfile)

    # We must explicitly set curve here to actually enable ciphers
    # using them. They can provide Perfect Forward Secrecy.
    # http://stackoverflow.com/questions/32094145/python-paste-ssl-server-with-tlsv1-2-and-forward-secrecy#32101078
    # NOTE: PQC curves / KEMs like x25519mlkem768 are NOT supported here
    # TODO: use ssl_ctx.set_groups(curves) for PQC once Python 3.15+ lands
    activated_curve = None
    if curve_priority:
        for curve_name in curve_priority.split(':'):
            try:
                _logger.debug("Blindly trying elliptic curve %s" % curve_name)
                ssl_ctx.set_ecdh_curve(curve_name)
                activated_curve = curve_name
                pfs_available = True
                break
            except Exception as exc:
                _logger.warning("Couldn't init elliptic curve %s: %s" %
                                (curve_name, exc))

    if not activated_curve:
        _logger.info("""You need a modern openssl built with elliptic
curves to take advantage of this optional improved security feature""")

    if not pfs_available:
        _logger.warning("""No Perfect Forward Secrecy with neither 
dhparams nor elliptic curves available.""")

    ssl_ctx.set_ciphers(ciphers)
    return ssl_ctx


def hardened_openssl_context(configuration, OpenSSL, keyfile, certfile,
                             cacertfile=None, dhparamsfile=None,
                             ciphers=keyword_auto, curve_priority=keyword_auto,
                             allow_pre_tlsv13=True, allow_renegotiation=False,
                             ):
    """Build and return a hardened OpenSSL context to apply to a socket"""
    _logger = configuration.logger
    # NOTE: auto select best ciphers and curves unless specificly requested
    if ciphers is keyword_auto:
        _logger.debug("Auto select strong ciphers")
        ciphers = STRONG_TLS_CIPHERS
    if curve_priority is keyword_auto:
        # TODO: switch to STRONG_TLS_CURVES once PyOpenSSL gains support
        _logger.debug("Auto select strong legacy TLS curves without PQC")
        curve_priority = STRONG_TLS_LEGACY_CURVES
    SSL, crypto = OpenSSL.SSL, OpenSSL.crypto
    _logger.info("enforcing strong SSL/TLS connections")
    _logger.debug("using SSL/TLS ciphers: %s" % ciphers)
    _logger.debug("using SSL/TLS curves: %s" % curve_priority)
    ssl_ctx = SSL.Context(SSL.TLS_SERVER_METHOD)
    ssl_ctx.set_min_proto_version(SSL.TLS1_2_VERSION)
    # Mimic native ssl exposure of options
    ssl_ctx._minimum_version = SSL.TLS1_2_VERSION
    ssl_ctx.use_certificate_chain_file(certfile)
    ssl_ctx.use_privatekey_file(keyfile)
    if cacertfile:
        ssl_ctx.load_verify_locations(cacertfile)

    ssl_options = 0
    # NOTE: Override a number of weak and insecure legacy configurations
    #       Please keep updated based on e.g. Mozilla server recommendations:
    #       https://wiki.mozilla.org/Security/Server_Side_TLS
    ssl_options |= getattr(SSL, 'OP_NO_SSLv2', 0x1000000)
    ssl_options |= getattr(SSL, 'OP_NO_SSLv3', 0x2000000)
    ssl_options |= getattr(SSL, 'OP_NO_TLSv1', 0x4000000)
    ssl_options |= getattr(SSL, 'OP_NO_TLSv1_1', 0x10000000)
    # NOTE: refuse slightly dated TLS 1.2 protocol unless allow_pre_tlsv13
    if not allow_pre_tlsv13:
        # IMPORTANT: OpenSSL doesn't have TLSv1.3 support marker at the moment,
        #            so fall back to checking if native ssl does.
        if getattr(SSL, 'HAS_TLSv1_3', False) or \
                getattr(ssl, 'HAS_TLSv1_3', False):
            ssl_options |= getattr(SSL, 'OP_NO_TLSv1_2', 0x8000000)
            ssl_ctx.set_min_proto_version(SSL.TLS1_3_VERSION)
            # Mimic native ssl exposure of options
            ssl_ctx._minimum_version = SSL.TLS1_3_VERSION
        else:
            _logger.warning("won't disable TLS 1.2 without TLS 1.3 support")
    # NOTE: refuse client TLS renegotiation unless allow_renegotiation
    if not allow_renegotiation:
        ssl_options |= getattr(SSL, 'OP_NO_RENEGOTIATION', 0x40000000)
    # NOTE: recommended hardening against various potential weaknesses
    ssl_options |= getattr(SSL, 'OP_NO_COMPRESSION', 0x20000)
    ssl_options |= getattr(SSL, 'OP_CIPHER_SERVER_PREFERENCE', 0x400000)
    ssl_options |= getattr(SSL, 'OP_SINGLE_ECDH_USE', 0x80000)
    ssl_options |= getattr(SSL, 'OP_SINGLE_DH_USE', 0x100000)
    if sys.version_info[:2] >= (3, 7) and ssl_ctx:
        _logger.info("enforcing strong SSL/TLS options")
        _logger.debug("SSL/TLS options: %s" % ssl_options)
        ssl_ctx.set_options(ssl_options)
        # Mimic native ssl exposure of options
        ssl_ctx._options = ssl_options
    else:
        _logger.info("can't enforce strong SSL/TLS options")
        _logger.warning("Upgrade to at least python 3.7+ for best security")
        # Mimic native ssl exposure of options
        ssl_ctx._options = None

    pfs_available = False
    if dhparamsfile:
        try:
            ssl_ctx.load_tmp_dh(dhparamsfile)
            pfs_available = True
        except Exception:
            _logger.warning("Could not load optional dhparams from %s" %
                            dhparamsfile)
            _logger.info("""You can create a suitable dhparams file with:
openssl dhparam 2048 -out %s""" % dhparamsfile)

    # We must explicitly set curve here to actually enable ciphers
    # using them. They can provide Perfect Forward Secrecy.
    # http://stackoverflow.com/questions/32094145/python-paste-ssl-server-with-tlsv1-2-and-forward-secrecy#32101078
    # Some help for installing pyopenssl with EC support at
    # http://stackoverflow.com/questions/7340784/easy-install-pyopenssl-error/34048924#34048924
    # NOTE: PQC curves / KEMs like x25519mlkem768 are NOT supported here
    # TODO: mimic ssl_ctx.set_groups(curves) for PQC once Python 3.15+ lands
    activated_curve = None
    if curve_priority:
        try:
            # Returns a python set of curves to grab best one from
            available_curves = crypto.get_elliptic_curves()
            curve_map = dict([(i.name, i) for i in available_curves])
            for curve_name in curve_priority.split(':'):
                if curve_name in curve_map:
                    use_curve = curve_map[curve_name]
                    activated_curve = curve_name
                    break
            _logger.debug("Found elliptic curves %s and picked %s" %
                          (', '.join(list(curve_map)), use_curve.name))
            ssl_ctx.set_tmp_ecdh(use_curve)
            pfs_available = True
        except Exception as exc:
            _logger.warning("Couldn't init elliptic curve ciphers: %s" %
                            exc)

    if not activated_curve:
        _logger.info("""You need a modern (py)openssl built with elliptic
curves to take advantage of this optional improved security feature""")

    if not pfs_available:
        _logger.warning("""No Perfect Forward Secrecy with neither 
dhparams nor elliptic curves available.""")

    ssl_ctx.set_cipher_list(ciphers)

    # Mimic dumbed down version of native ssl get_ciphers method yielding specs
    ssl_ctx._ciphers = ':'.join([i for i in ciphers.split(':')
                                 if not i.startswith('!')])

    return ssl_ctx
