#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# valuecheck - [insert a few words of module description on this line]
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

# -*- coding: iso-8859-1 -*-

"""This module contains general functions for validating the
value of input.
"""

def lines_value_checker(value_string):
    """Value checker for the lines variables"""
    value = int(value_string)
    if value < 1 or value > 1000000:
        raise ValueError("lines: out of range")

def max_jobs_value_checker(value_string):
    """Value checker for the max_jobs variables"""
    value = int(value_string)
    if value < 1 or value > 1000000:
        raise ValueError("max_jobs: out of range")
