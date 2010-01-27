#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobman - Job manager UI for browsing and manipulating jobs
#
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

"""Script to provide users with a means of listing files and directories in
their home directories.
"""

import os
import time
import glob
import stat

from shared.parseflags import all, long_list, recursive
from shared.validstring import valid_user_path
from shared.init import initialize_main_variables, find_entry
from shared.functional import validate_input_and_cert
import shared.returnvalues as returnvalues
from shared.settings import load_settings
from shared.useradm import client_id_dir

def html_tmpl():
  """HTML page base"""

  html = '''
  <div>
    <div class="toolbar">        
      <div class="pager" id="pager">
      <form style="display: inline;" action="">
        <img class="first" src="/images/icons/arrow_left.png"/>
        <img class="prev" src="/images/icons/arrow_left.png"/>
        <input type="text" class="pagedisplay" />
        <img class="next" src="/images/icons/arrow_right.png"/>
        <img class="last" src="/images/icons/arrow_right.png"/>
        <select class="pagesize">
          <option value="10">10</option>
          <option value="15" selected>15</option>
          <option value="20">20</option>
          <option value="25">25</option>
          <option value="40">40</option>
          <option value="50">50</option>
          <option value="60">60</option>
          <option value="80">80</option>
          <option value="100">100</option>
        </select>
      </form>
      <div id="append"  style="display: inline;"><img src="/images/icons/arrow_refresh.png" /></div>
      </div>
      
    </div>
    <div class="stuff">
      <table id="jm_jobmanager">      
      <thead>
        <tr>
          <th style="width: 20px;"><input type="checkbox" id="checkAll" /></th>
          <th>JobID</th>
          <th style="width: 120px;">Status</th>
          <th style="width: 180px;">Date</th>
        </tr>        
      </thead>
      <tbody>
        <tr><td>.</td><td>JobID</td><td>Status</td><td>Date</td></tr>
      </tbody>
    </table>
    </div>
    
  </div>
  
  <ul id="job_context" class="contextMenu">        
      <li class="resubmit single">
          <a href="#resubmit">Resubmit</a>
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
      <li class="liveoutput single">
          <a href="#liveoutput">Live Output</a>
      </li>
      <li class="statusfiles single separator">
          <a href="#statusfiles">Status Files</a>
      </li>
      <li class="outputfiles single">
          <a href="#outputfiles">Output Files</a>
      </li>
      
      <li class="schedule multi">
          <a href="#schedule">Schedule Status All</a>
      </li>
      <li class="resubmit multi">
          <a href="#resubmit">Resubmit All</a>
      </li>
      <li class="cancel multi separator">
          <a href="#cancel">Cancel All</a>
      </li>        
  </ul>
  
  <div id="cmd_helper" title="Command output" style="display: none;"></div>
  '''
  return html

def js_tmpl():
  """Javascript to include in the page header"""
  
  js = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.contextmenu.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-1.7.2.custom.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery-1.3.2.min.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui-1.7.2.custom.min.js"></script>
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.prettyprint.js"></script>
<script type="text/javascript" src="/images/js/jquery.jobmanager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.contextmenu.js"></script>
  
  <script type="text/javascript">
  
  function toTimestamp(strDate) {
      return Date.parse(strDate);
  }

  function jsonWrapper(el_id, dialog, url, jsonOptions) {
        
    var jsonSettings = {	output_format: "json" };
    
    $.fn.extend(jsonSettings, jsonOptions);
    
    $.getJSON(
    url,
    jsonSettings,
    function(jsonRes, textStatus) {
    
      var errors			= "";
      var file_output = "";
      var dir_listings = "";
      var misc_output = "";
      var submit_output = "";
      var success_message = "<br />Success!";
      
      for(var i=0; i<jsonRes.length; i++) {
      
        switch(jsonRes[i]["object_type"]) {
            
          case "error_text":
            errors += "<p>Errors:</p>";
            errors +="<p>"+jsonRes[i].text+"</p>";
          break;
          
          case "file_output":
            
            for(j=0; j<jsonRes[i].lines.length; j++) {
              file_output += jsonRes[i].lines[j]+"\\n";
            }
            if (file_output.length>0) {
              file_output += "<p>File output:</p>"+file_output;  
            }
          break;
          
          case "dir_listings":
            
            for(j=0; j<jsonRes[i]["dir_listings"].length; j++) {
              dir_listings += jsonRes[i]["dir_listings"][j];
            }
            if (dir_listings.length >0) {
              dir_listings = "<p>Directory Listings</p>"+dir_listings;  
            }
          break;
          
          case "submitstatuslist":
          
            for(j=0; j<jsonRes[i]["submitstatuslist"].length; j++) {
            
              if (jsonRes[i]["submitstatuslist"][j]["status"]) {
                misc_output +=	"<p>Submitted '"
                            +		jsonRes[i]["submitstatuslist"][j]["name"]
                            +		"'</p>"
                            +		"<p>Job identfier: '"+jsonRes[i]["submitstatuslist"][j]["job_id"]
                            +		"'</p>";
              } else {
                misc_output +=	"<p>Failed submitting:</p><p>"
                            +		jsonRes[i]["submitstatuslist"][j]["name"]
                            +		" "+jsonRes[i]["submitstatuslist"][j]["message"]
                            +		"</p>";
              }													
            
            }
              
          break;
          
          case "changedstatusjobs":
          
            for(j=0; j<jsonRes[i]["changedstatusjobs"].length; j++) {
              if (jsonRes[i]["changedstatusjobs"][j]["message"]) {
                misc_output += jsonRes[i]["changedstatusjobs"][j]["message"];
              } else {
                success_message = "<p>Job status changed from '"+ jsonRes[i]["changedstatusjobs"][j]["oldstatus"] + "' to '"+jsonRes[i]["changedstatusjobs"][j]["newstatus"]+"'.</p>";
              }
            }
              
          break;
          
          case "saveschedulejobs":
            for(j=0; j<jsonRes[i]["saveschedulejobs"].length; j++) {
              if (jsonRes[i]["saveschedulejobs"][j]["message"]) {
                misc_output += jsonRes[i]["saveschedulejobs"][j]["message"];
              } else {
                success_message = "<p>Job schedule '"+ jsonRes[i]["saveschedulejobs"][j]["oldstatus"]+"'.";
              }
            }
          break;
          
          case "resubmitobjs":
            for(j=0; j<jsonRes[i]["resubmitobjs"].length; j++) {
              if (jsonRes[i]["resubmitobjs"][j]["status"]) {
                success_message = "<br />Resubmitted job as: "+jsonRes[i]["resubmitobjs"][j]["new_job_id"];
              } else {
                misc_output += jsonRes[i]["resubmitobjs"][j]["message"];  
              }
              
            }
          break;
          
          case "text":
            misc_output += jsonRes[i]["text"];                        
          break;
          
          case "file_not_found":
            misc_output += "<p>File not found: '"+jsonRes[i]["name"]+"'.</p>";
          break;
            
        }
          
      }
        
      if ((errors.length + file_output.length + misc_output.length + dir_listings.length) >0){
                    
        if (file_output.length>0) {
          file_output = "<pre>"+file_output+"</pre>";	
        }
        
        if (dir_listings.length>0) {
          dir_listings = "<pre>"+dir_listings+"</pre>";	
        }
        
        if ((errors.length>0) || (misc_output.length>0)) {
          $("#cmd_helper div[title="+el_id+"]").removeClass("spinner").addClass("error");  
        } else {
          $("#cmd_helper div[title="+el_id+"]").removeClass("spinner").addClass("ok");
        }
        
        $("#cmd_helper div[title="+el_id+"] p").append("<br />"+errors+file_output+misc_output+dir_listings);
        
      } else {
        $("#cmd_helper div[title="+el_id+"]").removeClass("spinner").addClass("ok");
        $("#cmd_helper div[title="+el_id+"] p").append(success_message);
        
      }
      
    });
      
  }

  $(document).ready(

    function() {
    
    $.tablesorter.addWidget({
        id: "multiselect",
        format: function(table) {
        
            $("#jm_jobmanager tbody tr td input").bind("click", function(event) {

                var job_id = $(this).parent().parent().attr("id");
                var is_checked = $("#"+job_id+" input").attr("checked");
                                
                if (is_checked) {
                    $("#"+job_id).addClass("ui-selected");
                } else {
                    $("#"+job_id).removeClass("ui-selected");
                }
                
                return true;
                
            });
            
        }
    });
    
    $.tablesorter.addWidget({ 

        id: "contextual", 
        format: function(table) { 

            var actions = {
                cancel: function (job_id) {                    
                    jsonWrapper(job_id, "#cmd_dialog", "canceljob.py", {job_id: job_id})
                },
                mrsl: function (job_id) {
                  jsonWrapper(job_id, "#cmd_dialog", "mrslview.py", {job_id: job_id})
                },
                resubmit: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "resubmit.py", {job_id: job_id})
                },
                statusfiles: function (job_id) {    
                    document.location = "fileman.py?path="+"job_output/"+job_id;
                },
                outputfiles: function (job_output) {    
                    // TODO: fileman does not support file paths and multi path - use old ls
                    //document.location = "fileman.py?"+job_output.match(/^ls.py\?(.*)$/)[1];
                    document.location = job_output;
                },
                liveoutput: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "liveoutput.py", {job_id: job_id})
                },
                schedule: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobschedule.py", {job_id: job_id})
                },
            };

            $("#jm_jobmanager tbody tr td").contextMenu({ menu: "job_context"},
                function(action, el, pos) {
                    
                    // Status and output files redirect to the filemanager, so they do not match the general case of jsonwrapping/commandoutput
                    if (action == "statusfiles") {
                      actions[action]($("input[name=job_identifier]", $(el).parent()).val());                      
                      return true;
                    }
                    else if (action == "outputfiles") {
                      actions[action]($("input[name=job_output]", $(el).parent()).val());                      
                      return true;
                    }                    
                    
                    // All other actions are handled by the general case.
                    var single_selection = !$(el).parent().hasClass("ui-selected");
                    var job_id = "";
                    
                    $("#cmd_helper").dialog({buttons: {Close: function() {$(this).dialog("close");} }, width: "620px", autoOpen: false, closeOnEscape: true, modal: true, position: [300, 70]});
                    $("#cmd_helper").dialog("open");
                    $("#cmd_helper").html("");
                                                        
                    if (single_selection) {
                    
                        job_id = $("input[name=job_identifier]", $(el).parent()).val();
                                                
                        $("#cmd_helper").append("<div class='spinner' title='"+job_id+"' style='padding-left: 20px;'><p>JobId: "+job_id+"</p></div>");
                        actions[action](job_id);
                        
                    } else {
                        var selected_rows = $("#jm_jobmanager tbody tr.ui-selected");
                        $("#cmd_helper").append("<p>"+action+": "+selected_rows.length+" jobs, see individual status below:</p>");
                        selected_rows.each(function(i) {
                            job_id = $("input[name=job_identifier]", this).val();                            
                            $("#cmd_helper").append("<div class='spinner' title='"+job_id+"' style='padding-left: 20px;'><p>"+job_id+"</p></div>");
                            actions[action](job_id);
                        });                        
                    }
                    
                    $("#append").click();
                    
                },
                function(el) {
                    if ($(el).parent().hasClass("ui-selected")) {
                        $("#job_context .single").hide();
                        $("#job_context .multi").show();    
                    } else {
                        $("#job_context .single").show();
                        $("#job_context .multi").hide();
                    }
                    
                }
            );
            
        } 
    });
    
    $("table")
    .tablesorter({  widgets: ["zebra", "multiselect", "contextual"],
                    textExtraction: function(node) {
                                    var stuff = $("div", node).html();
                                    if (stuff == null) {
                                      stuff = ""; 
                                    }
                                    return stuff;
                                  },
                    headers: {0: {sorter: false}}
                  })
    .tablesorterPager({ container: $("#pager"),
                        size: 300
                    });

    // Check CheckAll when read all
    $("table").bind("sortEnd", function() { $("#checkAll").attr("checked", false); });
    
    $("#append").click(function() { 
        
        $("table tbody").html("");
        var job_count = 0;
        var sched_hint = '';
        var output_url = '';
        
        // add some html      
        $.getJSON("jobstatus.py?output_format=json", {}, function(jsonRes, textStatus) {
        
            var jobList = new Array();
            var i = 0;
            
            // Grab jobs from json response and place them in jobList.
            for(i=0; i<jsonRes.length; i++) {
                if ((jsonRes[i].object_type == "job_list") && (jsonRes[i].jobs.length >0)) {    
                  jobList = jobList.concat(jsonRes[i].jobs);
                  job_count++;
                }
            }   
    
            // Wrap each json result into html
            $.each(jobList, function(i, item) {
                if (item.schedule_hint != null) {
                    sched_hint = " ("+item.schedule_hint+")";
                } else {
                    sched_hint = "";
                }
                if (item.outputfileslink != null) {
                    output_url = item.outputfileslink.destination;
                } else {
                    output_url = "";
                }
                $("#jm_jobmanager tbody").append("<tr id='"+item.job_id.match(/^([0-9_]+)__/)[1]+"'>"+
                  "<td><div class='sortkey'></div><input type='checkbox' name='job_identifier' value='"+item.job_id+"' /></td>"+
                  "<td><div class='sortkey'>"+item.job_id.match(/^([0-9]+)_/)[1]+"</div>"+item.job_id+"</td>"+                 
                  "<input type='hidden' name='job_output' value='"+output_url+"' />"+
                  "<td><div class='sortkey'>"+item.status+"</div><div class='jobstatus'>"+item.status+sched_hint+"</div></td>"+
                  "<td><div class='sortkey'>"+toTimestamp(item.received_timestamp)+"</div>"+item.received_timestamp+"</td>"+                 
                  "</tr>"                  
                  );

            });
        
        var sorting = [[1,1]]; 
        // Inform tablesorter of new data
        $("table").trigger("update");
        if (job_count>0) {
          $("table").trigger("sorton",[sorting]);
        }
        
      });

    }); 

    $("#append").click();
    
    $("#checkAll").bind("click", function(event) {
        event.stopPropagation();

        $("#jm_jobmanager tbody input[type='checkbox']").attr("checked", $("#checkAll").is(":checked"));
        if ($("#checkAll").is(":checked")) {
            $("#jm_jobmanager tbody tr").addClass("ui-selected");
        } else {
            $("#jm_jobmanager tbody tr").removeClass("ui-selected");
        }
        return true;
    });
    
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
      initialize_main_variables(op_header=False)
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
  title_entry['javascript'] = js_tmpl()
  
  output_objects.append({'object_type': 'header', 'text': 'Job Manager' })
  
  output_objects.append({'object_type': 'html_form', 'text': html_tmpl()})
  
  return (output_objects, status)
