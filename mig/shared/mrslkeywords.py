#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# mrslkeywords - [insert a few words of module description on this line]
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

"""Keywords in the mRSL language"""

def get_keywords_dict(configuration):
    execute = {
      "Description": "One or more commands to execute",
      "Example": "uname -a\necho text >> file\nls", 
      "Type":"multiplestrings", 
      "Value":[],
      "Required":True
    }
    inputfiles = {
      "Description": "Files to be copied to the resource before job execution. Relative paths like plain file names are automatically taken from the user home on the MiG server. External sources are also allowed as long as they can be downloaded with the 'curl' client without user interaction. This means that HTTP, HTTPS, FTP, FTPS, SCP, SFTP, TFTP, DICT, TELNET or even LDAP are at least technically supported. External data sources obviously require the executing resource to have outbound network access to the data source. Thus HTTP and HTTPS are the most likely to generally work even on network restricted resources. Inputfiles may be specified as a single name per line or as lines of source and destination path separated by a space. In the single name format the file will be called the same on the destination as on the source.",
      "Example":"file\nanother_file another_file_renamed\n Copies file and another_file to the resource, but another_file is called another_file_renamed on the resource.\n\nsome_url some_file\n downloads the contents in some_url to a file called some_file on the resource.",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    outputfiles = {
      "Description": "Files to be copied from the resource after job execution. Relative paths like plain file names are automatically sent to the user home on the MiG server. External destinations are also allowed as long as they can be uploaded with the 'curl' client without user interaction. This means that HTTP, HTTPS, FTP, FTPS, SCP, SFTP, TFTP, DICT, TELNET or even LDAP are at least technically supported. External data destinations obviously require the executing resource to have outbound network access to the data destination. Thus HTTP or HTTPS are the most likely to be allowed even on network restricted resources. Please note however, that HTTP upload requires the destination HTTP server to support the PUT operation, which is not generally enabled on all servers. Outputfiles may be specified as a single name per line or as lines of source and destination path separated by a space. In the single name format the file will be called the same on the destination as on the source.",
      "Example":"file\nanother_file_renamed another_file\n Copies file and another_file_renamed to the MiG server, but another_file_renamed is renamed to another_file.\n\nsome_file some_url\n uploads some_file on the resource to some_url.",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    verifyfiles = {
      "Description": "Files to verify job execution results and output against",
      "Example":"EXPECTED.status\nEXPECTED.stdout\nEXPECTED.stderr\n Compares JOB_ID.status from the job against the file called EXPECTED.status from the MiG home directory and similarly for JOB_ID.stdout and JOB_ID.stderr. For each supplied verify file, EXPECTED.X, the corresponding JOB_ID.X file will be verified line by line using regular expression matching. If any verification fails, the VERIFIED field of the job will be set to FAILURE with the reason appended. If all verification succeeds the VERIFIED field will be set to SUCCESS with a list of the checks appended. If VERIFYFILES is left unset the VERIFIED field will simply be set to NO. In all cases the VERIFIED field is shown as a part of the job status",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    executables = {
      "Description": "Exactly the same as INPUTFILES, but the files are made executable (chmod +x) after they are copied to the resource",
      "Example":"script\nMiGserverScript ResourceScript",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    cputime = {
      "Description": "The time required to execute the job. The time is specified in seconds",
      "Example":"60",
      "Type":"int",
      "Value":600,
      "Required":False
    }
    memory = {
      "Description": "Amount of memory required to execute the job. The amount is specified in megabytes ",
      "Example":"128",
      "Type":"int",
      "Value":1,
      "Required":False
    }
    disk = {
      "Description": "Amount of disk space required to execute the job. The amount is specified in gigabytes aand the default is zero.",
      "Example":"10",
      "Type":"int",
      "Value":0,
      "Required":False
    }
    runtimeenvironment = {
      "Description": "Software packages the job requires",
      "Example":"POVRAY3-6 (the job will only be executed on resources that have ..)",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    jobname = {
      "Description": "Name identifying the job",
      "Example":"JOB23",
      "Type":"string",
      "Value":"",
      "Required":False
    }
    notify = {
      "Description": "Email and/or Instant Messenger account to notify when the job is done. If you have configured your MiG settings you may leave the address part empty or set it to 'SETTINGS' to use the saved setting.",
      "Example":"myemail@mailserver.org\njabber: myaccount@jabberserver.org\nyahoo: \nmsn: SETTINGS",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    architecture = {
      "Description": "Cpu architecture",
      "Example":"Valid values: %s" % configuration.architectures,
      "Type":"string",
      "Value":"",
      "Required":False
    }
    project = {
      "Description": "Mark this job as part of a project. This makes is possible to get a total statistic for all jobs in a project.",
      "Example":"myprojectname",
      "Type":"string",
      "Value":"",
      "Required":False
    }
    environment = {
      "Description": "Sets the environments specified before job execution",
      "Example":"myenv=/home/user/dir",
      "Type":"multiplekeyvalues",
      "Value":[],
      "Required":False
    }
    cpucount = {
      "Description": "Number of CPU's the job requires on each node.",
      "Example":"4",
      "Type":"int",
      "Value":1,
      "Required":False
    }
    nodecount = {
      "Description": "Number of nodes.",
      "Example":"4",
      "Type":"int",
      "Value":1,
      "Required":False
    }
    sandbox = {
      "Description": "Specifies whether the job may run in a sandbox. If 0 it may not, if 1 it may.",
      "Example":"0",
      "Type":"int",
      "Value":0,
      "Required":False
    }
    jobtype = {
      "Description": "Specifies the type of a job: A job can be of type 'interactive', 'batch' or 'bulk'. Interactive jobs are executed on a resource but with the graphical display forwarded to the MiG display of the user. Batch jobs are executed in a headless mode and can not use graphical output. Bulk jobs are like batch jobs, but additionally allows concurrent execution of your other jobs on the same resource as long as the resource can provide the requested job resources (cpucpunt, nodecount, memory, disk). Set to 'interactive' for jobs that use a display, set to bulk for high throughput jobs and leave unset or set to batch for the rest. This particular MiG server supports the following jobtypes: %s" % ', '.join(configuration.jobtypes),
      "Example":"interactive",
      "Type":"string",
      "Value":'batch',
      "Required":False
    }
    maxprice = {
      "Description": "Maximum price to pay for the execution of the job. The economy is not yet enforced, so this is a proof of concept option only.",
      "Example":"40",
      "Type":"string",
      "Value":"0",
      "Required":False
    }
    vgrid = {
      "Description": "A prioritized list of the VGRIDs allowed to execute the job (Default value is Generic). During job submit the keyword ANY is replaced by a list of all the VGrids that you can access.",
      "Example":"dalton\nGeneric",
      "Type":"multiplestrings",
      "Value":[],
      "Required":False
    }
    platform = {
      "Description": "Specifies the platform architecture used for the execution of the job.",
      "Example":"ONE-CLICK",
      "Type":"string",
      "Value":"",
      "Required":False
    }

    # create the keywords in a single dictionary
    keywords_dict = { 
      "EXECUTE":execute, 
      "INPUTFILES":inputfiles, 
      "OUTPUTFILES":outputfiles, 
      "VERIFYFILES":verifyfiles, 
      "EXECUTABLES":executables,
      "CPUTIME":cputime,
      "MEMORY":memory,
      "DISK":disk,
      "RUNTIMEENVIRONMENT":runtimeenvironment,
      "JOBNAME":jobname,
      "NOTIFY":notify,
      "ARCHITECTURE":architecture,
      "PROJECT":project,
      "ENVIRONMENT":environment,
      "CPUCOUNT":cpucount,
      "NODECOUNT":nodecount,
      "SANDBOX":sandbox,
      "JOBTYPE":jobtype,
      "MAXPRICE":maxprice,
      "VGRID":vgrid,
      "PLATFORM":platform
    }
    return keywords_dict
