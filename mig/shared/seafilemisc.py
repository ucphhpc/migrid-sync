#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# seafilemisc - helpers for interacting with seafile
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

import os
import urllib2

from shared.base import client_id_dir
#from shared.defaults import seafile_conf_dir, authpasswords_filename, \
#     authdigests_filename
from shared.useradm import extract_field


def seafile_register_html(seafile_url, username, configuration):
    """Build html form for restricted seafile registration"""
    register_url = os.path.join(seafile_url, 'accounts', 'register', '')
    # Fetch register page with urllib2 nad extract csrf token for post
    req = urllib2.Request(register_url)
    req.add_header('Referer', seafile_url)
    content = urllib2.urlopen(req)    
    csrf_input = ''
    for line in content:
        if 'csrfmiddlewaretoken' in line:
            pos = line.find('<input ')
            csrf_input = line[pos:]
            break
    content.close()
    register_html = '''
    <div class="formlist">
    <form method="post" action="%(register_url)s">
        %(csrf_input)s
        <!-- prevent user changing email but show it as read-only input field -->
        <input class="input" id="id_email" name="email" type="hidden" value=%(username)s/>
        <fieldset>
        <label for="dummy_email">Username</label>
        <input class="input" id="dummy_email" type="text" value=%(username)s readonly/><br/>
        <label for="id_password1">Password</label>
        <input class="input" id="id_password1" name="password1" type="password" />
        <br/>
        <label for="id_password2">Confirm Password</label>
        <input class="input" id="id_password2" name="password2" type="password" />
        <br/>
        <input type="submit" value="Sign Up" class="submit" /><br/>
        </fieldset>
    </form>
    </div>
''' % {'register_url': register_url, 'csrf_input': csrf_input, 'username': username}

    return register_html

