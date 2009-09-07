#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# init - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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


def make_basic_entry(kind, values):
    """Create basic entry for output_objects"""
    entry =  {'object_type': kind}
    entry.update(values)
    return entry

def make_start_entry(headers=[]):
    """Create start entry for output_objects"""
    return make_basic_entry('start', {'headers': headers})

def make_title_entry(text, javascript='', bodyfunctions='', skipmenu=False,
                     defaultcss='', usercss='', favicon='', logoimage='',
                     logotitle=''):
    """Create title entry for output_objects"""
    return make_basic_entry('title', {'text': text,
                                      'javascript': javascript,
                                      'bodyfunctions': bodyfunctions,
                                      'skipmenu': skipmenu,
                                      'defaultcss': defaultcss,
                                      'usercss': usercss,
                                      'favicon': favicon,
                                      'logoimage': logoimage,
                                      'logotitle': logotitle,
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

def initialize_main_variables(op_title=True, op_header=True,
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
        title_object = make_title_entry('%s' % op_name, skipmenu=(not op_menu),
                                        defaultcss=configuration.site_default_css,
                                        usercss=configuration.site_user_css,
                                        favicon=configuration.site_fav_icon,
                                        logoimage=configuration.site_logo_image,
                                        logotitle=configuration.site_logo_text)
        output_objects.append(title_object)
    if op_header:
        header_object = make_header_entry('%s' % op_name)
        output_objects.append(header_object)

    return (configuration, logger, output_objects, op_name)


