#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sitecustomize - site-specific setup auto-loaded if in PYTHONPATH
# Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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

"""Site-specific configuration hook as explained e.g. on
https://docs.python.org/2.7/library/site.html

Include the module dir in PYTHONPATH to enable where needed.

This particular hook changes the default encoding to utf-8, which seems
required in order to get wgidav-3.x working with non-ascii character filenames
on python 2. The wsgidav library relies on Jinja2 and fails with unicode
decoding errors when rendering output from (ascii) templates filling with
 utf-8 encoded variables.
"""

import sys
sys.setdefaultencoding('UTF-8')
print("fixed default encoding: %s" % sys.getdefaultencoding())
