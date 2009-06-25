#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resource_edit_help - [insert a few words of module description on this line]
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

# Minimum Intrusion Grid
# Martin Rehr martin@rehr.dk August 2005

import cgi
import cgitb
cgitb.enable()
import os
import string
import pickle
import sys
import time

import shared.resconfkeywords as resconfkeywords
from shared.cgishared import init_cgi_script_with_cert
from shared.html import get_cgi_html_header

(logger, configuration, client_id, o) = \
    init_cgi_script_with_cert()
resource_keywords = resconfkeywords.get_resource_keywords(configuration)
exenode_keywords = resconfkeywords.get_exenode_keywords(configuration)

print get_cgi_html_header('MiG Resource administration help',
                          'Welcome to the MiG resource administration help.'
                          )

print """		<B><A NAME="hosturl">Host FQDN:</A></B><BR>"""
print resource_keywords['HOSTURL']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['HOSTURL']['Example']
print """		<BR><BR>
                        <B><A NAME="hostidentifier">Host identifier:</A></B><BR>"""
print resource_keywords['HOSTIDENTIFIER']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['HOSTIDENTIFIER']['Example']
print """		<BR><BR>
			<B><A NAME="publicname">Public name:</A></B><BR>"""
print resource_keywords['PUBLICNAME']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['PUBLICNAME']['Example']
print """		<BR><BR>
			<B><A NAME="mig_user">MiG user:</A></B><BR>"""
print resource_keywords['MIGUSER']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['MIGUSER']['Example']
print """		<BR><BR>
			<B><A NAME="mig_home">MiG home:</A></B><BR>"""
print resource_keywords['RESOURCEHOME']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['RESOURCEHOME']['Example']
print """		<BR><BR>
                        <B><A NAME="hostip">Host IP:</A></B><BR>"""

# print resource_keywords["HOSTIP"]["Description"]
# print """........<BR><BR>Example:&nbsp;"""
# print resource_keywords["HOSTIP"]["Example"]
# print """........<BR><BR>

print """               This is the IP address which corresponds to the 'Host FQDN'.
                        <BR><BR>
			<B><A NAME="sshport">Ssh port:</A></B><BR>"""
print resource_keywords['SSHPORT']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['SSHPORT']['Example']
print """		<BR><BR>
			<B><A NAME="sshmultiplex">Ssh multiplex:</A></B><BR>"""
print resource_keywords['SSHMULTIPLEX']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['SSHMULTIPLEX']['Example']
print """		<BR><BR>
			<B><A NAME="hostkey">Host key:</A></B><BR>"""
print resource_keywords['HOSTKEY']['Description']
print """		<BR><BR>Example:&nbsp;"""
if -1 != resource_keywords['HOSTKEY']['Example'].find('ssh-rsa'):
    print resource_keywords['HOSTKEY']['Example'].replace('ssh-rsa', '')
else:
    print resource_keywords['HOSTKEY']['Example']

print """		<BR><BR>
			<B><A NAME="frontend_node">Frontend node:</A></B><BR>"""
print resource_keywords['FRONTENDNODE']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['FRONTENDNODE']['Example']
print """		<BR><BR>
			<B><A NAME="max_download_bandwidth">Max download bandwidth:</A></B><BR>"""
print resource_keywords['MAXDOWNLOADBANDWIDTH']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['MAXDOWNLOADBANDWIDTH']['Example']
print """		<BR><BR>
			<B><A NAME="max_upload_bandwidth">Max upload bandwidth:</A></B><BR>"""
print resource_keywords['MAXUPLOADBANDWIDTH']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['MAXUPLOADBANDWIDTH']['Example']
print """		<BR><BR>
			<B><A NAME="lrms_type">LRMS type:</A></B><BR>"""
print resource_keywords['LRMSTYPE']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['LRMSTYPE']['Example']
print """		<BR><BR>
			<B><A NAME="execution_delay_command">LRMS execution delay command:</A></B><BR>"""
print resource_keywords['LRMSDELAYCOMMAND']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['LRMSDELAYCOMMAND']['Example']
print """		<BR><BR>
			<B><A NAME="submit_job_command">LRMS submit job command:</A></B><BR>"""
print resource_keywords['LRMSSUBMITCOMMAND']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['LRMSSUBMITCOMMAND']['Example']
print """		<BR><BR>
			<B><A NAME="remove_job_command">LRMS remove job command:</A></B><BR>"""
print resource_keywords['LRMSREMOVECOMMAND']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['LRMSREMOVECOMMAND']['Example']
print """		<BR><BR>
			<B><A NAME="query_done_command">LRMS query done command:</A></B><BR>"""
print resource_keywords['LRMSDONECOMMAND']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['LRMSDONECOMMAND']['Example']

# Not all exenode fields map directly to documentation in resconfkeywords

print """		<BR><BR>
			<B><A NAME="execution_nodes">Execution node(s):</A></B><BR>"""
print exenode_keywords['NAME']['Description']
print """		<BR>"""
print """		This fields configures all the nodes to execute MiG jobs in one.<BR>
			It is possible to specify several execution nodes by seperating them with ';'<BR>
			and it's possible to denote ranges of execution nodes by using '->'.<BR><BR>
			Example:&nbsp; n0->n8 ; n10 ; n12->n24
			<BR><BR>
			Specifies the nodes n0 to n8, n10 and n12 to n24.
			<BR><BR>
			Please note that the following node count field specifies the number of actual physical hosts associated with each of these MiG execution nodes. In case of a one-to-one mapping between MiG execution nodes and actual nodes, the it should just be set to 1. Only if each MiG execution node gives access to multiple nodes e.g. in a cluster or batch system, should it be set higher.
			<BR><BR>
			<B><A NAME="nodecount">Node count:</A></B><BR>"""
print exenode_keywords['NODECOUNT']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['NODECOUNT']['Example']
print """		<BR><BR>
			<B><A NAME="cpucount">Cpu count:</A></B><BR>"""
print resource_keywords['CPUCOUNT']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['CPUCOUNT']['Example']
print """		<BR><BR>
			<B><A NAME="cputime">Cpu time:</A></B><BR>"""
print exenode_keywords['CPUTIME']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['CPUTIME']['Example']
print """		<BR><BR>
			<B><A NAME="memory">Memory (MB):</A></B><BR>"""
print resource_keywords['MEMORY']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['MEMORY']['Example']
print """		<BR><BR>
			<B><A NAME="disk">Disk (GB):</A></B><BR>"""
print resource_keywords['DISK']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['DISK']['Example']
print """		<BR><BR>
			<B><A NAME="architecture">Architecture:</A></B><BR>"""
print resource_keywords['ARCHITECTURE']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['ARCHITECTURE']['Example']
print """		<BR><BR>
			<B><A NAME="scriptlanguage">Script language:</A></B><BR>"""
print resource_keywords['SCRIPTLANGUAGE']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['SCRIPTLANGUAGE']['Example']
print """		<BR><BR>
			<B><A NAME="jobtype">Job type:</A></B><BR>"""
print resource_keywords['JOBTYPE']['Description']
print """		<BR><BR>Example:&nbsp;"""
print resource_keywords['JOBTYPE']['Example']
print """		<BR><BR>
			<B><A NAME="runtimeenvironment">Runtime environment:</A></B><BR>"""
print resource_keywords['RUNTIMEENVIRONMENT']['Description']
print """		<BR><BR>Example:<BR>"""

runtimeenvironment_example = resource_keywords['RUNTIMEENVIRONMENT'
        ]['Example']
if -1 != runtimeenvironment_example.find('name: '):
    runtimeenvironment_example = \
        runtimeenvironment_example.replace('name: ', '')
if -1 != runtimeenvironment_example.find('\n'):
    runtimeenvironment_example = runtimeenvironment_example.replace('\n'
            , '<BR>')
print runtimeenvironment_example

print """		<BR><BR>
			<B><A NAME="execution_precondition">Execution precondition:</A></B><BR>"""
print exenode_keywords['EXECUTION_PRECONDITION']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['EXECUTION_PRECONDITION']['Example']
print """		<BR><BR>
			<B><A NAME="prepend_execute">Prepend execute:</A></B><BR>"""
print exenode_keywords['PREPEND_EXECUTE']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['PREPEND_EXECUTE']['Example']
print """		<BR><BR>
			<B><A NAME="execute_command">Execute command:</A></B><BR>"""
print exenode_keywords['START_COMMAND']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['START_COMMAND']['Example']
print """		<BR><BR>
			<B><A NAME="status_command">Status command:</A></B><BR>"""
print exenode_keywords['STATUS_COMMAND']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['STATUS_COMMAND']['Example']
print """		<BR><BR>
			<B><A NAME="stop_command">Stop command:</A></B><BR>"""
print exenode_keywords['STOP_COMMAND']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['STOP_COMMAND']['Example']
print """		<BR><BR>
			<B><A NAME="clean_command">Clean command:</A></B><BR>"""
print exenode_keywords['CLEAN_COMMAND']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['CLEAN_COMMAND']['Example']
print """		<BR><BR>
			<B><A NAME="continuous">Job mode:</A></B><BR>"""
print exenode_keywords['CONTINUOUS']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['CONTINUOUS']['Example']
print """		<BR><BR>
			<B><A NAME="shared_fs">Shared filesystem:</A></B><BR>"""
print exenode_keywords['SHARED_FS']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['SHARED_FS']['Example']
print """		<BR><BR>
			<B><A NAME="vgrid">VGrid:</A></B><BR>"""
print exenode_keywords['VGRID']['Description']
print """		<BR><BR>Example:&nbsp;"""
print exenode_keywords['VGRID']['Example']
print """		<BR><BR>
			<hr>
			</body
		    </html>
		    """
