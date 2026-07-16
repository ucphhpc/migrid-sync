#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcsbackup - backup files with XMLRPC and user certificate
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

"""XMLRPC backup helper with support for HTTPS using client certificates"""

from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
import os
import sys
from urllib.parse import urlparse, parse_qs

from xmlrpcsslclient import xmlrpcgetserver, read_user_conf


if '__main__' == __name__:
    csrf_field = '_csrf'
    csrf_val = None
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

    print('''Running XMLRPC backup script against %(migserver)s with user certificate
from %(certfile)s , key from %(keyfile)s and
CA certificate %(cacertfile)s . You may get prompted for your MiG
key/certificate passphrase before you can continue.
    ''' % conf)
    server = xmlrpcgetserver(conf)

    for method in ['createbackup', 'showfreeze']:
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

    print('Running createbackup method:')
    print('backup files: %s' % ', '.join(path_list))
    create_args = {'freeze_id': [freeze_id],
                   # csrf_field: [csrf_val]
                   }
    for i in range(len(path_list)):
        create_args['freeze_copy_%d' % i] = [path_list[i]]

    (outlist, retval) = server.createbackup(create_args)
    (returnval, returnmsg) = retval
    if returnval != 0:
        print('Error %s:%s ' % (returnval, returnmsg))
        sys.exit(1)

    # print "DEBUG: createbackup response: %s" % outlist

    print("Archive create status:")
    for elem in outlist:
        if elem.get('object_type', 'UNKNOWN') != 'freezestatus':
            continue
        print("Created %(flavor)s archive %(freeze_id)s: %(freeze_state)s" %
              elem)

    # Find actual archive ID from resulting link
    archive_id_list = None
    for elem in outlist:
        if elem.get('object_type', 'UNKNOWN') != 'link':
            continue

        link_url = elem.get('destination', False)
        if not link_url:
            print("WARNING: skip broken link: %s" % elem)
            continue
        url_query = urlparse(link_url).query
        archive_id_list = parse_qs(url_query).get('freeze_id', [])
        if not archive_id_list:
            print("WARNING: skip entry without archive_id: %s" % elem)
            continue

    if not archive_id_list:
        print("ERROR: found no archive id")
        sys.exit(1)

    print('Running showfreeze method for %s:' % archive_id_list)
    (outlist, retval) = server.showfreeze({'freeze_id': archive_id_list,
                                           'flavor': ['backup'],
                                           'checksum': ['sha1'],
                                           'operation': ['list']
                                           })
    (returnval, returnmsg) = retval
    if returnval != 0:
        print('Error %s:%s ' % (returnval, returnmsg))
        print('DEBUG: %s' % outlist)
        sys.exit(1)

    # print "DEBUG: showfreeze response: %s" % outlist

    print("Archive sha1 sums:")
    for elem in outlist:
        if elem.get('object_type', 'UNKNOWN') != 'frozenarchive':
            continue
        if not elem.get('frozenfiles', []):
            print("WARNING: skip entry without frozenfiles: %s" % elem)
            continue
        for entry in elem['frozenfiles']:
            print("%(name)s: %(sha1sum)s" % entry)

    sys.exit(0)
