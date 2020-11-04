#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# adminfreeze - back end to request freeze files in write-once fashion
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

"""Request freeze of one or more files into a write-once archive"""
from __future__ import absolute_import

import datetime

from mig.shared import returnvalues
from mig.shared.defaults import upload_tmp_dir, trash_linkname, csrf_field, \
    freeze_flavors, keyword_final, keyword_pending, keyword_updating, \
    keyword_auto, public_archive_index
from mig.shared.freezefunctions import get_frozen_archive, brief_freeze
from mig.shared.functional import validate_input_and_cert
from mig.shared.handlers import get_csrf_limit, make_csrf_token
from mig.shared.html import man_base_js, man_base_html, fancy_upload_js, \
    fancy_upload_html, themed_styles
from mig.shared.init import initialize_main_variables, find_entry


def signature():
    """Signature of the main function"""

    defaults = {'flavor': ['freeze'],
                'freeze_id': [keyword_auto]}
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
    freeze_id = accepted['freeze_id'][-1].strip()

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
Please contact the site admins %s if you think it should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    # Load existing freeze for stepwise construction if requested
    freeze_dict = {'ID': freeze_id, 'FLAVOR': flavor}
    if freeze_id != keyword_auto:
        (load_status, freeze_dict) = get_frozen_archive(client_id, freeze_id,
                                                        configuration,
                                                        checksum_list=[])
        if not load_status:
            logger.error("%s: load failed for '%s': %s" %
                         (op_name, freeze_id, brief_freeze(freeze_dict)))
            output_objects.append({'object_type': 'error_text', 'text':
                                   'Could not read details for "%s"' %
                                   freeze_id})
            return (output_objects, returnvalues.SYSTEM_ERROR)

        logger.debug("%s: loaded freeze: %s" %
                     (op_name, brief_freeze(freeze_dict)))

        # Preserve already saved flavor
        flavor = freeze_dict.get('FLAVOR', 'freeze')

        freeze_state = freeze_dict.get('STATE', keyword_final)
        if freeze_state == keyword_final:
            logger.error("%s tried to edit finalized %s archive %s" %
                         (client_id, flavor, freeze_id))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'You cannot edit finalized %s archive %s' % (flavor,
                                                              freeze_id)})
            output_objects.append({
                'object_type': 'link',
                'destination': 'showfreeze.py?freeze_id=%s;flavor=%s' %
                (freeze_id, flavor),
                'class': 'viewarchivelink iconspace genericbutton',
                'title': 'View details about your %s archive' % flavor,
                'text': 'View details',
            })
            return (output_objects, returnvalues.CLIENT_ERROR)
        elif freeze_state == keyword_updating:
            logger.error("%s tried to edit %s archive %s under update" %
                         (client_id, flavor, freeze_id))
            output_objects.append(
                {'object_type': 'error_text', 'text':
                 'You cannot edit %s archive %s until active update completes'
                 % (flavor, freeze_id)})
            output_objects.append({
                'object_type': 'link',
                'destination': 'showfreeze.py?freeze_id=%s;flavor=%s' %
                (freeze_id, flavor),
                'class': 'viewarchivelink iconspace genericbutton',
                'title': 'View details about your %s archive' % flavor,
                'text': 'View details',
            })
            return (output_objects, returnvalues.CLIENT_ERROR)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'flavor': flavor, 'form_method': form_method,
                    'csrf_field': csrf_field, 'csrf_limit': csrf_limit}
    target_op = 'uploadchunked'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    lookup_map = {'freeze_id': 'ID', 'freeze_name': 'NAME',
                  'freeze_author': 'AUTHOR',
                  'freeze_description': 'DESCRIPTION'}
    for (key, val) in lookup_map.items():
        fill_helpers[key] = freeze_dict.get(val, '')
    fill_helpers['publish_value'] = 'no'
    if freeze_dict.get('PUBLISH', False):
        fill_helpers['publish_value'] = 'yes'

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
var trash_linkname = "%s";
var copy_div_id = "copyfiles";
var upload_div_id = "uploadfiles";
/* for upload_callback */
var field_id, field_name, wrap_id, upload_path, on_remove;

function add_copy() {
    var div_id = copy_div_id;
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

function upload_callback() {
    var div_id = upload_div_id;
    console.log("in upload callback");
    $(".uploadfileslist > tr > td > p.name > a").each(
        function(index) {
            console.log("callback for upload item no. "+index);
            upload_path = $(this).text();
            if ($(this).attr("href") == "") {
                console.log("skipping empty (error) upload: "+upload_path);
                // Continue to next iteration on errors
                return true;
            }
            console.log("callback for upload path "+upload_path);
            field_id = "freeze_move_"+upload_fields;
            field_name = "freeze_move_"+upload_fields;
            wrap_id = field_id+"_wrap";
            if ($("#"+div_id+" > span > input[value=\\""+upload_path+"\\"]").length) {
                console.log("skipping duplicate path: "+upload_path);
                // Continue to next iteration on errors
                return true;
            } else {
                console.log("adding new path: "+upload_path);
            }
            on_remove = "";
            on_remove += "remove_field("+wrap_id+");";
            on_remove += "$.fn.delete_upload(\\""+upload_path+"\\");";
            upload_entry = "<span id=\'"+wrap_id+"\'>";
            upload_entry += "<input type=\'button\' value=\'Remove\' ";
            upload_entry += " onClick=\'"+on_remove+"\'/>";
            upload_entry += "<input type=\'text\' id=\'"+field_id+"\' ";
            upload_entry += " name=\'" + field_name + "\' size=50 ";
            upload_entry += "value=\\""+upload_path+"\\" /><br / >";
            upload_entry += "</span>";
            $("#"+div_id).append(upload_entry);
            console.log("callback added upload: "+upload_entry);
            upload_fields += 1;
        });
    console.log("callback done");
}

function add_upload() {
    openFancyUpload("Upload Files", upload_callback, "", remote_path, true,
                    "", "%s");
}

function remove_field(field_id) {
    $(field_id).remove();
}

// init file chooser dialogs with directory selection support
function init_dialogs() {
    open_file_chooser = mig_filechooser_init("fm_filechooser",
        function(file) {
            return;
        }, false, "/");
    /* We reuse shared init function but use custom actual opener above
    to mangle resulting files into archive form. */
    initFancyUpload();
    /* Alias open_dialog to open_upload_dialog for clarity */
    open_upload_dialog = open_dialog;

    $("#addfilebutton").click(function() { add_copy(); });
    $("#adduploadbutton").click(function() { add_upload(); });
}

function init_page() {
    init_dialogs();
}

    ''' % (upload_tmp_dir, trash_linkname, csrf_token)
    add_ready += '''
         // do sequenced initialisation (separate function)
         init_page();
    '''

    # TODO: can we update style inline to avoid explicit themed_styles?
    title_entry['style'] = themed_styles(configuration,
                                         base=['jquery.contextmenu.css',
                                               'jquery.managers.contextmenu.css',
                                               'jquery.xbreadcrumbs.css',
                                               'jquery.fmbreadcrumbs.css',
                                               'jquery.fileupload.css',
                                               'jquery.fileupload-ui.css'],
                                         skin=['fileupload-ui.custom.css',
                                               'xbreadcrumbs.custom.css'],
                                         user_settings=title_entry.get(
                                             'user_settings', {}))
    title_entry['script']['advanced'] += add_import
    title_entry['script']['init'] += add_init
    title_entry['script']['ready'] += add_ready

    if flavor == 'freeze':
        fill_helpers['freeze_name'] = fill_helpers.get('freeze_name', '')
        fill_helpers["archive_header"] = "Freeze Archive Files"
        fill_helpers["button_label"] = "Save and Preview"
        intro_text = """
Please enter your archive details below and select any files to be included in
the archive.
"""
    elif flavor == 'phd':
        fill_helpers['freeze_name'] = fill_helpers.get('freeze_name', '')
        fill_helpers["archive_header"] = "Thesis and Associated Files to Archive"
        fill_helpers["button_label"] = "Save and Preview"
        intro_text = """
Please enter your PhD details below and select any files associated with your
thesis.
"""
    elif flavor == 'backup':
        fill_helpers['freeze_name'] = fill_helpers.get('freeze_name', '')
        if not fill_helpers['freeze_name']:
            now = datetime.datetime.now().isoformat().replace(':', '')
            fill_helpers['freeze_name'] = 'backup-%s' % now
        fill_helpers["archive_header"] = "Files and folders to Archive"
        fill_helpers["button_label"] = "Save and Preview"
        intro_text = """
Please select the files and folders to backup below.
"""
    else:
        output_objects.append({'object_type': 'error_text', 'text':
                               "unknown flavor: %s" % flavor})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # Only warn here if default state is final and persistent
    if freeze_flavors[flavor]['states'][0] == keyword_final and \
            flavor in configuration.site_permanent_freeze:
        intro_text += """
<p class='warn_message'>Note that frozen archives <em>cannot</em> be changed
after final creation and then they can only be manually removed by management,
so please be careful when filling in the details.
</p>
"""

    fill_helpers["fancy_dialog"] = fancy_upload_html(configuration)

    files_form = """
<!-- and now this... we do not want to see it, except in a dialog: -->
<div id='fm_filechooser' style='display:none'>
    <div class='tree-container container-fluid'>
        <div class='tree-row row'>
            <div class='tree-header col-3'></div>
            <div class='fm_path_breadcrumbs col-6'>
                <ul id='fm_xbreadcrumbs' class='xbreadcrumbs'><!-- dynamic --></ul>
            </div>
            <div class='fm_buttonbar col-3 d-none d-lg-block'>
                <ul id='fm_buttons' class='buttonbar'>
                    <!-- dynamically modified by js to show optional buttons -->
                    <li class='datatransfersbutton hidden' title='Manage Data Transfers'>&nbsp;</li>
                    <li class='sharelinksbutton hidden' title='Manage Share Links'>&nbsp;</li>
                    <li class='parentdirbutton' title='Open Parent Directory'>&nbsp;</li>
                    <li class='refreshbutton' title='Refresh'>&nbsp;</li>
                </ul>
            </div>
            <div class='fm_buttonbar-big col-6 d-block d-lg-none hidden'>
                <ul id='fm_buttons' class='buttonbar'>
                    <!-- dynamically modified by js to show optional buttons -->
                    <li class='datatransfersbutton hidden' title='Manage Data Transfers'>&nbsp;</li>
                    <li class='sharelinksbutton hidden' title='Manage Share Links'>&nbsp;</li>
                    <li class='parentdirbutton' title='Open Parent Directory'>&nbsp;</li>
                    <li class='refreshbutton' title='Refresh'>&nbsp;</li>
                </ul>
            </div>
        </div>
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
                    <th class='fm_name'>Name</th>
                    <th class='fm_size'>Size</th>
                    <th class='fm_type'>Type</th>
                    <th class='fm_date'>Date Modified</th>
                    <th class='fm_toolbox'>...</th>
                </tr>
            </thead>
            <tbody>
                <!-- this is a placeholder for contents: do not remove! -->
            </tbody>
         </table>
    </div>
    <div id='fm_statusbar' class='col-lg-12'>
        <div id='fm_statusprogress' class=' col-lg-3'>
            <div class='progress-label'>Loading...</div>
        </div>
        <div id='fm_options' class='col-lg-2'>
            <label id='fm_toggle_touchscreen' class='switch' for='fm_touchscreen' >
            <input id='fm_touchscreen' type='checkbox' />
            <span class='slider round' title='all clicks trigger menu'></span>
            </label><span id='fm_touchscreen_label'>Touch mode</span>
            <label id='fm_toggle_dotfiles' class='switch'>
            <input id='fm_dotfiles' type='checkbox' />
            <span class='slider round' title='Show hidden files and folders'></span>
            </label><span id='fm_dotfiles_label'>Hidden files</span>
        </div>
        <div id='fm_statusinfo' class='col-lg-9'>&nbsp;</div>
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
<input type='hidden' name='flavor' value='%(flavor)s' />
<input type='hidden' name='freeze_id' value='%(freeze_id)s' />
<b>Name:</b><br />
<input class='fillwidth padspace' type='text' name='freeze_name'
    value='%(freeze_name)s' autofocus required pattern='[a-zA-Z0-9_. -]+'
    title='unique name for the freeze archive. I.e. letters and digits separated only by spaces, underscores, periods and hyphens' />
"""
    if flavor != 'backup':
        # TODO: do these make sense to have here or just forced in backend?
        freeze_form += """
<input type='hidden' name='freeze_department' value='' />
<input type='hidden' name='freeze_organization' value='' />
<br><b>Author(s):</b><br />
<input class='fillwidth padspace' type='text' name='freeze_author'
    value='%(freeze_author)s' title='optional archive author(s) in case archive is created on behalf of one or more people' />
<br /><b>Description:</b><br />
<textarea class='fillwidth padspace' rows='20' name='freeze_description'>%(freeze_description)s</textarea>
<br />
"""
    freeze_form += """
<br />
<div id='freezefiles'>
<b>%(archive_header)s:</b><br/>
"""
    freeze_form += """
<input type='button' id='addfilebutton' value='Add file/directory' />
"""
    if flavor != 'backup':
        freeze_form += """
<input type='button' id='adduploadbutton' value='Add upload' />
"""
    freeze_form += """
<div id='copyfiles'>
<!-- Dynamically filled -->
</div>
"""
    if flavor != 'backup':
        freeze_form += """
<div id='uploadfiles'>
<!-- Dynamically filled -->
</div>
"""
    freeze_form += """
</div>
<br />
"""
    if flavor != 'backup':
        freeze_form += """
<div id='freezepublish'>
<b>Make Dataset Publicly Available</b>
"""
        for val in ('yes', 'no'):
            checked = ''
            if fill_helpers['publish_value'] == val:
                checked = 'checked="checked"'
            freeze_form += """
<input type='radio' name='freeze_publish' value='%s' %s />%s
""" % (val, checked, val)
        freeze_form += """
</div>
<br />
"""
    freeze_form += """
<input type='submit' value='%(button_label)s' />
</form>
"""

    # TODO: consider in-lining showfreeze file table for direct modify instead
    #       probably requires more AJAX handling of actions.

    # for rel_path in frozen_files:
    #    freeze_form += """%s<br/>""" % rel_path

    output_objects.append({'object_type': 'html_form', 'text': intro_text})
    output_objects.append({'object_type': 'html_form', 'text': files_form})
    output_objects.append({'object_type': 'html_form', 'text': freeze_form %
                           fill_helpers})

    # Link to view if archive already exists
    if freeze_id != keyword_auto:
        frozen_files = [i['name'] for i in freeze_dict.get('FILES', [])
                        if i['name'] != public_archive_index]
        # Info about contents and spacing before view button otherwise
        if frozen_files:
            output_objects.append(
                {'object_type': 'html_form', 'text': """
<h3>Previously Added Files</h3>
<p>There are already %d file(s) saved in the archive and you can view and
manage those through the link below e.g. in case you change your mind
about including any of them.
</p>""" % len(frozen_files)})
        else:
            output_objects.append({'object_type': 'text', 'text': ''})

        output_objects.append({
            'object_type': 'link',
            'destination': 'showfreeze.py?freeze_id=%s;flavor=%s' % (freeze_id,
                                                                     flavor),
            'class': 'viewarchivelink iconspace genericbutton',
            'title': 'View details about your %s archive' % flavor,
            'text': 'View details',
            'target': '_blank',
        })

    # Spacing
    output_objects.append({'object_type': 'html_form', 'text': '''
            <div class="vertical-spacer"></div>
    '''})

    return (output_objects, returnvalues.OK)
