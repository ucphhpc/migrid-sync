#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcsslclient - [insert a few words of module description on this line]
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

""" XMLRPC client with support for HTTPS with client certificates! """

import httplib
import xmlrpclib
import sys
import os
from urlparse import urlparse

SCRIPTNAME = "/cgi-bin/xmlrpcinterface.py"
user_conf_dict = {}

def read_user_conf():
    conf_path = os.environ["HOME"] + os.sep + ".mig" + os.sep + "miguser.conf"
    if not os.path.exists(conf_path):
        print "mig user configuration not found, %s does not exist" % conf_path
        sys.exit(1)
    if not os.path.isfile(conf_path):
        print "mig user configuration not found, %s exists but is not a file!" % conf_path
        sys.exit(1)
        
    needed_settings = ["migserver", "certfile", "keyfile"]
    try:
        fh = open(conf_path, "r")
        thisline = fh.readline()
        while thisline != "":
            (key, val) = thisline.split(" ", 1)
            if key.strip() in needed_settings:
                user_conf_dict[key.strip()] = val.strip()
            thisline = fh.readline()
        fh.close()
    except Exception, exc:
        print "Could not read miguser conf: %s, %s" % (conf_path, exc)
        sys.exit(1)
    for needed_key in needed_settings:
        if not user_conf_dict.has_key(needed_key):
            print "Needed setting %s not found in %s" % (needed_key, conf_path)
            sys.exit(1)
            
read_user_conf()
CERTFILE = user_conf_dict["certfile"]
if not os.path.isfile(CERTFILE):
    print "Certfile file %s not found!" % CERTFILE
    sys.exit(1)
    
KEYCERTFILE = user_conf_dict["keyfile"]
if not os.path.isfile(KEYCERTFILE):
    print "Keycertfile %s not found!" % KEYCERTFILE
    sys.exit(1)

urlparseoutput = urlparse(user_conf_dict["migserver"])
HOSTNAME = urlparseoutput.hostname
HOSTPORT = urlparseoutput.port
if HOSTPORT == None:
    HOSTPORT = 443
    
#print "Hostname: %s" % HOSTNAME
#print "Hostport: %s" % HOSTPORT
#print "Certfile: %s" % CERTFILE
#print "Keyfile: %s" % KEYCERTFILE

class https_with_client_cert_transport(xmlrpclib.Transport):
    h = None
    
    def make_connection(self, host):                
        conn = httplib.HTTPSConnection(
        HOSTNAME, HOSTPORT,
        key_file = KEYCERTFILE,
        cert_file = CERTFILE
        )
        #conn.set_debuglevel(10)
        return conn

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request
        if self.h == None:
            self.h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        self.send_request(self.h, handler, request_body)
        # MiG changed
        #self.send_host(h, host)
        self.send_user_agent(self.h)
        self.send_content(self.h, request_body)

        # MiG changed
        #errcode, errmsg, headers = h.getreply()
        resp = self.h.getresponse()
        errcode = resp.status
        errmsg = resp.reason
        headers = resp.getheaders()       

        ###
        if errcode != 200:
            raise xmlrpclib.ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        self.verbose = verbose

        try:
            sock = self.h._conn.sock
        except AttributeError:
            sock = None

        # MiG changed:!
        #return self._parse_response(h.getfile(), sock)
        return self._parse_response(resp, sock)

def xmlrpcgetserver():
    p = https_with_client_cert_transport()
    server = xmlrpclib.Server('https://%s:%s%s' % (HOSTNAME, HOSTPORT, SCRIPTNAME), transport=p)
    return server