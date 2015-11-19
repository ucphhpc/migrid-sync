#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# vncfunctions - vnc helper functions for interactive jobs
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

"""VNC helper functions"""

import os
import tempfile
import random
import base64
import popen2

from shared.defaults import vnc_pw_len


def create_vnc_password():
    """Create vnc password"""

    password = ''
    try:
        rand = random.Random()
        for i in range(vnc_pw_len):
            index = rand.randint(32, 255)
            password += chr(index)
        password = base64.urlsafe_b64encode(password)[:vnc_pw_len]
        (filehandle, passwdfile) = tempfile.mkstemp(dir='/tmp', text=False)
        os.close(filehandle)
        (sdout, sdin) = popen2.popen2('vncpasswd %s' % passwdfile)
        sdin.write(password + '\n')
        sdin.flush()
        sdin.write(password + '\n')
        sdin.flush()
        return (True, (password, passwdfile))
    except Exception, err:
        return (False, 'Error creating vnc password (%s)' % err)
