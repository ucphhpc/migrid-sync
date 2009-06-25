#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcsslclient - XMLRPC client with HTTPS user certificate support
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

"""XMLRPC client with support for HTTPS using client certificates"""

import sys
import os
import time
import httplib
import xmlrpclib
from urlparse import urlparse

SCRIPTNAME = '/cgi-bin/xmlrpcinterface.py'
user_conf_dict = {}


def read_user_conf():
    """Read and parse 'KEY VAL' formatted user conf file"""

    conf_path = os.path.expanduser(os.path.join('~', '.mig',
                                   'miguser.conf'))
    if not os.path.exists(conf_path):
        print 'mig user configuration not found, %s does not exist'\
             % conf_path
        sys.exit(1)

    needed_settings = ['migserver', 'certfile', 'keyfile']
    optional_settings = ['password', 'cacertfile', 'connect_timeout']
    try:
        conf_fd = open(conf_path, 'r')
        for thisline in conf_fd:

            # ignore comments

            comment_start = thisline.find('#')
            if comment_start > -1:
                thisline = thisline[:comment_start]
            thisline = thisline.rstrip()
            if not thisline:
                continue
            parts = thisline.split(None)
            (key, val) = parts[:2]
            if key.strip() in needed_settings + optional_settings:
                user_conf_dict[key.strip()] = val.strip()
        conf_fd.close()
    except IOError, exc:
        print 'Could not read miguser conf: %s, %s' % (conf_path, exc)
        sys.exit(1)
    for needed_key in needed_settings:
        if not user_conf_dict.has_key(needed_key):
            print 'Needed setting %s not found in %s' % (needed_key,
                    conf_path)
            sys.exit(1)


read_user_conf()
CERTFILE = user_conf_dict['certfile']
if not os.path.isfile(CERTFILE):
    print 'Certfile file %s not found!' % CERTFILE
    sys.exit(1)

KEYCERTFILE = user_conf_dict['keyfile']
if not os.path.isfile(KEYCERTFILE):
    print 'Keycertfile %s not found!' % KEYCERTFILE
    sys.exit(1)

# CA cert is not currently used but we include it for future verification support

CACERTFILE = user_conf_dict.get('cacertfile', None)
if CACERTFILE and not os.path.isfile(CACERTFILE):
    print 'specified cacertfile %s not found!' % CACERTFILE
    sys.exit(1)

url_tuple = urlparse(user_conf_dict['migserver'])

# second item in tuple is network location part with hostname and optional port

host_port = url_tuple[1].split(':', 1)
if len(host_port) < 2:
    host_port.append('443')
host_port[1] = int(host_port[1])
(HOSTNAME, HOSTPORT) = host_port


class HTTPSCertTransport(xmlrpclib.Transport):

    """HTTPS with user certificate"""

    host = None

    def make_connection(self, host):

        # TODO: we should try to use supplied password here, but it is difficult!
        # it seems the password handling is passed directly to openssl through console

        conn = httplib.HTTPSConnection(HOSTNAME, HOSTPORT,
                key_file=KEYCERTFILE, cert_file=CERTFILE)

        # conn.set_debuglevel(10)

        return conn

    def request(
        self,
        host,
        handler,
        request_body,
        verbose=0,
        ):

        # issue XML-RPC request

        if not self.host:
            self.host = self.make_connection(host)
        if verbose:
            self.host.set_debuglevel(1)

        self.send_request(self.host, handler, request_body)

        self.send_user_agent(self.host)
        self.send_content(self.host, request_body)

        resp = self.host.getresponse()
        errcode = resp.status
        errmsg = resp.reason
        headers = resp.getheaders()

        if errcode != 200:
            raise xmlrpclib.ProtocolError(host + handler, errcode,
                    errmsg, headers)

        self.verbose = verbose

        try:
            sock = self.host._conn.sock
        except AttributeError:
            sock = None

        return self._parse_response(resp, sock)


def xmlrpcgetserver():
    cert_transport = HTTPSCertTransport()
    server = xmlrpclib.Server('https://%s:%s%s' % (HOSTNAME, HOSTPORT,
                              SCRIPTNAME), transport=cert_transport)
    return server


if '__main__' == __name__:
    if len(sys.argv) > 1:
        job_id_list = sys.argv[1:]
    else:
        job_id_list = ['*']
    print 'Testing XMLRPC client over HTTPS with user certificates'
    print 'You may get prompted for your MiG key/certificate passphrase before you can continue'
    server = xmlrpcgetserver()

    methods = server.system.listMethods()
    print 'supported remote methods:\n%s' % '\n'.join(methods)
    print
    print 'checking job status for job(s) with IDs: %s'\
         % ' '.join(job_id_list)
    (inlist, retval) = server.jobstatus({'job_id': job_id_list, 'flags'
            : 'vs', 'max_jobs': '5'})
    (returnval, returnmsg) = retval
    if returnval != 0:
        print 'Error %s:%s ' % (returnval, returnmsg)

    for ele in inlist:
        if ele['object_type'] == 'job_list':
            for el in ele['jobs']:
                print 'The job with job_id %s: %s' % (el['job_id'],
                        el['status'])

    print
    print 'Listing contents of MiG home directory'
    (inlist, retval) = server.ls({'path': '.', 'flags': 'v'})
    (returnval, returnmsg) = retval
    if returnval != 0:
        print 'Error %s:%s ' % (returnval, returnmsg)

    for ele in inlist:
        if ele['object_type'] == 'dir_listings':
            for dle in ele['dir_listings']:
                for el in dle['entries']:
                    print '%s %s' % (el['type'], el['name'])
    print

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
    # (inlist, retval) = server.textarea({"jobname_0_0_0":"abc", "fileupload_0_0_0filename":"nyfil.mrsl", "submitmrsl_0":["ON"], "fileupload_0_0_0":["%s" % mrsl]})
    # print  "%s : %s" % (retval, inlist)
    # (inlist, retval) = server.editfile({"path":["/m2"], "submitjob":["True"], "editarea":["%s" % mrsl]})
    # (inlist, retval) = server.canceljob({"job_id":["%s" % sys.argv[1]]})

    print 'testing a basic job flow'
    mrsl_path = 'xmlrpc-test-job.mRSL'
    mrsl = """::EXECUTE::
uname -a

::CPUTIME::
30

::SANDBOX::
1
"""
    print 'writing job description to %s file on server' % mrsl_path
    (inlist, retval) = server.editfile({'path': [mrsl_path], 'editarea'
            : ['%s' % mrsl]})
    print 'write status: %s' % retval

    # print "DEBUG: %s\n%s" % (inlist, retval)

    print 'submit job description in %s' % mrsl_path
    (inlist, retval) = server.submit({'path': [mrsl_path]})

    # print "DEBUG: %s\n%s" % (inlist, retval)

    job_id = None
    for entry in inlist:
        if 'submitstatuslist' == entry['object_type']\
             and entry.has_key('submitstatuslist'):
            submit_status = entry['submitstatuslist'][0].get('status',
                    False)
            job_id = entry['submitstatuslist'][0].get('job_id', None)
            print 'submit status: %s' % submit_status
    while job_id:
        print 'wait for job %s to finish' % job_id
        (inlist, retval) = server.jobstatus({'job_id': ['%s' % job_id]})

        # print "DEBUG: %s\n%s" % (inlist, retval)

        for entry in inlist:
            if 'job_list' == entry['object_type']\
                 and entry.has_key('jobs'):
                job_status = entry['jobs'][0].get('status', 'UNKNOWN')
                print 'job name:\t\t%s' % job_id
                print 'job status:\t\t%s' % job_status
                for name in ['queued', 'executing', 'finished']:
                    print '%s date:\t\t%s' % (name, entry['jobs'
                            ][0].get('%s_timestamp' % name, ''))
                print

                if 'FINISHED' == job_status:
                    print 'Read output of job %s' % job_id
                    for name in ['status', 'stdout', 'stderr']:
                        (inlist, retval) = server.cat({'path'
                                : ['job_output/%s/%s.%s' % (job_id,
                                job_id, name)]})

                        # print "DEBUG: %s\n%s" % (inlist, retval)

                        for entry in inlist:
                            if 'file_output' == entry['object_type']\
                                 and entry.has_key('lines'):
                                output_lines = entry['lines']
                                print '''job %s contents:
%s
'''\
                                     % (name, '\n'.join(output_lines))
                    job_id = None
                else:
                    time.sleep(2)

    # (inlist, retval) = server.resubmit({"job_id":["%s" % sys.argv[1]]})
    # (inlist, retval) = server.liveoutput({"job_id":["%s" % sys.argv[1]]})

    # print inlist

    print
    print 'all server methods: %s' % ', '.join(server.dirserver())
    print 'submit() signature: %s'\
         % server.system.methodSignature('submit')
    print 'the signature is a tuple of output object type and a list of expected/default input values'
    print 'submit() help: %s' % server.system.methodHelp('submit')
    print 'please note that help is not yet available for all methods'

