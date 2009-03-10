#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcsslclient_test - [insert a few words of module description on this line]
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

""" Test XMLRPC client """

import sys
import os
import xmlrpcsslclient

server = xmlrpcsslclient.xmlrpcgetserver()

print server.system.listMethods()

(inlist, retval) = server.jobstatus({'job_id': ['%s' % sys.argv[1]],
                                    'flags': 'v'})
(returnval, returnmsg) = retval
if returnval != 0:
    print 'Error %s:%s ' % (returnval, returnmsg)

for ele in inlist:
    if ele['object_type'] == 'job_list':
        for el in ele['jobs']:

            # print el["status"]

            if el['status'] == 'FAILED':
                print 'The job with job_id %s failed!' % el['job_id']

                # print el["execution_histories"]

# print server.ls({"job_id":["56_1_3_2007__22_34_41_vcr", "20_12_6_2006__21_38_28_vcr", "invaliddsfjsdj"]})

resconfig = \
    r"""::MIGUSER::
karlsen

::HOSTURL::
lucia.imada.sdu.dk

::HOSTIDENTIFIER::
0

::RESOURCEHOME::
/home/karlsen/MiG/mig_frontend/lucia.imada.sdu.dk.0

::SCRIPTLANGUAGE::
python

::JOBTYPE::
batch

::SSHPORT::
22

::MEMORY::
256

::DISK::
10

::CPUCOUNT::
1

::ARCHITECTURE::
X86

::NODECOUNT::
1

::RUNTIMEENVIRONMENT::

::HOSTKEY::
lucia.imada.sdu.dk,130.225.128.193 ssh-rsa todoinputsshkey

::FRONTENDNODE::
lucia

::FRONTENDLOG::
/home/karlsen/MiG/mig_frontend/lucia.imada.sdu.dk.0/frontendlog

::LRMSDELAYCOMMAND::

::LRMSSUBMITCOMMAND::

::LRMSDONECOMMAND::

::EXECONFIG::
name=lucia
nodecount=1
cputime=1000
execution_precondition=' '
prepend_execute="nice -19"
exehostlog=/home/karlsen/MiG/mig_exe/lucia.imada.sdu.dk.0/lucia/exehostlog
joblog=/home/karlsen/MiG/mig_exe/lucia.imada.sdu.dk.0/lucia/joblog
execution_user=karlsen
execution_node=lucia
execution_dir=/home/karlsen/MiG/mig_exe/lucia.imada.sdu.dk.0/lucia/
start_command=ssh lucia \"cd /home/karlsen/MiG/mig_exe/lucia.imada.sdu.dk.0/lucia/; chmod 700 master_node_script_lucia.sh; ./master_node_script_lucia.sh \"
status_command=ssh lucia \"exit \\\\\`ps -o pid= -g $mig_exe_pgid | wc -l \\\\\`\"
stop_command=ssh lucia \"kill -9 -$mig_exe_pgid \"
clean_command=ssh brunnhilde \"[ -e clean.sh ] && sh clean.sh \"
continuous=True
shared_fs=True
vgrid=Generic

"""

# (inlist, retval) = server.ls({"path":"%s" % sys.argv[1]})
# print server.lsresowners({"unique_resource_name":["%s" % sys.argv[2]]})
# print server.addresowner({"new_owner":["%s" % sys.argv[1]], "unique_resource_name":["%s" % sys.argv[2]]})
# print server.lsresowners({"unique_resource_name":["%s" % sys.argv[2]]})
# print server.updateresconfig({"resconfig":[resconfig], "unique_resource_name":["%s" % sys.argv[1]]})
# print server.rmresowner({"remove_owner":["%s" % sys.argv[1]], "unique_resource_name":["%s" % sys.argv[2]]})
# print server.lsresowners({"unique_resource_name":["%s" % sys.argv[2]]})
# print server.stopfe({"unique_resource_name":["%s" % sys.argv[2]]})
# print server.restartfe({"unique_resource_name":["%s" % sys.argv[2]]})
# print server.statusfe({"unique_resource_name":["%s" % sys.argv[2]]})
# print server.startfe({"unique_resource_name":["%s" % sys.argv[2]]})
# print server.lsvgridowners({"vgrid_name":["%s" % sys.argv[1]]})
# print server.showre({"re_name":["%s" % sys.argv[1]]})
# print server.spell({"path":["%s" % sys.argv[1]]})
# print server.redb({})
# print server.scripts({})
# print server.wc({"path":["%s" % sys.argv[1], "TextAreaAt_6_7_2007__9_21_27.mRSL"], "flags":"v"})

# print server.addvgridmember({"vgrid_name":["%s" % sys.argv[1]], "cert_name":["%s" % sys.argv[2]]})
# print server.addvgridres({"vgrid_name":["%s" % sys.argv[1]], "unique_resource_name":["%s" % sys.argv[2]]})
# print server.lsvgridres({"vgrid_name":["%s" % sys.argv[1]]})
# print server.adminvgrid({"vgrid_name":["%s" % sys.argv[1]]})
# print server.rmvgridres({"vgrid_name":["%s" % sys.argv[1]], "unique_resource_name":["%s" % sys.argv[2]]})
# print server.lsvgridmembers({"vgrid_name":["%s" % sys.argv[1]]})
# print server.rmvgridmember({"vgrid_name":["%s" % sys.argv[1]], "cert_name":["%s" % sys.argv[2]]})
# print server.addvgridowner({"vgrid_name":["%s" % sys.argv[1]], "cert_name":["%s" % sys.argv[2]]})
# print server.rmvgridowner({"vgrid_name":["%s" % sys.argv[1]], "cert_name":["%s" % sys.argv[2]]})
# print server.rmvgridowner({"vgrid_name":["%s" % sys.argv[1]], "cert_name":["%s" % sys.argv[2]]})
# print server.lsvgridowners({"vgrid_name":["%s" % sys.argv[1]]})
# print server.createvgrid({"vgrid_name":["%s" % sys.argv[1]]})
# print server.lsvgridowners({"vgrid_name":["%s" % sys.argv[1]]})
# print server.vgridmemberrequestaction({"vgrid_name":["%s" % sys.argv[1]], "request_type":["%s" % sys.argv[2]], "request_text":["%s" % sys.argv[3]]})
# (inlist, retval) = server.head({"path":["%s" % sys.argv[1]], "flags":"v"})
# (inlist, retval) = server.tail({"path":["%s" % sys.argv[1]], "flags":"v"})
# (inlist, retval) = server.cp({"src":["%s" % sys.argv[1]], "dst":["%s" % sys.argv[2]], "flags":"v"})
# (inlist, retval) = server.cat({"path":["%s" % sys.argv[1]], "flags":"v"})
# (inlist, retval) = server.touch({"path":["%s" % sys.argv[1]], "flags":"v"})
# (inlist, retval) = server.truncate({"path":["%s" % sys.argv[1]], "flags":"v"})
# (inlist, retval) = server.rm({"path":["%s" % sys.argv[1]], "flags":"v"})
# (inlist, retval) = server.stat({"path":["%s" % sys.argv[1]], "flags":"v"})

# (inlist, retval) = server.mkdir({"path":["%s" % sys.argv[1]], "flags":"v"})
# print "%s : %s" % (retval, inlist)
# (inlist, retval) = server.rmdir({"path":["%s" % sys.argv[1]], "flags":"v"})
# print  "%s : %s" % (retval, inlist)

# (inlist, retval) = server.jobstatus({"job_id":["%s" % sys.argv[1]]})
# mrsl = """::EXECUTE::
# echo test
# """
# (inlist, retval) = server.textarea({"jobname_0_0_0":"abc", "fileupload_0_0_0filename":"nyfil.mrsl", "submitmrsl_0":["ON"], "fileupload_0_0_0":["%s" % mrsl]})
# print  "%s : %s" % (retval, inlist)
# (inlist, retval) = server.editfile({"path":["/m2"], "submitjob":["True"], "editarea":["%s" % mrsl]})
# (inlist, retval) = server.canceljob({"job_id":["%s" % sys.argv[1]]})
# (inlist, retval) = server.resubmit({"job_id":["%s" % sys.argv[1]]})
# (inlist, retval) = server.liveoutput({"job_id":["%s" % sys.argv[1]]})

# print inlist

# print server.dirserver()
# print server.system.methodSignature("jobstatus")
# print server.system.methodHelp("jobstatus")
