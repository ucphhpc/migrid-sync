#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# safeeval - Safe evaluation of expressions and commands
# Copyright (C) 2003-2023  The MiG Project
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

import codecs
import sys

PY2 = sys.version_info[0] == 2

if PY2:
    def _as_ascii_string(value): return value
else:
    def _as_ascii_string(value): return codecs.decode(value, 'ascii')


def safename_encode(value):
    return _as_ascii_string(codecs.encode(value, 'punycode'))


def safename_decode(value):
    return codecs.decode(value, 'punycode')
