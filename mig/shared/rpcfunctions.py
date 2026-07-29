#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# rpcfunctions - Backend for XMLRPC and JSONRPC interfaces over CGI
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Backend functions for use in XMLRPC and JSONRPC interfaces, exposing all XGI
methods through platform-independent Remote Procedure Calls.
"""

from __future__ import absolute_import

import importlib
import os
import time

from mig.shared import returnvalues
from mig.shared.conf import get_configuration_object
from mig.shared.httpsclient import extract_client_id
from mig.shared.objecttypes import get_object_type_info
from mig.shared.output import validate, kwargs_for_functionality, dummy_main


def system_method_signature(method_name):
    """List method signatures"""

    signature = id
    try:
        exec(compile('from mig.shared.functionality.%s import signature'
                     % method_name, '', 'single'))
        signature_string = "%s" % signature()
    except Exception:
        signature_string = 'none, array'
    return signature_string


def system_method_help(method_name):
    """List method usage"""

    usage = method_help = id
    try:
        exec(compile('from mig.shared.functionality.%s import usage'
                     % method_name, '', 'single'))
        help_string = "%s" % usage()
    except Exception:
        try:
            exec(compile(
                'from mig.shared.functionality.%s import __doc__ as method_help' %
                method_name, '', 'single'))
            help_string = "%s" % method_help
        except Exception:
            help_string = ''
    return help_string


def object_type_info(object_type):
    """Lookup object type"""

    return get_object_type_info(object_type)


def stub(function, user_arguments_dict, environ=None,
         _import_module=importlib.import_module):
    """Run backend function with supplied arguments"""

    before_time = time.time()

    if environ is None:
        environ = os.environ
    configuration = get_configuration_object()
    _logger = configuration.logger

    # get ID of user currently logged in

    client_id = extract_client_id(configuration, environ)
    output_objects = []
    main = dummy_main
    _logger.debug("import main for function: %s" % function)
    try:
        # NOTE: dynamic module loading to find corresponding main function
        module_handle = _import_module(function)
        main = module_handle.main
    except Exception as err:
        _logger.warning("import main for %s failed: %s" % (function, err))
        output_objects.extend([
            {'object_type': 'error_text', 'text':
             'Could not load %r backend!' % function}])
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Save actual functionality backend for initialize_main_variables to expose
    environ['BACKEND_NAME'] = function.split('.')[-1]
    if not isinstance(user_arguments_dict, dict):
        output_objects.extend([
            {'object_type': 'error_text', 'text':
             'user_arguments_dict is not a dictionary/struct type!'}])
        return (output_objects, returnvalues.INVALID_ARGUMENT)

    # TODO: Force to unicode now with py3?
    # NOTE: on py2 JSONRPC dict was unicode and XMLRPC UTF-8 so we forced utf8

    _logger.debug("run %s.main(%s)" % (function, user_arguments_dict))
    try:
        main_kwargs = kwargs_for_functionality(main,
                                               configuration=configuration,
                                               environ=environ)

        (output_objects, (ret_code, ret_msg)) = main(client_id,
                                                     user_arguments_dict,
                                                     **main_kwargs)
    except Exception as err:
        _logger.error("%s main failed: %s" % (function, err))
        import traceback
        _logger.debug("%s main trace:" % traceback.format_exc())
        output_objects.extend([
            {'object_type': 'error_text', 'text':
             'Error calling function: %s' % err}])
        return (output_objects, returnvalues.ERROR)

    (val_ret, val_msg) = validate(output_objects)
    if not val_ret:
        (ret_code, ret_msg) = returnvalues.OUTPUT_VALIDATION_ERROR

        # remove previous output
        # output_objects = []

        _logger.error("%s output validation failed: %s" % (function, val_msg))
        output_objects.extend([
            {'object_type': 'error_text', 'text': 'Validation error! %s' %
             val_msg}, {'object_type': 'title', 'text': 'Validation error!'}])
    after_time = time.time()
    _logger.debug("finished %s.main" % function)
    output_objects.append({'object_type': 'timing_info', 'text':
                           "done in %.3fs" % (after_time - before_time)})
    return (output_objects, (ret_code, ret_msg))


def ls(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.ls', user_arguments_dict)


def tail(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.tail', user_arguments_dict)


def head(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.head', user_arguments_dict)


def find(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.find', user_arguments_dict)


def grep(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.grep', user_arguments_dict)


def wc(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.wc', user_arguments_dict)


def docs(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.docs', user_arguments_dict)


def spell(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.spell', user_arguments_dict)


def editfile(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.editfile', user_arguments_dict)


def editor(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.editor', user_arguments_dict)


def rmdir(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.rmdir', user_arguments_dict)


def zip(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.zip', user_arguments_dict)


def unzip(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.unzip', user_arguments_dict)


def tar(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.tar', user_arguments_dict)


def untar(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.untar', user_arguments_dict)


def pack(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.pack', user_arguments_dict)


def unpack(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.unpack', user_arguments_dict)


def chksum(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.chksum', user_arguments_dict)


def mv(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.mv', user_arguments_dict)


def mkdir(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.mkdir', user_arguments_dict)


def touch(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.touch', user_arguments_dict)


def cat(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.cat', user_arguments_dict)


def cp(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.cp', user_arguments_dict)


def stat(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.statpath', user_arguments_dict)


def truncate(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.truncate', user_arguments_dict)


def rm(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.rm', user_arguments_dict)


def mrslview(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.mrslview', user_arguments_dict)


def jobstatus(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.jobstatus', user_arguments_dict)


def jobaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.jobaction', user_arguments_dict)


def jobfeasible(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.jobfeasible', user_arguments_dict)


def jobschedule(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.jobschedule', user_arguments_dict)


def canceljob(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.canceljob', user_arguments_dict)


def submit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.submit', user_arguments_dict)


def resubmit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.resubmit', user_arguments_dict)


def jobobjsubmit(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.jobobjsubmit',
                user_arguments_dict)


def getjobobj(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.getjobobj', user_arguments_dict)


def scripts(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.scripts', user_arguments_dict)


def liveio(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.liveio', user_arguments_dict)


def mqueue(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.mqueue', user_arguments_dict)


def datatransfer(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.datatransfer', user_arguments_dict)


def sharelink(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.sharelink', user_arguments_dict)


def crontab(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.crontab', user_arguments_dict)


def lscrontab(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.lscrontab', user_arguments_dict)


def addcrontab(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.addcrontab', user_arguments_dict)


def rmcrontab(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.rmcrontab', user_arguments_dict)


def textarea(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.textarea', user_arguments_dict)


def updateresconfig(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.updateresconfig',
                user_arguments_dict)


def addresowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.addresowner', user_arguments_dict)


def rmresowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.rmresowner', user_arguments_dict)


def lsresowners(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.lsresowners', user_arguments_dict)


def delres(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.delres', user_arguments_dict)


def restartfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.restartfe', user_arguments_dict)


def startfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.startfe', user_arguments_dict)


def statusfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.statusfe', user_arguments_dict)


def stopfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.stopfe', user_arguments_dict)


def cleanfe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.cleanfe', user_arguments_dict)


def restartallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.restartallexes', user_arguments_dict)


def restartexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.restartexe', user_arguments_dict)


def startallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.startallexes', user_arguments_dict)


def startexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.startexe', user_arguments_dict)


def statusallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.statusallexes', user_arguments_dict)


def statusexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.statusexe', user_arguments_dict)


def stopallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.stopallexes', user_arguments_dict)


def stopexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.stopexe', user_arguments_dict)


def cleanallexes(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.cleanallexes', user_arguments_dict)


def cleanexe(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.cleanexe', user_arguments_dict)


def restartallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.restartallstores', user_arguments_dict)


def restartstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.restartstore', user_arguments_dict)


def startallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.startallstores', user_arguments_dict)


def startstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.startstore', user_arguments_dict)


def statusallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.statusallstores', user_arguments_dict)


def statusstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.statusstore', user_arguments_dict)


def stopallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.stopallstores', user_arguments_dict)


def stopstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.stopstore', user_arguments_dict)


def cleanallstores(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.cleanallstores', user_arguments_dict)


def cleanstore(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.cleanstore', user_arguments_dict)


def vgridmemberrequest(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.vgridmemberrequest',
                user_arguments_dict)


def vgridmemberrequestaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.vgridmemberrequestaction',
                user_arguments_dict)


def createvgrid(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.createvgrid', user_arguments_dict)


def rmvgridowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.rmvgridowner',
                user_arguments_dict)


def rmvgridmember(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.rmvgridmember',
                user_arguments_dict)


def addvgridmember(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.addvgridmember',
                user_arguments_dict)


def addvgridowner(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.addvgridowner',
                user_arguments_dict)


def lsvgridowners(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.lsvgridowners',
                user_arguments_dict)


def lsvgridmembers(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.lsvgridmembers',
                user_arguments_dict)


def lsvgridres(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.lsvgridres', user_arguments_dict)


def addvgridres(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.addvgridres', user_arguments_dict)


def rmvgridres(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.rmvgridres', user_arguments_dict)


def lsvgridtriggers(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.lsvgridtriggers', user_arguments_dict)


def addvgridtrigger(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.addvgridtrigger', user_arguments_dict)


def rmvgridtrigger(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.rmvgridtrigger', user_arguments_dict)


def vgridworkflows(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.vgridworkflows', user_arguments_dict)


def vgridsettings(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.vgridsettings', user_arguments_dict)


def viewvgrid(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.viewvgrid', user_arguments_dict)


def showvgridmonitor(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.showvgridmonitor',
                user_arguments_dict)


def showvgridprivatefile(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.showvgridprivatefile',
                user_arguments_dict)


def adminvgrid(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.adminvgrid', user_arguments_dict)


def createre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.createre', user_arguments_dict)


def deletere(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.deletere', user_arguments_dict)


def showre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.showre', user_arguments_dict)


def redb(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.redb', user_arguments_dict)


def adminre(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.adminre', user_arguments_dict)


def createbackup(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.createbackup', user_arguments_dict)


def deletebackup(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.deletebackup', user_arguments_dict)


def showbackup(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.showbackup', user_arguments_dict)


def createfreeze(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.createfreeze', user_arguments_dict)


def deletefreeze(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.deletefreeze', user_arguments_dict)


def adminfreeze(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.adminfreeze', user_arguments_dict)


def showfreeze(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.showfreeze', user_arguments_dict)


def freezedb(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.freezedb', user_arguments_dict)


def settings(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.settings', user_arguments_dict)


def settingsaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.settingsaction', user_arguments_dict)


def sendrequest(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.sendrequest', user_arguments_dict)


def sendrequestaction(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.sendrequestaction', user_arguments_dict)


def pubvgridprojects(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.pubvgridprojects',
                user_arguments_dict)


def people(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.people', user_arguments_dict)


def signature(user_arguments_dict):
    """Wrap backend of same name"""

    return stub('mig.shared.functionality.signature', user_arguments_dict)


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
                    sharelink,
                    crontab,
                    lscrontab,
                    addcrontab,
                    rmcrontab,
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
