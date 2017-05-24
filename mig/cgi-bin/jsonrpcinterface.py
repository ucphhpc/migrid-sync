#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jsonrpcinterface - Provides the entire JSONRPC interface over CGI
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

"""JSONRPC interface to expose all XGI methods through platform-independent
JSON Remote Procedure Calls.

Requires the jsonrpclib module from https://pypi.python.org/pypi/jsonrpclib
to be installed. That is easily done with e.g.
pip install jsonrpclib
or
apt install python-jsonrpclib
or
yum install python-jsonrpclib
depending on the platform.
"""

from jsonrpclib.SimpleJSONRPCServer import CGIJSONRPCRequestHandler

# NOTE: Pull as much as possible from xmlrpcinterface to avoid redundant code
from xmlrpcinterface import MiGCGIXMLRPCRequestHandler, expose_functions


class MiGCGIJSONRPCRequestHandler(CGIJSONRPCRequestHandler,
                                  MiGCGIXMLRPCRequestHandler):
    """Override default request handler to pull doc from our backend modules.

    NOTE: Inherit first from JSONRPC and then from XMLRPC handler to get
    otherwise missing handle_request method.
    """

    system_methodSignature = MiGCGIXMLRPCRequestHandler.system_methodSignature
    system_methodHelp = MiGCGIXMLRPCRequestHandler.system_methodHelp


def serverMethodSignatures(server):
    """List all methods as well as signatures"""
    methods = CGIJSONRPCRequestHandler.system_listMethods(server)
    methods_and_signatures = [(method, server.system_methodSignature(method)) \
                              for method in methods]
    return methods_and_signatures


if '__main__' == __name__:
    server = MiGCGIJSONRPCRequestHandler()

    def AllMethodSignatures(): return serverMethodSignatures(server)
    server.register_function(AllMethodSignatures)

    for func_impl in expose_functions:
        server.register_function(func_impl)

    server.register_introspection_functions()
    server.handle_request()
