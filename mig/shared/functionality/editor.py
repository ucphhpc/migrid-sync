#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# editor - Online editor back end
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

""" Simple web based file editor to edit files in MiG home

Enable users to make (limited) changes to their files without the
need to download, edit and upload the files.
"""

import os
import sys
import glob
import time

from shared.validstring import valid_user_path
from shared.editing import acquire_edit_lock, get_edit_lock_suffix
from shared.init import initialize_main_variables
from shared.functional import validate_input_and_cert, REJECT_UNSET
import shared.returnvalues as returnvalues
from shared.useradm import client_id_dir


def signature():
    """Signature of the main function"""

    defaults = {'path': [''], 'current_dir': ['']}
    return ['html_form', defaults]


def lock_info(real_path, time_left):

    # This function generates javascript similar to that used in Moin Moin Wiki
    # (http://moinmoin.wikiwikiweb.de)

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


def edit_file(path, real_path):
    """Format and return the contents of a given file"""

    text = ['']
    if os.path.isfile(real_path):
        try:
            fd = open(real_path, 'rb')
            text = fd.readlines()
            fd.close()
        except Exception, e:
            return 'Failed to open file %s: %s' % (path, e)

    html = \
        '''Select file:<br>
<form method="post" action="editfile.py">
<input type="text" size='120' name="path" value="%s">
<p>
Edit contents:<br>
<textarea cols="120" rows="25" wrap="off" name="editarea">'''\
         % path
    for line in text:
        html += line

    html += \
        '''</textarea>
<br>
Newline mode:
<select name="newline">
<option selected value="unix">UNIX</option>
<option value="mac">Mac OS (pre OS X)</option>
<option value="windows">DOS / Windows</option>
</select>
(<a href="http://en.wikipedia.org/wiki/Newline">help</a>)
<br>
Submit file as job after saving <input type=checkbox name="submitjob">
<br>
"Save changes" stores the edited contents in the selected file.<br>
"Forget changes" reloads the last saved version of the selected file.<br>
<input type="submit" value="Save">
----------
<input type="reset" value="Forget changes">
</form>
<form method="post" action="rm.py">
<input type="hidden" name="output_format" value="html">
<input type="hidden" name="flags" value="rf">
<input type="hidden" name="path" value="%(path)s%(lock_suffix)s">
<input type="submit" value="Discard changes">
</form>
<p>
<form method="post" action="spell.py">
Spell check (last saved) contents:<br>
<input type="hidden" name="path" value="%(path)s">
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
<input type="submit" value="Check">
</form>
<p>
'''\
         % {'path': path, 'lock_suffix': get_edit_lock_suffix()}
    return html


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_title=False, op_header=False)
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

    # !!! IMPORTANT !!!
    # This is a (dynamic) user interface so we expect html to be used.
    # We don't use CGIOutput for printing since we neither need a
    # status nor like to wait for all data before printing
    # !!!

    # the client can choose to specify the path of the target directory with
    # current_dir + "/" + path, instead of specifying the complete path in
    # subdirs. This is usefull from ls.py where a hidden html control makes it
    # possible to target the directory from the current dir.

    output_objects.append({'object_type': 'title', 'text'
                          : 'MiG file web editor', 'javascript'
                          : lock_info('this file', -1)})
    output_objects.append({'object_type': 'header', 'text'
                          : 'Editing file in MiG home directory'})

    # addMiGhtmlHeader( "MiG file web editor",  "Editing file in MiG home directory of %s " % client_id , printhtml, scripts=lock_info("this file", -1))lock_info("this file", -1)

    if not path:
        now = time.gmtime()
        path = 'noname-%s.txt' % time.strftime('%d%m%y-%H%M%S', now)
        output_objects.append({'object_type': 'text', 'text'
                              : 'No path supplied - creating new file in %s'
                               % path})

    path = os.path.normpath(current_dir + path)
    real_path = os.path.abspath(base_dir + current_dir + path)
    if not valid_user_path(real_path, base_dir):

        # out of bounds!

        output_objects.append({'object_type': 'error_text', 'text'
                              : "You're only allowed to edit your own files! (%s expands to an illegal path)"
                               % path})
        return (output_objects, returnvalues.CLIENT_ERROR)

    (owner, time_left) = acquire_edit_lock(real_path, client_id)
    if owner == client_id:
        javascript = \
            '''<script type="text/javascript">
setTimeout("newcountdown('%s', %d)", 1)
</script>
'''\
             % (path, time_left / 60)
        output_objects.append({'object_type': 'html_form', 'text'
                              : javascript})

        html = edit_file(path, real_path)
        output_objects.append({'object_type': 'html_form', 'text'
                              : html})
    else:
        output_objects.append({'object_type': 'error_text', 'text'
                              : '%s has acquired the editing lock for %s! (timeout in %d seconds)'
                               % (owner, path, time_left)})
        return (output_objects, returnvalues.CLIENT_ERROR)

    return (output_objects, returnvalues.OK)


