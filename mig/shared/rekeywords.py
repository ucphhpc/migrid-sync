#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rekeywords - [insert a few words of module description on this line]
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

"""Keywords in the runtimeenvironment configuration files"""

def get_keywords_dict():
    rename = {
      "Description": "The name of the runtime environment.",
      "Example": "POVRAY-3.6", 
      "Type":"string", 
      "Value":"",
      "Required":True
    }
    description = {
      "Description": "The general description of this runtime environment.",
      "Example":"Support execution of POVRAY-3.6 jobs.",
      "Type":"string",
      "Value":"Not available",
      "Required":False
    }
    software = {
      "Description": "The software required to satisfy this runtime environment. Keywords: 'name', 'version', 'url', 'description', 'icon'",
      "Example": "['povray','3.6','http://www.povray.org/download/','This will make the most amazing povray ever seen.','povray.jpg']",
      "Type":"RE_software",
      "Value":[],
      "Required":False,
      "Sublevel": True,
      "Sublevel_required": ["name", "version", "url", "description", "icon"],
      "Sublevel_optional": []			
    }
    testprocedure = {
      "Description": "The procedure for testing the runtime environment, this must be on the mRSL format.",
      "Example":"::EXECUTE::\ncommand\n\n::VERIFYFILES::\nTODO: complete this example!\n",
      "Type":"testprocedure",
      "Value":[],
      "Required":False
    }
    verifystdout = {
      "Description": "The expected content of the .stdout file if a testprocedure job is executed. (empty lines not supported)",
      "Example":"::dido.imada.sdu.dk\n",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    verifystderr = {
      "Description": "The expected content of the .stderr file if a testprocedure job is executed. (empty lines not supported)",
      "Example":"::bash: notvalidcomnmand: command not found\n",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    verifystatus = {
      "Description": "The expected content of the .status file if a testprocedure job is executed. (empty lines not supported)",
      "Example":".* 0\n",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    environmentvariable = {
      "Description": "The environment variables which must be set on the resource for the runtime environment to work. name, example, description",
      "Example": "['name=POVRAY_HOME','example=/usr/local/povray/','description=Path to Povray home.']",
      "Type":"RE_environmentvariable",
      "Value":[],
      "Required":False,
      "Sublevel": True,
      "Sublevel_required": ["name", "example", "description"],
      "Sublevel_optional": []
    }
    # create the keywords in a single dictionary
    keywords_dict = { 
      "RENAME":rename,
      "DESCRIPTION":description,
      "SOFTWARE":software,
      "TESTPROCEDURE":testprocedure,
      "VERIFYSTDOUT":verifystdout,
      "VERIFYSTDERR":verifystderr,
      "VERIFYSTATUS":verifystatus,
      "ENVIRONMENTVARIABLE":environmentvariable
    }
    return keywords_dict
