#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# editor - Online editor back end
# Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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

""" Simple web based file editor to edit files in MiG home

Enable users to make (limited) changes to their files without the
need to download, edit and upload the files.
"""

import os
import time

import shared.returnvalues as returnvalues
from shared.base import client_id_dir
from shared.defaults import csrf_field
from shared.editing import acquire_edit_lock, edit_lock_suffix, cm_css, \
     cm_javascript, cm_options, miu_css, miu_javascript, miu_options, \
     init_editor_js, run_editor_js, change_editor_mode_js, kill_editor_js
from shared.functional import validate_input_and_cert
from shared.handlers import get_csrf_limit, make_csrf_token
from shared.init import initialize_main_variables, find_entry
from shared.validstring import valid_user_path

edit_includes = ['switcher', 'newline', 'submit', 'discard', 'spellcheck',
                 'save']

def signature():
    """Signature of the main function"""

    defaults = {'path': [''], 'current_dir': ['']}
    return ['html_form', defaults]

def advanced_editor_css_deps():
    """Add css dependencies for advanced editor"""
    css = '''
%s

%s

<!-- TODO: move to markitup.custom.css -->
<!-- MarkItUp style fixes -->
<style type="text/css">
<!--
/* fancy editor switcher */
#switcher {
    padding: 2px;
}
#switcher li {
    list-style:none;
    float:left;
    padding: 4px;
}
#switcher .currentSet {
    font-weight:bold;
    color:#990066;
}

/* prevent menu float from interfering with editor button header */
.markItUp {
    overflow: auto;
}
-->
</style>
''' % (miu_css, cm_css)
    return css

def advanced_editor_js_deps(include_jquery=True):
    """Add js dependencies for advanced editor"""
    js = ''
    if include_jquery:
        js += '<script type="text/javascript" src="/images/js/jquery.js"></script>'
    js += '''
%s

%s

<script type="text/javascript">
    /* Keep track of editor type */
    var lastEdit = "raw";
    
    function enableStyleSheet(title) {
        var i, a, main;
        for(i=0; (a = document.getElementsByTagName("link")[i]); i++) {
            if(a.getAttribute("rel").indexOf("style") != -1 && a.getAttribute("title")) {
                if(a.getAttribute("title") == title) a.disabled = false;
            }
        }
    }
    function disableStyleSheet(title) {
       var i, a, main;
       for(i=0; (a = document.getElementsByTagName("link")[i]); i++) {
           if(a.getAttribute("rel").indexOf("style") != -1 && a.getAttribute("title")) {
               if(a.getAttribute("title") == title) a.disabled = true;
           }
       }
    }

    %s

    %s

    function autoDetectMode() {
        //console.log("autoDetectMode");
        var mode, ext;
        var path = $("#editorpath").val();
        //console.log("autoDetectMode path: "+path);
        var filename = path.split("/").pop();
        var parts = filename.split(".");
        if (parts.length == 1 || ( parts[0] == "" && parts.length == 2 ) ) {
            ext = "";
        }
        ext = parts.pop(); 
        if (ext == "py") {
            mode = "python";
        } else if (ext == "java") {
            mode = "java";
        } else if (ext == "pl") {
            mode = "perl";
        } else if (ext == "c") {
            mode = "clike";
        } else if (ext == "cc") {
            mode = "clike";
        } else if (ext == "cpp") {
            mode = "clike";
        } else if (ext == "f") {
            mode = "fortran";
        } else if (ext == "f90") {
            mode = "fortran";
        } else if (ext == "f95") {
            mode = "fortran";
        } else if (ext == "for") {
            mode = "fortran";
        } else if (ext == "rb") {
            mode = "ruby";
        } else if (ext == "rbw") {
            mode = "ruby";
        } else if (ext == "hs") {
            mode = "haskell";
        } else if (ext == "hi") {
            mode = "haskell";
        } else if (ext == "ml") {
            mode = "mllike";
        } else if (ext == "mli") {
            mode = "mllike";
        } else if (ext == "erl") {
            mode = "erlang";
        } else if (ext == "hrl") {
            mode = "erlang";
        } else if (ext == "groovy") {
            mode = "groovy";
        } else if (ext == "gy") {
            mode = "groovy";
        } else if (ext == "gvy") {
            mode = "groovy";
        } else if (ext == "gsh") {
            mode = "groovy";
        } else if (ext == "go") {
            mode = "go";
        } else if (ext == "fs") {
            mode = "mllike";
        } else if (ext == "fsx") {
            mode = "mllike";
        } else if (ext == "m") {
            mode = "octave";
        } else if (ext == "mat") {
            mode = "octave";
        } else if (ext == "sh") {
            mode = "shell";
        } else if (ext == "tex") {
            mode = "stex";
        } else if (ext == "rst") {
            mode = "rst";
        } else if (ext == "yaml") {
            mode = "yaml";
        } else if (ext == "xml") {
            mode = "xml";
        } else if (ext == "html") {
            mode = "htmlmixed";
        } else if (ext == "js") {
            mode = "javascript";
        } else if (ext == "json") {
            mode = "javascript";
        } else if (ext == "css") {
            mode = "css";
        } else {
            // mode null means plain text
            mode = "null";
        }
        console.log("autoDetectMode mode: "+mode);
        change_editorarea_editor_mode(mode);
    }

    function disable_editorarea_editor(lastEdit) {
        if (lastEdit == "MarkItUp") {
            $("#editorarea").markItUpRemove();
            /* stylesheet button settings collide for different sets
            disable all set stylesheets and enable only selected one */
            disableStyleSheet("html");
            //disableStyleSheet("txt2tags");
        } else if (lastEdit == "CodeMirror") {
            %s
            /* no need to fiddle with stylesheet here */
            //disableStyleSheet("codemirror-ui");
        }
    }

    function enable_editorarea_editor(newSet) {
        lastEdit = "raw";
        switch(newSet) {
            case "html":
                lastEdit = "MarkItUp";
                enableStyleSheet("html");
                $("#editorarea").markItUp(myHtmlSettings);
                break;
            /*
            case "txt2tags":
                lastEdit = "MarkItUp";
                enableStyleSheet("txt2tags");
                $("#editorarea").markItUp(myTxt2TagsSettings);
                break;
            */
            case "codemirror":
                lastEdit = "CodeMirror";
                /* no need to fiddle with stylesheet here */
                //enableStyleSheet("codemirror-ui");
                %s
                autoDetectMode();
                break;
        }
    }
    
    $(document).ready(function() {
        $("#switcher li").click(function() {
            $("#switcher li").removeClass("currentSet");
            newSet = $(this).attr("class");
            $(this).addClass("currentSet");
            disable_editorarea_editor(lastEdit);
            enable_editorarea_editor(newSet);
            return false;
        });
    $("#switcher .currentSet").click();
    });
</script>
''' % (cm_javascript, miu_javascript, init_editor_js("editorarea",
       cm_options, wrap_in_tags=False), change_editor_mode_js("editorarea",
       wrap_in_tags=False), kill_editor_js("editorarea", wrap_in_tags=False),
       run_editor_js("editorarea", wrap_in_tags=False))
    return js

def lock_info(abs_path, time_left):
    """This function generates javascript similar to that used in Moin Moin Wiki
    (http://moinmoin.wikiwikiweb.de)
    """

    lock_timeout = time_left / 60
    lock_expire = 'Your edit lock on __file__ has expired!'
    lock_mins = 'Your edit lock on __file__ will expire in # minutes.'
    lock_secs = 'Your edit lock on __file__ will expire in # seconds.'

    script = \
        '''
<!-- javascript borrowed from Moin Moin Wiki (http://moinmoin.wikiwikiweb.de) -->
<script type="text/javascript">
var lock_file = "this file"
var timeout_min = %(lock_timeout)s;
var state = 0; // 0: start; 1: long count; 2: short count; 3: timeout; 4/5: blink
var counter = 0, step = 1, delay = 1;

function countdown() {
    // change state if counter is down
    if (counter <= 1) {
        state += 1
        if (state == 1) {
            counter = timeout_min
            step = 1
            delay = 60000
        }
        if (state == 2) {
            counter = 60
            step = 5
            delay = step * 1000
        }
        if (state == 3 || state == 5) {
            window.status = "%(lock_expire)s".replace(/__file__/, lock_file)
            state = 3
            counter = 1
            step = 1
            delay = 500
        }
        if (state == 4) {
            // blink the above text
            window.status = " "
            counter = 1
            delay = 250
        }
    }
        
    // display changes
    if (state < 3) {
        var msg
        if (state == 1) msg = "%(lock_mins)s"
        if (state == 2) msg = "%(lock_secs)s"
        window.status = msg.replace(/#/, counter).replace(/__file__/, lock_file)
    }
    counter -= step
    
    // Set timer for next update
    setTimeout("countdown()", delay)
}

function newcountdown(path, minutes) {
    //window.status = "test"
    lock_file = path
    timeout_min = minutes
    setTimeout("countdown()", delay)
}
</script>
'''\
         % {
        'lock_timeout': lock_timeout,
        'lock_expire': lock_expire,
        'lock_mins': lock_mins,
        'lock_secs': lock_secs,
        }
    return script


def edit_file(configuration, client_id, path, abs_path, output_format='html',
              includes=edit_includes):
    """Format and return the contents of a given file"""

    text = ''
    if os.path.isfile(abs_path):
        try:
            src_fd = open(abs_path, 'rb')
            text = src_fd.read()
            src_fd.close()
        except Exception, exc:
            return 'Failed to open file %s: %s' % (path, exc)

    form_method = 'post'
    csrf_limit = get_csrf_limit(configuration)
    fill_helpers = {'path': path, 'lock_suffix': edit_lock_suffix,
                    'output_format': output_format, 'text': text,
                    'form_method': form_method, 'csrf_field': csrf_field,
                    'csrf_limit': csrf_limit}
    target_op = 'editfile'
    csrf_token = make_csrf_token(configuration, form_method, target_op,
                                 client_id, csrf_limit)
    fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
    
    html = '''Select file:<br />
<form id="editor_form" enctype="multipart/form-data" method="%(form_method)s"
    action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="output_format" value="%(output_format)s" />
<input id="editorpath" class="fillwidth padspace" type="text" name="path"
    value="%(path)s" />
<br /><br />
Edit contents:<br />
<textarea id="editorarea" class="fillwidth padspace" rows="25"
          name="editarea">%(text)s</textarea>
''' % fill_helpers
    if 'switcher' in includes:
        html += '''
<ul id="switcher">
<li class="html currentSet"><a href="#">HTML/Text Editor</a></li>
<li class="codemirror"><a href="#">Code Editor</a></li>
<!-- <li class="txt2tags"><a href="#">Txt2Tags Editor</a></li> -->
<li class="remove"><a href="#">Raw text field</a></li>
</ul>
'''
    if 'newline' in includes:
        html += '''
<br />
Newline mode:
<select name="newline">
<option selected value="unix">UNIX</option>
<option value="mac">Mac OS (pre OS X)</option>
<option value="windows">DOS / Windows</option>
</select>
<a class="infolink iconspace" href="http://en.wikipedia.org/wiki/Newline">help
</a>
'''
    if 'submit' in includes:
        html += '''
<br />
Submit file as job after saving <input type=checkbox name="submitjob" />
'''
    if 'save' in includes:
        html += '''
<br />
"Save changes" stores the edited contents in the selected file.<br />
"Forget changes" reloads the last saved version of the selected file.<br />
<input type="submit" value="Save" />
----------
<input type="reset" value="Forget changes" />
'''
        
    html += '''
</form>
'''
    
    if 'discard' in includes:
        target_op = 'rm'
        csrf_token = make_csrf_token(configuration, form_method, target_op,
                                     client_id, csrf_limit)
        fill_helpers.update({'target_op': target_op, 'csrf_token': csrf_token})
        html += '''
<form id="discard_form" method="%(form_method)s" action="%(target_op)s.py">
<input type="hidden" name="%(csrf_field)s" value="%(csrf_token)s" />
<input type="hidden" name="output_format" value="%(output_format)s" />
<input type="hidden" name="flags" value="rf" />
<input type="hidden" name="path" value="%(path)s%(lock_suffix)s" />
<input type="submit" value="Discard changes" />
</form>
''' % fill_helpers
    if 'spellcheck' in includes:
        html += '''
<p>
<form id="spell_form" method="%(form_method)s" action="spell.py">
<input type="hidden" name="output_format" value="%(output_format)s" />
Spell check (last saved) contents:<br />
<input type="hidden" name="path" value="%(path)s" />
Language:
<select name="lang">
<option value="da">Danish</option>
<option value="da_dk">Danish - DK</option>
<option selected value="en">English</option>
<option value="en_gb">English - GB</option>
<option value="en_us">English - US</option>
</select>
Type:
<select name="mode">
<option selected value="none">Text</option>
<option value="url">URL</option>
<option value="email">Email</option>
<option value="sgml">SGML</option>
<option value="tex">LaTeX</option>
</select>
<input type="submit" value="Check" />
</form>
<p>
'''
    return html % fill_helpers


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

    # TODO: if validator is too tight we should accept rejects here
    #   and then make sure that such rejected fields are never printed

    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    path = accepted['path'][-1]
    current_dir = accepted['current_dir'][-1]

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.user_home,
                               client_dir)) + os.sep

    # the client can choose to specify the path of the target directory with
    # current_dir + "/" + path, instead of specifying the complete path in
    # subdirs. This is usefull from ls.py where a hidden html control makes it
    # possible to target the directory from the current dir.

    title_entry = find_entry(output_objects, 'title')
    title_entry['text'] = '%s file web editor' % configuration.short_title
    title_entry['style'] = advanced_editor_css_deps()
    title_entry['javascript'] = advanced_editor_js_deps()
    title_entry['javascript'] += lock_info('this file', -1)
    output_objects.append({'object_type': 'header', 'text'
                          : 'Editing file in %s home directory' % \
                            configuration.short_title })

    if not path:
        now = time.gmtime()
        path = 'noname-%s.txt' % time.strftime('%d%m%y-%H%M%S', now)
        output_objects.append({'object_type': 'text', 'text'
                              : 'No path supplied - creating new file in %s'
                               % path})

    rel_path = os.path.join(current_dir.lstrip(os.sep), path.lstrip(os.sep))
    # IMPORTANT: path must be expanded to abs for proper chrooting
    abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
    if not valid_user_path(abs_path, base_dir):
        logger.warning('%s tried to %s restricted path %s ! (%s)'
                       % (client_id, op_name, abs_path, rel_path))
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : "Invalid path! (%s expands to an illegal path)" % path})
        return (output_objects, returnvalues.CLIENT_ERROR)

    (owner, time_left) = acquire_edit_lock(abs_path, client_id)
    if owner == client_id:
        javascript = \
            '''<script type="text/javascript">
setTimeout("newcountdown('%s', %d)", 1)
</script>
'''\
             % (path, time_left / 60)
        output_objects.append({'object_type': 'html_form', 'text'
                              : javascript})

        html = edit_file(configuration, client_id, path, abs_path)
        output_objects.append({'object_type': 'html_form', 'text'
                              : html})
    else:
        output_objects.append(
            {'object_type': 'error_text', 'text'
             : '%s acquired the editing lock for %s! (timeout in %d seconds)'
             % (owner, path, time_left)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    return (output_objects, returnvalues.OK)
