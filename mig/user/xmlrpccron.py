#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcscron - cron manipulation with XMLRPC and user certificate
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""XMLRPC cron helper with support for HTTPS using client certificates"""

from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
import http.client
import os
import ssl
import sys
import time
import xmlrpc.client
from urllib.parse import urlparse, parse_qs


def read_user_conf():
    """Read and parse 'KEY VAL' formatted user conf file"""
    user_conf = {}
    conf_path = os.path.expanduser(os.path.join('~', '.mig',
                                                'miguser.conf'))
    if not os.path.exists(conf_path):
        print('mig user configuration not found, %s does not exist'
              % conf_path)
        sys.exit(1)

    needed_settings = ['migserver', 'certfile', 'keyfile']
    optional_settings = ['password', 'cacertfile', 'connect_timeout']
    expand_paths = ['certfile', 'keyfile', 'cacertfile']
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
            (key, val) = key.strip(), val.strip()
            if not key in needed_settings + optional_settings:
                continue
            if key in expand_paths:
                val = os.path.expandvars(os.path.expanduser(val))
            user_conf[key] = val
        conf_fd.close()
    except IOError as exc:
        print('Could not read miguser conf: %s, %s' % (conf_path, exc))
        sys.exit(1)
    for needed_key in needed_settings:
        if needed_key not in user_conf:
            print('Needed setting %s not found in %s' % (needed_key,
                                                         conf_path))
            sys.exit(1)
    return user_conf


class SafeCertTransport(xmlrpc.client.SafeTransport):

    """HTTPS with user certificate"""

    host = None
    conf = {}

    def __init__(self, use_datetime=0, conf={}):
        """For backward compatibility with python < 2.7 . Call parent
        constructor and check if the new _connection attribute is set.
        If not we must switch to compatibility mode where the request
        method needs to be overridden.
        """
        xmlrpc.client.SafeTransport.__init__(self, use_datetime)
        self.conf.update(conf)

        if not hasattr(self, '_connection'):
            # print "DEBUG: switch to compat mode"
            self._connection = (None, None)
            self.request = self._compat_request

    def _compat_request(self, host, handler, request_body, verbose=0):
        """For backward compatibility with < 2.7 : must override connection
        calls to fit older httplib API.

        Reuse existing connections to avoid repeating passphrase every single
        time.
        """

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
            raise xmlrpc.client.ProtocolError(host + handler, errcode,
                                          errmsg, headers)

        self.verbose = verbose

        try:
            sock = self.host._conn.sock
        except AttributeError:
            sock = None

        return self._parse_response(resp, sock)

    def make_connection(self, host):
        """Override default HTTPS Transport to include key/cert support. This
        is the python 2.7 version which changed internals and broke
        backward compatibility. We use the exact same structure and do the
        plumbing for backward compatibility in the constructor instead.

        Reuses connections if possible to support HTTP/1.1 keep-alive.

        Finally allows non-interactive use with password from conf file.
        """
        if self._connection and host == self._connection[0]:
            return self._connection[1]
        try:
            HTTPS = http.client.HTTPSConnection
        except AttributeError:
            raise NotImplementedError(
                "your version of httplib doesn't support HTTPS")

        key_pw = self.conf.get('password', None)
        cacert = None
        if conf['cacertfile'] and conf['cacertfile'] != 'AUTO':
            cacert = self.conf['cacertfile']
        ssl_ctx = ssl.create_default_context(cafile=cacert)
        ssl_ctx.load_cert_chain(self.conf['certfile'],
                                keyfile=self.conf['keyfile'], password=key_pw)
        self._connection = host, HTTPS(self.conf['host'],
                                       port=self.conf['port'], context=ssl_ctx)
        return self._connection[1]


def xmlrpcgetserver(conf):
    cert_transport = SafeCertTransport(conf=conf)
    server = xmlrpc.client.ServerProxy('https://%(host)s:%(port)s%(script)s' %
                                   conf, transport=cert_transport,
                                   # encoding='utf-8',
                                   # verbose=True
                                   )
    return server


if '__main__' == __name__:
    csrf_helpers = {'csrf_field': '_csrf', 'addcrontab': '',
                    'rmcrontab': ''}
    freeze_id = 'AUTO'
    path_list = ['welcome.txt']
    if sys.argv[1:]:
        path_list += sys.argv[1:]

    conf = {'script': '/cgi-bin/xmlrpcinterface.py'}
    user_conf = read_user_conf()
    conf.update(user_conf)
    if not os.path.isfile(conf['certfile']):
        print('Cert file %(certfile)s not found!' % conf)
        sys.exit(1)
    if not os.path.isfile(conf['keyfile']):
        print('Key file %(keyfile)s not found!' % conf)
        sys.exit(1)
    # CA cert is not currently used, but we include it for future verification
    cacert = conf.get('cacertfile', None)
    if cacert and cacert != 'AUTO' and not os.path.isfile(cacert):
        print('specified CA cert file %(cacertfile)s not found!' % conf)
        sys.exit(1)
    url_tuple = urlparse(conf['migserver'])
    # second item in tuple is network location part with hostname and optional
    # port
    host_port = url_tuple[1].split(':', 1)
    if len(host_port) < 2:
        host_port.append('443')
    host_port[1] = int(host_port[1])
    conf['host'], conf['port'] = host_port

    print('''Running XMLRPC cron script against %(migserver)s with user certificate
from %(certfile)s , key from %(keyfile)s and
CA certificate %(cacertfile)s . You may get prompted for your MiG
key/certificate passphrase before you can continue.
    ''' % conf)
    server = xmlrpcgetserver(conf)

    api_methods = ['crontab', 'lscrontab', 'addcrontab', 'rmcrontab']
    for method in api_methods:
        print('%s() signature: %s' % (method,
                                      server.system.methodSignature(method)))
        print('the signature is a tuple of output object type and a list of ')
        print('expected/default input values')
        print('%s() help: %s' % (method, server.system.methodHelp(method)))
        print('please note that help is not yet available for all methods')
        print()
        print("Info about %s remote method and variable arguments:" % method)
        signature = server.system.methodSignature(method)
        if 'none' in signature or 'array' in signature:
            print()
            continue
        signature_list = eval(signature.replace('none', 'None'))
        var_dict = signature_list[1]
        var_list = list(var_dict)
        print('%s : %s' % (method, var_list))

    print('Running lscrontab method:')
    lscrontab_args = {}
    (outlist, retval) = server.lscrontab(lscrontab_args)
    (returnval, returnmsg) = retval
    if returnval != 0:
        print('Error %s:%s ' % (returnval, returnmsg))
        print(outlist)
        sys.exit(1)

    # print "DEBUG: lscrontab response: %s" % outlist

    print("lscrontab response:")
    for entry in outlist:
        if entry['object_type'] == 'crontab_listing':
            print("atjobs:")
            for line in entry.get('atjobs', []):
                print(line)
            print("crontab:")
            for line in entry.get('crontab', []):
                print(line)
            # Read out csrf helpers for later use in editing
            csrf_helpers.update(entry.get('csrf_helpers', {}))

    csrf_field = csrf_helpers['csrf_field']
    # print 'DEBUG: csrf helpers: %s' % csrf_helpers

    # print 'Running crontab method:'
    # print 'backup files: %s' % ', '.join(path_list)
    # crontab_args = {
    # 'freeze_id': [freeze_id],
    # csrf_field: [csrf_helpers.get('crontab', '')]
    # }
    # for i in xrange(len(path_list)):
    #    create_args['freeze_copy_%d' % i] = [path_list[i]]

    #(outlist, retval) = server.crontab(crontab_args)
    #(returnval, returnmsg) = retval
    # if returnval != 0:
    #    print 'Error %s:%s ' % (returnval, returnmsg)
    #    sys.exit(1)

    # print "DEBUG: crontab response: %s" % outlist
    # atjobs = ''
    # for entry in outlist:
    #    if entry['object_type'] == 'crontab_log':
    #        print "= Latest Cron/At Log ="
    #        log_lines = entry['log_content']
    # Print last 10 lines
    #        print log_lines.split('\n')[-10:]

    # Dummy jobs for testing add and remove
    cron_jobs = ['49 13 * * * touch add-cron-job-test.txt']
    at_jobs = ['2019-12-24 12:13:14 touch Christmas-test-+SCHEDYEAR+.txt']

    print('Running addcrontab method:')
    addcrontab_args = {'crontab': cron_jobs, 'atjobs': at_jobs,
                       csrf_field: [csrf_helpers.get('addcrontab', '')]
                       }
    (outlist, retval) = server.addcrontab(addcrontab_args)
    (returnval, returnmsg) = retval
    if returnval != 0:
        print('Error %s:%s ' % (returnval, returnmsg))
        print(outlist)
        sys.exit(1)

    # print "DEBUG: addcrontab response: %s" % outlist
    print("addcrontab response:")
    for entry in outlist:
        if entry.get('text', None):
            print("%(object_type)s: %(text)s" % entry)

    print('Running lscrontab method:')
    (outlist, retval) = server.lscrontab(lscrontab_args)
    (returnval, returnmsg) = retval
    if returnval != 0:
        print('Error %s:%s ' % (returnval, returnmsg))
        print(outlist)
        sys.exit(1)

    print("lscrontab response:")
    for entry in outlist:
        if entry['object_type'] == 'crontab_listing':
            print("atjobs:")
            for line in entry.get('atjobs', []):
                print(line)
            print("crontab:")
            for line in entry.get('crontab', []):
                print(line)

    print('Running rmcrontab method:')
    rmcrontab_args = {'crontab': cron_jobs, 'atjobs': at_jobs,
                      csrf_field: [csrf_helpers.get('rmcrontab', '')]
                      }
    (outlist, retval) = server.rmcrontab(rmcrontab_args)
    (returnval, returnmsg) = retval
    if returnval != 0:
        print('Error %s:%s ' % (returnval, returnmsg))
        print(outlist)
        sys.exit(1)

    # print "DEBUG: rmcrontab response: %s" % outlist
    print("rmcrontab response:")
    for entry in outlist:
        if entry.get('text', None):
            print("%(object_type)s: %(text)s" % entry)

    print('Running lscrontab method:')
    (outlist, retval) = server.lscrontab(lscrontab_args)
    (returnval, returnmsg) = retval
    if returnval != 0:
        print('Error %s:%s ' % (returnval, returnmsg))
        print(outlist)
        sys.exit(1)

    print("lscrontab response:")
    for entry in outlist:
        if entry['object_type'] == 'crontab_listing':
            print("atjobs:")
            for line in entry.get('atjobs', []):
                print(line)
            print("crontab:")
            for line in entry.get('crontab', []):
                print(line)

    sys.exit(0)
