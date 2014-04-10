#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobman - Job manager UI for browsing and manipulating jobs
#
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

"""Script to provide users with a means of listing and managing jobs"""

import datetime

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import default_pager_entries
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry

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
        <div id="append" style="display: inline;">
            <img alt="refresh" src="/images/icons/arrow_refresh.png" />
        </div>
''' % datetime.date.today().year

def html_pre():
    """HTML page start"""
    html = '  <div>'
    return html

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
    </div>
    <div id="jm_touchscreen"><input type="checkbox">Enable touch screen
    interface (all clicks trigger menu)</div>
'''
    # Close div from html_pre and add top level context menu
    html += '''
  </div>
  
  <ul id="job_context" class="contextMenu">
      <li class="resubmit single">
          <a href="#resubmit">Resubmit</a>
      </li>
      <li class="freeze single">
          <a href="#freeze">Freeze</a>
      </li>
      <li class="thaw single">
          <a href="#thaw">Thaw</a>
      </li>
      <li class="cancel single">
          <a href="#cancel">Cancel</a>
      </li>
      <li class="mrsl single separator">
          <a href="#mrsl">Raw Description</a>
      </li>
      <li class="schedule single">
          <a href="#schedule">Schedule Status</a>
      </li>
      <li class="feasible single">
          <a href="#feasible">Feasibility Check</a>
      </li>
      <li class="verbosestatus single">
          <a href="#verbosestatus">Verbose Status</a>
      </li>
      <li class="liveio single separator">
          <a href="#liveio">Live I/O</a>
      </li>
      <li class="statusfiles single">
          <a href="#statusfiles">Status Files</a>
      </li>
      <li class="outputfiles single">
          <a href="#outputfiles">Output Files</a>
      </li>
      
      <li class="schedule multi">
          <a href="#schedule">Schedule Status All</a>
      </li>
      <li class="feasible multi">
          <a href="#feasible">Feasibility Check All</a>
      </li>
      <li class="resubmit multi">
          <a href="#resubmit">Resubmit All</a>
      </li>
      <li class="freeze multi">
          <a href="#freeze">Freeze All</a>
      </li>
      <li class="thaw multi">
          <a href="#thaw">Thaw All</a>
      </li>
      <li class="cancel multi separator">
          <a href="#cancel">Cancel All</a>
      </li>
  </ul>
  
  <div id="cmd_helper" title="Command output" style="display: none;"></div>
'''
    return html

def css_tmpl():
    """Stylesheets to include in the page header"""
    css = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.contextmenu.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.custom.css" media="screen"/>
'''
    return css

def js_tmpl():
    """Javascript to include in the page header"""
    js = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.prettyprint.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.contextmenu.js"></script>
<script type="text/javascript" src="/images/js/jquery.jobmanager.js"></script>
<script type="text/javascript">

    try {
        /* jquery-ui-1.8.x option format */
        $.ui.dialog.prototype.options.bgiframe = true;
    } catch(err) {
        /* jquery-ui-1.7.x option format */
        $.ui.dialog.defaults.bgiframe = true;
    }

    $(document).ready(function() {

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
    });
</script>
'''
    return js

def signature():
    """Signature of the main function"""

    defaults = {'dir' : ['']}
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
  
    status = returnvalues.OK
  
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Job Manager'
    title_entry['style'] = css_tmpl()
    title_entry['javascript'] = js_tmpl()
  
    output_objects.append({'object_type': 'header', 'text': 'Job Manager'})
    output_objects.append({'object_type': 'html_form', 'text': html_pre()})
    output_objects.append({'object_type': 'table_pager', 'entry_name': 'jobs',
                           'default_entries': default_pager_entries,
                           'form_append': pager_append()})
    output_objects.append({'object_type': 'html_form', 'text': html_post()})
  
    return (output_objects, status)
