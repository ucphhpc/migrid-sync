#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcsslclient - XMLRPC client with HTTPS user certificate support
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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
from xmlrpcsslclient import xmlrpcgetserver


if '__main__' == __name__:
    if len(sys.argv) > 1:
        vgrid_name = sys.argv[1:]
    else:
        vgrid_name = ['eScience']
    print 'Testing XMLRPC client over HTTPS with user certificates for triggers'
    print 'You may get prompted for your MiG key/certificate passphrase before you can continue'
    server = xmlrpcgetserver()

    methods = server.system.listMethods()
    print 'supported remote methods:\n%s' % '\n'.join(methods)
    print
    print 'submit() signature: %s'\
        % server.system.methodSignature('submit')
    print 'the signature is a tuple of output object type and a list of expected/default input values'
    print 'submit() help: %s' % server.system.methodHelp('submit')
    print 'please note that help is not yet available for all methods'
    print

    print 'Testing some trigger methods:'
    print 'checking triggers for vgrid: %s' % vgrid_name
    (inlist, retval) = server.lsvgridtriggers({'vgrid_name': vgrid_name})
    (returnval, returnmsg) = retval
    if returnval != 0:
        print 'Error %s:%s ' % (returnval, returnmsg)

    for ele in inlist:
        if ele['object_type'] == 'list':
            for el in ele['list']:
                print '%(rule_id)s\t%(path)s\t%(changes)s\t%(action)s\t%(arguments)s\t%(run_as)s\t%(rate_limit)s' % el

    print 'adding dummy trigger for vgrid: %s' % vgrid_name
    (inlist, retval) = server.addvgridtrigger({'vgrid_name': vgrid_name,
                                               'rule_id': ['xmlrpcdummytrigger'],
                                               'path': 'xmldummy-*.txt',
                                               'changes': ['created'],
                                               'action': ['trigger-modified'],
                                               'arguments': ['xmlrpcdummy.out'],
                                               'rate_limit': ['1/m']})
    (returnval, returnmsg) = retval
    if returnval != 0:
        print 'Error %s:%s' % (returnval, returnmsg)

    for ele in inlist:
        if ele['object_type'] == 'text':
            print "Success: %s" % ele['text']
        if ele['object_type'] == 'error_text':
            print "ERROR: %s" % ele['text']

    print 'removing dummy trigger for vgrid: %s' % vgrid_name
    (inlist, retval) = server.rmvgridtrigger({'vgrid_name': vgrid_name,
                                              'rule_id': ['xmlrpcdummytrigger']})
    (returnval, returnmsg) = retval
    if returnval != 0:
        print 'Error %s:%s' % (returnval, returnmsg)

    for ele in inlist:
        if ele['object_type'] == 'text':
            print "Success: %s" % ele['text']
        if ele['object_type'] == 'error_text':
            print "ERROR: %s" % ele['text']
