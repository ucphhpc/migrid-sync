#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# jobsjsoninterface - JSON interface for managing workflows
# Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# -- END_HEADER ---
#

"""JSON interface for job related requests"""

import cgi
import cgitb
cgitb.enable()

from mig.shared.functionality.jobsjsoninterface import main
from mig.shared.cgiscriptstub import run_cgi_script_possibly_with_cert

# Expect requests with a JSON formatted body and no field values
run_cgi_script_possibly_with_cert(main, delayed_input=True, delay_format=True)
