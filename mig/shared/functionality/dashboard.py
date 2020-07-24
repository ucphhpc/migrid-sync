#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# dashboard - Dashboard entry page backend
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

# See all_docs dictionary below for information about adding
# documentation topics.

"""Dashboard used as entry page"""

import os

from shared import returnvalues
from shared.base import extract_field
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {}
    return ['text', defaults]


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

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Dashboard'

    # jquery support for tablesorter and confirmation on "leave":

    add_import, add_init, add_ready = '', '', ''
    add_init += '''
              function roundNumber(num, dec) {
              var result = Math.round(num*Math.pow(10,dec))/Math.pow(10,dec);
              return result;
          }
    '''
    add_ready += '''
          $("#jobs_stats").addClass("spinner iconleftpad");
          $("#jobs_stats").html("Loading job stats...");
          $("#res_stats").addClass("spinner iconleftpad");
          $("#res_stats").html("Loading resource stats...");
          $("#disk_stats").addClass("spinner iconleftpad");
          $("#disk_stats").html("Loading disk stats...");
          $("#cert_stats").addClass("spinner iconleftpad");
          $("#cert_stats").html("Loading certificate information...");
          /* Run certificate request in the background and handle as soon as results come in */
          $.ajax({
              url: "userstats.py?output_format=json;stats=certificate",
              type: "GET",
              dataType: "json",
              cache: false,
              success: function(jsonRes, textStatus) {
                  var i = 0;
                  var certificate = null;
                  var renew_days = 30;
                  var day_msecs = 24*60*60*1000;
                  // Grab results from json response and place them in resource status.
                  for(i=0; i<jsonRes.length; i++) {
                      if (jsonRes[i].object_type == "user_stats") {    
                          certificate = jsonRes[i].certificate;
                          $("#cert_stats").removeClass("spinner iconleftpad");
                          $("#cert_stats").empty();
                          if (certificate.expire == -1) {
                              break;
                          }
                          var expire_date = new Date(certificate.expire);
                          $("#cert_stats").append("Your user certificate expires on " +
                          expire_date + ".");
                          // Use date from time diff in ms to avoid calendar mangling
                          var show_renew = new Date(expire_date.getTime() - renew_days*day_msecs);
                          if(new Date().getTime() > show_renew.getTime()) {
                              $("#cert_stats").addClass("warningtext");
                              $("#cert_stats").append("&nbsp;<a class=\'certrenewlink  iconspace\' href=\'reqcert.py\'>Renew certificate</a>.");
                          }
                          break;
                      }
                  }
              }
          });
          /* Run jobs request in the background and handle as soon as results come in */
          $.ajax({
              url: "userstats.py?output_format=json;stats=jobs",
              type: "GET",
              dataType: "json",
              cache: false,
              success: function(jsonRes, textStatus) {
                  var i = 0;
                  var jobs = null;
                  // Grab results from json response and place them in job status.
                  for(i=0; i<jsonRes.length; i++) {
                      if (jsonRes[i].object_type == "user_stats") {    
                          jobs = jsonRes[i].jobs;
                          //alert("inspect stats result: " + jobs);
                          $("#jobs_stats").removeClass("spinner iconleftpad");
                          $("#jobs_stats").empty();
                          $("#jobs_stats").append("You have submitted a total of " + jobs.total +
                              " jobs: " + jobs.parse + " parse, " + jobs.queued + " queued, " +
                              jobs.frozen + " frozen, " + jobs.executing + " executing, " +
                              jobs.finished + " finished, " + jobs.retry + " retry, " +
                              jobs.canceled + " canceled, " + jobs.expired + " expired and " +
                              jobs.failed + " failed.");
                         break;
                      }
                  }   
              }
          });
          /* Run resources request in the background and handle as soon as results come in */
          $.ajax({
              url: "userstats.py?output_format=json;stats=resources",
              type: "GET",
              dataType: "json",
              cache: false,
              success: function(jsonRes, textStatus) {
                  var i = 0;
                  var resources = null;
                  // Grab results from json response and place them in resource status.
                  for(i=0; i<jsonRes.length; i++) {
                      if (jsonRes[i].object_type == "user_stats") {    
                          resources = jsonRes[i].resources;
                          //alert("inspect resources stats result: " + resources);
                          $("#res_stats").removeClass("spinner iconleftpad");
                          $("#res_stats").empty();
                          $("#res_stats").append(resources.resources + " resources providing " +
                          resources.exes + " execution units in total allow execution of your jobs.");
                          break;
                      }
                  }
              }
          });
          /* Run disk request in the background and handle as soon as results come in */
          $.ajax({
              url:"userstats.py?output_format=json;stats=disk",
              type: "GET",
              dataType: "json",
              cache: false,
              success: function(jsonRes, textStatus) {
                  var i = 0;
                  var disk = null;
                  // Grab results from json response and place them in resource status.
                  for(i=0; i<jsonRes.length; i++) {
                      if (jsonRes[i].object_type == "user_stats") {    
                          disk = jsonRes[i].disk;
                          //alert("inspect disk stats result: " + disk);
                          $("#disk_stats").removeClass("spinner iconleftpad");
                          $("#disk_stats").empty();
                          $("#disk_stats").append("Your own " + disk.own_files +" files and " +
                              disk.own_directories + " directories take up " + roundNumber(disk.own_megabytes, 2) +
                              " MB in total and you additionally share " + disk.vgrid_files +
                              " files and " + disk.vgrid_directories + " directories of " +
                              roundNumber(disk.vgrid_megabytes, 2) + " MB in total.");
                          break;
                      }
                  }
              }
          });
    '''
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    output_objects.append({'object_type': 'header', 'text': 'Dashboard'})
    output_objects.append({'object_type': 'sectionheader', 'text':
                           "Welcome to the %s" %
                           configuration.site_title})
    welcome_line = "Hi %s" % extract_field(client_id, "full_name")
    output_objects.append({'object_type': 'text', 'text': welcome_line})
    dashboard_info = """
This is your private entry page or your dashboard where you can get a
quick status overview and find pointers to help and documentation.
When you are logged in with your user credentials/certificate, as you are now,
you can navigate your pages using the menu on the left.
""" % os.environ
    output_objects.append({'object_type': 'text', 'text': dashboard_info})

    output_objects.append({'object_type': 'sectionheader', 'text':
                           "Your Status"})
    output_objects.append({'object_type': 'html_form', 'text': '''
<p>
This is a general status overview for your Grid activities. Please note that some
of the numbers are cached for a while to keep server load down.
</p>
<div id="jobs_stats"><!-- for jquery --></div><br />
<div id="res_stats"><!-- for jquery --></div><br />
<div id="disk_stats"><!-- for jquery --></div><br />
<div id="cert_stats"><!-- for jquery --></div><br />
<div id="cert_renew" class="hidden"><a href="reqcert.py">renew certificate</a>
</div>
'''})

    output_objects.append({'object_type': 'sectionheader', 'text':
                           'Documentation and Help'})
    online_help = """
%s includes some built-in documentation like the
""" % configuration.site_title
    output_objects.append({'object_type': 'text', 'text': online_help})
    output_objects.append({'object_type': 'link', 'destination': 'docs.py',
                           'class': 'infolink iconspace', 'title': 'built-in documentation',
                           'text': 'Docs page'})
    project_info = """
but additional help, background information and tutorials are available in the
"""
    output_objects.append({'object_type': 'text', 'text': project_info})
    output_objects.append({'object_type': 'link', 'destination':
                           configuration.site_external_doc,
                           'class': 'urllink iconspace', 'title':
                           'external documentation',
                           'text': 'external %s documentation' %
                           configuration.site_title})

    output_objects.append({'object_type': 'sectionheader', 'text':
                           "Personal Settings"})
    settings_info = """
You can customize your personal pages by opening the Settings
page from the navigation menu and entering personal preferences. In that way you
can completely redecorate your interface and configure things like notification,
profile visibility and remote file access.
"""
    output_objects.append({'object_type': 'text', 'text': settings_info})

    #env_info = """Env %s""" % os.environ
    #output_objects.append({'object_type': 'text', 'text': env_info})

    return (output_objects, returnvalues.OK)
