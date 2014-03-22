#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# submitjob - Job submission interfaces
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

"""Simple front end to job and file uploads"""

import os

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import any_vgrid, default_mrsl_filename, upload_tmp_dir
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
from shared.mrslkeywords import get_job_specs
from shared.parser import parse_lines
from shared.refunctions import list_runtime_environments
from shared.settings import load_settings
from shared.useradm import get_default_mrsl
from shared.vgrid import user_allowed_vgrids
from shared.vgridaccess import user_allowed_res_exes


def signature():
    """Signature of the main function"""

    defaults = {'description': ['False']}
    return ['html_form', defaults]


def available_choices(configuration, client_id, field, spec):
    """Find the available choices for the selectable field.
    Tries to lookup all valid choices from configuration if field is
    specified to be a string variable.
    """
    if 'boolean' == spec['Type']:
        choices = [True, False]
    elif spec['Type'] in ('string', 'multiplestrings'):
        try:
            choices = getattr(configuration, '%ss' % field.lower())
        except AttributeError, exc:
            configuration.logger.error('%s' % exc)
            choices = []
    else:
        choices = []
    if not spec['Required']:
        choices = [''] + choices
    default = spec['Value']
    if default in choices:
        choices = [default] + [i for i in choices if not default == i]
    return choices


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False)
    client_dir = client_id_dir(client_id)
    status = returnvalues.OK
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

    show_description = accepted['description'][-1].lower() == 'true'

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    template_path = os.path.join(base_dir, default_mrsl_filename)

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'Submit Job'
    output_objects.append({'object_type': 'header', 'text'
                          : 'Submit Job'})
    default_mrsl = get_default_mrsl(template_path)
    settings_dict = load_settings(client_id, configuration)
    if not settings_dict or not settings_dict.has_key('SUBMITUI'):
        logger.info('Settings dict does not have SUBMITUI key - using default'
                    )
        submit_style = configuration.submitui[0]
    else:
        submit_style = settings_dict['SUBMITUI']

    # We generate all 3 variants of job submission (fields, textarea, files),
    # initially hide them and allow to switch between them using js.

    # could instead extract valid prefixes as in settings.py
    # (means: by "eval" from configuration). We stick to hard-coding.
    submit_options = ['fields_form', 'textarea_form', 'files_form']

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css"
      href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css"
      href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css"
      media="screen"/>
<link rel="stylesheet" href="/images/css/jquery.fileupload.css">
<link rel="stylesheet" href="/images/css/jquery.fileupload-ui.css">
<link rel="stylesheet" type="text/css"
      href="/images/css/jquery.fileupload-ui.custom.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>
<!--
<script src="/images/js/jquery.ui.widget.js"></script>
-->
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<!-- The Templates plugin is included to render the upload/download listings -->
<script type="text/javascript" src="/images/js/tmpl.min.js"></script>
<!-- The Load Image plugin is included for the preview images and image resizing functionality -->
<script src="/images/js/load-image.min.js"></script>
<!-- The Canvas to Blob plugin is included for image resizing functionality -->
<script src="/images/js/canvas-to-blob.min.js"></script>
<!-- Bootstrap JS is not required, but included for the responsive demo navigation -->
<!--
<script src="//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
-->
<!-- The Iframe Transport is required for browsers without support for XHR file uploads -->
<script src="/images/js/jquery.iframe-transport.js"></script>
<!-- The basic File Upload plugin -->
<script src="/images/js/jquery.fileupload.js"></script>
<!-- The File Upload processing plugin -->
<script src="/images/js/jquery.fileupload-process.js"></script>
<!-- The File Upload image preview & resize plugin -->
<script src="/images/js/jquery.fileupload-image.js"></script>
<!-- The File Upload audio preview plugin -->
<script src="/images/js/jquery.fileupload-audio.js"></script>
<!-- The File Upload video preview plugin -->
<script src="/images/js/jquery.fileupload-video.js"></script>
<!-- The File Upload validation plugin -->
<script src="/images/js/jquery.fileupload-validate.js"></script>
<!-- The File Upload user interface plugin -->
<script src="/images/js/jquery.fileupload-ui.js"></script>
<!-- The File Upload jQuery UI plugin -->
<script src="/images/js/jquery.fileupload-jquery-ui.js"></script>

<script type="text/javascript" src="/images/js/jquery.filemanager.js"></script>

<script type="text/javascript" >
    var base_url = "uploadchunked.py?output_format=json;action=";
    var upload_url = base_url+"put";
    var status_url = base_url+"status";
    var delete_url = base_url+"delete";
    var default_upload_dest = "%s";

    options = %s;

    function setDisplay(this_id, new_d) {
        //console.log("setDisplay with: "+this_id);
        el = document.getElementById(this_id)
        if ( el == undefined || el.style == undefined ) {
            console.log("failed to locate display element: "+this_id);
            return; // avoid js null ref errors
        }
        el.style.display=new_d;
    }

    function switchTo(name) {
        //console.log("switchTo: "+name);
        for (o=0; o < options.length; o++) {
            if (name == options[o]) {
                setDisplay(options[o],"block");
            } else {
                setDisplay(options[o],"none");
            }
        }
    }

    function dumpObject(obj) {
        try {
            return obj.toSource();
        } catch (err) {
            console.log("failed to dump obj: "+err);
            return obj;
        }
    }    

    function openChunkedUpload() {
        var open_dialog = mig_uploadchunked_init("uploadchunked_dialog");
        var remote_path = ".";
        open_dialog("Upload Files in Chunks", function() { return false; },
                    remote_path, false);
    }

    function parseReply(raw_data) {
        var data = {"files": []};
        //console.log("parseReply raw data: "+dumpObject(raw_data));
        if (raw_data.files != undefined) {
             console.log("parseReply return direct files data: "+dumpObject(raw_data.files));
             //return raw_data;
             data.files = raw_data.files;
             return data;
        }
        try {
            $.each(raw_data, function (index, obj) {
                //console.log("result obj: "+index+" "+dumpObject(obj));
                if (obj.object_type == "uploadfiles") {
                    //console.log("found files in obj "+index);
                    var files = obj.files;
                    //console.log("found files: "+index+" "+dumpObject(files));
                    $.each(files, function (index, file) {
                        //console.log("found file entry in results: "+index);
                        if (file.error != undefined) {
                            console.log("found file error: "+file.error);
                            return false;
                        }
                        data["files"].push(file);
                        //console.log("added upload file: "+dumpObject(file));
                    });
                }
            });
        } catch(err) {
            console.log("err in parseReply: "+err);
        }
        console.log("parsed raw reply into files: "+dumpObject(data.files));
        return data;
    }

    function init_fancyupload() {
        "use strict";

        console.log("init_fancyupload");
        // Initialize the jQuery File Upload widget:
        $("#fileupload").fileupload({
            // Uncomment the following to send cross-domain cookies:
            //xhrFields: {withCredentials: true},
            url: upload_url,
            dataType: "json",
            maxChunkSize: 32000000, // 32 MB
            disableImageResize: true,
            filesContainer: ".uploadfileslist",
            add: function (e, data) {
                console.log("add file");
                //var data = parseReply(raw_data);
                //console.log("add file with data: "+dumpObject(data));
                console.log("add file with data files: "+dumpObject(data.files));
                var that = this;
                try {
                    $.blueimp.fileupload.prototype
                                .options.add.call(that, e, data);
                } catch(err) {
                    console.log("err in add file: "+err);
                }
            },
            /* TODO: uploaded entry link and buttons in uploadfileslist silently fail */
            done: function (e, data) {
                console.log("done file");
                console.log("done with data: "+dumpObject(data));
                if (data.result.files == undefined) {
                    var parsed = parseReply(data);
                    console.log("done parsed result: "+dumpObject(parsed));
                    data.result = parsed;
                }
                console.log("done with data result: "+dumpObject(data.result));
                var that = this;
                try {
                    $.blueimp.fileupload.prototype
                                .options.done.call(that, e, data);
                } catch(err) {
                    console.log("err in done file: "+err);
                }                               
            }
        });

        console.log("check server status");
        // Upload server status check for browsers with CORS support:
        if ($.support.cors) {
            $.ajax({
                url: status_url,
                dataType: "json",
                type: "POST"
            }).fail(function () {
                console.log("server status fail");
                $("<div class=\'alert alert-danger\'/>")
                    .text("Upload server currently unavailable - " + new Date())
                    .appendTo("#fileupload");
            }).done(function (raw_result) {
                        console.log("done checking server");
                        //var result = parseReply(raw_result);
                        //console.log("done checking server parsed result: "+dumpObject(result));
                    }
           );
        }
        
        // Load existing files:
        console.log("load existing files");
        $("#fileupload").addClass("fileupload-processing");
        $.ajax({
            // Uncomment the following to send cross-domain cookies:
            //xhrFields: {withCredentials: true},
            url: status_url,
            dataType: "json",
            type: "POST",            
            context: $("#fileupload")[0]
        }).always(function () {
            //console.log("load existing files always handler");
            $(this).removeClass("fileupload-processing");
        }).done(function (raw_result) {
                    //console.log("loaded existing files: "+dumpObject(raw_result));
                    var result = parseReply(raw_result);
                    console.log("parsed existing files: "+dumpObject(result.files));
                    $(this).fileupload("option", "done")
                        .call(this, $.Event("done"), {result: result});
                    console.log("done handling existing files");
                }
           );
    }
    
    function openFancyUploadExt() {
        var open_dialog = mig_fancyupload_init("fancyupload_dialog");
        var remote_path = ".";
        open_dialog("Upload Files in Chunks", function() { return false; },
                    remote_path, false);
    }

    function openFancyUpload() {
        var remote_path = ".";
        init_fancyupload();
        $("#fancyupload_dialog").show();
    }

    $(document).ready( function() {
         console.log("document ready handler");
         switchTo("%s");
         $("#basicdialog").click(openChunkedUpload);
         $("#fancydialog").click(openFancyUpload);
         console.log("init fancydialog");
         try {
             init_fancyupload();
         } catch(err) {
             console.log("error init fancy upload: "+err);
         }
    });

</script>
''' % (upload_tmp_dir, submit_options, submit_style + "_form")

    output_objects.append({'object_type': 'text', 'text':
                           'This page is used to submit jobs to the grid.'})

    output_objects.append({'object_type': 'verbatim',
                           'text': '''
There are %s interface styles available that you can choose among:''' % \
                           len(submit_options)})

    links = []
    for opt in submit_options:
        name = opt.split('_', 2)[0] 
        links.append({'object_type': 'link', 
                      'destination': "javascript:switchTo('%s')" % opt,
                      'class': 'submit%slink' % name,
                      'title': 'Switch to %s submit interface' % name,
                      'text' : '%s style' % name,
                      })
    output_objects.append({'object_type': 'multilinkline', 'links': links})

    output_objects.append({'object_type': 'text', 'text': '''
Please note that changes to the job description are *not* automatically
transferred if you switch style.'''}) 

    output_objects.append({'object_type': 'html_form', 'text':
                           '<div id="fields_form" style="display:none;">\n'})
    
    # Fields
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Please fill in your job description in the fields'
                           ' below:'
                          })
    output_objects.append({'object_type': 'text', 'text'
                          : """
Please fill in one or more fields below to define your job before hitting
Submit Job at the bottom of the page.
Empty fields will simply result in the default value being used and each field
is accompanied by a help link providing further details about the field."""})
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<table class="submitjob">
<form method="post" action="submitfields.py" id="miginput">
"""
                          })
    show_fields = get_job_specs(configuration)
    try:
        parsed_mrsl = dict(parse_lines(default_mrsl))
    except:
        parsed_mrsl = {}

    # Find allowed VGrids and Runtimeenvironments and add them to
    # configuration object for automated choice handling
    
    allowed_vgrids = user_allowed_vgrids(configuration, client_id) + \
                     [any_vgrid]
    allowed_vgrids.sort()
    configuration.vgrids = allowed_vgrids
    (re_status, allowed_run_envs) = list_runtime_environments(configuration)
    if not re_status:
        logger.error('Failed to extract allowed runtime envs: %s' % \
                     allowed_run_envs)
        allowed_run_envs = []
    allowed_run_envs.sort()
    configuration.runtimeenvironments = allowed_run_envs
    user_res = user_allowed_res_exes(configuration, client_id)

    # Allow any exe unit on all allowed resources
        
    allowed_resources = ['%s_*' % res for res in user_res.keys()]
    allowed_resources.sort()
    configuration.resources = allowed_resources
    field_size = 30
    area_cols = 80
    area_rows = 5

    for (field, spec) in show_fields:
        title = spec['Title']
        if show_description:
            description = '%s<br />' % spec['Description']
        else:
            description = ''
        field_type = spec['Type']
        # Use saved value and fall back to default if it is missing
        saved = parsed_mrsl.get('::%s::' % field, None)
        if saved:
            if not spec['Type'].startswith('multiple'):
                default = saved[0]
            else:
                default = saved
        else:
            default = spec['Value']
        # Hide sandbox field if sandboxes are disabled
        if field == 'SANDBOX' and not configuration.site_enable_sandboxes:
            continue
        if 'invisible' == spec['Editor']:
            continue
        if 'custom' == spec['Editor']:
            continue
        output_objects.append({'object_type': 'html_form', 'text'
                                   : """
<b>%s:</b>&nbsp;<a class='infolink' href='docs.py?show=job#%s'>help</a><br />
%s""" % (title, field, description)
                               })
        
        if 'input' == spec['Editor']:
            if field_type.startswith('multiple'):
                output_objects.append({'object_type': 'html_form', 'text'
                                       : """
<textarea name='%s' cols='%d' rows='%d'>%s</textarea><br />
""" % (field, area_cols, area_rows, '\n'.join(default))
                               })
            else:
                output_objects.append({'object_type': 'html_form', 'text'
                                       : """
<input type='text' name='%s' size='%d' value='%s' /><br />
""" % (field, field_size, default)
                               })
        elif 'select' == spec['Editor']:
            choices = available_choices(configuration, client_id,
                                        field, spec)
            res_value = default
            value_select = ''
            if field_type.startswith('multiple'):
                value_select += '<div class="scrollselect">'
                for name in choices:
                    # Blank default value does not make sense here
                    if not str(name):
                        continue
                    selected = ''
                    if str(name) in res_value:
                        selected = 'checked'
                    value_select += '''
                        <input type="checkbox" name="%s" %s value=%s>%s<br />
                        ''' % (field, selected, name, name)
                value_select += '</div>\n'
            else:
                value_select += "<select name='%s'>\n" % field
                for name in choices:
                    selected = ''
                    if str(res_value) == str(name):
                        selected = 'selected'
                    value_select += """<option %s value='%s'>%s</option>\n""" \
                                    % (selected, name, name)
                value_select += """</select><br />\n"""    
            output_objects.append({'object_type': 'html_form', 'text'
                                   : value_select
                                   })
        output_objects.append({'object_type': 'html_form', 'text': "<br />"})

    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<tr>
<td><br /></td>
<td class=centertext>
<input type='submit' value='Submit Job' />
<input type='checkbox' name='save_as_default'> Save as default job template
</td>
<td><br /></td>
</tr>
</form>
</table>
"""
                           })
    output_objects.append({'object_type': 'html_form', 
                           'text': '''
</div><!-- fields_form-->
<div id="textarea_form" style="display:none;">
'''})
    
    # Textarea
    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Please enter your mRSL job description below:'
                          })
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<div class='smallcontent'>
Job descriptions can use a wide range of keywords to specify job requirements
and actions.<br />
Each keyword accepts one or more values of a particular type.<br />
The full list of keywords with their default values and format is available in
the on-demand <a href='docs.py?show=job'>mRSL Documentation</a>.
<p>
Actual examples for inspiration:
<a href=/cpuinfo.mRSL>CPU Info</a>,
<a href=/basic-io.mRSL>Basic I/O</a>,
<a href=/notification.mRSL>Job Notification</a>,
<a href=/povray.mRSL>Povray</a> and
<a href=/vcr.mRSL>VCR</a>
</div>
    """})

    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<!-- 
Please note that textarea.py chokes if no nonempty KEYWORD_X_Y_Z fields 
are supplied: thus we simply send a bogus jobname which does nothing
-->
<table class="submitjob">
<tr><td class=centertext>
<form method="post" action="textarea.py" id="miginput">
<input type=hidden name=jobname_0_0_0 value=" " />
<textarea cols="82" rows="25" name="mrsltextarea_0">
%(default_mrsl)s
</textarea>
</td></tr>
<tr><td>
<center><input type="submit" value="Submit Job" /></center>
<input type="checkbox" name="save_as_default" >Save as default job template
</form>
</td></tr>
</table>
"""
                           % {'default_mrsl': default_mrsl}})

    output_objects.append({'object_type': 'html_form', 
                           'text': '''
</div><!-- textarea_form-->
<div id="files_form" style="display:none;">
'''})
    # Upload form

    output_objects.append({'object_type': 'sectionheader', 'text'
                          : 'Please upload your job file or packaged job files'
                           ' below:'
                          })
    output_objects.append({'object_type': 'html_form', 'text'
                          : """
<table class='files'>
<tr class=title><td class=centertext colspan=4>
Upload job files
</td></tr>
<tr><td colspan=4>
Upload file to current directory (%(dest_dir)s)
</td></tr>
<tr><td colspan=2>
<form enctype='multipart/form-data' action='textarea.py' method='post'>
Extract package files (.zip, .tar.gz, .tar.bz2)
</td><td colspan=2>
<input type=checkbox name='extract_0' />
</td></tr>
<tr><td colspan=2>
Submit mRSL files (also .mRSL files included in packages)
</td><td colspan=2>
<input type=checkbox name='submitmrsl_0' checked />
</td></tr>
<tr><td>    
File to upload
</td><td class=righttext colspan=3>
<input name='fileupload_0_0_0' type='file' size='50'/>
</td></tr>
<tr><td>
Optional remote filename (extra useful in windows)
</td><td class=righttext colspan=3>
<input name='default_remotefilename_0' type='hidden' value='%(dest_dir)s'/>
<input name='remotefilename_0' type='text' size='50' value='%(dest_dir)s'/>
<input type='submit' value='Upload' name='sendfile'/>
</form>
</td></tr>
<tr><td colspan=3>
<hr>
</td></tr>
<tr class=title><td class=centertext colspan=4>
Upload other files efficiently (using chunking).
</td></tr>
<tr><td colspan=2>
<button id='basicdialog'>Open Basic Upload dialog</button>
</td></tr>
<tr><td colspan=2>
<button id='fancydialog'>Open Fancy Upload dialog</button>
</td></tr>
</table>
</div>

<div id='uploadchunked_dialog' title='Upload File' style='display: none;'>
  
    <fieldset>
        <label id='basicfileuploaddestlabel' for='basicfileupload'>
            Optional final destination dir:
        </label>
        <input id='basicfileuploaddest' type='text' size=60 value=''>
      
        <label for='basicfileupload'>File:</label>
        <input id='basicfileupload' type='file' name='files[]' multiple>
    </fieldset>

    <div id='uploadfiles' class='uploadfiles'>
        <div id='globalprogress' class='uploadprogress'>
          <div class='progress-label'>= Init =</div>
        </div>
        <div id='actionbuttons'>
            <button id='pauseupload'>Pause/Resume</button>
            <button id='cancelupload'>Cancel</button>
        </div>
        <br />
        <div id='recentupload'>
            <b>Recently uploaded files:</b> <button id='clearuploads'>Clear</button>
            <div id='uploadedfiles'>
                <!-- dynamically filled by javascript after uploads -->
            </div>
        </div>
        <br />
        <div id='recentfail'>
            <b>Recently failed uploads:</b> <button id='clearfailed'>Clear</button>
            <div id='failedfiles'>
                <!-- dynamically filled by javascript after uploads -->
            </div>
        </div>
        <div id='uploadchunked_output'></div>
    </div>
</div>      

<div id='fancyupload_dialog' title='Upload File' > <!-- style='display: none;' -->

    <!-- The file upload form used as target for the file upload widget -->
    <form id='fileupload' action='uploadchunked.py?output_format=json;action=put'
        method='POST' enctype='multipart/form-data'>
        <p>
            <input id='fileuploaddest' type='text' size=60 value=''>
        </p>

        <!-- The fileupload-buttonbar contains buttons to add/delete files and start/cancel the upload -->
        <div class='fileupload-buttonbar'>
            <div class='fileupload-buttons'>
                <!-- The fileinput-button span is used to style the file input field as button -->
                <span class='fileinput-button'>
                    <span>Add files...</span>
                    <input type='file' name='files[]' multiple>
                </span>
                <button type='submit' class='start'>Start upload</button>
                <button type='reset' class='cancel'>Cancel upload</button>
                <button type='button' class='delete'>Delete</button>
                <input type='checkbox' class='toggle'>
                <!-- The global file processing state -->
                <span class='fileupload-process'></span>
            </div>
            <!-- The global progress state -->
            <div class='fileupload-progress fade' style='display:none'>
                <!-- The global progress bar -->
                <div class='progress' role='progressbar' aria-valuemin='0' aria-valuemax='100'></div>
                <!-- The extended global progress state -->
                <div class='progress-extended'>&nbsp;</div>
            </div>
        </div>
        <!-- The table listing the files available for upload/download -->
        <table role='presentation' class='table table-striped'><tbody class='uploadfileslist'></tbody></table>
    </form>
</div>
    """ % {'dest_dir': '.' + os.sep}})
    
    output_objects.append({'object_type': 'html_form', 
                           'text': '''
<!-- The template to display files available for upload -->
<script id="template-upload" type="text/x-tmpl">
{% console.log("using upload template"); %}
{% console.log("... with upload files: "+dumpObject(o)); %}
{% var dest_dir = $("#fileuploaddest").val() || default_upload_dest; %}
{% console.log("using upload dest: "+dest_dir); %}
{% for (var i=0, file; file=o.files[i]; i++) { %}
    <tr class="template-upload fade">
        <td>
            <span class="preview"></span>
        </td>
        <td>
            <p class="name">{%=dest_dir%}/{%=file.name%}</p>
            <strong class="error"></strong>
        </td>
        <td>
            <p class="size">Processing...</p>
            <div class="progress"></div>
        </td>
        <td>
            {% if (!i && !o.options.autoUpload) { %}
                <button class="start" disabled>Start</button>
            {% } %}
            {% if (!i) { %}
                <button class="cancel">Cancel</button>
            {% } %}
        </td>
    </tr>
{% } %}
</script>
<!-- The template to display files available for download -->
<script id="template-download" type="text/x-tmpl">
{% console.log("using download template"); %}
{% console.log("... with download files: "+dumpObject(o)); %}
{% for (var i=0, file; file=o.files[i]; i++) { %}
    {% console.log("adding download: "+i); %}
    {% console.log("adding download: "+file.name); %}
    <tr class="template-download fade">
        <td>
            <span class="preview">
                {% if (file.thumbnailUrl) { %}
                <a href="{%=file.url%}" title="{%=file.name%}" download="{%=file.name%}" data-gallery><img src="{%=file.thumbnailUrl%}"></a>
                {% } %}
            </span>
        </td>
        <td>
            <p class="name">
                <a href="{%=file.url%}" title="{%=file.name%}" download="{%=file.name%}" {%=file.thumbnailUrl?\'data-gallery\':\'\'%}>{%=file.name%}</a>
            </p>
            {% if (file.error) { %}
                <div><span class="error">Error</span> {%=file.error%}</div>
            {% } %}
        </td>
        <td>
            <span class="size">{%=o.formatFileSize(file.size)%}</span>
        </td>
        <td>
            <button class="delete" data-type="{%=file.deleteType%}" data-url="{%=file.deleteUrl%}"{% if (file.deleteWithCredentials) { %} data-xhr-fields=\'{"withCredentials":true}\'{% } %}>Delete</button>
            <input type="checkbox" name="delete" value="1" class="toggle">
        </td>
    </tr>
{% } %}
</script>
    '''})

    output_objects.append({'object_type': 'html_form', 
                           'text': '\n</div><!-- files_form-->'})
    return (output_objects, status)
