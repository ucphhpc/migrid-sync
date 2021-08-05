#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# debug - Python debug helpers
# Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
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

"""MiG Python Python debug helpers"""

from __future__ import print_function
from __future__ import absolute_import

import os
import sys
try:
    import pygdb.breakpoint
except Exception as exc:
    pygdb = None
    print("ERROR: the python pygdb module is missing: %s" % exc)

from mig.shared.conf import get_configuration_object
from mig.shared.logger import daemon_logger


def init_pygdb(logpath=None):
    """Initialize pygdb with logging
    NOTE: 1) A pygdb instance is needed at the top-most-level 
             of the debugged python program
          2) When debugging NON-daemons make sure to use 'cgi-bin'
    USAGE cgi-bin:
        1) At top-most-level: cgi-bin/X.py:
            from mig.shared.debug import init_pygdb
            pygdb = init_pygdb()
        2) In any of the descendant modules:
            import pygdb.breakpoint
            pygdb.breakpoint.set()
    """
    configuration = get_configuration_object(skip_log=True)
    if not hasattr(configuration, 'gdb_logger'):
        if not logpath:
            logpath = os.path.join(configuration.log_dir, "gdb.log")

        logger = configuration.gdb_logger = daemon_logger(
            "gdb",
            level=configuration.loglevel,
            path=logpath)
    else:
        logger = configuration.gdb_logger

    if not pygdb:
        msg = "The python pygdb module is missing"
        logger.error(msg)
        raise RuntimeError(msg)

    pygdb.breakpoint.enable(logger=logger)

    return pygdb
