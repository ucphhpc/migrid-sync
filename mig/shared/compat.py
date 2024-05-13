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
lifetime is intentionally intended to be time limited."""

from __future__ import absolute_import
import codecs
import sys

PY2 = sys.version_info[0] < 3

from mig.shared.base import STR_KIND, _force_default_coding


def ensure_native_string(string_or_bytes):
    """Given a supplied input which can be either a string or bytes
    return a representation string operations while ensuring that its
    contents represent a valid series of textual characters.

    Arrange identical operation across python 2 and 3 - specifically,
    the presence of invalid UTF-8 bytes (thus the input not being a
    valid textual string) will trigger a UnicodeDecodeError on PY3.
    Force the same to occur on PY2.
    """
    textual_output = _force_default_coding(string_or_bytes, STR_KIND)
    if PY2:
        # Simulate decoding done by PY3 to trigger identical exceptions
        # note the used of a forced "utf8" encoding value: this function
        # is generally used to wrap, for example, substitutions of values
        # into strings that are defined in the source code. In Python 3
        # these are mandated to be UTF-8, and thus decoding as "utf8" is
        # what will be attempted on supplied input. Match it.
        codecs.decode(textual_output, "utf8")
    return textual_output
