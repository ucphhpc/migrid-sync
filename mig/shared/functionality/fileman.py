#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fileman - File manager UI for browsing and manipulating files and folders
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
from shared.functionality.editor import advanced_editor_deps, lock_info, \
     edit_file
import shared.returnvalues as returnvalues
from shared.settings import load_settings
from shared.useradm import client_id_dir

def html_tmpl():
  """HTML page base"""

  html = '''
  <div id="debug"></div>
  <div id="fm_filemanager">
    <div class="fm_addressbar">
      <ul><li class="fm_path"><input type="text" value="/" name="fm_current_path" readonly="readonly" /></li></ul>
    </div>
    <div class="fm_folders">
      <ul class="jqueryFileTree">
        <li class="directory expanded">
          <a href="#">...</a>
        </li>
      </ul>
    </div>
    <div class="fm_files">
    
      <table id="fm_filelisting" cellspacing="0">
      <thead>
        <tr>
          <th>Name</th>
          <th style="width: 80px;">Size</th>
          <th style="width: 50px;">Type</th>
          <th style="width: 120px;">Date Modified</th>
        </tr>        
      </thead>
      <tbody>
      <!-- this is a placeholder for contents: do not remove! -->
      </tbody>
      </table>            
    
    </div>        
    <div class="fm_statusbar">&nbsp;</div>    
  </div>
  
  <ul id="folder_context" class="contextMenu">
    <li class="mkdir separator">
      <a href="#mkdir">Create Folder</a>
    </li>
    <li class="create">
      <a href="#create">Create File</a>
    </li>
    <li class="upload">
      <a href="#upload">Upload File</a>
    </li>
    <li class="zip">
      <a href="#zip">Zip</a>
    </li>
    <li class="copy separator">
      <a href="#copy">Copy</a>
    </li>
    <li class="paste">
      <a href="#paste">Paste</a>
    </li>
    <li class="rmdir">
      <a href="#rm">Delete Folder</a>
    </li>
    <li class="rename separator">
      <a href="#rename">Rename...</a>
    </li>
  </ul>
  
  <ul id="file_context" class="contextMenu">        
    <li class="download">
      <a href="#show">Download</a>
    </li>
    <li class="edit">
      <a href="#edit">Edit</a>
    </li>
    <li class="copy separator">
      <a href="#copy">Copy</a>
    </li>
    <li class="paste">
      <a href="#paste">Paste</a>
    </li>
    <li class="delete">
      <a href="#rm">Delete</a>
    </li>
    <li class="rename separator">
      <a href="#rename">Rename</a>
    </li>
    <li class="zip">
      <a href="#zip">Zip</a>
    </li>
    <li class="unzip">
      <a href="#unzip">Unzip</a>
    </li>
    <li class="cat separator">
      <a href="#cat">cat</a>
    </li>
    <li class="head">
      <a href="#head">head</a>
    </li>
    <li class="tail">
      <a href="#tail">tail</a>
    </li>
    <li class="submit separator">
      <a href="#submit">submit</a>
    </li>        
  </ul>

  <div id="cmd_dialog" title="Command output" style="display: none;"></div>

  <div id="upload_dialog" title="Upload File" style="display: none;">
  
    <form id="upload_form" enctype="multipart/form-data" method="post" action="textarea.py">
    <fieldset>
      <input type="hidden" name="output_format" value="json"/>
      <input type="hidden" name="max_file_size" value="100000"/>
      
      <label for="submitmrsl_0">Submit mRSL files (also .mRSL files included in packages):</label>
      <input type="checkbox" checked="" name="submitmrsl_0"/>
      <br />
      
      <label for="remotefilename_0">Optional remote filename (extra useful in windows):</label>
      <input type="text" value="./" size="50" name="remotefilename_0" />
      <br />
      
      <label for="extract_0">Extract package files (.zip, .tar.gz, .tar.bz2)</label>
      <input type="checkbox" name="extract_0"/>
      <br />
      
      <label for="fileupload_0_0_0">File:</label>
      <input type="file" name="fileupload_0_0_0"/>

    </fieldset>
    </form>

    <div id="upload_output"></div>

  </div>
      
  <div id="mkdir_dialog" title="Create New Folder" style="display: none;">
  
    <form id="mkdir_form" action="mkdir.py">
    <fieldset>
      <input type="hidden" name="output_format" value="json" />
      <input type="hidden" name="current_dir" value="./" />
      <label for="path">Enter the new name:</label>
      <input type="text" name="path"/>
      
    </fieldset>
    </form>
    <div id="mkdir_output"></div>
  </div>
  
  <div id="rename_dialog" title="Rename" style="display: none;">
  <form id="rename_form" action="mv.py">
  <fieldset>
  
    <input type="hidden" name="output_format" value="json" />
    <input type="hidden" name="flags" value="r" />
    <input type="hidden" name="src" value="" />
    <input type="hidden" name="dst" value="" />
    
    <label for="name">Enter the new name:</label>
    <input type="text" name="name" value="" />
    
  </fieldset>
  </form>
  <div id="rename_output"></div>
  </div>

  <div id="zip_dialog" title="Zip" style="display: none;">
  <form id="zip_form" action="zip.py">
  <fieldset>
  
    <input type="hidden" name="output_format" value="json" />
    <input type="hidden" name="flags" value="" />
    <input type="hidden" name="src" value="" />
    <input type="hidden" name="current_dir" value="" />
    
    <label for="dst">Enter the zip file name:</label>
    <input type="text" name="dst" value="" />
    
  </fieldset>
  </form>
  <div id="zip_output"></div>
  </div>
  '''
  html += '''
  <div id="editor_dialog" title="Editor" style="display: none;">
  <div class="spinner" style="padding-left: 20px;">Loading file...</div>
  %s
''' % edit_file('', '', output_format='json', includes=['switcher', 'submit'])
  html += '''
  <div id="editor_output"></div>
  </div>
  '''
  return html

def js_tmpl(entry_path='/'):
  """Javascript to include in the page header"""

  js = '''
<link rel="stylesheet" type="text/css" href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery.contextmenu.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css" media="screen"/>

<script type="text/javascript" src="/images/js/jquery.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui.js"></script>
<script type="text/javascript" src="/images/js/jquery.form.js"></script>
<script type="text/javascript" src="/images/js/jquery.prettyprint.js"></script>
<script type="text/javascript" src="/images/js/jquery.filemanager.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.js"></script>
<script type="text/javascript" src="/images/js/jquery.tablesorter.pager.js"></script>
<script type="text/javascript" src="/images/js/jquery.contextmenu.js"></script>
'''
  js += advanced_editor_deps(include_jquery=False)
  js += lock_info('this file', -1)
  js += '''
  <script type="text/javascript">
  
  $.ui.dialog.defaults.bgiframe = true;

  $(document).ready( function() {
  
    $("#fm_filemanager").filemanager({
                                      root: "/",
                                      connector: "ls.py",
                                      params: "path",
                                      expandSpeed: 0,
                                      collapseSpeed: 0,
                                      multiFolder: false,
                                      subPath: "%s"
                                      }
    );
  
  });

  </script>
  ''' % entry_path
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
  title_entry['javascript'] = js_tmpl(entry_path)        
  
  output_objects.append({'object_type': 'header', 'text': 'File Manager' })
  output_objects.append({'object_type': 'html_form', 'text': html_tmpl()})

  if len(all_paths) > 1:
    output_objects.append({'object_type': 'sectionheader', 'text':
                           'All requested paths:'})
    for path in all_paths:
      output_objects.append({'object_type': 'link', 'text': path,
                             'destination': 'fileman.py?path=%s' % path})
      output_objects.append({'object_type': 'text', 'text': ''})
      
  return (output_objects, status)
