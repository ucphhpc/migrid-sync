#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fileman - File manager UI for browsing and manipulating files and folders
#
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

"""Script to provide users with a means of listing files and directories in
their home directories.
"""

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.functional import validate_input_and_cert
from shared.functionality.editor import advanced_editor_css_deps, \
     advanced_editor_js_deps, lock_info, edit_file
from shared.html import themed_styles
from shared.init import initialize_main_variables, find_entry, extract_menu

def html_tmpl(configuration, title_entry):
    """HTML page base: some upload and menu entries depend on configuration"""

    edit_includes = ['switcher']
    fill_entries = {}
    if 'submitjob' in extract_menu(configuration, title_entry):
        fill_entries["upload_submit_entry"] = '''
            <label for="submitmrsl_0">Submit mRSL files (also .mRSL files included in packages):</label>
            <input id="submitmrsl_0" type="checkbox" checked="" name="submitmrsl_0"/>
            '''
        edit_includes.append('submit')
    else:
        fill_entries["upload_submit_entry"] = '''
            <input id="submitmrsl_0" type="hidden" value="0" name="submitmrsl_0"/>
        '''
    html = '''
    <div id="fm_debug"></div>
    <div id="fm_filemanager">
        <div class="fm_path_breadcrumbs">
            <ul id="fm_xbreadcrumbs" class="xbreadcrumbs">
            </ul>
        </div>
        <div class="fm_addressbar">
            <input type="hidden" value="/" name="fm_current_path" />
        </div>
        <div class="fm_previews">       
            <input type="hidden" value="" name="fm_preview_base_path" />
            <input type="hidden" value="" name="fm_preview_path" />
            <input type="hidden" value="" name="fm_preview_filename" />
            <input type="hidden" value="" name="fm_preview_extension" />
            <div id="fm_preview_menubar" class="fm_preview_menubar">
                <div id="fm_preview_menubar_refresh" class="fm_preview_menubar_entry" title="Refresh Preview">
                    <img src="/images/icons/arrow_refresh.png">
                </div>
                <div id="fm_preview_menubar_zoom_in" class="fm_preview_menubar_entry" title="Zoom In">
                    <img src="/images/icons/add.png">
                </div>
                <div id="fm_preview_menubar_zoom_out" class="fm_preview_menubar_entry" title="Zoom Out">
                    <img src="/images/icons/delete.png">
                </div>                  
            </div>
            <div id="fm_preview_left_tile" class="fm_preview_left_tile">
                <div id="fm_preview_left_tile_histogram">
                    <canvas id="fm_preview_histogram_image"></canvas>
                </div>
                <div id="fm_preview_left_tile_histogram_actions">
                    <input type="hidden" value="" name="fm_preview_histogram_scale" />
                    <input type="hidden" value="" name="fm_preview_histogram_scale" />
                    <div id="fm_preview_histogram_min_max_slider"></div>   
                    <br>
                    <button id="preview_histogram_reset_button" title="Reset sliders">Reset</button>
                    <button id="preview_histogram_set_cutoff_button" title="Set preview cutoff based on sliders">Set Cutoff</button>
                    <!-- <button id="preview_histogram_auto_button">Auto</button> -->
                </div>
                <div id="fm_preview_left_output">
                <!-- this is a placeholder for contents: do not remove! -->
                </div>
            </div>
            <div id="fm_preview_center_tile" class="fm_preview_center_tile">
                <canvas id="fm_preview_image"></canvas>
            </div>
            <div id="fm_preview_right_tile" class="fm_preview_right_tile"> 
                <div id="fm_preview_right_output">
                <!-- this is a placeholder for contents: do not remove! -->
                </div>
            </div>
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
    </div>
    <div id="fm_options"><input id="fm_touchscreen" type="checkbox">
        Enable touch screen interface (all clicks trigger menu)
        <input id="fm_dotfiles" type="checkbox">
        Show hidden files and dirs</div>
    
    <div id="cmd_dialog" title="Command output" style="display: none;"></div>

    <div id="upload_dialog" title="Upload File" style="display: none;">

      <div id="upload_tabs">
        <ul>
              <li><a href="#fancyuploadtab">Fancy Upload</a></li>
              <li><a href="#legacyuploadtab">Legacy Upload</a></li>
        </ul>
        <div id="fancyuploadtab">
            <!-- The file upload form used as target for the file upload widget -->
            <form id="fancyfileupload" action="uploadchunked.py?output_format=json;action=put"
                method="POST" enctype="multipart/form-data">
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
                        <span class="fileupload-process"></span>
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
                </tbody></table>
            </form>
            <!-- For status and error output messages -->
            <div id="fancyuploadchunked_output"></div>
        </div>
        <div id="legacyuploadtab">
            <form id="upload_form" enctype="multipart/form-data" method="post" action="textarea.py">
                <fieldset>
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
                    <input type="submit" value="Upload" onClick="$(\'#upload_output\').html(\'<div><span class=\\\'iconspace info spinner\\\'>uploading ... please wait</span></div>\')" />
                </fieldset>
            </form>
            <div id="upload_output"></div>
        </div>
      </div>
    </div>
    
    <div id="mkdir_dialog" title="Create New Folder" style="display: none;">
    
        <form id="mkdir_form" method="post" action="mkdir.py">
        <fieldset>
            <input type="hidden" name="output_format" value="json" />
            <input type="hidden" name="current_dir" value="./" />
            <label for="path">Enter the new name:</label>
            <input id="path" type="text" name="path"/>            
        </fieldset>
        </form>
        <div id="mkdir_output"></div>
    </div>
    
    <div id="rename_dialog" title="Rename" style="display: none;">
    <form id="rename_form" method="post" action="mv.py">
    <fieldset>    
        <input type="hidden" name="output_format" value="json" />
        <input type="hidden" name="flags" value="r" />
        <input type="hidden" name="src" value="" />
        <input type="hidden" name="dst" value="" />
        
        <label for="name">Enter the new name:</label>
        <input id="name" type="text" name="name" value="" />
    </fieldset>
    </form>
    <div id="rename_output"></div>
    </div>

    <div id="pack_dialog" title="Pack" style="display: none;">
    <form id="pack_form" method="post" action="pack.py">
    <fieldset>
        <input type="hidden" name="output_format" value="json" />
        <input type="hidden" name="flags" value="" />
        <input type="hidden" name="src" value="" />
        <input type="hidden" name="current_dir" value="" />
        
        <label for="dst">Enter the archive file name:</label>
        <input id="dst" type="text" name="dst" size=50  value="" />
        <p>The provided file extension decides the archive type.
        Use .e.g. .zip for a zip archive or .tgz for compressed tarball.
        </p>
    </fieldset>
    </form>
    <div id="pack_output"></div>
    </div>

    <div id="imagesettings_dialog" title="Image Settings" style="display: none;">
    <form id="imagesettings_form" method="post" action="filemetaio.py">
    <fieldset>
        <input type="hidden" name="output_format" value="json" />
        <input type="hidden" name="flags" value="" />
        <input type="hidden" name="action" value="" />
        <input type="hidden" name="path" value="" />
        <input type="hidden" name="settings_status" value="" />
        <div id="imagesettings_list" class="fm_metaio_list"></div>
        <div id="imagesettings_edit">
            <label for="extension">Image extension:</label>
            <br>
            <input type="text" name="extension" value="" />
            <br>
            <label for="setting_recursive">Apply to sub-folders:</label>
            <br>
            <input type="checkbox" name="settings_recursive" value="False" />
            <br>
            <label for="image_type">Image type:</label>
            <br>
            <select name="image_type">
                <option value="raw">Raw</option>
                <option value="tiff">Tiff</option>
            </select>
            <br>
            <div id="imagesettings_edit_image_type_raw">
                <label for="data_type">Image data type:</label>
                <br>
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
                <br>
                <label for="offset">Image offset:</label>
                <br>
                <input type="text" name="offset" value="" />
                <br>
                <label for="x_dimension">Image width:</label>
                <br>
                <input type="text" name="x_dimension" value="" />
                <br>
                <label for="y_dimension">Image height:</label>
                <br>
                <input type="text" name="y_dimension" value="" />
                <br>
            </div>
            <label for="preview_cutoff_min">Preview image cutoff min value:</label>
            <br>
            <input type="text" name="preview_cutoff_min" value="" />
            <br>
            <label for="preview_cutoff_max">Preview image cutoff max value:</label>
            <br>
            <input type="text" name="preview_cutoff_max" value="" />
        </div>    
    </fieldset>
    </form>                
    <div id="imagesettings_output"></div>
    </div>
    ''' % fill_entries
    html += '''
    <div id="editor_dialog" title="Editor" style="display: none;">
    <div class="iconspace spinner"></div>
    %s
''' % edit_file('', '', output_format='json', includes=edit_includes)
    html += '''
    <div id="editor_output"></div>
    </div>
    '''
    return html

def css_tmpl(configuration):
    """Stylesheets to include in the page header"""
    css = themed_styles(configuration, base=['jquery.contextmenu.css',
                                             'jquery.xbreadcrumbs.css',
                                             'jquery.fmbreadcrumbs.css',
                                             'jquery.fileupload.css',
                                             'jquery.fileupload-ui.css'],
                        skin=['fileupload-ui.custom.css',
                              'xbreadcrumbs.custom.css'])
    css['advanced'] += '''
<link href="/images/lib/noUiSlider/jquery.nouislider.css"  rel="stylesheet"
    type="text/css" />   
'''
    css['advanced'] += advanced_editor_css_deps()
    return css

def js_tmpl(entry_path='/', enable_submit='true', preview='true'):
    """Javascript to include in the page header"""
    js = '''
<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<!-- Filemanager and dependencies -->
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.prettyprint.js"></script>
<script type="text/javascript" src="/images/js/jquery.filemanager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.widgets.js"></script>
<script type="text/javascript" src="/images/js/jquery.contextmenu.js"></script>
<script type="text/javascript" src="/images/js/jquery.xbreadcrumbs.js"></script>
<!-- The preview image plugin -->
<script type="text/javascript" src="/images/js/preview.js"></script>
<!-- The image manipulation CamanJS plugin used by the preview image plugin -->
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
                                             connector: "ls.py",
                                             params: "path",
                                             multiFolder: false,
                                             filespacer: true,
                                             uploadspace: true,
                                             enableSubmit: %s,
                                             subPath: "%s",
                                             imagesettings: %s
                                             }
            );

        /*
        } catch(err) {
            alert("Internal error in file manager: " + err);
        }
        */

        /* init upload dialog tabs */
        $("#upload_tabs").tabs();
    });
</script>
    ''' % (enable_submit.lower(), entry_path, preview.lower())
    return js
        
def signature():
    """Signature of the main function"""

    defaults = {'path' : ['']}
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

    all_paths = accepted['path']
    entry_path = all_paths[-1]
    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = 'File Manager'
    title_entry['style'] = css_tmpl(configuration)
    if 'submitjob' in extract_menu(configuration, title_entry):
        enable_submit = 'true'
    else:
        enable_submit = 'false'
    title_entry['javascript'] = js_tmpl(entry_path, enable_submit,
                                        str(configuration.site_enable_preview))
    
    output_objects.append({'object_type': 'header', 'text': 'File Manager' })
    output_objects.append({'object_type': 'html_form', 'text':
                           html_tmpl(configuration, title_entry)})

    if len(all_paths) > 1:
        output_objects.append({'object_type': 'sectionheader', 'text':
                               'All requested paths:'})
        for path in all_paths:
            output_objects.append({'object_type': 'link', 'text': path,
                                   'destination': 'fileman.py?path=%s' % path})
            output_objects.append({'object_type': 'text', 'text': ''})

    return (output_objects, status)
