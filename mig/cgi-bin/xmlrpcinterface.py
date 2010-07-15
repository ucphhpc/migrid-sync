#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# xmlrpcinterface - Provides the entire XMLRPC interface over CGI
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

from SimpleXMLRPCServer import CGIXMLRPCRequestHandler

import shared.returnvalues as returnvalues
from shared.httpsclient import extract_client_id
from shared.objecttypes import get_object_type_info
from shared.output import validate


class MiGCGIXMLRPCRequestHandler(CGIXMLRPCRequestHandler):

    def system_methodSignature(self, method_name):
        """List method signatures"""

        signature = id
        try:
            exec compile('from shared.functionality.%s import signature'
                          % method_name, '', 'single')
            signature_string = str(signature())
        except:
            signature_string = 'none, array'
        return signature_string

    def system_methodHelp(self, method_name):
        """List method usage"""

        usage = method_help = id
        try:
            exec compile('from shared.functionality.%s import usage'
                          % method_name, '', 'single')
            help_string = str(usage())
        except:
            try:
                exec compile('from shared.functionality.%s import __doc__ as method_help'
                              % method_name, '', 'single')
                help_string = str(method_help)
            except:
                help_string = ''
        return help_string



def serverMethodSignatures(server):
    """List all methods as well as signatures"""
    methods=CGIXMLRPCRequestHandler.system_listMethods(server)
    methods_and_signatures=[(method, server.system_methodSignature(method)) for method in methods]
    return methods_and_signatures

def object_type_info(object_type):
    """Lookup object type"""

    return get_object_type_info(object_type)


def my_id():
    """Return DN of user currently logged in"""

    return extract_client_id()


def stub(function, user_arguments_dict):
    """Run backend function with supplied arguments"""

    # get ID of user currently logged in

    main = id
    client_id = extract_client_id()
    output_objects = []
    try:
        exec 'from %s import main' % function
    except Exception, err:
        output_objects.extend([{'object_type': 'error_text', 'text'
                              : 'Could not import module! %s: %s'
                               % (function, err)}])
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if not isinstance(user_arguments_dict, dict):
        output_objects.extend([{'object_type': 'error_text', 'text'
                              : 'user_arguments_dict is not a dictionary/struct type!'
                              }])
        return (output_objects, returnvalues.INVALID_ARGUMENT)

    return_val = returnvalues.OK
    try:

        # return (user_arguments_dict)

        (output_objects, return_val) = main(client_id,
                user_arguments_dict)
    except Exception, err:
        return ('Error calling function: %s' % err, returnvalues.ERROR)

    (val_ret, val_msg) = validate(output_objects)
    if not val_ret:
        return_val = returnvalues.OUTPUT_VALIDATION_ERROR

        # remove previous output
        # output_objects = []

        output_objects.extend([{'object_type': 'error_text', 'text'
                              : 'Validation error! %s' % val_msg},
                              {'object_type': 'title', 'text'
                              : 'Validation error!'}])
    return (output_objects, return_val)


def jobstatus(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.jobstatus', user_arguments_dict)


def ls(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.ls', user_arguments_dict)


def liveio(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.liveio', user_arguments_dict)


def tail(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.tail', user_arguments_dict)


def head(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.head', user_arguments_dict)


def addresowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.addresowner', user_arguments_dict)


def rmresowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rmresowner', user_arguments_dict)


def lsresowners(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.lsresowners', user_arguments_dict)


def startfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.startfe', user_arguments_dict)


def statusfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.statusfe', user_arguments_dict)


def stopfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.stopfe', user_arguments_dict)


def restartfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.restartfe', user_arguments_dict)


def lsvgridowners(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.lsvgridowners',
                user_arguments_dict)


def showre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.showre', user_arguments_dict)


def createvgrid(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.createvgrid', user_arguments_dict)


def redb(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.redb', user_arguments_dict)


def wc(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.wc', user_arguments_dict)


def scripts(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.scripts', user_arguments_dict)


def canceljob(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.canceljob', user_arguments_dict)


def submit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.submit', user_arguments_dict)


def resubmit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.resubmit', user_arguments_dict)


def textarea(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.textarea', user_arguments_dict)


def restartexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.restartexe', user_arguments_dict)


def stopexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.stopexe', user_arguments_dict)


def vgridmemberrequest(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.vgridmemberrequest',
                user_arguments_dict)


def vgridmemberrequestaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.vgridmemberrequestaction',
                user_arguments_dict)


def mkdir(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.mkdir', user_arguments_dict)


def touch(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.touch', user_arguments_dict)


def cat(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cat', user_arguments_dict)


def cp(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cp', user_arguments_dict)


def stat(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.statpath', user_arguments_dict)


def truncate(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.truncate', user_arguments_dict)


def rm(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rm', user_arguments_dict)


def rmvgridowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rmvgridowner',
                user_arguments_dict)


def rmvgridmember(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rmvgridmember',
                user_arguments_dict)


def addvgridmember(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.addvgridmember',
                user_arguments_dict)


def addvgridowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.addvgridowner',
                user_arguments_dict)


def lsvgridmembers(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.lsvgridmembers',
                user_arguments_dict)


def lsvgridres(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.lsvgridres', user_arguments_dict)


def addvgridres(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.addvgridres', user_arguments_dict)


def rmvgridres(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rmvgridres', user_arguments_dict)


def adminvgrid(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.adminvgrid', user_arguments_dict)


def updateresconfig(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.updateresconfig',
                user_arguments_dict)


def createre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.createre', user_arguments_dict)


def docs(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.docs', user_arguments_dict)


def spell(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.spell', user_arguments_dict)


def startexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.startexe', user_arguments_dict)


def cleanexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cleanexe', user_arguments_dict)


def cleanfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cleanfe', user_arguments_dict)


def statusexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.statusexe', user_arguments_dict)


def adminre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.adminre', user_arguments_dict)


def editfile(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.editfile', user_arguments_dict)


def editor(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.editor', user_arguments_dict)


def rmdir(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rmdir', user_arguments_dict)


def settings(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.settings', user_arguments_dict)


def pubvgridprojects(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.pubvgridprojects',
                user_arguments_dict)


def zip(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.zip', user_arguments_dict)


def showvgridmonitor(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.showvgridmonitor',
                user_arguments_dict)


def mv(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.mv', user_arguments_dict)


def signature(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.signature', user_arguments_dict)


def jobobjsubmit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.jobobjsubmit',
                user_arguments_dict)


def getjobobj(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.getjobobj', user_arguments_dict)


# ## Main ###

if '__main__' == __name__:
    server = MiGCGIXMLRPCRequestHandler()

    def AllMethodSignatures(): return serverMethodSignatures(server)
    server.register_function(AllMethodSignatures)

    server.register_function(object_type_info)
    server.register_function(my_id)
    server.register_function(jobstatus)
    server.register_function(ls)
    server.register_function(liveio)
    server.register_function(tail)
    server.register_function(head)
    server.register_function(addresowner)
    server.register_function(rmresowner)
    server.register_function(lsresowners)
    server.register_function(startfe)
    server.register_function(statusfe)
    server.register_function(stopfe)
    server.register_function(restartfe)
    server.register_function(lsvgridowners)
    server.register_function(showre)
    server.register_function(createvgrid)
    server.register_function(redb)
    server.register_function(wc)
    server.register_function(scripts)
    server.register_function(canceljob)
    server.register_function(submit)
    server.register_function(resubmit)
    server.register_function(textarea)
    server.register_function(restartexe)
    server.register_function(stopexe)
    server.register_function(cleanfe)
    server.register_function(cleanexe)
    server.register_function(vgridmemberrequest)
    server.register_function(vgridmemberrequestaction)
    server.register_function(mkdir)
    server.register_function(touch)
    server.register_function(cat)
    server.register_function(cp)
    server.register_function(stat)
    server.register_function(truncate)
    server.register_function(rm)
    server.register_function(rmvgridowner)
    server.register_function(rmvgridmember)
    server.register_function(addvgridmember)
    server.register_function(addvgridowner)
    server.register_function(lsvgridmembers)
    server.register_function(lsvgridres)
    server.register_function(addvgridres)
    server.register_function(rmvgridres)
    server.register_function(adminvgrid)
    server.register_function(updateresconfig)
    server.register_function(createre)
    server.register_function(docs)
    server.register_function(spell)
    server.register_function(startexe)
    server.register_function(statusexe)
    server.register_function(adminre)
    server.register_function(editfile)
    server.register_function(editor)
    server.register_function(rmdir)
    server.register_function(settings)
    server.register_function(pubvgridprojects)
    server.register_function(zip)
    server.register_function(showvgridmonitor)
    server.register_function(mv)
    server.register_function(signature)
    server.register_function(jobobjsubmit)
    server.register_function(getjobobj)
    server.register_introspection_functions()
    server.handle_request()
