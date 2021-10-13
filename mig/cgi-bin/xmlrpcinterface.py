#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcinterface - Provides the entire XMLRPC interface over CGI
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""XMLRPC interface to expose all XGI methods through platform-independent
XML Remote Procedure Calls.
"""
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from xmlrpc.server import CGIXMLRPCRequestHandler

from mig.shared.rpcfunctions import expose_functions, system_method_signature, \
       system_method_help


class MiGCGIXMLRPCRequestHandler(CGIXMLRPCRequestHandler):
    """Override default request handler to pull doc from our backend modules"""

    def system_methodSignature(self, method_name):
        """List method signatures"""

        return system_method_signature(method_name)

    def system_methodHelp(self, method_name):
        """List method usage"""

        return system_method_help(method_name)


def serverMethodSignatures(server):
    """List all methods as well as signatures"""
    methods = CGIXMLRPCRequestHandler.system_listMethods(server)
    methods_and_signatures = [(method, server.system_methodSignature(method)) \
                              for method in methods]
    return methods_and_signatures

if '__main__' == __name__:
    server = MiGCGIXMLRPCRequestHandler()

    def AllMethodSignatures(): return serverMethodSignatures(server)
    server.register_function(AllMethodSignatures)

    for func_impl in expose_functions:
        server.register_function(func_impl)

    server.register_introspection_functions()
    server.handle_request()
