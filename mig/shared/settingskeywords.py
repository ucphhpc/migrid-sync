#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# settingskeywords - [insert a few words of module description on this line]
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

"""Keywords in the settings files"""

def get_keywords_dict():
    email = {
      "Description": "List of email addresses",
      "Example": "my@email.com, my_other@email.com", 
      "Type":"multiplestrings", 
      "Value":[],
      "Required":False
    }
    jabber = {
      "Description": "List of jabber addresses",
      "Example": "me@jabber.com, me2@jabber.com", 
      "Type":"multiplestrings", 
      "Value":[],
      "Required":False
    }
    msn = {
      "Description": "List of msn addresses",
      "Example": "me@hotmail.com, me2@hotmail.com", 
      "Type":"multiplestrings", 
      "Value":[],
      "Required":False
    }
    icq = {
    "Description": "List of icq numbers",
    "Example": "2364236, 2342342",
    "Type":"multiplestrings",
    "Value":[],
    "Required":False
    }
    aol = {
    "Description": "List of aol addresses",
    "Example": "me@aol.com, me2@aol.com",
    "Type":"multiplestrings",
    "Value":[],
    "Required":False
    }
    yahoo = {
    "Description": "List of msn addresses",
    "Example": "me@yahoo.com, me2@hotmail.com",
    "Type":"multiplestrings",
    "Value":[],
    "Required":False
    }
    language = {
    "Description": "Your prefered language",
    "Example": "English",
    "Type":"string",
    "Value":"English",
    "Required":False
    }

    # create the keywords in a single dictionary
    keywords_dict = { 
      "EMAIL":email,
      "JABBER":jabber,
      "MSN":msn,
      "ICQ":icq,
      "AOL":aol,
      "YAHOO":yahoo,
      "LANGUAGE":language
      
    }
    return keywords_dict
