#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# editing - [insert a few words of module description on this line]
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

"""This module contains general functions used for the online
file editor.
"""

import os
import time

# CodeMirror helpers

cm_prefix = '/images/lib/codemirror'
cm_css_prefix = '%s/lib' % cm_prefix
cm_js_prefix = '%s/lib' % cm_prefix
cm_addon_prefix = '%s/addon' % cm_prefix
cm_mode_prefix = '%s/mode' % cm_prefix

cm_css = '''
<!-- CodeMirror style -->
<link rel="stylesheet" type="text/css" href="%s/codemirror.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%s/dialog/dialog.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/codemirror.custom.css" media="screen"/>
''' % (cm_css_prefix, cm_addon_prefix)
cm_javascript = '''
<!-- CodeMirror scripts -->
<script type="text/javascript" src="%s/codemirror.js"></script>
<script src="%s/dialog/dialog.js"></script>
<script src="%s/search/searchcursor.js"></script>
<script src="%s/search/search.js"></script>
<script src="%s/edit/matchbrackets.js"></script>
<script src="%s/xml/xml.js"></script>
<script src="%s/javascript/javascript.js"></script>
<script src="%s/css/css.js"></script>
<script src="%s/htmlmixed/htmlmixed.js"></script>
''' % (cm_js_prefix, cm_addon_prefix, cm_addon_prefix, cm_addon_prefix,
       cm_addon_prefix, cm_mode_prefix, cm_mode_prefix, cm_mode_prefix,
       cm_mode_prefix)

cm_options = {'matchBrackets': "true", 'indentUnit': 4}

miu_css = '''
<!-- MarkItUp style -->
<link rel="stylesheet" type="text/css" href="/images/lib/markitup/markitup/skins/markitup/style.css" />
<link rel="stylesheet" type="text/css" href="/images/lib/markitup/markitup/sets/txt2tags/style.css" title="txt2tags"/>
<link rel="stylesheet" type="text/css" href="/images/lib/markitup/markitup/sets/html/style.css" title="html"/>
'''
miu_javascript = '''
<!-- MarkItUp scripts -->
<script type="text/javascript" src="/images/lib/markitup/markitup/jquery.markitup.js"></script>
<script type="text/javascript" src="/images/lib/markitup/markitup/sets/html/set.js"></script>
<script type="text/javascript">
var myHtmlSettings = mySettings;
myHtmlSettings["nameSpace"] = "html";
</script>
<script type="text/javascript" src="/images/lib/markitup/markitup/sets/txt2tags/set.js"></script>
<script type="text/javascript">
var myTxt2TagsSettings = mySettings;
myTxt2TagsSettings["nameSpace"] = "txt2tags";
</script>
'''
miu_options = {}

def py_to_js(options):
    """Format python dictionary as dictionary string used in javascript"""

    out = []
    for (key, val) in options.items():
        if isinstance(val, basestring):
            val = '"%s"' % val
        out.append('%s: %s' % (key, val))
    return '{%s}' % ', '.join(out)

def wrap_edit_area(name, area, edit_opts=cm_options, toolbar_buttons='ALL',
                   exec_callback=None):
    """Wrap HTML textarea in user friendly editor with syntax highlighting
    and optional basic toolbar.
    if exec_callback is set to a string the wrapping will not be executed but
    a function called the provided exec_callback name will be prepared for
    delayed wrapping.
    """
    run_script = '''
var editor = new TextAreaEditor(document.getElementById("%stoolbar"),
                                    document.getElementById("%s"), %s);
'''
    if exec_callback:
        run_script = '''
function %s() {
%s        
}
''' % (exec_callback, run_script)
        
    init_buttons = ''
    button_impl = ''
    if toolbar_buttons:
        # TODO: switch to python generated html with icon buttons!
        init_buttons = '''  
  this.spellcheck;
  makeField(this.searchid, 15);
  makeButton("Search", "search");
  makeField(this.replaceid, 15);
  makeButton("Replace", "replace");
  makeButton("Replace All", "replaceall");
  makeSpace("SearchSep");
  makeButton("Undo", "undo");
  makeButton("Redo", "redo");
  makeSpace("UndoSep");
  makeButton("Help", "help");
'''
        button_impl = '''
  search: function() {
    var text = document.getElementById(this.searchid).value;
    if (!text) {
      alert("Please specify something in the search field!");
      return;
    }
    var first = true;
    var line = this.editor.getCursor()
    do {
      if (!first) line = 0;
      var cursor = this.editor.getSearchCursor(text, line, first);
      first = false;
      while (cursor.findNext()) {
        this.editor.setSelection(cursor.from(), cursor.to());
        return;
      }
    } while (confirm("End of document reached. Start over?"));
  },

  replace: function() {
    var from = document.getElementById(this.searchid).value;
    if (!from) {
      alert("Please specify something to replace in the search field!");
      return;
    }
    var to = document.getElementById(this.replaceid).value;
    var cursor = this.editor.getSearchCursor(from, this.editor.pos, false);
    while (cursor.findNext()) {
      this.editor.setSelection(cursor.from(), cursor.to());
      if (confirm("Replace selected entry with '" + to + "'?")) {
        cursor.replace(to);
      }
    }
  },

  replaceall: function() {
    var from = document.getElementById(this.searchid).value, to;
    if (!from) {
      alert("Please specify something to replace in the search field!");
      return;
    }
    var to = document.getElementById(this.replaceid).value;

    var cursor = this.editor.getSearchCursor(from, false);
    while (cursor.findNext()) {
      cursor.replace(to);
    }
  },

  undo: function() {
    this.editor.undo();
  },
  
  redo: function() {
    this.editor.redo();
  },
  
  help: function() {
    alert("Quick help:\\n\\nShortcuts:\\nCtrl-z: undo\\nCtrl-y: redo\\nTab re-indents line\\nEnter inserts a new indented line\\n\\nPlease refer the CodeMirror manual for more detailed help.");
  },
'''

    if toolbar_buttons == 'ALL':
        init_buttons += '''
  makeSpace("HelpSep");
  makeField(this.jumpid, 2);
  makeButton("Jump to line", "jump");
  makeSpace("JumpSep");
  makeButton("Re-Indent all", "reindent");
  makeSpace("IndentSep");
  makeButton("Toggle line numbers", "line");
  //makeSpace("LineSep");
  //makeButton("Toggle spell check", "spell");
'''
        button_impl += '''
  jump: function() {
    var line = document.getElementById(this.jumpid).value;
    if (line && !isNaN(Number(line)))
      this.editor.scrollIntoView(Number(line));
    else
      alert("Please specify a line to jump to in the jump field!");
  },

  line: function() {
    this.editor.setOption("lineNumbers", !this.editor.getOption("lineNumbers"));
    this.editor.focus();
  },

  reindent: function() {
    var that = this.editor;
    var last = that.lineCount();
    that.operation(function() {
                       for (var i = 0; i < last; ++i) that.indentLine(i);
                   });
  },
  
  spell: function() {
    if (this.spellcheck == undefined) this.spellcheck = !this.editor.options.disableSpellcheck;
    this.spellcheck = !this.spellcheck
    this.editor.setSpellcheck(this.spellcheck);
    this.editor.focus();
  },
'''

    script = '''
/*
Modified version of the MirrorFrame example from CodeMirror:
Adds a basic toolbar to the editor widget with limited use of alert popups.
*/


function dumpobj(obj) {
  alert("dump: " + obj.toSource());
}


function TextAreaEditor(toolbar, textarea, options) {
  this.bar = toolbar;
  this.prefix = textarea;
  this.searchid = this.prefix + "searchfield";
  this.replaceid = this.prefix + "replacefield";
  this.jumpid = this.prefix + "jumpfield";

  var self = this;
  function makeButton(name, action) {
    var button = document.createElement("INPUT");
    button.type = "button";
    button.value = name;
    self.bar.appendChild(button);
    button.onclick = function() { self[action].call(self); };
  }
  function makeField(name, size) {
    var field = document.createElement("INPUT");
    field.type = "text";
    field.id = name;
    field.size = size;
    self.bar.appendChild(field);
  }
  function makeSpace(name) {
    var elem = document.createTextNode(" | ");
    self.bar.appendChild(elem);
  }

%s  

  this.editor = CodeMirror.fromTextArea(textarea, options);
}

TextAreaEditor.prototype = {
%s
};
''' % (init_buttons, button_impl)
    out = '''
<div class="inlineeditor" id="%sinlineeditor">
<div class="editortoolbar" id="%stoolbar">
<!-- filled by script -->
</div>
%s
<script type="text/javascript">
%s
'''
    out += run_script
    out += '''
</script>
</div>
'''
    return out % (name, name, area, script, name, name, py_to_js(edit_opts))


# Edit lock functions


def get_edit_lock_suffix():
    return '.editor_lock__'


def get_edit_lock_default_timeout():
    """Allow locking files for 600 seconds i.e. 10 minutes."""

    return 600


def acquire_edit_lock(real_path, client_id):
    """Try to lock file in real_path for exclusive editing. On success the
    file is locked and client_id is returned along with the
    default timeout in seconds. In case someone else actively holds the lock,
    the corresponding client_id is returned along with the
    remaining time in seconds before the current lock will expire.
    If the file is already locked by the requester the lock is updated in order
    to reset the timeout. Stale locks are simply removed before the check.
    Please note that locks don't prevent users from seeing the last saved
    version of the file, only from truncating any concurrent changes.
    """

    default_timeout = get_edit_lock_default_timeout()
    take_lock = False
    lock_path = real_path + get_edit_lock_suffix()
    info_path = lock_path + os.sep + 'info'

    # We need atomic operation in locking - check for file or create followed by
    # lock won't do! mkdir is atomic, so it can work as a lock.

    try:
        os.makedirs(lock_path)
        lock_exists = False
    except OSError, ose:

        # lock dir exists - previously locked

        lock_exists = True

    now = time.mktime(time.gmtime())
    if lock_exists:

        # Read lock info - any error here means an invalid lock -> truncate

        try:
            info_fd = open(info_path, 'r+')
            info_lines = info_fd.readlines()
            info_fd.close()
            owner = info_lines[0].strip()
            timestamp = float(info_lines[1].strip())
            time_left = default_timeout - (now - timestamp)
        except Exception, err:
            print 'Error: %s - taking broken lock' % err
            owner = client_id
            time_left = default_timeout
            take_lock = True

        if owner == client_id or time_left < 0:
            take_lock = True
    else:
        take_lock = True

    if take_lock:
        owner = client_id
        time_left = default_timeout

        # Truncate info file

        try:
            info_fd = open(info_path, 'w')
            info_fd.write('''%s
%f
''' % (client_id, now))
            info_fd.close()
        except Exception, err:
            print 'Error opening or writing to %s, (%s)' % (info_path,
                    err)

    return (owner, time_left)


def got_edit_lock(real_path, client_id):
    """Check that caller actually acquired the required file editing lock. 
    """

    lock_path = real_path + get_edit_lock_suffix()
    info_path = lock_path + os.sep + 'info'

    # We need atomic operation in locking - check for file or create followed by
    # lock won't do! mkdir is atomic, so it can work as a lock.

    try:
        os.mkdir(lock_path)

        # lock didn't exist - clean up and fail

        os.rmdir(lock_path)
        return False
    except OSError, ose:

        # lock dir exists - previously locked

        pass

    # Read lock info - any error here means an invalid lock

    try:
        info_fd = open(info_path, 'r+')
        info_lines = info_fd.readlines()
        info_fd.close()
        now = time.mktime(time.gmtime())
        owner = info_lines[0].strip()
        timestamp = float(info_lines[1].strip())
        time_left = get_edit_lock_default_timeout() - (now - timestamp)
    except Exception, err:
        print 'Error: %s - not accepting invalid lock' % err
        return False

    if owner != client_id:
        print "Error: You don't have the lock for %s - %s does"\
             % (real_path, owner)
        return False
    elif time_left < 0:

        print "Error: You don't have the lock for %s any longer - time out %f seconds ago"\
             % (real_path, -time_left)
        return False
    else:
        return True


def release_edit_lock(real_path, client_id):
    """Try to release an acquired file editing lock. Check that owner
    matches release caller.
    """

    if not got_edit_lock(real_path, client_id):
        return False

    # We need atomic operation in locking - remove info file followed by
    # rmdir won't do! rename is atomic, so it can work as removal of lock.
    # create unique dir in tmp to avoid clashes and manual clean up on errors

    lock_path = real_path + get_edit_lock_suffix()
    stale_lock_path = lock_path + 'stale__'
    stale_info_path = stale_lock_path + os.sep + 'info'
    try:
        os.rename(lock_path, stale_lock_path)
        os.remove(stale_info_path)
        os.rmdir(stale_lock_path)
    except OSError, ose:

        # rename failed - previously locked

        print 'Error: renaming and removing lock dir: %s' % ose
        return False
    return True


