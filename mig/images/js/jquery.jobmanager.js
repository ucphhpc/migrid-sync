/*

  #
  # --- BEGIN_HEADER ---
  #
  # jquery.jobmanager - jquery based job manager
  # Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

*/

/* Enable strict mode to help catch tricky errors early */
var __dummy = "IE requires ANY code first to avoid crash on 'use strict' line";
"use strict";

/* switch on/off console debug globally here */
var enable_debug = false;

/* 
   Make sure we can always use console.X without scripts crashing. IE<=9
   does not init it unless in developer mode and things thus randomly fail
   without a trace.
*/
var noOp = function(){}; // no-op function
if (!window.console || !enable_debug) {
    console = {
        debug: noOp,
        log: noOp,
        warn: noOp,
        error: noOp
    };
}
/* 
   Make sure we can use Date.now which was not available in IE<9
*/
if (!Date.now) {
    Date.now = function now() {
        return new Date().getTime();
    };
}

if (!enable_debug) {
    console.debug = noOp;
} else {
    console.debug = function(msg){ 
        console.log(Date.now()+" DEBUG: "+msg); 
    };
}

if (jQuery) (function($){
  
        // Check if touchscreen interface (left click only) is enabled
        function touchscreenChecker() {
            var touchscreen = $("#jm_touchscreen[type='checkbox']").is(":checked");
            //alert("use touchscreen interface: " + touchscreen);
            return touchscreen;
        }

        // Check if auto refresh is enabled
        function autorefreshChecker() {
            var autorefresh = $("#jm_autorefresh[type='checkbox']").is(":checked");
            //alert("use autorefresh: " + autorefresh);
            return autorefresh;
        }

        function dump(element) {
            /* some browsers support toSource as easy dump */
            if (element.toSource !== undefined) {
                return element.toSource();
            }
            var a = ["Element dump:"];
            a.push("Raw: " + element);
            for (var k in element) {
                if (element.hasOwnProperty(k)) {
                    a.push(k + ": " + element[k]);
                }
            }
            a.push("HTML: " + element.innerHTML);
            return(a.join('\n'));
        }

        function toTimestamp(strDate) {
            return Date.parse(strDate);
        }

        function windowWrapper(el_id, dialog, url) {
            window.open(url);
            $("#cmd_helper div[title='"+el_id+"']").removeClass("spinner").addClass("ok");
            $("#cmd_helper div[title='"+el_id+"'] p").append("<br/>Opened in new window/tab");
            $("#cmd_helper div[title='"+el_id+"']").css("height", "auto");
            return true;
        }

        function jsonWrapper(el_id, dialog, url, jsonOptions) {
        
            var jsonSettings = {output_format: "json"};
    
            $.fn.extend(jsonSettings, jsonOptions);
    
            /* We used to use $.getJSON() here but now some back ends require POST */
            $.post(
                   url,
                   jsonSettings,
                   function(jsonRes, textStatus) {
    
                       var errors = "";
                       var file_output = "";
                       var dir_listings = "";
                       var misc_output = "";
                       var submit_output = "";
                       var success_message = "<br />Success!";
      
                       for(var i = 0; i < jsonRes.length; i++) {
      
                           switch(jsonRes[i]["object_type"]) {
            
                           case "error_text":
                               errors += "<p>Errors:</p>";
                               errors +="<p>"+jsonRes[i].text+"</p>";
                               break;
          
                           case "file_output":
                               file_output += "<p>Contents:</p>";
                               for(var j = 0; j < jsonRes[i].lines.length; j++) {
                                   file_output += jsonRes[i].lines[j];
                               }
                               break;
          
                           case "dir_listings":
            
                               for(j = 0; j < jsonRes[i]["dir_listings"].length; j++) {
                                   dir_listings += jsonRes[i]["dir_listings"][j];
                               }
                               if (dir_listings.length > 0) {
                                   dir_listings = "<p>Directory Listings</p>"+dir_listings;
                               }
                               break;
          
                           case "submitstatuslist":
          
                               for(j = 0; j < jsonRes[i]["submitstatuslist"].length; j++) {
            
                                   if (jsonRes[i]["submitstatuslist"][j]["status"]) {
                                       misc_output +=  "<p>Submitted '" +
                                           jsonRes[i]["submitstatuslist"][j]["name"] +
                                           "'</p><p>Job identfier: '"+
                                           jsonRes[i]["submitstatuslist"][j]["job_id"] +
                                           "'</p>";
                                   } else {
                                       misc_output +=  "<p>Failed submitting:</p><p>" +
                                           jsonRes[i]["submitstatuslist"][j]["name"] + " " +
                                           jsonRes[i]["submitstatuslist"][j]["message"] +
                                           "</p>";
                                   }
            
                               }
              
                               break;
          
                           case "changedstatusjobs":
          
                               for(j = 0; j < jsonRes[i]["changedstatusjobs"].length; j++) {
                                   if (jsonRes[i]["changedstatusjobs"][j]["message"]) {
                                       misc_output += jsonRes[i]["changedstatusjobs"][j]["message"];
                                   } else {
                                       success_message = "<p>Job status changed from '"+ jsonRes[i]["changedstatusjobs"][j]["oldstatus"] + "' to '"+jsonRes[i]["changedstatusjobs"][j]["newstatus"]+"'.</p>";
                                   }
                               }
              
                               break;
          
                           case "saveschedulejobs":
                               for(j = 0; j < jsonRes[i]["saveschedulejobs"].length; j++) {
                                   if (jsonRes[i]["saveschedulejobs"][j]["message"]) {
                                       misc_output += jsonRes[i]["saveschedulejobs"][j]["message"];
                                   } else {
                                       success_message = "<p>Job schedule requested for '"+ jsonRes[i]["saveschedulejobs"][j]["oldstatus"]+"' job.</p>";
                                   }
                               }
                               if (jsonRes[i]["savescheduleinfo"]) {
                                   success_message += '<p>'+jsonRes[i]["savescheduleinfo"]+'</p>';
                               }
                               break;
          
                           case "checkcondjobs":
                               for(j = 0; j < jsonRes[i]["checkcondjobs"].length; j++) {
                                   if (jsonRes[i]["checkcondjobs"][j]["message"]) {
                                       misc_output += jsonRes[i]["checkcondjobs"][j]["message"];
                                   } else {
                                       var cond_item = jsonRes[i]["checkcondjobs"][j];
                                       success_message = "<p><img src='"+cond_item["icon"]+"' /> Job feasibility:<br />" + cond_item["verdict"]+ "<br />";
                                       var err_item = cond_item["error_desc"];
                                       for (var k in err_item) {
                                           success_message += k + "<br /> " + err_item[k] + "<br />";
                                       }
                                       if (cond_item["suggestion"] !== undefined) {
                                           success_message += cond_item["suggestion"] + "<br />";
                                       }
                                   }
                               }
                               break;
          
                           case "resubmitobjs":
                               for(j = 0; j < jsonRes[i]["resubmitobjs"].length; j++) {
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
        
                       if ((errors.length + file_output.length + misc_output.length + dir_listings.length) > 0){
        
                           if (file_output.length > 0) {
                               file_output = "<pre>"+file_output+"</pre>";
                           }
        
                           if (dir_listings.length > 0) {
                               dir_listings = "<pre>"+dir_listings+"</pre>";
                           }
        
                           if ((errors.length > 0) || (misc_output.length > 0)) {
                               $("#cmd_helper div[title='"+el_id+"']").removeClass("spinner").addClass("error");
                           } else {
                               $("#cmd_helper div[title='"+el_id+"']").removeClass("spinner").addClass("ok");
                           }
                           $("#cmd_helper div[title='"+el_id+"'] p").append("<br />"+errors+file_output+misc_output+dir_listings);
        
                       } else {
                           $("#cmd_helper div[title='"+el_id+"']").removeClass("spinner").addClass("ok");
                           $("#cmd_helper div[title='"+el_id+"'] p").append(success_message);
        
                       }
                       $("#cmd_helper div[title='"+el_id+"']").css("height", "auto");
                   }, "json");
      
        }

        $.fn.jobmanager = function(user_options, clickaction) {

            var defaults = {};
            console.debug("define actions");
            var url;
            defaults['actions'] = {
                cancel: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobaction.py", {job_id: job_id, action: 'cancel'});
                },
                freeze: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobaction.py", {job_id: job_id, action: 'freeze'});
                },
                thaw: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobaction.py", {job_id: job_id, action: 'thaw'});
                },
                mrsl: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "mrslview.py", {job_id: job_id});
                },
                resubmit: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "resubmit.py", {job_id: job_id});
                },
                statusfiles: function (job_id) {
                    url = "fileman.py?path=job_output/"+job_id+"/";
                    windowWrapper(job_id, "#cmd_dialog", url);
                },
                outputfiles: function (job_id, job_output) {
                    /* fall back to default fileman if job has no output files */
                    if (job_output === undefined) {
                        url = "fileman.py";
                    } else {
                        url = "fileman.py?"+job_output.match(/^ls.py\?(.*)$/)[1];
                    }
                    windowWrapper(job_id, "#cmd_dialog", url);
                },
                liveio: function (job_id) {
                    url = "liveio.py?job_id="+job_id;
                    windowWrapper(job_id, "#cmd_dialog", url);
                },
                schedule: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobschedule.py", {job_id: job_id});
                },
                feasible: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobfeasible.py", {job_id: job_id});
                },
                verbosestatus: function (job_id) {
                    url = "jobstatus.py?flags=v;job_id="+job_id;
                    windowWrapper(job_id, "#cmd_dialog", url);
                },
            };

            var options = $.extend(defaults, user_options);

            function menu_callback(key, call_opts, el) {
                var m = "job menu clicked: " + key;                         
                console.debug = console.log;
                console.debug(m); 
                var action = key;
                if (el === undefined) {
                    el = $(this);
                }
                
                var single_selection = !$(el).parent().hasClass("ui-selected");
                var job_id = "";
                
                $("#cmd_helper").dialog({buttons: {Close: function() {$(this).dialog("close");} }, 
                            width: "800px", 
                            autoOpen: false, 
                            closeOnEscape: true, 
                            position: { my: "top", at: "top+100px", of: window},
                            modal: true
                            });
                $("#cmd_helper").dialog("open");
                $("#cmd_helper").html("");
                
                if (single_selection) {
                          
                    job_id = $("input[name='job_identifier']", $(el).parent()).val();
                          
                    $("#cmd_helper").append("<div class='spinner' title='"+job_id+"' style='padding-left: 20px;'><p>JobId: "+job_id+"</p></div>");
                    // Output files redirect to the filemanager with extra args.
                    // All other actions are handled by the general case.
                    console.debug("call "+action+" with job: "+job_id);
                    if (action === "outputfiles") {
                        options['actions'][action](job_id, $("input[name='job_output']", $(el).parent()).val());
                    } else {
                        options['actions'][action](job_id);
                    }
                } else {
                    var selected_rows = $("#jm_jobmanager tbody tr.ui-selected");
                    $("#cmd_helper").append("<p>"+action+": "+selected_rows.length+" jobs, see individual status below:</p>");
                    selected_rows.each(function(i) {
                            job_id = $("input[name='job_identifier']", this).val();
                            $("#cmd_helper").append("<div class='spinner' title='"+job_id+"' style='padding-left: 20px;'><p>"+job_id+"</p></div>");
                            options['actions'][action](job_id);
                        });
                }
                
                $("#pagerrefresh").click();
                      
            }

            function doubleClickEvent(el) {
                if (clickaction !== undefined) {
                    clickaction(event);
                    return;
                } 
                // if no clickaction is provided, default to opening raw description
                var job_id = $("input[name='job_identifier']", $(el).parent()).val();
                console.debug("in dclick handler with job: "+job_id);
                menu_callback("mrsl", null, $(el));
                console.debug("done in dclick handler with job: "+job_id);
            }

            function bindContextMenus() {
                /* Bind context menu for job elements */
                var job_menu = {
                    "resubmit": {name: "Resubmit", icon: "resubmit"},
                    "freeze": {name: "Freeze", icon: "freeze"},
                    "thaw": {name: "Thaw", icon: "thaw"},
                    "cancel": {name: "Cancel", icon: "cancel"},
                    "sep1": "---------",
                    "mrsl": {name: "Raw Description", icon: "mrsl"},
                    "schedule": {name: "Schedule Status", icon: "schedule"},
                    "feasible": {name: "Feasibility Check", icon: "feasible"},
                    "verbosestatus": {name: "Verbose Status", icon: "verbosestatus"},
                    "sep2": "---------",
                    "liveio": {name: "Live I/O", icon: "liveio"},
                    "statusfiles": {name: "Status Files", icon: "statusfiles"},
                    "outputfiles": {name: "Output Files", icon: "outputfiles"}
                };
                var bind_click = 'right';
                if (touchscreenChecker()) {
                    bind_click = 'left';
                }
                $.contextMenu({
                        selector: '#jm_jobmanager tbody tr td:not(.checkbox)', 
                        trigger: bind_click,
                        callback: menu_callback,
                        items: job_menu
                    });

            }

            console.debug("add tablesorter multiselect widget");
      
            $.tablesorter.addWidget({
                    id: "multiselect",
                        format: function(table) {
                        $("#jm_jobmanager").on("click", "tbody tr td input", 
                                               function(event) {
                                                   var job_id = $(this).parent().parent().attr("id");
                                                   var is_checked = $("#"+job_id+" input").prop("checked");
                
                                                   if (is_checked) {
                                                       $("#"+job_id).addClass("ui-selected");
                                                   } else {
                                                       $("#"+job_id).removeClass("ui-selected");
                                                   }
                                                   return true;
                                               });            
                    }
                });
    
            console.debug("add tablesorter contextual widget");
            $.tablesorter.addWidget({ 
                    id: "contextual", 
                        format: function(table) {
                        bindContextMenus();
                    }
                });
    
            console.debug("init job manager");
            var config = {container: $("#pager"), size: 300};
            var doSort = true;
            $("#jm_jobmanager")
            .tablesorter({  widgets: ["zebra", "multiselect", "contextual", "saveSort"],
                        textExtraction: function(node) {
                        var stuff = $("div", node).html();
                        if (stuff === undefined) {
                            stuff = "";
                        }
                        return stuff;
                    },
                        sortColumn: 'Job ID',
                        headers: {0: {sorter: false}}
                })
            .tablesorterPager(config);

            console.debug("bind handlers");
            // Check CheckAll when read all
            $("#jm_jobmanager").bind("sortEnd", function() { $("#checkAll").prop("checked", false); });

            $("#pagerrefresh").click(function() {

                    // Busy marker while loading jobs from server
                    $("#jm_jobmanager tbody").html("<tr class='odd'><td class='wait'></td><td>Loading jobs...</td><td></td><td></td></tr>");
                    var job_count = 0;
                    var sched_hint = '';
                    var output_url = '';
                    var max_jobs = -1;
                    var filter_id = '';
                    var limit_opts = 'flags=i;';

                    // Read out current max jobs and filter settings from fields
                    max_jobs = parseInt($(".maxjobs", config.container).val());
                    if (max_jobs > 0) {
                        limit_opts += "flags=s;max_jobs=" + max_jobs + ';';
                    }
                    filter_id = $(".filterid", config.container).val();
                    if (filter_id !== '') {
                        limit_opts += "job_id=" + filter_id + ';';
                    }
                    // add some html
                    $.ajax({
                            url: "jobstatus.py?output_format=json;"+limit_opts, 
                                type: "GET",
                                dataType: "json",
                                cache: false, // Avoid IE caching
                                success: 
                            function(jsonRes, textStatus) {
                                var jobList = [];
                                var i = 0;
                          
                                // Grab jobs from json response and place them in jobList.
                                for(i = 0; i < jsonRes.length; i++) {
                                    if ((jsonRes[i].object_type === "job_list") && (jsonRes[i].jobs.length > 0)) {
                                        jobList = jobList.concat(jsonRes[i].jobs);
                                        job_count++;
                                    }
                                }
                          
                                // Remove busy marker
                                $("#jm_jobmanager tbody").html("");
                                // Wrap each json result into html
                                $.each(jobList, function(i, item) {
                                        if (item.schedule_hint !== undefined) {
                                            sched_hint = " ("+item.schedule_hint+")";
                                        } else {
                                            sched_hint = "";
                                        }
                                        if (item.outputfileslink !== undefined) {
                                            output_url = item.outputfileslink.destination;
                                        } else {
                                            /* dummy value of user home for jobs without output files */
                                            output_url = "ls.py?path=";
                                        }
                                        $("#jm_jobmanager tbody").append("<tr id='"+item.job_id.match(/^([0-9_]+)__/)[1]+"'>"+
                                                                         "<td class='checkbox'><div class='sortkey'></div><input type='checkbox' name='job_identifier' value='"+item.job_id+"' /></td>"+
                                                                         "<td><div class='sortkey'>"+item.job_id.match(/^([0-9]+)_/)[1]+"</div>"+item.job_id+"</td>"+
                                                                         "<input type='hidden' name='job_output' value='"+output_url+"' />"+
                                                                         "<td><div class='sortkey'>"+item.status+"</div><div class='jobstatus'>"+item.status+sched_hint+"</div></td>"+
                                                                         "<td><div class='sortkey'>"+toTimestamp(item.received_timestamp)+"</div>"+item.received_timestamp+"</td>"+
                                                                         "</tr>"
                                                                         );

                                    });

                                var sorting = [[1,1]];
                                // Inform tablesorter of new data
                                $("#jm_jobmanager").trigger("update");
                                // NOTE: disabled now that we use saveSort widget
                                if (doSort)  { // only first time now that we use saveSort
                                    // Disabled explicit sort as it breaks zebra-coloring for some reason
                                    //    if (job_count > 0) {
                                    //        $("#jm_jobmanager").trigger("sorton", [sorting]);
                                    //    }
                                    doSort = false;
                                }
                            }
                        });
                });

            $("#pagerrefresh").click();

            /* refresh when pressing enter in the filter input box */
            $("input.filterid").keypress(function (e) {
                    if (e.which === 13) {
                        $("#pagerrefresh").click();
                        return false;
                    }
                });

            console.debug("add dclick handler");
            //$("#jm_jobmanager").off("dblclick", "tbody tr td:not(.checkbox)");
            $("#jm_jobmanager").on("dblclick", 
                                   "tbody tr td:not(.checkbox)",
                                   function(event) {
                                       console.debug("in dclick handler: "+$(this));
                                       doubleClickEvent(this);
                                       console.debug("done dclick handler: "+$(this));
                                   }); 


            $("#checkAll").bind("click", function(event) {
                    event.stopPropagation();

                    $("#jm_jobmanager tbody input[type='checkbox']").prop("checked", $("#checkAll").is(":checked"));
                    if ($("#checkAll").is(":checked")) {
                        $("#jm_jobmanager tbody tr").addClass("ui-selected");
                    } else {
                        $("#jm_jobmanager tbody tr").removeClass("ui-selected");
                    }
                    return true;
                });

            // bind reload to touchscreen checkbox
            console.debug("bind reload to touchscreen checkbox");
            $("#jm_touchscreen[type='checkbox']").on('click',
                                                     function() {
                                                         /* Remove old context menu and reload */
                                                         $.contextMenu('destroy');
                                                         bindContextMenus();
                                                     });

            // Auto refresh every 60 seconds
            var refresh_delay = 60000;
            function refreshHandler() {
                if (autorefreshChecker()) {
                    //console.debug("do refresh");
                    $("#pagerrefresh").click();
                }
                setTimeout(refreshHandler, refresh_delay);
            }
            console.debug("start autorefresh handler");
            setTimeout(refreshHandler, refresh_delay);

        };

    })(jQuery);
