#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# returnvalues - [insert a few words of module description on this line]
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

""" Returnvalues / exit code constants """

OK = (0, "OK")
    
ERROR = (1, "Client or system error")

# CLIENT ERRORS
CLIENT_ERROR = (100, "Client error")
NO_SUCH_JOB_ID = (101, "No job id..")
INVALID_ARGUMENT = (102, "Invalid argument")
NO_FILE_PATH = (103, "No file path provided")
AUTHENTICATION_ERROR = (104, "Authentication error")
FILE_NOT_FOUND = (105, "File not found")

# SYSTEM ERRORS
SYSTEM_ERROR = (200, "SYSTEM_ERROR")
USER_NOT_CREATED = (201, "USER_NOT_CREATED")
OUTPUT_VALIDATION_ERROR = (202, "The output the MiG server " + \
                        "has generated could not be validated")
