#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminfreeze - back end to request freeze files in write-once fashion
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

"""Request freeze of one or more files into a write-once archive"""

import shared.returnvalues as returnvalues
from shared.defaults import upload_tmp_dir, csrf_field
from shared.freezefunctions import freeze_flavors
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.html import jquery_ui_js, man_base_js, man_base_html, \
     fancy_upload_js, fancy_upload_html, themed_styles
from shared.init import initialize_main_variables, find_entry

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

    flavor = accepted['flavor'][-1].strip()

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
                               '''Freezing archives is disabled on this site.
Please contact the Grid admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers =  {'flavor': flavor, 'form_method': form_method,
                     'csrf_field': csrf_field, 'csrf_limit': csrf_limit}
    target_op = 'uploadchunked'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})    

    # jquery fancy upload

    (add_import, add_init, add_ready) = fancy_upload_js(configuration,
                                                        csrf_token=csrf_token)

    # We need filechooser deps and dynamic addition of copy/upload fields
    
    add_import += '''
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.prettyprint.js"></script>
<script type="text/javascript" src="/images/js/jquery.contextmenu.js"></script>
<script type="text/javascript" src="/images/js/jquery.xbreadcrumbs.js"></script>
<!-- The preview image plugin -->
<script type="text/javascript" src="/images/js/preview.js"></script>
<!-- The image manipulation CamanJS plugin used by the preview image plugin -->
<script type="text/javascript" src="/images/lib/CamanJS/dist/caman.full.js"></script>
<!-- The nouislider plugin used by the preview image plugin -->
<script type="text/javascript" src="/images/lib/noUiSlider/jquery.nouislider.all.js"></script>
    '''
    add_init += '''
Caman.DEBUG = false

var copy_fields = 0;
var upload_fields = 0;
var open_file_chooser;
var open_upload_dialog;
/* default upload destination */
var remote_path = "%s";

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
        open_file_chooser("Add file or directory (right click to select)",
            function(file) {
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
                    if ($("#"+div_id+" > span > input[value=\\""+path+"\\"]").length) {
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
                    upload_entry += "value=\\""+path+"\\" /><br / >";
                    upload_entry += "</span>";
                    $("#"+div_id).append(upload_entry);
                    console.log("callback added upload: "+upload_entry);
                    upload_fields += 1;
                });
            console.log("callback done");
        }, remote_path, true, "", "%s");
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
    ''' % (upload_tmp_dir, csrf_token)
    add_ready += '''
         // do sequenced initialisation (separate function)
         init_page();
    '''
    title_entry['style'] = themed_styles(configuration,
                                         base=['jquery.contextmenu.css',
                                               'jquery.xbreadcrumbs.css',
                                               'jquery.fmbreadcrumbs.css',
                                               'jquery.fileupload.css',
                                               'jquery.fileupload-ui.css'],
                                         skin=['fileupload-ui.custom.css',
                                               'xbreadcrumbs.custom.css'])
    title_entry['javascript'] = jquery_ui_js(configuration, add_import,
                                             add_init, add_ready)

    if flavor == 'freeze':
        fill_helpers["archive_header"] = "Freeze Archive Files"
        fill_helpers["button_label"] = "Create Archive"
        intro_text = """
Please enter your archive details below and select any files to be included in
the archive.
<p class='warn_message'>Note that a frozen archive can not be changed after
creation and it can only be manually removed by the management, so please be
careful when filling in the details.
</p>
"""
    elif flavor == 'phd':
        fill_helpers["archive_header"] = \
                                       "Thesis and Associated Files to Archive"
        fill_helpers["button_label"] = "Archive Thesis"
        intro_text = """
Please enter your PhD details below and select any files associated with your
thesis.
<p class='warn_message'>Note that a thesis archive can not be changed after
creation and it can only be manually removed by the management, so please be
careful when filling in the details.
</p>
"""
    else:
        output_objects.append({'object_type': 'error_text', 'text':
                               "unknown flavor: %s" % flavor})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    fill_helpers["fancy_dialog"] = fancy_upload_html(configuration)

    files_form = """
<!-- and now this... we do not want to see it, except in a dialog: -->
<div id='fm_filechooser' style='display:none'>
    <div class='fm_path_breadcrumbs'>
        <ul id='fm_xbreadcrumbs' class='xbreadcrumbs'>
        </ul>
    </div>
    <div class='fm_buttonbar'>
        <ul id='fm_buttons' class='buttonbar'>
        <!-- dynamically modified by js to show optional buttons -->
        <li class='datatransfersbutton hidden' title='Manage Data Transfers'>&nbsp;</li>
        <li class='sharelinksbutton hidden' title='Manage Share Links'>&nbsp;</li>
        <li class='parentdirbutton' title='Open Parent Directory'>&nbsp;</li>
        <li class='refreshbutton' title='Refresh'>&nbsp;</li>
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
    <div id='fm_statusbar'>
        <div id='fm_statusprogress'><div class='progress-label'>Loading...</div></div>
        <div id='fm_statusinfo'>&nbsp;</div>
    </div>
    <div id='fm_options'><input id='fm_touchscreen' type='checkbox'>
    Enable touch screen interface (all clicks trigger menu)
    <input id='fm_dotfiles' type='checkbox'>
    Show hidden files and dirs
    </div>
</div>
<div id='cmd_dialog' title='Command output' style='display: none;'></div>

%(fancy_dialog)s
    """ % fill_helpers

    target_op = 'createfreeze'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})

    freeze_form = """
<form enctype='multipart/form-data' method='%(form_method)s' action='%(target_op)s.py'>
<input type='hidden' name='%(csrf_field)s' value='%(csrf_token)s' />
<b>Name:</b><br />
<input type='hidden' name='flavor' value='%(flavor)s' />
<input class='fillwidth padspace' type='text' name='freeze_name' autofocus />
<input type='hidden' name='freeze_author' value='UNSET' />
<input type='hidden' name='freeze_department' value='UNSET' />
<input type='hidden' name='freeze_organization' value='UNSET' />
<br /><b>Description:</b><br />
<textarea class='fillwidth padspace' rows='20' name='freeze_description'></textarea>
<br />
<br />
<div id='freezefiles'>
<b>%(archive_header)s:</b>
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
<input type='submit' value='%(button_label)s' />
</form>
""" % fill_helpers
    output_objects.append({'object_type': 'html_form', 'text': intro_text})
    output_objects.append({'object_type': 'html_form', 'text': files_form})
    output_objects.append({'object_type': 'html_form', 'text': freeze_form})

    return (output_objects, returnvalues.OK)
