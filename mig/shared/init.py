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

""" Script initialization helper functions """

import os
import sys

def initialize_main_variables(op_title=True, op_header=True, op_menu=True):
    """Script initialization is identical for most scripts in 
    shared/functionalty. This function should be called in most cases.
    """
    from shared.conf import get_configuration_object
    configuration = get_configuration_object()
    logger = configuration.logger
    output_objects = []
    output_objects.append({"object_type":"start"})
    op_name = os.path.basename(sys.argv[0]).replace(".py", "")

    if op_title:
        title_object = {"object_type":"title",
                        "text":"MiG %s" % op_name,
                        "javascript":"", "bodyfunctions":""}
        if not op_menu:
            title_object["skipmenu"] = True
        output_objects.append(title_object)
    if op_header:
        output_objects.append({"object_type":"header",
        "text":"MiG %s" % op_name})
                                                                                              
    return configuration, logger, output_objects, op_name
