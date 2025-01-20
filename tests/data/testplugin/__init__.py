# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# tests/data/testplugin - demonstration of a route plugin for use by tests
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


"""
Demonstration of a route plugin for use in tests.
"""


def tests_data__GET_testpluginendpoint(request_info, data):
    """
    Request handler: GET /testpluginendpoint
    """

    greeting = request_info._arg_string("greeting", "<none>")

    return {
        "template_args": {
            "greeting": greeting,
        },
        "template_name": "test_something",
    }


def tests_data__GET_testpluginendpoint_missing_template(request_info, data):
    """
    Request handler: GET /testpluginendpoint_missing_template
    """

    return {
        "template_args": {},
        "template_name": "test_nonexistent",
    }


TEMPLATE_PACKAGES = [
    "testplugin",
    "testplugin.inner",
]


TEMPLATE_ROUTES = {
    "GET /testpluginendpoint": {
        "generate_args": tests_data__GET_testpluginendpoint,
    },
    "GET /testpluginendpoint_missing_template": {
        "generate_args": tests_data__GET_testpluginendpoint_missing_template,
    },
}
