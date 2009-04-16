#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# oneclick - Oneclick resource backend
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

# Minimum Intrusion Grid

"""Oneclick resource back end"""

import sys
import os

from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
from shared.sandbox import get_resource

import shared.returnvalues as returnvalues

def signature():
    defaults = {'debug': ["false"]}
    return ['html_form', defaults]

def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG One-click resource'})

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    (status, result) = get_resource(cert_name_no_spaces, configuration, logger)
    if not status:
        output_objects.append({'object_type': 'html_form', 'text'
                               : result})
        return (output_objects, returnvalues.CLIENT_ERROR)
        
    fields = {'sandboxkey':result[0],
              'resource_name':result[1],
              'cookie':result[2],
              'cputime':result[3],
              'codebase':'%s/sid_redirect/%s.oneclick/' % \
              (configuration.migserver_https_url, result[0]),
              'applet_code':'MiG.oneclick.Applet.class',
              'resource_code':'MiG.oneclick.Resource.class',
              'archive':'MiGOneClickCodebase.jar',
              'server':configuration.migserver_https_url
              }

    if 'false' == accepted['debug'][0].lower():
        # Generate applet output
        
        body = """
        <Applet codebase='%(codebase)s' code='%(applet_code)s' archive='%(archive)s' width='800' height='600'>
        <PARAM name='server' value='%(server)s'>
        <PARAM name='sandboxkey' value='%(sandboxkey)s'>
        <PARAM name='resource_name' value='%(resource_name)s'>
        <PARAM name='cputime' value='%(cputime)s'>
        </Applet>
        <p>
        Your computer will act as a MiG One-click resource as long as this browser
        window/tab remains open.
        <p>
        Please note that if you get no applet picture above with status text,
        it is a likely indicator that you do not have the required Java plugin installed in your
        browser. You can download and install it from
        <a href='http://www.java.com/en/download/manual.jsp'>Sun Java Downloads</a>. The browser
        probably needs to be restarted after the installation before the plugin will be enabled.
        """ % fields
        output_objects.append({'object_type': 'html_form', 'text': body})
    else:
        body = """
DEBUG input vars:
%s
""" % fields
        output_objects.append({'object_type': 'text', 'text': body})

    return (output_objects, returnvalues.OK)
