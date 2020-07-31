#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobman - Job manager UI for browsing and manipulating jobs
#
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

"""Script to provide users with a means of listing and managing jobs"""
from __future__ import absolute_import

import datetime

from mig.shared import returnvalues
from mig.shared.base import client_id_dir
from mig.shared.defaults import default_pager_entries, csrf_backends
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.html import themed_styles
from mig.shared.init import initialize_main_variables, find_entry


def pager_append():
    """Additional html for the pager to extend navigation"""
    return '''
        load <select class="maxjobs">
          <option value="100" selected>100</option>
          <option value="200">200</option>
          <option value="500">500</option>
          <option value="1000">1000</option>
          <option value="5000">5000</option>
          <option value="10000">10000</option>
          <option value="-1">all</option>
        </select> last jobs
        matching <input class="filterid" name="filterid" size=16 value="*_%s_*"/>
''' % datetime.date.today().year


def html_post():
    """HTML page end"""

    html = '''
    <div class="jm_container">
        <table id="jm_jobmanager">
            <thead>
                <tr>
                    <th style="width: 20px;">
                        <input type="checkbox" id="checkAll" />
                    </th>
                    <th>Job ID</th>
                    <th style="width: 120px;">Status</th>
                    <th style="width: 180px;">Date</th>
                </tr>        
            </thead>
            <tbody>
                <tr><td>.</td><td>Job ID</td><td>Status</td><td>Date</td></tr>
            </tbody>
        </table>
        <div id="jm_options">
            <input id="jm_touchscreen" type="checkbox">Enable touch screen
            interface (all clicks trigger menu)
            <input id="jm_autorefresh" type="checkbox">Enable automatic refresh
        </div>
    </div>
  
    <div id="cmd_helper" title="Command output" style="display: none;"></div>
'''
    return html


def css_tmpl(configuration, user_settings):
    """Stylesheets to include in the page header"""

    # TODO: can we update style inline to avoid explicit themed_styles?
    css = themed_styles(configuration, base=['jquery.contextmenu.css',
                                             'jquery.managers.contextmenu.css'],
                        user_settings=user_settings)
    return css


def js_tmpl_parts(csrf_map={}):
    """Javascript to include in the page header"""
    add_import = '''
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.prettyprint.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
<script type="text/javascript" src="/images/js/jquery.contextmenu.js"></script>
<script type="text/javascript" src="/images/js/jquery.jobmanager.js"></script>
    '''
    add_init = '''
var csrf_map = {};
'''
    for (target_op, token) in csrf_map.items():
        add_init += '''
csrf_map["%s"] = "%s";
''' % (target_op, token)
    add_init += '''
    try {
        /* jquery-ui-1.8.x option format */
        $.ui.dialog.prototype.options.bgiframe = true;
    } catch(err) {
        /* jquery-ui-1.7.x option format */
        $.ui.dialog.defaults.bgiframe = true;
    }
    '''
    add_ready = '''
        /* wrap in try/catch for debugging - disabled in prodution */
        /*
        try {
        */    
            $("#jm_jobmanager").jobmanager({});
        /*
        } catch(err) {
            alert("Internal error in job manager: " + err);
        }
        */
    '''
    return (add_import, add_init, add_ready)


def js_tmpl(csrf_map={}):
    """Javascript to include in the page header"""
    (js_import, js_init, js_ready) = js_tmpl_parts(csrf_map)
    js = '''
%s
    
<script type="text/javascript">
    %s

    $(document).ready(function() {
    %s
    });
</script>
''' % (js_import, js_init, js_ready)
    return js


def signature():
    """Signature of the main function"""

    defaults = {'dir': ['']}
    return ['', defaults]


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
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

    if not configuration.site_enable_jobs:
        output_objects.append({'object_type': 'error_text', 'text':
                               '''Job execution is not enabled on this system'''})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    status = returnvalues.OK

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Job Manager'
    user_settings = title_entry.get('user_settings', {})
    title_entry['style'] = css_tmpl(configuration, user_settings)
    csrf_map = {}
    method = 'post'
    limit = get_csrf_limit(configuration)
    for target_op in csrf_backends:
        csrf_map[target_op] = make_csrf_token(configuration, method,
                                              target_op, client_id, limit)
    (add_import, add_init, add_ready) = js_tmpl_parts(csrf_map)
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'header', 'text': 'Job Manager'})
    output_objects.append({'object_type': 'table_pager', 'entry_name': 'jobs',
                           'default_entries': default_pager_entries,
                           'form_append': pager_append()})
    output_objects.append({'object_type': 'html_form', 'text': html_post()})

    return (output_objects, status)
