#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# resadmin - Administrate a MiG Resource
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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
from binascii import hexlify

import shared.returnvalues as returnvalues
from shared.base import sandbox_resource
from shared.functional import validate_input_and_cert
from shared.html import html_post_helper
from shared.init import initialize_main_variables, find_entry
from shared.refunctions import get_re_dict, list_runtime_environments
from shared.vgrid import res_allowed_vgrids, vgrid_list_vgrids
from shared.vgridaccess import get_resource_map, CONF, OWNERS, RESID


def signature():
    """Signature of the main function"""

    defaults = {'unique_resource_name': []}
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
    row_name = ('even_row', 'odd_row')

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
        configuration.logger.warning(
            'failed to find host identifier from unique resource name!')
        (hosturl, identifier) = (None, 0)

    html += '<a name="%s"></a>' % resourcename
    html += '<h1>%s</h1>\n' % resourcename
    html += '<h3>Configuration</h3>'
    html += '''
Use the <a class="editlink" href="resedit.py?hosturl=%s;hostidentifier=%s">
editing interface
</a>
or make any changes manually in the text box below.<br />
<a class="infolink" href="docs.py?show=Resource">
Resource configuration docs
</a>
''' % (hosturl, identifier)  
    html += '<table class=resources>\n<tr><td class=centertext>'
    html += '''
<form method="post" action="updateresconfig.py">
<textarea cols="100" rows="25" wrap="off" name="resconfig">'''
    for line in raw_conf:
        html += '%s\n' % line.strip()
    html += \
        '''</textarea>
<br />
<input type="hidden" name="unique_resource_name" value="%s" />
<input type="submit" value="Save" />
----------
<input type="reset" value="Forget changes" />
</form>
'''\
         % resourcename

    html += '''
</td></tr></table><p>
<table class=resources><tr class=title><td colspan="5">Front End</td></tr>
'''

    if not frontend:
        html += '<tr><td colspan=5>Not specified</td></tr>\n'
    else:
        html += '<tr><td>%s</td>' % frontend

        for action in ['restart', 'status', 'stop', 'clean']:
            if action == 'restart':
                action_str = '(Re)Start'
            else:
                action_str = action.capitalize()
            html += \
                '''<td>
            <form method="post" action="%sfe.py">
            <input type="hidden" name="unique_resource_name" value="%s" />
            <input type="submit" value="%s" />
            </form>
            </td>
            '''\
                 % (action, resourcename, action_str)
        html += '</tr>'

    html += '<tr class=title><td colspan=5>Execution Units</td></tr>\n'

    if not exe_units:
        html += '<tr><td colspan=5>None specified</td></tr>\n'
    else:
        html += '<tr><td>ALL UNITS</td>'
        for action in ['restart', 'status', 'stop', 'clean']:
            html += \
                '''<td>
            <form method="post" action="%sexe.py">
            <input type="hidden" name="unique_resource_name" value="%s" />
            <input type="hidden" name="all" value="true" />
            <input type="hidden" name="parallel" value="true" />'''\
                 % (action, resourcename)
            if action == 'restart':
                action_str = '(Re)Start'
            else:
                action_str = action.capitalize()
            html += \
                '''
            <input type="submit" value="%s" />
            </form>
            </td>
            '''\
                 % action_str
        html += '</tr>'

        row_number = 1
        for unit in exe_units:
            row_class = row_name[row_number % 2]
            html += '<tr class=%s><td>%s</td>' % (row_class, unit)
            for action in ['restart', 'status', 'stop', 'clean']:
                if action == 'restart':
                    action_str = '(Re)Start'
                else:
                    action_str = action.capitalize()
                html += \
                    '''<td>
                <form method="post" action="%sexe.py">
                <input type="hidden" name="unique_resource_name" value="%s" />
                <input type="hidden" name="exe_name" value="%s" />
                <input type="submit" value="%s" />
                </form>
                </td>
                '''\
                     % (action, resourcename, unit, action_str)
            html += '</tr>'
            row_number += 1

    html += '<tr class=title><td colspan=5>Storage Units</td></tr>\n'

    if not store_units:
        html += '<tr><td colspan=5>None specified</td></tr>\n'
    else:
        html += '<tr><td>ALL UNITS</td>'
        for action in ['restart', 'status', 'stop', 'clean']:
            html += \
                '''<td>
            <form method="post" action="%sstore.py">
            <input type="hidden" name="unique_resource_name" value="%s" />
            <input type="hidden" name="all" value="true" />
            <input type="hidden" name="parallel" value="true" />'''\
                 % (action, resourcename)
            if action == 'restart':
                action_str = '(Re)Start'
            else:
                action_str = action.capitalize()
            html += \
                '''
            <input type="submit" value="%s" />
            </form>
            </td>
            '''\
                 % action_str
        html += '</tr>'

        row_number = 1
        for unit in store_units:
            row_class = row_name[row_number % 2]
            html += '<tr class=%s><td>%s</td>' % (row_class, unit)
            for action in ['restart', 'status', 'stop', 'clean']:
                if action == 'restart':
                    action_str = '(Re)Start'
                else:
                    action_str = action.capitalize()
                html += \
                    '''<td>
                <form method="post" action="%sstore.py">
                <input type="hidden" name="unique_resource_name" value="%s" />
                <input type="hidden" name="store_name" value="%s" />
                <input type="submit" value="%s" />
                </form>
                </td>
                '''\
                     % (action, resourcename, unit, action_str)
            html += '</tr>'
            row_number += 1

    html += '</table><p>'

    html += '<h3>Owners</h3>'
    html += \
        '''
Owners are specified with the Distinguished Name (DN)
from the certificate.<br /> 
<table class=resources>
'''

    html += \
        '''<tr><td>
<form method="post" action="addresowner.py">
<input type="hidden" name="unique_resource_name" value="%s" />
<input type="hidden" name="output_format" value="html" />
<input type="text" name="cert_id" size="72" />
</td><td>
<input type="submit" value=" Add " />
</form>
</td></tr></table><br />
<table class=resources>
'''\
         % resourcename

    for owner_id in owners:
        html += \
            '''<tr><td>
<form method="post" action="rmresowner.py">
<input type="hidden" name="unique_resource_name" value="%s" />
<input type="hidden" name="cert_id" value="%s" />
<input type="hidden" name="output_format" value="html" />
<input type="submit" value="Remove" />
</form>
</td>
'''\
             % (resourcename, owner_id)
        html += '<td>' + owner_id + '</td></tr>'
    html += '</table>'

    # create html to request vgrid resource access

    html += '<h3>VGrid access</h3>'

    html += \
        """Request resource access to additional VGrids.
    <table class=resources>
    <tr><td>
    <form method="post" action="sendrequestaction.py">
    <input type="hidden" name="unique_resource_name" value="%s" />
    <input type="hidden" name="request_type" value="vgridresource" />
    <select name="vgrid_name">"""\
         % resourcename

    # list all vgrids without access

    allowed_vgrids = res_allowed_vgrids(configuration, resourcename)
    (vgrid_status, vgrid_list) = vgrid_list_vgrids(configuration)
    if not vgrid_status:
        vgrid_list = []
    for vgrid_name in vgrid_list:
        if not vgrid_name in allowed_vgrids:
            html += '<option value=%s>%s' % (vgrid_name, vgrid_name)

    html += """</select></td>"""
    html += '''<td>Message to owners:
<input type="text" name="request_text" size=50 value="" />
<input type="submit" value="send" /></td>
'''
    html += '</form></tr></table><p>'

    # create html to select and execute a runtime environment testprocedure

    html += '<h3>Runtime environments</h3>'

    html += \
        """Verify that resource supports the selected runtime environment.
    <table class=resources>
    <tr><td>
    <form method="post" action="testresupport.py">
    <input type="hidden" name="with_html" value="true" />
    <input type="hidden" name="unique_resource_name" value="%s" />
    <select name="re_name">"""\
         % resourcename

    # list runtime environments that have a testprocedure

    for env in re_list:
        (re_dict, re_msg) = get_re_dict(env, configuration)
        if re_dict:
            if re_dict.has_key('TESTPROCEDURE'):
                if re_dict['TESTPROCEDURE'] != []:
                    html += '<option value=%s>%s' % (env, env)

    html += """</select></td>"""
    html += '<td><input type="submit" name="submit" value="verify" /></td>'
    html += '</form></tr></table><p>'

    # create html to select and call script to display testprocedure history

    html += \
        """
Show testprocedure history for the selected runtime environment and the
resource with its current configuration.
    <table class=resources>
    <tr><td>
    <form method="post" action="showresupporthistory.py">
    <input type="hidden" name="unique_resource_name" value="%s" />
    <select name="re_name">"""\
         % resourcename

    # list runtime environments that have a testprocedure

    for env in re_list:
        (re_dict, re_msg) = get_re_dict(env, configuration)
        if re_dict:
            if re_dict.has_key('TESTPROCEDURE'):
                if re_dict['TESTPROCEDURE'] != []:
                    html += '<option value=%s>%s' % (env, env)

    html += """</select></td>"""
    html += '<td><input type="submit" name="submit" value="Show" /></td>'
    html += '</form></tr></table><p>'
    return html


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
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

    unique_res_names = accepted['unique_resource_name']

    (re_stat, re_list) = list_runtime_environments(configuration)
    if not re_stat:
        logger.warning('Failed to load list of runtime environments')
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Error getting list of runtime environments'
                              })
        return (output_objects, returnvalues.SYSTEM_ERROR)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Resource Management'
    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.confirm.js"></script>

<script type="text/javascript" >
var toggleHidden = function(classname) {
    // classname supposed to have a leading dot 
        $(classname).toggleClass("hidden");
    }
    
$(document).ready(function() {

          // init confirmation dialog
          $("#confirm_dialog").dialog(
              // see http://jqueryui.com/docs/dialog/ for options
              { autoOpen: false,
                modal: true, closeOnEscape: true,
                width: 500,
                buttons: {
                   "Cancel": function() { $("#" + name).dialog("close"); }
	        }
              });
     }
);
</script>
'''
    output_objects.append({'object_type': 'header', 'text'
                          : ' Resource Management'})

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : '%s Resources Owned' % configuration.short_title})
    quick_links = [{'object_type': 'text', 'text'
                   : 'Quick links to all your resources and individual management'}]
    quick_links.append({'object_type': 'html_form', 
                        'text': '<div class="hidden quicklinks">'})
    quick_links.append({'object_type': 'link', 
                        'destination': 
                        "javascript:toggleHidden('.quicklinks');",
                        'class': 'removeitemlink',
                        'title': 'Toggle view',
                        'text': 'Hide quick links'})
    quick_links.append({'object_type': 'text', 'text': ''}) 

    quick_res = {}
    quick_links_index = len(output_objects)
    output_objects.append({'object_type': 'sectionheader', 'text': ''})

    output_objects.append({'object_type': 'html_form',
                           'text':'''
 <div id="confirm_dialog" title="Confirm" style="background:#fff;">
  <div id="confirm_text"><!-- filled by js --></div>
   <textarea cols="40" rows="4" id="confirm_input" style="display:none;"/></textarea>
 </div>
'''                       })

    owned = 0
    res_map = get_resource_map(configuration)
    for unique_resource_name in res_map.keys():
        if sandbox_resource(unique_resource_name):
            continue
        owner_list = res_map[unique_resource_name][OWNERS]
        resource_config = res_map[unique_resource_name][CONF]
        visible_res_name = res_map[unique_resource_name][RESID]
        if client_id in owner_list:
            quick_res[unique_resource_name] = \
                                            {'object_type': 'multilinkline',
                                             'links': [
                {'object_type': 'link',
                 'destination': '?unique_resource_name=%s' % \
                 unique_resource_name,
                 'class': 'adminlink',
                 'title': 'Manage %s' % unique_resource_name,
                 'text': 'Manage %s' % unique_resource_name,
                 },
                {'object_type': 'link',
                 'destination': 'viewres.py?unique_resource_name=%s' % \
                 visible_res_name,
                 'class': 'infolink',
                 'title': 'View %s' % unique_resource_name,
                 'text': 'View %s' % unique_resource_name,
                 }
                ]
                                             }


            if unique_resource_name in unique_res_names:
                raw_conf_file = os.path.join(configuration.resource_home,
                                             unique_resource_name,
                                             'config.MiG')
                try:
                    filehandle = open(raw_conf_file, 'r')
                    raw_conf = filehandle.readlines()
                    filehandle.close()
                except:
                    raw_conf = ['']

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


                output_objects.append({'object_type': 'sectionheader', 'text':
                                       'Retire resource'})
                output_objects.append({'object_type': 'text', 'text': '''
Use the link below to permanently remove the resource from the grid after
stopping all units and the front end.
'''
                                       })
                js_name = 'delres%s' % hexlify(unique_resource_name)
                helper = html_post_helper(js_name, 'delres.py',
                                          {'unique_resource_name':
                                           unique_resource_name})
                output_objects.append({'object_type': 'html_form', 'text': helper})
                output_objects.append(
                    {'object_type': 'link', 'destination':
                     "javascript: confirmDialog(%s, '%s');" % \
                     (js_name, 'Really delete %s? (fails if it is busy)' % \
                      unique_resource_name),
                     'class': 'removelink',
                     'title': 'Delete %s' % unique_resource_name, 
                     'text': 'Delete %s' % unique_resource_name}
                    )
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

            quick_links.append({'object_type': 'text', 'text': ''}) 

        quick_links.append({'object_type': 'html_form', 
                            'text': '</div><div class="quicklinks">'})
        quick_links.append({'object_type': 'link', 
                            'destination': 
                            "javascript:toggleHidden('.quicklinks');",
                            'class': 'additemlink',
                            'title': 'Toggle view',
                            'text': 'Show quick links'})
        quick_links.append({'object_type': 'html_form', 
                            'text': '</div>' })

        output_objects = output_objects[:quick_links_index]\
             + quick_links + output_objects[quick_links_index:]

    return (output_objects, returnvalues.OK)


