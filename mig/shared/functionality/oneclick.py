#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# oneclick - Oneclick resource backend
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

# Minimum Intrusion Grid

"""Oneclick resource back end"""

import shared.returnvalues as returnvalues
from shared.functional import validate_input
from shared.init import initialize_main_variables
from shared.sandbox import get_resource


def signature():
    """Signature of the main function"""

    defaults = {'debug': ['false'], 'console': ['false']}
    return ['html_form', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    output_objects.append({'object_type': 'header', 'text'
                        : '%s One-click resource' % configuration.short_title
                          })
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    debug = ('true' == accepted['debug'][0].lower())
    console = ('true' == accepted['console'][0].lower())

    if not configuration.site_enable_sandboxes:
        output_objects.append({'object_type': 'text', 'text':
                               '''Sandbox resources are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)


    (status, result) = get_resource(client_id, configuration, logger)
    if not status:
        output_objects.append({'object_type': 'html_form', 'text'
                              : result})
        return (output_objects, returnvalues.CLIENT_ERROR)

    fields = {
        'sandboxkey': result[0],
        'resource_name': result[1],
        'cookie': result[2],
        'cputime': result[3],
        'codebase': '%s/sid_redirect/%s.oneclick/'\
             % (configuration.migserver_https_sid_url, result[0]),
        'oneclick_code': 'MiG.oneclick.Applet.class',
        'resource_code': 'MiG.oneclick.Resource.class',
        'oneclick_archive': 'MiGOneClickCodebase.jar',
        'info_code': 'JavaInfoApplet.class',
        'info_archive': '',
        'server': configuration.migserver_https_sid_url,
        'site' : configuration.short_title,
        }

    if debug:
        body = """
DEBUG input vars:
%s
""" % fields
        output_objects.append({'object_type': 'text', 'text': body})

    elif console:
        body = \
                 """
codebase: %(codebase)s
code: %(resource_code)s
archive: %(oneclick_archive)s
server: %(server)s
sandboxkey: %(sandboxkey)s
resource_name: %(resource_name)s
cputime: %(cputime)s
        """ % fields
        output_objects.append({'object_type': 'text', 'text'
                                   : body})
    else:
        body = """
        <object type='application/x-java-applet' height='600' width='800'>
        <param name='codebase' value='%(codebase)s' />
        <param name='code' value='%(oneclick_code)s' />
        <param name='archive' value='%(oneclick_archive)s' />
        <param name='server' value='%(server)s'>
        <param name='sandboxkey' value='%(sandboxkey)s'>
        <param name='resource_name' value='%(resource_name)s'>
        <param name='cputime' value='%(cputime)s'>
        OneClick applet failed to run (requires Java plug-in).
        </object>
        <p>
        Your computer will act as a %(site)s One-click resource as long as
        this browser window/tab remains open.
        </p>
        <h3>Java requirements and background</h3>
        Please note that if you get no applet picture above with status text,
        it is a likely indicator that you do not have the required Java plugin
        installed in your browser. You can download and install it from
        <a class='urllink iconspace' href='http://www.java.com/en/download/manual.jsp'>
        Sun Java Downloads</a>. The browser probably needs to be restarted
        after the installation before the plugin will be enabled.<br />
        Other Java implementations may <i>appear</i> to work but not really
        deliver job results correctly, so if you want to be sure, please
        install the Sun Java plugin.<br />
        Your browser provides the following Java information:<br />
        <object type='application/x-java-applet' height='60' width='400'>
        <param name='codebase' value='%(codebase)s' />
        <param name='code' value='%(info_code)s' />
        Java plugin not installed or disabled.
        </object>
        """ % fields
        output_objects.append({'object_type': 'html_form', 'text'
                               : body})

    return (output_objects, returnvalues.OK)


