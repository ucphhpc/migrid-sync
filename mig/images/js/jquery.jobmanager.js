if (jQuery) (function($){
  
    // Use touchscreen interface without need for right clicking
    function touchscreenChecker() {
        var touchscreen = $("#jm_touchscreen input[type='checkbox']").is(":checked");
        //alert("use touchscreen interface: " + touchscreen);
        return touchscreen;
    }

  function toTimestamp(strDate) {
      return Date.parse(strDate);
  }

  function windowWrapper(el_id, dialog, url) {
    window.open(url);
    $("#cmd_helper div[title="+el_id+"]").removeClass("spinner").addClass("ok");
    $("#cmd_helper div[title="+el_id+"] p").append("<br/>Opened in new window/tab");
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
            for(j = 0; j < jsonRes[i].lines.length; j++) {
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
                misc_output +=  "<p>Submitted '"
                            + jsonRes[i]["submitstatuslist"][j]["name"]
                            + "'</p>"
                            + "<p>Job identfier: '"+jsonRes[i]["submitstatuslist"][j]["job_id"]
                            + "'</p>";
              } else {
                misc_output +=  "<p>Failed submitting:</p><p>"
                            + jsonRes[i]["submitstatuslist"][j]["name"]
                            + " "+jsonRes[i]["submitstatuslist"][j]["message"]
                            + "</p>";
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
	    if (jsonRes[i]["savescheduleinfo"])
		success_message += '<p>'+jsonRes[i]["savescheduleinfo"]+'</p>';
          break;
          
          case "checkcondjobs":
            for(j = 0; j < jsonRes[i]["checkcondjobs"].length; j++) {
              if (jsonRes[i]["checkcondjobs"][j]["message"]) {
                misc_output += jsonRes[i]["checkcondjobs"][j]["message"];
              } else {
		  var cond_item = jsonRes[i]["checkcondjobs"][j];
                success_message = "<p><img src='"+cond_item["icon"]+"' /> Job feasibility:<br />" + cond_item["verdict"]+ "<br />";
		  var err_item = cond_item["error_desc"];
		  for(var k in err_item) {
		      success_message += k + "<br /> " + err_item[k] + "<br />";
		  }
		  if (cond_item["suggestion"] != null) {
		      success_message += cond_item["suggestion"] + "<br />"
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
          $("#cmd_helper div[title="+el_id+"]").removeClass("spinner").addClass("error");
        } else {
          $("#cmd_helper div[title="+el_id+"]").removeClass("spinner").addClass("ok");
        }
        
        $("#cmd_helper div[title="+el_id+"] p").append("<br />"+errors+file_output+misc_output+dir_listings);
        
      } else {
        $("#cmd_helper div[title="+el_id+"]").removeClass("spinner").addClass("ok");
        $("#cmd_helper div[title="+el_id+"] p").append(success_message);
        
      }      
    }, "json");
      
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
                    jsonWrapper(job_id, "#cmd_dialog", "jobaction.py", {job_id: job_id, action: 'cancel'})
                },
                freeze: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobaction.py", {job_id: job_id, action: 'freeze'})
                },
                thaw: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobaction.py", {job_id: job_id, action: 'thaw'})
                },
                mrsl: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "mrslview.py", {job_id: job_id})
                },
                resubmit: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "resubmit.py", {job_id: job_id})
                },
                statusfiles: function (job_id) {
                    url = "fileman.py?path=job_output/"+job_id+"/";
                    windowWrapper(job_id, "#cmd_dialog", url);
                },
                outputfiles: function (job_id, job_output) {
                    url = "fileman.py?"+job_output.match(/^ls.py\?(.*)$/)[1];
                    windowWrapper(job_id, "#cmd_dialog", url);
                },
                liveio: function (job_id) {
                    url = "liveio.py?job_id="+job_id;
                    windowWrapper(job_id, "#cmd_dialog", url);
                },
                schedule: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobschedule.py", {job_id: job_id})
                },
                feasible: function (job_id) {
                    jsonWrapper(job_id, "#cmd_dialog", "jobfeasible.py", {job_id: job_id})
                },
                verbosestatus: function (job_id) {
                    url = "jobstatus.py?flags=v;job_id="+job_id;
                    windowWrapper(job_id, "#cmd_dialog", url);
                },
            };

            $("#jm_jobmanager tbody tr td").contextMenu({ menu: "job_context", 
							  leftButtonChecker: touchscreenChecker},
                function(action, el, pos) {
                    
                    var single_selection = !$(el).parent().hasClass("ui-selected");
                    var job_id = "";
                    
                    $("#cmd_helper").dialog({buttons: {Close: function() {$(this).dialog("close");} }, width: "800px", autoOpen: false, closeOnEscape: true, modal: true, position: [300, 70]});
                    $("#cmd_helper").dialog("open");
                    $("#cmd_helper").html("");
                    
                    if (single_selection) {
                    
                        job_id = $("input[name=job_identifier]", $(el).parent()).val();
                        
                        $("#cmd_helper").append("<div class='spinner' title='"+job_id+"' style='padding-left: 20px;'><p>JobId: "+job_id+"</p></div>");
                        // Output files redirect to the filemanager with extra args.
                        // All other actions are handled by the general case.
                        if (action == "outputfiles") {
                          actions[action](job_id, $("input[name=job_output]", $(el).parent()).val());
                        } else {
                          actions[action](job_id);
                        }
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
    
    $("#jm_jobmanager")
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
    $("#jm_jobmanager").bind("sortEnd", function() { $("#checkAll").attr("checked", false); });
    
    $("#append").click(function() {

        // Busy marker while loading jobs from server
        $("#jm_jobmanager tbody").html("<tr class='odd'><td class='wait'></td><td>Loading jobs...</td><td></td><td></td></tr>");
        var job_count = 0;
        var sched_hint = '';
        var output_url = '';
        var max_jobs = -1;
        var filter_id = '';
        var limit_opts = '';

        // Read out current max jobs and filter settings from fields
        max_jobs = parseInt($(".maxjobs", config.container).val());
        if (max_jobs > 0) {
            limit_opts += "flags=s;max_jobs=" + max_jobs + ';';
        }
        filter_id = $(".filterid", config.container).val();
        if (filter_id != '') {
            limit_opts += "job_id=" + filter_id + ';';
        }
        // add some html
        $.getJSON("jobstatus.py?output_format=json;"+limit_opts, {}, function(jsonRes, textStatus) {
        
            var jobList = new Array();
            var i = 0;
            
            // Grab jobs from json response and place them in jobList.
            for(i = 0; i < jsonRes.length; i++) {
                if ((jsonRes[i].object_type == "job_list") && (jsonRes[i].jobs.length > 0)) {
                  jobList = jobList.concat(jsonRes[i].jobs);
                  job_count++;
                }
            }
    
            // Remove busy marker
            $("#jm_jobmanager tbody").html("");
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
                    /* dummy value of user home for jobs without output files */
                    output_url = "ls.py?path=";
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
        $("#jm_jobmanager").trigger("update");
        if (job_count > 0) {
          $("#jm_jobmanager").trigger("sorton", [sorting]);
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
  
})(jQuery);
