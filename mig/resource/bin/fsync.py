#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# fsync - Simple wrapper for the file sync sys call
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

"""Call fsync sys call on provided paths to force buffer sync to disk without requiring general sync of all buffered files as in sync command.
This is intended as a workaround for delayed writes on NFS.
"""

import os
import sys

if len(sys.argv) < 2:
    print "Usage: %s PATH [PATH ...]" % \
          os.path.basename((sys.argv)[0])
    sys.exit(1)

for path in (sys.argv)[1:]:
    # TODO: This is completely untested!
    # From python library reference:
    # If you're starting with a Python file object f, first
    # do f.flush(), and then do os.fsync(f.fileno()), to
    # ensure that all internal buffers associated with f
    # are written to disk.
    #
    # The question is if this works when the flush was called
    # by another process.
    sync_fd = open(path, 'rb+', 0)
    os.fsync(sync_fd)
    sync_fd.close()
