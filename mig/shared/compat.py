# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# support - helper functions for unit testing
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
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

"""This file contains an assortment of compatibility functions whose
lifetime is intentionally intended to be time limited. We intentionally
place these in their own namespace to make them easily identifiable and
ease their subsequent removal.
"""

from __future__ import absolute_import
from past.builtins import basestring

import codecs
import io
import sys

_TYPE_UNICODE = type(u"")


def _is_unicode(val):
    """Return boolean indicating if the value is a unicode string.

    We avoid the `isinstance(val, unicode)` recommended by PEP8 here since it
    breaks when combined with python-future and futurize.
    """
    return (type(val) == _TYPE_UNICODE)


def ensure_native_string(string_or_bytes):
    """Given a supplied input which can be either a string or bytes
    return a representation providing string operations while ensuring that
    its contents represent a valid series of textual characters.
    """
    if not _is_unicode(string_or_bytes):
        textual_output = str(string_or_bytes, 'utf8')
    else:
        textual_output = string_or_bytes
    return textual_output
