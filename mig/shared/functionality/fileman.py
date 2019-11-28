#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fileman - File manager UI for browsing and manipulating files and folders
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

"""Script to provide users with a means of listing files and directories in
their home directories.
"""

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import trash_linkname, csrf_backends, csrf_field, \
    default_max_chunks
from shared.freezefunctions import import_freeze_form
from shared.functional import validate_input_and_cert
from shared.functionality.editor import advanced_editor_css_deps, \
    advanced_editor_js_deps, lock_info, edit_file
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.gdp import get_project_from_client_id
from shared.html import themed_styles
from shared.init import initialize_main_variables, find_entry, extract_menu
from shared.sharelinks import create_share_link_form, import_share_link_form


def html_tmpl(configuration, client_id, title_entry, csrf_map={}, chroot=''):
    """HTML page base: some upload and menu entries depend on configuration"""

    edit_includes = ['switcher']
    fill_entries = {'vgrid_label': configuration.site_vgrid_label,
                    'default_max_chunks': default_max_chunks,
                    'chroot': chroot}
    fill_entries['create_sharelink_form'] = create_share_link_form(
        configuration, client_id, 'json', '', csrf_map.get('sharelink', ''))
    fill_entries['import_sharelink_form'] = import_share_link_form(
        configuration, client_id, 'json', '', csrf_map.get('cp', ''))
    fill_entries['import_freeze_form'] = import_freeze_form(
        configuration, client_id, 'json', '', csrf_map.get('cp', ''))
    if configuration.site_enable_jobs and \
            'submitjob' in extract_menu(configuration, title_entry):
        fill_entries["upload_submit_entry"] = '''
            <label for="submitmrsl_0">Submit mRSL files (also .mRSL files included in packages):</label>
            <input id="submitmrsl_0" type="checkbox" checked="" name="submitmrsl_0"/>
            '''
        edit_includes.append('submit')
    else:
        fill_entries["upload_submit_entry"] = '''
            <input id="submitmrsl_0" type="hidden" value="0" name="submitmrsl_0"/>
        '''
    # Fill csrf tokens for targets with static form, others are filled in JS
    fill_entries["csrf_field"] = csrf_field
    for (target_op, token) in csrf_map.items():
        fill_entries["%s_csrf_token" % target_op] = token

    # TODO: switch to use shared fancy_upload_html from shared.html!
    html = '''
    <div id="fm_debug"></div>
    <div id="fm_filemanager">
        <div class="fm_path_breadcrumbs">
            <ul id="fm_xbreadcrumbs" class="xbreadcrumbs"><!-- dynamic --></ul>
        </div>
        <div class="fm_buttonbar">
            <ul id="fm_buttons" class="buttonbar">
            <!-- dynamically modified by js to show optional buttons -->
            <li class="datatransfersbutton hidden" title="Manage Data Transfers">&nbsp;</li>
            <li class="sharelinksbutton hidden" title="Manage Share Links">&nbsp;</li>
            <li class="parentdirbutton" title="Open Parent Directory">&nbsp;</li>
            <li class="refreshbutton" title="Refresh">&nbsp;</li>
            </ul>
        </div>
        <div class="fm_addressbar">
            <input type="hidden" value="/" name="fm_current_path" />
        </div>
        <div id="fm_previews" class="fm_previews">       
            <!-- this is a placeholder for contents: do not remove! -->
            <!-- filled by preview.js : init_html -->
        </div>
        <div class="fm_folders">
            <ul class="jqueryFileTree">
                <li class="directory expanded">
                    <a href="#">...</a>
                </li>
            </ul>
        </div>
        
        <div class="fm_files">
            <table id="fm_filelisting" style="border-spacing=0;" >
            <thead>
                <tr>
                    <th>Name</th>
                    <th style="width: 80px;">Size</th>
                    <th style="width: 50px;">Type</th>
                    <th style="width: 120px;">Date Modified</th>
                </tr>
            </thead>
            <tbody id=fm_filelistbody>
            <!-- this is a placeholder for contents: do not remove! -->
            </tbody>
            </table>
        
        </div>                
        <div id="fm_statusbar">
            <div id="fm_statusprogress"><div class="progress-label">Loading...</div></div>
            <div id="fm_statusinfo">&nbsp;</div>
        </div>
        <div id="fm_options"><input id="fm_touchscreen" type="checkbox" />
            Enable touch screen interface (all clicks trigger menu)
            <input id="fm_dotfiles" type="checkbox" />
            Show hidden files and folders
        </div>
    </div>
    
    <div id="cmd_dialog" title="Command output" style="display: none;"></div>

    <div id="upload_dialog" title="Upload File" style="display: none;">
      <div id="upload_tabs">
        <ul>'''
    if configuration.site_enable_gdp:
        html += '''
            <li><a href="#fancyuploadtab">Upload</a></li>'''
    else:
        html += '''
            <li><a href="#fancyuploadtab">Fancy Upload</a></li>
            <li><a href="#legacyuploadtab">Legacy Upload</a></li>'''
    html += '''
        </ul>
        <div id="fancyuploadtab">
            <!-- The file upload form used as target for the file upload widget -->
            <!-- TODO: this form action and args do not seem to have any effect -->
            <!-- Probably all overriden in our filemanager upload JS -->
            <form id="fancyfileupload" action="uploadchunked.py?output_format=json;action=put"
                method="POST" enctype="multipart/form-data">
                <input type="hidden" name="%(csrf_field)s" value="%(uploadchunked_csrf_token)s" />
                <fieldset id="fancyfileuploaddestbox">
                    <label id="fancyfileuploaddestlabel" for="fancyfileuploaddest">
                        Optional final destination dir:
                    </label>
                    <input id="fancyfileuploaddest" type="text" size=60 value="">
                </fieldset>
    
                <!-- The fileupload-buttonbar contains buttons to add/delete files and start/cancel the upload -->
                <div class="fileupload-buttonbar">
                    <div class="fileupload-buttons">
                        <!-- The fileinput-button span is used to style the file input field as button -->
                        <span class="fileinput-button">
                            <span>Add files...</span>
                            <input type="file" name="files[]" multiple>
                        </span>
                        <button type="submit" class="start">Start upload</button>
                        <button type="reset" class="cancel">Cancel upload</button>
                        <button type="button" class="delete">Delete</button>
                        <input type="checkbox" class="toggle">
                        <!-- The global file processing state -->
                        <span class="fileupload-process"><!-- dynamic --></span>
                    </div>
                    <!-- The global progress state -->
                    <div class="fileupload-progress fade" style="display:none">
                        <!-- The global progress bar -->
                        <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100"></div>
                        <!-- The extended global progress state -->
                        <div class="progress-extended">&nbsp;</div>
                    </div>
                </div>
                <!-- The table listing the files available for upload/download -->
                <table role="presentation" class="table table-striped"><tbody class="uploadfileslist">
                <!-- dynamic --></tbody></table>
            </form>
            <!-- For status and error output messages -->
            <div id="fancyuploadchunked_output"><!-- dynamic --></div>
        </div>'''
    if not configuration.site_enable_gdp:
        html += '''
        <div id="legacyuploadtab">
            <form id="upload_form" enctype="multipart/form-data" method="post" action="textarea.py">
                <fieldset>
                    <input type="hidden" name="%(csrf_field)s" value="%(textarea_csrf_token)s" />
                    <input type="hidden" name="output_format" value="json"/>
                    <input type="hidden" name="max_file_size" value="100000"/>

                    %(upload_submit_entry)s
                    <br />
            
                    <label for="remotefilename_0">Optional remote filename (extra useful in windows):</label>
                    <input id="remotefilename_0" type="text" value="./" size="50" name="remotefilename_0" />
                    <br />
            
                    <label for="extract_0">Extract package files (.zip, .tar.gz, .tar.bz2)</label>
                    <input id="extract_0" type="checkbox" name="extract_0"/>
                    <br />
            
                    <label for="fileupload_0_0_0">File:</label>
                    <input id="fileupload_0_0_0" type="file" name="fileupload_0_0_0"/>
                    <input type="submit" value="Upload" onClick="$(\'#upload_output\').html(\'<div><span class=\\\'iconleftpad info spinner\\\'>uploading ... please wait</span></div>\')" />
                </fieldset>
            </form>
            <div id="upload_output"><!-- dynamic --></div>
        </div>'''
    html += '''
      </div>
    </div>    
    <div id="mkdir_dialog" title="Create New Folder" style="display: none;">
    
        <form id="mkdir_form" method="post" action="mkdir.py">
        <fieldset>
            <input type="hidden" name="%(csrf_field)s" value="%(mkdir_csrf_token)s" />
            <input type="hidden" name="output_format" value="json" />
            <input type="hidden" name="current_dir" value="./" />
            <label for="path">Directory name:</label>
            <input id="path" class="singlefield" type="text" name="path" size=50 />            
        </fieldset>
        </form>
        <div id="mkdir_output"><!-- dynamic --></div>
    </div>
    
    <div id="rename_dialog" title="Rename" style="display: none;">
    <form id="rename_form" method="post" action="mv.py">
    <fieldset>    
        <input type="hidden" name="%(csrf_field)s" value="%(mv_csrf_token)s" />
        <input type="hidden" name="output_format" value="json" />
        <input type="hidden" name="flags" value="r" />
        <input type="hidden" name="src" value="" />
        <input type="hidden" name="dst" value="" />
        
        <label for="name">New name:</label>
        <input id="name" class="singlefield" type="text" name="name" size=50 value="" />
    </fieldset>
    </form>
    <div id="rename_output"><!-- dynamic --></div>
    </div>

    <div id="chksum_dialog" title="Checksum" style="display: none;">
    <!-- NOTE: no explicit form action, only submit through jquery -->
    <form id="chksum_form" action="javascript:void(0);">
    <fieldset>
        <input type="hidden" name="%(csrf_field)s" value="%(pack_csrf_token)s" />
        <input type="hidden" name="output_format" value="json" />
        <input type="hidden" name="flags" value="" />
        <input type="hidden" name="hash_algo" value="" />
        <input type="hidden" name="current_dir" value="" />
        
        <label for="path">Target file name(s):</label>
        <input id="path" class="singlefield" type="text" name="path" size=50  value="" />
        <br/><br/>
        <input type="hidden" name="path" value="" />
        <label for="dst">Output file name:</label>
        <input id="dst" class="singlefield" type="text" name="dst" size=50  value="" />
        <br/><br/>
        <label for="max_chunks">Max chunks:</label>
        <input id="max_chunks" class="singlefield" type="text" name="max_chunks"
            size=8  value="%(default_max_chunks)s" />
    </fieldset>
    <p>
    The optional output file is particularly convenient for checksums on big
    files, where the web browser may time-out before the checksum returns an
    answer.<br />
    Optionally change Max chunks to 0 in order to checksum the entire file. It
    may be slow, though, as the run time is proportional to the chunks checked.
    <br />
    </p>
    </form>
    <div id="chksum_output"><!-- dynamic --></div>
    </div>

    <div id="pack_dialog" title="Pack" style="display: none;">
    <!-- NOTE: no explicit form action, only submit through jquery -->
    <form id="pack_form" action="javascript:void(0);">
    <fieldset>
        <input type="hidden" name="%(csrf_field)s" value="%(pack_csrf_token)s" />
        <input type="hidden" name="output_format" value="json" />
        <input type="hidden" name="flags" value="" />
        <input type="hidden" name="src" value="" />
        <input type="hidden" name="current_dir" value="" />
        
        <label for="dst">Archive file name:</label>
        <input id="dst" class="singlefield" type="text" name="dst" size=50  value="" />
    </fieldset>
    <p>
    The provided file extension decides the archive type.<br />
    Use .e.g. <em>.zip</em> for a zip archive or <em>.tgz</em> for compressed tarball.
    </p>
    </form>
    <div id="pack_output"><!-- dynamic --></div>
    </div>

    <div id="unpack_dialog" title="Unpack" style="display: none;">
    <!-- NOTE: no explicit form action, only submit through jquery -->
    <form id="unpack_form" action="javascript:void(0);">
    <fieldset>
        <input type="hidden" name="%(csrf_field)s" value="%(unpack_csrf_token)s" />
        <input type="hidden" name="output_format" value="json" />
        <input type="hidden" name="flags" value="" />
        <input type="hidden" name="src" value="" />
        
        <label for="dst">Unpack to folder:</label>
        <input id="dst" class="singlefield" type="text" name="dst" size=50  value="" />
    </fieldset>
    </form>
    <div id="unpack_output"><!-- dynamic --></div>
    </div>

    <div id="grep_dialog" title="Text search in file" style="display: none;">
    
        <form id="grep_form" method="post" action="grep.py">
        <fieldset>
            <input type="hidden" name="output_format" value="json" />
            <label for="path">Path to search:</label>
            <input id="path" class="singlefield" type="text" name="path" size=50 />
            <br />
            <label for="pattern">Search word/pattern:</label>
            <input id="pattern" class="singlefield" type="text" name="pattern" size=50 />
        </fieldset>
        </form>
        <div id="grep_output"><!-- dynamic --></div>
    </div>
    
    <div id="create_sharelink_dialog" title="Create Share Link"
        style="display: none;">
    %(create_sharelink_form)s
    <div id="create_sharelink_output"><!-- dynamic --></div>
    </div>

    <div id="import_sharelink_dialog" title="Import from Share Link"
        style="display: none;">
    %(import_sharelink_form)s
    <div id="import_sharelink_output"><!-- dynamic --></div>
    </div>

    <div id="import_freeze_dialog" title="Import from archive"
        style="display: none;">
    %(import_freeze_form)s
    <div id="import_freeze_output"><!-- dynamic --></div>
    </div>

    <div id="imagesettings_dialog" title="Image Settings" style="display: none;">
    <fieldset>
    <div id="imagesettings_list" class="fm_metaio_list"></div>
    <div id="imagesettings_edit_tabs">
        <form id="imagesettings_form" method="post" action="imagepreview.py">
        <input type="hidden" name="%(csrf_field)s" value="%(imagepreview_csrf_token)s" />
        <input type="hidden" name="output_format" value="json" />
        <input type="hidden" name="flags" value="" />
        <input type="hidden" name="action" value="" />
        <input type="hidden" name="path" value="" />
        <input type="hidden" name="settings_status" value="" />
        <ul>
            <li><a href="#imagesettings_edit_file_tab">File</a></li>
            <li><a href="#imagesettings_edit_volume_tab">Volume</a></li>
        </ul>
        <div id="imagesettings_edit_file_tab">
            <table class="fm_metaio_edit_table">
            <tr><td>
                <label class="halffield">-- Image --</label>
            </td></tr>
            <tr><td>            
                <label class="halffield" for="extension">Extension:</label>
                <input type="text" name="extension" value="" />
            </td></tr>
            <tr><td>     
                <label class="halffield" for="setting_recursive">Apply to sub-folders:</label>
                <input type="checkbox" name="settings_recursive" value="False" />      
            </td></tr>
            <tr><td>     
                <label class="halffield" for="image_type">Type:</label>
                <select name="image_type">
                    <option value="raw">Raw</option>
                    <option value="tiff">Tiff</option>
                </select>
            </td></tr>
            </table>   
            <div id="imagesettings_edit_image_type_raw">
                <table class="fm_metaio_edit_table">
                <tr><td>
                    <label class="halffield" for="data_type">Data type:</label>
                    <select name="data_type">
                        <option value="float32">float32</option>
                        <option value="float64">float64</option>
                        <option value="uint8">uint8</option>
                        <option value="uint16">uint16</option>
                        <option value="uint32">uint32</option>
                        <option value="uint64">uint64</option>
                        <option value="int8">int8</option>
                        <option value="int16">int16</option>
                        <option value="int32">int32</option>
                        <option value="int64">int64</option>
                    </select>
                </td></tr>
                <tr><td> 
                    <label class="halffield" for="offset">Offset:</label>
                    <input type="text" name="offset" value="" />
                </td></tr>
                <tr><td> 
                    <label class="halffield" for="x_dimension">Width:</label>
                    <input type="text" name="x_dimension" value="" />
                </td></tr>
                <tr><td> 
                    <label class="halffield" for="y_dimension">Height:</label>
                    <input type="text" name="y_dimension" value="" />
                </td></tr>
                </table>   
            </div>
            <table class="fm_metaio_edit_table">
            <tr><td> 
            </td></tr>
            <tr><td> 
                <label class="halffield" for="dummy">-- Preview --</label>
                <input type="hidden" name="dummy" value="" />
            </td></tr>
            <tr><td>
                <label class="halffield" for="preview_cutoff_min">Cutoff min value:</label>
                <input type="text" name="preview_cutoff_min" value="" />
            </td></tr>
            <tr><td>         
                <label class="halffield" for="preview_cutoff_max">Cutoff max value:</label>
                <input type="text" name="preview_cutoff_max" value="" />
            </td></tr>
            </table>
        </div>
        <div id="imagesettings_edit_volume_tab">
            <table class="fm_metaio_edit_table">
            <tr><td>
                <label class="halffield">-- Volume --</label>
            </td></tr>
            <tr><td>         
                <label class="halffield" for="volume_slice_filepattern">Slice file pattern:</label>
                <input type="text" name="volume_slice_filepattern" value="" />
            </td></tr>
            <tr><td> 
                <label class="halffield" for="z_dimension">Number of slices:</label>
                <input type="text" name="z_dimension" value="" />
            </td></tr>
            </table>
        </div>
        </form>                
    </div>
    </fieldset>
    <div id="imagesettings_output"><!-- dynamic --></div>
    </div>
    '''
    html += '''
    <div id="editor_dialog" title="Editor" style="display: none;">
    <div class="iconleftpad spinner"></div>
    %s
''' % edit_file(configuration, client_id, '', '', output_format='json',
                includes=edit_includes)
    html += '''
    <div id="editor_output"><!-- dynamic --></div>
    </div>
    '''
    return html % fill_entries


def css_tmpl(configuration):
    """Stylesheets to include in the page header"""
    css = themed_styles(configuration, base=['jquery.contextmenu.css',
                                             'jquery.managers.contextmenu.css',
                                             'jquery.xbreadcrumbs.css',
                                             'jquery.fmbreadcrumbs.css',
                                             'jquery.fileupload.css',
                                             'jquery.fileupload-ui.css'],
                        skin=['fileupload-ui.custom.css',
                              'xbreadcrumbs.custom.css'])
    css['advanced'] += '''
<link href="/images/lib/noUiSlider/jquery.nouislider.css"  rel="stylesheet"
    type="text/css" />   
<link href="/images/lib/ParaView/Visualizer/main.css" rel="stylesheet"
    type="text/css" />   
'''
    css['advanced'] += advanced_editor_css_deps()
    return css


def js_tmpl(configuration,
            entry_path='/',
            enable_submit='true',
            preview='true',
            csrf_map={},
            chroot=''):
    """Javascript to include in the page header"""

    fill_entries = {
        'chroot': chroot,
        'default_max_chunks': default_max_chunks,
        'trash_linkname': trash_linkname,
        'csrf_field': csrf_field,
        'enable_submit': enable_submit.lower(),
        'entry_path': entry_path,
        'preview': preview.lower(),
        'enable_sharelinks':
            ('%s' % configuration.site_enable_sharelinks).lower(),
        'enable_datatransfers':
            ('%s' % configuration.site_enable_transfers).lower(),
        'enable_gdp':
            ('%s' % configuration.site_enable_gdp).lower(),
    }
    js = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<!-- NOTE: only for testing JQuery API compliance - not for production use -->
<!--
<script type="text/javascript" src="/images/js/jquery-migrate.js"></script>
-->
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<!-- Filemanager and dependencies -->
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.prettyprint.js"></script>
<script type="text/javascript">
var default_max_chunks = "%(default_max_chunks)s";
var trash_linkname = "%(trash_linkname)s";
var csrf_field = "%(csrf_field)s";
var csrf_map = {};
''' % (fill_entries)
    for (target_op, token) in csrf_map.items():
        js += '''
csrf_map["%s"] = "%s";
''' % (target_op, token)
    js += '''
</script>
<script type="text/javascript" src="/images/js/jquery.filemanager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
<script type="text/javascript" src="/images/js/jquery.contextmenu.js"></script>
<script type="text/javascript" src="/images/js/jquery.xbreadcrumbs.js"></script>
<!-- Smart resize debounce resize events -->
<script type="text/javascript" src="/images/js/jquery.debouncedresize.js"></script>
<!-- The preview image plugin -->
<script type="text/javascript" src="/images/js/preview.js"></script>
<!-- The paraview rendering plugin -->
<script type="text/javascript" src="/images/js/preview-paraview.js" load="core, pv-preview-visualizer"></script>
<!-- The image manipulation CamanJS plugin used by the preview image plugin -->
<script type="text/javascript" src="/images/js/preview-caman.js"></script>
<script type="text/javascript" src="/images/lib/CamanJS/dist/caman.full.js"></script>
<script type="text/javascript">
       Caman.DEBUG = false
</script>
<!-- The nouislider plugin used by the preview image plugin -->
<script type="text/javascript" src="/images/lib/noUiSlider/jquery.nouislider.all.js"></script>

<!-- Fancy file uploader and dependencies -->
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
<!-- The File Upload jQuery UI plugin using simple jQuery UI -->
<!-- Please note that this is no longer distributed with file uploader since
     switch to bootstrap. We still use it to style the fileupload dialog buttons. -->
<script type="text/javascript" src="/images/js/jquery.fileupload-jquery-ui.js"></script>

<!-- The template to display files available for upload -->
<script id="template-upload" type="text/x-tmpl">
{% console.debug("using upload template"); %}
{% console.debug("... with upload files: "+$.fn.dump(o)); %}
{% var dest_dir = "./" + $("#fancyfileuploaddest").val(); %}
{% console.debug("using upload dest: "+dest_dir); %}
{% for (var i=0, file; file=o.files[i]; i++) { %}
    {% var rel_path = $.fn.normalizePath(dest_dir+"/"+file.name); %}
    {% console.debug("using upload rel_path: "+rel_path); %}
    <tr class="template-upload fade">
        <td>
            <span class="preview"></span>
        </td>
        <td>
            <p class="name">{%=rel_path%}</p>
            <strong class="error"></strong>
        </td>
        <td>
            <div class="size pending">Processing...</div>
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
{% console.debug("using download template"); %}
{% console.debug("... with download files: "+$.fn.dump(o)); %}
{% for (var i=0, file; file=o.files[i]; i++) { %}
    {% var rel_path = $.fn.normalizePath("./"+file.name); %}
    {% var plain_name = rel_path.substring(rel_path.lastIndexOf("/") + 1); %}
    {% console.debug("using download rel_path: "+rel_path); %}
    {% console.debug("original delete URL: "+file.deleteUrl); %}
    {% function encodeName(str, match) { return "filename="+encodeURIComponent(match)+";files"; }  %}
    {% if (file.deleteUrl != undefined) { file.deleteUrl = file.deleteUrl.replace(/filename\=(.+)\;files/, encodeName); console.debug("updated delete URL: "+file.deleteUrl); } %}    
    <tr class="template-download fade">
        <td>
            <span class="preview">
                {% if (file.thumbnailUrl) { %}
                <a href="{%=file.url%}" title="{%=file.name%}" download="{%=plain_name%}" data-gallery><img src="{%=file.thumbnailUrl%}"></a>
                {% } %}
            </span>
        </td>
        <td>
            <p class="name">
                <a href="{%=file.url%}" title="{%=file.name%}" download="{%=plain_name%}" {%=file.thumbnailUrl?\'data-gallery\':\'\'%}>{%=rel_path%}</a>
            </p>
            {% if (file.error) { %}
                <div><span class="error">Error</span> {%=file.error%}</div>
            {% } %}
        </td>
        <td>
            <div class="size">{%=o.formatFileSize(file.size)%}</div>
        </td>
        <td>
            <button class="delete" data-type="{%=file.deleteType%}" data-url="{%=file.deleteUrl%}"{% if (file.deleteWithCredentials) { %} data-xhr-fields=\'{"withCredentials":true}\'{% } %}>{% if (file.deleteUrl) { %}Delete{% } else { %}Dismiss{% } %}</button>
            <input type="checkbox" name="delete" value="1" class="toggle">
        </td>
    </tr>
{% } %}
</script>
'''
    js += advanced_editor_js_deps(include_jquery=False)
    js += lock_info('this file', -1)
    js += '''
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
    
            $("#fm_filemanager").filemanager({
                                             root: "/",
                                             chroot: "%(chroot)s",
                                             connector: "ls.py",
                                             params: "path",
                                             multiFolder: false,
                                             filespacer: true,
                                             uploadspace: true,
                                             enableSubmit: %(enable_submit)s,
                                             subPath: "%(entry_path)s",
                                             imagesettings: %(preview)s, 
                                             sharelinksbutton: %(enable_sharelinks)s,
                                             datatransfersbutton: %(enable_datatransfers)s,
                                             enableGDP: %(enable_gdp)s,
                                             }
            );

        /*
        } catch(err) {
            alert("Internal error in file manager: " + err);
        }
        */

        /* init upload dialog tabs */
        $("#upload_tabs").tabs();

        /* Always resize filemanager box to fit window height if possible */
        $(window).trigger("resize");
    });
</script>
    ''' % fill_entries

    return js


def signature():
    """Signature of the main function"""

    defaults = {'path': ['']}
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

    chroot = ''
    if configuration.site_enable_gdp:
        chroot = get_project_from_client_id(configuration, client_id)

    all_paths = accepted['path']
    entry_path = all_paths[-1]
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'File Manager'
    title_entry['style'] = css_tmpl(configuration)
    if configuration.site_enable_jobs and \
            'submitjob' in extract_menu(configuration, title_entry):
        enable_submit = 'true'
    else:
        enable_submit = 'false'
    csrf_map = {}
    method = 'post'
    limit = get_csrf_limit(configuration)
    for target_op in csrf_backends:
        csrf_map[target_op] = make_csrf_token(configuration, method,
                                              target_op, client_id, limit)
    title_entry['javascript'] = js_tmpl(
        configuration, entry_path, enable_submit,
        str(configuration.site_enable_preview),
        csrf_map, chroot)

    output_objects.append({'object_type': 'header', 'class': 'fileman-title',
                           'text': 'File Manager'})
    output_objects.append({'object_type': 'html_form', 'text':
                           html_tmpl(configuration, client_id, title_entry,
                                     csrf_map, chroot)})

    if len(all_paths) > 1:
        output_objects.append({'object_type': 'sectionheader', 'text':
                               'All requested paths:'})
        for path in all_paths:
            output_objects.append({'object_type': 'link', 'text': path,
                                   'destination': 'fileman.py?path=%s' % path})
            output_objects.append({'object_type': 'text', 'text': ''})

    return (output_objects, status)
