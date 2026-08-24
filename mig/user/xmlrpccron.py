#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcscron - cron manipulation with XMLRPC and user certificate
# Copyright (C) 2003-2026  The MiG Project by the Science HPC Center at UCPH
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""XMLRPC cron helper with support for HTTPS using client certificates"""

from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
import os
import sys
from urllib.parse import urlparse

from mig.user.xmlrpcsslclient import xmlrpcgetserver, read_user_conf


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
    conf['host'], conf['port'] = host_port[0], int(host_port[1])

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

    # (outlist, retval) = server.crontab(crontab_args)
    # (returnval, returnmsg) = retval
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
    at_jobs = ['2042-12-24 12:13:14 touch Christmas-test-+SCHEDYEAR+.txt']

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
        print('Error %s:%s' % (returnval, returnmsg))
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
