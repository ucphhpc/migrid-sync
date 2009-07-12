#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resadmin - [insert a few words of module description on this line]
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

"""Enable resource administrators to manage their own resources
through a web interface. Management includes adding new
resources, tweaking the configuration of existing resources,
starting, stopping and getting status of resources, and
administrating owners.
"""

import os
import sys
import glob
import time

from shared.conf import get_resource_configuration
from shared.refunctions import get_re_dict, list_runtime_environments
from shared.fileio import unpickle
from shared.init import initialize_main_variables
from shared.findtype import is_owner
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues


def signature():
    """Signature of the main function"""

    defaults = {'benchmark': 'false'}
    return ['html_form', defaults]


def display_resource(
    resourcename,
    raw_conf,
    resource_config,
    owners,
    re_list,
    configuration,
    ):
    """Format and print the information and actions for a
    given resource.
    """

    exe_units = []
    store_units = []
    frontend = None
    hosturl = None
    html = ''

    if resource_config:
        if resource_config.has_key('EXECONFIG'):
            for exe in resource_config['EXECONFIG']:
                exe_units.append(exe['name'])
        if resource_config.has_key('STORECONFIG'):
            for store in resource_config['STORECONFIG']:
                store_units.append(store['name'])
        if resource_config.has_key('FRONTENDNODE'):
            frontend = resource_config['FRONTENDNODE']
        if resource_config.has_key('HOSTURL'):
            hosturl = resource_config['HOSTURL']

    # Try to split resourcename first to support resources where name
    # doesn't match hosturl.

    sep = '.'
    index = resourcename.rfind(sep)
    if index:
        hosturl = resourcename[:index]
        identifier = resourcename[index + 1:]
    elif hosturl:
        identifier = resourcename.replace(hosturl + sep, '')
    else:
        print 'WARNING: failed to find host identifier from unique resource name!'
        (hosturl, identifier) = (None, 0)

    html += '<a name="%s"></a>' % resourcename
    html += '<h1>%s</h1>\n' % resourcename
    html += '<h3>Configuration</h3>'
    html += \
        'Use the <a href="resource_edit.py?hosturl=%s;hostidentifier=%s">editing interface</a> '\
         % (hosturl, identifier)
    html += 'or make any changes manually in the text box below.<br>'
    html += \
        '<a href="docs.py?show=Resource">Resource configuration docs</a>'
    html += '<table class=resources>\n<tr><td class=centertext>'
    html += \
        '''
<form method="post" action="updateresconfig.py">
<textarea cols="100" rows="25" wrap="off" name="resconfig">'''
    for line in raw_conf:
        html += '%s\n' % line.strip()
    html += \
        '''</textarea>
<br>
<input type="hidden" name="unique_resource_name" value="%s">
<input type="submit" value="Save">
----------
<input type="reset" value="Forget changes">
</form>
'''\
         % resourcename
    html += '</td></tr></table><p>'

    html += \
        '<table class=resources><tr class=title><td colspan="5">Front End</td></tr>\n'

    if not frontend:
        html += '<tr><td>Not specified</td><tr>'
    else:
        html += '<tr><td>' + frontend + '</td>'

        for action in ['restart', 'status', 'stop', 'clean']:
            if action == 'restart':
                action_str = '(Re)Start'
            else:
                action_str = action.capitalize()
            html += \
                '''<td>
            <form method="get" action="%sfe.py">
            <input type="hidden" name="unique_resource_name" value="%s">
            <input type="submit" value="%s">
            </form>
            </td>
            '''\
                 % (action, resourcename, action_str)

    html += '</tr>'

    # html += '</tr></table><p>'

    html += '<tr class=title><td colspan=5>Execution Units</td></tr>\n'

    if not exe_units:
        html += '<tr><td>Not specified</td><tr>'
    else:
        html += '<tr><td>ALL UNITS</td>'
        for action in ['restart', 'status', 'stop', 'clean']:
            html += \
                '''<td>
            <form method="get" action="%sexe.py">
            <input type="hidden" name="unique_resource_name" value="%s">
            <input type="hidden" name="all" value="true">
            <input type="hidden" name="parallel" value="true">'''\
                 % (action, resourcename)
            if action == 'restart':
                action_str = '(Re)Start'
            else:
                action_str = action.capitalize()
            html += \
                '''
            <input type="submit" value="%s">
            </form>
            </td>
            '''\
                 % action_str
        html += '</tr>'

        for unit in exe_units:
            html += '<tr><td>' + unit + '</td>'
            for action in ['restart', 'status', 'stop', 'clean']:
                if action == 'restart':
                    action_str = '(Re)Start'
                else:
                    action_str = action.capitalize()
                html += \
                    '''<td>
                <form method="get" action="%sexe.py">
                <input type="hidden" name="unique_resource_name" value="%s">
                <input type="hidden" name="exe_name" value="%s">
                <input type="submit" value="%s">
                </form>
                </td>
                '''\
                     % (action, resourcename, unit, action_str)
            html += '</tr>'

    html += '<tr class=title><td colspan=5>Storage Units</td></tr>\n'

    if not store_units:
        html += '<tr><td>Not specified</td><tr>'
    else:
        html += '<tr><td>ALL UNITS</td>'
        for action in ['restart', 'status', 'stop', 'clean']:
            html += \
                '''<td>
            <form method="get" action="%sstore.py">
            <input type="hidden" name="unique_resource_name" value="%s">
            <input type="hidden" name="all" value="true">
            <input type="hidden" name="parallel" value="true">'''\
                 % (action, resourcename)
            if action == 'restart':
                action_str = '(Re)Start'
            else:
                action_str = action.capitalize()
            html += \
                '''
            <input type="submit" value="%s">
            </form>
            </td>
            '''\
                 % action_str
        html += '</tr>'

        for unit in store_units:
            html += '<tr><td>' + unit + '</td>'
            for action in ['restart', 'status', 'stop', 'clean']:
                if action == 'restart':
                    action_str = '(Re)Start'
                else:
                    action_str = action.capitalize()
                html += \
                    '''<td>
                <form method="get" action="%sstore.py">
                <input type="hidden" name="unique_resource_name" value="%s">
                <input type="hidden" name="store_name" value="%s">
                <input type="submit" value="%s">
                </form>
                </td>
                '''\
                     % (action, resourcename, unit, action_str)
            html += '</tr>'

    html += '</table><p>'

    html += '<h3>Owners</h3>'
    html += \
        '''
Owners are specified with the Distinguished Name (DN)
from the certificate.<br> 
<table class=resources>
'''

    html += \
        '''<tr><td>
<form method="get" action="addresowner.py">
<input type="hidden" name="unique_resource_name" value="%s">
<input type="hidden" name="output_format" value="html">
<input type="text" name="cert_id" size=30>
</td><td>
<input type="submit" value=" Add ">
</form>
</td></tr></table><br>
<table class=resources>
'''\
         % resourcename

    for owner_id in owners:
        html += \
            '''<tr><td>
<form method="get" action="rmresowner.py">
<input type="hidden" name="unique_resource_name" value="%s">
<input type="hidden" name="cert_id" value="%s">
<input type="hidden" name="output_format" value="html">
<input type="submit" value="Remove">
</form>
</td>
'''\
             % (resourcename, owner_id)
        html += '<td>' + owner_id + '</td></tr>'
    html += '</table>'

    # create html to select and execute a runtime environment testprocedure

    html += '<h3>Runtime environments</h3>'

    html += \
        """Verify that resource supports the selected runtime environment.
    <table class=resources>
    <tr><td>
    <form method="get" action="testresupport.py">
    <input type="hidden" name="with_html" value="true">
    <input type="hidden" name="unique_resource_name" value="%s">
    <select name="re_name">"""\
         % resourcename

    # list runtime environments that have a testprocedure

    for re in re_list:
        (re_dict, re_msg) = get_re_dict(re, configuration)
        if re_dict:
            if re_dict.has_key('TESTPROCEDURE'):
                if re_dict['TESTPROCEDURE'] != []:
                    html += '<option value=%s>%s' % (re, re)

    html += """</select></td>"""
    html += '<td><input type=submit name=submit value=verify>'
    html += '</form></table><p>'

    # create html to select and call script to display testprocedure history

    html += \
        """Show testprocedure history for the selected runtime environment and the resource with its current configuration.
    <table class=resources>
    <tr><td>
    <form method="get" action="showresupporthistory.py">
    <input type="hidden" name="unique_resource_name" value="%s">
    <select name="re_name">"""\
         % resourcename

    # list runtime environments that have a testprocedure

    for re in re_list:
        (re_dict, re_msg) = get_re_dict(re, configuration)
        if re_dict:
            if re_dict.has_key('TESTPROCEDURE'):
                if re_dict['TESTPROCEDURE'] != []:
                    html += '<option value=%s>%s' % (re, re)

    html += """</select></td>"""
    html += '<td><input type=submit name=submit value=Show>'
    html += '</form></table><p>'
    return html


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False, op_title=False)
    defaults = signature()[1]
    (validate_status, accepted) = validate_input_and_cert(
        user_arguments_dict,
        defaults,
        output_objects,
        client_id,
        configuration,
        allow_rejects=False,
        )
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    benchmark = accepted['benchmark'][-1].lower() != 'false'
    start_time = time.time()

    (re_stat, re_list) = list_runtime_environments(configuration)
    if not re_stat:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of runtime environments'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG Resource Management'})
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Resource Management'})
    output_objects.append({'object_type': 'link', 'text'
                          : 'Create a new MiG resource', 'destination'
                          : 'resource_edit.py?new_resource=true'})
    output_objects.append({'object_type': 'sectionheader', 'text': ''})

    # Use cgi-bin links to sandboxes here to preserve menu

    output_objects.append({'object_type': 'link', 'text'
                          : 'Administrate MiG sandbox resources',
                          'destination': 'ssslogin.py'})
    output_objects.append({'object_type': 'sectionheader', 'text': ''})
    output_objects.append({'object_type': 'link', 'text'
                          : 'Use this computer as One-click MiG resource'
                          , 'destination': 'oneclick.py'})

    quick_links = [{'object_type': 'sectionheader', 'text'
                   : 'Quick links to existing resources:'}]
    quick_res = {}
    quick_links_index = len(output_objects)
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'MiG Resources Owned'})

    base = configuration.resource_home
    owned = 0
    for resource_dir in glob.glob(base + os.sep + '*'):
        if os.path.isdir(resource_dir):
            unique_resource_name = resource_dir.replace(base, '')
            if is_owner(client_id, unique_resource_name,
                        configuration.resource_home, logger):
                raw_conf_file = os.path.join(resource_dir, 'config.MiG')
                owners_file = os.path.join(resource_dir, 'owners')
                owner_list = unpickle(owners_file, logger)
                (status, resource_config) = \
                    get_resource_configuration(configuration.resource_home,
                        unique_resource_name, logger)
                if not status:
                    output_objects.append({'object_type': 'warning',
                            'text'
                            : "Could not unpack resource configuration - Don't worry if this is a new MiG resource."
                            })
                    continue
                try:
                    filehandle = open(raw_conf_file, 'r')
                    raw_conf = filehandle.readlines()
                    filehandle.close()
                except:
                    raw_conf = ['']

                quick_res[unique_resource_name] = \
                    {'object_type': 'link', 'text': '%s'\
                      % unique_resource_name, 'destination': '#%s'\
                      % unique_resource_name}
                res_html = display_resource(
                    unique_resource_name,
                    raw_conf,
                    resource_config,
                    owner_list,
                    re_list,
                    configuration,
                    )
                output_objects.append({'object_type': 'html_form',
                        'text': res_html})
                owned += 1

    if owned == 0:
        output_objects.append({'object_type': 'text', 'text'
                              : 'You are not listed as owner of any resources!'
                              })
    else:
        sorted_links = quick_res.items()
        sorted_links.sort()
        for (res_id, link_obj) in sorted_links:
            quick_links.append(link_obj)

            # add new line

            quick_links.append({'object_type': 'html_form', 'text'
                               : '<br>'})
        output_objects = output_objects[:quick_links_index]\
             + quick_links + output_objects[quick_links_index:]

    finish_time = time.time()
    if benchmark:
        output_objects.append({'object_type': 'text', 'text'
                              : 'Resource admin back end delivered data in %.2f seconds'
                               % (finish_time - start_time)})

    return (output_objects, returnvalues.OK)


