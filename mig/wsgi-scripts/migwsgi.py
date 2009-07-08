#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# migwsgi.py - Provides the entire WSGI interface
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

import os
import sys
import cgi

import shared.returnvalues as returnvalues
from shared.cgiinput import fieldstorage_to_dict
from shared.httpsclient import extract_client_id
from shared.objecttypes import get_object_type_info
from shared.output import validate, do_output


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
    try:
        exec 'from %s import main' % function
    except Exception, err:
        return ('Could not import module! %s: %s' % (function, err),
                returnvalues.SYSTEM_ERROR)

    if not isinstance(user_arguments_dict, dict):
        return ('user_arguments_dict is not a dictionary/struct type!',
                returnvalues.INVALID_ARGUMENT)

    return_val = returnvalues.OK
    try:

        # return (user_arguments_dict)

        (output_objects, return_val) = main(client_id, user_arguments_dict)
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


def liveoutput(user_arguments_dict):
    """Wrap backend of same name"""
    return stub('shared.functionality.liveoutput', user_arguments_dict)


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


# def resetexe(user_arguments_dict):
#    """Wrap backend of same name"""
#    return stub("shared.functionality.stopexe", user_arguments_dict)


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


def public_vgrid_projects(user_arguments_dict):
    """Wrap backend of same name"""
    return stub('shared.functionality.public_vgrid_projects',
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
def basic_application(environ, start_response):
    """Sample app called automatically by wsgi"""
    status = '200 OK'
    output = 'Hello World!'

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

def application(environ, start_response):
    """MiG app called automatically by wsgi"""

    # pass environment on to sub handlers
    os.environ = environ

    # make sure print calls do not interfere with wsgi
    sys.stdout = sys.stderr
    fieldstorage = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ) 
    user_arguments_dict = fieldstorage_to_dict(fieldstorage)

    # default to html

    output_format = 'html'
    if user_arguments_dict.has_key('output_format'):
        output_format = user_arguments_dict['output_format'][0]

    try:
        backend = eval(environ['SCRIPT_URL'].replace('/MiG/', '').replace('.py', ''))
        (output_objs, ret_val) = backend(user_arguments_dict)
    except:
        #(output_objs, ret_val) = (my_id(), returnvalues.OK)
        #(output_objs, ret_val) = (user_arguments_dict, returnvalues.OK)
        (output_objs, ret_val) = ([{'object_type': 'text', 'text': str(environ)}], returnvalues.OK)
    if returnvalues.OK == ret_val:
        status = '200 OK'
    else:
        status = '403 ERROR'

    (ret_code, ret_msg) = ret_val
    output = do_output(ret_code, ret_msg, output_objs, output_format)
    if not output:

        # Error occured during output print
    
        output = 'Return object was _not_ successfully extracted!'

    content = 'text/html'
    if 'html' !=  output_format:
        content = 'text/plain'
    response_headers = [('Content-type', content),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]
