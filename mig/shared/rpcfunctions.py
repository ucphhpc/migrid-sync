#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rpcfunctions - Backend for XMLRPC and JSONRPC interfaces over CGI
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

"""Backend functions for use in XMLRPC and JSONRPC interfaces, exposing all XGI
methods through platform-independent Remote Procedure Calls.
"""

import os
import time

import shared.returnvalues as returnvalues
from shared.base import force_utf8_rec
from shared.conf import get_configuration_object
from shared.httpsclient import extract_client_id
from shared.objecttypes import get_object_type_info
from shared.output import validate

def system_method_signature(method_name):
    """List method signatures"""

    signature = id
    try:
        exec compile('from shared.functionality.%s import signature'
                      % method_name, '', 'single')
        signature_string = str(signature())
    except:
        signature_string = 'none, array'
    return signature_string

def system_method_help(method_name):
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



def object_type_info(object_type):
    """Lookup object type"""

    return get_object_type_info(object_type)

def stub(function, user_arguments_dict):
    """Run backend function with supplied arguments"""

    before_time = time.time()

    environ = os.environ
    configuration = get_configuration_object()
    _logger = configuration.logger

    # get ID of user currently logged in

    main = id
    client_id = extract_client_id(configuration, environ)
    output_objects = []
    _logger.debug("import main for function: %s" % function)
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

    ## NOTE: Force to UTF-8 - JSONRPC dict is unicode while XMLRPC is UTF-8
    if user_arguments_dict and True in [isinstance(i, unicode) for i in \
                                        user_arguments_dict.keys()]:
        user_arguments_dict = force_utf8_rec(user_arguments_dict)

    _logger.debug("run %s.main(%s)" % (function, user_arguments_dict))
    try:

        # TODO: add environ arg support to all main backends and use here

        (output_objects, (ret_code, ret_msg)) = main(client_id,
                                                     user_arguments_dict)
    except Exception, err:
        _logger.error("%s main failed: %s" % (function, err))
        import traceback
        _logger.debug("%s main trace:" % traceback.format_exc())
        return ('Error calling function: %s' % err, returnvalues.ERROR)

    (val_ret, val_msg) = validate(output_objects)
    if not val_ret:
        (ret_code, ret_msg) = returnvalues.OUTPUT_VALIDATION_ERROR

        # remove previous output
        # output_objects = []

        _logger.error("%s output validation failed: %s" % (function, val_msg))
        output_objects.extend([{'object_type': 'error_text', 'text'
                              : 'Validation error! %s' % val_msg},
                              {'object_type': 'title', 'text'
                              : 'Validation error!'}])
    after_time = time.time()
    _logger.debug("finished %s.main" % function)
    output_objects.append({'object_type': 'timing_info', 'text':
                           "done in %.3fs" % (after_time - before_time)})
    return (output_objects, (ret_code, ret_msg))


def ls(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.ls', user_arguments_dict)


def tail(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.tail', user_arguments_dict)


def head(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.head', user_arguments_dict)


def find(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.find', user_arguments_dict)


def grep(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.grep', user_arguments_dict)


def wc(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.wc', user_arguments_dict)


def docs(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.docs', user_arguments_dict)


def spell(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.spell', user_arguments_dict)


def editfile(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.editfile', user_arguments_dict)


def editor(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.editor', user_arguments_dict)


def rmdir(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rmdir', user_arguments_dict)


def zip(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.zip', user_arguments_dict)


def unzip(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.unzip', user_arguments_dict)


def tar(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.tar', user_arguments_dict)


def untar(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.untar', user_arguments_dict)


def pack(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.pack', user_arguments_dict)


def unpack(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.unpack', user_arguments_dict)


def chksum(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.chksum', user_arguments_dict)


def mv(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.mv', user_arguments_dict)


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


def mrslview(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.mrslview', user_arguments_dict)


def jobstatus(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.jobstatus', user_arguments_dict)


def jobaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.jobaction', user_arguments_dict)


def jobfeasible(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.jobfeasible', user_arguments_dict)


def jobschedule(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.jobschedule', user_arguments_dict)


def canceljob(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.canceljob', user_arguments_dict)


def submit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.submit', user_arguments_dict)


def resubmit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.resubmit', user_arguments_dict)


def jobobjsubmit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.jobobjsubmit',
                user_arguments_dict)


def getjobobj(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.getjobobj', user_arguments_dict)


def scripts(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.scripts', user_arguments_dict)


def liveio(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.liveio', user_arguments_dict)


def mqueue(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.mqueue', user_arguments_dict)


def datatransfer(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.datatransfer', user_arguments_dict)


def imagepreview(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.imagepreview', user_arguments_dict)


def textarea(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.textarea', user_arguments_dict)


def updateresconfig(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.updateresconfig',
                user_arguments_dict)


def addresowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.addresowner', user_arguments_dict)


def rmresowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rmresowner', user_arguments_dict)


def lsresowners(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.lsresowners', user_arguments_dict)


def delres(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.delres', user_arguments_dict)


def restartfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.restartfe', user_arguments_dict)


def startfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.startfe', user_arguments_dict)


def statusfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.statusfe', user_arguments_dict)


def stopfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.stopfe', user_arguments_dict)


def cleanfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cleanfe', user_arguments_dict)


def restartallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.restartallexes', user_arguments_dict)


def restartexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.restartexe', user_arguments_dict)


def startallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.startallexes', user_arguments_dict)


def startexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.startexe', user_arguments_dict)


def statusallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.statusallexes', user_arguments_dict)


def statusexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.statusexe', user_arguments_dict)


def stopallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.stopallexes', user_arguments_dict)


def stopexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.stopexe', user_arguments_dict)


def cleanallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cleanallexes', user_arguments_dict)


def cleanexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cleanexe', user_arguments_dict)


def restartallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.restartallstores', user_arguments_dict)


def restartstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.restartstore', user_arguments_dict)


def startallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.startallstores', user_arguments_dict)


def startstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.startstore', user_arguments_dict)


def statusallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.statusallstores', user_arguments_dict)


def statusstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.statusstore', user_arguments_dict)


def stopallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.stopallstores', user_arguments_dict)


def stopstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.stopstore', user_arguments_dict)


def cleanallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cleanallstores', user_arguments_dict)


def cleanstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.cleanstore', user_arguments_dict)


def vgridmemberrequest(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.vgridmemberrequest',
                user_arguments_dict)


def vgridmemberrequestaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.vgridmemberrequestaction',
                user_arguments_dict)


def createvgrid(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.createvgrid', user_arguments_dict)


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


def lsvgridowners(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.lsvgridowners',
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


def lsvgridtriggers(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.lsvgridtriggers', user_arguments_dict)


def addvgridtrigger(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.addvgridtrigger', user_arguments_dict)


def rmvgridtrigger(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.rmvgridtrigger', user_arguments_dict)


def vgridworkflows(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.vgridworkflows', user_arguments_dict)


def vgridsettings(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.vgridsettings', user_arguments_dict)


def viewvgrid(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.viewvgrid', user_arguments_dict)


def showvgridmonitor(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.showvgridmonitor',
                user_arguments_dict)


def showvgridprivatefile(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.showvgridprivatefile',
                user_arguments_dict)


def adminvgrid(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.adminvgrid', user_arguments_dict)


def createre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.createre', user_arguments_dict)


def deletere(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.deletere', user_arguments_dict)


def showre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.showre', user_arguments_dict)


def redb(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.redb', user_arguments_dict)


def adminre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.adminre', user_arguments_dict)


def createbackup(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.createbackup', user_arguments_dict)


def deletebackup(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.deletebackup', user_arguments_dict)


def showbackup(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.showbackup', user_arguments_dict)


def createfreeze(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.createfreeze', user_arguments_dict)


def deletefreeze(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.deletefreeze', user_arguments_dict)


def adminfreeze(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.adminfreeze', user_arguments_dict)


def showfreeze(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.showfreeze', user_arguments_dict)


def freezedb(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.freezedb', user_arguments_dict)


def settings(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.settings', user_arguments_dict)


def settingsaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.settingsaction', user_arguments_dict)


def sendrequest(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.sendrequest', user_arguments_dict)


def sendrequestaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.sendrequestaction', user_arguments_dict)


def pubvgridprojects(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.pubvgridprojects',
                user_arguments_dict)


def people(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.people', user_arguments_dict)


def signature(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('shared.functionality.signature', user_arguments_dict)


# IMPORTANT: List of all functions to expose both in XMLRPC and JSONRPC
expose_functions = [object_type_info,
                    ls,
                    tail,
                    head,
                    find,
                    grep,
                    wc,
                    docs,
                    spell,
                    editfile,
                    editor,
                    rmdir,
                    zip,
                    unzip,
                    tar,
                    untar,
                    pack,
                    unpack,
                    chksum,
                    mv,
                    mkdir,
                    touch,
                    cat,
                    cp,
                    stat,
                    truncate,
                    rm,
                    mrslview,
                    jobstatus,
                    jobaction,
                    jobfeasible,
                    jobschedule,
                    canceljob,
                    submit,
                    resubmit,
                    jobobjsubmit,
                    getjobobj,
                    scripts,
                    liveio,
                    mqueue,
                    datatransfer,
                    imagepreview,
                    textarea,
                    updateresconfig,
                    addresowner,
                    rmresowner,
                    lsresowners,
                    delres,
                    restartfe,
                    startfe,
                    statusfe,
                    stopfe,
                    cleanfe,
                    restartallexes,
                    restartexe,
                    startallexes,
                    startexe,
                    statusallexes,
                    statusexe,
                    stopallexes,
                    stopexe,
                    cleanallexes,
                    cleanexe,
                    restartallstores,
                    restartstore,
                    startallstores,
                    startstore,
                    statusallstores,
                    statusstore,
                    stopallstores,
                    stopstore,
                    cleanallstores,
                    cleanstore,
                    vgridmemberrequest,
                    vgridmemberrequestaction,
                    createvgrid,
                    rmvgridowner,
                    rmvgridmember,
                    addvgridmember,
                    addvgridowner,
                    lsvgridowners,
                    lsvgridmembers,
                    lsvgridres,
                    addvgridres,
                    rmvgridres,
                    lsvgridtriggers,
                    addvgridtrigger,
                    rmvgridtrigger,
                    vgridworkflows,
                    vgridsettings,
                    viewvgrid,
                    showvgridmonitor,
                    showvgridprivatefile,
                    adminvgrid,
                    createre,
                    deletere,
                    showre,
                    redb,
                    adminre,
                    createbackup,
                    deletebackup,
                    showbackup,
                    createfreeze,
                    deletefreeze,
                    adminfreeze,
                    showfreeze,
                    freezedb,
                    settings,
                    settingsaction,
                    sendrequest,
                    sendrequestaction,
                    pubvgridprojects,
                    people,
                    signature,
                    ]
