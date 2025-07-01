#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xgicore - Xgi wrapper functions for functionality backends
# Copyright (C) 2003-2025  The MiG Project by the Science HPC Center at UCPH
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

"""Shared helpers for CGI+WSGI interface to functionality backends."""


def get_output_format(configuration, user_args, default_format='html'):
    """Get output_format from user_args."""
    return user_args.get('output_format', [default_format])[0]


def override_output_format(configuration, user_args, out_objs, out_format):
    """Override output_format if requested in start entry of output_objs."""
    if not [i for i in out_objs if i.get('object_type', None) == 'start' and
            i.get('override_format', False)]:
        return out_format
    return get_output_format(configuration, user_args)


def fill_start_headers(configuration, out_objs, out_format):
    """Make sure out_objs has start entry with basic content headers."""
    start_entry = None
    for entry in out_objs:
        if entry['object_type'] == 'start':
            start_entry = entry
    if not start_entry:
        start_entry = {'object_type': 'start', 'headers': []}
        out_objs.insert(0, start_entry)
    elif not start_entry.get('headers', False):
        start_entry['headers'] = []
    # Now fill headers to match output format
    default_content = 'text/html'
    if 'json' == out_format:
        default_content = 'application/json'
    elif 'file' == out_format:
        default_content = 'application/octet-stream'
    elif 'html' != out_format:
        default_content = 'text/plain'
    if not start_entry['headers']:
        start_entry['headers'].append(('Content-Type', default_content))
    return start_entry
