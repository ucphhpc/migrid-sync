#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# init - shared helpers to init functionality backends
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

"""Script initialization helper functions"""

import os
import sys

from shared.conf import get_configuration_object
from shared.settings import load_settings, load_widgets


def make_basic_entry(kind, values):
    """Create basic entry for output_objects"""
    entry =  {'object_type': kind}
    entry.update(values)
    return entry

def make_start_entry(headers=[]):
    """Create start entry for output_objects"""
    return make_basic_entry('start', {'headers': headers})

def make_title_entry(text, javascript='', bodyfunctions='',
                     skipmenu=False):
    """Create title entry for output_objects"""
    return make_basic_entry('title', {'text': text,
                                      'javascript': javascript,
                                      'bodyfunctions': bodyfunctions,
                                      'skipmenu': skipmenu,
                                      })

def make_header_entry(text):
    """Create header entry for output_objects"""
    return  make_basic_entry('header', {'text': text})

def find_entry(output_objects, kind):
    """Find entry in output_objects"""
    for entry in output_objects:
        if kind == entry['object_type']:
            return entry
    return None

def initialize_main_variables(client_id, op_title=True, op_header=True,
                              op_menu=True):
    """Script initialization is identical for most scripts in 
    shared/functionalty. This function should be called in most cases.
    """

    configuration = get_configuration_object()
    logger = configuration.logger
    output_objects = []
    start_entry = make_start_entry()
    output_objects.append(start_entry)
    op_name = os.path.basename(sys.argv[0]).replace('.py', '')

    if op_title:
        title_object = make_title_entry('%s' % op_name, skipmenu=(not op_menu))
        output_objects.append(title_object)
    if op_header:
        header_object = make_header_entry('%s' % op_name)
        output_objects.append(header_object)
    if client_id:
        # add the user-defined menu and widgets (if possible)
        title = find_entry(output_objects, 'title')
        if title:
            settings = load_settings(client_id, configuration)
            if settings:
                base_menu = settings.get('SITE_BASE_MENU', 'default')
                if not base_menu in configuration.site_base_menu:
                    base_menu = 'default'
                if base_menu == 'simple' and configuration.site_simple_menu:
                    title['base_menu'] = configuration.site_simple_menu
                elif base_menu == 'advanced' and configuration.site_advanced_menu:
                    title['base_menu'] = configuration.site_advanced_menu
                else:
                    title['base_menu'] = configuration.site_default_menu
                user_menu = settings.get('SITE_USER_MENU', None)
                if configuration.site_user_menu and user_menu:
                    title['user_menu'] = user_menu
            if configuration.site_script_deps:
                user_widgets = load_widgets(client_id, configuration)
                if user_widgets:
                    title['user_widgets'] = user_widgets

    return (configuration, logger, output_objects, op_name)


