#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminfreeze - back end to request freeze files in write-once fashion
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

"""Request freeze of one or more files into a write-once archive"""

import shared.returnvalues as returnvalues
from shared.defaults import upload_tmp_dir
from shared.freezefunctions import freeze_flavors
from shared.functional import validate_input_and_cert
from shared.init import initialize_main_variables, find_entry
from shared.safeinput import html_escape

def signature():
    """Signature of the main function"""

    defaults = {'flavor': ['freeze']}
    return ['html_form', defaults]


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

    flavor = accepted['flavor'][-1]

    if not flavor in freeze_flavors.keys():
        output_objects.append({'object_type': 'error_text', 'text':
                           'Invalid freeze flavor: %s' % flavor})
        return (output_objects, returnvalues.CLIENT_ERROR)

    title = freeze_flavors[flavor]['adminfreeze_title']
    output_objects.append({'object_type': 'header', 'text': title})
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = title

    if not configuration.site_enable_freeze:
        output_objects.append({'object_type': 'text', 'text':
                               '''Freezing archives is not enabled on this site.
Please contact the Grid admins %s if you think it should be.
''' % html_escape(configuration.admin_email)})
        return (output_objects, returnvalues.OK)

    # jquery support for dynamic addition of copy/upload fields

    title_entry['javascript'] = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.contextmenu.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui-theme.custom.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.xbreadcrumbs.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.fmbreadcrumbs.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.fileupload.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.fileupload-ui.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.fileupload-ui.custom.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.prettyprint.js"></script>
<script type="text/javascript" src="/images/js/jquery.filemanager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.contextmenu.js"></script>
<script type="text/javascript" src="/images/js/jquery.xbreadcrumbs.js"></script>
<!-- The Templates plugin is included to render the upload/download listings -->
<script type="text/javascript" src="/images/js/tmpl.min.js"></script>
<!-- The Load Image plugin is included for the preview images and image resizing functionality -->
<script type="text/javascript" src="/images/js/load-image.min.js"></script>
<!-- Bootstrap JS is not required, but included for the responsive demo navigation -->
<!-- The Iframe Transport is required for browsers without support for XHR file uploads -->
<script type="text/javascript" src="/images/js/jquery.iframe-transport.js"></script>
<!-- The basic File Upload plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload.js"></script>
<!-- The File Upload processing plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-process.js"></script>
<!-- The File Upload image preview & resize plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-image.js"></script>
<!-- The File Upload validation plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-validate.js"></script>
<!-- The File Upload user interface plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-ui.js"></script>
<!-- The File Upload jQuery UI plugin -->
<script type="text/javascript" src="/images/js/jquery.fileupload-jquery-ui.js"></script>

<!-- The template to display files available for upload -->
<script id="template-upload" type="text/x-tmpl">
{% console.log("using upload template"); %}
{% console.log("... with upload files: "+$.fn.dump(o)); %}
{% var dest_dir = "./" + $("#fancyfileuploaddest").val(); %}
{% console.log("using upload dest: "+dest_dir); %}
{% for (var i=0, file; file=o.files[i]; i++) { %}
    {% var rel_path = $.fn.normalizePath(dest_dir+"/"+file.name); %}
    {% console.log("using upload rel_path: "+rel_path); %}
    <tr class="template-upload fade">
        <td>
            <span class="preview"></span>
        </td>
        <td>
            <p class="name">{%=rel_path%}</p>
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
{% console.log("... with download files: "+$.fn.dump(o)); %}
{% for (var i=0, file; file=o.files[i]; i++) { %}
    {% var rel_path = $.fn.normalizePath("./"+file.name); %}
    {% console.log("using download rel_path: "+rel_path); %}
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
                <a href="{%=file.url%}" title="{%=file.name%}" download="{%=file.name%}" {%=file.thumbnailUrl?\'data-gallery\':\'\'%}>{%=rel_path%}</a>
            </p>
            {% if (file.error) { %}
                <div><span class="error">Error</span> {%=file.error%}</div>
            {% } %}
        </td>
        <td>
            <span class="size">{%=o.formatFileSize(file.size)%}</span>
        </td>
        <td>
            <button class="delete" data-type="{%=file.deleteType%}" data-url="{%=file.deleteUrl%}"{% if (file.deleteWithCredentials) { %} data-xhr-fields=\'{"withCredentials":true}\'{% } %}>{% if (file.deleteUrl) { %}Delete{% } else { %}Dismiss{% } %}</button>
            <input type="checkbox" name="delete" value="1" class="toggle">
        </td>
    </tr>
{% } %}
</script>

<script type="text/javascript" >

var copy_fields = 0;
var upload_fields = 0;
var open_file_chooser;
var open_upload_dialog;
'''
    title_entry['javascript'] += '''
/* default upload destination */
var remote_path = "%s";
''' % upload_tmp_dir
    title_entry['javascript'] += '''
function add_copy(div_id) {
    var field_id = "freeze_copy_"+copy_fields;
    var field_name = "freeze_copy_"+copy_fields;
    var wrap_id = field_id+"_wrap";
    var browse_id = field_id+"_browse";
    copy_entry = "<span id=\'"+wrap_id+"\'>";
    copy_entry += "<input type=\'button\' value=\'Remove\' ";
    copy_entry += " onClick=\'remove_field(\"+wrap_id+\");\'/>";
    // add browse button to mimic upload field
    copy_entry += "<input type=\'button\' id=\'"+browse_id+"\' ";
    copy_entry += " value=\'Browse...\' />";
    copy_entry += "<input type=\'text\' id=\'"+field_id+"\' ";
    copy_entry += " name=\'" + field_name + "\' size=80 /><br / >";
    copy_entry += "</span>";

    $("#"+div_id).append(copy_entry);
    $("#"+field_id).click(function() {
        open_file_chooser("Add file(s)", function(file) {
                $("#"+field_id).val(file);
            });
    });
    $("#"+browse_id).click(function() {
         $("#"+field_id).click();
    });
    $("#"+field_id).click();
    copy_fields += 1;
}

function add_upload(div_id) {
    var field_id, field_name, wrap_id, path, on_remove;
    open_upload_dialog("Upload Files", function() {
            console.log("in upload callback");
            $(".uploadfileslist > tr > td > p.name > a").each(
                function(index) {
                    console.log("callback for upload item no. "+index);
                    path = $(this).text();
                    if ($(this).attr("href") == "") {
                        console.log("skipping empty (error) upload: "+path);
                        // Continue to next iteration on errors
                        return true;
                    }
                    console.log("callback for upload path "+path);
                    field_id = "freeze_move_"+upload_fields;
                    field_name = "freeze_move_"+upload_fields;
                    wrap_id = field_id+"_wrap";
                    if ($("#"+div_id+" > span > input[value=\'"+path+"\']").length) {
                        console.log("skipping duplicate path: "+path);
                        // Continue to next iteration on errors
                        return true;
                    } else {
                        console.log("adding new path: "+path);
                    }
                    on_remove = "";
                    on_remove += "remove_field("+wrap_id+");";
                    on_remove += "$.fn.delete_upload(\\""+path+"\\");";
                    upload_entry = "<span id=\'"+wrap_id+"\'>";
                    upload_entry += "<input type=\'button\' value=\'Remove\' ";
                    upload_entry += " onClick=\'"+on_remove+"\'/>";
                    upload_entry += "<input type=\'text\' id=\'"+field_id+"\' ";
                    upload_entry += " name=\'" + field_name + "\' size=50 ";
                    upload_entry += "value=\'"+path+"\' /><br / >";
                    upload_entry += "</span>";
                    $("#"+div_id).append(upload_entry);
                    console.log("callback added upload: "+upload_entry);
                    upload_fields += 1;
                });
            console.log("callback done");
        }, remote_path, true);
}

function remove_field(field_id) {
    $(field_id).remove();
}

// init file chooser dialogs with directory selction support
function init_dialogs() {
    open_file_chooser = mig_filechooser_init("fm_filechooser",
        function(file) {
            return;
        }, false, "/");
    open_upload_dialog = mig_fancyuploadchunked_init("fancyuploadchunked_dialog");

    $("#addfilebutton").click(function() { add_copy(\"copyfiles\"); });
    $("#adduploadbutton").click(function() { add_upload(\"uploadfiles\"); });
}

function init_page() {
    init_dialogs();
}

$(document).ready(function() {
         // do sequenced initialisation (separate function)
         init_page();
     }
);
</script>
'''

    shared_files_form = """
<!-- and now this... we do not want to see it, except in a dialog: -->
<div id='fm_filechooser' style='display:none'>
    <div class='fm_path_breadcrumbs'>
        <ul id='fm_xbreadcrumbs' class='xbreadcrumbs'>
        </ul>
    </div>
    <div class='fm_addressbar'>
        <input type='hidden' value='/' name='fm_current_path' />
    </div>
    <div class='fm_folders'>
        <ul class='jqueryFileTree'>
            <li class='directory expanded'>
                <a>...</a>
            </li>
        </ul>
    </div>
    <div class='fm_files'>
        <table id='fm_filelisting' style='font-size:13px; border-spacing=0;'>
            <thead>
                <tr>
                    <th>Name</th>
                    <th style='width: 80px;'>Size</th>
                    <th style='width: 50px;'>Type</th>
                    <th style='width: 120px;'>Date Modified</th>
                </tr>
            </thead>
            <tbody>
                <!-- this is a placeholder for contents: do not remove! -->
            </tbody>
         </table>     
    </div>
    <div class='fm_statusbar'>&nbsp;</div>
</div>
<!-- very limited menus here - maybe we should add select all entry? -->
<ul id='folder_context' class='contextMenu' style='display:none'>
    <li class='select'>
        <a href='#select'>Select</a>
    </li>
</ul>
<ul id='file_context' class='contextMenu' style='display:none'>
    <li class='select'>
        <a href='#select'>Select</a>
    </li>
</ul>
<div id='cmd_dialog' title='Command output' style='display: none;'></div>

<div id='fancyuploadchunked_dialog' title='Upload File' style='display: none;'>

    <!-- The file upload form used as target for the file upload widget -->
    <form id='fancyfileupload' action='uploadchunked.py?output_format=json;action=put'
        method='POST' enctype='multipart/form-data'>
        <fieldset id='fancyfileuploaddestbox'>
            <label id='fancyfileuploaddestlabel' for='fancyfileuploaddest'>
                Optional final destination dir:
            </label>
            <input id='fancyfileuploaddest' type='text' size=60 value=''>
        </fieldset>

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
    <!-- For status and error output messages -->
    <div id='fancyuploadchunked_output'></div>
</div>
    """

    if flavor == 'freeze':
        intro_text = """
Please enter your archive details below and select any files to be included in
the archive.
<p class='warn_message'>Note that a frozen archive can not be changed after
creation and it can only be manually removed by the management, so please be
careful when filling in the details.
</p>
"""
        files_form = shared_files_form
        freeze_form = """
<form enctype='multipart/form-data' method='post' action='createfreeze.py'>
<b>Name:</b><br />
<input type='hidden' name='flavor' value='freeze' />
<input type='text' name='freeze_name' size=30 />
<input type='hidden' name='freeze_author' value='UNSET' />
<input type='hidden' name='freeze_department' value='UNSET' />
<input type='hidden' name='freeze_organization' value='UNSET' />
<br /><b>Description:</b><br />
<textarea cols='80' rows='20' name='freeze_description'></textarea>
<br />
<br />
<div id='freezefiles'>
<b>Freeze Archive Files:</b>
<input type='button' id='addfilebutton' value='Add file/directory' />
<input type='button' id='adduploadbutton' value='Add upload' />
<div id='copyfiles'>
<!-- Dynamically filled -->
</div>
<div id='uploadfiles'>
<!-- Dynamically filled -->
</div>
</div>
<br />
<div id='freezepublish'>
<input type='checkbox' name='freeze_publish' />
<b>Make Dataset Publicly Available</b>
</div>
<br />
<input type='submit' value='Create Archive' />
</form>
"""
    if flavor == 'phd':
        intro_text = """
Please enter your PhD details below and select any files associated with your
thesis.
<p class='warn_message'>Note that a thesis archive can not be changed after
creation and it can only be manually removed by the management, so please be
careful when filling in the details.
</p>
"""
        files_form = shared_files_form
        freeze_form = """
<form enctype='multipart/form-data' method='post' action='createfreeze.py'>
<b>Thesis Title:</b><br />
<input type='hidden' name='flavor' value='phd' />
<input type='hidden' name='freeze_organization' value='UNSET' />
<input type='text' name='freeze_name' size=80 />
<br /><b>Author Name:</b><br />
<input type='text' name='freeze_author' size=40 />
<br /><b>Department:</b><br />
<input type='text' name='freeze_department' size=40 />
<br />
<br />
<div id='freezefiles'>
<b>Thesis and Associated Files to Archive:</b>
<input type='button' id='addfilebutton' value='Add file/directory' />
<input type='button' id='adduploadbutton' value='Add upload' />
<div id='copyfiles'>
<!-- Dynamically filled -->
</div>
<div id='uploadfiles'>
<!-- Dynamically filled -->
</div>
</div>
<br />
<div id='freezepublish'>
<input type='checkbox' name='freeze_publish' />
<b>Make Dataset Publicly Available</b>
</div>
<br /><b>Dataset Description:</b><br />
<textarea cols='80' rows='20' name='freeze_description'></textarea>
<br />
<br />
<input type='submit' value='Archive Thesis' />
</form>
"""

    output_objects.append({'object_type': 'html_form', 'text': intro_text})
    output_objects.append({'object_type': 'html_form', 'text': files_form})
    output_objects.append({'object_type': 'html_form', 'text': freeze_form})

    return (output_objects, returnvalues.OK)
