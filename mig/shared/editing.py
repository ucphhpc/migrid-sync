#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# editing - helper functions for the inline editors
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

"""This module contains general functions used for the online
file editor.
"""

import os
import time

from shared.defaults import edit_lock_suffix, edit_lock_timeout

# CodeMirror helpers

cm_prefix = '/images/lib/codemirror'
cm_css_prefix = '%s/lib' % cm_prefix
cm_js_prefix = '%s/lib' % cm_prefix
cm_addon_prefix = '%s/addon' % cm_prefix
cm_mode_prefix = '%s/mode' % cm_prefix
cmui_prefix = '/images/lib/codemirror-ui'
cmui_js_prefix = '%s/js' % cmui_prefix
cmui_css_prefix = '%s/css' % cmui_prefix
cmui_images_prefix = '%s/images/silk' % cmui_prefix

cm_css = '''
<!-- CodeMirror style -->
<link rel="stylesheet" type="text/css" href="%s/codemirror.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%s/dialog/dialog.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="%s/codemirror-ui.css" media="screen" title="codemirror-ui" />
<link rel="stylesheet" type="text/css" href="/images/css/codemirror.custom.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/codemirror-ui.custom.css" media="screen"/>
''' % (cm_css_prefix, cm_addon_prefix, cmui_css_prefix)
cm_javascript = '''
<!-- CodeMirror scripts -->
<script type="text/javascript" src="%s/codemirror.js"></script>
<script type="text/javascript" src="%s/dialog/dialog.js"></script>
<script type="text/javascript" src="%s/search/searchcursor.js"></script>
<script type="text/javascript" src="%s/search/search.js"></script>
<script type="text/javascript" src="%s/edit/matchbrackets.js"></script>
<script type="text/javascript" src="%s/xml/xml.js"></script>
<script type="text/javascript" src="%s/javascript/javascript.js"></script>
<script type="text/javascript" src="%s/css/css.js"></script>
<script type="text/javascript" src="%s/htmlmixed/htmlmixed.js"></script>
<!-- CodeMirror UI scripts -->
<script type="text/javascript" src="%s/codemirror-ui.js"></script>
''' % (cm_js_prefix, cm_addon_prefix, cm_addon_prefix, cm_addon_prefix,
       cm_addon_prefix, cm_mode_prefix, cm_mode_prefix, cm_mode_prefix,
       cm_mode_prefix, cmui_js_prefix)

cm_options = {'matchBrackets': "true", 'indentUnit': 4}
cmui_options = {'path': cmui_js_prefix, 'imagePath': cmui_images_prefix,
                'searchMode': 'popup'}

miu_css = '''
<!-- MarkItUp style -->
<link rel="stylesheet" type="text/css" href="/images/lib/markitup/markitup/skins/markitup/style.css"/>
<!--
<link rel="stylesheet" type="text/css" href="/images/lib/markitup/markitup/sets/txt2tags/style.css" title="txt2tags"/>
-->
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
<!--
<script type="text/javascript" src="/images/lib/markitup/markitup/sets/txt2tags/set.js"></script>
<script type="text/javascript">
var myTxt2TagsSettings = mySettings;
myTxt2TagsSettings["nameSpace"] = "markitup-txt2tags";
</script>
-->
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

def html_wrap_js(code):
    """Wrap a chunk of javascript in HTML script tags"""
    return '''
<script type="text/javascript">
    %s
</script>
''' % code

def create_editor_area(name, area):
    """Create HTML textarea for use by user friendly code editor with syntax
    highlighting and basic toolbar.
    """
    out = '''
    <div class="inlineeditor" id="%sinlineeditor">
    %s
    </div>
    ''' % (name, area)
    return out

def init_editor_js(name, edit_opts, wrap_in_tags=True):
    """Return javascript to init wrap of HTML textarea in user friendly code
    editor with syntax highlighting and basic toolbar.
    If wrap_in_tags is set the javascript will be wrapped in html script tags.
    """
    out = '''
    function run_%s_editor() {
        var textarea = document.getElementById("%s");
        var uiOptions = %s;
        var codeMirrorOptions = %s;
        new CodeMirrorUI(textarea, uiOptions, codeMirrorOptions);
    }
    ''' % (name, name, py_to_js(cmui_options), py_to_js(edit_opts))
    if wrap_in_tags:
        out = html_wrap_js(out)
    return out

def run_editor_js(name, wrap_in_tags=True):
    """Create javascript to actually wrap a previously initialized HTML
    textarea in user friendly code editor with syntax highlighting and basic
    toolbar.
    If wrap_in_tags is set the javascript will be wrapped in html script tags.
    """
    out = '''
    var %s_editor = run_%s_editor();
    ''' % (name, name)
    if wrap_in_tags:
        out = html_wrap_js(out)
    return out

def kill_editor_js(name, wrap_in_tags=True):
    """Create javascript to actually unwrap a previously wrapped HTML
    textarea code editor.
    If wrap_in_tags is set the javascript will be wrapped in html script tags.
    """
    out = '''
    delete %s_editor;
    ''' % name
    if wrap_in_tags:
        out = html_wrap_js(out)
    return out

def wrap_edit_area(name, area, edit_opts=cm_options, toolbar_buttons='ALL',
                   exec_callback=None):
    """Wrap HTML textarea in user friendly code editor with syntax highlighting
    and basic toolbar.
    The area variable should contain a string with HTML form code to wrap.
    """
    out = create_editor_area(name, area)
    out += init_editor_js(name, edit_opts)
    out += run_editor_js(name)
    return out


# Edit lock functions

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

    default_timeout = edit_lock_timeout
    take_lock = False
    lock_path = real_path + edit_lock_suffix
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

    lock_path = real_path + edit_lock_suffix
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
        time_left = edit_lock_timeout - (now - timestamp)
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

    lock_path = real_path + edit_lock_suffix
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


