/*

#
# --- BEGIN_HEADER ---
#
# jquery.migtools - jquery based helpers for e.g. portals
# Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

# This is a modified version of the Matlab Grid service by Jost Berthold.
# Original license headers follow below.

*/

var todo="TODO:\n"
	 + "-add scheduling-related parameters to dialogs\n"
	 + " (CPU time estimate, or just a switch \"Low priority job\")\n"
	 + " we can model N priorities through REs \"Prio-N\" "
	             + "and give numeric priorities\n"
	 + " Jobs are classified by a given maximum time in minutes,\n"
	 + " and into classes defined in a global configuration variable.\n"
	 + "\n-------------------------------------\n"
	 + "-compile with options -R -nojvm -R -nodisplay (after -m)?\n"
         + "-store global variables in a json file, and matlab_e, matlab_c\n"
         + "-add CPUtime field to submit dialog? (high default for now)\n"
         ;

/*
# (C) 2010 Jost Berthold (berthold at diku.dk), grid.dk
#          E-science Center, Copenhagen University
# This file is part of MatLab Grid Service.
# 
# MatLab Grid Service is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# MatLab Grid Service is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

/* Some global variables, initialised nby corresponding html
 *   app_list_body:  id to fill/refresh table of compiled applications
 *   compiled_dir:   where the compilation output is stored
 *   run_output_dir: where the run output is stored
 */
var app_list_body;
var out_list_body;
var compiled_dir;
var run_output_dir;
var priority_classes = []; // one class (unlimited) in default

/* submit one job given as a dictionary. EXECUTE must be defined,
 * no field names unknown to MiG mRSL should be given.
 *
 * Arguments: job dictionary, callbacks for success and error case
 * Returns: nothing.
 */ 
function mig_submit_dict(dict, callback_ok, callback_error) {
    /* take the result of a job submission, extract the job-ID if
     * successful, all error messages otherwise. Only one job
     * submission is expected, not multiple results.
     *
     * Arguments: json result of job submission (submitfields.py)
     * Returns (boolean,string), with String being either a job_id
     * or a concatenation of error messages enclosed in <p>..</p>
     */
    function extract_result(jsonRes) {
        var errors="";
        var job_id="";
        for(var i=0; i<jsonRes.length; i++) {
            switch(jsonRes[i]["object_type"]) {
            case "error_text":
                errors +="<p>"+jsonRes[i].text+"</p>";
                break;
            case "submitstatuslist":
                // we only expect one job, not several
                if (jsonRes[i]["submitstatuslist"].length > 1) {
                    errors += "<p>Unexpected: multiple submission results</p>";
                    break;
                }
                if (jsonRes[i]["submitstatuslist"][0]["status"]) {
                    job_id = jsonRes[i]["submitstatuslist"][0]["job_id"];
                } else {
                    errors += "<p>" 
                           + jsonRes[i]["submitstatuslist"][0]["message"] 
                           + "</p>";
                }
                break;
            case "text":
                errors += "<p>" + jsonRes[i]["text"] + "</p>";
                break;
            default:
                // skip
            }
            // stop as soon as job_id is found
            if (job_id != "") {
                return [true,job_id];
            }
        }

        // we reach here, so no job_id has been found
        if (errors == "") {
            errors = "<p>Invalid reply (no job id, no errors)</p>";
        }
        return [false, errors];
    }

    // make sure we have an "EXECUTE" field
    if (dict.EXECUTE == undefined || dict.EXECUTE == "") {
        callback_error("<p>No EXECUTE sequence given.</p>");
        return;
    }

    // do the job submission
    $.post("submitfields.py", dict, 
              function(reply, statusText) {
                  var res = extract_result(reply);
                  var success = res[0];
                  var message = res[1];
                  if (success) {
                      callback_ok(message);
                  } else {
                      callback_error(message);
                  }
    }, "json");
    return;
}

/* *********************************************/
/* submission of a compilation job
 * 
 * Uses fixed naming scheme for fields in the web form:
 *   #file_name    - path to main Matlab file, checked to match "*.m"
 *   #output_name  - name for executable, default: basename of main file
 *   #other_names  - component files to provide for compilation
 *   #target_arch  - target architecture, goes into mRSL unmodified
 *
 * Global variables assumed:
 *   the_vgrid, for file input and output
 *   matlab_c, name of runtime env providing MCC (MatLab compiler)
 */
function compile_submit() { 

    var abort = false;

    if (the_vgrid == undefined || matlab_c == undefined) {
        alert("Setup error: VGrid or Runtime Env. unknown.");
        return;
    }

    var file_name = $( "#file_name" )[0].value;
    
    // check and truncate file name
    if (file_name == "") {
        alert("Error: No file to compile given.");
        return;
    }
    var match = file_name.match(/^(.*\/)?([^\/]+)\.m$/);
    var base_name;
    if (match == null) {
        alert(file_name + ": invalid name (should end in \".m\")");
        return;
    } else {
        base_name = match[2];
    }
    
    // use explicit output destination if given
    var output_name = base_name;
    match = $( "#output_name" )[0].value;
    if (match != "") {
        output_name = match;
    }

    // check for valid output name
    match = output_name.match(/^[a-zA-Z_][a-zA-Z0-9_]*$/);
    if (match == null) {
            alert("Invalid name `" + output_name + "' for output.\n"
                + "Must begin with a letter or '_' and contain "
                + "only alpha-numeric characters or '_'.\n"
                + "\nIf your main Matlab file has an inconvenient "
                + "name, use a different output name.");
            return;
    }

    // write back the instrument to the output dir
    //   executable, run script, an info file
    var suffix = ["", ".sh", ".info"];
    var out_files = ""; // will build multiline string OUTPUTFILES
    var i;
    for (i=0; i < suffix.length; i++) {
        var n = output_name + suffix[i];
        out_files += n + "\t" + compiled_dir + n + "\n";
    }

    var arch=$( "#target_arch" )[0].value || "X86"; // just in case...
    
    var files_raw   = ($( "#other_names" )[0].value || "").split("\n");
    var extra_files = [];
    var extra_names = "";
    $.each(files_raw, function(i,str) {
               if (str == "") { // ignore empty lines
                    return true;
               }
               if (str.match(/[\t ]/)) {
                   alert("Warning: Ignoring file name with space (\"" 
                         + str + "\")");
                   return true;
               }
               var base = str.match(/\/([^/]+$)/);
               if (base != undefined) {
                   extra_files.push(str + "\t " + base[1]);
                   extra_names += ", \"" + base[1] + "\"";
               } else {
                   extra_files.push(str);
                   extra_names += ", \"" + str + "\"";
               }
               return true;
           });

    extra_names = extra_names.replace(/^, /,"");

    var in_files = file_name + " " + base_name + ".m\n" 
                   + extra_files.join("\n");

// compilation only, did not work..
//     var exec = "$MCC -c -W main " + base_name + ".m " + extra_names + "\n"
//        + "(echo \"<html><head/><body><pre>\"; cat run_" + base_name +".sh; echo \"</pre></body></html>\") > " + base_name + ".html\n";
// compilation, linking, and writing a json info file
     var exec = "$MCC -o " + output_name + " -m " 
                      + base_name + ".m " 
                      + extra_names.replace(/[",]/g,"") + "\n"
        + "echo '{ \"arch\": \"" + arch + "\",' "
                + "> " + output_name + ".info\n" 
        + "[ -f \"run_" + output_name + "\" ] || "
	        + "echo '  \"comment\": \"Compilation +JOBID+ failed\",' "
                + ">> " + output_name + ".info\n"
        + "echo '  \"name\": \"" + output_name + "\",' "
                + ">> " + output_name + ".info\n"
        + "echo '  \"source\": \"" + file_name + "\",' "
                + ">> " + output_name + ".info\n"
        + "echo '  \"other_files\": [" + extra_names + "]}' "
                + ">> " + output_name + ".info\n"
        + "mv run_" + output_name + ".sh " + output_name + ".sh\n";


    var dict = {"output_format":"json",
                "RUNTIMEENVIRONMENT": matlab_c,
                "VGRID": "ANY",
                "JOBNAME":"compile-" + base_name,
                "OUTPUTFILES": out_files,
                "INPUTFILES" : in_files,
                "EXECUTE":exec,
                "ARCHITECTURE": arch,
               };

/* DEBUG 
    var msg = "Job will be this:\n";
    var keys = ["output_format", "RUNTIMEENVIRONMENT", "JOBNAME", "OUTPUTFILES", "INPUTFILES", "EXECUTE", "ARCHITECTURE" ];
    $.each (keys, function(i,k) {
        msg += k + ": " + dict[k] + "\n-----------\n";
    });
    alert(msg);
    return;
/* */
    
    mig_submit_dict(dict, 
         // callback for success:
         function(job_id) {
	     // write a temp json file to the compiled directory
	     var json = "{ \"arch\": \"" + arch
		        + "\", \"name\": \"" + output_name 
		        + "\", \"source\": \"" + file_name 
		        + "\", \"other_files\": [" + extra_names + "]"
			+ ", \"comment\": \"Pending Job: " + job_id +"\"}\n";
	     // if writing it out goes wrong, we cannot do much. 
	     $.post("editfile.py", {
			   "path": compiled_dir + output_name + ".info",
			   "editarea": json,
			   "output_format": "json",
		       }, function(reply, statusText) {
			   list_refresh();
		       }, "json");
	     // write status message
	     var files = base_name + ".m";
	     if (extra_names != "") {
		 files += " and " + extra_names.replace(/"/g,"");
	     }
             $( "#result" ).append("Compilation of " + files
				   + ". Job is: " 
                                   + job_id + "<br/>");
         },
         // callback for errors
         function(errors) {
             $( "#result" ).append("<div class='errortext'>"
				   + "Submission failed for compiling "
				   + base_name + ".m<br/>"
				   + "Errors: " 
                                   + errors + "</div><br/>");
         });
        
    return;
}

/* list_refresh reads directory contents from the compiled directory,
 * then, for each file *.info, reads that file as json and 
 * turns its information into a table row appended to the ID tbody.
 * 
 * compiled_dir is assumed to be an accessible directory on the MiG server, 
 * the *.info files in it are assumed to contain information generated
 * by the compilation (see above): arch, name, source, other_files.
 */

function list_refresh() { 

    if ( (app_list_body && compiled_dir) == undefined ) {
	alert("Setup error: list of executables not defined.");
    }

    if ( $( app_list_body ).is(":hidden")) {
	// no need to refresh what we do not see
	return;
    }

    // delete all
    $( app_list_body ).empty();

    // read directory using mig "ls" and extract info files
    // returns (success::bool, result) where result is the error msg
    // as a singleton string list if no success
    function extract_info_files(jsonRes) {
        var errors="";
        var result=[];
        for(var i=0; i<jsonRes.length; i++) {
            switch(jsonRes[i]["object_type"]) {
            case "error_text":
                errors +="<p>"+jsonRes[i].text+"</p>";
                break;
            case "file_not_found":
                errors += "<p>Path not found!</p>";
                break;
            case "dir_listings":
                
                var list = jsonRes[i]["dir_listings"];
                if (list == []) {
                    errors += "<p>Empty result received.</p>";
                    break;
                } else {
                    // use first listing only, select entries
                    list = list[0]["entries"];
                    
                    for (var j=0; j < list.length; j++) {
                        if (list[j]["type"] == "file"
                            && list[j]["name"].match(/.*\.info$/)) {
                            result.push(list[j]["file_with_dir"]);
                        }
                    }
                    // done, since we expect exactly one "dir_listings"
                    return [true, result];
                }

            case "text":
                errors += "<p>" + jsonRes[i]["text"] + "</p>";
                break;
                
            default:
                break;
                // skip
            }
        }
        // if we reach here, something was wrong with the result
        return[false, [errors]];
    }

    function appendRow(infos) {
        var row = "<tr>";

        // this is not used; invalid json is filtered out before.
        if (!infos) {
            $( app_list_body ).append("<tr><td colspan=\"5\">(file invalid)"); 
            return true;
        }
        row += "<td>" + infos["name"];
        row += "<td>" + infos["source"];
	if (infos["other_files"].length > 0) {
	    row += " (and " + infos["other_files"] + ")";
	}
        row += "<td>" + infos["arch"];
	
        row += "<td><input type=\"submit\" " + "value=\"Delete\" "
		+ "onclick=\"rm_compiled('" + infos["name"] + "\')\">" 
	        + "</input>";
	if (infos["comment"] == undefined) {
            row += "<td><input type=\"submit\" "
		+ "value=\"Submit job\" "
		+ "onclick=\"do_run_dialog('" 
                  + infos["name"] + "\', \'" + infos["arch"] + "\')\">"
		+ "</input>&nbsp;&nbsp;";
            row += "<input type=\"submit\" "
		+ "value=\"Do a parameter sweep\" "
		+ "onclick=\"do_sweep_dialog('" 
                  + infos["name"] + "\', \'" + infos["arch"] + "\')\">"
		+ "</input>";
	} else {
	    row += "<td style=\"font-size:smaller\">" + infos["comment"];
	}

        $( app_list_body ).append(row);
        return true;
    }

    $.post("ls.py", { "path": compiled_dir, "output_format": "json"},
              function(reply, statusText) {
                  var res = extract_info_files(reply);
                  if (res[0]) { // success
                      $.each(res[1], function(i, path) {
                                 $.post("/cert_redirect/" + path, {},
                                           function(reply, statusText) {
                                               appendRow(reply);
                                           }, "json");
                             });
                  } else {
                      $( app_list_body ).append("<tr><td colspan=\"5\">" 
					    + res[1][0]);
                      return;
                  }
              }, "json");
    return;
}
              

/* Running a precompiled application.
 * 
 * This function expects an initialised dialog "run_dialog" on the page,
 * which contains a run_text div and a run_args field to read out.
 * list_refresh creates buttons calling this function for every entry.
 * When valid data is supplied, it submits a job to run the file with 
 * given arguments (in a subdirectory) and retrieve produced output.
 * 
 * Arguments: 
 *   name - Name of the compiled Matlab code (in "compiled/")
 *   arch - Architecture for which the code was compiled
 * 
 * Uses fixed naming scheme for a pre-initialised dialog on the page:
 *   #run_dialog  - the dialog, containing the following
 *   #run_text    - text (should mention name and architecture for executable)
 *   #run_limit   - max runtime in minutes
 *   #run_args    - input line for arguments
 *   #run_infiles - text area with input files
 *   #run_result  - section on page where the results should go
 * 
 * Global variables assumed:
 *   the_vgrid, for file input and output
 *   matlab_e, name of runtime env providing MCR (MatLab Compiler Runtime)
 */ 

function do_run_dialog(name, arch) {

    if ( (matlab_e && run_output_dir && compiled_dir) == undefined) {
        alert("Setup error: not configured.");
        return;
    }

    $( "#run_text").html("Run the compiled application " 
                         + name + "(on " + arch + " architecture):<br>");

    var output_zip   = "+JOBNAME+-+JOBID+.zip";

    // set up the MRSL dictionary for the job and callbacks for
    // error and success, then use mig_submit_dict.
    // Run arguments will replace string "ARGUMENTS" inside handler below.
    // Input files section will be parsed and added to dictionary.
     var dict = {"output_format":"json",
                "RUNTIMEENVIRONMENT": matlab_e,
                "VGRID": "ANY",
                "JOBNAME":"run-" + name,
                "OUTPUTFILES": output_zip + " " + run_output_dir + output_zip,
                "EXECUTABLES": compiled_dir + name + ".sh "
                                    + "+JOBID+/" + name + ".sh\n" +
                               compiled_dir + name + " "
                                    + "+JOBID+/" + name + "\n",
                "EXECUTE": [ "cd +JOBID+", 
                             "./" + name + ".sh $MCR ARGUMENTS",
                             "cd ..",
			     "cp +JOBID+.std* +JOBID+",
			     "rm -f  +JOBID+/" + name 
			         + " +JOBID+/" + name + ".sh"
			         + " +JOBID+/+JOBID+.status"
				 + " +JOBID+/joblog",
                             "zip " + output_zip + " +JOBID+/*"
                             ].join("\n"),
                "ARCHITECTURE": arch
               };

    function make_extra_files(files_raw) {
	
	// add input files, if any given. Return a multiline string.
	var extra_files = [];
	$.each(files_raw, function(i,str) {
               if (str == "") { // ignore empty lines
                    return true;
               }
               if (str.match(/[\t ]/)) {
                   alert("Warning: Ignoring file name with space (\"" 
                         + str + "\")");
                   return true;
               }
               var base = str.match(/\/([^/]+$)/);
               if (base != undefined) {
                   extra_files.push(str + "\t +JOBID+/" + base[1]);
               } else {
                   extra_files.push(str + "\t +JOBID+/" + str);
               }
               return true;
        });
	return extra_files.join("\n");
    }

    function clear_close() {
	$("#run_text").empty();
	$("#run_limit")[0].value="";
        $("#run_args")[0].value="";
	$("#run_infiles")[0].value="";
        $("#run_dialog").dialog("close");
    }

    $( "#run_dialog").dialog("option", "buttons", {
              "Cancel": function() { 
		  clear_close();
              },
              "Run": function() { 
                  var args = $("#run_args")[0].value || "";
		  var files_raw 
		      = ($( "#run_infiles" )[0].value || "").split("\n");

		  // time_limit is max.time for the job, in minutes
		  var prio_class = 0;
		  var time_limit
                      = new Number($("#run_limit")[0].value || "0");

		  if (time_limit > 0) {
		      dict["CPUTIME"] = 60 * time_limit;
		      // classify the job (for priority queues)
		      while (prio_class < priority_classes.length 
			     && dict["CPUTIME"] <= 
			     60 * priority_classes[ prio_class ] ) {
 				 prio_class++;
			     }
		      // would be nice to specify priorities like this
		      // classification somewhere with the job dictionary
		  }

                  dict["EXECUTE"] = 
                      dict["EXECUTE"].replace(/ARGUMENTS/,args);
		  dict["INPUTFILES"] = make_extra_files(files_raw);
                                  
                         /* DEBUG 
                         var msg = "Job will be this:\n";
                         var keys = ["output_format", "RUNTIMEENVIRONMENT", "JOBNAME", "OUTPUTFILES", "INPUTFILES", "EXECUTABLES", "EXECUTE", "ARCHITECTURE" ];
                         $.each (keys, function(i,k) {
                                           msg += k + ": " + dict[k] + "\n-----------\n";
                                       });
                         alert(msg);
                         /* */

                         // mig_submit_dict(the_job,...)
                         mig_submit_dict(dict, 
                              function(job_id) {
				  output_zip = "run-" + name + "-" 
				               + job_id + ".zip";
                                  $( "#run_result" ).append("Running " 
                                          + name + ". Job ID is " + job_id
					  + ". Output file: " 
                                          + "<a href='/cert_redirect/"
					  + run_output_dir + output_zip
					  + "' target='_blank'>" 
					  + output_zip + "</a><br/>");
                              },
                              function(errors) {
                                  $( "#run_result" ).append(
                                          "<div class='errortext'>"
                                          + "<h4>Errors:</h4>"
                                          + errors + "</div>");
                              });

		              clear_close();
                     }
               });

    $( "#run_dialog").dialog("open");
}

/* Deleting items from the list of compiled applications
 *  
 * This is done using the mig rm.py handler. Since we generate the 
 * calls ourselves, no attempts to restrict or check for failures.
 */
function rm_compiled(name) {
    
    if ( compiled_dir == undefined) {
        alert("Setup error: directory not configured.");
        return;
    }

    var yes = confirm("Delete " + name + " from compiled applications?");

    if (yes) {
	var files = [compiled_dir + name, 
		     compiled_dir + name + ".sh", 
		     compiled_dir + name + ".info"];
	// weird hack: cannot pass several "path" to one call with jquery
	$.each(files, function(i,path) {
		   	$.post("rm.py", { 
				      "output_format" : "json", 
				      "path" : path,
				  }, 
				  function(a,b) { 
				      if (path.match(/.*info$/)) {
					  list_refresh( ); 
				      }
				  }, "json");
	       });
    } 
    
    return;
}


/* out_refresh reads directory contents from the output directory,
 * and creates a list of zip files with hyperlinks, disassembling the names
 * into a table row appended to the out_list_body.
 */

function out_refresh() { 

    if ( (out_list_body && run_output_dir) == undefined ) {
	alert("Setup error: output directory not configured.");
	return;
    }

    if ( $( out_list_body ).is(":hidden")) {
	// no need to refresh what we do not see
	return;
    }

    // delete all entries created by 
    $( out_list_body ).empty();

    // read directory using mig "ls" and extract info files
    // returns (success::bool, result) where result is the error msg
    // as a singleton string list if no success
    function extract_zip_files(jsonRes) {
        var errors="";
        var result=[];
        for(var i=0; i<jsonRes.length; i++) {
            switch(jsonRes[i]["object_type"]) {
            case "error_text":
                errors +="<p>"+jsonRes[i].text+"</p>";
                break;
            case "file_not_found":
                errors += "<p>Path not found!</p>";
                break;
            case "dir_listings":
                
                var list = jsonRes[i]["dir_listings"];
                if (list == undefined || list.length == 0) {
                    errors += "<p>Empty</p>";
                    break;
                } else {
                    // use first listing only, select entries
                    list = list[0]["entries"];
                    
                    for (var j=0; j < list.length; j++) {
                        if (list[j]["type"] == "file"
                            && list[j]["name"].match(/.*\.zip$/)) {
                            result.push(list[j]["name"]);
                        }
                    }
                    // done, since we expect exactly one "dir_listings"
                    return [true, result];
                }

            case "text":
                errors += "<p>" + jsonRes[i]["text"] + "</p>";
                break;
                
            default:
                break;
                // skip
            }
        }
        // if we reach here, something was wrong with the result
        return[false, [errors]];
    }

    function appendRow(index, filename) {
        var row = "<tr>";

	var match = filename.match(/^run-([^-]*)-(.*).zip$/);

	if (match == undefined ) {
	    row += "<td style=\"font-size:x-small\" colspan=\"4\">"
		+ "<a href=\"/cert_redirect/" + run_output_dir + filename 
		+ "\" target=\"_blank\">" 
		+ filename + "</a>  (filename unexpected)";
	} else {
            row += "<td>" + match[1]; // name of application
            row += "<td>" + match[2]; // Job ID
	    
            row += "<td><input type=\"submit\" " + "value=\"Delete\" "
		+ "onclick=\"rm_output('" + match[0] + "\')\">" 
	        + "</input>";
            row += "<td style=\"font-size:x-small\">" 
		+ "<a href=\"/cert_redirect/" + run_output_dir + match[0] 
		+ "\" target=\"_blank\">" + filename + "</a>";
	}

        $( out_list_body ).append(row);
        return true;
    }

    $.post("ls.py", { "path": run_output_dir, "output_format": "json"},
              function(reply, statusText) {
                  var res = extract_zip_files(reply);
                  if (res[0]) { // success
                      $.each(res[1], appendRow );
                  } else {
                      $( out_list_body ).append("<tr><td colspan=\"4\">" 
						+ res[1][0]);
                      return;
                  }
              }, "json");
    return;
}

/* Deleting files from the output directory
 *  
 * Again done using the mig rm.py handler. Won't be called unless file exists.
 */
function rm_output(name) {
    
    if ( run_output_dir == undefined) {
        alert("Setup error: directory not configured.");
        return;
    }

    var yes = confirm("Delete " + name + " from output directory?");

    if (yes) {
	$.post("rm.py", { "output_format" : "json", 
			     "path" : run_output_dir + name,
			   }, 
		  function(a,b) { 
		      out_refresh( ); 
		  },"json");
    } 
    return;
}


/* do_sweep_dialog: Running a parameter sweep for a precompiled application.
 * 
 * Differs from do_run_dialog by a parse of the arguments and an input
 * for the job count. See regexp and comments below for the syntax.
 * Arguments can be either plain or an "enum range".
 * Job count determines how many jobs to create. Each job will have its 
 * own output file.
 * 
 * The maximum runtime is specified in minutes for one call, CPUTIME will
 * be computed as the sum of calls in one job (overhead is ignored!).
 * For the priority classification, we make sure that all jobs get the 
 * same class.
 * 
 *  * This function expects an initialised dialog "sweep_dialog" on the page,
 * which contains a run_text div and a run_args field to read out.
 * list_refresh creates buttons calling this function for every entry.
 * When valid data is supplied, it submits a job to run the file with 
 * given arguments (in a subdirectory) and retrieve produced output.
 * 
 * Arguments: 
 *   name - Name of the compiled Matlab code (in "compiled/")
 *   arch - Architecture for which the code was compiled
 * 
 * Uses fixed naming scheme for a pre-initialised dialog on the page:
 *   #sweep_dialog  - the dialog, containing the following
 *   #sweep_text    - text in dialog
 *   #sweep_args    - input line for arguments, parsed!
 *   #sweep_limit   - max runtime for one call, in minutes
 *   #sweep_jobs    - desired job count (default is 1)
 *   #sweep_infiles - text area with input files
 *   #run_result  - section on page where the results should go
 * 
 * Global variables assumed:
 *   the_vgrid, for file input and output
 *   matlab_e, name of runtime env providing MCR (MatLab Compiler Runtime)
 * 
 */

function do_sweep_dialog(name, arch) {
    
    if ( (matlab_e && run_output_dir && compiled_dir) == undefined) {
        alert("Setup error: not configured.");
        return;
    }

    $( "#sweep_text" ).html("Run a parameter sweep for the application " 
                         + name + "(on " + arch + " architecture):<br>");
    $( "#sweep_jobs" )[0].value="1";

    /* ARGUMENT SYNTAX
     * Arguments can be "plain" or "enum ranges", otherwise they are ignored.
     * 
     *  plain either does not contain squared brackets or is a (single or 
     * double) quoted region:
     */
    var plain = "([^\\[\\]\\s]+|\"[^\"]*\"|'[^']*')";
    /* 
     * An enum range specifies a range of whole numbers by a starting value, 
     * optionally followed by comma and a next value (default is start +- 1),
     * and two dots followed by an end value, enclosed in squared brackets.
     * Whole numbers can be zero, or else may have a sign, then start by 1-9
     * and be followed by any number (or no) digits 0-9.
     */
    var num   = "([+-]?[1-9][0-9]*|0)";
    var range = "\\[" + num + "(," + num + ")?" + "\\.\\." + num + "\\]";
    // portioning argument line into arguments. Global repeated match ("g")
    var matchArgs = new RegExp( plain + "|" + range, "g");
    // matching enum ranges to tell them apart from plain arguments 
    var matchRange = new RegExp ( range ,"");

    function make_sweep_args(jobs, arg_line) {
	/* parse the argument line and identify all ranges
	 * then expand all ranges, then chop into number of jobs
	 * Returns list of list of argument strings.
	 *  outer.length == jobs
	 *  inner.length == ceil(product of range_extension / jobs)
	 */
	
	// list of all arguments that are valid "plain" or "enum range"s
	var args_matched = arg_line.match(matchArgs);

	if (args_matched == undefined) {
	    // no arguments given? at least none we can understand
	    alert("No arguments. Aborting.");
	    return([]);
	}

	var result=[], tmp, args_all = [""]; // to build and split results
	var i,j,k,l;
	for ( i=0; i < args_matched.length; i++ ) {
	    var this_arg;
	    var from, inc, to;
	    var is_range = args_matched[i].match(range);

	    tmp = [];
	    if ( is_range == undefined ) {
		// plain, so only one variant
		for (j = 0; j < args_all.length; j++ ) {
		    tmp.push( args_all[j] + " " + args_matched[i] ); 
		}
	    } else {
		from = new Number(is_range[1]);
		to   = new Number(is_range[4]);
		if (is_range[3] == undefined ) {
		    if (from > to) {
			inc = -1;
		    } else {
			inc = 1; 
		    }
		} else {
		    inc = new Number(is_range[3]) - new Number(is_range[1]);
		}
		// sanity check:
		if (inc == 0 || from < to && inc < 0 || from > to && inc > 0) {
		    alert(is_range[0] + ": Invalid range. Aborting.");
		    return([]);
		}

		for (j = 0; j < args_all.length; j++) {
		    if (from <= to) {
			for ( k=from; k <= to; k += inc ) {
			    tmp.push( args_all[j] + " " + k);
			}
		    } else {
			for ( k=from; k >= to; k += inc ) {
			    tmp.push( args_all[j] + " " + k);
			}
		    }
		}
	    }
	    args_all = tmp;
	}

	// split into as many jobs as requested, taking arguments from
	// the front (keeping the output in order).
	// Some magic to split the jobs evenly
	i = Math.floor(args_all.length / jobs);
	l = args_all.length - jobs * i;
	i = Math.ceil(args_all.length / jobs);
	for (j = 0; j < args_all.length; j+=i ) {
	    tmp = [];
	    // correct target length here for equal distribution
	    if (l == 0) {
		i = Math.floor(args_all.length / jobs);
	    }
	    l--;
	    for (k = 0; k < i; k++) {
		if (args_all[j + k] == undefined) {
		    break;
		}
		tmp.push(args_all[j + k]);
	    }
	    result.push(tmp);
	}
	return ( result );
    }

    var output_zip   = "+JOBNAME+-+JOBID+.zip";

    // other input files, if any. Filled before submitting
    var extra_files = [];

    // maximum runtime for jobs in this sweep. Filled before
    // submitting, equal for all jobs to send them to similar
    // execution units (in case of priority queues).
    var max_time;
    // and assign a priority class for the jobs
    var prio_class = 0;

    // pre and post execution parts
    var preprocess = "cd +JOBID+\n";
    var postprocess= [ "cd ..",
		       "cp +JOBID+.std* +JOBID+",
		       "rm -f  +JOBID+/" + name 
		       + " +JOBID+/" + name + ".sh"
		       + " +JOBID+/+JOBID+.status"
		       + " +JOBID+/joblog",
                       "zip " + output_zip + " +JOBID+/*"
                     ].join("\n");

    function clear_close() {
	$("#sweep_text").empty();
        $("#sweep_args")[0].value="";
	$("#sweep_limit")[0].value="";
	$("#sweep_jobs")[0].value="1";
	$("#sweep_infiles")[0].value="";
	$("#sweep_dialog").dialog("close");
    }

    function add_extra_files(files_raw) {

	// add input files, if any given, to the extra_files list.
	$.each(files_raw, function(i,str) {
               if (str == "") { // ignore empty lines
                    return true;
               }
               if (str.match(/[\t ]/)) {
                   alert("Warning: Ignoring file name with space (\"" 
                         + str + "\")");
                   return true;
               }
               var base = str.match(/\/([^/]+$)/);
               if (base != undefined) {
                   extra_files.push(str + "\t +JOBID+/" + base[1]);
               } else {
                   extra_files.push(str + "\t +JOBID+/" + str);
               }
               return true;
        });
    }

    function submit_part(args) {

	var i;
	// MRSL dictionary template for jobs. EXECUTE is added later
	var dict = {"output_format":"json",
                    "RUNTIMEENVIRONMENT": matlab_e,
                    "VGRID": "ANY",
                    "JOBNAME":"run-" + name,
		    "CPUTIME": max_time,
                    "OUTPUTFILES": output_zip + " " + run_output_dir + output_zip,
		    "INPUTFILES" : extra_files.join("\n"),
                    "EXECUTABLES": compiled_dir + name + ".sh "
                                  + "+JOBID+/" + name + ".sh\n" +
                                  compiled_dir + name + " "
                                  + "+JOBID+/" + name + "\n",
                    "ARCHITECTURE": arch
		   };
	dict["EXECUTE"] = preprocess;
	for (i = 0; i < args.length; i++) {
	    dict["EXECUTE"] += "./" + name + ".sh $MCR " + args[i] + "\n";
	}
	dict["EXECUTE"] += postprocess;

        mig_submit_dict(dict, 
                        function(job_id) {
			    output_zip = "run-" + name + "-" 
				+ job_id + ".zip";
                            $( "#run_result" ).append("Running " 
				+ name + ". Job ID is " + job_id
				+ ". Output file: " 
                                + "<a href='/cert_redirect/"
				+ run_output_dir + output_zip
				+ "' target='_blank'>" 
                                + output_zip + "</a><br/>");
                              },
                        function(errors) {
                            $( "#run_result" ).append(
                                "<div class='errortext'>"
                                + "<h4>Errors:</h4>"
                                + errors + "</div>");
                        });
	return(true);
    }


    function pretty_args(argss) {
	var msg = "Resulting argument strings:\n";

	function join_head_tail(list, count, inter) {
	    if (count <= 0) {
		return("...");
	    }
	    if (list.length <= count) {
		return(list.join(inter));
	    }
	    var tmp = "";
	    var i;
	    for (i = 0; i < count-1; i++ ) {
		tmp += list[i] + inter;
	    }
	    tmp += "..." + inter + list[ list.length - 1 ];
	    return(tmp);
	}

	switch (argss.length) {
	case 0: 
	    // should not happen (caught by caller)
	    msg += "None!\n";
	    break;
	case 1: 
	    msg += join_head_tail(argss[0], 20, "\n") + "\n";
	    break;
	case 2: 
	    msg += "Job 1:\n   " + join_head_tail(argss[0], 9, "\n   ") + "\n"
	          +"Job 2:\n   " + join_head_tail(argss[1], 9, "\n   ") + "\n";
	    break;
	case 3: 
	    msg += "Job 1:\n   " + join_head_tail(argss[0], 6, "\n   ") + "\n"
	          +"Job 2:\n   " + join_head_tail(argss[1], 6, "\n   ") + "\n"
	          +"Job 3:\n   " + join_head_tail(argss[2], 6, "\n   ") + "\n";
	    break;
	default:
	    msg += "Job 1:\n   " + join_head_tail(argss[0], 5, "\n   ") + "\n"
	          +"Job 2:\n   " + join_head_tail(argss[1], 5, "\n   ") + "\n"
		  + "...   ...\n(" + argss.length + " jobs in total)\n"
		  + "...   ...\n"
	          +"Last :\n   " 
		  + join_head_tail(argss[argss.length-1], 5, "\n   ") + "\n";
	    break;
	}

	return msg;
    }

    $( "#sweep_dialog").dialog("option", "buttons", {
	   "Cancel": function() { 
	       clear_close(); 
	   },
	   "Run": function() { 
	       var files_raw 
		    = ($("#sweep_infiles")[0].value || "").split("\n");
	       add_extra_files(files_raw);

               var arg_line = $("#sweep_args")[0].value || "";
	       var jobs = $("#sweep_jobs")[0].value || "1";
               var limit = new Number($("#sweep_limit")[0].value || "0");
	       var argss = make_sweep_args(jobs, arg_line);

	       if (argss != undefined && argss.length > 0) {

		   var msg = pretty_args(argss);

		   // limit is max.time for one call, in minutes
		   // we calculate a global maximum for all jobs and
		   // classify, if a limit has been given. Otherwise the
		   // jobs get low priority and default limit.
		   if (limit > 0) {
		       max_time = 60 * limit * argss[0].length;
		       while (prio_class < priority_classes.length 
			      && max_time <= 60*priority_classes[prio_class] ) {
 				  prio_class++;
			      }
		       // would be nice to have MiG consider this
		       // classification as a job priority into the dictionary
		       msg += "\nJob time limit: " + (max_time / 60) 
		           + " min.\nJob priority class: " + (prio_class+1)
		           + " (of " + (1+priority_classes.length) 
		           + ", 1 = lowest)\n";
		   } else {
		       msg += "\nNo maximum time given,\n"
			      + "     using default and low priority.";
		   }

		   msg +=  "\nSubmit job(s)?";
		   var yes = confirm(msg);

		   if (yes) {
		       $.each(argss, function(i,args) { 
				  submit_part(args, limit); 
			      });
		   }
	       }

	       clear_close();
	   }
    });

    $( "#sweep_dialog").dialog("open");
}

/* Language selector to trigger dynamic change of language on pages */

function switch_language(lang) {
    /* Hide all before showing only selected - use the built-in lang selector 
       to match all accented versions like 'en' -> 'en', 'en-US', 'en-GB'
    */
    /* TODO: optimize this and use list of lang values */

    /* TODO: switch away from div-only lang and use i18n class instead */

    $("div:lang(en)").hide();
    $("div:lang(da)").hide();    
    $(".i18n:lang(en)").hide();
    $(".i18n:lang(da)").hide();

    $("div:lang("+lang+")").show();
    $(".i18n:lang("+lang+")").show();
}

/* OpenID availability checker for use on signup and login pages */    
function check_oid_available(action, oid_title, oid_url, tag_prefix) {
    $("#"+tag_prefix+"status").removeClass();
    $("#"+tag_prefix+"status").addClass("status_box");
    $("#"+tag_prefix+"status").addClass("spinner").css("padding-left", "20px");
    $("#"+tag_prefix+"status").append("<span>"+oid_title+" OpenID server status: </span>");
    $("#"+tag_prefix+"status").append("<span id="+tag_prefix+"msg></span> <span id="+tag_prefix+"err></span>");
    $("#"+tag_prefix+"msg").append("checking availability ...");
    /* Run oidping check in the background and handle as soon as results come in */
    $.ajax({
        url: "oidping.py?output_format=json;url="+oid_url,
        type: "GET",
        dataType: "json",
        cache: false,
        success: function(jsonRes, textStatus) {
            var i = 0;
            var online = false;
            var err = "";
            // Grab results from json response and place them in resource status.
            for (i=0; i<jsonRes.length; i++) {
                //alert("debug: parsing entry "+i);
                //alert("debug: parsing "+jsonRes[i]);
                //$("#"+tag_prefix+"debug").append(jsonRes[i].toSource());
                if (jsonRes[i].object_type == "openid_status") {    
                    online = jsonRes[i].status;
                    error = jsonRes[i].error;
                    $("#"+tag_prefix+"status").removeClass("spinner").css("padding-left", "0px");
                    $("#"+tag_prefix+"msg").empty();
                    $("#"+tag_prefix+"msg").append(online);
                    if (online == "online") {
                         $("#"+tag_prefix+"status").addClass("ok").css("padding-left", "20px");
                         $("#"+tag_prefix+"msg").addClass("status_online");
                         $("#"+tag_prefix+"button").attr("disabled", false);
                    } else {
                         $("#"+tag_prefix+"err").append("("+error+")<br/>");
                         $("#"+tag_prefix+"status").append("<span>Unable to "+action+" with this method until OpenID server comes back online. Please report the problem to the "+oid_title+" OpenID administrators.</span>");
                         $("#"+tag_prefix+"status").addClass("error").css("padding-left", "20px");
                         $("#"+tag_prefix+"msg").addClass("status_offline");
                         $("#"+tag_prefix+"button").attr("disabled", true);
                    }
                   break;
                }
            }
        }
    });
}

/* Seafile settings helper used to switch between register and save sections */
function select_seafile_section(section_prefix) {
    var reg_prefix="seafilereg";
    var save_prefix="seafilesave";
    if (section_prefix == reg_prefix) {
        //alert("show reg section");
	$("#"+reg_prefix+"button").attr("disabled", false);
	$("#"+save_prefix+"button").attr("disabled", true);
	$("#"+reg_prefix+"access").show();
	$("#"+save_prefix+"access").hide();
    } else if (section_prefix == save_prefix) {
        //alert("show save section");
	$("#"+reg_prefix+"button").attr("disabled", true);
	$("#"+save_prefix+"button").attr("disabled", false);
	$("#"+reg_prefix+"access").hide();
	$("#"+save_prefix+"access").show();
    } else {
        alert("invalid section prefix: "+section_prefix);
        return false;
    }
    return true;
}
/* Seafile registration helper to get the CSRF tag from the signup form and
switch to the save form if registration url shows that user registered and
logged in already */
function prepare_seafile_settings(reg_url, username, integration, 
	 		status_prefix, reg_prefix, save_prefix) {
    $("#"+status_prefix+"status").removeClass();
    $("#"+status_prefix+"status").addClass("status_box");
    $("#"+status_prefix+"status").addClass("spinner").css("padding-left", "20px");
    $("#"+status_prefix+"status").append("<span>Seafile server status: </span>");
    $("#"+status_prefix+"status").append("<span id="+status_prefix+"msg></span>");
    $("#"+status_prefix+"msg").append("checking availability ...");
    /* Run CSRF tag grabber in the background and handle as soon as results come in */
    //alert("DEBUG: run csrf token grabber: "+reg_url);
    $.ajax({
	    url: reg_url,
	    dataType: "html",
	    cache: false,
	    success: function(output, status, xhr) {
		/* Parse output for hidden form input with csrf token */
		//alert("DEBUG: got csrf output: "+output);
		//alert("DEBUG: got csrf status: "+status);
		$("#"+status_prefix+"msg").empty();
		var csrf_token = $("input[name=csrfmiddlewaretoken]", output).val();
		var id_user = $("#account", output).find("div.txt:contains("+username+")").text();
		var logged_in = "";
		$("#"+status_prefix+"msg").append('online');
		if (id_user) {
		    logged_in = "you are already registered and logged in as "+username;
		    //alert("DEBUG: "+logged_in+" ("+id_user+")");
		    $("#"+status_prefix+"status").addClass("ok").css("padding-left", "20px");
		    $("#"+status_prefix+"msg").addClass("status_online");
		    select_seafile_section(save_prefix);
		} else if (csrf_token != undefined) {
		    //alert("DEBUG: got csrf token: "+csrf_token);
		    if (integration) {
		        logged_in = "apparently you already registered and integrated as "+username;
		        select_seafile_section(save_prefix);
		    } else {
		        logged_in = "your are either not registered yet or not currently logged in";
    			select_seafile_section(reg_prefix);
		    }
		    //alert("DEBUG: "+logged_in+" ("+id_user+")");
		    $("#"+status_prefix+"status").addClass("ok").css("padding-left", "20px");
		    $("#"+status_prefix+"msg").addClass("status_online");
		    $("input[name=csrfmiddlewaretoken]").val(csrf_token);
		} else {
		    //alert("Warning: unknown state");
		    logged_in = "unexpected response from server";
		    $("#"+status_prefix+"status").append(" <span>("+logged_in+")</span>");
		    $("#"+status_prefix+"status").addClass("warn").css("padding-left", "20px");
		    $("#"+status_prefix+"msg").addClass("status_slack");
		    $("#"+reg_prefix+"button").attr("disabled", false);
		    $("#"+save_prefix+"button").attr("disabled", false);
		}
		$("#"+status_prefix+"status").append(" <span>("+logged_in+")</span>");

	    },
	    error: function(xhr, status, error) {
		//alert("DEBUG: ajax failed! server probably unavailable");
		$("#"+status_prefix+"msg").empty();
		$("#"+status_prefix+"msg").append('offline');
		$("#"+status_prefix+"status").append(" <span>(Error: "+error+")</span>");
		$("#"+status_prefix+"status").addClass("error").css("padding-left", "20px");
		$("#"+status_prefix+"msg").addClass("status_offline");
		select_seafile_section(save_prefix);
	    }
	});
}

